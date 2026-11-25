"""
Stimuli and trial lists: the geometry of the display, the order of the blocks,
the window, the slider, the response bar and the axes of the TET.
"""

import itertools
import math
import re

import numpy as np
from psychopy import monitors, visual

from .init import *
from .text import *

try:
    import serial
except ImportError:
    serial = None  # only needed with SLIDER_INPUT = "device"

# =============================================================================
# Stimuli (cm; at 57.3 cm, 1 cm = 1 degree of visual angle)
# =============================================================================

FIX_DIAM_CM = .27
TARGET_SIZE_CM = 1.8         # 6 SD of the Gaussian mask (SD = 0.3 cm)
TARGET_ANGLE_DEG = 135.0     # upper left
TARGET_ECC_CM = {"peripheral": 5.45, "near_fixation": 1.0}
CROSS_WIDTH_CM = .8
CROSS_ARM_RATIO = .1
GRID_N = 11                  # mask: a grid of 11 x 11 crosses
GRID_SPACING_CM = CROSS_WIDTH_CM * 1.5
ROTATION_HZ = .37           # cycles per second of the mask
# Crosses are not drawn within this distance of the fixation point and the target
CLEARANCE_CM = .9 + CROSS_WIDTH_CM / 2 + .05

BG_COLOR = [0.0, 0.0, 0.0]
FIX_COLOR = [-1.0, -1.0, -1.0]
TARGET_COLOR = [1.0, 1.0, 1.0]
CROSS_COLOR = [-.18, -.18, -.18]
TEXT_COLOR = [-1.0, -1.0, -1.0]
EMPHASIS_COLOR = [1.0, .8, -.2]
TRACE_COLOR = [.8, -.4, -.4]
BAR_FRAME_COLOR = [-.7, -.7, -.7]
BAR_FILL_COLOR = [.6, .6, .6]

# Slider response at the start of a trial when it is not read from the device
START_VALUE = {"peripheral": .5, "near_fixation": 1.0, "calibration_up": 0.0,
               "calibration_down": 1.0, "calibration_sinusoidal": 1.0}


def clamp(x, low, high):
    return max(low, min(x, high))


def pol2cart(r, theta_deg):
    theta = math.radians(theta_deg)
    return np.array([r * math.cos(theta), r * math.sin(theta)])


def rect_vertices(width, height):
    w, h = width / 2, height / 2
    return np.array([[-w, h], [w, h], [w, -h], [-w, -h]])


def cross_vertices(width, arm_ratio):
    w, t = width / 2, width * arm_ratio / 2
    return np.array([[-t, w], [t, w], [t, t], [w, t], [w, -t], [t, -t],
                     [t, -w], [-t, -w], [-t, -t], [-w, -t], [-w, t], [-t, t]])


def circle_vertices(radius, n=64):
    angles = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.column_stack((radius * np.cos(angles), radius * np.sin(angles)))


# =============================================================================
# Trial lists
# =============================================================================

def block_order(participant):
    """The order of the three blocks: the permutation of METHODS at position
    participant number modulo 6."""
    orders = list(itertools.permutations(METHODS))
    return orders[participant % len(orders)]


def make_block(rng):
    """The trial types of one experimental block, in random order."""
    trials = [trial_type for trial_type, n in N_PER_TYPE.items() for _ in range(n)]
    rng.shuffle(trials)
    return trials


def target_contrast(trial_type, t, duration):
    """Contrast of the target at time t: constant in the MIB trials, and following
    the visibility to track in the calibration trials."""
    if trial_type == "calibration_up":
        ramp = max(duration - CALIBRATION_HOLD_S, .001)
        return 1.0 if t >= ramp else clamp(t / ramp, 0.0, 1.0)
    if trial_type == "calibration_down":
        ramp = max(duration - CALIBRATION_HOLD_S, .001)
        return 0.0 if t >= ramp else clamp(1.0 - t / ramp, 0.0, 1.0)
    if trial_type == "calibration_sinusoidal":
        return .5 + .5 * math.cos(2 * math.pi * CALIBRATION_SINE_HZ * t)
    return 1.0


def resample_trace(points, duration):
    """The drawn trace on the same time grid as the other methods. The points are
    (time, visibility) as proportions of the axes; between them, the trace is
    interpolated linearly."""
    x, y = np.asarray(points, dtype=float).T
    times = np.arange(0.0, duration, 1.0 / SAMPLE_HZ)
    return times, np.interp(np.clip(times / duration, 0.0, 1.0), x, y, left=y[0], right=y[-1])


# =============================================================================
# Window and stimuli
# =============================================================================

def setup_window():
    mon = monitors.Monitor(MONITOR_NAME)
    mon.setWidth(MONITOR_WIDTH_CM)
    mon.setSizePix(MONITOR_SIZE_PX)
    mon.setDistance(MONITOR_DISTANCE_CM)
    win = visual.Window(size=MONITOR_SIZE_PX, monitor=mon, units="cm", fullscr=FULLSCREEN, color=BG_COLOR,
                        colorSpace="rgb", allowGUI=not FULLSCREEN)
    rate = win.getActualFrameRate(nIdentical=20, nMaxFrames=240, nWarmUpFrames=30, threshold=1)
    if rate is None or abs(rate - 60) > 3:
        print(f"Warning: the measured refresh rate is {rate} Hz (60 Hz expected).")
    return win, rate


class Scene:
    """The display of a trial: mask of rotating crosses, fixation point and target.
    The calibration trials have only the target, at the centre of the screen."""

    def __init__(self, win):
        coords = (np.arange(GRID_N) - (GRID_N - 1) / 2) * GRID_SPACING_CM
        self.grid = np.array([(x, y) for y in coords for x in coords])
        vertices = cross_vertices(CROSS_WIDTH_CM, CROSS_ARM_RATIO)
        self.crosses = [visual.ShapeStim(win, vertices=vertices, closeShape=True, fillColor=CROSS_COLOR,
                                         lineColor=CROSS_COLOR, lineWidth=1, pos=xy, ori=0, colorSpace="rgb", units="cm")
                        for xy in self.grid]
        self.fixation = visual.ShapeStim(win, vertices=circle_vertices(FIX_DIAM_CM / 2), closeShape=True, pos=(0, 0),
                                         fillColor=FIX_COLOR, lineColor=FIX_COLOR, lineWidth=1, colorSpace="rgb", units="cm")
        self.target = visual.GratingStim(win, tex=np.ones((256, 256)), mask="gauss", size=TARGET_SIZE_CM, pos=(0, 0),
                                         color=TARGET_COLOR, colorSpace="rgb", units="cm", interpolate=True)
        self.target_pos = {trial_type: pol2cart(ecc, TARGET_ANGLE_DEG) for trial_type, ecc in TARGET_ECC_CM.items()}

    def draw(self, trial_type, t, duration=None):
        calibration = trial_type.startswith("calibration")
        pos = np.zeros(2) if calibration else self.target_pos[trial_type]
        if not calibration:
            angle = (360.0 * ROTATION_HZ * t) % 360.0
            c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
            x, y = self.grid.T
            rotated = np.column_stack((c * x - s * y, s * x + c * y))
            outside = ((np.linalg.norm(rotated, axis=1) >= CLEARANCE_CM)
                       & (np.linalg.norm(rotated - pos, axis=1) >= CLEARANCE_CM))
            for cross, xy, draw in zip(self.crosses, rotated, outside):
                if draw:
                    cross.pos = xy
                    cross.ori = angle
                    cross.draw()
            self.fixation.draw()
        contrast = target_contrast(trial_type, t, duration)
        if contrast > 0:
            self.target.pos = pos
            self.target.contrast = contrast
            self.target.draw()


class ResponseBar:
    """Indicator of the slider response, at the right of the screen (shown only in
    the demo of the slider and in the calibration)."""

    HEIGHT_CM = 8.0
    X_CM = 18.5

    def __init__(self, win):
        self.frame = visual.ShapeStim(win, vertices=rect_vertices(.8, self.HEIGHT_CM), closeShape=True, pos=(self.X_CM, 0),
                                      lineColor=BAR_FRAME_COLOR, fillColor=None, lineWidth=2, units="cm")
        self.fill = visual.ShapeStim(win, vertices=rect_vertices(.6, .04), closeShape=True, pos=(self.X_CM, -4),
                                     lineColor=BAR_FILL_COLOR, fillColor=BAR_FILL_COLOR, lineWidth=1, units="cm")
        self.labels = [visual.TextStim(win, text=txt, pos=(self.X_CM, y), height=h, color=TEXT_COLOR, colorSpace="rgb",
                                       units="cm", wrapWidth=w, alignText="center")
                       for txt, y, h, w in ((BAR_LABEL, 5.2, .45, None), (BAR_TOP, 4.95, .31, 4.4), (BAR_BOTTOM, -5.0, .31, 4.1))]

    def draw(self, value):
        height = max(.04, self.HEIGHT_CM * value)
        self.fill.vertices = rect_vertices(.6, height)
        self.fill.pos = (self.X_CM, -self.HEIGHT_CM / 2 + height / 2)
        for stim in (self.frame, self.fill, *self.labels):
            stim.draw()


class TetAxes:
    """The axes on which the participants draw the trace."""

    LEFT, RIGHT, BOTTOM, TOP = -8.0, 8.0, -4.0, 4.0

    def __init__(self, win):
        text = dict(color=TEXT_COLOR, colorSpace="rgb", units="cm")
        self.stims = [
            visual.TextStim(win, text=TET_DRAW, pos=(0, 7), height=.5, wrapWidth=26, **text),
            visual.ShapeStim(win, vertices=rect_vertices(self.RIGHT - self.LEFT, self.TOP - self.BOTTOM), closeShape=True,
                             pos=(0, 0), lineColor=TEXT_COLOR, fillColor=None, lineWidth=1, units="cm"),
            visual.Line(win, start=(self.LEFT, self.BOTTOM), end=(self.RIGHT, self.BOTTOM), lineColor=TEXT_COLOR, lineWidth=2, units="cm"),
            visual.Line(win, start=(self.LEFT, self.BOTTOM), end=(self.LEFT, self.TOP), lineColor=TEXT_COLOR, lineWidth=2, units="cm"),
            visual.TextStim(win, text=TET_TIME_AXIS, pos=(0, -5.1), height=.45, **text),
            visual.TextStim(win, text=TET_TOP, pos=(-10.9, 3.45), height=.34, wrapWidth=4.2, alignText="center", **text),
            visual.TextStim(win, text=TET_BOTTOM, pos=(-10.5, -3.55), height=.34, wrapWidth=3.8, alignText="center", **text)]
        self.trace = visual.ShapeStim(win, vertices=[(0, 0), (.1, .1)], closeShape=False, lineColor=TRACE_COLOR,
                                      lineWidth=2, units="cm")

    def draw(self, points):
        for stim in self.stims:
            stim.draw()
        if len(points) >= 2:
            self.trace.vertices = points
            self.trace.draw()


# =============================================================================
# Slider
# =============================================================================

class Slider:
    """The slider response, from 0 (bottom) to 1 (top). With the device, it is
    updated DEVICE_HZ times per second; with the keyboard, on every frame."""

    def __init__(self, is_down):
        self.is_down = is_down  # function: is a key held down?
        self.port = None
        self.value = .5
        self.next_query = 0.0
        if SLIDER_INPUT == "device" and not AUTO:
            if serial is None:
                raise RuntimeError("pyserial is not installed (see requirements.txt).")
            try:
                self.port = serial.Serial(port=SERIAL_PORT, baudrate=SERIAL_BAUD, timeout=SERIAL_TIMEOUT_S)
            except serial.SerialException as error:
                raise RuntimeError(f"The slider does not respond on {SERIAL_PORT}: {error}\n"
                                   "Check SERIAL_PORT in task/init.py, or set SLIDER_INPUT = 'keyboard' to try the task without it.")

    def read(self):
        """Query the device; if no level is read, the response does not change."""
        self.port.write(SERIAL_QUERY.encode("ascii"))
        self.port.flush()
        match = re.search(r"-?\d+", self.port.readline().decode("ascii", errors="ignore"))
        if match:
            low, high = SERIAL_LEVELS
            self.value = (clamp(int(match.group(0)), low, high) - low) / (high - low)

    def start(self, value):
        """At the start of a trial: the current position of the device or, with the
        keyboard, the given value."""
        self.value = value
        if self.port:
            self.read()
        self.next_query = 1.0 / DEVICE_HZ

    def update(self, t, dt):
        if AUTO:
            self.value = .5 + .5 * math.cos(2 * math.pi * .2 * t)
        elif self.port:
            if t >= self.next_query:
                self.read()
                while self.next_query <= t:
                    self.next_query += 1.0 / DEVICE_HZ
        else:
            delta = KEYBOARD_RATE * dt * (self.is_down("up") - self.is_down("down"))
            self.value = clamp(self.value + delta, 0.0, 1.0)
        return self.value

    def close(self):
        if self.port:
            self.port.close()
            self.port = None

"""
The session: instructions, demonstration, the block of each method (button,
slider and TET) with its practice, the calibration of the slider and the data
file. Experiment.run() gives the order of the session.
"""

import csv
import math
import os
import random
from datetime import datetime

import numpy as np
from psychopy import core, event, gui, visual
from psychopy.hardware import keyboard
from pyglet.window import key as pyglet_key

from .init import *
from .helper import *
from .text import *

# Data: one CSV per session, one row per sample of the response (see README.md)
COLUMNS = ["participant_id", "age", "gender", "frame_rate",
           "phase", "block", "method", "trial_in_block", "trial_type",
           "time_s", "target_contrast", "response"]

# Keys read as held down (button and keyboard slider) rather than as key presses
HELD_KEYS = {
    "space": pyglet_key.SPACE,
    "escape": pyglet_key.ESCAPE,
    "up": pyglet_key.UP,
    "down": pyglet_key.DOWN,
    "y": pyglet_key.Y,
}


def number(x):
    """A value for the data file: up to six decimals, without trailing zeros."""
    return f"{x:.6f}".rstrip("0").rstrip(".")


class Experiment:

    def __init__(self, participant, demographics):
        fixed = os.environ.get("MIB_SEED") if AUTO else None  # same trial order in two code checks
        self.rng = random.Random(int(fixed)) if fixed else random.Random()
        self.order = block_order(participant)
        self.slider = Slider(self.is_down)  # before the window: the task stops here if the device does not respond
        self.win, frame_rate = setup_window()
        self.win.mouseVisible = False
        self.kb = keyboard.Keyboard()
        self.held = pyglet_key.KeyStateHandler()
        self.win.winHandle.push_handlers(self.held)
        self.scene = Scene(self.win)
        self.bar = ResponseBar(self.win)
        self.axes = TetAxes(self.win)
        self.info = {"participant_id": participant, "frame_rate": "" if frame_rate is None else number(round(frame_rate, 2)), **demographics}
        os.makedirs(DATA_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = os.path.join(DATA_DIR, f"mib_{participant}_{stamp}.csv")
        self.file = open(self.path, "w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.file, fieldnames=COLUMNS)
        self.writer.writeheader()

    # ---- helpers -----------------------------------------------------------

    def save_samples(self, times, contrasts, responses, phase, block, method, trial_in_block, trial_type):
        """Every trial is written as soon as it ends, not during the trial."""
        self.writer.writerows(
            {**self.info, "phase": phase, "block": block, "method": method, "trial_in_block": trial_in_block,
             "trial_type": trial_type, "time_s": number(t), "target_contrast": number(c), "response": number(r)}
            for t, c, r in zip(times, contrasts, responses))
        self.file.flush()

    def is_down(self, key):
        """Is the key held down now? The window updates this on every flip."""
        return bool(self.held[HELD_KEYS[key]])

    def screenshot(self, name):
        if AUTO and name:
            folder = os.path.join(DATA_DIR, "screenshots")
            os.makedirs(folder, exist_ok=True)
            self.win.getMovieFrame(buffer="front")
            self.win.saveMovieFrames(os.path.join(folder, f"{name}.png"))

    def quit(self):
        self.file.close()
        self.slider.close()
        self.win.close()
        core.quit()

    def text(self, txt, pos=(0, 0), height=.58, wrap=26, color=TEXT_COLOR, bold=False):
        return visual.TextStim(self.win, text=txt, pos=pos, height=height, color=color, colorSpace="rgb", units="cm",
                               wrapWidth=wrap, alignText="center", bold=bold)

    def wait_release(self, keys):
        """Wait until none of the keys is held down, so that a key still pressed
        from the previous screen does not carry over."""
        while not AUTO and any(self.is_down(k) for k in keys):
            if self.is_down(QUIT_KEY):
                self.quit()
            core.wait(.01)  # it also updates the state of the keys

    def wait_key(self, stims, keys=("space",), name=None):
        """Show the stimuli until one of the keys is pressed."""
        self.wait_release(keys)
        for stim in stims:
            stim.draw()
        self.win.flip()
        self.screenshot(name)
        if AUTO:
            core.wait(.05)
            return
        self.kb.clearEvents()
        while True:
            for k in self.kb.getKeys(keyList=list(keys) + [QUIT_KEY], waitRelease=False):
                if k.name == QUIT_KEY:
                    self.quit()
                return
            core.wait(.005)

    def screen(self, txt, key="space", name=None):
        """A screen of text, centred, until the key is pressed."""
        self.wait_key([self.text(txt)], (key,), name)

    # ---- trials ------------------------------------------------------------

    def show_trial(self, trial_type, duration, method=None, name=None):
        """The display for the duration of the trial. Button and slider responses
        are read on every frame; each frame gives the value of the samples of the
        time grid (SAMPLE_HZ) that have elapsed. With method=None (demonstration
        and viewing in the TET) nothing is recorded here."""
        self.wait_release(("space", "up", "down") if method == "slider" else ("up", "down"))
        calibration = trial_type.startswith("calibration")
        value = 0.0
        if method == "slider":
            self.slider.start(START_VALUE[trial_type])
        times, contrasts, responses = [], [], []
        k = 0
        last_t = 0.0
        clock = core.Clock()
        while True:
            t = clock.getTime()
            if t >= duration:
                break
            if self.is_down(QUIT_KEY):
                self.quit()
            if method == "button":
                value = float(int(t * 2) % 2) if AUTO else float(self.is_down("space"))
            elif method == "slider":
                value = self.slider.update(t, max(t - last_t, 0.0))
            last_t = t
            self.scene.draw(trial_type, t, duration)
            if calibration:
                self.bar.draw(value)
            self.win.flip()
            if name and t >= duration / 2:
                self.screenshot(name)
                name = None
            if method:
                while k / SAMPLE_HZ <= t and k / SAMPLE_HZ < duration:
                    times.append(k / SAMPLE_HZ)
                    contrasts.append(target_contrast(trial_type, k / SAMPLE_HZ, duration))
                    responses.append(value)
                    k += 1
        return times, contrasts, responses

    def response_trial(self, trial_type, phase, method, block, trial_in_block, duration=TRIAL_S, name=None):
        """A trial of the button or the slider."""
        samples = self.show_trial(trial_type, duration, method, name)
        self.save_samples(*samples, phase, block, method, trial_in_block, trial_type)

    def tet_trial(self, trial_type, phase, block, trial_in_block, name=None):
        """A trial of the TET: the display, without responses, and then the trace,
        which is saved on the time grid of the other methods."""
        self.show_trial(trial_type, TRIAL_S, name=f"{name}_view" if name else name)
        times, responses = resample_trace(self.draw_trace(name=f"{name}_trace" if name else name), TRIAL_S)
        self.save_samples(times, [target_contrast(trial_type, t, TRIAL_S) for t in times], responses,
                          phase, block, "tet", trial_in_block, trial_type)

    def draw_trace(self, name=None):
        """The participant draws the trace with the mouse, from left to right.
        Returns its points as proportions of the axes (time, visibility)."""
        a = self.axes
        width, height = a.RIGHT - a.LEFT, a.TOP - a.BOTTOM
        points = []
        warning = None
        if AUTO:
            x = np.linspace(a.LEFT, a.RIGHT, 200)
            points = list(zip(x, a.BOTTOM + height * (.5 + .5 * np.cos(2 * math.pi * 3 * (x - a.LEFT) / width))))
            a.draw(points)
            self.win.flip()
            self.screenshot(name)
        else:
            mouse = event.Mouse(win=self.win)
            mouse.setVisible(True)
            self.kb.clearEvents()
            while True:
                keys = [k.name for k in self.kb.getKeys(keyList=["return", "r", "backspace", QUIT_KEY], waitRelease=False)]
                if QUIT_KEY in keys:
                    self.quit()
                if "r" in keys or "backspace" in keys:
                    points, warning = [], None
                mouse_x, mouse_y = mouse.getPos()
                if mouse.getPressed()[0] and a.LEFT <= mouse_x <= a.RIGHT:
                    y = clamp(mouse_y, a.BOTTOM, a.TOP)
                    if not points:
                        points.append((a.LEFT, y))  # the trace always starts at the left edge
                    x = max(clamp(mouse_x, a.LEFT, a.RIGHT), points[-1][0])  # time only goes forward
                    if math.hypot(x - points[-1][0], y - points[-1][1]) >= .05:
                        points.append((x, y))
                        warning = None
                if "return" in keys:
                    if points and points[-1][0] >= a.RIGHT - TET_END_TOLERANCE * width:
                        break
                    warning = self.text(TET_INCOMPLETE, pos=(0, -6.5))
                a.draw(points)
                if warning:
                    warning.draw()
                self.win.flip()
            mouse.setVisible(False)
        return [((x - a.LEFT) / width, (y - a.BOTTOM) / height) for x, y in points]

    # ---- parts of the session ----------------------------------------------

    def arrow(self, start, end):
        """A line from start to end with a triangle at the end."""
        start, end = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
        theta = math.atan2(*(end - start)[::-1])
        direction = np.array([math.cos(theta), math.sin(theta)])
        side = np.array([-direction[1], direction[0]]) * .45 / 2
        base = end - direction * .7
        return [visual.Line(self.win, start=tuple(start), end=tuple(end), lineColor=TEXT_COLOR, lineWidth=2, units="cm"),
                visual.ShapeStim(self.win, vertices=np.vstack([end, base + side, base - side]), closeShape=True,
                                 fillColor=TEXT_COLOR, lineColor=TEXT_COLOR, lineWidth=1, colorSpace="rgb", units="cm")]

    def display_example(self):
        """The display, static, with arrows to the target and the fixation point."""
        target = self.scene.target_pos["peripheral"]
        self.scene.draw("peripheral", 0.0)
        self.wait_key([self.text(EXAMPLE_TITLE, pos=(0, 8.2), wrap=28),
                       self.text(EXAMPLE_TARGET, pos=(-13.2, 7.0), height=.5, wrap=None),
                       self.text(EXAMPLE_FIXATION, pos=(11.0, 4.7), height=.5, wrap=None),
                       self.text(EXAMPLE_FOOTER, pos=(0, -9.1), height=.52, wrap=None),
                       *self.arrow((-11.2, 6.4), target + np.array([-.25, .25])),
                       *self.arrow((9.6, 4.0), (0.0, 0.0))], name="display_example")

    def demo(self):
        self.screen(DEMO_INTRO, name="demo_intro")
        self.show_trial("peripheral", DEMO_S, name="demo")
        self.screen(DEMO_END, key="y", name="demo_end")

    def experimental_trials(self, method, block):
        """The trials of a block, with a screen between them."""
        trials = make_block(self.rng)
        for i, trial_type in enumerate(trials, start=1):
            name = f"{method}_{trial_type}" if i == 1 else None
            if method == "tet":
                self.tet_trial(trial_type, "experimental", block, i, name=name)
            else:
                self.response_trial(trial_type, "experimental", method, block, i, name=name)
            if i < len(trials):
                self.between_trials(method)

    def between_trials(self, method):
        if method == "slider" and SLIDER_INPUT == "device":
            self.screen(TRIAL_END_REMINDER.format(PLACE_NEXT["high"]), key="y", name="trial_end_slider")
        else:
            self.screen(TRIAL_END, key="y", name="trial_end")

    def button_block(self, block):
        self.wait_key([self.text(BUTTON_TITLE, pos=(0, 4.8), wrap=28),
                       self.text(BUTTON_EMPHASIS, pos=(0, 1.8), height=.7, wrap=28, color=EMPHASIS_COLOR, bold=True),
                       self.text(BUTTON_FOOTER, pos=(0, -2.2), wrap=28)], name="button_instructions")
        self.wait_key([self.text(BUTTON_PRACTICE_TITLE, pos=(0, 4.6), wrap=28),
                       self.text(BUTTON_PRACTICE_EMPHASIS, pos=(0, 1.4), height=.66, wrap=28, color=EMPHASIS_COLOR, bold=True),
                       self.text(BUTTON_PRACTICE_FOOTER, pos=(0, -2.4), wrap=28)], name="button_practice_intro")
        for i in range(1, N_PRACTICE + 1):
            self.response_trial("peripheral", "practice", "button", block, i)
            if i < N_PRACTICE:
                self.screen(BUTTON_PRACTICE_NEXT, key="y", name="button_practice_next")
        self.screen(PRACTICE_END.format(READY_FIRST_TRIAL), key="y", name="button_practice_end")
        self.experimental_trials("button", block)

    def slider_demo(self):
        """Move the slider freely, seeing the response bar."""
        stim = self.text(SLIDER_DEMO[SLIDER_INPUT], pos=(0, 2.6), height=.56, wrap=25)
        self.wait_release(("space", "up", "down"))
        self.kb.clearEvents()
        self.slider.start(1.0)
        clock = core.Clock()
        last_t = 0.0
        while True:
            t = clock.getTime()
            if AUTO and t > .3:
                self.screenshot("slider_demo")
                return
            for k in self.kb.getKeys(keyList=["space", QUIT_KEY], waitRelease=False):
                if k.name == QUIT_KEY:
                    self.quit()
                return
            value = self.slider.update(t, max(t - last_t, 0.0))
            last_t = t
            stim.draw()
            self.bar.draw(value)
            self.win.flip()

    def calibration(self, block):
        """Tracking of a target of known contrast, to learn to use the slider."""
        self.slider_demo()
        self.screen(CALIBRATION_INTRO, name="calibration_intro")
        device = SLIDER_INPUT == "device"

        def position(trial_type):
            return "low" if trial_type == "calibration_up" else "high"

        for i, trial_type in enumerate(CALIBRATION_TRIALS, start=1):
            start = PLACE_SLIDER[position(trial_type)] if device else START_TRIAL
            self.screen(f"{CALIBRATION_TRIAL[trial_type]}\n\n{start}", name=f"{trial_type}_intro")
            duration = CALIBRATION_SINE_S if trial_type == "calibration_sinusoidal" else CALIBRATION_RAMP_S
            self.response_trial(trial_type, "calibration", "slider", block, i, duration=duration, name=trial_type)
            if i < len(CALIBRATION_TRIALS):
                if device:
                    self.screen(TRIAL_END_REMINDER.format(PLACE_NEXT[position(CALIBRATION_TRIALS[i])]), key="y",
                                name=f"calibration_next_{position(CALIBRATION_TRIALS[i])}")
                else:
                    self.screen(TRIAL_END, key="y")
        self.screen(CALIBRATION_END, name="calibration_end")

    def slider_block(self, block):
        self.screen(SLIDER_INTRO.format(SLIDER_HOW[SLIDER_INPUT], SLIDER_KEYS[SLIDER_INPUT]), name="slider_instructions")
        self.calibration(block)
        self.screen(PRACTICE_START.format(SLIDER_PRACTICE), name="slider_practice_intro")
        for i in range(1, N_PRACTICE + 1):
            self.response_trial("peripheral", "practice", "slider", block, i)
            if i < N_PRACTICE:
                self.between_trials("slider")
        ready = SLIDER_READY if SLIDER_INPUT == "device" else READY_FIRST_TRIAL
        self.screen(PRACTICE_END.format(ready), key="y", name="slider_practice_end")
        self.experimental_trials("slider", block)

    def tet_block(self, block):
        self.screen(TET_INTRO.format(TRIAL_S), name="tet_instructions")
        self.screen(TET_GRAPH_INTRO, name="tet_graph_intro")
        self.draw_trace(name="tet_graph")  # to try the graph: it is not saved
        self.screen(TET_GRAPH_END, name="tet_graph_end")
        self.screen(PRACTICE_START.format(TET_PRACTICE.format(TRIAL_S)), name="tet_practice_intro")
        for i in range(1, N_PRACTICE + 1):
            self.tet_trial("peripheral", "practice", block, i)
            if i < N_PRACTICE:
                self.screen(TET_PRACTICE_NEXT, key="y", name="tet_practice_next")
        self.screen(PRACTICE_END.format(TET_READY), key="y", name="tet_practice_end")
        self.screen(TET_EXPERIMENT.format(TRIAL_S), name="tet_experiment")
        self.experimental_trials("tet", block)

    def run(self):
        self.wait_release(("space", "up", "down"))
        self.screen(WELCOME, name="welcome")
        self.display_example()
        self.demo()
        blocks = {"button": self.button_block, "slider": self.slider_block, "tet": self.tet_block}
        for block, method in enumerate(self.order, start=1):
            blocks[method](block)
            if block < len(self.order):
                self.screen(BLOCK_END, key="y", name="block_end")
        self.screen(GOODBYE, name="goodbye")
        self.file.close()
        self.slider.close()
        self.win.close()
        print(f"Data saved in {self.path}")


def session_dialog():
    """Participant number (it sets the order of the blocks) and demographics in one
    form before the task. If something is missing or invalid, it asks again."""
    typed = {"participant": "", "age": ""}
    while True:
        values = {**typed, "gender": [""] + GENDERS}
        dlg = gui.DlgFromDict(values, title=DIALOG_TITLE, labels=DIALOG_LABELS, sortKeys=False,
                              order=["participant", "age", "gender"])
        if not dlg.OK:
            core.quit()
        participant, age = str(values["participant"]).strip(), str(values["age"]).strip()
        if participant.isdigit() and age.isdigit() and values["gender"] in GENDERS:
            return int(participant), {"age": int(age), "gender": values["gender"]}
        typed = {"participant": participant, "age": age}

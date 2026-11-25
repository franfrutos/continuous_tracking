"""
Settings of the task: monitor, slider, timing, design, recording and the auto
mode used for code checks.
"""

import os

# ---- Monitor ----------------------------------------------------------------
# Monitor of the lab where the task is run. Stimuli are defined in cm, so these
# values set their size on the screen
MONITOR_NAME = "mib_lab_monitor"
MONITOR_WIDTH_CM = 59.8          # visible width of the screen
MONITOR_DISTANCE_CM = 57.3       # viewing distance (1 cm = 1 degree)
MONITOR_SIZE_PX = (1920, 1080)   # resolution
FULLSCREEN = True

# ---- Slider -----------------------------------------------------------------
# A potentiometer read through a serial port: it answers the query with its level
# as a line of text. "keyboard" uses the up and down arrows instead, to try the
# task without the device (the instructions mention the keys then). If the device
# does not respond at the start of the session, the task stops with a message.
SLIDER_INPUT = "device"          # "device" or "keyboard"
SERIAL_PORT = "COM5"             # port of the device on this computer
SERIAL_BAUD = 115200
SERIAL_TIMEOUT_S = .05
SERIAL_QUERY = "R"
SERIAL_LEVELS = (0, 4095)        # levels at the two ends of the slider
KEYBOARD_RATE = .75             # change of the response per second (keyboard only)

# ---- Timing (s) -------------------------------------------------------------
TRIAL_S = 30.0                   # practice and experimental trials of all methods
DEMO_S = 15.0
CALIBRATION_RAMP_S = 5.0         # calibration_up and calibration_down trials...
CALIBRATION_HOLD_S = 2.0         # ...of which the last seconds stay at the end value
CALIBRATION_SINE_S = 30.0        # calibration_sinusoidal trials
CALIBRATION_SINE_HZ = .2

# ---- Design -----------------------------------------------------------------
# One block per method. The order is one of the six permutations of METHODS, the
# one at position participant number modulo 6
METHODS = ("button", "slider", "tet")
N_PER_TYPE = {"peripheral": 8, "near_fixation": 4}  # 12 experimental trials per block, in random order
N_PRACTICE = 5                   # practice trials before each block (peripheral)
CALIBRATION_TRIALS = ["calibration_up"] * 2 + ["calibration_down"] * 2 + ["calibration_sinusoidal"] * 2

# ---- Recording --------------------------------------------------------------
SAMPLE_HZ = 50.0                 # samples per second in the data file, for all methods
DEVICE_HZ = 50.0                 # queries to the slider per second
TET_END_TOLERANCE = .02         # the trace can end this proportion of the axis before its end

# ---- Keys -------------------------------------------------------------------
QUIT_KEY = "escape"

# ---- Auto mode (code checks: MIB_AUTO=1, optional MIB_SEED, MIB_PARTICIPANT and MIB_SLIDER) -
AUTO = os.environ.get("MIB_AUTO") == "1"
if AUTO:  # short run in a window with automatic responses
    FULLSCREEN = False
    MONITOR_SIZE_PX = (1280, 800)
    SLIDER_INPUT = os.environ.get("MIB_SLIDER", SLIDER_INPUT)  # the slider itself is simulated
    TRIAL_S = 2.0
    DEMO_S = .5
    CALIBRATION_RAMP_S = 3.0
    CALIBRATION_SINE_S = 5.0
    N_PER_TYPE = {"peripheral": 1, "near_fixation": 1}
    N_PRACTICE = 1
    CALIBRATION_TRIALS = ["calibration_up", "calibration_down", "calibration_sinusoidal"]

assert SLIDER_INPUT in ("device", "keyboard")

# ---- Paths ------------------------------------------------------------------
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # folder of main.py
DATA_DIR = os.path.join(HERE, "data")

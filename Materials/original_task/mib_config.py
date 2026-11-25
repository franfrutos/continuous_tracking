"""
Local configuration overrides for the blocked MIB task.

Edit this file to change common settings without touching the main experiment script.
Environment variables still take priority over anything defined here.
"""

# -------------------------------------------------------------------
# Run mode
# -------------------------------------------------------------------
# "full" or "test"
MIB_BLOCKED_RUN_MODE = "full"

# Optional forced block order, for example: "button,potentiometer,tet"
MIB_FORCE_BLOCK_ORDER = ""


# -------------------------------------------------------------------
# Participant defaults shown in the startup dialog
# -------------------------------------------------------------------
MIB_PARTICIPANT_ID = ""
MIB_PARTICIPANT_AGE = ""
MIB_PARTICIPANT_GENDER = "Prefiero no decir"


# -------------------------------------------------------------------
# Data output
# -------------------------------------------------------------------
# Use `None` to keep the default `data/` folder inside the project.
MIB_DATA_DIR = None


# -------------------------------------------------------------------
# Potentiometer / serial device
# -------------------------------------------------------------------
# Main on/off switch for the external device.
MIB_DEVICE_RATING = True

# Change this to the COM port used on the current computer.
# Example: "COM3", "COM5", "COM7"
MIB_DEVICE_SERIAL_PORT = "COM5"

MIB_DEVICE_SERIAL_BAUD = 115200
MIB_DEVICE_SERIAL_TIMEOUT_S = 0.05
MIB_DEVICE_QUERY_CHAR = "R"
MIB_DEVICE_LEVEL_MIN = 0
MIB_DEVICE_LEVEL_MAX = 4095
MIB_DEVICE_ALLOW_KEYBOARD_FALLBACK = True


# -------------------------------------------------------------------
# Response logging
# -------------------------------------------------------------------
MIB_RESPONSE_LOG_HZ = 50.0
MIB_DEVICE_QUERY_HZ = 50.0


# -------------------------------------------------------------------
# Display and monitor
# -------------------------------------------------------------------
MIB_MONITOR_NAME = "mib_lab_monitor"
MIB_MONITOR_WIDTH_CM = 59.8
MIB_VIEWING_DISTANCE_CM = 57.3
MIB_USE_DETECTED_FULLSCREEN_RESOLUTION = True
# Example alternative if needed:
# MIB_MONITOR_RES = "1920x1080"


# -------------------------------------------------------------------
# Experimental options
# -------------------------------------------------------------------
MIB_INCLUDE_POTENTIOMETER = True
MIB_TET_EXPERIMENTAL_DISPLAY_DURATION = 30.0
# These three values set the experimental composition in full mode.
MIB_PERIPHERAL_TRIALS_PER_BLOCK = 8
MIB_NO_TARGET_TRIALS_PER_BLOCK = 0
MIB_CONTROL_TRIALS_PER_BLOCK = 4
# Optional test-mode overrides if you ever need them:
MIB_TEST_PERIPHERAL_TRIALS_PER_BLOCK = 1
MIB_TEST_NO_TARGET_TRIALS_PER_BLOCK = 0
MIB_TEST_CONTROL_TRIALS_PER_BLOCK = 1
MIB_CONTROL_TRIAL_MODE = "near_fixation"
MIB_CONTROL_TARGET_ECC_CM = 1.0

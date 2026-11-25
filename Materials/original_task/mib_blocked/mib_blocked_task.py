# -*- coding: utf-8 -*-
"""
Blocked Motion-Induced Blindness task.

This version implements a three-method blocked protocol (button,
potentiometer/continuous, and TET) with counterbalanced block order,
method-specific practices, and pre-potentiometer calibration.
"""

import csv
from datetime import datetime
import importlib.util
import itertools
import math
import os
import random
import re
import sys
import types


def _bootstrap_windows_dll_path():
    """
    Ensure conda DLLs (including freetype) are visible on Windows before importing PsychoPy.
    """
    if os.name != "nt":
        return

    candidates = []
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        candidates.append(os.path.join(conda_prefix, "Library", "bin"))

    py_exec = os.path.abspath(sys.executable)
    env_root = os.path.dirname(py_exec)
    candidates.append(os.path.join(env_root, "Library", "bin"))

    for dll_dir in candidates:
        if not os.path.isdir(dll_dir):
            continue
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(dll_dir)
            except OSError:
                pass
        path_entries = os.environ.get("PATH", "").split(os.pathsep)
        if dll_dir not in path_entries:
            os.environ["PATH"] = dll_dir + os.pathsep + os.environ.get("PATH", "")


_bootstrap_windows_dll_path()


def _bootstrap_pyglet_compat():
    """
    PsychoPy 2022 expects pyglet.canvas (pyglet<2 API).
    If pyglet 2.x is installed, provide a minimal compatibility alias.
    """
    try:
        import pyglet  # noqa: WPS433
    except Exception:
        return

    if hasattr(pyglet, "canvas"):
        return

    try:
        import pyglet.display as _pyglet_display  # noqa: WPS433

        pyglet.canvas = _pyglet_display
    except Exception:
        pass


_bootstrap_pyglet_compat()


def _install_textbox2_import_stub():
    """
    Avoid TextBox2 font-manager initialization on import, which can hang on some Windows setups.
    This task only uses TextStim, not TextBox2.
    """
    if os.environ.get("MIB_DISABLE_TEXTBOX2_STUB", "0") == "1":
        return

    module_name = "psychopy.visual.textbox2.textbox2"
    if module_name in sys.modules:
        return

    stub = types.ModuleType(module_name)

    class _TextBox2Stub:  # pragma: no cover - defensive fallback only
        pass

    stub.TextBox2 = _TextBox2Stub
    stub.allFonts = None
    sys.modules[module_name] = stub


_install_textbox2_import_stub()

from psychopy import visual, core, event, monitors, gui
from psychopy.hardware import keyboard

import matplotlib

matplotlib.use("Agg")
import numpy as np

try:
    import serial  # pyserial
except Exception:
    serial = None

try:
    from pyglet.window import key as pyglet_key
except Exception:
    pyglet_key = None


# =========================================================
# PATHS AND SESSION
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)


def load_project_config():
    config_path = os.path.join(PROJECT_ROOT, "mib_config.py")
    if not os.path.exists(config_path):
        return {}
    spec = importlib.util.spec_from_file_location("mib_config", config_path)
    if spec is None or spec.loader is None:
        return {}
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {
        name: getattr(module, name)
        for name in dir(module)
        if name.startswith("MIB_")
    }


PROJECT_CONFIG = load_project_config()
DEFAULT_DATA_DIR = os.path.join(PROJECT_ROOT, "data")
if "MIB_DATA_DIR" in os.environ:
    DATA_DIR = os.environ.get("MIB_DATA_DIR", DEFAULT_DATA_DIR)
else:
    config_data_dir = PROJECT_CONFIG.get("MIB_DATA_DIR")
    if config_data_dir in (None, ""):
        DATA_DIR = DEFAULT_DATA_DIR
    else:
        DATA_DIR = str(config_data_dir)
if not os.path.isabs(DATA_DIR):
    DATA_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, DATA_DIR))
os.makedirs(DATA_DIR, exist_ok=True)

SESSION_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
COUNTERBALANCE_FILE = os.path.join(DATA_DIR, "counterbalance_assignments.csv")
PARTICIPANT_DATA_DIR = ""
SESSION_SUMMARY_FILE = ""
TRIAL_SUMMARY_FILE = ""
BUTTON_EVENTS_FILE = ""
CONTINUOUS_FILE = ""
TET_FILE = ""


def configure_output_files(participant_id):
    global PARTICIPANT_DATA_DIR
    global SESSION_SUMMARY_FILE
    global TRIAL_SUMMARY_FILE
    global BUTTON_EVENTS_FILE
    global CONTINUOUS_FILE
    global TET_FILE

    PARTICIPANT_DATA_DIR = os.path.join(DATA_DIR, f"participant_{participant_id}")
    os.makedirs(PARTICIPANT_DATA_DIR, exist_ok=True)
    SESSION_SUMMARY_FILE = os.path.join(
        PARTICIPANT_DATA_DIR, f"session_summary_p{participant_id}.csv"
    )
    TRIAL_SUMMARY_FILE = os.path.join(
        PARTICIPANT_DATA_DIR, f"trial_summary_p{participant_id}.csv"
    )
    BUTTON_EVENTS_FILE = os.path.join(
        PARTICIPANT_DATA_DIR, f"button_events_p{participant_id}.csv"
    )
    CONTINUOUS_FILE = os.path.join(
        PARTICIPANT_DATA_DIR, f"continuous_responses_p{participant_id}.csv"
    )
    TET_FILE = os.path.join(PARTICIPANT_DATA_DIR, f"tet_traces_p{participant_id}.csv")

COUNTERBALANCE_FIELDNAMES = [
    "session_id",
    "participant_id",
    "participant_age",
    "participant_gender",
    "assigned_at",
    "assigned_order",
]
TRIAL_SUMMARY_FIELDNAMES = [
    "session_id",
    "participant_id",
    "phase",
    "block_index",
    "block_type",
    "trial_global_index",
    "trial_in_block",
    "trial_type",
    "control_trial",
    "target_kind",
    "target_position_x_cm",
    "target_position_y_cm",
    "target_contrast_mode",
    "response_mode",
    "duration_s",
    "button_press_count",
    "button_press_times_s",
    "n_response_samples",
    "mean_response_value",
    "min_response_value",
    "max_response_value",
    "final_response_value",
    "button_state_proportion",
    "mean_visibility",
    "min_visibility",
    "max_visibility",
    "final_visibility",
]
BUTTON_FIELDNAMES = [
    "session_id",
    "participant_id",
    "block_index",
    "block_type",
    "trial_global_index",
    "trial_in_block",
    "trial_type",
    "event_index",
    "event_time_s",
]
CONTINUOUS_FIELDNAMES = [
    "session_id",
    "participant_id",
    "phase",
    "block_index",
    "block_type",
    "trial_global_index",
    "trial_in_block",
    "trial_type",
    "response_mode",
    "is_calibration",
    "time_s",
    "target_contrast",
    "target_contrast_true",
    "response_value",
]
TET_FIELDNAMES = [
    "session_id",
    "participant_id",
    "tet_phase",
    "trial_index",
    "phase",
    "block_index",
    "block_type",
    "trial_global_index",
    "trial_in_block",
    "trial_type",
    "response_mode",
    "display_duration_s",
    "attempt_index",
    "point_index",
    "x_cm",
    "y_cm",
    "normalized_time",
    "normalized_visibility",
]


# =========================================================
# CONFIG HELPERS
# =========================================================
def get_config_value(name, default=None):
    if name in os.environ:
        return os.environ.get(name)
    config_value = PROJECT_CONFIG.get(name)
    if config_value is None:
        return default
    return config_value


def env_flag(name, default=False):
    raw = get_config_value(name, "1" if default else "0")
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in ("0", "false", "no", "off")


def env_float(name, default):
    raw = get_config_value(name)
    if raw is None or str(raw).strip() == "":
        return float(default)
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid float for {name}: {raw}") from exc


def env_int(name, default):
    raw = get_config_value(name)
    if raw is None or str(raw).strip() == "":
        return int(default)
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid integer for {name}: {raw}") from exc


def env_resolution(name, default):
    raw = get_config_value(name)
    if raw is None or str(raw).strip() == "":
        return tuple(default)
    cleaned = str(raw).lower().replace(" ", "")
    if "x" in cleaned:
        width_str, height_str = cleaned.split("x", 1)
    elif "," in cleaned:
        width_str, height_str = cleaned.split(",", 1)
    else:
        raise ValueError(f"Invalid resolution format for {name}: {raw}")
    return (int(width_str), int(height_str))


def detect_primary_screen_resolution(default):
    try:
        import pyglet  # noqa: WPS433

        if not hasattr(pyglet, "canvas"):
            return tuple(default)
        display = pyglet.canvas.get_display()
        screen = display.get_default_screen()
        return (int(screen.width), int(screen.height))
    except Exception:
        return tuple(default)


def show_input_error_dialog(message):
    dlg = gui.Dlg(title="Error de entrada")
    dlg.addText(message)
    dlg.show()


def collect_participant_info():
    default_id = str(get_config_value("MIB_PARTICIPANT_ID", "1001" if TEST_MODE else ""))
    default_age = str(get_config_value("MIB_PARTICIPANT_AGE", ""))
    default_gender = str(get_config_value("MIB_PARTICIPANT_GENDER", "Prefiero no decir"))
    gender_options = [
        "Mujer",
        "Hombre",
        "No binario",
        "Prefiero no decir",
        "Otro",
    ]
    if default_gender not in gender_options:
        default_gender = "Prefiero no decir"

    while True:
        dialog = gui.Dlg(title="Datos de participante")
        dialog.addText("Introduce los datos antes de empezar.")
        dialog.addField("ID participante (ej. 1001):", default_id)
        dialog.addField("Edad:", default_age)
        dialog.addField("Genero:", choices=gender_options, initial=default_gender)
        response = dialog.show()
        if not dialog.OK:
            raise SystemExit("Sesion cancelada por el usuario.")

        participant_id_raw = str(response[0]).strip()
        participant_age_raw = str(response[1]).strip()
        participant_gender = str(response[2]).strip()

        if not participant_id_raw.isdigit():
            show_input_error_dialog(
                "El ID de participante debe ser numerico (por ejemplo, 1001)."
            )
            default_id = participant_id_raw
            default_age = participant_age_raw
            default_gender = participant_gender
            continue

        if participant_age_raw == "" or (not participant_age_raw.isdigit()):
            show_input_error_dialog("La edad debe ser un numero entero.")
            default_id = participant_id_raw
            default_age = participant_age_raw
            default_gender = participant_gender
            continue

        return participant_id_raw, int(participant_age_raw), participant_gender


def validate_block_sequence(block_sequence, expected_blocks):
    if len(block_sequence) != len(expected_blocks):
        raise ValueError(
            f"Invalid block order: expected {len(expected_blocks)} blocks, got {len(block_sequence)}."
        )
    if len(set(block_sequence)) != len(block_sequence):
        raise ValueError("Invalid block order: duplicated blocks are not allowed.")
    if set(block_sequence) != set(expected_blocks):
        raise ValueError(
            f"Invalid block order: expected blocks {expected_blocks}, got {block_sequence}."
        )


def assigned_order_from_participant_id(participant_id, available_blocks):
    block_permutations = list(itertools.permutations(available_blocks))
    if not block_permutations:
        raise ValueError("No available blocks to counterbalance.")
    participant_number = int(participant_id)
    permutation_index = participant_number % len(block_permutations)
    return list(block_permutations[permutation_index])


def assigned_order_to_label(block_sequence):
    return "__".join(block_sequence)


def resolve_block_sequence(participant_id):
    if INCLUDE_POTENTIOMETER_BLOCK:
        expected_blocks = list(EXPERIMENTAL_BLOCKS_ALL)
    else:
        expected_blocks = ["button", "tet"]

    if FORCE_BLOCK_ORDER_RAW:
        forced_sequence = [
            block.strip().lower()
            for block in FORCE_BLOCK_ORDER_RAW.split(",")
            if block.strip()
        ]
        validate_block_sequence(forced_sequence, expected_blocks)
        return forced_sequence

    assigned_sequence = assigned_order_from_participant_id(
        participant_id=participant_id,
        available_blocks=expected_blocks,
    )
    validate_block_sequence(assigned_sequence, expected_blocks)
    return assigned_sequence


# =========================================================
# SETUP
# =========================================================
RUN_MODE = str(get_config_value("MIB_BLOCKED_RUN_MODE", "full")).strip().lower()
TEST_MODE = RUN_MODE == "test"
INCLUDE_POTENTIOMETER_BLOCK = (
    str(get_config_value("MIB_INCLUDE_POTENTIOMETER", "1")).strip().lower()
    not in ("0", "false", "no", "off")
)
FORCE_BLOCK_ORDER_RAW = str(get_config_value("MIB_FORCE_BLOCK_ORDER", "")).strip()
FULLSCR = True

MONITOR_NAME = str(get_config_value("MIB_MONITOR_NAME", "mib_lab_monitor"))
DEFAULT_MONITOR_WIDTH_CM = 53.0
DEFAULT_MONITOR_RES = (1920, 1080)
DEFAULT_VIEWING_DISTANCE_CM = 57.3
USE_DETECTED_FULLSCREEN_RESOLUTION = env_flag(
    "MIB_USE_DETECTED_FULLSCREEN_RESOLUTION",
    True,
)
MONITOR_WIDTH_CM_FROM_ENV = "MIB_MONITOR_WIDTH_CM" in os.environ
MONITOR_RES_FROM_ENV = "MIB_MONITOR_RES" in os.environ

MONITOR_WIDTH_CM = env_float("MIB_MONITOR_WIDTH_CM", DEFAULT_MONITOR_WIDTH_CM)
VIEWING_DISTANCE_CM = env_float("MIB_VIEWING_DISTANCE_CM", DEFAULT_VIEWING_DISTANCE_CM)
if USE_DETECTED_FULLSCREEN_RESOLUTION and FULLSCR:
    MONITOR_RES = detect_primary_screen_resolution(DEFAULT_MONITOR_RES)
else:
    MONITOR_RES = env_resolution("MIB_MONITOR_RES", DEFAULT_MONITOR_RES)

# Optional hardware potentiometer (serial protocol).
DEVICE_RATING = env_flag("MIB_DEVICE_RATING", True)
DEVICE_SERIAL_PORT = str(get_config_value("MIB_DEVICE_SERIAL_PORT", "COM5"))
DEVICE_SERIAL_BAUD = env_int("MIB_DEVICE_SERIAL_BAUD", 115200)
DEVICE_SERIAL_TIMEOUT_S = env_float("MIB_DEVICE_SERIAL_TIMEOUT_S", 0.05)
DEVICE_QUERY_CHAR = str(get_config_value("MIB_DEVICE_QUERY_CHAR", "R"))[:1] or "R"
DEVICE_LEVEL_MIN = env_int("MIB_DEVICE_LEVEL_MIN", 0)
DEVICE_LEVEL_MAX = env_int("MIB_DEVICE_LEVEL_MAX", 4095)
DEVICE_ALLOW_KEYBOARD_FALLBACK = env_flag("MIB_DEVICE_ALLOW_KEYBOARD_FALLBACK", True)
if DEVICE_LEVEL_MAX <= DEVICE_LEVEL_MIN:
    raise ValueError("DEVICE_LEVEL_MAX must be larger than DEVICE_LEVEL_MIN.")
# Fixed-interval logging/query to keep row counts comparable across methods.
RESPONSE_LOG_HZ = env_float("MIB_RESPONSE_LOG_HZ", 50.0)
if RESPONSE_LOG_HZ <= 0.0:
    raise ValueError("MIB_RESPONSE_LOG_HZ must be > 0.")
RESPONSE_LOG_INTERVAL_S = 1.0 / RESPONSE_LOG_HZ
DEVICE_QUERY_HZ = env_float("MIB_DEVICE_QUERY_HZ", 50.0)
if DEVICE_QUERY_HZ <= 0.0:
    raise ValueError("MIB_DEVICE_QUERY_HZ must be > 0.")
DEVICE_QUERY_INTERVAL_S = 1.0 / DEVICE_QUERY_HZ

# Test mode keeps the full flow but uses fewer trials.
TRIAL_DURATION = 30.0
DEMO_DURATION = 15.0
PRACTICE_TRIAL_DURATION = 30.0
PRACTICE_TRIALS_PER_BLOCK = 1 if TEST_MODE else 5
TET_PRACTICE_TRIAL_DURATION = 30.0
TET_EXPERIMENTAL_DISPLAY_DURATION = env_float(
    "MIB_TET_EXPERIMENTAL_DISPLAY_DURATION",
    30.0,
)
TET_COMPLETION_TOLERANCE = 0.02
# First two calibration trials (up/down) duration.
CALIBRATION_DURATION = 5.0
SINUSOIDAL_CALIBRATION_DURATION = 30.0
CALIBRATION_ENDPOINT_HOLD_S = 2.0
SINUSOIDAL_CALIBRATION_HZ = 0.2

FPS_WARNING_THRESHOLD_HZ = 3.0
POTENTIOMETER_RATE_PER_SEC = 0.75
# Visibility bar for continuous response can be configured separately.
SHOW_POTENTIOMETER_BAR_IN_CALIBRATION = True
SHOW_POTENTIOMETER_BAR_IN_EXPERIMENTAL_BLOCK = False
# Legacy compatibility flag retained in the session summary. Trial wait screens
# are now always shown after practice and experimental trials.
SHOW_INTERTRIAL_BREAK_SCREEN = False

DEFAULT_BLOCK_SIZE = 3 if TEST_MODE else 20
DEFAULT_NO_TARGET_TRIALS_PER_BLOCK = 1 if TEST_MODE else 4
DEFAULT_CONTROL_TRIALS_PER_BLOCK = 1 if TEST_MODE else 4
DEFAULT_PERIPHERAL_TRIALS_PER_BLOCK = (
    DEFAULT_BLOCK_SIZE
    - DEFAULT_NO_TARGET_TRIALS_PER_BLOCK
    - DEFAULT_CONTROL_TRIALS_PER_BLOCK
)
PERIPHERAL_TRIAL_COUNT_ENV = (
    "MIB_TEST_PERIPHERAL_TRIALS_PER_BLOCK"
    if TEST_MODE
    else "MIB_PERIPHERAL_TRIALS_PER_BLOCK"
)
NO_TARGET_TRIAL_COUNT_ENV = (
    "MIB_TEST_NO_TARGET_TRIALS_PER_BLOCK"
    if TEST_MODE
    else "MIB_NO_TARGET_TRIALS_PER_BLOCK"
)
CONTROL_TRIAL_COUNT_ENV = (
    "MIB_TEST_CONTROL_TRIALS_PER_BLOCK"
    if TEST_MODE
    else "MIB_CONTROL_TRIALS_PER_BLOCK"
)
PERIPHERAL_TRIALS_PER_BLOCK = env_int(
    PERIPHERAL_TRIAL_COUNT_ENV,
    DEFAULT_PERIPHERAL_TRIALS_PER_BLOCK,
)
NO_TARGET_TRIALS_PER_BLOCK = env_int(
    NO_TARGET_TRIAL_COUNT_ENV,
    DEFAULT_NO_TARGET_TRIALS_PER_BLOCK,
)
STATIC_MASK_TRIALS_PER_BLOCK = env_int(
    CONTROL_TRIAL_COUNT_ENV,
    DEFAULT_CONTROL_TRIALS_PER_BLOCK,
)
BLOCK_SIZE = (
    PERIPHERAL_TRIALS_PER_BLOCK
    + NO_TARGET_TRIALS_PER_BLOCK
    + STATIC_MASK_TRIALS_PER_BLOCK
)
INCLUDE_NO_TARGET_TRIALS = NO_TARGET_TRIALS_PER_BLOCK > 0
if min(
    PERIPHERAL_TRIALS_PER_BLOCK,
    NO_TARGET_TRIALS_PER_BLOCK,
    STATIC_MASK_TRIALS_PER_BLOCK,
) < 0:
    raise ValueError("Trial counts per block cannot be negative.")
if BLOCK_SIZE <= 0:
    raise ValueError("Experimental block size must be greater than zero.")
CONTROL_TRIAL_MODE = str(
    get_config_value("MIB_CONTROL_TRIAL_MODE", "near_fixation")
).strip().lower()
CONTROL_TARGET_ECC_CM = env_float("MIB_CONTROL_TARGET_ECC_CM", 1.0)
if CONTROL_TRIAL_MODE not in ("static_mask", "near_fixation"):
    raise ValueError(
        "MIB_CONTROL_TRIAL_MODE must be 'static_mask' or 'near_fixation'."
    )
CONTROL_TRIAL_TYPE = CONTROL_TRIAL_MODE

EXPERIMENTAL_BLOCKS_ALL = ["button", "potentiometer", "tet"]


# =========================================================
# DISPLAY PARAMETERS
# =========================================================
FIX_DIAM_CM = 0.27

TARGET_SIGMA_CM = 0.30
TARGET_SIZE_CM = TARGET_SIGMA_CM * 6.0
TARGET_ECC_CM = 5.45
TARGET_ANGLE_DEG = 135.0
CROSS_WIDTH_CM = 0.80
CROSS_ARM_RATIO = 0.10
CROSS_SPACING_CM = CROSS_WIDTH_CM * 1.5
PROTECTION_DIAM_CM = 1.80
PROTECTION_RADIUS_CM = PROTECTION_DIAM_CM / 2.0

ROT_CYCLES_PER_SEC = 0.37
ROT_DEG_PER_SEC = 360.0 * ROT_CYCLES_PER_SEC

GRID_N = 11


# =========================================================
# COLORS
# =========================================================
BG_COLOR = [0.0, 0.0, 0.0]
FIX_COLOR = [-1.0, -1.0, -1.0]
TARGET_COLOR = [1.0, 1.0, 1.0]
CROSS_COLOR = [-0.18, -0.18, -0.18]
TEXT_COLOR = [-1.0, -1.0, -1.0]
TRACE_COLOR = [0.8, -0.4, -0.4]
EMPHASIS_TEXT_COLOR = [1.0, 0.8, -0.2]
BAR_FRAME_COLOR = [-0.7, -0.7, -0.7]
BAR_FILL_COLOR = [0.6, 0.6, 0.6]


# =========================================================
# UTILITIES
# =========================================================
def pol2cart(r, theta_deg):
    theta = math.radians(theta_deg)
    return np.array([r * math.cos(theta), r * math.sin(theta)])


def rotate_xy(xy, angle_deg):
    theta = math.radians(angle_deg)
    c, s = math.cos(theta), math.sin(theta)
    rot = np.array([[c, -s], [s, c]])
    return rot @ np.asarray(xy)


def cross_vertices(width, arm_ratio=0.28):
    w = width / 2.0
    t = width * arm_ratio / 2.0
    return np.array(
        [
            [-t, w],
            [t, w],
            [t, t],
            [w, t],
            [w, -t],
            [t, -t],
            [t, -w],
            [-t, -w],
            [-t, -t],
            [-w, -t],
            [-w, t],
            [-t, t],
        ]
    )


def circle_vertices(radius, n_vertices=64):
    angles = np.linspace(0.0, 2.0 * math.pi, n_vertices, endpoint=False)
    return np.column_stack((radius * np.cos(angles), radius * np.sin(angles)))


def rect_vertices(width, height):
    half_w = width / 2.0
    half_h = height / 2.0
    return np.array(
        [
            [-half_w, half_h],
            [half_w, half_h],
            [half_w, -half_h],
            [-half_w, -half_h],
        ]
    )


def make_grid_positions(n, spacing):
    coords = (np.arange(n) - (n - 1) / 2.0) * spacing
    return np.array([(x, y) for y in coords for x in coords])


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def normalize_device_level(level):
    clamped = clamp(level, DEVICE_LEVEL_MIN, DEVICE_LEVEL_MAX)
    level_span = DEVICE_LEVEL_MAX - DEVICE_LEVEL_MIN
    return (clamped - DEVICE_LEVEL_MIN) / level_span


class SerialRatingDevice:
    def __init__(self):
        self.enabled = DEVICE_RATING
        self.port = DEVICE_SERIAL_PORT
        self.baudrate = DEVICE_SERIAL_BAUD
        self.timeout_s = DEVICE_SERIAL_TIMEOUT_S
        self.query_char = DEVICE_QUERY_CHAR
        self.status = "disabled"
        self.error = ""
        self.connected = False
        self.last_raw_level = None
        self.last_normalized_value = 0.5
        self._serial = None
        if self.enabled:
            self._connect()

    def _connect(self):
        if serial is None:
            self.status = "pyserial_missing"
            self.error = "pyserial is not available."
            return
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout_s,
            )
            self.connected = True
            self.status = "connected"
        except Exception as exc:
            self.status = "connection_error"
            self.error = str(exc)
            self.connected = False
            self._serial = None

    def _parse_level_line(self, raw_line):
        if raw_line is None:
            return None
        if isinstance(raw_line, bytes):
            line = raw_line.decode("ascii", errors="ignore").strip()
        else:
            line = str(raw_line).strip()
        if line == "":
            return None
        try:
            return int(line)
        except ValueError:
            match = re.search(r"-?\d+", line)
            if match is None:
                return None
            try:
                return int(match.group(0))
            except ValueError:
                return None

    def read_normalized_value(self, fallback_value):
        if not self.connected or self._serial is None:
            return fallback_value
        latest_value = fallback_value
        try:
            query_bytes = self.query_char.encode("ascii", errors="ignore")
            if len(query_bytes) == 0:
                query_bytes = b"R"
            self._serial.write(query_bytes)
            self._serial.flush()

            parsed = self._parse_level_line(self._serial.readline())
            if parsed is not None:
                self.last_raw_level = int(
                    clamp(parsed, DEVICE_LEVEL_MIN, DEVICE_LEVEL_MAX)
                )
                latest_value = normalize_device_level(self.last_raw_level)
            self.last_normalized_value = latest_value
            return latest_value
        except Exception as exc:
            self.status = "read_error"
            self.error = str(exc)
            self.connected = False
            return fallback_value

    def close(self):
        if self._serial is None:
            return
        try:
            self._serial.close()
        except Exception:
            pass
        self._serial = None
        self.connected = False
        if self.status == "connected":
            self.status = "closed"


def close_rating_device():
    device = globals().get("rating_device")
    if device is None:
        return
    try:
        device.close()
    except Exception:
        pass


def write_csv_rows(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_csv_rows(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def append_csv_row(path, fieldnames, row):
    file_exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def append_csv_rows(path, fieldnames, rows):
    if not rows:
        return
    file_exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def persist_trial_outputs(trial_summary, button_rows, continuous_rows):
    append_csv_row(TRIAL_SUMMARY_FILE, TRIAL_SUMMARY_FIELDNAMES, trial_summary)
    append_csv_rows(BUTTON_EVENTS_FILE, BUTTON_FIELDNAMES, button_rows)
    append_csv_rows(CONTINUOUS_FILE, CONTINUOUS_FIELDNAMES, continuous_rows)


def persist_tet_rows(rows):
    append_csv_rows(TET_FILE, TET_FIELDNAMES, rows)


def make_key_state_handler(win):
    if pyglet_key is None or not hasattr(win, "winHandle"):
        return None
    try:
        handler = pyglet_key.KeyStateHandler()
        win.winHandle.push_handlers(handler)
        return handler
    except Exception:
        return None


def key_is_down(handler, key_name):
    if handler is None or pyglet_key is None:
        return False
    key_map = {
        "space": pyglet_key.SPACE,
        "escape": pyglet_key.ESCAPE,
        "up": pyglet_key.UP,
        "down": pyglet_key.DOWN,
        "y": pyglet_key.Y,
        "n": pyglet_key.N,
        "r": pyglet_key.R,
        "return": pyglet_key.RETURN,
    }
    key_code = key_map.get(key_name)
    if key_code is None:
        return False
    return bool(handler[key_code])


def any_key_down(handler, key_names):
    return any(key_is_down(handler, key_name) for key_name in key_names)


def ensure_not_pressed(handler, key_names):
    while any_key_down(handler, key_names):
        if key_is_down(handler, "escape"):
            terminate_experiment()
        core.wait(0.01)


def terminate_experiment():
    close_rating_device()
    win_obj = globals().get("win")
    if win_obj is not None:
        try:
            win_obj.close()
        except Exception:
            pass
    core.quit()


def wait_for_choice_screen(text, choices):
    event.clearEvents()
    response_keyboard.clearEvents()
    ensure_not_pressed(key_state_handler, list(choices.keys()))
    while True:
        if key_is_down(key_state_handler, "escape"):
            terminate_experiment()
        text_stim.text = text
        text_stim.draw()
        win.flip()
        keys = event.waitKeys(keyList=list(choices.keys()) + ["escape"])
        if "escape" in keys:
            terminate_experiment()
        for key in keys:
            if key in choices:
                return choices[key]


def show_message_and_wait(text, key_list=None):
    if key_list is None:
        key_list = ["space"]
    event.clearEvents()
    response_keyboard.clearEvents()
    ensure_not_pressed(key_state_handler, key_list)
    while True:
        if key_is_down(key_state_handler, "escape"):
            terminate_experiment()
        text_stim.text = text
        text_stim.draw()
        win.flip()
        keys = event.waitKeys(keyList=key_list + ["escape"])
        if "escape" in keys:
            terminate_experiment()
        if any(key in key_list for key in keys):
            return


def show_trial_wait_screen():
    show_message_and_wait(
        "Has terminado este ensayo.\n\nPulsa Y para continuar.",
        key_list=["y"],
    )


def show_potentiometer_wait_screen(reminder_text):
    show_message_and_wait(
        "Has terminado este ensayo.\n\n"
        f"{reminder_text}\n\n"
        "Pulsa Y para continuar.",
        key_list=["y"],
    )


def show_practice_complete_screen(final_prompt):
    show_message_and_wait(
        "Has terminado la práctica.\n\n"
        "A continuación empezará el bloque experimental.\n\n"
        f"{final_prompt}",
        key_list=["y"],
    )


def show_practice_intro_screen(text):
    show_message_and_wait(
        f"{text}\n\nPulsa ESPACIO para empezar la práctica.",
        key_list=["space"],
    )


def show_calibration_intro_screen():
    show_message_and_wait(
        "Ahora vamos a realizar unos ensayos de calibración para que aprendas a usar el potenciómetro.\n"
        "Durante estos ensayos tendrás que ajustar la respuesta para seguir los cambios de visibilidad del punto.\n"
        "Mantén la mirada en el centro en todo momento.\n\n"
        "Pulsa ESPACIO para continuar.",
        key_list=["space"],
    )


def show_potentiometer_device_demo():
    if DEVICE_RATING:
        body_text = (
            "Antes de empezar, prueba a mover el potenciómetro para ver cómo funciona.\n\n"
            "A medida que lo muevas, verás cambiar el indicador de la derecha.\n\n"
            "Pulsa ESPACIO para continuar."
        )
    else:
        body_text = (
            "Antes de empezar, prueba a mover la respuesta para ver cómo funciona.\n\n"
            "Usa las teclas UP y DOWN para cambiar el indicador de la derecha.\n\n"
            "Pulsa ESPACIO para continuar."
        )

    demo_text = visual.TextStim(
        win=win,
        text=body_text,
        pos=(0.0, 2.6),
        height=0.56,
        color=TEXT_COLOR,
        colorSpace="rgb",
        units="cm",
        wrapWidth=25,
        alignText="center",
    )

    event.clearEvents()
    response_keyboard.clearEvents()
    ensure_not_pressed(key_state_handler, ["space", "up", "down"])

    response_value = 1.0
    demo_clock = core.Clock()
    next_device_query_t = 0.0
    last_t = 0.0

    while True:
        if key_is_down(key_state_handler, "escape"):
            terminate_experiment()

        keys = event.getKeys(keyList=["space", "escape"])
        if "escape" in keys:
            terminate_experiment()
        if "space" in keys:
            return

        t = demo_clock.getTime()
        dt = max(t - last_t, 0.0)
        last_t = t

        if DEVICE_RATING and rating_device.connected:
            if t >= next_device_query_t:
                response_value = rating_device.read_normalized_value(response_value)
                while next_device_query_t <= t:
                    next_device_query_t += DEVICE_QUERY_INTERVAL_S
        else:
            delta = 0.0
            if key_is_down(key_state_handler, "up"):
                delta += POTENTIOMETER_RATE_PER_SEC * dt
            if key_is_down(key_state_handler, "down"):
                delta -= POTENTIOMETER_RATE_PER_SEC * dt
            response_value = clamp(response_value + delta, 0.0, 1.0)

        demo_text.draw()
        draw_response_bar(response_value)
        win.flip()


def show_demo_complete_screen():
    show_message_and_wait(
        "Has terminado la demostración.\n\n"
        "Pulsa Y para continuar.",
        key_list=["y"],
    )


def show_block_complete_screen():
    show_message_and_wait(
        "Has terminado esta parte de la tarea.\n\n"
        "Por favor, avisa al experimentador.\n\n"
        "Pulsa Y cuando te indiquen que puedes continuar.",
        key_list=["y"],
    )


def show_button_block_instruction_screen():
    title = visual.TextStim(
        win=win,
        text=(
            "En esta parte de la tarea, debes indicar si percibes o no el punto blanco.\n"
            "Mantén la mirada en el punto central durante todos los ensayos."
        ),
        pos=(0.0, 4.8),
        height=0.58,
        color=TEXT_COLOR,
        colorSpace="rgb",
        units="cm",
        wrapWidth=28,
        alignText="center",
    )
    emphasis = visual.TextStim(
        win=win,
        text="Pulsa y mantén ESPACIO mientras NO PERCIBAS EL PUNTO BLANCO.",
        pos=(0.0, 1.8),
        height=0.7,
        bold=True,
        color=EMPHASIS_TEXT_COLOR,
        colorSpace="rgb",
        units="cm",
        wrapWidth=28,
        alignText="center",
    )
    footer = visual.TextStim(
        win=win,
        text=(
            f"Suelta ESPACIO cuando vuelva a ser visible.\n"
            "Pulsa ESPACIO para continuar."
        ),
        pos=(0.0, -2.2),
        height=0.58,
        color=TEXT_COLOR,
        colorSpace="rgb",
        units="cm",
        wrapWidth=28,
        alignText="center",
    )
    event.clearEvents()
    ensure_not_pressed(key_state_handler, ["space"])
    while True:
        if key_is_down(key_state_handler, "escape"):
            terminate_experiment()
        keys = event.getKeys(keyList=["space", "escape"])
        if "escape" in keys:
            terminate_experiment()
        if "space" in keys:
            return
        title.draw()
        emphasis.draw()
        footer.draw()
        win.flip()


def show_button_practice_intro_screen():
    title = visual.TextStim(
        win=win,
        text=(
            "Primero vamos a realizar unos ensayos de práctica.\n"
            "Mantén la mirada en el punto central en todo momento."
        ),
        pos=(0.0, 4.6),
        height=0.58,
        color=TEXT_COLOR,
        colorSpace="rgb",
        units="cm",
        wrapWidth=28,
        alignText="center",
    )
    emphasis = visual.TextStim(
        win=win,
        text=(
            "Recuerda: mantén pulsada la tecla ESPACIO\n"
            "mientras no percibas el estímulo blanco."
        ),
        pos=(0.0, 1.4),
        height=0.66,
        bold=True,
        color=EMPHASIS_TEXT_COLOR,
        colorSpace="rgb",
        units="cm",
        wrapWidth=28,
        alignText="center",
    )
    footer = visual.TextStim(
        win=win,
        text=(
            "Suelta ESPACIO cuando el estímulo vuelva a ser visible.\n\n"
            "Pulsa ESPACIO para empezar la práctica."
        ),
        pos=(0.0, -2.4),
        height=0.58,
        color=TEXT_COLOR,
        colorSpace="rgb",
        units="cm",
        wrapWidth=28,
        alignText="center",
    )
    event.clearEvents()
    ensure_not_pressed(key_state_handler, ["space"])
    while True:
        if key_is_down(key_state_handler, "escape"):
            terminate_experiment()
        keys = event.getKeys(keyList=["space", "escape"])
        if "escape" in keys:
            terminate_experiment()
        if "space" in keys:
            return
        title.draw()
        emphasis.draw()
        footer.draw()
        win.flip()


def show_potentiometer_trial_start_screen(base_text, start_position="high"):
    if DEVICE_RATING:
        if start_position == "low":
            position_text = (
                "Antes de empezar, coloca el potenciómetro en la posición más baja.\n"
                "Cuando lo tengas abajo del todo, pulsa ESPACIO para empezar."
            )
        else:
            position_text = (
                "Antes de empezar, coloca el potenciómetro en la posición más alta.\n"
                "Cuando lo tengas arriba del todo, pulsa ESPACIO para empezar."
            )
        message = (
            f"{base_text}\n\n"
            f"{position_text}"
        )
    else:
        message = f"{base_text}\n\nPulsa ESPACIO para empezar."
    show_message_and_wait(message)


def practice_instruction_count_text():
    return (
        "un ensayo de práctica"
        if PRACTICE_TRIALS_PER_BLOCK == 1
        else "varios ensayos de práctica"
    )


def prompt_for_understanding(text):
    while True:
        answer = wait_for_choice_screen(
            text
            + "\n\nPulsa Y si lo has entendido. Pulsa N para volver a leerlo.",
            {"y": True, "n": False},
        )
        if answer:
            return


def compute_contrast(trial_spec, t):
    if trial_spec["target_contrast_mode"] == "constant":
        return trial_spec["target_contrast_value"]
    if trial_spec["target_contrast_mode"] == "ramp_up":
        ramp_duration_s = max(
            trial_spec["duration_s"] - CALIBRATION_ENDPOINT_HOLD_S,
            0.001,
        )
        if t >= ramp_duration_s:
            return 1.0
        return clamp(t / ramp_duration_s, 0.0, 1.0)
    if trial_spec["target_contrast_mode"] == "ramp_down":
        ramp_duration_s = max(
            trial_spec["duration_s"] - CALIBRATION_ENDPOINT_HOLD_S,
            0.001,
        )
        if t >= ramp_duration_s:
            return 0.0
        return clamp(1.0 - (t / ramp_duration_s), 0.0, 1.0)
    if trial_spec["target_contrast_mode"] == "sinusoidal":
        return 0.5 + 0.5 * math.cos(2.0 * math.pi * SINUSOIDAL_CALIBRATION_HZ * t)
    return 0.0


def get_protected_positions(trial_spec):
    protected_positions = [np.array([0.0, 0.0])]
    if trial_spec["target_kind"] != "none":
        protected_positions.append(np.asarray(trial_spec["target_pos_cm"]))
    return protected_positions


def cross_is_outside_clearance(cross_pos, protected_positions, clearance_cm):
    for protected_pos in protected_positions:
        if np.linalg.norm(cross_pos - protected_pos) < clearance_cm:
            return False
    return True


def draw_response_bar(response_value):
    bar_height = 8.0
    fill_height = max(0.04, bar_height * response_value)
    response_bar_fill.vertices = rect_vertices(0.6, fill_height)
    response_bar_fill.pos = (
        18.5,
        0.0 - (bar_height / 2.0) + (fill_height / 2.0),
    )
    response_bar_frame.draw()
    response_bar_fill.draw()
    response_bar_label.draw()
    response_bar_top_label.draw()
    response_bar_bottom_label.draw()


def should_draw_potentiometer_bar(trial_spec):
    if trial_spec["response_mode"] != "continuous":
        return False
    if trial_spec["phase"] == "calibration":
        return SHOW_POTENTIOMETER_BAR_IN_CALIBRATION
    if trial_spec["block_type"] == "potentiometer":
        return SHOW_POTENTIOMETER_BAR_IN_EXPERIMENTAL_BLOCK
    return SHOW_POTENTIOMETER_BAR_IN_EXPERIMENTAL_BLOCK


def draw_trial_scene(trial_spec, t, response_value=None):
    angle = 0.0 if trial_spec["mask_motion"] == "static" else (ROT_DEG_PER_SEC * t) % 360.0
    if trial_spec["phase"] != "calibration":
        protected_positions = get_protected_positions(trial_spec)
        for stim, base_pos in zip(crosses, base_positions):
            rot_pos = rotate_xy(base_pos, angle)
            if cross_is_outside_clearance(rot_pos, protected_positions, clearance_cm):
                stim.pos = rot_pos
                stim.ori = angle
                stim.draw()

    target_contrast = compute_contrast(trial_spec, t)
    draw_fixation = trial_spec["target_kind"] != "fixation_calibration"
    if draw_fixation:
        fix.draw()

    if trial_spec["target_kind"] != "none" and target_contrast > 0.0:
        target_stim.pos = trial_spec["target_pos_cm"]
        target_stim.contrast = target_contrast
        target_stim.draw()

    if response_value is not None and should_draw_potentiometer_bar(trial_spec):
        draw_response_bar(response_value)

    return target_contrast


def make_arrow_head(center, angle_deg, length_cm=0.7, width_cm=0.45):
    angle_rad = math.radians(angle_deg)
    direction = np.array([math.cos(angle_rad), math.sin(angle_rad)])
    perpendicular = np.array([-direction[1], direction[0]])
    tip = np.asarray(center, dtype=float)
    base_center = tip - (direction * length_cm)
    left = base_center + (perpendicular * (width_cm / 2.0))
    right = base_center - (perpendicular * (width_cm / 2.0))
    return np.vstack([tip, left, right])


def draw_arrow(start, end, color=None, line_width=2):
    if color is None:
        color = TEXT_COLOR
    start = np.asarray(start, dtype=float)
    end = np.asarray(end, dtype=float)
    shaft = visual.Line(
        win=win,
        start=tuple(start),
        end=tuple(end),
        lineColor=color,
        lineWidth=line_width,
        units="cm",
    )
    angle_deg = math.degrees(math.atan2(end[1] - start[1], end[0] - start[0]))
    head = visual.ShapeStim(
        win=win,
        vertices=make_arrow_head(end, angle_deg),
        closeShape=True,
        fillColor=color,
        lineColor=color,
        lineWidth=1,
        colorSpace="rgb",
        units="cm",
    )
    shaft.draw()
    head.draw()


def show_static_display_example():
    example_spec = build_trial_spec(
        phase="demo",
        trial_type="peripheral",
        duration_s=DEMO_DURATION,
        response_mode="none",
        block_index=0,
        block_type="demo",
        trial_global_index=0,
        trial_in_block=0,
    )
    title_stim = visual.TextStim(
        win=win,
        text=(
            "A continuación verás un ejemplo estático de la pantalla.\n"
            "Tu tarea consistirá en informar de la visibilidad del estímulo blanco.\n"
            "Aunque ese estímulo aparezca en la periferia, debes mantener la mirada en todo momento en el punto de fijación central."
        ),
        pos=(0.0, 8.2),
        height=0.58,
        color=TEXT_COLOR,
        colorSpace="rgb",
        units="cm",
        wrapWidth=28,
        alignText="center",
    )
    target_label = visual.TextStim(
        win=win,
        text="Estímulo blanco",
        pos=(-13.2, 7.0),
        height=0.5,
        color=TEXT_COLOR,
        colorSpace="rgb",
        units="cm",
    )
    fixation_label = visual.TextStim(
        win=win,
        text="Punto de fijación",
        pos=(11.0, 4.7),
        height=0.5,
        color=TEXT_COLOR,
        colorSpace="rgb",
        units="cm",
    )
    footer_stim = visual.TextStim(
        win=win,
        text="Pulsa ESPACIO para continuar.",
        pos=(0.0, -9.1),
        height=0.52,
        color=TEXT_COLOR,
        colorSpace="rgb",
        units="cm",
    )

    event.clearEvents()
    ensure_not_pressed(key_state_handler, ["space"])
    while True:
        if key_is_down(key_state_handler, "escape"):
            terminate_experiment()
        keys = event.getKeys(keyList=["space", "escape"])
        if "escape" in keys:
            terminate_experiment()
        if "space" in keys:
            return

        draw_trial_scene(example_spec, 0.0)
        title_stim.draw()
        target_label.draw()
        fixation_label.draw()
        footer_stim.draw()
        draw_arrow(start=(-11.2, 6.4), end=tuple(peripheral_target_pos + np.array([-0.25, 0.25])))
        draw_arrow(start=(9.6, 4.0), end=(0.0, 0.0))
        win.flip()


def resample_tet_trace_rows(
    tet_trace_points,
    tet_phase,
    trial_index,
    attempt_index,
    display_duration_s,
    trial_spec,
    plot_left,
    plot_right,
    plot_bottom,
    plot_top,
):
    plot_width = plot_right - plot_left
    plot_height = plot_top - plot_bottom
    normalized_x = np.asarray(
        [(point_x - plot_left) / plot_width for point_x, _ in tet_trace_points],
        dtype=float,
    )
    normalized_y = np.asarray(
        [(point_y - plot_bottom) / plot_height for _, point_y in tet_trace_points],
        dtype=float,
    )
    sample_times = np.arange(0.0, display_duration_s, RESPONSE_LOG_INTERVAL_S)
    if len(sample_times) == 0:
        sample_times = np.array([0.0], dtype=float)
    normalized_time_grid = np.clip(sample_times / display_duration_s, 0.0, 1.0)
    sampled_normalized_visibility = np.interp(
        normalized_time_grid,
        normalized_x,
        normalized_y,
        left=normalized_y[0],
        right=normalized_y[-1],
    )

    rows = []
    for point_index, (normalized_time, normalized_visibility) in enumerate(
        zip(normalized_time_grid, sampled_normalized_visibility),
        start=1,
    ):
        point_x = plot_left + (normalized_time * plot_width)
        point_y = plot_bottom + (normalized_visibility * plot_height)
        rows.append(
            {
                "session_id": SESSION_ID,
                "participant_id": participant_id,
                "tet_phase": tet_phase,
                "trial_index": trial_index,
                "phase": trial_spec["phase"],
                "block_index": trial_spec["block_index"],
                "block_type": trial_spec["block_type"],
                "trial_global_index": trial_spec["trial_global_index"],
                "trial_in_block": trial_spec["trial_in_block"],
                "trial_type": trial_spec["trial_type"],
                "response_mode": trial_spec["response_mode"],
                "display_duration_s": f"{display_duration_s:.3f}",
                "attempt_index": attempt_index,
                "point_index": point_index,
                "x_cm": f"{point_x:.6f}",
                "y_cm": f"{point_y:.6f}",
                "normalized_time": f"{normalized_time:.6f}",
                "normalized_visibility": f"{normalized_visibility:.6f}",
            }
        )
    return rows


def run_visual_trial(trial_spec):
    event.clearEvents()
    response_keyboard.clearEvents()
    # Avoid hidden blocking between button trials when SPACE is still held.
    # For continuous mode we still require key release to avoid carryover.
    if trial_spec["response_mode"] == "continuous":
        keys_to_release = ["space", "up", "down"]
    else:
        keys_to_release = ["up", "down"]
    ensure_not_pressed(key_state_handler, keys_to_release)

    response_value = trial_spec["initial_response_value"]
    button_state_value = 0.0
    button_presses = []
    continuous_rows = []
    trial_clock = core.Clock()
    last_t = 0.0
    next_response_log_t = 0.0
    next_device_query_t = 0.0
    # For calibration/experimental continuous trials, initialize from the
    # physical potentiometer value so each trial starts from real device state.
    if (
        trial_spec["response_mode"] == "continuous"
        and trial_spec["phase"] in ("calibration", "experimental")
        and DEVICE_RATING
        and rating_device.connected
    ):
        response_value = rating_device.read_normalized_value(response_value)
        next_device_query_t = DEVICE_QUERY_INTERVAL_S

    while True:
        t = trial_clock.getTime()
        if t >= trial_spec["duration_s"]:
            break
        if key_is_down(key_state_handler, "escape"):
            terminate_experiment()

        dt = max(t - last_t, 0.0)
        last_t = t

        if trial_spec["response_mode"] == "button":
            keys = response_keyboard.getKeys(
                keyList=["space", "escape"], waitRelease=False, clear=True
            )
            space_pressed_this_frame = False
            for key_press in keys:
                if key_press.name == "escape":
                    terminate_experiment()
                if key_press.name == "space":
                    button_presses.append(float(key_press.rt))
                    space_pressed_this_frame = True
            if key_state_handler is not None:
                button_state_value = 1.0 if key_is_down(key_state_handler, "space") else 0.0
            else:
                button_state_value = 1.0 if space_pressed_this_frame else 0.0

        elif trial_spec["response_mode"] == "continuous":
            if DEVICE_RATING and rating_device.connected:
                if t >= next_device_query_t:
                    response_value = rating_device.read_normalized_value(response_value)
                    while next_device_query_t <= t:
                        next_device_query_t += DEVICE_QUERY_INTERVAL_S
            else:
                delta = 0.0
                if key_is_down(key_state_handler, "up"):
                    delta += POTENTIOMETER_RATE_PER_SEC * dt
                if key_is_down(key_state_handler, "down"):
                    delta -= POTENTIOMETER_RATE_PER_SEC * dt
                response_value = clamp(response_value + delta, 0.0, 1.0)

        target_contrast = draw_trial_scene(
            trial_spec,
            t,
            response_value if trial_spec["response_mode"] == "continuous" else None,
        )
        win.flip()

        if trial_spec["response_mode"] in ("continuous", "button"):
            frame_response_value = (
                response_value
                if trial_spec["response_mode"] == "continuous"
                else button_state_value
            )
            while (
                next_response_log_t <= t
                and next_response_log_t < trial_spec["duration_s"]
            ):
                sampled_target_contrast = compute_contrast(trial_spec, next_response_log_t)
                continuous_rows.append(
                    {
                        "session_id": SESSION_ID,
                        "participant_id": participant_id,
                        "phase": trial_spec["phase"],
                        "block_index": trial_spec["block_index"],
                        "block_type": trial_spec["block_type"],
                        "trial_global_index": trial_spec["trial_global_index"],
                        "trial_in_block": trial_spec["trial_in_block"],
                        "trial_type": trial_spec["trial_type"],
                        "response_mode": trial_spec["response_mode"],
                        "is_calibration": int(trial_spec["phase"] == "calibration"),
                        "time_s": f"{next_response_log_t:.6f}",
                        "target_contrast": f"{sampled_target_contrast:.6f}",
                        "target_contrast_true": f"{sampled_target_contrast:.6f}",
                        "response_value": f"{frame_response_value:.6f}",
                    }
                )
                next_response_log_t += RESPONSE_LOG_INTERVAL_S

    n_response_samples = ""
    mean_response_value = ""
    min_response_value = ""
    max_response_value = ""
    final_response_value = ""
    button_state_proportion = ""
    mean_visibility = ""
    min_visibility = ""
    max_visibility = ""
    final_visibility = ""
    if continuous_rows:
        continuous_values = [float(row["response_value"]) for row in continuous_rows]
        n_response_samples = len(continuous_values)
        mean_response_value = f"{np.mean(continuous_values):.6f}"
        min_response_value = f"{np.min(continuous_values):.6f}"
        max_response_value = f"{np.max(continuous_values):.6f}"
        final_response_value = f"{continuous_values[-1]:.6f}"
        if trial_spec["response_mode"] == "button":
            button_state_proportion = mean_response_value
        mean_visibility = mean_response_value
        min_visibility = min_response_value
        max_visibility = max_response_value
        final_visibility = final_response_value

    trial_summary = {
        "session_id": SESSION_ID,
        "participant_id": participant_id,
        "phase": trial_spec["phase"],
        "block_index": trial_spec["block_index"],
        "block_type": trial_spec["block_type"],
        "trial_global_index": trial_spec["trial_global_index"],
        "trial_in_block": trial_spec["trial_in_block"],
        "trial_type": trial_spec["trial_type"],
        "control_trial": int(trial_spec["control_trial"]),
        "target_kind": trial_spec["target_kind"],
        "target_position_x_cm": f"{trial_spec['target_pos_cm'][0]:.6f}",
        "target_position_y_cm": f"{trial_spec['target_pos_cm'][1]:.6f}",
        "target_contrast_mode": trial_spec["target_contrast_mode"],
        "response_mode": trial_spec["response_mode"],
        "duration_s": f"{trial_spec['duration_s']:.3f}",
        "button_press_count": len(button_presses),
        "button_press_times_s": ";".join(f"{value:.6f}" for value in button_presses),
        "n_response_samples": n_response_samples,
        "mean_response_value": mean_response_value,
        "min_response_value": min_response_value,
        "max_response_value": max_response_value,
        "final_response_value": final_response_value,
        "button_state_proportion": button_state_proportion,
        "mean_visibility": mean_visibility,
        "min_visibility": min_visibility,
        "max_visibility": max_visibility,
        "final_visibility": final_visibility,
    }

    button_rows = []
    for event_index, press_time in enumerate(button_presses, start=1):
        button_rows.append(
            {
                "session_id": SESSION_ID,
                "participant_id": participant_id,
                "block_index": trial_spec["block_index"],
                "block_type": trial_spec["block_type"],
                "trial_global_index": trial_spec["trial_global_index"],
                "trial_in_block": trial_spec["trial_in_block"],
                "trial_type": trial_spec["trial_type"],
                "event_index": event_index,
                "event_time_s": f"{press_time:.6f}",
            }
        )

    return trial_summary, button_rows, continuous_rows


def build_trial_spec(
    phase,
    trial_type,
    duration_s,
    response_mode,
    block_index,
    block_type,
    trial_global_index,
    trial_in_block,
):
    target_kind = "none"
    target_pos_cm = np.array([0.0, 0.0])
    target_contrast_mode = "constant"
    target_contrast_value = 1.0
    control_trial = False
    initial_response_value = 0.5
    mask_motion = "rotating"

    if trial_type == "peripheral":
        target_kind = "peripheral"
        target_pos_cm = peripheral_target_pos
        target_contrast_value = 1.0
    elif trial_type == "no_target":
        target_kind = "none"
        target_contrast_value = 0.0
    elif trial_type == "static_mask":
        target_kind = "peripheral"
        target_pos_cm = peripheral_target_pos
        target_contrast_value = 1.0
        control_trial = True
        mask_motion = "static"
    elif trial_type == "near_fixation":
        target_kind = "near_fixation_control"
        target_pos_cm = near_fixation_target_pos
        target_contrast_value = 1.0
        control_trial = True
    elif trial_type == "calibration_up":
        target_kind = "fixation_calibration"
        target_pos_cm = np.array([0.0, 0.0])
        target_contrast_mode = "ramp_up"
        target_contrast_value = 0.0
        response_mode = "continuous"
        initial_response_value = 0.0
    elif trial_type == "calibration_down":
        target_kind = "fixation_calibration"
        target_pos_cm = np.array([0.0, 0.0])
        target_contrast_mode = "ramp_down"
        target_contrast_value = 1.0
        response_mode = "continuous"
        initial_response_value = 1.0
    elif trial_type == "calibration_sinusoidal":
        target_kind = "fixation_calibration"
        target_pos_cm = np.array([0.0, 0.0])
        target_contrast_mode = "sinusoidal"
        target_contrast_value = 0.0
        response_mode = "continuous"
        initial_response_value = 1.0

    if response_mode == "continuous" and trial_type == "no_target":
        initial_response_value = 0.0
    elif response_mode == "continuous" and trial_type in ("static_mask", "near_fixation"):
        initial_response_value = 1.0

    return {
        "phase": phase,
        "trial_type": trial_type,
        "duration_s": duration_s,
        "response_mode": response_mode,
        "block_index": block_index,
        "block_type": block_type,
        "trial_global_index": trial_global_index,
        "trial_in_block": trial_in_block,
        "target_kind": target_kind,
        "target_pos_cm": np.asarray(target_pos_cm, dtype=float),
        "target_contrast_mode": target_contrast_mode,
        "target_contrast_value": target_contrast_value,
        "control_trial": control_trial,
        "initial_response_value": initial_response_value,
        "mask_motion": mask_motion,
    }


def validate_block_trials(trials, block_type):
    if len(trials) != BLOCK_SIZE:
        raise ValueError(
            f"{block_type} block must contain exactly {BLOCK_SIZE} trials."
        )

    counts = {
        "peripheral": 0,
        "no_target": 0,
        CONTROL_TRIAL_TYPE: 0,
    }
    for trial in trials:
        counts[trial] += 1

    if counts["peripheral"] != PERIPHERAL_TRIALS_PER_BLOCK:
        raise ValueError(
            f"Each block must contain exactly {PERIPHERAL_TRIALS_PER_BLOCK} peripheral target trials."
        )
    if counts["no_target"] != NO_TARGET_TRIALS_PER_BLOCK:
        raise ValueError(
            f"Each block must contain exactly {NO_TARGET_TRIALS_PER_BLOCK} no-target trials."
        )
    if counts[CONTROL_TRIAL_TYPE] != STATIC_MASK_TRIALS_PER_BLOCK:
        raise ValueError(
            f"Each block must contain exactly {STATIC_MASK_TRIALS_PER_BLOCK} control trials of type {CONTROL_TRIAL_TYPE}."
        )


def build_block_trials(block_type, block_index, starting_trial_index, rng):
    trial_types = ["peripheral"] * PERIPHERAL_TRIALS_PER_BLOCK
    if NO_TARGET_TRIALS_PER_BLOCK > 0:
        trial_types += ["no_target"] * NO_TARGET_TRIALS_PER_BLOCK
    if STATIC_MASK_TRIALS_PER_BLOCK > 0:
        trial_types += [CONTROL_TRIAL_TYPE] * STATIC_MASK_TRIALS_PER_BLOCK
    validate_block_trials(trial_types, block_type)
    rng.shuffle(trial_types)

    if block_type == "button":
        response_mode = "button"
        duration_s = TRIAL_DURATION
    elif block_type == "potentiometer":
        response_mode = "continuous"
        duration_s = TRIAL_DURATION
    elif block_type == "tet":
        response_mode = "tet"
        duration_s = TET_EXPERIMENTAL_DISPLAY_DURATION
    else:
        raise ValueError(f"Unsupported block type: {block_type}")

    trial_specs = []
    for offset, trial_type in enumerate(trial_types, start=1):
        trial_specs.append(
            build_trial_spec(
                phase="experimental",
                trial_type=trial_type,
                duration_s=duration_s,
                response_mode=response_mode,
                block_index=block_index,
                block_type=block_type,
                trial_global_index=starting_trial_index + offset - 1,
                trial_in_block=offset,
            )
        )
    return trial_specs


def build_practice_trial_specs(block_type):
    if block_type == "button":
        response_mode = "button"
        practice_block_type = "button_practice"
    elif block_type == "potentiometer":
        response_mode = "continuous"
        practice_block_type = "potentiometer_practice"
    elif block_type == "tet":
        response_mode = "tet"
        practice_block_type = "tet_practice"
    else:
        raise ValueError(f"Unsupported practice block type: {block_type}")

    trial_specs = []
    for trial_in_block in range(1, PRACTICE_TRIALS_PER_BLOCK + 1):
        trial_specs.append(
            build_trial_spec(
                phase="practice",
                trial_type="peripheral",
                duration_s=PRACTICE_TRIAL_DURATION,
                response_mode=response_mode,
                block_index=0,
                block_type=practice_block_type,
                trial_global_index=0,
                trial_in_block=trial_in_block,
            )
        )
    return trial_specs


def run_internal_protocol_validations():
    expected_blocks = set(EXPERIMENTAL_BLOCKS_ALL)
    permutations = list(itertools.permutations(EXPERIMENTAL_BLOCKS_ALL))
    if len(permutations) != 6:
        raise ValueError("Expected exactly 6 permutations for three experimental blocks.")
    if len(set(permutations)) != 6:
        raise ValueError("Duplicated permutations detected in block counterbalancing.")
    for permutation in permutations:
        if len(set(permutation)) != 3 or set(permutation) != expected_blocks:
            raise ValueError(
                f"Invalid permutation detected in block counterbalancing: {permutation}."
            )

    if TEST_MODE:
        if PRACTICE_TRIALS_PER_BLOCK != 1:
            raise ValueError("TEST_MODE must run with PRACTICE_TRIALS_PER_BLOCK = 1.")
        if (
            PERIPHERAL_TRIALS_PER_BLOCK
            + NO_TARGET_TRIALS_PER_BLOCK
            + STATIC_MASK_TRIALS_PER_BLOCK
        ) != BLOCK_SIZE:
            raise ValueError("TEST_MODE trial composition must sum to BLOCK_SIZE.")
    else:
        if TRIAL_DURATION != 30.0:
            raise ValueError("Full mode trials must last 30 seconds.")
        if PRACTICE_TRIALS_PER_BLOCK != 5:
            raise ValueError("Practice blocks must contain 5 trials.")
        if (
            PERIPHERAL_TRIALS_PER_BLOCK
            + NO_TARGET_TRIALS_PER_BLOCK
            + STATIC_MASK_TRIALS_PER_BLOCK
        ) != BLOCK_SIZE:
            raise ValueError("Full mode trial composition must sum to BLOCK_SIZE.")

    for block_type in EXPERIMENTAL_BLOCKS_ALL:
        block_trials = build_block_trials(
            block_type=block_type,
            block_index=1,
            starting_trial_index=1,
            rng=random.Random(17),
        )
        if len(block_trials) != BLOCK_SIZE:
            raise ValueError(f"{block_type} block does not match BLOCK_SIZE.")
        if block_type == "tet":
            for trial_spec in block_trials:
                if trial_spec["response_mode"] != "tet":
                    raise ValueError("TET trial response_mode must be 'tet'.")
                if (
                    abs(trial_spec["duration_s"] - TET_EXPERIMENTAL_DISPLAY_DURATION)
                    > 1e-9
                ):
                    raise ValueError(
                        "TET trial duration must use TET_EXPERIMENTAL_DISPLAY_DURATION."
                    )

    practice_specs = build_practice_trial_specs("button")
    if len(practice_specs) != PRACTICE_TRIALS_PER_BLOCK:
        raise ValueError("Button practice does not match PRACTICE_TRIALS_PER_BLOCK.")
    practice_specs = build_practice_trial_specs("potentiometer")
    if len(practice_specs) != PRACTICE_TRIALS_PER_BLOCK:
        raise ValueError(
            "Potentiometer practice does not match PRACTICE_TRIALS_PER_BLOCK."
        )
    practice_specs = build_practice_trial_specs("tet")
    if len(practice_specs) != PRACTICE_TRIALS_PER_BLOCK:
        raise ValueError("TET practice does not match PRACTICE_TRIALS_PER_BLOCK.")

    if STATIC_MASK_TRIALS_PER_BLOCK > 0:
        button_trials = build_block_trials(
            block_type="button",
            block_index=1,
            starting_trial_index=1,
            rng=random.Random(23),
        )
        button_trial_types = [trial["trial_type"] for trial in button_trials]
        if "fixation_above" in button_trial_types or "fixation_below" in button_trial_types:
            raise ValueError("Legacy fixation control trials should not appear in blocks.")
        if button_trial_types.count(CONTROL_TRIAL_TYPE) != STATIC_MASK_TRIALS_PER_BLOCK:
            raise ValueError("Configured control trials do not match block composition.")


def validate_output_paths(participant_id):
    expected_participant_dir = os.path.join(DATA_DIR, f"participant_{participant_id}")
    if PARTICIPANT_DATA_DIR != expected_participant_dir:
        raise ValueError("Participant data directory does not match expected structure.")
    for path in (
        SESSION_SUMMARY_FILE,
        TRIAL_SUMMARY_FILE,
        BUTTON_EVENTS_FILE,
        CONTINUOUS_FILE,
        TET_FILE,
    ):
        if not path.startswith(PARTICIPANT_DATA_DIR):
            raise ValueError("Output file is outside the participant data directory.")


def record_counterbalance_assignment(
    participant_id,
    participant_age,
    participant_gender,
    assigned_order,
):
    append_csv_row(
        COUNTERBALANCE_FILE,
        COUNTERBALANCE_FIELDNAMES,
        {
            "session_id": SESSION_ID,
            "participant_id": participant_id,
            "participant_age": participant_age,
            "participant_gender": participant_gender,
            "assigned_at": SESSION_ID,
            "assigned_order": assigned_order,
        },
    )


def show_standardized_instructions():
    show_message_and_wait(
        "Vas a realizar una tarea en la que nos interesa cómo percibes la visibilidad de un estímulo que aparecerá en pantalla.\n"
        "En algunas condiciones, la visibilidad de ese estímulo puede fluctuar a lo largo del tiempo.\n"
        "Durante toda la tarea debes mantener la mirada en el punto de fijación central.\n"
        "A lo largo del experimento te pediremos que informes de la visibilidad del estímulo de distintas maneras, según se te indique en cada parte.\n\n"
        "Pulsa ESPACIO para continuar.",
        key_list=["space"],
    )


def show_demo():
    show_message_and_wait(
        "A continuación verás un ensayo breve de demostración.\n"
        "Mantén la mirada en el punto central.\n"
        "Durante esta parte no tienes que responder.\n\n"
        "Pulsa ESPACIO para empezar."
    )

    demo_spec = build_trial_spec(
        phase="demo",
        trial_type="peripheral",
        duration_s=DEMO_DURATION,
        response_mode="none",
        block_index=0,
        block_type="demo",
        trial_global_index=0,
        trial_in_block=0,
    )
    run_visual_trial(demo_spec)
    show_demo_complete_screen()


def show_tet_block_instructions(block_index, total_blocks):
    show_message_and_wait(
        f"En este bloque, primero observarás el estímulo durante {TET_EXPERIMENTAL_DISPLAY_DURATION:.0f} segundos y, después, dibujarás cómo cambió su visibilidad a lo largo del tiempo.\n"
        f"Antes de empezar el bloque experimental harás {practice_instruction_count_text()}.\n\n"
        "El dibujo se hará sobre unos ejes.\n"
        "El eje horizontal representa el tiempo y el eje vertical representa la visibilidad.\n"
        "La parte alta indica más visibilidad y la parte baja menos visibilidad.\n"
        "Es importante que lleves la línea hasta el final del eje temporal antes de terminar.\n\n"
        "Pulsa ESPACIO para continuar."
    )


def show_tet_experimental_instructions(block_index, total_blocks):
    show_message_and_wait(
        f"En cada ensayo, al igual que en la práctica observarás el estímulo durante {TET_EXPERIMENTAL_DISPLAY_DURATION:.0f} segundos.\n"
        "Mantén la mirada en el punto central mientras lo observas.\n"
        "Después dibuja, en los ejes, cómo fue cambiando la visibilidad a lo largo del ensayo.\n"
        "No termines el trazado hasta haber llegado al borde derecho de la gráfica.\n\n"
        "Pulsa ESPACIO para continuar."
    )


def show_tet_graph_example():
    show_message_and_wait(
        "Antes de empezar las prácticas, vas a ver un ejemplo de la gráfica en la que tendrás que dibujar.\n"
        "Puedes probar cómo se dibuja la línea con el ratón y familiarizarte con los ejes.\n"
        "Puedes borrar tantas veces como desees.\n"
        "Cuando quieras, completa el trazado hasta el final y pulsa ENTER.\n\n"
        "Pulsa ESPACIO para continuar.",
        key_list=["space"],
    )
    example_spec = build_trial_spec(
        phase="practice",
        trial_type="peripheral",
        duration_s=TET_PRACTICE_TRIAL_DURATION,
        response_mode="tet",
        block_index=0,
        block_type="tet_graph_example",
        trial_global_index=0,
        trial_in_block=0,
    )
    run_tet_drawing(
        tet_phase="practice",
        trial_index=0,
        attempt_index=0,
        display_duration_s=TET_PRACTICE_TRIAL_DURATION,
        trial_spec=example_spec,
    )
    show_message_and_wait(
        "Has terminado esta prueba de la gráfica.\n\n"
        "Pulsa ESPACIO para continuar.",
        key_list=["space"],
    )


def run_tet_drawing(
    tet_phase,
    trial_index,
    attempt_index,
    display_duration_s,
    trial_spec,
):
    mouse = event.Mouse(win=win)
    mouse.setVisible(True)
    event.clearEvents()

    plot_left = -8.0
    plot_right = 8.0
    plot_bottom = -4.0
    plot_top = 4.0
    plot_width = plot_right - plot_left
    plot_height = plot_top - plot_bottom

    horizontal_axis.start = (plot_left, plot_bottom)
    horizontal_axis.end = (plot_right, plot_bottom)
    vertical_axis.start = (plot_left, plot_bottom)
    vertical_axis.end = (plot_left, plot_top)
    plot_border.pos = ((plot_left + plot_right) / 2.0, (plot_top + plot_bottom) / 2.0)
    plot_border.vertices = rect_vertices(plot_width, plot_height)

    tet_instruction.text = (
        "Haz clic y arrastra para dibujar la visibilidad a lo largo del tiempo.\n"
        "El trazado debe empezar en el borde izquierdo y terminar en el borde derecho.\n"
        "Arriba significa más visible y abajo menos visible.\n"
        "Si percibes el estímulo con máxima intensidad, intenta con tu línea llegar hasta arriba de la gráfica. Si dejas de ver el estímulo, llega hasta abajo con la línea.\n"
        "Pulsa RETROCESO para reiniciar. Pulsa ENTER para confirmar."
    )

    tet_trace_points = []
    warning_text = ""
    completion_tolerance_cm = plot_width * TET_COMPLETION_TOLERANCE

    while True:
        if key_is_down(key_state_handler, "escape"):
            terminate_experiment()

        keys = event.getKeys(keyList=["return", "r", "backspace", "escape"])
        if "escape" in keys:
            terminate_experiment()
        if "r" in keys or "backspace" in keys:
            tet_trace_points = []
            warning_text = ""

        left_button = mouse.getPressed()[0]
        mouse_x, mouse_y = mouse.getPos()
        inside_time_window = plot_left <= mouse_x <= plot_right

        if left_button and inside_time_window:
            clamped_y = clamp(mouse_y, plot_bottom, plot_top)
            if not tet_trace_points:
                # Force canonical start at the left edge.
                tet_trace_points.append((plot_left, clamped_y))
            clamped_x = clamp(mouse_x, plot_left, plot_right)
            clamped_x = max(clamped_x, tet_trace_points[-1][0])
            if (
                np.linalg.norm(
                    np.asarray([clamped_x, clamped_y])
                    - np.asarray(tet_trace_points[-1])
                )
                >= 0.05
            ):
                tet_trace_points.append((clamped_x, clamped_y))
                warning_text = ""

        if "return" in keys and len(tet_trace_points) >= 1:
            if tet_trace_points[-1][0] < (plot_right - completion_tolerance_cm):
                warning_text = (
                    "El trazado no llega hasta el final del ensayo.\n"
                    "Continúa la línea hasta el borde derecho de la gráfica antes de terminar."
                )
            else:
                break
        elif "return" in keys:
            warning_text = (
                "El trazado no llega hasta el final del ensayo.\n"
                "Continúa la línea hasta el borde derecho de la gráfica antes de terminar."
            )

        tet_instruction.draw()
        plot_border.draw()
        horizontal_axis.draw()
        vertical_axis.draw()
        x_axis_label.draw()
        visible_label.draw()
        invisible_label.draw()
        if len(tet_trace_points) >= 2:
            tet_trace.vertices = tet_trace_points
            tet_trace.draw()
        if warning_text:
            text_stim.text = warning_text
            text_stim.pos = (0.0, -6.5)
            text_stim.draw()
        win.flip()

    text_stim.pos = (0.0, 0.0)

    mouse.setVisible(False)

    return resample_tet_trace_rows(
        tet_trace_points=tet_trace_points,
        tet_phase=tet_phase,
        trial_index=trial_index,
        attempt_index=attempt_index,
        display_duration_s=display_duration_s,
        trial_spec=trial_spec,
        plot_left=plot_left,
        plot_right=plot_right,
        plot_bottom=plot_bottom,
        plot_top=plot_top,
    )


def run_tet_practice():
    tet_rows = []
    practice_specs = build_practice_trial_specs("tet")
    show_tet_graph_example()
    show_practice_intro_screen(
        "Ahora vamos a realizar unos ensayos de práctica.\n"
        f"En cada uno de ellos observarás primero el estímulo durante {TET_PRACTICE_TRIAL_DURATION:.0f} segundos y, después, tendrás que dibujar de la manera más fiel posible cómo cambió su visibilidad a lo largo del tiempo."
    )
    for practice_spec in practice_specs:
        trial_summary, trial_button_rows, trial_continuous_rows = run_visual_trial(
            practice_spec
        )
        persist_trial_outputs(
            trial_summary, trial_button_rows, trial_continuous_rows
        )
        practice_rows = run_tet_drawing(
            tet_phase="practice",
            trial_index=practice_spec["trial_in_block"],
            attempt_index=1,
            display_duration_s=TET_PRACTICE_TRIAL_DURATION,
            trial_spec=practice_spec,
        )
        tet_rows.extend(practice_rows)
        persist_tet_rows(practice_rows)
        if practice_spec is not practice_specs[-1]:
            show_message_and_wait(
                "Has terminado este ensayo de práctica.\n\nPulsa Y para continuar.",
                key_list=["y"],
            )
    show_practice_complete_screen("Pulsa Y cuando estés listo/a para continuar.")
    return tet_rows


def run_tet_experimental_block(block_index, total_blocks, starting_trial_index, rng):
    show_tet_experimental_instructions(block_index, total_blocks)
    trial_specs = build_block_trials(
        block_type="tet",
        block_index=block_index,
        starting_trial_index=starting_trial_index,
        rng=rng,
    )
    all_rows = []
    for trial_spec in trial_specs:
        trial_summary, trial_button_rows, trial_continuous_rows = run_visual_trial(trial_spec)
        persist_trial_outputs(trial_summary, trial_button_rows, trial_continuous_rows)
        tet_rows = run_tet_drawing(
            tet_phase="experimental",
            trial_index=trial_spec["trial_in_block"],
            attempt_index=1,
            display_duration_s=trial_spec["duration_s"],
            trial_spec=trial_spec,
        )
        persist_tet_rows(tet_rows)
        all_rows.extend(tet_rows)
        if trial_spec is not trial_specs[-1]:
            show_trial_wait_screen()
    return all_rows


def run_button_practice(block_index, total_blocks):
    practice_specs = build_practice_trial_specs("button")
    show_button_practice_intro_screen()
    for practice_spec in practice_specs:
        trial_summary, trial_button_rows, trial_continuous_rows = run_visual_trial(
            practice_spec
        )
        persist_trial_outputs(
            trial_summary, trial_button_rows, trial_continuous_rows
        )
        if practice_spec is not practice_specs[-1]:
            show_message_and_wait(
                "Has terminado este ensayo.\n\nPulsa Y para continuar el próximo ensayo de práctica.",
                key_list=["y"],
            )
    show_practice_complete_screen(
        "Pulsa Y cuando estés listo/a para comenzar el primer ensayo."
    )


def run_potentiometer_practice(block_index, total_blocks):
    practice_specs = build_practice_trial_specs("potentiometer")
    show_practice_intro_screen(
        "Ahora vamos a realizar unos ensayos de práctica con el potenciómetro.\n"
        "Durante estas prácticas, ajusta la respuesta de forma continua para reflejar cuánta visibilidad percibes. Si percibes la intensidad máxima, lleva el potenciómetro hasta el tope de arriba del todo. Si percibes la intensidad mínima, lleva el potenciómetro hasta el tope de abajo del todo. Realiza los movimientos tan bruscamente o tan progresivamente como tu visibilidad cambie."
    )
    for practice_spec in practice_specs:
        trial_summary, trial_button_rows, trial_continuous_rows = run_visual_trial(
            practice_spec
        )
        persist_trial_outputs(
            trial_summary, trial_button_rows, trial_continuous_rows
        )
        if DEVICE_RATING and practice_spec is not practice_specs[-1]:
            show_potentiometer_wait_screen(
                "Antes del siguiente ensayo, vuelve a colocar el potenciómetro en la posición más alta."
            )
        elif practice_spec is not practice_specs[-1]:
            show_trial_wait_screen()
    if DEVICE_RATING:
        final_prompt = (
            "Antes de empezar, coloca el potenciómetro en la posición más alta.\n\n"
            "Pulsa Y para continuar."
        )
    else:
        final_prompt = "Pulsa Y cuando estés listo/a para comenzar el primer ensayo."
    show_practice_complete_screen(final_prompt)


def show_button_block_instructions(block_index, total_blocks):
    show_button_block_instruction_screen()


def show_potentiometer_block_instructions(block_index, total_blocks):
    response_device_text = (
        "Usa el potenciómetro para indicar cuánta visibilidad percibes."
        if DEVICE_RATING
        else "Usa las teclas UP y DOWN para indicar cuánta visibilidad percibes."
    )
    controls_hint = (
        "Si usas el teclado, la tecla UP indica más visibilidad y la tecla DOWN menos visibilidad."
        if not DEVICE_RATING
        else ""
    )
    message = (
        "En esta parte de la tarea, debes ajustar la respuesta de forma continua para reflejar cómo cambia la visibilidad del estímulo.\n"
        "Mantén la mirada en el punto central durante todos los ensayos.\n"
        f"{response_device_text}\n"
        "La parte alta de la escala corresponde a más visibilidad y la parte baja a menos visibilidad.\n"
    )
    if controls_hint:
        message += f"{controls_hint}\n"
    message += (
        f"Primero realizarás una breve calibración y, después, harás {practice_instruction_count_text()}.\n\n"
        "Pulsa ESPACIO para continuar."
    )
    show_message_and_wait(message)


def run_potentiometer_calibration(block_index):
    show_potentiometer_device_demo()
    show_calibration_intro_screen()
    if TEST_MODE:
        calibration_plan = [
            ("calibration_up", CALIBRATION_DURATION),
            ("calibration_down", CALIBRATION_DURATION),
            ("calibration_sinusoidal", SINUSOIDAL_CALIBRATION_DURATION),
        ]
    else:
        calibration_plan = [
            ("calibration_up", CALIBRATION_DURATION),
            ("calibration_up", CALIBRATION_DURATION),
            ("calibration_down", CALIBRATION_DURATION),
            ("calibration_down", CALIBRATION_DURATION),
            ("calibration_sinusoidal", SINUSOIDAL_CALIBRATION_DURATION),
            ("calibration_sinusoidal", SINUSOIDAL_CALIBRATION_DURATION),
        ]
    for trial_in_block, (trial_type, duration_s) in enumerate(
        calibration_plan,
        start=1,
    ):
        start_position = "high"
        trial_intro_text = (
            "En este ensayo, la intensidad del punto blanco irá bajando y subiendo de intensidad.\n"
            "Mantén la mirada en el centro y ajusta la respuesta para seguir la visibilidad del punto."
        )
        if trial_type == "calibration_up":
            start_position = "low"
            trial_intro_text = (
                "En este ensayo, la intensidad del punto blanco irá subiendo desde la mínima intensidad hasta la máxima intensidad.\n"
                "Mantén la mirada en el centro y ajusta la respuesta para seguir la visibilidad del punto."
            )
        elif trial_type in ("calibration_down", "calibration_sinusoidal"):
            start_position = "high"
            if trial_type == "calibration_down":
                trial_intro_text = (
                    "En este ensayo, la intensidad del punto blanco irá bajando desde la máxima intensidad hasta la mínima intensidad.\n"
                    "Mantén la mirada en el centro y ajusta la respuesta para seguir la visibilidad del punto."
                )
        show_potentiometer_trial_start_screen(
            trial_intro_text,
            start_position=start_position,
        )
        calibration_spec = build_trial_spec(
            phase="calibration",
            trial_type=trial_type,
            duration_s=duration_s,
            response_mode="continuous",
            block_index=block_index,
            block_type="potentiometer_calibration",
            trial_global_index=0,
            trial_in_block=trial_in_block,
        )
        trial_summary, _, trial_continuous_rows = run_visual_trial(calibration_spec)
        persist_trial_outputs(trial_summary, [], trial_continuous_rows)
        if DEVICE_RATING and trial_in_block < len(calibration_plan):
            next_trial_type = calibration_plan[trial_in_block][0]
            if next_trial_type == "calibration_up":
                reminder_text = (
                    "Antes del siguiente ensayo, vuelve a colocar el potenciómetro en la posición más baja."
                )
            else:
                reminder_text = (
                    "Antes del siguiente ensayo, vuelve a colocar el potenciómetro en la posición más alta."
                )
            show_potentiometer_wait_screen(reminder_text)
        elif trial_in_block < len(calibration_plan):
            show_trial_wait_screen()

    show_message_and_wait(
        "Has terminado la calibración.\n\n"
        "Pulsa ESPACIO para continuar."
    )


def run_standard_experimental_block(
    block_type,
    block_index,
    starting_trial_index,
    rng,
):
    trial_specs = build_block_trials(block_type, block_index, starting_trial_index, rng)
    for trial_index, trial_spec in enumerate(trial_specs, start=1):
        trial_summary, trial_button_rows, trial_continuous_rows = run_visual_trial(
            trial_spec
        )
        persist_trial_outputs(
            trial_summary, trial_button_rows, trial_continuous_rows
        )
        if (
            block_type == "potentiometer"
            and DEVICE_RATING
            and trial_index < len(trial_specs)
        ):
            show_potentiometer_wait_screen(
                "Antes del siguiente ensayo, vuelve a colocar el potenciómetro en la posición más alta."
            )
        elif trial_index < len(trial_specs):
            show_trial_wait_screen()


# =========================================================
# PARTICIPANT SETUP
# =========================================================
participant_id, participant_age, participant_gender = collect_participant_info()
configure_output_files(participant_id)
validate_output_paths(participant_id)
block_sequence = resolve_block_sequence(participant_id)
assigned_order = assigned_order_to_label(block_sequence)
if INCLUDE_POTENTIOMETER_BLOCK:
    counterbalance_rule = (
        "participant_id_modulo_6_over_button_potentiometer_tet_permutations"
    )
else:
    counterbalance_rule = "participant_id_modulo_2_over_button_tet_permutations"


# =========================================================
# MONITOR AND WINDOW
# =========================================================
mon = monitors.Monitor(MONITOR_NAME)
mon.setWidth(MONITOR_WIDTH_CM)
mon.setSizePix(MONITOR_RES)
mon.setDistance(VIEWING_DISTANCE_CM)

monitor_saved = True
monitor_save_error = ""
try:
    mon.saveMon()
except Exception as exc:
    monitor_saved = False
    monitor_save_error = str(exc)

win = visual.Window(
    size=MONITOR_RES,
    monitor=mon,
    units="cm",
    fullscr=FULLSCR,
    color=BG_COLOR,
    colorSpace="rgb",
    allowGUI=not FULLSCR,
)

measured_fps = win.getActualFrameRate(
    nIdentical=20,
    nMaxFrames=240,
    nWarmUpFrames=30,
    threshold=1,
)
fps_warning = ""
if measured_fps is None:
    fps_warning = "No stable frame-rate estimate was obtained."
else:
    nominal_refresh_hz = 60.0
    if abs(measured_fps - nominal_refresh_hz) > FPS_WARNING_THRESHOLD_HZ:
        fps_warning = f"Estimated refresh rate: {measured_fps:.2f} Hz."


# =========================================================
# STIMULI
# =========================================================
fix = visual.ShapeStim(
    win=win,
    vertices=circle_vertices(FIX_DIAM_CM / 2.0),
    closeShape=True,
    pos=(0, 0),
    fillColor=FIX_COLOR,
    lineColor=FIX_COLOR,
    lineWidth=1,
    colorSpace="rgb",
    units="cm",
)

gauss_tex = np.ones((256, 256))
target_stim = visual.GratingStim(
    win=win,
    tex=gauss_tex,
    mask="gauss",
    size=TARGET_SIZE_CM,
    pos=(0, 0),
    color=TARGET_COLOR,
    colorSpace="rgb",
    units="cm",
    interpolate=True,
)

base_positions = make_grid_positions(GRID_N, CROSS_SPACING_CM)
clearance_cm = PROTECTION_RADIUS_CM + (CROSS_WIDTH_CM / 2.0) + 0.05
cross_verts = cross_vertices(CROSS_WIDTH_CM, arm_ratio=CROSS_ARM_RATIO)
crosses = []
for position in base_positions:
    stim = visual.ShapeStim(
        win=win,
        vertices=cross_verts,
        closeShape=True,
        fillColor=CROSS_COLOR,
        lineColor=CROSS_COLOR,
        lineWidth=1,
        pos=position,
        ori=0,
        colorSpace="rgb",
        units="cm",
    )
    crosses.append(stim)

text_stim = visual.TextStim(
    win=win,
    text="",
    color=TEXT_COLOR,
    colorSpace="rgb",
    height=0.58,
    units="cm",
    wrapWidth=26,
)

response_bar_frame = visual.ShapeStim(
    win=win,
    vertices=rect_vertices(0.8, 8.0),
    closeShape=True,
    pos=(18.5, 0.0),
    lineColor=BAR_FRAME_COLOR,
    fillColor=None,
    lineWidth=2,
    units="cm",
)
response_bar_fill = visual.ShapeStim(
    win=win,
    vertices=rect_vertices(0.6, 0.04),
    closeShape=True,
    pos=(18.5, -4.0),
    lineColor=BAR_FILL_COLOR,
    fillColor=BAR_FILL_COLOR,
    lineWidth=1,
    units="cm",
)
response_bar_label = visual.TextStim(
    win=win,
    text="Visibilidad",
    pos=(18.5, 5.2),
    height=0.45,
    color=TEXT_COLOR,
    colorSpace="rgb",
    units="cm",
)
response_bar_top_label = visual.TextStim(
    win=win,
    text="Veo el estímulo\ncon total claridad",
    pos=(18.5, 4.95),
    height=0.31,
    color=TEXT_COLOR,
    colorSpace="rgb",
    units="cm",
    wrapWidth=4.4,
    alignText="center",
)
response_bar_bottom_label = visual.TextStim(
    win=win,
    text="No veo\nel estímulo",
    pos=(18.5, -5.0),
    height=0.31,
    color=TEXT_COLOR,
    colorSpace="rgb",
    units="cm",
    wrapWidth=4.1,
    alignText="center",
)

tet_instruction = visual.TextStim(
    win=win,
    text="",
    pos=(0.0, 7.0),
    height=0.5,
    color=TEXT_COLOR,
    colorSpace="rgb",
    units="cm",
    wrapWidth=26,
)
plot_border = visual.ShapeStim(
    win=win,
    vertices=rect_vertices(16.0, 8.0),
    closeShape=True,
    pos=(0.0, 0.0),
    lineColor=TEXT_COLOR,
    fillColor=None,
    lineWidth=1,
    units="cm",
)
horizontal_axis = visual.Line(
    win=win,
    start=(-8.0, -4.0),
    end=(8.0, -4.0),
    lineColor=TEXT_COLOR,
    lineWidth=2,
    units="cm",
)
vertical_axis = visual.Line(
    win=win,
    start=(-8.0, -4.0),
    end=(-8.0, 4.0),
    lineColor=TEXT_COLOR,
    lineWidth=2,
    units="cm",
)
x_axis_label = visual.TextStim(
    win=win,
    text="Tiempo",
    pos=(0.0, -5.1),
    height=0.45,
    color=TEXT_COLOR,
    colorSpace="rgb",
    units="cm",
)
visible_label = visual.TextStim(
    win=win,
    text="Veo el estímulo\ncon total claridad",
    pos=(-10.9, 3.45),
    height=0.34,
    color=TEXT_COLOR,
    colorSpace="rgb",
    units="cm",
    wrapWidth=4.2,
    alignText="center",
)
invisible_label = visual.TextStim(
    win=win,
    text="No veo\nel estímulo",
    pos=(-10.5, -3.55),
    height=0.34,
    color=TEXT_COLOR,
    colorSpace="rgb",
    units="cm",
    wrapWidth=3.8,
    alignText="center",
)
tet_trace = visual.ShapeStim(
    win=win,
    vertices=[(0.0, 0.0), (0.1, 0.1)],
    closeShape=False,
    lineColor=TRACE_COLOR,
    lineWidth=2,
    units="cm",
)

peripheral_target_pos = pol2cart(TARGET_ECC_CM, TARGET_ANGLE_DEG)
near_fixation_target_pos = pol2cart(CONTROL_TARGET_ECC_CM, TARGET_ANGLE_DEG)

run_internal_protocol_validations()


# =========================================================
# INPUT DEVICES
# =========================================================
response_keyboard = keyboard.Keyboard()
key_state_handler = make_key_state_handler(win)
ensure_not_pressed(key_state_handler, ["space", "up", "down"])
rating_device = SerialRatingDevice()
device_startup_warning = ""
if DEVICE_RATING and not rating_device.connected:
    if DEVICE_ALLOW_KEYBOARD_FALLBACK:
        device_startup_warning = (
            "No se pudo conectar el potenciómetro. Se usará UP/DOWN como respaldo."
        )
    else:
        raise RuntimeError(
            f"Potenciometro no disponible en {DEVICE_SERIAL_PORT} "
            f"({rating_device.error or rating_device.status})."
        )


# =========================================================
# RUN EXPERIMENT
# =========================================================
rng = random.Random()

show_standardized_instructions()
show_static_display_example()
show_demo()

next_trial_index = 1
total_blocks = len(block_sequence)
for block_index, block_type in enumerate(block_sequence, start=1):
    if block_type == "button":
        show_button_block_instructions(block_index, total_blocks)
        run_button_practice(block_index, total_blocks)
        run_standard_experimental_block(
            block_type=block_type,
            block_index=block_index,
            starting_trial_index=next_trial_index,
            rng=rng,
        )
    elif block_type == "potentiometer":
        show_potentiometer_block_instructions(block_index, total_blocks)
        run_potentiometer_calibration(block_index=block_index)
        run_potentiometer_practice(block_index, total_blocks)
        run_standard_experimental_block(
            block_type=block_type,
            block_index=block_index,
            starting_trial_index=next_trial_index,
            rng=rng,
        )
    elif block_type == "tet":
        show_tet_block_instructions(block_index, total_blocks)
        run_tet_practice()
        run_tet_experimental_block(
            block_index=block_index,
            total_blocks=total_blocks,
            starting_trial_index=next_trial_index,
            rng=rng,
        )
    else:
        raise ValueError(f"Unsupported block type in block sequence: {block_type}")
    if block_index < total_blocks:
        show_block_complete_screen()
    next_trial_index += BLOCK_SIZE


# =========================================================
# SAVE DATA
# =========================================================
if not TEST_MODE:
    record_counterbalance_assignment(
        participant_id=participant_id,
        participant_age=participant_age,
        participant_gender=participant_gender,
        assigned_order=assigned_order,
    )

session_summary_rows = [
    {
        "session_id": SESSION_ID,
        "run_mode": RUN_MODE,
        "data_dir": DATA_DIR,
        "participant_data_dir": PARTICIPANT_DATA_DIR,
        "session_data_dir": PARTICIPANT_DATA_DIR,
        "participant_id": participant_id,
        "participant_age": participant_age,
        "participant_gender": participant_gender,
        "assigned_order": assigned_order,
        "include_potentiometer_block": int(INCLUDE_POTENTIOMETER_BLOCK),
        "show_potentiometer_bar_in_calibration": int(
            SHOW_POTENTIOMETER_BAR_IN_CALIBRATION
        ),
        "show_potentiometer_bar_in_experimental_block": int(
            SHOW_POTENTIOMETER_BAR_IN_EXPERIMENTAL_BLOCK
        ),
        "show_intertrial_break_screen": int(SHOW_INTERTRIAL_BREAK_SCREEN),
        "counterbalance_rule": counterbalance_rule,
        "forced_block_order_raw": FORCE_BLOCK_ORDER_RAW,
        "consent_confirmed": 0,
        "experimental_blocks": len(block_sequence),
        "block_size": BLOCK_SIZE,
        "practice_trials_per_block": PRACTICE_TRIALS_PER_BLOCK,
        "trial_duration_s": f"{TRIAL_DURATION:.3f}",
        "practice_trial_duration_s": f"{PRACTICE_TRIAL_DURATION:.3f}",
        "include_no_target_trials": int(INCLUDE_NO_TARGET_TRIALS),
        "peripheral_trials_per_block": PERIPHERAL_TRIALS_PER_BLOCK,
        "no_target_trials_per_block": NO_TARGET_TRIALS_PER_BLOCK,
        "control_trials_per_block": STATIC_MASK_TRIALS_PER_BLOCK,
        "control_trial_mode": CONTROL_TRIAL_MODE,
        "control_target_ecc_cm": f"{CONTROL_TARGET_ECC_CM:.3f}",
        "demo_duration_s": f"{DEMO_DURATION:.3f}",
        "tet_practice_trial_duration_s": f"{TET_PRACTICE_TRIAL_DURATION:.3f}",
        "tet_experimental_display_duration_s": f"{TET_EXPERIMENTAL_DISPLAY_DURATION:.3f}",
        "tet_experimental_trials": BLOCK_SIZE if "tet" in block_sequence else 0,
        "calibration_duration_s": f"{CALIBRATION_DURATION:.3f}",
        "sinusoidal_calibration_duration_s": f"{SINUSOIDAL_CALIBRATION_DURATION:.3f}",
        "sinusoidal_calibration_hz": f"{SINUSOIDAL_CALIBRATION_HZ:.6f}",
        "monitor_width_cm": f"{MONITOR_WIDTH_CM:.3f}",
        "viewing_distance_cm": f"{VIEWING_DISTANCE_CM:.3f}",
        "monitor_resolution_px": f"{MONITOR_RES[0]}x{MONITOR_RES[1]}",
        "monitor_width_from_env": int(MONITOR_WIDTH_CM_FROM_ENV),
        "monitor_resolution_from_env": int(MONITOR_RES_FROM_ENV),
        "use_detected_fullscreen_resolution": int(USE_DETECTED_FULLSCREEN_RESOLUTION),
        "monitor_name": MONITOR_NAME,
        "monitor_saved": int(monitor_saved),
        "monitor_save_error": monitor_save_error,
        "device_rating_enabled": int(DEVICE_RATING),
        "device_rating_port": DEVICE_SERIAL_PORT,
        "device_rating_baud": DEVICE_SERIAL_BAUD,
        "device_query_char": DEVICE_QUERY_CHAR,
        "response_log_hz": f"{RESPONSE_LOG_HZ:.6f}",
        "device_query_hz": f"{DEVICE_QUERY_HZ:.6f}",
        "device_rating_connected": int(rating_device.connected),
        "device_rating_status": rating_device.status,
        "device_rating_error": rating_device.error,
        "device_rating_level_min": DEVICE_LEVEL_MIN,
        "device_rating_level_max": DEVICE_LEVEL_MAX,
        "device_rating_keyboard_fallback": int(DEVICE_ALLOW_KEYBOARD_FALLBACK),
        "device_startup_warning": device_startup_warning,
        "measured_refresh_hz": "" if measured_fps is None else f"{measured_fps:.6f}",
        "fps_warning": fps_warning,
        "counterbalance_file": COUNTERBALANCE_FILE,
        "button_events_file": BUTTON_EVENTS_FILE,
        "continuous_file": CONTINUOUS_FILE,
        "tet_file": TET_FILE,
        "trial_summary_file": TRIAL_SUMMARY_FILE,
    }
]

write_csv_rows(
    SESSION_SUMMARY_FILE,
    list(session_summary_rows[0].keys()),
    session_summary_rows,
)


# =========================================================
# FINAL SCREEN AND CONSOLE OUTPUT
# =========================================================
show_message_and_wait(
    "La tarea ha terminado. Puedes llamar al experimentador.\n\n"
    "Gracias por participar.\n\n"
    "Pulsa ESPACIO para salir."
)

print("\n=== Blocked MIB task saved files ===")
print(f"Session summary: {SESSION_SUMMARY_FILE}")
print(f"Trial summary: {TRIAL_SUMMARY_FILE}")
print(f"Button events: {BUTTON_EVENTS_FILE}")
print(f"Continuous responses: {CONTINUOUS_FILE}")
print(f"TET traces: {TET_FILE}")
print(f"Counterbalance file: {COUNTERBALANCE_FILE}")
print(f"Assigned order: {assigned_order}")
print(f"Participant ID: {participant_id}")
if measured_fps is None:
    print("Refresh estimate: unavailable")
else:
    print(f"Refresh estimate: {measured_fps:.2f} Hz")
if fps_warning:
    print(f"FPS warning: {fps_warning}")
if monitor_save_error:
    print(f"Monitor warning: {monitor_save_error}")
if device_startup_warning:
    print(f"Device warning: {device_startup_warning}")
if DEVICE_RATING:
    print(f"Device status: {rating_device.status}")
    if rating_device.error:
        print(f"Device error: {rating_device.error}")

close_rating_device()
win.close()
core.quit()

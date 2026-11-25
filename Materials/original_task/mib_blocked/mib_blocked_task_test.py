# -*- coding: utf-8 -*-
"""
Short launcher for the blocked MIB task in test mode.
"""

import os
import runpy
from pathlib import Path


os.environ["MIB_BLOCKED_RUN_MODE"] = "test"
runpy.run_path(
    str(Path(__file__).with_name("mib_blocked_task.py")),
    run_name="__main__",
)

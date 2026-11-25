# -*- coding: utf-8 -*-
"""
Unified launcher for MIB blocked task modes.

Usage:
    python run_mib_blocked.py --mode test
    python run_mib_blocked.py --mode full
"""

import argparse
import os
import runpy
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Run MIB blocked task.")
    parser.add_argument(
        "--mode",
        choices=["test", "full"],
        default="full",
        help="Execution mode.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    blocked_script = project_root / "mib_blocked" / "mib_blocked_task.py"

    if not blocked_script.exists():
        raise FileNotFoundError(f"MIB blocked task script not found: {blocked_script}")

    os.environ["MIB_BLOCKED_RUN_MODE"] = args.mode
    runpy.run_path(str(blocked_script), run_name="__main__")


if __name__ == "__main__":
    main()

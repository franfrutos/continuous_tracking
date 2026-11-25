#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Motion-induced blindness (MIB) task with three methods to report the visibility
of the target: a button, a slider and temporal experience tracing (TET). Run it
with run_task.bat, from PsychoPy (Coder: Run) or with the PsychoPy Python.
Settings are in task/init.py; see README.md.
"""

import os
import sys

from psychopy import core

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # task/ next to this file, from any working folder
from task.experiment import AUTO, Experiment, session_dialog

if __name__ == "__main__":
    if AUTO:  # code check (MIB_AUTO=1): no form, automatic responses
        participant, demographics = int(os.environ.get("MIB_PARTICIPANT", 9000)), {"age": 20, "gender": "Prefiero no decir"}
    else:
        participant, demographics = session_dialog()
    Experiment(participant, demographics).run()
    core.quit()

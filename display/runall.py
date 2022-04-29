"""Use this run a complete behavioral subject.
It runs the empathic accuracy task before and after
an intervention task. The intervention task is picked
based on the subject number being odd or even.
"""
import json
import argparse

from bct import BreathCountingTask
from svp import SerialVisualPresentation

with open("./config.json", "r", encoding="utf-8") as f:
    C = json.load(f)
    task_length = C["task_length_mins"]

parser = argparse.ArgumentParser()
parser.add_argument("--subject", type=int, required=True)
parser.add_argument("--session", type=int, default=1)
args = parser.parse_args()

subject_number = args.subject
session_number = args.session

assert 1 <= subject_number <= 999, "Subject number needs to be between 1 and 999."
assert 1 <= session_number <= 999, "Session number needs to be between 1 and 999."

if subject_number % 2 == 0: # even subject numbers
    game1 = SerialVisualPresentation(subject_number, session_number, task_length_mins=task_length)
    game2 = BreathCountingTask(subject_number, session_number, task_length_mins=task_length)
else:
    game1 = BreathCountingTask(subject_number, session_number, task_length_mins=task_length)
    game2 = SerialVisualPresentation(subject_number, session_number, task_length_mins=task_length)

game1.run()
game2.run()

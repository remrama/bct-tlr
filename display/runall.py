"""Use this run a complete behavioral subject pre or post.
"""
import json
import argparse

from bct import BreathCountingTask
from svp import SerialVisualPresentation
from soc import StreamOfConsciousness
from mwt import MindWanderingTask

with open("./config.json", "r", encoding="utf-8") as f:
    C = json.load(f)
    bct_task_length = C["task_length-bct"]
    svp_task_length = C["task_length-svp"]
    mwt_task_length = C["task_length-mwt"]
    soc_task_length = C["task_length-soc"]

parser = argparse.ArgumentParser()
parser.add_argument("--subject", type=int, required=True)
parser.add_argument("--session", type=int, default=1)
parser.add_argument("--acq", type=str, default="pre", choices=["pre", "post"])
parser.add_argument("--room", type=int, default=207, choices=[0, 207])
parser.add_argument("--mwt", action="store_true", help="Run mind-wandering task.")
parser.add_argument("--soc", action="store_true", help="Run stream-of-consciousness task.")
args = parser.parse_args()

subject_number = args.subject
session_number = args.session
acquisition_code = args.acq
room_number = args.room
run_mindwandering = args.mwt
run_streamofconsciousness = args.soc

assert 1 <= subject_number <= 999, "Subject number needs to be between 1 and 999."
assert 1 <= session_number <= 999, "Session number needs to be between 1 and 999."

svp_game = SerialVisualPresentation(subject_number, session_number, acquisition_code, room_number)
bct_game = BreathCountingTask(subject_number, session_number, acquisition_code, room_number)

if subject_number % 2 == 0: # even subject numbers
    svp_game.run()
    bct_game.run()
else:
    bct_game.run()
    svp_game.run()

if run_mindwandering:
    mwt_game = MindWanderingTask(subject_number, session_number, acquisition_code, room_number)
    mwt_game.run()

if run_streamofconsciousness:
    soc_game = StreamOfConsciousness(subject_number, session_number, acquisition_code, room_number)
    soc_game.run()
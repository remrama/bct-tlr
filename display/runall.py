"""Use this run a complete behavioral subject.
It runs the empathic accuracy task before and after
an intervention task. The intervention task is picked
based on the subject number being odd or even.
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
parser.add_argument("--pre", action="store_true")
parser.add_argument("--post", action="store_true")
args = parser.parse_args()

subject_number = args.subject
session_number = args.session
presleep = args.pre
postsleep = args.post

assert (presleep or postsleep) and not (presleep and postsleep), "Must choose one of pre or post."
assert 1 <= subject_number <= 999, "Subject number needs to be between 1 and 999."
assert 1 <= session_number <= 999, "Session number needs to be between 1 and 999."

if subject_number % 2 == 0: # even subject numbers
    game1 = SerialVisualPresentation(subject_number, session_number)
    game2 = BreathCountingTask(subject_number, session_number)
 else:
    game1 = BreathCountingTask(subject_number, session_number)
    game2 = SerialVisualPresentation(subject_number, session_number)
game3 = MindWanderingTask(subject_number, session_number)
game4 = StreamOfConsciousness(subject_number, session_number)

game1.run()
game2.run()
game3.run()
game4.run()
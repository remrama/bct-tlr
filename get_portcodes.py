"""
The EEG events file will come from the raw neuroscan EEG file,
but to get event ID codes, need to parse this GUI log.

So might end up as a single function used within
source2raw-eeg.py

NO, need to get ALL portcodes, from behavioral scripts
and GUI.

Actually, YES. These portcodes should be loaded separately
since they will apply to different files?
Or maybe not if all data is collected together.
Still, have separate functions that can be merged.

"""

from pathlib import Path

import pandas as pd

import utils

import dmlab

participant_id = "sub-902"
session_id = "ses-001"
def get_portcodes(
        participant_id,
        session_id="ses-001",
        task_id="task-sleep",
    ):

    source_dir = utils.config.get("Paths", "source")

    if task_id == "task-sleep":
        #### Get event codes from TWC GUI log.

        tmr_log_path = Path(source_dir).joinpath(
            participant_id,
            f"{participant_id}_{session_id}_tmr.log",
        )

        tmr = pd.read_csv(tmr_log_path, sep=" - ", engine="python",
            names=["timestamp", "entities", "msg_level", "msg"])

        # legend_str = tmr.query("msg.str.startswith('Portcode legend')")["msg"].values[0]
        # legend_str = legend_str.split("Portcode legend: ")[1]
        # import json
        # tmr_codes = json.loads(legend_str)

        # Reduce to only events with portcodes
        tmr = tmr.query("~msg.str.startswith('Portcode legend')")

        events = tmr.query("msg.str.contains('Portcode')")
        assert events["msg"].str.contains("sent").all()
        cues = events.query("msg.str.contains('played')")

        cue_list = cues["msg"].tolist()
        codes = { x[4:].split(" ")[0]: x.split("Portcode ")[1][:-5] for x in cue_list }
        codes = { f"cue-{k}": int(v) for k, v in codes.items() }

    else:
        # must be a behavior one

        # beh_portcode_paths = Path(source_dir).joinpath(participant_id
        #     ).glob(f"{participant_id}_{session_id}_task-*_acq-pre_portcodes.json")
        task_portcode_path = Path(source_dir).joinpath(
            participant_id
            f"{participant_id}_{session_id}_{task_id}_acq-pre_portcodes.json",
        )
        #### Get event codes from behavior files.
        # beh_codes = {}
        # for filepath in beh_portcode_paths:
        #     task_codes = dmlab.io.load_json(filepath)
        #     beh_codes.update(task_codes)
        codes = dmlab.io.load_json(task_portcode_path)

    # Flip so portcode is the key and description the value.
    # And sort.
    # all_codes = beh_codes | cue_codes
    codes = { v: k for k, v in codes.items() }
    codes = { k: codes[k] for k in sorted(codes) }
    return codes
    
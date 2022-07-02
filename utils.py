"""Helper functions"""

# Add development dir while working on dmlab.
import sys
sys.path.append("C:/Users/malle/packages/dmlab")

import configparser
import json
from pathlib import Path

import pandas as pd

import dmlab


# Load configuration file so it's accessible from utils
config = configparser.ConfigParser(converters={"list": json.loads})
config.read("./config.ini")


def load_participants_file():
    bids_root = config.get("Paths", "bids_root")
    filepath = Path(bids_root) / "participants.tsv"
    return pd.read_csv(filepath, index_col="participant_id", sep="\t")


####################################### Portcode functions

def get_tmr_codes(participant, session):
    #### Get event codes from TWC GUI log.

    source_dir = config.get("Paths", "source")
    tmr_log_path = Path(source_dir).joinpath(
        f"sub-{participant:03d}",
        f"sub-{participant:03d}_ses-{session:03d}_tmr.log",
    )

    ser = pd.read_csv(tmr_log_path,
        names=["timestamp", "msg_level", "msg"],
        usecols=["timestamp", "msg"], index_col="timestamp",
        parse_dates=["timestamp"]
    ).squeeze("columns"
    ).str.strip()

    # Reduce to only events with portcodes
    assert not ser.str.contains("Failed portcode").any()
    ser = ser[ser.str.contains("Sent portcode")]

    codes = {}
    for timestamp, msg in ser.items():
        if "cue" in msg:
            description, _, portcode_str = msg.split(" - ")
        else:
            description, portcode_str = msg.split(" - ")
        portcode = int(portcode_str.split()[-1])

        # Ignore portcodes for stopping cues and dream reports.
        if description.startswith("Stopped"):
            continue
        elif description.startswith("Played cue"):
            description = description.split()[-1]

        if portcode in codes:
            assert codes[portcode] == description
        else:
            codes[portcode] = description

    codes = { k: codes[k] for k in sorted(codes) }

    ## Getting duration of cues.
    ## Need to figure out how to match with timed EEG file.
    # df = ser[ser.str.contains("cue")].to_frame()
    # df["s"] = df.index
    # df.s.diff().dt.total_seconds().shift(-1)[::2]
    return codes


def get_beh_codes(participant, session):
    # All behavior json code files are the same.
    # They save out codes for all the tasks so just grab BCT pre arbitrarily.
    source_dir = config.get("Paths", "source")
    beh_code_path = Path(source_dir).joinpath(
        f"sub-{participant:03d}",
        f"sub-{participant:03d}_ses-{session:03d}_task-bct_acq-pre_portcodes.json",
    )
    codes = dmlab.io.load_json(beh_code_path)
    # Flip so portcode is the key and description the value.
    # And sort.
    codes = { v: k for k, v in codes.items() }
    codes = { k: codes[k] for k in sorted(codes) }
    return codes

def get_all_portcodes(participant, session):
    tmr_codes = get_tmr_codes(participant, session)
    beh_codes = get_beh_codes(participant, session)
    all_codes = beh_codes | tmr_codes
    assert len(all_codes) == len(tmr_codes) + len(beh_codes)
    return { k: all_codes[k] for k in sorted(all_codes) }


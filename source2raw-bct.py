"""Clean the BCT task data.
Go from raw psychopy log file output to usable dataframe in BIDS format.
"""
import json

from pathlib import Path

from bids.layout import parse_file_entities
import pandas as pd

import utils



ROOT_DIR = utils.ROOT_DIR
SOURCE_DIR = utils.SOURCE_DIR

# file_list = utils.find_source_files("bct", "json")
filepaths = SOURCE_DIR.glob("sub-*/sub-*_task-bct_acq-*_psychopy.log")

# global_metadata = utils.load_config(as_object=False)["global_bids_metadata"]
global_metadata = {
    "InstitutionName": "Northwestern University",
    "InstitutionDepartmentName": "Department of Psychology"
}

task_metadata = {
    "TaskName": "Breath Counting Task",
    "TaskDescription": "",
    "Instructions": [
        "line 1",
        "line 2"
    ]
}

column_metadata = {

    "cycle": {
        "LongName": "Cycle count",
        "Description": "Indicates the cycle number, which ends on either a target or reset press."
    },

    "press": {
        "LongName": "Press count",
        "Description": "Indicates the press count within each cycle",
        "Levels": {
            "nontarget": "Breaths 1-8",
            "target": "Breath 9"
        }
    },

    "response": {
        "LongName": "Button response",
        "Description": "Indicator of what button was pushed",
        "Levels": {
            "left": "participant estimated a nontarget trial",
            "right": "participant estimated a target trial",
            "space": "participant lost count and reset counter"
        }
    },

    "response_time": {
        "LongName": "Response time (ms)",
        "Description": "Indicator of time (milliseconds) between prior and current response"
    },

    "accuracy": {
        "LongName": "Press accuracy",
        "Description": "Indicator of press-level accuracy",
        "Levels": {
            "correct": "participant responded with target on target breath or nontarget on pre-target breaths",
            "undershoot": "participant responded with target before target breath",
            "overshoot": "participant responded with target or nontarget after target breath",
            "selfcaught": "participant lost count and reset counter"
        }
    },

    # "cycle_accuracy": {
    #     "LongName": "Cycle accuracy",
    #     "Description": "Indicator of cycle-level accuracy",
    #     "dtype": "str",
    #     "Levels": {
    #         "correct": "participant estimated a nontarget trial",
    #         "undershoot": "participant estimated a target trial",
    #         "overshoot": "participant lost count and reset counter",
    #         "selfcaught": "participant lost count and reset counter"
    #     }
    # }

}

# column_names = list(column_metadata.keys())
# column_names.remove("press_accuracy")

sidecar = task_metadata | global_metadata | column_metadata


target = 9
target_response = "right"
nontarget_response = "left"
reset_response = "space"
def press_accuracy(row):
    """Works as cycle accuracy too if take last row of each cycle.
    """
    if row["response"] == "reset":
        return "selfcaught"
    elif row["response"] == "target" and row["press"] == target:
        return "correct"
    elif row["press"] > target:
        return "overshoot"
    elif row["press"] == target and row["response"] == "nontarget":
        return "overshoot"
    elif row["press"] < target and row["response"] == "nontarget":
        return "correct"
    elif row["press"] < target and row["response"] == "target":
        return "undershoot"
    else:
        raise ValueError("Should never get here")



for fp in filepaths:

    sub_number = int(fp.parts[-2].split("-")[1])
    if 900 < sub_number < 907:
        continue

    # Load data.
    df = pd.read_csv(fp, sep="\t", names=["timestamp", "level", "info"])
    df["level"] = df["level"].str.strip()  # psychopy has a space after these for some reason

    # Restrict to after the task started and before it ended.
    assert df["info"].eq("Main task started").sum() == 1
    assert df["info"].eq("Main task ended").sum() == 1
    start_msg_row = df["info"].eq("Main task started").argmax()
    end_msg_row = df["info"].eq("Main task ended").argmax()
    starttime = df.loc[start_msg_row, "timestamp"]
    df = df[start_msg_row+1:end_msg_row]

    # Get rid of non-data and button-up messages (so it's only button presses)
    df = df.query("level=='DATA'")

    # Sometimes there are different amounts of spaces between words in info.
    # Get rid of excess text to avoid this.
    ## I pressed mouse once for 909 :/// during task :////
    if sub_number == 909:
        df = df[df["info"].str.startswith("Keypress:")]
        # and they pushed down but it's like 8 ms after a press so doesn't count (and didn't move press count forward)
        df = df[df["info"].ne("Keypress: down")]
    assert df["info"].str.startswith("Keypress:").all()
    df["info"] = df["info"].str.split("Keypress: ").str[1].str.strip()

    # Add columns
    cycle_counter = 1
    def cycle_incrementer(x):
        global cycle_counter
        if x == target_response:
            cycle_counter += 1
        return cycle_counter
    df["cycle"] = df["info"].shift(1, fill_value=nontarget_response).apply(cycle_incrementer)

    press_counter = 0
    def press_cycler(x):
        global press_counter
        if x == nontarget_response:
            press_counter += 1
        else:
            press_counter = 1
        return press_counter

    # Shift forward to look behind.
    df["press"] = df["info"].shift(1, fill_value=nontarget_response).apply(press_cycler)

    # # Convert timestamp to response time?
    # df["response_time"] = df["response_time"].diff().fillna(df["response_time"][0]).mul(1000)

    # Remove final trial if it wasn't finished.
    n_cycles = df["cycle"].max()
    if not df.query(f"cycle.eq({n_cycles})")["info"].is_unique:
        df = df.query(f"cycle.lt({n_cycles})")

    df = df.rename(columns={"info": "response"})
    # df["response"] = df["response"].str.lower()
    df["response"] = df["response"].replace(
        {
            nontarget_response: "nontarget",
            target_response: "target",
            reset_response: "reset",
        }
    )

    df["timestamp"] = df["timestamp"].sub(starttime)
    df["accuracy"] = df.apply(press_accuracy, axis=1)
    
    df = df[["cycle", "press", "response", "timestamp", "accuracy"]]

    entities = parse_file_entities(fp)
    subject_id = "sub-" + entities["subject"]
    task_id = "task-" + entities["task"]
    acquisition_id = "acq-" + entities["acquisition"]
    suffix_id = "beh"

    stem = "_".join([subject_id, task_id, acquisition_id, suffix_id])
    export_path = ROOT_DIR / subject_id / suffix_id / f"{stem}.tsv"
    utils.export_tsv(df, export_path, index=False)
    utils.export_json(sidecar, export_path.with_suffix(".json"))

    # with open(file, "r", encoding="utf-8") as f:
    #     subject_data = json.load(f)
    # # convert cycle number strings to integers
    # subject_data = { int(k): v for k, v in subject_data.items() }
    # # remove practice cycles
    # subject_data = { k: v for k, v in subject_data.items() if k < 900 }
    # # remove final trial if it wasn't finished
    # subject_data = { k: v for k, v in subject_data.items() if len(v) > 0 and v[-1][0] != "left" }
    # # wrangle data
    # cycle_list = [ v for v in subject_data.values() ]
    # rows = [ [i+1, j+1] + resp for i, cycle in enumerate(cycle_list) for j, resp in enumerate(cycle) ]
    # df = pd.DataFrame(rows, columns=column_names)
    # df["response_time"] = df["response_time"].diff().fillna(df["response_time"][0]).mul(1000)
    # # [ r0[:3]+[r1[3]-r0[3]] for r0, r1 in zip(rows[:-1], rows[1:]) ]
    # sub, ses, task = utils.filename2labels(file)
    # basename = os.path.basename(file).replace(".json", "_beh.tsv").replace("_ses-001", "")
    # data_filepath = os.path.join(utils.load_config().bids_root, sub, "beh", basename)
    # utils.make_pathdir_if_not_exists(data_filepath)
    # df.to_csv(data_filepath, index=False, sep="\t", float_format="%.0f")
    # utils.pretty_sidecar_export(sidecar, data_filepath)


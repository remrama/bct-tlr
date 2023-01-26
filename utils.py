"""Global parameters and helper functions."""

from datetime import timezone
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


################################################################################
# GLOBAL PARAMETERS
################################################################################


# Directories
ROOT_DIR = Path("~/PROJECTS/bct-tmr").expanduser()
SOURCE_DIR = ROOT_DIR / "sourcedata"
DERIVATIVES_DIR = ROOT_DIR / "derivatives"
STIMULI_DIR = ROOT_DIR / "stimuli"

# PSG
EEG_SOURCE_EXTENSION = ".cnt"
EEG_RAW_EXTENSION = ".fif"
EEG_CHANNELS = ["Fz", "Cz", "Oz"]
EOG_CHANNELS = ["L-VEOG", "R-HEOG"]
ECG_CHANNELS = ["HR"]
EMG_CHANNELS = ["EMG"]
MISC_CHANNELS = ["L-MSTD", "Airflow", "Snoring", "RESP"]
# REFERENCE_CHANNEL = "R-MSTD"
# GROUND_CHANNEL = "Fpz"
NOTCH_FREQUENCY = 60

MNE_VERBOSITY = False


################################################################################
# MISCELLANEOUS
################################################################################


def import_json(filepath: str, **kwargs) -> dict:
    """Loads json file as a dictionary"""
    with open(filepath, "rt", encoding="utf-8") as fp:
        return json.load(fp, **kwargs)

def export_json(obj: dict, filepath: str, mode: str="wt", **kwargs):
    kwargs = {"indent": 4} | kwargs
    with open(filepath, mode, encoding="utf-8") as fp:
        json.dump(obj, fp, **kwargs)

def export_tsv(df, filepath, mkdir=True, **kwargs):
    kwargs = {"sep": "\t", "na_rep": "n/a"} | kwargs
    if mkdir:
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, **kwargs)

def export_mpl(filepath, mkdir=True, close=True):
    filepath = Path(filepath)
    if mkdir:
        filepath.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(filepath)
    plt.savefig(filepath.with_suffix(".pdf"))
    if close:
        plt.close()

def load_participants_file():
    filepath = ROOT_DIR / "participants.tsv"
    df = pd.read_csv(filepath, index_col="participant_id", parse_dates=["measurement_date"], sep="\t")
    # MNE wants UTC and check fails if UTC is a string rather than datetime timezone.
    # https://github.com/mne-tools/mne-python/blob/3c23f13c0262118d075de0719248409bdc838982/mne/utils/numerics.py#L1036
    df["measurement_date"] = df["measurement_date"].dt.tz_localize("US/Central").dt.tz_convert(timezone.utc)
    return df


################################################################################
# SMACC LOG PROCESSING
################################################################################

def read_smacc_log(filepath):
    # early_subject = "sub-90" in filepath.name
    df = pd.read_csv(filepath, names=["timestamp", "msg_level", "msg"], parse_dates=["timestamp"])
    # Localize timestamp.
    df["timestamp"] = df["timestamp"].dt.tz_localize("US/Central").dt.tz_convert(timezone.utc)
    # Remove excess whitespace.
    df["msg"] = df["msg"].str.strip()
    # Drop msg_level column (useless because always "INFO")
    df = df.drop(columns="msg_level")
    # Drop some rows that are useless.
    df = df[df.msg.ne("Opened TWC interface v0.0")]
    df = df[df.msg.ne("Program closed")]
    df = df[~df.msg.str.contains("VolumeSet")]
    # Reduce to only events with portcodes
    assert not df.msg.str.contains("Failed portcode").any()
    df = df.loc[df.msg.str.contains("Sent portcode")]
    # Expand single "msg" column to "description" and "value"
    df["value"] = df.msg.str.split(" - ").str[-1].str.split().str[-1].astype(int)
    df["description"] = df.msg.str.split(" - ").str[0].str.split("-").str[0]
    df["stim_file"] = df.msg.str.split(" - ").str[0].str.split("-").str[1].add(".wav")
    df["trial_type"] = np.nan
    df.loc[df.stim_file.str.startswith("lux3").fillna(False), "trial_type"] = "bct"
    df.loc[df.stim_file.str.startswith("med1").fillna(False), "trial_type"] = "mwt"
    # df["trial_type"] = df.msg.str.split("CueStarted-").str[1].str.split("_").str[0].replace({"lux3": "bct", "med1": "mwt"})
    # Get duration of each cue (this ASSUMES there is a start for every stop)
    assert df.msg.str.contains("CueStarted").sum() == df.msg.str.contains("CueStarted").sum(), "Make sure each cue has both start and stop messages."
    assert df.msg.str.contains("DreamReportStarted").sum() == df.msg.str.contains("DreamReportStopped").sum(), "Make sure each dream report has both start and stop messages."
    df["duration"] = df["timestamp"].diff().dt.total_seconds().shift(-1)
    df.loc[~df.description.isin(["CueStarted", "DreamReportStarted"]), "duration"] = np.nan
    # Now able to drop the Stopped codes.
    df = df.loc[~df.msg.str.contains("Stopped")]
    df["description"] = df.description.str.rsplit("Started").str[0]
    # Add *initial* volume for cues.
    df["volume"] = df.msg.str.split("Volume ").str[1].str.split(" - ").str[0]
    df.loc[df.description.str.startswith("Parallel port connection"), "description"] = "CONNECTION"
    # df["description"] = df["description"].replace({"Parallel port connection succeeded.": "CONNECTION"})
    df = df.drop(columns="msg")
    # Remove cues from before lights were out??

    # Check some expectations.
    assert df.description.value_counts().at["CONNECTION"] == 1

    return df.reset_index(drop=True).sort_values("timestamp")



################################################################################
# PORTCODE EXTRACTION
################################################################################


# def get_smacc_codes(filepath):
#     """Get {code: description} event codes from SMACC log file."""
#     return read_smacc_log(filepath).set_index("value").description.to_dict()

    # df = read_smacc_log(filepath)
    # # Combine columns to get back unique portcode identifiers.
    # df["code_description"] = df[["description", "stim_file"]].fillna("").agg("-".join, axis=1).str.rstrip("-")
    # assert df.groupby("value").code_description.nunique().eq(1).all(), "All portcode values must have unique descriptions."
    # ser = df.set_index("value").description.to_dict()
    # return ser

    # event_id = 
    # df = read_smacc_log(filepath)
    # ser = df.set_index("timestamp")["msg"]
    # codes = {}
    # for timestamp, msg in ser.items():
    #     if msg.startswith("Cue"):
    #         description, _, portcode_str = msg.split(" - ")
    #     else:
    #         description, portcode_str = msg.split(" - ")
    #     portcode = int(portcode_str.split()[-1])
    #     # Portcodes for cue stopping will be same code but different descriptions.
    #     if description.startswith("CueStopped"):
    #         description = "CueStopped"
    #     # elif description.startswith("Played cue"):
    #     #     description = description.split()[-1]
    #     if portcode in codes:
    #         assert codes[portcode] == description, f"{portcode} has varying descriptions, here it was {description}"
    #     else:
    #         codes[portcode] = description
    # codes = { k: codes[k] for k in sorted(codes) }
    # return codes

# def get_beh_codes(participant, session):
#     # All behavior json code files are the same.
#     # They save out codes for all the tasks so just grab BCT pre arbitrarily.
#     source_dir = config.get("Paths", "source")
#     beh_code_path = Path(source_dir).joinpath(
#         f"sub-{participant:03d}",
#         f"sub-{participant:03d}_ses-{session:03d}_task-bct_acq-pre_portcodes.json",
#     )
#     codes = dmlab.io.load_json(beh_code_path)
#     # Flip so portcode is the key and description the value.
#     # And sort.
#     codes = { v: k for k, v in codes.items() }
#     codes = { k: codes[k] for k in sorted(codes) }
#     return codes

# def get_all_portcodes(participant, session):
#     tmr_codes = get_tmr_codes(participant, session)
#     beh_codes = get_beh_codes(participant, session)
#     all_codes = beh_codes | tmr_codes
#     assert len(all_codes) == len(tmr_codes) + len(beh_codes)
#     return { k: all_codes[k] for k in sorted(all_codes) }


################################################################################
# GENERATING BIDS SIDECAR FILES
################################################################################


def generate_eeg_sidecar(
        task_name,
        task_description,
        task_instructions,
        reference_channel,
        ground_channel,
        sampling_frequency,
        recording_duration,
        n_eeg_channels,
        n_eog_channels,
        n_ecg_channels,
        n_emg_channels,
        n_misc_channels,
        **kwargs,
    ):
    return {
        "TaskName": task_name,
        "TaskDescription": task_description,
        "Instructions": task_instructions,
        "InstitutionName": "Northwestern University",
        "Manufacturer": "Neuroscan",
        "ManufacturersModelName": "tbd",
        "CapManufacturer": "tbd",
        "CapManufacturersModelName": "tbd",
        "PowerLineFrequency": 60,
        "EEGPlacementScheme": "10-20",
        "EEGReference": f"single electrode placed on {reference_channel}",
        "EEGGround": f"single electrode placed on {ground_channel}",
        "SamplingFrequency": sampling_frequency,
        "EEGChannelCount": n_eeg_channels,
        "EOGChannelCount": n_eog_channels,
        "ECGChannelCount": n_ecg_channels,
        "EMGChannelCount": n_emg_channels,
        "MiscChannelCount": n_misc_channels,
        "TriggerChannelCount": 0,
        "SoftwareFilters": "tbd",
        "HardwareFilters": {
            "tbd": {
                "tbd": "tbd",
                "tbd": "tbd"
            }
        },
        "RecordingType": "continuous",
        "RecordingDuration": recording_duration,
    } | kwargs

def generate_channels_sidecar(**kwargs):
    return {
        "name": "See BIDS spec",
        "type": "See BIDS spec",
        "units": "See BIDS spec",
        "description": "See BIDS spec",
        "sampling_frequency": "See BIDS spec",
        "reference": "See BIDS spec",
        "low_cutoff": "See BIDS spec",
        "high_cutoff": "See BIDS spec",
        "notch": "See BIDS spec",
        "status": "See BIDS spec",
        "status_description": "See BIDS spec",
        "RespirationHardware": "tbd", # seems like a good thing to add??
    } | kwargs

def generate_events_sidecar(columns, **kwargs):
    column_info = {
        "onset": {
            "LongName": "Onset (in seconds) of the event",
            "Description": "Onset (in seconds) of the event"
        },
        "duration": {
            "LongName": "Duration of the event (measured from onset) in seconds",
            "Description": "Duration of the event (measured from onset) in seconds"
        },
        "value": {
            "LongName": "Marker/trigger value associated with the event",
            "Description": "Marker/trigger value associated with the event"
        },
        "description": {
            "LongName": "Value description",
            "Description": "Readable explanation of value markers column",
        },
        "stim_file": {
            "LongName": "words",
            "Description": "more words",
        },
        "volume": {
            "LongName": "words",
            "Description": "more words",
        },
        "trial_type": {
            "LongName": "General event category",
            "Description": "Very different event types are included, so this clarifies",
            "Levels": {
                "tmr": "A sound cue for targeted memory reactivation",
                "misc": "Things like lights-on lights-off or note"
            }
        }
    }
    info = { c: column_info[c] for c in columns }
    # info["StimulusPresentation"] = {
    #     "OperatingSystem": "Linux Ubuntu 18.04.5",
    #     "SoftwareName": "Psychtoolbox",
    #     "SoftwareRRID": "SCR_002881",
    #     "SoftwareVersion": "3.0.14",
    #     "Code": "doi:10.5281/zenodo.3361717"
    # }
    return info | kwargs


################################################################################
# PLOTTING
################################################################################


def set_matplotlib_style(mpl_style="technical"):
    if mpl_style == "technical":
        # plt.rcParams["figure.dpi"] = 600
        plt.rcParams["savefig.dpi"] = 600
        plt.rcParams["interactive"] = True
        plt.rcParams["figure.constrained_layout.use"] = True
        plt.rcParams["font.family"] = "Times New Roman"
        # plt.rcParams["font.sans-serif"] = "Arial"
        plt.rcParams["mathtext.fontset"] = "custom"
        plt.rcParams["mathtext.rm"] = "Times New Roman"
        plt.rcParams["mathtext.cal"] = "Times New Roman"
        plt.rcParams["mathtext.it"] = "Times New Roman:italic"
        plt.rcParams["mathtext.bf"] = "Times New Roman:bold"
        plt.rcParams["font.size"] = 8
        plt.rcParams["axes.titlesize"] = 8
        plt.rcParams["axes.labelsize"] = 8
        plt.rcParams["axes.labelsize"] = 8
        plt.rcParams["xtick.labelsize"] = 8
        plt.rcParams["ytick.labelsize"] = 8
        plt.rcParams["axes.linewidth"] = 0.8 # edge line width
        plt.rcParams["axes.axisbelow"] = True
        plt.rcParams["axes.grid"] = True
        plt.rcParams["axes.grid.axis"] = "y"
        plt.rcParams["axes.grid.which"] = "major"
        plt.rcParams["axes.labelpad"] = 4
        plt.rcParams["xtick.top"] = True
        plt.rcParams["ytick.right"] = True
        plt.rcParams["xtick.direction"] = "in"
        plt.rcParams["ytick.direction"] = "in"
        plt.rcParams["grid.color"] = "gainsboro"
        plt.rcParams["grid.linewidth"] = 1
        plt.rcParams["grid.alpha"] = 1
        plt.rcParams["legend.frameon"] = False
        plt.rcParams["legend.edgecolor"] = "black"
        plt.rcParams["legend.fontsize"] = 8
        plt.rcParams["legend.title_fontsize"] = 8
        plt.rcParams["legend.borderpad"] = .4
        plt.rcParams["legend.labelspacing"] = .2 # the vertical space between the legend entries
        plt.rcParams["legend.handlelength"] = 2 # the length of the legend lines
        plt.rcParams["legend.handleheight"] = .7 # the height of the legend handle
        plt.rcParams["legend.handletextpad"] = .2 # the space between the legend line and legend text
        plt.rcParams["legend.borderaxespad"] = .5 # the border between the axes and legend edge
        plt.rcParams["legend.columnspacing"] = 1 # the space between the legend line and legend text
    else:
        raise ValueError(f"matplotlib style {mpl_style} is not an option")

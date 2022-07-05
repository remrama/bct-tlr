"""Convert sourcedata .cnt EEG file (Neuroscan)
to multiple raw .fif EEG BIDS-formatted files
and their corresponding information files.

Clean a participant's raw PSG file.
Break it into the different tasks,
preprocess it, rename the triggers,
add sleep stage annotations, etc.

python eeg-cnt2fif.py --subject 1 --session 1
=> sub-001/eeg/sub-001_ses-001_task-nap_eeg.fif
=> sub-001/eeg/sub-001_ses-001_task-nap_eeg.json
=> sub-001/eeg/sub-001_ses-001_task-nap_events.tsv
=> sub-001/eeg/sub-001_ses-001_task-nap_events.json
=> sub-001/eeg/sub-001_ses-001_task-nap_channels.tsv
=> sub-001/eeg/sub-001_ses-001_task-nap_channels.json
=> ... [same for tasks bct and svp]
"""

import argparse
from os import getcwd
from os.path import relpath
from pathlib import Path

import mne
import numpy as np
import pandas as pd
import yasa

import utils

import dmlab


parser = argparse.ArgumentParser()
parser.add_argument("--participant", type=int, default=907)
parser.add_argument("--session", type=int, default=1)
args = parser.parse_args()

participant_number = args.participant
session_number = args.session


#############################################
# Setup
#############################################

# Load parameters from configuration file.
source_dir = utils.config.get("Paths", "source")
raw_dir = utils.config.get("Paths", "raw")
stimuli_dir = utils.config.get("Paths", "stimuli")
eeg_source_extension = utils.config.get("PSG", "source_extension")
eeg_raw_extension = utils.config.get("PSG", "raw_extension")
# reference_channel = utils.config.get("PSG", "reference")
# ground_channel = utils.config.get("PSG", "ground")
notch_frequency = utils.config.getint("PSG", "notch_frequency")
eeg_channels = utils.config.getlist("PSG", "eeg")
eog_channels = utils.config.getlist("PSG", "eog")
misc_channels = utils.config.getlist("PSG", "misc")
ecg_channels = utils.config.getlist("PSG", "ecg")
emg_channels = utils.config.getlist("PSG", "emg")

# Define parameters that require manipulation.
participant_id = f"sub-{participant_number:03d}"
session_id = f"ses-{session_number:03d}"
import_basename = f"{participant_id}_{session_id}_eeg{eeg_source_extension}"
import_path = Path(source_dir) / participant_id / import_basename
participant_parent = Path(raw_dir) / participant_id

# Nap i/o
task = "nap"
eeg_name = f"{participant_id}_task-{task}_eeg{eeg_raw_extension}"
eeg_path = participant_parent / eeg_name
events_path = participant_parent / eeg_path.with_suffix(".tsv").name.replace("_eeg", "_events")
channels_path = participant_parent / eeg_path.with_suffix(".tsv").name.replace("_eeg", "_channels")
# channels_path = str(eeg_path.with_suffix(".tsv")).replace("_eeg", "_channels")
# Sidecar paths can be created on the fly using .with_suffix

# Create participant raw directory if not present already.
participant_parent.mkdir(parents=True, exist_ok=True)

# Load participants file.
participants = utils.load_participants_file()
measurement_date = participants.loc[participant_id, "measurement_date"]

# Load raw Neuroscan EEG file
raw = mne.io.read_raw_cnt(import_path,
    eog=eog_channels, misc=misc_channels,
    ecg=ecg_channels, emg=emg_channels,
    data_format="auto", date_format="mm/dd/yy",
    preload=False, verbose=None)

# Load TMR logfile
tmr_log = utils.load_tmr_logfile(participant_number, session_number)



############################### Preprocessing (minimal)

# # Trim to sleep
# raw.crop(tmin=0, tmax=600)

# # Filter
# # Apply a bandpass filter from 0.1 to 40 Hz
# filter_params = dict(filter_length="auto", method="fir")
# raw.filter(0.1, 40, picks=["eeg", "eog", "emg", "L-MSTD"], **filter_params)
# raw.filter(0.1, 40, picks=["RESP", "Airflow", "Snoring"], **filter_params)
# raw.filter(0.1, 40, picks="ecg", **filter_params)



################################# Generate channel info file

reference_channel = participants.loc[participant_id, "eeg_reference"]
ground_channel = participants.loc[participant_id, "eeg_ground"]


# Compose channels dataframe
# n_total_channels = raw.channel_count
# Convert from MNE FIFF codes
fiff2str = {2: "eeg", 202: "eog", 302: "emg", 402: "ecg", 502: "misc"}
channels_info = {
    "name": [ x["ch_name"] for x in raw.info["chs"] ], # OR raw.ch_names
    "type": [ fiff2str[x["kind"]].upper() for x in raw.info["chs"] ],
    # "types": [ raw.get_channel_types(x)[0].upper() for x in raw.ch_names ],
    "units": [ x["unit"] for x in raw.info["chs"] ],
    "description": "none",
    "sampling_frequency": raw.info["sfreq"],
    "reference": reference_channel,
    "low_cutoff": raw.info["highpass"],
    "high_cutoff": raw.info["lowpass"],
    "notch": notch_frequency,
    "status": "none",
    "status_description": "none",
}

channels_df = pd.DataFrame.from_dict(channels_info)
channels_sidecar = utils.generate_eeg_channels_bids_sidecar()



############################################ Generate EEG sidecar file
eeg_sidecar = utils.generate_eeg_bids_sidecar(
    task_name="nap",
    task_description="Participants went to sleep and TMR cues were played quietly during slow-wave sleep",
    task_instructions="Go to sleep",
    reference_channel=reference_channel,
    ground_channel=ground_channel,
    sampling_frequency=raw.info["sfreq"],
    recording_duration=raw.times[-1],
    n_eeg_channels=len(eeg_channels),
    n_eog_channels=len(eog_channels),
    n_ecg_channels=len(ecg_channels),
    n_emg_channels=len(emg_channels),
    n_misc_channels=len(misc_channels),
)

######### Events

# Load stimuli filenames.
cue_paths = Path(stimuli_dir).glob("*_Cue*.wav")
biocal_paths = Path(stimuli_dir).joinpath("biocals").glob("*.mp3")
stimuli_abspaths = list(cue_paths) + list(biocal_paths)
stimuli_relpaths = [ relpath(p, getcwd()) for p in stimuli_abspaths ]

# Load all the portcodes
event_code2str = utils.get_all_portcodes(participant_number, session_number)
# event_id = { v: k for k, v in event_desc.items() }
## temp fix
# event_code2str[204] = "Note"

# Generate events dataframe
## to_data_frame puts onset as a timestamp which is dumb
## events_df = raw.annotations.to_data_frame()
events_array, event_code2mne = mne.events_from_annotations(raw, verbose=0)
events_df = pd.DataFrame(events_array, columns=["onset", "duration", "value"])

# Manipulate/add info.
# event_mne2code = { v: int(k) for k, v in event_code2mne.items() }
# event_mne2str = { k: event_code2str[v] for k, v in event_mne2code.items() }
event_mne2str = { v: event_code2str[int(k)] for k, v in event_code2mne.items() }
# events_df["value"] = events_df["value"].map(event_mne2code)
events_df["description"] = events_df["value"].map(event_mne2str)

# mne returns onset in unit of sample number, change to seconds
events_df["onset"] /= raw.info["sfreq"]

def get_stim_name(x):
    for p in stimuli_relpaths:
        if x.split("-")[-1] in p:
            return p

events_df["stim_file"] = events_df["description"].apply(get_stim_name)
events_df["description"] = events_df["description"].apply(
    lambda x: x.split("-")[0] if x.split("-")[0] in ["Biocal", "CueStarted"] else x)

events_df["next_description"] = events_df["description"].shift(-1, fill_value="FILL")
events_df["next_onset"] = events_df["onset"].shift(-1, fill_value="FILL")
end_duration_descriptions = ["CueStopped", "DreamReportStopped"]
def get_duration(row):
    if row["next_description"] in end_duration_descriptions:
        return row["next_onset"] - row["onset"]
    else:
        return row["duration"]

events_df["duration"] = events_df.apply(get_duration, axis=1)
events_df = events_df.drop(columns=["next_description", "next_onset"])
events_df = events_df.query(f"~description.isin({end_duration_descriptions})")

# Remove some descriptions/codes we don't care about for now.
events_df = events_df[~events_df["description"].str.split("-").str[1].isin([
    "target", "nontarget", "reset"])]


# # Could get measurement date from participants file,
# # but to get very specific timestamps and link to TMR log file,
# # pick one of the TMR log timestamps arbitrarily and set it
# # relative to that.
# # raw.set_meas_date(measurement_date.to_pydatetime())
# # set_meas_date
# # If datetime object, it must be timezone-aware and in UTC.
# # port_connection_str = tmr_log.query("msg.str.startswith('Parallel port connection succeeded')")["msg"].values[0]
# # port_connection_code = int(port_connection_str.split()[-1])
# events_df["onset_ts"] = pd.NaT
# row_index = events_df["description"].str.startswith("Parallel port connection succeeded")
# events_df.loc[row_index, "onset_ts"] = tmr_log.loc[tmr_log["msg"].str.endswith("200"), "timestamp"].values[0]

# # Remove more don't care about.
# events_df = events_df.query("description.ne('Parallel port connection succeeded.')")


new_unique_values = { d: i+1 for i, d in enumerate(events_df["description"].unique()) }
events_df["value"] = events_df["description"].map(new_unique_values)

# Remove existing annotations (to avoid redundancy).
while raw.annotations:
    raw.annotations.delete(0)

# ## (this might be unsafe)
# raw.annotations.description = np.array([ event_desc[int(x)]
#     for x in raw.annotations.description if int(x) in event_desc ])

events_sidecar = utils.generate_eeg_events_bids_sidecar()





######################################## Break up task files

raw_save_kwargs = dict(fmt="single", overwrite=True)

events = events_df.set_index("description")

# Extract nap. (on/off reversed for 906, change for new subs)
if "LightsOff" in events.index and "LightsOn" in events.index:
    nap_tmin = events.loc["LightsOff", "onset"]
    nap_tmax = events.loc["LightsOn", "onset"]
    ## Save nap data.
    # nap_raw = raw.copy().crop(tmin=nap_tmin, tmax=nap_tmax, include_tmax=True)
    nap_events = events_df.query(f"onset.between({nap_tmin}, {nap_tmax})")
    raw.save(eeg_path, tmin=nap_tmin, tmax=nap_tmax, **raw_save_kwargs)
    dmlab.io.export_dataframe(nap_events, events_path)
    dmlab.io.export_dataframe(channels_df, channels_path)
    dmlab.io.export_json(eeg_sidecar, eeg_path.with_suffix(".json"))
    dmlab.io.export_json(events_sidecar, events_path.with_suffix(".json"))
    dmlab.io.export_json(channels_sidecar, channels_path.with_suffix(".json"))
else:
    raise ValueError("Missing LightsOff and/or LightsOn")

# biocals_tmin = events.loc["Biocals OpenEyes", "onset"]
prenap_events = events.query(f"onset.lt({nap_tmin})")
postnap_events = events.query(f"onset.gt({nap_tmax})")
path_adjuster = lambda p, t, a: p.as_posix().replace("task-nap", f"task-{t}_acq-{p}")

# if "bct-start" in prenap_events.index and "bct-stop" in prenap_events.index:
#     # Extract bct pre.
#     bct_pre_tmin = events.loc["bct-start", "onset"]
#     bct_pre_tmax = events.loc["bct-end", "onset"]
#     raw.save(path_adjuster(eeg_path, "bct", "pre"),
#         tmin=bct_pre_tmin, tmax=bct_pre_tmax, **raw_save_kwargs)



# Extract bct post.
# Extract svp pre.
# Extract svp post.



######################################## Export everything

# Nap


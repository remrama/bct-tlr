"""
Take in original .cnt EEG files (Neuroscan) and:
    - Split into separate task segments (sleep, BCT, MW, SVP)
    - Apply minimal preprocessing (rereferencing, filtering)
    - Export as .fif EEG files
    - Export corresponding metadata for each file (events, channels, and all sidecars)

This also involves loading in and processing the SMACC log files.
"""

from datetime import timezone
import argparse

# from os import getcwd
# from os.path import relpath

import mne
import numpy as np
import pandas as pd
import tqdm
import yasa

import utils


mne.set_log_level(verbose=False)

parser = argparse.ArgumentParser()
parser.add_argument("--participant", type=int, default=907)
parser.add_argument("--session", type=int, default=1)
args = parser.parse_args()

participant = args.participant
session = args.session


################################################################################
# SETUP
################################################################################

# Load parameters from configuration file.
ROOT_DIR = utils.ROOT_DIR
SOURCE_DIR = utils.SOURCE_DIR
DERIVATIVES_DIR = utils.DERIVATIVES_DIR
STIMULI_DIR = utils.STIMULI_DIR

participant_id = f"sub-{participant:03d}"
session_id = f"ses-{session:03d}"

import_name_eeg = f"{participant_id}_{session_id}_eeg" + utils.EEG_SOURCE_EXTENSION
import_name_smacc = f"{participant_id}_{session_id}_tmr.log"
import_path_eeg = SOURCE_DIR / participant_id / import_name_eeg
import_path_smacc = SOURCE_DIR / participant_id / import_name_smacc

# Load participants file.
participants = utils.load_participants_file()
measurement_date = participants.loc[participant_id, "measurement_date"]
reference_channel = participants.at[participant_id, "eeg_reference"]
ground_channel = participants.at[participant_id, "eeg_ground"]

# Load raw Neuroscan EEG file.
raw = mne.io.read_raw_cnt(
    import_path_eeg,
    eog=utils.EOG_CHANNELS,
    misc=utils.MISC_CHANNELS,
    ecg=utils.ECG_CHANNELS,
    emg=utils.EMG_CHANNELS,
    data_format="auto",
    date_format="dd/mm/yy",
    preload=False,
)

# Load TMR logfile.
smacc = utils.read_smacc_log(import_path_smacc)

if participant > 900:
    smacc["trial_type"] = smacc["trial_type"].replace({"mwt": "svp"})

# # Load stimuli filenames.
# cue_paths = STIMULI_DIR.glob("*_Cue*.wav")
# biocal_paths = STIMULI_DIR.joinpath("biocals").glob("*.mp3")
# stimuli_abspaths = list(cue_paths) + list(biocal_paths)
# # stimuli_relpaths = [ relpath(p, getcwd()) for p in stimuli_abspaths ]

# export_stem = f"{participant_id}_task-{task}_eeg"
# export_path_eeg = participant_parent / eeg_name.with_suffix(utils.EEG_RAW_EXTENSION)
# events_path = participant_parent / eeg_path.with_suffix(".tsv").name.replace("_eeg", "_events")
# channels_path = participant_parent / eeg_path.with_suffix(".tsv").name.replace("_eeg", "_channels")
# # channels_path = str(eeg_path.with_suffix(".tsv")).replace("_eeg", "_channels")
# # Sidecar paths can be created on the fly using .with_suffix


################################################################################
# CONSTRUCT EVENTS DATAFRAME
################################################################################

# Load all the portcodes.
smacc_codes = smacc.set_index("value").description.to_dict()
task_codes = {}
task_code_paths = SOURCE_DIR.joinpath(participant_id).glob("*task*_portcodes.json")
for p in task_code_paths:
    desc2val = utils.import_json(p)
    val2desc = { v: k for k, v in desc2val.items() }
    # Remove some descriptions/codes we don't care about for now.
    val2desc = { k: v for k, v in val2desc.items() if v.split("-")[-1] not in ["target", "nontarget", "reset"] }
    task_codes.update(val2desc)
event_codes = task_codes | smacc_codes
event_codes = { k: event_codes[k] for k in sorted(event_codes) }
# Add Note code for temp fix?
# all_codes[204] = "Note"

# unused_ann_indices = [ i for i, a in enumerate(raw.annotations) if int(a["description"]) not in events["value"].values ]
unused_ann_indices = [ i for i, a in enumerate(raw.annotations) if int(a["description"]) not in event_codes ]
raw.annotations.delete(unused_ann_indices)
# assert len(raw.annotations) == len(events)

if participant == 907:
    # Remove first "bct-stop" because there was no start and they redid it later.
    raw.annotations.delete(0)

# Generate events DataFrame from EEG file.
events = raw.annotations.to_data_frame()
# events["timestamp"] = events["onset"].dt.tz_localize("US/Central").dt.tz_convert(timezone.utc)
events["onset"] = raw.annotations.onset  # Seconds from start of file.
events["value"] = events["description"].astype(int)
events["description"] = events["value"].map(event_codes)
# unlabeled_codes = events.loc[events["description"].isna(), "value"].unique().tolist()
# assert not unlabeled_codes, f"Found unlabeled portcodes: {unlabeled_codes}"
# Remove unlabeled portcodes, some are not being used.
# events = events.dropna(subset="description")
# events = events.set_index("description")

# Merge to carry extra info over.
smacc = smacc.set_index(events.query("~description.str.contains('-')").index)
events = events.drop(columns="duration").join(smacc[["duration", "stim_file", "trial_type", "volume"]])
events["duration"] = events["duration"].fillna(0)

# Remove existing annotations in EEG raw file to avoid redundancy with events file and remove unwanted.
while raw.annotations:
    raw.annotations.delete(0)

# # Use parallel port init to sync up timestamps
# sync_time_eeg = events.loc[events["description"].eq("CONNECTION"), "timestamp"].values[0]
# sync_time_smacc = smacc.loc[smacc["description"].eq("CONNECTION"), "timestamp"].values[0]
# sync_time_diff = sync_time_smacc - sync_time_eeg
# events["timestamp"] = events["timestamp"].add(sync_time_diff)
# # This is imperfect, still some time ms time discrepancies.

# # MNE returns onset in unit of sample number, change to seconds.
# events["onset"] /= raw.info["sfreq"]

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



################################################################################
# SPLIT INTO SEPARATE TASK FILES
################################################################################

# Most subjects have two sleep sessions, an overnight and a nap,
#   but some subjects had only naps (early subjects).

n_sleep_tasks = 1 if participant > 900 else 2
assert events["description"].value_counts().at["LightsOn"] == n_sleep_tasks, "Unexpected 'LightsOn' events"
assert events["description"].value_counts().at["LightsOff"] == n_sleep_tasks, "Unexpected 'LightsOff' events"

# Replace with <task_name>-<start_or_stop> for simplified code later.
events["description"] = events["description"].replace({"LightsOff": "sleep-start", "LightsOn": "sleep-stop"})
# if n_sleep_tasks == 2:
#     # Replace first instance with overnight task label
#     events.at[events.description.eq("nap-start").argmax(), "description"] = "overnight-start"
#     events.at[events.description.eq("nap-stop").argmax(), "description"] = "overnight-stop"

# Participants performed different tasks, but all should have done their task before and after nap.
tasks_performed = { x.split("-")[0] for x in events["description"].unique() if x.endswith("start") }
for task in tasks_performed:
    # n_times = 1 if task in ["overnight", "nap"] else 2
    n_times = 2
    if participant == 907:
        n_times = 1
    assert events["description"].value_counts().at[f"{task}-start"] == n_times, f"Unexpected '{task}-start' events"
    assert events["description"].value_counts().at[f"{task}-stop"] == n_times, f"Unexpected '{task}-stop' events"
    # Or just assert they are the same

for task in tqdm.tqdm(tasks_performed, desc="EEG splitting and preprocessing tasks"):
    start_onsets = events.loc[events["description"].eq(f"{task}-start"), "onset"]
    stop_onsets = events.loc[events["description"].eq(f"{task}-stop"), "onset"]
    for i, (tmin, tmax) in enumerate(zip(start_onsets, stop_onsets)):
        # # Trim raw and events to this window.
        events_ = events.set_index("onset").loc[tmin:tmax].reset_index(drop=False)
        # # Readjust events onset to match new cropped file.
        events_["onset"] = events_["onset"].diff().fillna(0)
        # Drop events that bookend the file.
        events_ = events_.iloc[1:-1]
        raw_ = raw.copy()
        raw_.load_data()
        raw_.crop(tmin, tmax)

        ########################################################################
        # PREPROCESSING
        ########################################################################

        # Re-referencing
        # I think MNE loads with an average reference by default.
        mne.add_reference_channels(raw_, reference_channel, copy=False)
        raw_.set_eeg_reference(["L-MSTD", reference_channel])
        raw_.drop_channels(["L-MSTD", reference_channel])

        # Bandpass filtering
        filter_params = dict(filter_length="auto", method="fir")
        filter_cutoffs = {  # from AASM guidelines
            "eeg": (0.3, 35), # Hz; Low-cut, High-cut
            "eog": (0.3, 35),
            "emg": (10, 100),
            # "ecg": (0.3, 70),
            # "snoring": (10, 100),
            "respiration": (0.1, 15),
        }
        raw_.filter(*filter_cutoffs["eeg"], picks="eeg", **filter_params)
        raw_.filter(*filter_cutoffs["eog"], picks="eog", **filter_params)
        raw_.filter(*filter_cutoffs["emg"], picks="emg", **filter_params)
        # raw_.filter(*filter_cutoffs["ecg"], picks="ecg", **filter_params)
        # raw_.filter(*filter_cutoffs["snoring"], picks="Snoring", **filter_params)
        raw_.filter(*filter_cutoffs["respiration"], picks=["RESP", "Airflow"], **filter_params)

        # Downsampling
        raw_.resample(100)

        # Anonymizing
        raw_.set_meas_date(None)
        mne.io.anonymize_info(raw_.info)

        ########################################################################
        # GENERATE BIDS METADATA
        ########################################################################

        # Channels DataFrame
        # n_total_channels = raw_.channel_count
        # Convert from MNE FIFF codes
        fiff2str = {2: "eeg", 202: "eog", 302: "emg", 402: "ecg", 502: "misc"}
        channels_data = {
            "name": [ x["ch_name"] for x in raw_.info["chs"] ], # OR raw_.ch_names
            "type": [ fiff2str[x["kind"]].upper() for x in raw_.info["chs"] ],
            # "types": [ raw_.get_channel_types(x)[0].upper() for x in raw_.ch_names ],
            "units": [ x["unit"] for x in raw_.info["chs"] ],
            "description": "none",
            "sampling_frequency": raw_.info["sfreq"],
            "reference": reference_channel,
            "low_cutoff": raw_.info["highpass"],
            "high_cutoff": raw_.info["lowpass"],
            "notch": utils.NOTCH_FREQUENCY,
            "status": "none",
            "status_description": "none",
        }
        channels = pd.DataFrame.from_dict(channels_data)
        channels_sidecar = utils.generate_channels_sidecar()

        # EEG sidecar
        task_descriptions = {
            "sleep": "Participants went to sleep and TMR cues were played quietly during slow-wave sleep",
            "bct": "Participants went to sleep and TMR cues were played quietly during slow-wave sleep",
            "svp": "Participants went to sleep and TMR cues were played quietly during slow-wave sleep",
            "mwt": "Participants went to sleep and TMR cues were played quietly during slow-wave sleep",
        }
        task_instructions = {
            "sleep": "Go to sleep.",
            "bct": "Go to sleep.",
            "svp": "Go to sleep.",
            "mwt": "Go to sleep.",
        }
        ch_type_counts = channels["type"].value_counts()
        ch_type_counts = ch_type_counts.reindex(["EEG", "EOG", "EMG", "ECG", "MISC"], fill_value=0)
        eeg_sidecar = utils.generate_eeg_sidecar(
            task_name=task,
            task_description=task_descriptions[task],
            task_instructions=task_instructions[task],
            reference_channel=reference_channel,
            ground_channel=ground_channel,
            sampling_frequency=raw_.info["sfreq"],
            recording_duration=raw_.times[-1],
            n_eeg_channels=int(ch_type_counts.at["EEG"]),
            n_eog_channels=int(ch_type_counts.at["EOG"]),
            n_ecg_channels=int(ch_type_counts.at["ECG"]),
            n_emg_channels=int(ch_type_counts.at["EMG"]),
            n_misc_channels=int(ch_type_counts.at["MISC"]),
        )

        # Events sidecar
        events_sidecar = utils.generate_events_sidecar(events.columns)

        ########################################################################
        # EXPORTING
        ########################################################################

        # Pick filepaths.
        if task == "sleep":
            acq = "nap" if i == 1 or n_sleep_tasks == 1 else "overnight"
        else:  # behavioral tasks
            acq = "pre" if i == 0 else "post"
        export_stem = f"{participant_id}_task-{task}_acq-{acq}"
        export_name_eeg = export_stem + "_eeg" + utils.EEG_RAW_EXTENSION
        export_name_events = export_stem + "_events.tsv"
        export_name_channels = export_stem + "_channels.tsv"
        export_path_eeg = ROOT_DIR / participant_id / export_name_eeg
        export_path_events = ROOT_DIR / participant_id / export_name_events
        export_path_channels = ROOT_DIR / participant_id / export_name_channels

        # Export.
        raw_.save(export_path_eeg, fmt="single", overwrite=True)
        utils.export_json(eeg_sidecar, export_path_eeg.with_suffix(".json"))
        utils.export_tsv(channels, export_path_channels)
        utils.export_json(channels_sidecar, export_path_channels.with_suffix(".json"))
        if not events_.empty:
            utils.export_tsv(events, export_path_events, index=False)
            utils.export_json(events_sidecar, export_path_events.with_suffix(".json"))

        # del raw_  # Not necessary.

# raw_save_kwargs = dict(fmt="single", overwrite=True)

# events = events_df.set_index("description")

# # Extract nap. (on/off reversed for 906, change for new subs)
# if "LightsOff" in events.index and "LightsOn" in events.index:
#     nap_tmin = events.loc["LightsOff", "onset"]
#     nap_tmax = events.loc["LightsOn", "onset"]
#     ## Save nap data.
#     # nap_raw = raw.copy().crop(tmin=nap_tmin, tmax=nap_tmax, include_tmax=True)
#     nap_events = events_df.query(f"onset.between({nap_tmin}, {nap_tmax})")
#     raw.save(eeg_path, tmin=nap_tmin, tmax=nap_tmax, **raw_save_kwargs)
#     dmlab.io.export_dataframe(nap_events, events_path)
#     dmlab.io.export_dataframe(channels_df, channels_path)
#     dmlab.io.export_json(eeg_sidecar, eeg_path.with_suffix(".json"))
#     dmlab.io.export_json(events_sidecar, events_path.with_suffix(".json"))
#     dmlab.io.export_json(channels_sidecar, channels_path.with_suffix(".json"))
# else:
#     raise ValueError("Missing LightsOff and/or LightsOn")

# # biocals_tmin = events.loc["Biocals OpenEyes", "onset"]
# prenap_events = events.query(f"onset.lt({nap_tmin})")
# postnap_events = events.query(f"onset.gt({nap_tmax})")
# path_adjuster = lambda p, t, a: p.as_posix().replace("task-nap", f"task-{t}_acq-{p}")

# if "bct-start" in prenap_events.index and "bct-stop" in prenap_events.index:
#     # Extract bct pre.
#     bct_pre_tmin = events.loc["bct-start", "onset"]
#     bct_pre_tmax = events.loc["bct-end", "onset"]
#     raw.save(path_adjuster(eeg_path, "bct", "pre"),
#         tmin=bct_pre_tmin, tmax=bct_pre_tmax, **raw_save_kwargs)

# Extract bct post.
# Extract svp pre.
# Extract svp post.

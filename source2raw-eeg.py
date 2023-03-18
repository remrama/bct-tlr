"""
Take in original Neuroscan .cnt EEG files and SMACC .log files to:
    - Split into separate task segments (sleep, BCT, MW, SVP)
    - Apply minimal preprocessing (rereferencing, filtering)
    - Export as .edf EEG files
    - Export corresponding metadata for each file (events, channels, and all sidecars)
"""
from datetime import timezone
import argparse

import mne
import numpy as np
import pandas as pd
import tqdm
import yasa

import utils


mne.set_log_level(verbose=utils.MNE_VERBOSITY)

parser = argparse.ArgumentParser()
parser.add_argument("--participant", type=int, required=True)
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

while raw.info["bads"]:
    raw.info["bads"].pop(0)

# Load TMR logfile.
smacc = utils.read_smacc_log(import_path_smacc)

if participant > 900:
    # Pilot participants had a different task paired with this cue.
    smacc["trial_type"] = smacc["trial_type"].replace({"mwt": "svp"})

if participant == 4:
    # CONNECTION signal sent in SMACC but before EEG was started, so remove from SMACC
    smacc = smacc.iloc[1:].reset_index(drop=True)

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
    # val2desc = { k: v for k, v in val2desc.items() if v.split("-")[-1] not in ["target", "nontarget", "reset"] }
    # Rename behavioral task button-press descriptions.
    for k, v in val2desc.items():
        if v.split("-")[-1] in ["target", "nontarget", "reset"]:
            task, press = v.split("-")
            val2desc[k] = f"{task.capitalize()}Press{press.capitalize()}"
    task_codes.update(val2desc)
event_codes = task_codes | smacc_codes
event_codes = {k: event_codes[k] for k in sorted(event_codes)}

# Add Note code for temp fix?
# all_codes[204] = "Note"

# unused_ann_indices = [ i for i, a in enumerate(raw.annotations) if int(a["description"]) not in events["value"].values ]
unused_ann_indices = [i for i, a in enumerate(raw.annotations) if int(a["description"]) not in event_codes]
raw.annotations.delete(unused_ann_indices)
# assert len(raw.annotations) == len(events)

if participant == 907:
    # Remove first "bct-stop" because there was no start and they redid it later.
    raw.annotations.delete(0)

# Generate events DataFrame from EEG file.
## NOTE difference between BIDS events (desired) and MNE events. The latter has different units.
events = raw.annotations.to_data_frame()
# events["timestamp"] = events["onset"].dt.tz_localize("US/Central").dt.tz_convert(timezone.utc)
events["timestamp"] = events["onset"].dt.tz_localize("UTC")
events["onset"] = raw.annotations.onset  # Seconds from start of file.
events.insert(2, "value", events["description"].astype(int))
events["description"] = events["value"].map(event_codes)
# unlabeled_codes = events.loc[events["description"].isna(), "value"].unique().tolist()
# assert not unlabeled_codes, f"Found unlabeled portcodes: {unlabeled_codes}"
# Remove unlabeled portcodes, some are not being used.
# events = events.dropna(subset="description")
# events = events.set_index("description")

if participant == 908:
    # Correct for closing down EEG file before the LightsOn SMACC cue was registered.
    # It's in the SMACC file and basically occurs when the EEG file ends so just add it to the end.
    lights_on_row = {
        "onset": [np.floor(raw.times[-1])],
        "duration": [0],
        "value": [{ v: k for k, v in event_codes.items() }["LightsOn"]],
        "description": ["LightsOn"],
    }
    events = pd.concat([events, pd.DataFrame(lights_on_row)], ignore_index=True)


#### Merge to carry extra info over.
#### Merge SMACC log file info (e.g., duration) with EEG annotations/events.
# smacc["timestamp"] = smacc["timestamp"].tz_convert(timezone.utc)
# Use connection to get time difference between smacc and eeg computers.
t0 = events["timestamp"][0]  # TODO: assert this is CONNECTION
t1 = smacc["timestamp"][0]  # TODO: assert this is CONNECTION
td = t1 - t0
smacc["timestamp"] = smacc["timestamp"].sub(td)

# events = events.set_index("timestamp")
# smacc = smacc.set_index("timestamp")
#### TODO: set timestamp indices permanently and wrk with those
indxer = events.set_index("timestamp").index.get_indexer(smacc.set_index("timestamp").index, method="nearest")
smacc = smacc.set_index(indxer)

events = events.join(smacc[["stim_file", "trial_type", "volume"]])
events.loc[smacc.index, "duration"] = smacc["duration"].fillna(0)

# smacc = smacc.set_index(events.query("~description.str.contains('-')").index)
# events["duration"] = smacc["duration"].fillna(0)
# events = events.join(smacc[["stim_file", "trial_type", "volume"]])
# Make a function to match events between SMACC and EEG file
# (clock time between systems is not perfect, take EEG as truth)
# Sloppy for now
# events_stamp = events.query("description.eq('CONNECTION')").onset.to_numpy()[0]
# smacc["onset"] = smacc["timestamp"].diff().dt.total_seconds().fillna(events_stamp).cumsum()
# # still milliseconds off, so again take EEG as truth, right?
# a = events.loc[273:, "onset"]#.to_numpy()
# b = smacc["onset"]#.to_numpy()
# assert a.size == b.size
# assert pd.Series(a).sub(b).le(0.01).all(), "make sure SMACC and events file are synced"
# idx = pd.Index(a).get_indexer(pd.Index(b), method="nearest")
# or just use smacc.reindex(tolerance=)
# idx = pd.Series(a).sub(b).abs().idxmin()
# idx - pd.Series(a).sub(b).abs().argsort().to_numpy()
#### TODO: THE ABOVE CODE INDICATES INCREASING TIME DISCREPANCIES BETWEEN SMACC AND EEG,
#####      NEED TO FIGURE OUT WHY
# a = events.query("description.eq('CONNECTION')").index[0]
# b = events.query("description.eq('LightsOn')").index[-1]
# smacc.reindex(index=range(a, b+1))


if participant == 909:
    # # Button-mashed lights on/off at the end of this subject, remove.
    # events = events.drop(index=[25, 26, 27, 28]).reset_index(drop=True)
    # Get extra indices and drop them
    extras = events.query("description.isin(['LightsOff', 'LightsOn'])").iloc[2:].index.tolist()
    events = events.drop(index=extras).reset_index(drop=True)
if participant == 3:
    # Forgot last lights-on before BCT.
    # Use bct-start as rough estimate.
    bct2_onset = events.query("description.eq('bct-start')")["onset"].iloc[-1]
    lights_on_row = {
        "onset": [bct2_onset - 60],
        "duration": [0],
        "value": [{ v: k for k, v in event_codes.items() }["LightsOn"]],
        "description": ["LightsOn"],
    }
    events = pd.concat([events, pd.DataFrame(lights_on_row)], ignore_index=True)
    events = events.sort_values("onset").reset_index(drop=True)
if participant == 4:
    # testing cues at start
    events = events.loc[8:].reset_index(drop=True)
    # First BCT, participant didn't push anything, so we redid it.
    events = events.drop(index=range(2, 22)).reset_index(drop=True)
if participant == 5:
    # Drop testing before exp started
    events = events.loc[7:].reset_index(drop=True)
    bct1_onset = events.query("description.eq('BctPressNontarget')")["onset"].iloc[0]
    lights_on_row = {
        "onset": [bct1_onset - 60],
        "duration": [0],
        "value": [{ v: k for k, v in event_codes.items() }["LightsOn"]],
        "description": ["LightsOn"],
    }
    events = pd.concat([events, pd.DataFrame(lights_on_row)], ignore_index=True)
    events = events.sort_values("onset").reset_index(drop=True)
    # Missed first lights on for WBTB awakening, then smashed them a few times. Adjust.
    # remove the times i smashed it later.
    # Get extra indices and drop them
    extras = events.query("description.isin(['LightsOff', 'LightsOn'])").iloc[2:-2].index.tolist()
    events = events.drop(index=extras).reset_index(drop=True)

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

# # Bandpass filtering
# filter_params = dict(filter_length="auto", method="fir")
# filter_cutoffs = {  # from AASM guidelines
#     "eeg": (0.3, 35), # Hz; Low-cut, High-cut
#     "eog": (0.3, 35),
#     "emg": (10, 100),
#     # "ecg": (0.3, 70),
#     "snoring": (10, 100),
#     "respiration": (0.1, 15),
# }
# raw.load_data()
# raw.filter(*filter_cutoffs["eeg"], picks="eeg", **filter_params)
# raw.filter(*filter_cutoffs["eog"], picks="eog", **filter_params)
# raw.filter(*filter_cutoffs["emg"], picks="emg", **filter_params)
# # raw.filter(*filter_cutoffs["ecg"], picks="ecg", **filter_params)
# raw.filter(*filter_cutoffs["snoring"], picks="Snoring", **filter_params)
# raw.filter(*filter_cutoffs["respiration"], picks=["RESP", "Airflow"], **filter_params)
# # Downsampling
# raw.resample(100)



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
tasks_performed = {x.split("-")[0] for x in events["description"].unique() if x.endswith("start")}
for task in tasks_performed:
    # n_times = 1 if task in ["overnight", "nap"] else 2
    n_times = 2
    if participant in [907, 908] or (participant == 909 and task != "bct"):
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
        events_["onset"] = events_["onset"].sub(events_["onset"].at[0])
        # Drop events that bookend the file.
        events_ = events_.iloc[1:-1]
        # Restart event values at 1, bc number is arbitrary at this point.
        events_["value"].map(lambda x: events_["value"].unique().tolist().index(x) + 1)
        raw_ = raw.copy()
        raw_.load_data()
        raw_.crop(tmin, tmax)

        ########################################################################
        # PREPROCESSING
        ########################################################################

        # Re-referencing
        # I think MNE loads with an average reference by default.
        # raw_.add_reference_channels(reference_channel)
        # raw_.set_eeg_reference(["L-MSTD", reference_channel], projection=False)
        raw_.set_eeg_reference("average", projection=False)
        # raw_.drop_channels(["L-MSTD"])
        # raw_.drop_channels(["L-MSTD", reference_channel])

        # Bandpass filtering
        filter_params = dict(filter_length="auto", method="fir", fir_window="hamming")
        filter_cutoffs = {  # from AASM guidelines
            "eeg": (0.3, 35), # Hz; Low-cut, High-cut
            "eog": (0.3, 35),
            "emg": (10, 100),
            # "ecg": (0.3, 70),
            "snoring": (10, 100),
            "respiration": (0.1, 15),
        }
        raw_.filter(*filter_cutoffs["eeg"], picks="eeg", **filter_params)
        raw_.filter(*filter_cutoffs["eog"], picks="eog", **filter_params)
        raw_.filter(*filter_cutoffs["emg"], picks="emg", **filter_params)
        # raw_.filter(*filter_cutoffs["ecg"], picks="ecg", **filter_params)
        raw_.filter(*filter_cutoffs["snoring"], picks="Snoring", **filter_params)
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
            "name": [x["ch_name"] for x in raw_.info["chs"]], # OR raw_.ch_names
            "type": [fiff2str[x["kind"]].upper() for x in raw_.info["chs"]],
            # "types": [ raw_.get_channel_types(x)[0].upper() for x in raw_.ch_names ],
            "units": [x["unit"] for x in raw_.info["chs"]],
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
        events_sidecar = utils.generate_events_sidecar(events_.columns)

        ########################################################################
        # EXPORTING
        ########################################################################

        # Pick filepaths.
        if task == "sleep":
            acq = "nap" if i == 1 or n_sleep_tasks == 1 else "overnight"
        else:  # behavioral tasks
            acq = "pre" if i == 0 else "post"
        export_parent = ROOT_DIR / participant_id / "eeg"
        export_stem = f"{participant_id}_task-{task}_acq-{acq}"
        export_name_eeg = export_stem + "_eeg.edf"# + utils.EEG_RAW_EXTENSION
        export_name_events = export_stem + "_events.tsv"
        export_name_channels = export_stem + "_channels.tsv"
        export_path_eeg = export_parent / export_name_eeg
        export_path_events = export_parent / export_name_events
        export_path_channels = export_parent / export_name_channels

        # Export.
        # raw_.save(export_path_eeg, fmt="single", overwrite=True, split_naming="bids")
        export_parent.mkdir(parents=True, exist_ok=True)
        mne.export.export_raw(export_path_eeg, raw_, add_ch_type=False, overwrite=True)
        utils.export_json(eeg_sidecar, export_path_eeg.with_suffix(".json"))
        utils.export_tsv(channels, export_path_channels)
        utils.export_json(channels_sidecar, export_path_channels.with_suffix(".json"))
        if not events_.empty:
            utils.export_tsv(events_, export_path_events, index=False)
            utils.export_json(events_sidecar, export_path_events.with_suffix(".json"))

        del raw_  # Not necessary.

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

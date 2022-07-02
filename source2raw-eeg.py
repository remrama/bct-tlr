"""Convert sourcedata .cnt EEG file (Neuroscan)
to multiple raw .fif EEG BIDS-formatted files
and their corresponding information files.

Clean a participant's raw PSG file.
Break it into the different tasks,
preprocess it, rename the triggers,
add sleep stage annotations, etc.

Each session gets:
    _eeg.fif          - PSG data
    _eeg.json         - PSG sidecar info
    _channels.tsv     - channel information
    _events.tsv       - stimulus/trigger information

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

source_dir = utils.config.get("Paths", "source")
raw_dir = utils.config.get("Paths", "raw")
stimuli_dir = utils.config.get("Paths", "stimuli")
eeg_file_extension = utils.config.get("PSG", "file_extension")
reference_channel = utils.config.get("PSG", "reference")
ground_channel = utils.config.get("PSG", "ground")
notch_frequency = utils.config.getint("PSG", "notch_frequency")
eeg_channels = utils.config.getlist("PSG", "eeg")
eog_channels = utils.config.getlist("PSG", "eog")
misc_channels = utils.config.getlist("PSG", "misc")
ecg_channels = utils.config.getlist("PSG", "ecg")
emg_channels = utils.config.getlist("PSG", "emg")

parser = argparse.ArgumentParser()
parser.add_argument("--participant", type=int, default=906)
parser.add_argument("--session", type=int, default=1)
args = parser.parse_args()

participant_number = args.participant
session_number = args.session

new_extension = "fif"
participant_id = f"sub-{participant_number:03d}"
session_id = f"ses-{session_number:03d}"
import_basename = f"{participant_id}_{session_id}_eeg.{eeg_file_extension}"
export_basename = f"{participant_id}_task-nap_eeg.{new_extension}"
import_path = Path(source_dir) / participant_id / import_basename
eeg_path = Path(raw_dir) / participant_id / export_basename
eeg_sidecar_path = eeg_path.with_suffix(".json")
channels_path = str(eeg_path.with_suffix(".tsv")).replace("_eeg", "_channels")
events_path = str(eeg_path.with_suffix(".tsv")).replace("_eeg", "_events")
events_sidecar_path = Path(events_path).with_suffix(".json")
channels_sidecar_path = Path(channels_path).with_suffix(".json")

eeg_path.parent.mkdir(parents=True, exist_ok=True)


# Load raw Neuroscan EEG file
raw = mne.io.read_raw_cnt(import_path,
    eog=eog_channels, misc=misc_channels,
    ecg=ecg_channels, emg=emg_channels,
    data_format="auto", date_format="mm/dd/yy",
    preload=False, verbose=None)


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

channels_sidecar_info = {
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
}


############################################ Generate EEG sidecar file
eeg_sidecar_info = {
    "TaskName": "sleep",
    "TaskDescription": "Participants went to sleep and TMR cues were played quietly during slow-wave sleep",
    "Instructions": "Go to sleep",
    "InstitutionName": "Northwestern University",
    "Manufacturer": "Neuroscan",
    "ManufacturersModelName": "tbd",
    "CapManufacturer": "tbd",
    "CapManufacturersModelName": "tbd",
    "PowerLineFrequency": 60,
    "EEGPlacementScheme": "10-20",
    "EEGReference": f"single electrode placed on {reference_channel}",
    "EEGGround": f"single electrode placed on {ground_channel}",
    "SamplingFrequency": raw.info["sfreq"],
    "EEGChannelCount": len(eeg_channels),
    "EOGChannelCount": len(eog_channels),
    "ECGChannelCount": len(ecg_channels),
    "EMGChannelCount": len(emg_channels),
    "MiscChannelCount": len(misc_channels),
    "TriggerChannelCount": 0,
    "SoftwareFilters": "tbd",
    "HardwareFilters": {
        "tbd": {
            "tbd": "tbd",
            "tbd": "tbd"
        }
    },
    "RecordingType": "continuous",
    "RecordingDuration": raw.times[-1]
}


######### Events

# Load all the portcodes
event_desc = utils.get_all_portcodes(participant_number, session_number)
event_id = { v: k for k, v in event_desc.items() }

# Load stimuli filenames.
cue_paths = Path(stimuli_dir).glob("*_Cue*.wav")
biocal_paths = Path(stimuli_dir).joinpath("biocals").glob("*.mp3")
stimuli_abspaths = list(cue_paths) + list(biocal_paths)
stimuli_relpaths = [ relpath(p, getcwd()) for p in stimuli_abspaths ]

## (this might be unsafe)
raw.annotations.description = np.array([ event_desc[int(x)]
    for x in raw.annotations.description if int(x) in event_desc ])

# Add custom mapping to avoid arbitrary ints


### It can be passed as event_id=custom_mapping
### to handle the mapping simultaneously
### for epoching analyses, need triggers
### represented as "Events" rather than "Annotations"
events_from_annot, event_dict = mne.events_from_annotations(raw, event_id=event_id)

events_df = pd.DataFrame(events_from_annot, columns=["onset", "duration", "value"])

def get_stim_name(x):
    for p in stimuli_relpaths:
        if x in p:
            return p

events_df["description"] = events_df["value"].map(event_desc)
events_df["stim_file"] = events_df["description"].apply(get_stim_name)

events_sidecar_info = {
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
    "trial_type": {
        "LongName": "General event category",
        "Description": "Very different event types are included, so this clarifies",
        "Levels": {
            "tmr": "A sound cue for targeted memory reactivation",
            "staging": "A sleep stage",
            "misc": "Things like lights-on lights-off or note"
        }
    },
    "StimulusPresentation": {
        "OperatingSystem": "Linux Ubuntu 18.04.5",
        "SoftwareName": "Psychtoolbox",
        "SoftwareRRID": "SCR_002881",
        "SoftwareVersion": "3.0.14",
        "Code": "doi:10.5281/zenodo.3361717"
    }
}


######################################## Export everything

dmlab.io.export_json(channels_sidecar_info, channels_sidecar_path)
dmlab.io.export_json(events_sidecar_info, events_sidecar_path)
dmlab.io.export_json(eeg_sidecar_info, eeg_sidecar_path)
dmlab.io.export_dataframe(channels_df, channels_path)
dmlab.io.export_dataframe(events_df, events_path)
raw.save(eeg_path, overwrite=True)

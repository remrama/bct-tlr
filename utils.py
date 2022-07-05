"""Helper functions"""

# Add development dir while working on dmlab.
import sys
sys.path.append("C:/Users/malle/packages/dmlab")

import configparser
from datetime import timezone
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
    df = pd.read_csv(filepath, index_col="participant_id", parse_dates=["measurement_date"], sep="\t")
    # MNE wants UTC and check fails if UTC is a string rather than datetime timezone.
    # https://github.com/mne-tools/mne-python/blob/3c23f13c0262118d075de0719248409bdc838982/mne/utils/numerics.py#L1036
    df["measurement_date"] = df["measurement_date"].dt.tz_localize("US/Central").dt.tz_convert(timezone.utc)
    return df


####################################################
# Functions to generate BIDS sidecars
####################################################

def generate_eeg_bids_sidecar(
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
        **kwargs
    ):
    defaults = {
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
    }
    defaults.update(kwargs)
    return defaults

def generate_eeg_channels_bids_sidecar(**kwargs):
    defaults = {
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
    defaults.update(kwargs)
    return defaults

def generate_eeg_events_bids_sidecar(**kwargs):
    defaults = {
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
    defaults.update(kwargs)
    # Make sure stim presentation info is last (only one that's not a column).
    defaults["StimulusPresentation"] = defaults.pop("StimulusPresentation")
    return defaults



####################################################
# Portcode functions
####################################################

def load_tmr_logfile(participant, session):

    source_dir = config.get("Paths", "source")
    tmr_log_path = Path(source_dir).joinpath(
        f"sub-{participant:03d}",
        f"sub-{participant:03d}_ses-{session:03d}_tmr.log",
    )

    df = pd.read_csv(tmr_log_path,
        names=["timestamp", "msg_level", "msg"],
        parse_dates=["timestamp"])
    df["timestamp"] = df["timestamp"].dt.tz_localize("US/Central").dt.tz_convert(timezone.utc)
    df["msg"] = df["msg"].str.strip()
    return df


def get_tmr_codes(participant, session):
    #### Get event codes from TWC GUI log.

    df = load_tmr_logfile(participant, session)
    ser = df.set_index("timestamp")["msg"]

    # Reduce to only events with portcodes
    assert not ser.str.contains("Failed portcode").any()
    ser = ser[ser.str.contains("Sent portcode")]

    codes = {}
    for timestamp, msg in ser.items():
        if msg.startswith("Cue"):
            description, _, portcode_str = msg.split(" - ")
        else:
            description, portcode_str = msg.split(" - ")
        portcode = int(portcode_str.split()[-1])

        # Portcodes for cue stopping will be same code but different descriptions.
        if description.startswith("CueStopped"):
            description = "CueStopped"
        # elif description.startswith("Played cue"):
        #     description = description.split()[-1]

        if portcode in codes:
            assert codes[portcode] == description, f"{portcode} has varying descriptions, here it was {description}"
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


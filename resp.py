"""Respiration template."""
import argparse
from pathlib import Path

from bids import BIDSLayout
import mne
import neurokit2 as nk
import numpy as np
import pandas as pd
import tqdm

import utils

mne.set_log_level(verbose=utils.MNE_VERBOSITY)

parser = argparse.ArgumentParser()
parser.add_argument("--participant", type=int, default=4)
parser.add_argument("--overwrite", action="store_true")
args = parser.parse_args()


participant = args.participant

resp_channel = "Fz"


layout = BIDSLayout(utils.ROOT_DIR, validate=False)
# stimuli_dir = bids_root / "stimuli"
bids_files = layout.get(
    subject=f"{participant:03d}",
    task="sleep",
    suffix="eeg",
    # extension=utils.EEG_RAW_EXTENSION,
    extension=".edf",
)



# Loop over each file and export a hypnogram events file.
# for bf in tqdm.tqdm(bids_files, desc="Sleep Staging"):

bf = bids_files[0]

# Load raw data.
raw = mne.io.read_raw_edf(bf.path)

# Extract sampling frequency (for convenience).
sfreq = raw.info["sfreq"]

# Add annotations from events file.
events_path = bf.path.replace("eeg.edf", "events.tsv")
# if not Path(events_path).exists():
#     continue
events = pd.read_csv(events_path, sep="\t")
# # events = mne.read_events(bf.path.replace("eeg.edf", "events.tsv"))
# # mne.pick_events()
# if "Cue" not in events["description"]:
#     continue

# # Convert to epochs.
# events_arr = events[["onset", "duration", "value"]].to_numpy()
# # events don't have durations :/
# events_arr[:, 1] = 0
# # convert seconds to samples
# # TODO: should events files be exported with samples??
# events_arr[:, 0] = (events_arr[:, 0] * sfreq - 1).round()
# events_arr = events_arr.astype(int)
# events_desc = events.set_index("value")["description"].to_dict()

# # weird they have to be strings
# events_desc = {str(k): v for k, v in events_desc.items()}
# epochs = mne.Epochs(raw, events_arr, tmin=-0.2, tmax=0.5, event_id=events_desc)

# # Create equally spaced events
# mne.events_from_annotations(raw, chunk_duration=1.5)
# mne.make_fixed_length_events()

###############
######### FUCKING MNE ANNOTATIONS ONSET IS IN SECONDS AND EVENTS ONSET IS IN SAMPLES
###########
# Go annotations to events FOR NOW bc exported "events" have onset in duration.
# That way it converts samples to seconds and weird code shit for us.
# Confused y this does not return annotations with duration??
# events_arr = events[["onset", "duration", "value"]].to_numpy()
# events_desc = events.set_index("value")["description"].to_dict()
# annotations = mne.annotations_from_events(events_arr, sfreq, event_desc=events_desc, first_samp=0, orig_time=None)
# So creating manually.
annotations = mne.Annotations(
    onset=events["onset"].to_numpy(),
    duration=events["duration"].to_numpy(),
    description=events["description"].to_numpy(),
)
raw.set_annotations(annotations)
events, event_id = mne.events_from_annotations(raw)

events = mne.pick_events(events, include=event_id["Cue"])

######### I'm just using epochs to get the data chunks. prob overkill
## only need it if looking at short ERP-like stuff

epochs = mne.Epochs(
    raw,
    events,
    event_id=event_id,
    tmin=-60,
    tmax=60,  # because of this i might not even use Epochs (cues played diff lengths)
    picks=resp_channel,
    preload=True,
    on_missing="warn",
    baseline=(0, 0), ## CHECK ON THIS
)
data = epochs.get_data().squeeze() # squeeze out extra axis bc just one channel
rr
# # Drop to the only channels needed.
# raw.pick([resp_channel])

# # Load data.
# raw.load_data()

# # Extract single respiratory channel data.
# rsp = raw.get_data().flatten()
# Clean signal.
rsp = nk.rsp_clean(arr, sampling_rate=sfreq, method="khodadad2018")
# Extract candidate peaks.
df, peaks_dict = nk.rsp_peaks(rsp) 
# Get fixed peaks.
info = nk.rsp_fixpeaks(peaks_dict)
# Extract respiration rate.
rrate = nk.rsp_rate(rsp, peaks_dict, sampling_rate=sfreq)
# Calculate respiration rate variability (RRV) features.
rrv = nk.rsp_rrv(rrate, info, sampling_rate=sfreq)

# rrv_list = np.apply_along_axis(get_rrv, axis=1, arr=data)
pre = pd.concat([get_rrv(row, sfreq) for row in get_epoched_data(raw, events, event_id, resp_channel, tmin=-60, tmax=0)], ignore_index=True).rename_axis("cue").assign(location="pre").set_index("location", append=True)
post = pd.concat([get_rrv(row, sfreq) for row in get_epoched_data(raw, events, event_id, resp_channel, tmin=0, tmax=60)], ignore_index=True).rename_axis("cue").assign(location="post").set_index("location", append=True)

df = pd.concat([pre, post]).sort_index(ascending=[True, False])


export_pattern = "derivatives/sub-{subject}/sub-{subject}_task-{task}_acq-{acquisition}_rrv.tsv"
export_path = layout.build_path(bf.entities, export_pattern, validate=False)
utils.export_tsv(df, export_path, index=True)

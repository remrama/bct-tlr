import os
import sys
import mne
import argparse


parser = argparse.ArgumentParser()
parser.add_argument("--subject", type=int, required=True)
parser.add_argument("--session", type=int, required=True)
parser.add_argument("--rater", type=int, required=True)
args = parser.parse_args()


subject_id = args.subject
session_id = args.session
session_id = args.session
rater_id = args.rater

# choose filepaths
import_fname = f"./eeg_data/{subject_id}ses{session_id:02d}.set"
export_fname = f"./ratings/{subject_id}ses{session_id:02d}_rat{rater_id}.csv"

# make sure ratings file doesn't already exist
if os.path.exists(os.path.expanduser(export_fname)):
	keep_going = input("Rating file already exists. Press y to overwrite.\n")
	if keep_going.lower() != "y":
		sys.exit()

# Load eeg data
raw = mne.io.read_raw_eeglab(import_fname)


# select channels to view
channels = ["L-HEOG", "R-HEOG"]
channel_indices = [ raw.ch_names.index(c) for c in channels ]


# Remove any existing annotations
while raw.annotations:
	raw.annotations.delete(0)

# open plot
raw.plot(duration=30, order=channel_indices, block=True)



# ===========================================================================
# ===========================================================================
# ===========================================================================
# ===========================================================================



# generate dataframe from annotations
df = raw.annotations.to_data_frame()

# get back non-time timestamp
df["onset"] = raw.annotations.onset

# rename some columns
df = df.rename(columns={
		"onset": "TimeStart",
		"description": "Signal",
	})

# add time end
df["TimeEnd"] = raw.annotations.onset + raw.annotations.duration

# add participant and session
df["Participant"] = subject_id
df["Session"] = session_id
df["Rater"] = rater_id

# reorder
column_order = ["Participant", "Session", "Rater", "TimeStart", "TimeEnd", "Signal"]
df = df[column_order]


df.to_csv(export_fname, index=False, float_format="%.2f")




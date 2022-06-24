"""Manual staging for a single session

MUST have mne QT backend installed
https://github.com/mne-tools/mne-qt-browser
"""
import mne
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--subject", type=int, default=901)
parser.add_argument("--session", type=int, default=1)
args = parser.parse_args()

subject_number = args.subject
session_number = args.session

print(subject_number, session_number)

ss
edf_file, hypno_file = mne.datasets.sleep_physionet.age.fetch_data(subjects=[0], recording=[1])[0]

raw = mne.io.read_raw_edf(edf_file, stim_channel="Event marker", misc=["Temp rectal"])
hypno_annot = mne.read_annotations(hypno_file)

# keep last 30-min wake events before sleep and first 30-min wake events after
# sleep and redefine annotations on raw data
hypno_annot.crop(hypno_annot[1]["onset"] - 30 * 60,
                 hypno_annot[-2]["onset"] + 30 * 60)
raw.set_annotations(hypno_annot, emit_warning=False)

# plot some data
# scalings were chosen manually to allow for simultaneous visualization of
# different channel types in this specific dataset
# mne.viz.set_browser_backend("qt")
raw.plot(block=True, duration=30)
# raw.plot(start=60, duration=30,
#     block=True,
#     scalings=dict(eeg=1e-4, resp=1e3, eog=1e-4, emg=1e-7, misc=1e-1))


annotation_desc_2_event_id = {'Sleep stage W': 1,
                              'Sleep stage 1': 2,
                              'Sleep stage 2': 3,
                              'Sleep stage 3': 4,
                              'Sleep stage 4': 4,
                              'Sleep stage R': 5}


events_train, _ = mne.events_from_annotations(
    raw_train, event_id=annotation_desc_2_event_id, chunk_duration=30.)

# create a new event_id that unifies stages 3 and 4
event_id = {'Sleep stage W': 1,
            'Sleep stage 1': 2,
            'Sleep stage 2': 3,
            'Sleep stage 3/4': 4,
            'Sleep stage R': 5}

# plot events
fig = mne.viz.plot_events(events_train, event_id=event_id,
                          sfreq=raw_train.info['sfreq'],
                          first_samp=events_train[0, 0])

# keep the color-code for further plotting
stage_colors = plt.rcParams['axes.prop_cycle'].by_key()['color']



fig = raw.plot(start=2, duration=6)

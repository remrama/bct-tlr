import subprocess
import sys

from tqdm import tqdm


def run_command(command):
    """Run shell command and exit upon failure."""
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        sys.exit()


participants = [1, 2, 3, 4, 5, 907, 908, 909]
participant_scripts = [
    # "source2raw-eeg",  # Convert EEG file to separate BIDS-formatted edf (and associated) files.
    # "calc-hypno",  # Calculate overnight and nap hypnograms.
    # "plot-hypno",  # Plot overnight and night hypnograms.
    # "calc-cues",  # Calculate number of cues per sleep stage.
    "calc-resp",  # Calculate respiration features/timecourses.
    "plot-resp_hypno"  # Plot respiration rate aligned with hypnogram.
]
for p in tqdm(participants, desc="Participants"):
    for script in (pbar := tqdm(participant_scripts, leave=False)):
        pbar.set_description(script)
        command = f"python {script}.py --participant {p}"
        run_command(command)

for survey in (
    "Initial+Survey",
    "Debriefing+Survey",
    "Dream+Report",
    "sub-004+Followup",
    ):
    command = f"python source2raw-qualtrics.py --survey {survey}"
    # run_command(command)

group_scripts = [
    "source2raw-wav",  # Move dream reports wav recordings to raw, and convert to text.
    "source2raw-bct",  # Convert Breath-Counting Task behavior json/log files to tsv files.
    "plot-bct",  
# Compare group pre-nap and post-nap BCT performance.
]
for script in group_scripts:
    command = f"python {script}.py"
    # run_command(command)

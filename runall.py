import subprocess
import sys

for p in (907, 908, 909, 1, 2, 3, 4, 5):
    for script in (
        # "source2raw-eeg",
        # "calc-hypno",
        # "plot-hypno",
        # "calc-cues",
        "calc-resp",
    ):
        command = f"python {script}.py --participant {p}"
        result = subprocess.run(command, shell=True)
        if result.returncode != 0:
            sys.exit()

## Normalizing sound stimuli files
## https://superuser.com/a/323127
##
## 1. Install ffmpeg and ffmpeg-normalize
## 2. cd into directory with all the stimuli
## If not on Windows:
## 3. ffmpeg-normalize ./*.wav -of ./stimuli_normed -ext wav -p
## If on Windows:
## for %%f in ("*.mkv") do ffmpeg-normalize "%%f" -c:a aac -b:a 192k
##
## But here wrapping in Python...

import json
from pathlib import Path
import subprocess

with open("./config.json", "r", encoding="utf-8") as f:
    C = json.load(f)

stimuli_dir = Path(C["soundfile_directory"])
export_dir = stimuli_dir / "stimuli_normalized"
wav_files = stimuli_dir.glob("*.wav")
mp3_files = stimuli_dir.glob("*.mp3")
all_files = list(wav_files) + list(mp3_files)

export_dir.mkdir(parents=False, exist_ok=True)

for f in all_files[2:3]:
    extension = f.suffix[1:]
    json_export_path = export_dir / f.with_suffix(".json").name
    cmd = f"ffmpeg-normalize {f} -of {export_dir} -ext {extension} -p >> {json_export_path}"
    cmd_as_list = cmd.split(" ")
    subprocess.call(cmd_as_list, shell=True)
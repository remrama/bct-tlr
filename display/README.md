# BCT-TMR

## Display code

### Running a participant

There is one pre-sleep and one post-sleep script.

Note that session defaults to 1 so is only necessary if there is more than one.

```bash
python runall.py --subject 1 --session 2 --pre
```
Sleep
```bash
python runall.py --subject 1 --session 2 --post
```

### EEG trigger setup

Note the InpOut mess for parallel port setup (if using EEG triggers).

1. https://www.highrez.co.uk/Downloads/InpOut32/default.htm
2. Download the `Binaries only - x86 & x64 DLLs and libs.` zip
3. Unpack it all
4. Run `Win32/InstallDriver.exe` (it will install 64bit version)
5. Move the `x64/inpoutx64.dll` file into the `display` folder (or wherever the psychopy script is run from)


### Soundfile normalization.

Cues A/B are a 1-minute excerpt from the first/second half of each track, respectively. Three-second fade in/outs were added to each cue.

[Brian Eno - LUX 3](https://youtu.be/Es8kYGb5YzM)
[Brian Eno - Meditation No. 1](https://youtu.be/X6DxwTi2FNU)

Cues and background pink noise were normalized using [`ffmpeg-normalize`](https://superuser.com/a/323127).

```shell
ffmpeg-normalize pink.wav -ext wav -p > normalization_output_noise.json
ffmpeg-normalize lux3.wav med1.wav -ext wav --loudness-range-target 14 -p > normalization_output_tracks.json
ffmpeg-normalize lux3_CueA.wav lux3_CueB.wav med1_CueA.wav med1_CueB.wav -ext wav --loudness-range-target 9 -p > normalization_output_cues.json
```

Sham cue was created with `ffmpeg`.

```shell
ffmpeg -i CueA_lux3.wav -filter:a "volume=0" .\CueSham.wav
```
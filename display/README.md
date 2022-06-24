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
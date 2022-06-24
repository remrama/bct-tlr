Setup 
Download MNE-python on your computer (https://mne.tools/stable/install/index.html) 
Download EEG data from box (link) and save the folder to your desktop 
*if you don’t have enough storage on your computer, you can also download pairs of files in the eeg_data folder corresponding to the data you are opening, and then delete it off your computer before downloading the next pair 

Opening each dataset
Open “Prompt MNE” application 
Type “cd Desktop/alpha_ratings/” in the MNE app and press enter 
Type “python3 EMRatings.py --subject 101 --session 1 --rater 1” in the MNE app, except replacing the subject number and session number with those corresponding to the file you wish to open, and always type the rater number assigned to you. Press enter. 
MNE should open 

Navigating MNE
-/+ buttons decrease and increase the scale of the EEG. You will want to set the scale of the EEG to approximately 100 uV.
Left and right arrow keys allow you to scroll through the data
Holding shift while scrolling sends you 30 seconds forwards or backwards
Below the data display, there is a scroll bar you can adjust and bottom window you can click on to jump to different parts of the data. Seconds are often given in (ks), kiloseconds, which are 1000 seconds. 
To insert markers in the data, click the pencil icon in the app called “annotations” 
To add new types of annotations, click the “add description button.” Each dataset will have specific types of descriptions, listed below, depending on the signals used in that study. Make sure you use the exact wording and capitalization specified when entering descriptions. 
Click and drag your mouse in the dataset in order to highlight areas of the data where there are signals. Choose which type of signal is present using the drop-down options, which contain the annotations you have added. 
You can drag the edges of a marker to edit it. You can right-click to undo your selection. 

Your task 
Mark single rapid eye movements, bursts of rapid eye movements, slow rolling eye movements, and LRLR signals in the data 
Click the “x” to exit out of MNE. You should see that the signals you enter exist as a spreadsheet in the “ratings” folder of your “alpha_ratings” folder 
When you are done, upload your ratings folder to box and let me know 


import os
import sys
import tkinter as tk
import webbrowser

urls = {
    "protocol": "https://docs.google.com/document/d/e/2PACX-1vTm2RwA2wMzAg8JcXVr8MqmmOVgMmDNxiy74VfIq_k9yQobawyQl3rm4liIxdAB0lglR_Qm0eNV9uRV/pub",
    "participant_tracking": "https://docs.google.com/spreadsheets/d/1ULacGwbK59Q-wV178eOAccEM0euPe0Tul-DGjizzhr8/edit?usp=sharing",
    "channel_assignment": "https://docs.google.com/spreadsheets/d/15dRZ6KPBV5wzh8Jrm2Cc_lJkceE522G4W1gEE4pg0kE/edit?usp=sharing",
    "welcome_survey": "https://northwestern.az1.qualtrics.com/jfe/form/SV_bqqjFe5nsJVQAjI",
    "lucid_video": "https://youtu.be/L2YGWZAZQKU",
    "dream_report": "https://northwestern.az1.qualtrics.com/jfe/form/SV_eeMswgERpHkcPS6",
    "debriefing_survey": "https://northwestern.az1.qualtrics.com/jfe/form/SV_brC1nxQ4BuEgMg6",
    "osf_project": "https://osf.io/c3xp7",
}

root = tk.Tk()

root.title("BCT TMR Experiment")
root.geometry("550x200")
root.resizable(False, False)

def open_protocol_docs():
    for label in ["protocol", "participant_tracking", "channel_assignment", "osf_project"]:
        webbrowser.open(urls[label])

def open_welcome_survey():
    webbrowser.open(urls["welcome_survey"])

def open_debriefing_survey():
    webbrowser.open(urls["debriefing_survey"])

def open_lucid_video():
    webbrowser.open(urls["lucid_video"])

def open_dream_report():
    webbrowser.open(urls["dream_report"])


    # os.system('opencv_video.py')

btn1 = tk.Button(root, text="Open Protocol", bg="black", fg="white", command=open_protocol_docs)
btn2 = tk.Button(root, text="Open Dream Report", bg="black", fg="white", command=open_dream_report)
btn3 = tk.Button(root, text="Open Lucidity Video", bg="black", fg="white", command=open_lucid_video)
btn4 = tk.Button(root, text="Open Welcome Survey", bg="black", fg="white", command=open_welcome_survey)
btn5 = tk.Button(root, text="Open Debriefing Survey", bg="black", fg="white", command=open_debriefing_survey)
btn1.pack()
btn2.pack()
btn3.pack()
btn4.pack()
btn5.pack()

root.mainloop()


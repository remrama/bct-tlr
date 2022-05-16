"""A base class to use for a psychopy experiment.

It has essential stuff like opening a window,
setting up some text, some functions to show a message,
quit, save, send a slack message, and more.
"""
import os
import json
import random
import inspect
import requests

from psychopy import core, visual, event, monitors, logging, parallel

# Load parameters from configuration file.
with open("./config.json", "r", encoding="utf-8") as f:
    C = json.load(f)


class Game(object):
    def __init__(self, subject_number, session_number, task_name):

        self.subject_number = subject_number
        self.session_number = session_number
        self.task_name = task_name
        self.generate_experiment_id()
        self.development_mode = subject_number == 999

        self.data_directory = C["data_directory"]
        self.slack_url_path = C["slack_url_path"]
        
        self.pport_address = C["parallel_port_address"]
        self.pport_codes = C["parallel_port_codes"]

        self.data = {}
        self.passed_practice = False

        self.welcome_message = "Thank you for participating.\n\nLeft-click in the green box to continue"
        self.exit_message = "Thank you.\n\nYour responses have been recorded."

        self.quit_button = C["quit_button"]

        self.monitor_params = C["monitor_info"]
        self.window_params = {
            "size": [800, 800], # when not fullscreen
            "color": "gray", # background
            "screen": C["screen_number"],
            "units": "deg",
            "fullscr": self.development_mode^1,
            "allowGUI": False,
            "checkTiming": True,
        }

    def init(self):
        self.init_window()
        self.init_stimuli()
        self.mouse = event.Mouse(self.win)
        self.init_slack()
        self.init_pport()
        self.init_exporting()
        self.show_message_and_wait_for_press(self.welcome_message)
        self.send_slack_notification("Experiment started")

    def generate_experiment_id(self):
        self.experiment_id = "_".join([
            f"sub-{self.subject_number:03d}",
            f"ses-{self.session_number:03d}",
            f"task-{self.task_name}"
        ])

    def init_pport(self):
        try:
            self.pport = parallel.ParallelPort(address=self.pport_address)
            self.pport.setData(0) # clear all pins out to prep for sending
            msg = "Parallel port successfully connected."
        except:
            self.pport = None
            msg = "Parallel port connection failed."
        self.send_slack_notification(msg)

    def send_to_pport(self, portcode):
        """Wrapper to avoid rewriting if not None a bunch"""
        if self.pport is not None:
            self.pport.setData(portcode)
            self.pport.setData(0)

    def init_slack(self):
        if os.path.exists(self.slack_url_path):
            with open(self.slack_url_path, "r") as f:
                self.slack_url = f.read().strip()

    def init_exporting(self):
        log_fname = os.path.join(self.data_directory, self.experiment_id+".log")
        if not self.development_mode:
            assert not os.path.exists(log_fname), f"{log_fname} can't already exist."
        logging.LogFile(log_fname, level=logging.INFO, filemode="w")
        self.json_fname = log_fname.replace(".log", ".json")
    
    def init_window(self):
        monitor = monitors.Monitor("testMonitor")
        monitor.setDistance(distance=self.monitor_params["distance_cm"])
        monitor.setWidth(width=self.monitor_params["width_cm"])
        monitor.setSizePix(self.monitor_params["size_pix"])
        self.win = visual.Window(monitor="testMonitor", **self.window_params)

    def init_stimuli(self):
        self.topText = visual.TextStim(self.win, name="topTextStim",
            pos=[0, 4], height=.5, wrapWidth=20, color="white")
        self.middleText = visual.TextStim(self.win, name="middleTextStim",
            pos=[0, 0], height=.5, wrapWidth=20, color="white")
        self.bottomText = visual.TextStim(self.win, name="bottomTextStim",
            pos=[0, -4], height=.5, wrapWidth=20, color="white")
        self.fixationStim = visual.GratingStim(self.win, name="fixationStim",
            mask="cross", tex=None, size=[1, 1])
        self.nextButton = visual.Rect(self.win,
            name="ShapeStim-play",
            width=1, height=1, pos=[0, -8],
            fillColor="green", lineColor="black", lineWidth=1)

    def send_slack_notification(self, text):
        if not self.development_mode:
            text = self.experiment_id + ": " + text
            try:
                requests.post(self.slack_url, json=dict(text=text))
            except:
                pass

    def save_data(self):
        with open(self.json_fname, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, sort_keys=False)

    def quit(self, manual=False):
        slack_msg = "**MANUAL QUIT**" if manual else "Experiment ended"
        self.send_slack_notification(slack_msg)
        if not manual:
            self.show_message_and_wait_for_press(self.exit_message)
        self.win.close()
        self.save_data()
        if manual:
            core.quit()
            # sys.exit()
        else:
            logging.flush()

    def check_for_quit(self):
        if event.getKeys(keyList=[self.quit_button]):
            self.quit(manual=True)

    def show_message_and_wait_for_press(self, text):
        self.middleText.text = inspect.cleandoc(text)
        self.middleText.draw()
        self.nextButton.setOpacity(.2)
        self.nextButton.draw()
        self.win.flip()
        core.wait(3)
        self.nextButton.setOpacity(1)
        event.clearEvents(eventType="mouse")
        xpos = random.uniform(-10, 10)
        ypos = random.uniform(-10, 10)
        self.mouse.setPos([xpos, ypos])
        self.mouse.setVisible(True)
        while not self.mouse.isPressedIn(self.nextButton, buttons=[0]):
            self.middleText.draw()
            self.nextButton.draw()
            self.win.flip()
            self.check_for_quit()
        self.mouse.setVisible(False)

from psychopy import visual, event, core
from game import Game

class MindWanderingTask(Game):

    def __init__(self,
        subject_number,
        session_number,
        acquisition_code,
        room_number,
        task_name="mwt",
        ):
        super().__init__(subject_number, session_number, acquisition_code, room_number, task_name)


        self.instructions_messages = [
            f"For the next {self.task_length_mins} minutes, just sit and let your mind wander.",
            "We only ask you keep your eyes open and don't fall asleep.\n\nOnce you are ready, press the button below."
            f"Try to write continuously about whatever is on your mind.\n\nDo not use abbreviations and try your best to spell correctly.\n\nOnce you are ready, press the button below."
        ]
        self.header_text = "Relax and think about whatever you'd like."

    def task(self):
        self.topText.text = self.header_text
        self.send_to_pport(self.pport_codes["mwt-start"])
        self.clockCountdown = core.CountdownTimer(start=self.task_length)
        while self.clockCountdown.getTime() > 0:
            secs_left = round(self.clockCountdown.getTime())
            m, s = divmod(secs_left, 60)
            self.bottomText.text = f"{m:02d}:{s:02d}"
            self.topText.draw()
            self.bottomText.draw()
            self.fixationStim.draw()
            self.win.flip()
            self.check_for_quit()
        self.send_to_pport(self.pport_codes["mwt-stop"])

    def run(self):
        self.init()
        self.show_message_and_wait_for_press(self.prompt1)
        self.task()
        self.quit()



if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", type=int, default=999)
    parser.add_argument("--session", type=int, default=1)
    parser.add_argument("--acq", type=str, default="pre", choices=["pre", "post"])
    parser.add_argument("--room", type=int, default=207, choices=[0, 207])
    args = parser.parse_args()

    subject_number = args.subject
    session_number = args.session
    acquisition_code = args.acq
    room_number = args.room

    mwt = MindWanderingTask(subject_number, session_number, acquisition_code, room_number)
    mwt.run()

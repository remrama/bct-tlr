import inspect
from psychopy import visual, event, core
from game import Game

class MindWanderingTask(Game):

    def __init__(self,
        subject_number,
        session_number,
        task_name="mwt",
        ):
        super().__init__(subject_number, session_number, task_name)

        prompt1 = f"""For the next {self.task_length_mins} minutes,
        just sit here and let your mind wander.

        We only ask you keep your eyes open and don't fall asleep.
        
        Once you are ready, press the button below.
        """
        self.prompt1 = inspect.cleandoc(prompt1)
        self.prompt2 = "Relax and think about whatever you'd like."

    def task(self):
        self.topText.text = self.prompt2
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
    args = parser.parse_args()

    subject_number = args.subject
    session_number = args.session

    mwt = MindWanderingTask(subject_number, session_number)
    mwt.run()

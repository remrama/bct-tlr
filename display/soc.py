import inspect
from psychopy import visual, event, core
from game import Game

class StreamOfConsciousness(Game):

    def __init__(self,
        subject_number,
        session_number,
        room_number,
        task_name="soc",
        ):
        super().__init__(subject_number, session_number, room_number, task_name)

        self.letter_height = .3
        self.newline_pad = 0 # guessing here, trial and error
        self.newline_spacing = self.letter_height + self.newline_pad
        self.textbox_size = (15, 15)

        prompt1 = f"""For the next {self.task_length_mins} minutes, write what about whatever you'd like.

        Try to write continuously about whatever is on your mind.

        Do not use abbreviations and try your best to spell correctly.

        Once you are ready, press the button below.
        """
        self.prompt1 = inspect.cleandoc(prompt1)
        self.prompt2 = "Write continuously and avoid abbreviations."


    def more_stims(self):
        self.timerText = visual.TextStim(self.win)
        self.promptText = visual.TextStim(self.win)
        self.editableText = visual.TextBox2(self.win,
            text="Write something", font="Open Sans",
            size=self.textbox_size,
            letterHeight=self.letter_height,
            anchor="center", alignment="center",
            lineBreaking="uax14",
            editable=True)


    def task(self):
        self.send_to_pport(self.pport_codes["soc-start"])
        self.clockCountdown = core.CountdownTimer(start=self.task_length)
        n_lines = 1
        while self.clockCountdown.getTime() > 0:
            secs_left = round(self.clockCountdown.getTime())
            m, s = divmod(secs_left, 60)
            self.timerText.text = f"{m:02d}:{s:02d}"
            self.timerText.draw()
            self.editableText.draw()
            self.win.flip()
            if len(self.editableText._lineLenChars) > n_lines:
                self.editableText.pos[1] += self.newline_spacing
                n_lines += 1
            self.check_for_quit()
        self.send_to_pport(self.pport_codes["soc-stop"])

    def run(self):
        self.init()
        self.more_stims()
        # self.audioStim.play()
        self.show_message_and_wait_for_press(self.prompt1)
        self.task()
        self.quit()



if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", type=int, default=999)
    parser.add_argument("--session", type=int, default=1)
    parser.add_argument("--room", type=int, default=207, choices=[0, 207])
    args = parser.parse_args()

    subject_number = args.subject
    session_number = args.session
    room_number = args.room

    soc = StreamOfConsciousness(subject_number, session_number, room_number)
    soc.run()

from __future__ import annotations

from sound.core import Sound
from typing import TYPE_CHECKING
from time import sleep

if TYPE_CHECKING:
    from sound.core import SoundPlayer


class Sounds:
    """Sounds library"""

    def __init__(self, player: SoundPlayer) -> None:

        from sound.assets import Woop, Woop2, Error, Click, Ting

        self.woop = Woop(player)
        self.woop2 = Woop2(player)
        self.error = Error(player)
        self.click = Click(player)
        self.ting = Ting(player)


class Woop(Sound):
    def __init__(self, player: SoundPlayer) -> None:
        super().__init__(player)
        self.sequence = self.generator.get_arpeggio("C3", "A4")

    def play(self) -> None:
        with self.active():
            self.arpeggio(self.sequence, step_duration=0.008)


class Woop2(Sound):
    def __init__(self, player: SoundPlayer) -> None:
        super().__init__(player)
        self.sequence = self.generator.get_arpeggio("A4", "C3")

    def play(self) -> None:
        with self.active():
            self.arpeggio(self.sequence, step_duration=0.008)


class Ting(Sound):
    def __init__(self, player: SoundPlayer) -> None:
        super().__init__(player)
        self.sequence = self.generator.get_arpeggio("E5", "G5")
        self.note1 = self.generator.get_note_freq("C4")
        self.note2 = self.generator.get_note_freq("C5")
        self.note3 = self.generator.get_note_freq("C6")

    def play(self) -> None:
        with self.active():
            self.arpeggio(self.sequence, 0.04)
            sleep(0.02)
            self.note(self.note1, 0.12)

        self.pause(0.06)

        with self.active():
            self.note(self.note1, 0.1)
            self.note(self.note2, 0.1)
            self.note(self.note3, 0.25)


class Error(Sound):
    def __init__(self, player: SoundPlayer) -> None:
        super().__init__(player)
        self.note1 = self.generator.get_note_freq("C2")

    def play(self) -> None:
        for i in range(3):
            with self.active():
                self.note(self.note1, 0.11)
            self.pause(0.11)


class Click(Sound):
    def __init__(self, player: SoundPlayer) -> None:
        super().__init__(player)
        self.note1 = self.generator.get_note_freq("E3")
        self.note2 = self.generator.get_note_freq("G3")
        self.note3 = self.generator.get_note_freq("C4")
        self.note4 = self.generator.get_note_freq("C5")

    def play(self) -> None:
        with self.active():
            self.noise(0.4)
            self.note(self.note3, 0.08)
            self.note(self.note2, 0.08)
            self.note(self.note1, 0.08)
            self.note(self.note2, 0.08)
            self.note(self.note3, 0.08)
            self.note(self.note4, 0.08)

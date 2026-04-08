from __future__ import annotations

from time import time, sleep
from typing import Any, Generator
from RPi.GPIO import PWM  # type: ignore
from contextlib import contextmanager
from abc import ABC, abstractmethod
import threading

from sound.sound_generator import SoundGenerator


class SoundPlayer(ABC):
    """Sound player base class."""

    @abstractmethod
    def set_frequency(self, freq: float) -> None: ...

    @abstractmethod
    def set_active(self, active: bool) -> None: ...


class SoundPlayerPWM(SoundPlayer):
    """Sound player class with PWM support."""

    def __init__(self, pwm: PWM, duty_cycle: int) -> None:
        self._pwm = pwm
        self._duty_cycle = duty_cycle

    def set_active(self, active: bool) -> None:
        self._pwm.ChangeDutyCycle(self._duty_cycle if active else 0)

    def set_frequency(self, freq: float) -> None:
        self._pwm.ChangeFrequency(freq)


class Sound(ABC):
    """Base class for a playable sound."""

    def __init__(self, player: SoundPlayerPWM) -> None:
        self.player = player
        self.generator = SoundGenerator()

    @abstractmethod
    def play(self, pwm: PWM) -> None:
        """Override this in child classes, sequence of sounds to be played."""
        ...

    def play_threaded(self) -> None:
        """Run self.play inside a thread. Avoids blocking while sound is played app loop."""

        threading.Thread(target=self.play, daemon=True).start()

    def pause(self, duration: float) -> None:
        """Play a pause."""

        sleep(duration)

    def arpeggio(self, freqs: list[float], step_duration: float) -> None:
        """Play a sequence of frequencies."""

        for freq in freqs:
            self.player.set_frequency(freq)
            sleep(step_duration)

    def note(self, freq: float, duration: float) -> None:
        """Play a single sound."""

        self.player.set_frequency(freq)
        sleep(duration)

    def noise(self, duration: float = 0.1, span: tuple = (50, 220)) -> None:
        """Play random noise sound."""

        import random

        end_time = time() + duration
        while time() < end_time:
            freq = random.randint(span[0], span[1])
            self.player.set_frequency(freq)
            sleep(0.001)

    @contextmanager
    def active(self) -> Generator[None, Any, None]:
        """Context manager handling enabling and disabling the PWM by toggling duty cycle value."""

        self.player.set_active(True)
        try:
            yield
        finally:
            self.player.set_active(False)

from core.settings import GPIOSettings, InputMappingSettings, OutputMappingSettings

import RPi.GPIO as GPIO  # type: ignore
from dataclasses import dataclass, asdict
from queue import Queue, Empty
from typing import TypeVar, Generic, Protocol
from abc import ABC, abstractmethod
from time import monotonic


@dataclass
class IO:
    """GPIO identification base class"""

    channel: int
    label: str


T = TypeVar("T", bound=IO)
M = TypeVar("M")


@dataclass
class Output(IO):
    """Output identification class"""


@dataclass
class Input(IO):
    """Input identification class"""


class IOManager(Generic[T, M], ABC):
    """GPIO management base class."""

    _pin_class: type[T]
    """Stored Pin class"""
    _mapping_class: type[M]
    """IO mapping settings class"""

    def __init__(self) -> None:
        self.pins: dict[str, T] = {}

        for label, channel in asdict(self._mapping_class()).items():
            self.pins[label] = self._pin_class(channel, label)
            self._setup(self.pins[label])

    @abstractmethod
    def _setup(self, pin: T) -> None:
        """
        Setup a single input with a GPIO channel number and label string and add it to `items` dictionary e.g.:

            GPIO.setup(pin.channel, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        """


class Outputs(IOManager[Output, OutputMappingSettings]):
    """Output GPIO management class."""

    _pin_class = Output
    _mapping_class = OutputMappingSettings

    def _setup(self, pin: Output) -> None:
        """Setup a single output with a GPIO channel number and label string and add it to `items` dictionary."""
        GPIO.setup(pin.channel, GPIO.OUT)

    def set(self, label: str, value: bool) -> None:
        """Enable or disable selected output by passing a label string and boolean."""
        GPIO.output(self.pins[label].channel, value)

    def get(self, label: str) -> bool:
        """Get current state of an output selected by label string."""
        return GPIO.input(self.pins[label].channel)


class Inputs(IOManager[Input, InputMappingSettings]):
    """Input GPIO management class."""

    _pin_class = Input
    _mapping_class = InputMappingSettings

    def __init__(self) -> None:
        super().__init__()

        self._events = Queue()
        self._last_pin: int = None
        self._last_press: float = 0

    def _setup(self, pin: Input) -> None:
        """Setup a single input with a GPIO channel number and label string and add it to `items` dictionary."""

        GPIO.setup(pin.channel, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        GPIO.add_event_detect(
            pin.channel,
            GPIO.RISING,
            callback=lambda ch: self._callback(ch, pin),
            bouncetime=GPIOSettings.debounce,
        )

    def _callback(self, _, pin: Input) -> None:
        """Input callback function."""

        now = monotonic()
        if (self._has_debounce_time_passed(now) and self._is_pin_same(pin)) or not self._is_pin_same(pin):
            self._events.put(pin)
            self._last_press = now
            self._last_pin = pin

    def get_event(self, timeout: float | None = None) -> Input | None:
        """Retrieve an input event from the queue (non-blocking or with timeout)."""

        try:
            return self._events.get(timeout=timeout)
        except Empty:
            return None

    def _has_debounce_time_passed(self, now: float) -> bool:
        return (now - self._last_press) > GPIOSettings.debounce * 0.001  # convert to s

    def _is_pin_same(self, pin: Input) -> bool:
        return self._last_pin == pin


class PWMSettingsLike(Protocol):
    channel: int
    duty_cycle: int
    frequency: int


class PWM:
    """PWM setup class"""

    def __init__(self, settings: PWMSettingsLike) -> None:

        GPIO.setup(settings.channel, GPIO.OUT, initial=GPIO.LOW)
        self.pwm = GPIO.PWM(settings.channel, settings.frequency)
        self.pwm.start(0)

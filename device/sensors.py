from core.settings import PowerSettings, MotionSettings
from device.i2c import LIS2DW12, INA219

from enum import IntEnum
from typing import TypeVar, Generic, Optional
from threading import Lock, Thread
from time import sleep
from abc import ABC, abstractmethod
from dataclasses import dataclass

T = TypeVar("T")


class SensorBase(Generic[T], ABC):
    """Sensor base class with optional threading for background polling and cached state."""

    def __init__(self, interval: Optional[float] = None, verbose: Optional[bool] = False) -> None:
        self._interval = interval
        self._state: Optional[T] = None
        self._verbose = verbose

        self._lock = Lock()
        self._is_running = False
        self._thread: Optional[Thread] = None

        if interval:
            self.start()

    def start(self) -> None:
        if not self._interval:
            return

        self._is_running = True
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._is_running = False
        if self._thread:
            self._thread.join()

    def _run(self) -> None:
        while self._is_running:
            self.read()
            sleep(self._interval)

    def read(self) -> T:
        """Read and return recent sensor measurement data. Result is cached in `_state`."""

        state = self._get_data()
        with self._lock:
            self._state = state
        if self._verbose:
            print(self._state.__dict__)
        return state

    @property
    def state(self) -> Optional[T]:
        """Cached sensor measurement. Gets updated after every `read()` call."""

        if not self._state:
            return
        with self._lock:
            return self._state

    @abstractmethod
    def _get_data(self) -> T:
        """
        Read data from the sensor by reading the I2C chip, must return a State-like object.
        This method should return converted sensor State object, usable in the app directly.
        """

        ...


class MotionState(IntEnum):
    HORIZONTAL = 1
    HORIZONTAL_180 = 3
    PORTRAIT_CW = 6
    PORTRAIT_CCW = 8


class MotionSensor(SensorBase[MotionState]):
    """Motion sensor returning discrete device orientation (EXIF-compatible)."""

    ORIENTATION_MAP = {
        "xl": MotionState.HORIZONTAL,
        "xh": MotionState.HORIZONTAL_180,
        "yl": MotionState.PORTRAIT_CCW,
        "yh": MotionState.PORTRAIT_CW,
    }

    def __init__(self) -> None:
        self._i2cdevice = LIS2DW12(MotionSettings)

        super().__init__(interval=None, verbose=True)  # disable threading

    def _get_data(self) -> MotionState:
        data: LIS2DW12.Data = self._i2cdevice.read()

        for attr, state in MotionSensor.ORIENTATION_MAP.items():
            if getattr(data, attr):
                return state

        return MotionState.HORIZONTAL


@dataclass
class PowerState:
    voltage: float
    current: float
    power: float
    battery_percent: int
    charging: bool
    battery_low: bool
    battery_critical: bool
    no_battery: bool


class PowerMonitor(SensorBase[PowerState]):
    """Power monitor providing battery metrics (voltage, current, power and derived flags)."""

    def __init__(self, interval=1.0) -> None:
        self._i2cdevice = INA219(PowerSettings)

        self._vbus_buffer: list[float] = []  # buffer average calculation to flatten measurements

        super().__init__(interval, verbose=True)  # enable threading

    def _get_data(self) -> PowerState:
        data: INA219.Data = self._i2cdevice.read()

        vbus = self._average(data.bus_voltage)
        power = data.power
        current = data.current * 0.001  # convert to A
        percent = int(self._percent(vbus))

        return PowerState(
            voltage=vbus,
            current=current,
            power=power,
            battery_percent=percent,
            charging=current >= 0,
            battery_low=percent <= PowerSettings.low_pct_val,
            battery_critical=vbus < PowerSettings.min_voltage,
            no_battery=not bool(int(vbus)),
        )

    def _average(self, value: float) -> float:
        """
        Calculate average of last n measured values.
        Uses _vbus_buffer attribute to store the values, number of elements
        in the buffer is defined with buffer_len variable.
        """
        buffer_len = 5

        self._vbus_buffer.append(value)
        self._vbus_buffer = self._vbus_buffer[-buffer_len:]
        return sum(self._vbus_buffer) / len(self._vbus_buffer)

    def _percent(self, vbus: float) -> int:
        """
        Calculate percentage of battery capacity.
        The value is interpolated based on baterry discharge curve.
        Uses moving average to smooth the value over time.
        """
        if vbus < PowerSettings.min_voltage:
            return 0

        A, B, C = 105.2741, 630.3598, 939.9309
        return int(A * vbus**2 - B * vbus + C)

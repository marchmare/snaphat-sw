from dataclasses import dataclass, field


@dataclass
class AppSettings:
    output_path: str = "camera/"
    assets_path: str = "assets/"


@dataclass(frozen=True)
class PowerSettings:
    address: int = 0x43
    bus: int = 1
    min_voltage: float = 3.0
    max_voltage: float = 4.0
    low_pct_val = 2


@dataclass(frozen=True)
class MotionSettings:
    address: int = 0x19
    bus: int = 1


@dataclass(frozen=True)
class DisplaySettings:
    resolution: tuple[int, int] = (320, 240)
    red_gain: float = 1.15
    green_gain: float = 1.315
    blue_gain: float = 0.85


@dataclass(frozen=True)
class BuzzerSettings:
    channel: int = 18
    duty_cycle: int = 50
    frequency: int = 2700


@dataclass
class DithererSettings:
    bayer_size: int = 8  # 2, 4 or 8
    bayer_size_range: tuple[int, int] = (2, 8)
    colors: int = 4  # min. 2
    colors_range: tuple[int, int] = (2, 4)


@dataclass(frozen=True)
class GPIOSettings:
    debounce: int = 150


@dataclass(frozen=True)
class InputMappingSettings:
    up: int = 19
    down: int = 5
    left: int = 6
    right: int = 13
    a: int = 27
    menu: int = 17
    b: int = 22
    shutter: int = 26


@dataclass(frozen=True)
class OutputMappingSettings:
    battery_low: int = 16  # TODO: update this for rev.1.1
    display_backlight: int = 12

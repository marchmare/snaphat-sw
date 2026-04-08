from typing import Protocol
from dataclasses import dataclass
import ctypes


class I2CSettingsLike(Protocol):
    address: int
    bus: int


class I2C:
    """I2C device interfacing base class"""

    def __init__(self, settings: I2CSettingsLike) -> None:
        from smbus import SMBus  # type: ignore

        self.bus = SMBus(settings.bus)
        self.addr = settings.address

        self._configure()

    def _read_u8(self, reg_addr: int) -> int:
        return self.bus.read_byte_data(self.addr, reg_addr)

    def _write_u8(self, reg_addr: int, value: int) -> None:
        self.bus.write_byte_data(self.addr, reg_addr, value & 0xFF)

    def _read_u16(self, reg_addr: int) -> int:
        data = self.bus.read_i2c_block_data(self.addr, reg_addr, 2)
        return (data[0] << 8) | data[1]

    def _write_u16(self, reg_addr: int, value: int) -> None:
        self.bus.write_i2c_block_data(self.addr, reg_addr, [(value >> 8) & 0xFF, value & 0xFF])

    def _configure(self) -> None:
        """Override this method with chip-specific register configuration."""


class LIS2DW12(I2C):
    """Class for interfacing with LIS2DW12 accelerometer"""

    @dataclass
    class Data:
        """LIS2DW12 output data storage class"""

        xh: bool
        xl: bool
        yh: bool
        yl: bool

    class Registers:
        """LIS2DW12 used registers map"""

        CTRL1 = 0x20  # Control register 1
        CTRL2 = 0x21  # Control register 2
        CTRL4_INT1 = 0x23  # Control register 4
        CTRL6 = 0x25  # Control register 6
        CTRL7 = 0x3F  # Control register 7
        SIXD_SRC = 0x3A
        """6D source register"""
        TAP_THS_X = 0x30
        """4D configuration enable and TAP threshold configuration"""

    def _configure(self) -> None:
        """
        LIS2DW12 setup - configuration for 6D orientation detection.
        Source: https://www.st.com/resource/en/design_tip/dt0097-setting-up-6d-orientation-detection-with-sts-mems-accelerometers-stmicroelectronics.pdf
        """
        self._soft_reset()

        reg1 = 0x6 << 4  # High-performance / low-power mode 200 Hz 12-bit resolution
        reg4 = 0x1 << 7  # 6D recognition is routed to INT1 pad
        reg6 = 0x1 << 2  # low noise configuration, full scale ±2 g
        reg7 = 0x1 << 5 | 0x1  # LPF2 output data sent to 6D interrupt function
        reg_thsx = 0x1 << 7 | 0x2  # threshold 60 degrees, enable 4D detection portrait/landscape position

        self.write(self.Registers.CTRL1, reg1)
        self.write(self.Registers.CTRL4_INT1, reg4)
        self.write(self.Registers.CTRL6, reg6)
        self.write(self.Registers.CTRL7, reg7)
        self.write(self.Registers.TAP_THS_X, reg_thsx)

    def _soft_reset(self) -> None:
        """Write 1 to 6th bit of REG_CTRL_REG2 register to reset the settings in the chip."""

        value = self._read(self.Registers.CTRL2) & (1 << 6)
        self.write(self.Registers.CTRL2, value)

    def _read(self, address: int) -> int:
        """Read function wrapper - use 8 bit read method"""

        return self._read_u8(address)

    def write(self, address: int, value: int) -> None:
        """Write function wrapper - use 8 bit read method"""

        self._write_u8(address, value)

    def read(self) -> Data:
        """
        Read LIS2DW12 orientation measurement.
        Returns Data object with x and y orientation booleans.
        """

        value = self._read(self.Registers.SIXD_SRC)
        return LIS2DW12.Data(
            xl=value & (1 << 0),
            xh=value & (1 << 1),
            yl=value & (1 << 2),
            yh=value & (1 << 3),
        )


class INA219(I2C):
    """Class for interfacing with INA219 power monitor chip"""

    @dataclass
    class Data:
        """INA219 output data storage class"""

        shunt_voltage: float
        bus_voltage: float
        current: float
        power: float

    class Registers:
        """INA219 used registers map"""

        CONFIG = 0x00
        SHUNT_VOLTAGE = 0x01
        BUS_VOLTAGE = 0x02
        POWER = 0x03
        CURRENT = 0x04
        CALIBRATION = 0x05

    class Constants:
        """INA219 configuration constants"""

        CURRENT_LSB = 0.1524  # LSB = 100uA per bit
        POWER_LSB = 0.003048  # LSB = 2mW per bit
        VBUS_LSB = 0.004  # LSB = 4mV per bit
        CALIBRATION_VAL = 26868

    def _configure(self) -> None:
        """
        INA219 setup - configuration compatible with Waveshare UPS HAT for RaspberryPi.
        Using values from: https://github.com/waveshare/UPS-Power-Module/blob/master/ups_display/ina219.py
        """

        vbus_range = 0x00  # vbus range: 16V
        gain = 0x01  # gain: +/- 80mV
        bus_adc_res = 0x0D  # resolution: 32 samples
        shunt_adc_res = 0x0D  # resolution: 32 samples
        mode = 0x07  # mode: shunt and bus, continuous

        configuration = vbus_range << 13 | gain << 11 | bus_adc_res << 7 | shunt_adc_res << 3 | mode
        self.write(self.Registers.CONFIG, configuration)

        self.write(self.Registers.CALIBRATION, self.Constants.CALIBRATION_VAL)

    def _read(self, address: int) -> int:
        """Read function wrapper - use 16 bit read method"""

        return self._read_u16(address)

    def write(self, address: int, value: int) -> None:
        """Write function wrapper - use 16 bit read method"""

        self._write_u16(address, value)

    def read(self) -> Data:
        """
        Read INA219 power measurement.
        Returns Data object with shunt voltage, bus voltage, current and power floats.
        """

        sv_value = self._read(self.Registers.SHUNT_VOLTAGE)
        bv_value = (self._read(self.Registers.BUS_VOLTAGE) >> 3) * self.Constants.VBUS_LSB
        c_value = self._read(self.Registers.CURRENT)
        p_value = self._read(self.Registers.POWER)

        return INA219.Data(
            shunt_voltage=ctypes.c_int16(sv_value).value * 0.01,  # return mV
            bus_voltage=bv_value,
            current=ctypes.c_int16(c_value).value * self.Constants.CURRENT_LSB * 0.001,  # return A
            power=ctypes.c_int16(p_value).value * self.Constants.POWER_LSB,
        )

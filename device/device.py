from core.settings import BuzzerSettings
import RPi.GPIO as GPIO  # type: ignore


class Device:
    """Device management class."""

    def __init__(self) -> None:
        """Initialize all device modules."""

        GPIO.setmode(GPIO.BCM)

        from device.gpio import Inputs, Outputs, PWM
        from device.sensors import PowerMonitor
        from device.display import Display

        self.power = PowerMonitor()
        self.buttons = Inputs()
        self.leds = Outputs()

        if self.power.state.battery_low:
            self.leds.set("battery_low", True)
        self.leds.set("display_backlight", True)

        self.display = Display()

        from device.sensors import MotionSensor
        from device.camera import Camera

        self.motion = MotionSensor()
        self.buzzer = PWM(BuzzerSettings)
        self.camera = Camera()

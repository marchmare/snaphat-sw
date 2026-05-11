from __future__ import annotations

from device.device import Device
from core.settings import BuzzerSettings
from core.app_modes import CameraPreview
from core.mass_storage import MassStorage
from core.palette import Palettes
from sound.assets import Sounds
from sound.core import SoundPlayerPWM

from os import system
from time import sleep
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.app_modes import AppMode

_FORCE_RUN = True
"""Flag to make the app run regardless of power monitor state (debug)"""


class App:
    """Root app management class."""

    def __init__(self) -> None:
        """Initialize the app."""

        self.device = Device()
        self.storage = MassStorage()
        self.palettes = Palettes()
        self.sounds = Sounds(player=SoundPlayerPWM(self.device.buzzer.pwm, BuzzerSettings.duty_cycle))

        self.mode: AppMode = CameraPreview(self)

        while self.is_running():
            self.loop()
        self.shutdown()

    def loop(self) -> None:
        """App loop."""

        self.handle_storage()
        self.handle_buttons()
        self.update_state()
        self.handle_leds()
        self.update_display()

    def handle_buttons(self) -> None:
        """Handle input button presses. Redirect to AppState as each mode handles buttons differently."""

        self.mode.handle_buttons()

    def handle_leds(self) -> None:
        """Handle indicator and utility LEDs."""

        if self.device.power.state.battery_low:
            self.device.leds.set("battery_low", True)

    def handle_storage(self) -> None:
        """Handle USB mass storage connect/disconnect."""

        usb_ready = self.device.usb.state.usb_ready

        if usb_ready and not self.storage.is_exposed and self.storage.expose_allowed:
            # detect USB cable plugged and mass storage is not exposed
            # switch to new state here
            # self.storage.expose_allowed = False
            # self.mode = ... <- TODO: write storage input pending state
            pass

        if not usb_ready and self.storage.is_exposed:
            # force cleanup if the USB host disconnected unexpectedly,
            # resets `expose_allowed` so plugging cable again will trigger the expose prompt
            self.storage.expose_allowed = True
            self.storage.unexpose()

        # user disconnect will be handled in the specific app modes

    def update_state(self) -> None:
        """Handle sensor outputs and other app state logic. Redirect to AppState as each mode handles device/UI state differently."""

        self.mode.update_state()

    def update_display(self) -> None:
        """Refresh display. Redirect to AppState as each mode handles display differently."""

        self.mode.update_display()

    def is_running(self) -> bool:
        """
        Return boolean value whether app should run or not. Depends on battery state.
        Set _FORCE_RUN to True to force running regardless of the battery state.
        """
        return not self.device.power.state.battery_critical or _FORCE_RUN

    def shutdown(self) -> None:
        """Graceful shutdown function."""

        from ui.screens import SCR_shutdown

        print("Power too low, shutting down.")
        self.device.display.update(SCR_shutdown)
        self.sounds.error.play()
        self.device.camera.stop()
        self.device.power.stop()

        sleep(1)

        self.device.leds.set("display_backlight", False)
        system("sudo poweroff")

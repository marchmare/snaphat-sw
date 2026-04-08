from __future__ import annotations

from device.sensors import MotionState
from core.image import RGBImage, CameraFrame
from core.settings import AppSettings, InputMappingSettings, DithererSettings
from ui.elements import TextBlock, NotificationTextBlock, BatteryIndicator
from ui.screens import SCR_gallery_empty, SCR_img_load_failed
from ui.core import UITarget, AlignX, AlignY

from os import listdir, makedirs
from typing import TYPE_CHECKING
from abc import abstractmethod, ABC

if TYPE_CHECKING:
    from core.app import App


class AppMode(ABC):
    """App mode template class."""

    def __init__(self, app: "App") -> None:
        self.app = app
        self.ui = UITarget()
        self.setup_ui()

        self.button_map = {
            button: getattr(self, f"on_click_{button}")
            for button in InputMappingSettings.__dict__.keys()
            if hasattr(self, f"on_click_{button}")
        }
        """Button map dictionary mapping button label (e.g. `menu`, `shutter`) with handler function named using `on_click_{label}` convention. 
        Labels are directly directly sourced from InputMappingsSettings."""

    @abstractmethod
    def setup_ui(self) -> None:
        """
        Override in child class, add UI components here, e.g.:

            self.ui.add(TextBlock(id="unique_name", x_align="center", y_align="bottom"))
        """
        ...

    @abstractmethod
    def prepare_base_frame(self) -> RGBImage:
        """
        Override in child class, prepare base frame RGBImage here.
        Must return RGBImage-like - loaded image, `CameraFrame` from camera capture or preloaded screen.
        Postprocess the frame if needed.
        """
        ...

    @abstractmethod
    def update_state(self) -> None:
        """
        Override in child class, here update added UI elements' attributes  or pass device state from sensors etc.:

            self.ui.unique_name.text = f"Updated value: {value}"
        """
        ...

    def update_display(self) -> None:
        """
        **Do not override**. Display update loop.
        Applies combined UI overlay to base frame and calls `display.update()`
        """

        ui_overlay = self.ui.to_RGBAImage(self.app.palettes.current)

        base_frame = self.prepare_base_frame()
        base_frame.merge(ui_overlay)

        self.app.device.display.update(base_frame)

    def handle_buttons(self) -> None:
        """
        **Do not override**. Button event handler.
        Reads handler function from `button_map` dictionary and calls it.
        To use handlers, write required `on_click_{label}` methods inside child AppState classes.
        """

        button = self.app.device.buttons.get_event(timeout=0.1)
        if not button:
            return
        if handler := self.button_map.get(button.label):
            handler()


class Gallery(AppMode):
    """Photo gallery mode. Displays photos saved on SD card."""

    def __init__(self, app: App, current_file: int = 0) -> None:
        super().__init__(app)
        makedirs(AppSettings.output_path, exist_ok=True)

        self.files = sorted(listdir(AppSettings.output_path))[::-1]
        self.current_file = current_file

    def setup_ui(self) -> None:
        self.ui.add(TextBlock(id="tb_filename", x_align=AlignX.CENTER, y_align=AlignY.BOTTOM))
        self.ui.add(TextBlock(id="tb_count"))

    def update_state(self) -> None:
        if not len(self.files):
            self.ui.tb_filename.visible = False
            self.ui.tb_count.text = "0/0"
        else:
            self.ui.tb_filename.visible = True
            self.ui.tb_filename.text = self.files[self.current_file]
            self.ui.tb_count.text = f"{self.current_file + 1}/{len(self.files)}"

    def prepare_base_frame(self) -> RGBImage:
        if not len(self.files):
            base_frame = SCR_gallery_empty
        else:
            try:
                base_frame = RGBImage.load(AppSettings.output_path + self.files[self.current_file])
            except AttributeError:
                base_frame = SCR_img_load_failed

        return base_frame

    def on_click_right(self) -> None:
        """BUTTON RIGHT: navigate to previous photo"""

        self.current_file = self.navigate(self.current_file, lambda v: v + 1, (0, len(self.files) - 1))

    def on_click_left(self) -> None:
        """BUTTON LEFT: navigate to next photo"""

        self.current_file = self.navigate(self.current_file, lambda v: v - 1, (0, len(self.files) - 1))

    def on_click_b(self) -> None:
        """BUTTON B: switch AppState to CameraPreview"""

        self.app.sounds.woop2.play()
        self.app.mode = CameraPreview(self.app)
        print("Switched to CameraPreview.")

    def navigate(self, value: int, change: callable, range: tuple[int, int]) -> int:
        new_value = change(value)

        if range[0] <= new_value <= range[1]:
            if new_value > value:
                self.app.sounds.woop.play()
            else:
                self.app.sounds.woop2.play()

            print(f"Moved to photo {new_value}")
            return new_value

        else:
            self.app.sounds.error.play()
            print(f"Reached {'last' if new_value > value else 'first'} photo.")
            return value


class CameraPreview(AppMode):
    """Default mode. Displays camera preview continuously and allows to alter Bayer dithering settings and color palette with button presses."""

    def __init__(self, app: App) -> None:
        super().__init__(app)

        from core.ditherer import Ditherer

        self.ditherer = Ditherer()
        self.camera_image: CameraFrame = None

    def setup_ui(self) -> None:
        self.ui.add(NotificationTextBlock(id=f"popup", x_align=AlignX.RIGHT, y_align=AlignY.BOTTOM))
        self.ui.add(BatteryIndicator(id="battery_indicator", x_align=AlignX.RIGHT))

    def update_state(self) -> None:
        self.ui.battery_indicator.update_state(self.app.device.power.state)

    def prepare_base_frame(self) -> RGBImage:
        base_frame = self.app.device.camera.capture()
        base_frame.dither(self.ditherer, self.app.palettes.current)

        self.camera_image = base_frame.copy()

        return base_frame

    def on_click_a(self) -> None:
        """BUTTON A: Toggle color palette."""

        self.app.sounds.ting.play_threaded()
        self.app.palettes.next()

        self.ui.popup.text = f"Color palette: {self.app.palettes.current.id}"
        self.ui.popup.show()

        print(f"{self.app.palettes.current} set!")

    def on_click_b(self) -> None:
        """BUTTON B: Capture current dithered frame."""

        self.app.sounds.click.play()
        orientation = self.app.device.motion.read()
        path = self.save_frame(orientation)

        print(f"Saved frame to {path}, orientation is {orientation.name}")

    def on_click_up(self) -> None:
        """BUTTON UP: increase Bayer level"""

        DithererSettings.colors = self.adjust_setting(
            DithererSettings.colors,
            lambda v: v + 1,
            DithererSettings.colors_range,
            "Colors",
        )

    def on_click_down(self) -> None:
        """BUTTON DOWN: decrease Bayer level"""

        DithererSettings.colors = self.adjust_setting(
            DithererSettings.colors,
            lambda v: v - 1,
            DithererSettings.colors_range,
            "Colors",
        )

    def on_click_left(self) -> None:
        """BUTTON LEFT: decrease Bayer matrix size"""

        DithererSettings.bayer_size = self.adjust_setting(
            DithererSettings.bayer_size,
            lambda v: v // 2,
            DithererSettings.bayer_size_range,
            "Bayer size",
        )

    def on_click_right(self) -> None:
        """BUTTON RIGHT: increase Bayer matrix size"""

        DithererSettings.bayer_size = self.adjust_setting(
            DithererSettings.bayer_size,
            lambda v: v * 2,
            DithererSettings.bayer_size_range,
            "Bayer size",
        )

    def on_click_menu(self) -> None:
        """BUTTON MENU: switch AppState to Gallery"""

        self.app.sounds.woop.play_threaded()
        self.app.mode = Gallery(self.app)
        print("Switched to Gallery.")

    def on_click_shutter(self) -> None:
        """BUTTON SHUTTER: Capture current dithered frame."""

        ...

        # TODO: revert from "b" in rev.1.1
        # self.app.sounds.click.play()
        # orientation = self.app.device.motion.read()
        # path = self.save_frame(orientation)

        # print(f"Saved frame to {path}, orientation is {orientation.name}")

    def adjust_setting(self, value: int, change: callable, range: tuple[int, int], label: str) -> int:
        """Resolve adjusting a setting based on initial value, passed adjusting function, setting allowed range and label for displaying messages."""

        new_value = change(value)

        if range[0] <= new_value <= range[1]:
            if new_value > value:
                self.app.sounds.woop.play_threaded()
            else:
                self.app.sounds.woop2.play_threaded()

            self.ui.popup.text = f"{label}: {new_value}"
            self.ui.popup.show()

            print(f"{label} set to {new_value}!")
            return new_value

        else:
            self.app.sounds.error.play_threaded()
            print(f"{label} is set to {value} and can't be {'higher' if new_value > value else 'lower'}")
            return value

    def save_frame(self, motion_state: MotionState) -> str:
        """Save recent CameraFrame to SD card."""

        return self.camera_image.save(AppSettings.output_path, motion_state.value)

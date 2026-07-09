from __future__ import annotations

from device.sensors import MotionState
from core.image import RGBImage, CameraFrame, EmptyRGBImage
from core.mass_storage import StorageState
from core.settings import AppSettings, InputMappingSettings, DithererSettings
from ui.elements import TextBlock, NotificationTextBlock, BatteryIndicator, BoxFrame, MenuList, MenuListItem
from ui.screens import SCR_gallery_empty, SCR_img_load_failed
from ui.core import UITarget, AlignX, AlignY

from os import listdir, makedirs
from typing import TYPE_CHECKING
from abc import abstractmethod, ABC
from dataclasses import dataclass

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


class USBHandler(AppMode):
    """USB handler parent class for USB connection related modes."""

    def __init__(self, app: App) -> None:
        super().__init__(app)

        from core.ditherer import Ditherer

        self.ditherer = Ditherer()
        self.camera_image: CameraFrame = None

    def update_state(self) -> None:
        if self.app.device.usb.state.usb_ready == False:
            self.disconnect()

    def prepare_base_frame(self) -> RGBImage:
        base_frame = EmptyRGBImage(fill=171)
        base_frame.dither(self.ditherer, self.app.palettes.current)

        return base_frame

    def disconnect(self) -> None:
        """Disconnect and flush storage state"""
        self.app.storage.unexpose()
        self.app.storage.enable()
        self.app.mode = CameraPreview(self.app)
        print("Switched to CameraPreview (disconnected).")

    def cancel(self) -> None:
        """Cancel connection callback"""
        self.app.sounds.woop2.play()
        self.app.storage.unexpose()
        self.app.storage.decline()
        self.app.mode = CameraPreview(self.app)
        print("Switched to CameraPreview (declined).")


class USBPlugged(USBHandler):
    """Dialog box asking the user wether camera files should get exposed to host or not."""

    def setup_ui(self) -> None:
        self.ui.add(BoxFrame(height=10, width=30, x_align=AlignX.CENTER, y_align=AlignY.CENTER))
        self.ui.add(TextBlock(text="USB plugged in!", x_align=AlignX.CENTER, y=66))
        self.ui.add(TextBlock(text="Want to share stored files?", x_align=AlignX.CENTER, y=88))

        self.ui.add(
            MenuList(
                id="menu",
                items=[
                    MenuListItem(text="Let's go!", callback=self.accept),
                    MenuListItem(text="Not now", callback=self.cancel),
                ],
                x_align=AlignX.CENTER,
                y=132,
                frame=False,
                sound_walk=self.app.sounds.tick,
            )
        )

    def prepare_base_frame(self) -> RGBImage:
        base_frame = EmptyRGBImage(fill=85)
        base_frame.dither(self.ditherer, self.app.palettes.current)

        return base_frame

    def on_click_up(self) -> None:
        """BUTTON UP: navigate to previous menu item"""

        self.ui.menu.current -= 1

    def on_click_down(self) -> None:
        """BUTTON DOWN: navigate to next menu item"""

        self.ui.menu.current += 1

    def on_click_a(self) -> None:
        """BUTTON A: select currently highlighted menu item"""

        self.ui.menu.selected.callback()

    def on_click_b(self) -> None:
        """BUTTON B: cancel connection"""

        self.cancel()

    def accept(self) -> None:
        """Accept connection callback"""
        self.app.sounds.woop.play()
        self.app.mode = USBConnecting(self.app)
        print("Switched to USBConnecting.")


class USBConnecting(USBHandler):
    """Intermediate screen visible while mass storage image is being prepared."""

    def __init__(self, app: App) -> None:
        super().__init__(app)

        self.app.storage.update_storage()
        self.app.storage.expose()

    def setup_ui(self) -> None:
        self.ui.add(BoxFrame(height=10, width=30, x_align=AlignX.CENTER, y_align=AlignY.CENTER))
        self.ui.add(TextBlock(text="Connecting...", x_align=AlignX.CENTER, y=66))
        self.ui.add(TextBlock(text="Just a minute!", x_align=AlignX.CENTER, y=88))

    def update_state(self) -> None:
        super().update_state()

        if self.app.storage.state == StorageState.EXPOSED:
            self.app.mode = USBConnected(self.app)


class USBConnected(USBHandler):
    """Dialog box showing when mass storage is exposed, allowing user to disconnect."""

    def __init__(self, app: App) -> None:
        super().__init__(app)

        self.app.storage.update_storage()
        self.app.storage.expose()

    def setup_ui(self) -> None:
        self.ui.add(BoxFrame(height=10, width=30, x_align=AlignX.CENTER, y_align=AlignY.CENTER))
        self.ui.add(TextBlock(text="Connected!", x_align=AlignX.CENTER, y=66))
        self.ui.add(TextBlock(text=":)", x_align=AlignX.CENTER, y=88))

        self.ui.add(
            MenuList(
                id="menu",
                items=[
                    MenuListItem(text="Disconnect", callback=self.cancel),
                ],
                x_align=AlignX.CENTER,
                y=132,
                frame=False,
                sound_walk=self.app.sounds.tick,
            )
        )

    def on_click_a(self) -> None:
        """BUTTON A: select currently highlighted menu item"""

        self.ui.menu.selected.callback()

    def on_click_b(self) -> None:
        """BUTTON B: switch AppState to CameraPreview"""

        self.app.sounds.woop2.play()
        self.app.mode = CameraPreview(self.app)
        print("Switched to CameraPreview.")


class StartMenu(AppMode):
    """Menu overlay accessible from CameraPreview mode, provides access to other modes."""

    def __init__(self, app: App) -> None:
        super().__init__(app)

        from core.ditherer import Ditherer

        self.ditherer = Ditherer()
        self.camera_image: CameraFrame = None

    def setup_ui(self) -> None:
        self.ui.add(NotificationTextBlock(id=f"popup", x_align=AlignX.RIGHT, y_align=AlignY.BOTTOM))
        self.ui.add(BatteryIndicator(id="battery_indicator", x_align=AlignX.RIGHT))

        items = [
            MenuListItem(text="View photos", label="gallery", callback=self.goto_gallery),
            MenuListItem(text="Settings", label="settings", callback=self.goto_settings),
            MenuListItem(text="About", label="about", callback=self.goto_about),
        ]
        self.ui.add(
            MenuList(
                id="menu",
                items=items,
                x_align=AlignX.RIGHT,
                y_align=AlignY.CENTER,
                sound_walk=self.app.sounds.tick,
            )
        )

    def update_state(self) -> None:
        self.ui.battery_indicator.update_state(self.app.device.power.state)

    def prepare_base_frame(self) -> RGBImage:
        base_frame = self.app.device.camera.capture()
        base_frame.dither(self.ditherer, self.app.palettes.current)

        self.camera_image = base_frame.copy()

        return base_frame

    def on_click_a(self) -> None:
        """BUTTON A: Accept currently selected menu item."""

        self.app.sounds.woop.play()
        self.ui.menu.selected.callback()

    def on_click_b(self) -> None:
        """BUTTON B: Return to CameraPreview."""

        self.app.sounds.woop2.play()
        self.app.mode = CameraPreview(self.app)

    def on_click_up(self) -> None:
        """BUTTON UP: navigate to previous menu item"""

        self.ui.menu.current -= 1

    def on_click_down(self) -> None:
        """BUTTON DOWN: navigate to next menu item"""

        self.ui.menu.current += 1

    def goto_gallery(self) -> None:
        """Callback: go to Gallery app mode."""

        self.app.mode = Gallery(self.app)
        print("Switched to Gallery.")

    def goto_settings(self) -> None:
        """Callback: go to Settings app mode."""

        self.app.mode = Settings(self.app)
        print("Switched to Settings.")

    def goto_about(self) -> None:
        """Callback: go to About app mode."""

        ...


class SettingScreen:
    def __init__(self, setting_group: Any, setting: str, title: str, items_mapping: dict[str, MenuListItem]) -> None:
        self.setting_group = setting_group
        self.setting = setting
        self.title = title
        self.items_mapping = items_mapping
        self.saved = self.resolve_saved()

    def resolve_saved(self) -> int:
        if not self.setting_group:
            return
        current_value = getattr(self.setting_group, self.setting)
        return list(self.items_mapping.keys()).index(current_value)

    def save(self, index) -> None: ...


class Settings(AppMode):
    """Settings mode. Displays screens for adjusting multiple runtime settings"""

    def __init__(self, app: App) -> None:
        self.settings = [
            SettingScreen(
                setting_group=AppSettings,
                setting="sound",
                title="Sound settings",
                items_mapping={
                    True: MenuListItem(text="Enable", callback=self.save_setting),
                    False: MenuListItem(text="Disable", callback=self.save_setting),
                },
            ),
            SettingScreen(
                setting_group=DithererSettings,
                setting="bayer_size",
                title="Bayer threshold map size",
                items_mapping={size: MenuListItem(text=str(size), callback=self.save_setting) for size in [2, 4, 8]},
            ),
            SettingScreen(
                setting_group=DithererSettings,
                setting="colors",
                title="Bayer color levels",
                items_mapping={
                    colors: MenuListItem(text=str(colors), callback=self.save_setting) for colors in [2, 3, 4]
                },
            ),
        ]

        super().__init__(app)

        from core.ditherer import Ditherer

        self.ditherer = Ditherer()
        self.camera_image: CameraFrame = None

        self.current = 0

    def save_setting(self) -> None: ...

    def update_state(self) -> None: ...

    def prepare_base_frame(self) -> RGBImage:
        base_frame = EmptyRGBImage(fill=171)
        base_frame.dither(self.ditherer, self.app.palettes.current)

        return base_frame

    def setup_ui(self) -> None:
        self.ui.add(BoxFrame(height=10, width=30, x_align=AlignX.CENTER, y_align=AlignY.CENTER))
        self.ui.add(TextBlock(text=self.settings[0].title, x_align=AlignX.CENTER, y=66))

        self.ui.add(
            MenuList(
                id="menu",
                items=list(self.settings[0].items_mapping.values()),
                x_align=AlignX.CENTER,
                y=121,
                frame=False,
                sound_walk=self.app.sounds.tick,
            )
        )

    def prepare_base_frame(self) -> RGBImage:
        base_frame = EmptyRGBImage(fill=85)
        base_frame.dither(self.ditherer, self.app.palettes.current)

        return base_frame

    def on_click_up(self) -> None:
        """BUTTON UP: navigate to previous menu item"""

        self.ui.menu.current -= 1

    def on_click_down(self) -> None:
        """BUTTON DOWN: navigate to next menu item"""

        self.ui.menu.current += 1

    def on_click_a(self) -> None:
        """BUTTON A: select currently highlighted menu item"""

        self.ui.menu.selected.callback()

    def on_click_b(self) -> None:
        """BUTTON B: Return to CameraPreview."""

        self.app.sounds.woop2.play()
        self.app.mode = CameraPreview(self.app)


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

        self.app.sounds.tick.play_threaded()
        self.app.palettes.next()

        self.ui.popup.text = f"Color palette: {self.app.palettes.current.id}"
        self.ui.popup.show()

        print(f"{self.app.palettes.current} set!")

    def on_click_shutter(self) -> None:
        """BUTTON SHUTTER: Capture current dithered frame."""

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
        self.app.mode = StartMenu(self.app)
        print("Switched to StartMenu.")

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

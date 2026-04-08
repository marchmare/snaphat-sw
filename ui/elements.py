from __future__ import annotations

from ui.core import UIElement, UIElementKwargs, UITimer
from ui.assets import FONT_8x11, SP_heart_empty, SP_heart_full, SP_sad_smiley
from time import monotonic

from typing import Unpack, TYPE_CHECKING

if TYPE_CHECKING:
    from device.sensors import PowerState


# Generic UI elements


class TextBlock(UIElement):
    """One line text block using FONT_8x11 spritesheet."""

    def __init__(self, text: str = "", **kwargs: Unpack[UIElementKwargs]) -> None:
        super().__init__(**kwargs)
        self.text = text

    def compose(self) -> None:
        for idx, c in enumerate(self.text):
            c_idx = ord(c) - 32
            sprite = FONT_8x11.get(c_idx)
            self.merge(sprite, FONT_8x11.sw * idx, 0)


class NotificationTextBlock(UIElement):
    """One line text block using FONT_8x11 spritesheet that dissappears after delay."""

    def __init__(self, text: str = "", duration: float = 1.5, **kwargs: Unpack[UIElementKwargs]) -> None:
        super().__init__(**kwargs)
        self.text = text
        self.duration = duration
        self._start = 0.0

    def compose(self) -> None:
        if monotonic() - self._start > self.duration:
            self.visible = False

        for idx, c in enumerate(self.text):
            c_idx = ord(c) - 32
            sprite = FONT_8x11.get(c_idx)
            self.merge(sprite, FONT_8x11.sw * idx, 0)

    def show(self) -> None:
        self._start = monotonic()
        self.visible = True


# Complex UI elements:


class BatteryIndicator(UIElement):
    def __init__(self, **kwargs: Unpack[UIElementKwargs]) -> None:
        super().__init__(**kwargs)

        self._blink_timer = UITimer(interval=0.5, frames=2)
        self._charge_timer = UITimer(interval=0.5, frames=5)
        self.power_state: PowerState | None = None

    def update_state(self, power_state: PowerState) -> None:
        self.power_state = power_state

    def compose(self) -> None:
        sprite_w = 16

        blink_frame = self._blink_timer.frame
        charge_frame = self._charge_timer.frame

        for idx in range(5):
            # no PowerState readings or no battery
            if not self.power_state or self.power_state.no_battery:
                sprite = SP_heart_empty
                self.merge(sprite, idx * sprite_w, 0)
                continue

            # # when charger is plugged
            # # animate filling up of the health bar
            if self.power_state.charging and round(self.power_state.power) > 0:
                sprite = SP_heart_full if idx <= charge_frame else SP_heart_empty

            # # critical battery level
            # # last heart blinks
            elif self.power_state.battery_low and idx == 0:
                sprite = SP_heart_full if blink_frame == 0 else SP_heart_empty

            # # normal indicator
            else:
                threshold = 20 * idx
                sprite = SP_heart_full if self.power_state.battery_percent >= threshold else SP_heart_empty

            self.merge(sprite, (idx * sprite_w) + 2, 0)


# Screen templates:


class ShutdownScreen(UIElement):
    """Display shutdown due to low battery screen"""

    def compose(self) -> None:
        main_text = TextBlock("battery low, see you later!")

        self.merge(main_text, 10, 140)
        self.merge(SP_sad_smiley, 10, 126)


class ImageLoadFailedScreen(UIElement):
    """Display error screen when image from gallery fails to load"""

    def __init__(self, **kwargs: Unpack[UIElementKwargs]) -> None:
        super().__init__(**kwargs)

    def compose(self) -> None:
        main_text = TextBlock("cannot load image")

        self.merge(main_text, 10, 140)
        self.merge(SP_sad_smiley, 10, 126)


class GalleryEmptyScreen(UIElement):
    """Display error screen when there's no images in gallery to load"""

    def compose(self) -> None:
        main_text = TextBlock("there's no photos made yet!")

        self.merge(main_text, 10, 140)
        self.merge(SP_sad_smiley, 10, 126)

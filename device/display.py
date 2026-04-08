from core.settings import DisplaySettings
from core.settings import AppSettings
from core.image import RGBImage


class Display:
    """Display management class."""

    def __init__(self) -> None:
        """
        Initialize display.

        Uses /dev/fb1 as framebuffer (requires setting up in cmdline.txt and config.txt).
        """
        from numpy import memmap

        self.size = DisplaySettings.resolution
        self.buffer = memmap("/dev/fb1", dtype="uint16", mode="w+", shape=(self.size[0] * self.size[1],))

        SCR_splash = RGBImage.load(f"{AppSettings.assets_path}/splashscreen.png")
        self.update(SCR_splash)

    def update(self, image: RGBImage) -> None:
        """Update framebuffer with provided image"""

        self.buffer[:] = image.to_buffer()

    def clear(self) -> None:
        """Update framebuffer with black pixels."""

        self.buffer[:] = 0x0

    def noise(self) -> None:
        """Update framebuffer with noise."""

        from numpy import random

        self.buffer[:] = random.randint(0x10000, size=(self.size[0] * self.size[1],), dtype="uint16")

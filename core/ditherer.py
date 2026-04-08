"""
Bayer-based multi-level dithering utilities.
"""

from numpy import array, uint8, tile, zeros, bool_, where
from numpy.typing import NDArray
from cv2 import equalizeHist, cvtColor, rotate, inRange, COLOR_RGB2GRAY, ROTATE_180

from core.settings import DithererSettings
from core.palette import Palette


class Ditherer:
    """
    Ordered Bayer dithering engine.

    Applies multi-level ordered dithering to an image using configurable
    Bayer matrices and palette-based color mapping.

    The number of levels and Bayer matrix size are controlled via `DithererSettings`.
    """

    BAYER2 = array(
        [
            [0, 128],
            [192, 64],
        ],
        dtype=uint8,
    )
    BAYER4 = array(
        [
            [0, 128, 32, 160],
            [192, 64, 224, 96],
            [48, 176, 16, 144],
            [240, 112, 208, 80],
        ],
        dtype=uint8,
    )
    BAYER8 = array(
        [
            [0, 128, 32, 160, 8, 136, 40, 168],
            [192, 64, 224, 96, 200, 72, 232, 104],
            [48, 176, 16, 144, 56, 184, 24, 152],
            [240, 112, 208, 80, 247, 120, 213, 84],
            [12, 140, 44, 172, 4, 132, 36, 164],
            [203, 76, 235, 107, 195, 68, 227, 101],
            [60, 188, 28, 156, 52, 180, 20, 148],
            [251, 123, 219, 91, 243, 116, 211, 84],
        ],
        dtype=uint8,
    )

    def prepare_threshold_map(self, array: NDArray[uint8]) -> NDArray[bool_]:
        """
        Generate a tiled Bayer threshold map matching the input shape.

        Accepts grayscale image array as an input.
        Bayer matrix size is determined by `DithererSettings`.
        """

        h, w = array.shape[:2]
        size = DithererSettings.bayer_size

        threshold_map = getattr(self, f"BAYER{DithererSettings.bayer_size}")
        array = tile(threshold_map, (h // size + 1, w // size + 1))

        return array[:h, :w]

    def apply_binary_bayer(self, array: NDArray[uint8], threshold_map) -> NDArray[bool_]:
        """Apply Bayer thresholding to produce a binary array."""

        return array > threshold_map

    def apply_color(self, array: NDArray[bool_], color1: NDArray[uint8], color2: NDArray[uint8]) -> NDArray[uint8]:
        """Convert a binary mask to a color image using two colors."""

        return where(array[..., None], color1, color2)

    def prepare_level_masks(self, array: NDArray[uint8]) -> list[NDArray[bool_]]:
        """Split image into intensity level masks.

        Accepts grayscale image array as an input.
        Returns list of binary masks, each corresponding to a specific intensity range.
        Number of levels is defined in `DithererSettings`.
        Masks are mutually exclusive and cover the full range.
        """

        levels = [round(i * 255 / (DithererSettings.colors - 1)) for i in range(DithererSettings.colors)]

        return [
            (inRange(array, levels[i], levels[i + 1] - (0 if i == DithererSettings.colors - 2 else 1)) > 0).astype(
                uint8
            )
            for i in range(DithererSettings.colors - 1)
        ]

    def dither(self, array: NDArray[uint8], palette: Palette) -> NDArray[uint8]:
        """
        Dither an array and colorize it using provided Palette.

        Accepts BGR image array (H, W, 3) as an input.
        """

        array = cvtColor(array, COLOR_RGB2GRAY)
        array = equalizeHist(array)
        tmap = self.prepare_threshold_map(array)
        masks = self.prepare_level_masks(array)

        colors = palette.get_colors(DithererSettings.colors)

        combined_image = zeros((*array.shape[:2], 3), dtype=uint8)

        for i, mask in enumerate(masks):
            image = equalizeHist((array * (mask > 0)))
            image = self.apply_binary_bayer(image, tmap)
            image = self.apply_color(image, colors[i + 1], colors[i])
            combined_image += mask[..., None] * image

        return rotate(combined_image, ROTATE_180)[:, :, ::-1]

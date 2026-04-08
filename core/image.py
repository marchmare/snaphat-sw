"""
Display-focused image abstraction layer.
Supports RGB (BGR), RGBA and 2-bit indexed images,
with conversion to RGB565 and basic compositing.

* All images are NumPy arrays + boolean mask for convenient blit operations.
* OpenCV is used for loading images, internally images use BGR ordering
* Display resolution is used to constrict the image dimensions.
"""

from __future__ import annotations

from typing import Optional, Protocol, TYPE_CHECKING
from numpy import uint8, uint16, bool_, ones, zeros, clip, array, where
from numpy.typing import NDArray
from copy import deepcopy

from core.palette import Palette, GRAYSCALE
from core.settings import DisplaySettings

if TYPE_CHECKING:
    from core.ditherer import Ditherer

D_WIDTH, D_HEIGHT = DisplaySettings.resolution
"""Display resolution"""
D_RED = DisplaySettings.red_gain
"""Display Red channel gain"""
D_GREEN = DisplaySettings.green_gain
"""Display Green channel gain"""
D_BLUE = DisplaySettings.blue_gain
"""Display Blue channel gain"""


class ImageLike(Protocol):
    image: NDArray[uint8]
    mask: NDArray[uint8]


class Image:
    """
    Base image container with optional transparency mask.

    Stores image data as a NumPy array and an associated boolean mask
    indicating visible pixels.

    Image is automatically cropped to display resolution.

    Attributes:
        image: NumPy array representing pixel data.
        mask: Boolean array of same height/width as image where `True` indicates visible pixels.
    """

    def __init__(self, image: NDArray[uint8], mask: Optional[NDArray[bool_]] = None) -> None:
        """
        Initialize an Image.

        Args:
            image: Input image uint8 array to be quantized.
            mask: Boolean array of shape (H, W), where `True` indicates visible pixels.
        """

        self.image = image
        self.mask = mask if mask.any() else ones(image.shape, dtype=bool_)
        self._crop_to_display()

    def merge(self, mix_img: ImageLike, x: int = 0, y: int = 0) -> None:
        """Composite another image onto this one at a given position, performed in-place."""
        try:
            h, w = mix_img.image.shape[:2]
            mh, mw = mix_img.mask.shape[:2]

            src_img = mix_img.image
            src_mask = mix_img.mask

            img_roi = self.image[y : y + h, x : x + w]
            msk_roi = self.mask[y : y + mh, x : x + mw]

            img_roi[src_mask] = src_img[src_mask]
            msk_roi[src_mask] = True

        except IndexError:
            raise TypeError(f"`mix_image` out of bounds of {DisplaySettings.resolution}")

    def _crop_to_display(self) -> None:
        """Crop the image and mask to the display resolution, performed in-place."""
        ih, iw = self.image.shape[:2]
        if D_WIDTH >= iw and D_HEIGHT >= ih:
            return

        self.image = self.image[:D_HEIGHT, :D_WIDTH]
        self.mask = self.mask[:D_HEIGHT, :D_WIDTH]

    def trim(self) -> None:
        """Trim the image and mask to the non-alpha image contents, performed in-place."""
        rows_with_nonalpha = where(self.mask.any(axis=1))[0]
        cols_with_nonalpha = where(self.mask.any(axis=0))[0]

        y_min, y_max = rows_with_nonalpha[0], rows_with_nonalpha[-1]
        x_min, x_max = cols_with_nonalpha[0], cols_with_nonalpha[-1]

        self.image = self.image[y_min : y_max + 1, x_min : x_max + 1]
        self.mask = self.mask[y_min : y_max + 1, x_min : x_max + 1]

    def copy(self) -> ImageLike:
        return deepcopy(self)

    def display(self) -> None:
        """
        *Debug method:*
        Display the stored image attribute.

        Converts from BGR to RGB.
        """

        from PIL import Image as PILImage

        img = PILImage.fromarray(self.image[..., ::-1], mode="RGB")
        img.show()

    def display_alpha(self) -> None:
        """
        *Debug method:*
        Display the stored mask attribute.
        """

        from PIL import Image as PILImage

        mask = self.mask.astype(uint8) * 255
        img = PILImage.fromarray(mask, mode="L")
        img.show()

    @staticmethod
    def is_grayscale(image: NDArray[uint8]) -> bool:
        return image.ndim == 2

    @staticmethod
    def is_rgb(image: NDArray[uint8]) -> bool:
        return image.ndim == 3 and image.shape[2] == 3

    @staticmethod
    def is_rgba(image: NDArray[uint8]) -> bool:
        return image.ndim == 3 and image.shape[2] == 4

    @staticmethod
    def is_mask(image: NDArray[uint8]) -> bool:
        return image.dtype == bool_

    @staticmethod
    def is_indexed(image: NDArray[uint8]) -> bool:
        return image.max() <= 3


class RGBAImage(Image):
    """
    Image wrapper for 8-bit 3-channel color images.

    Stores `image` data as NumPy uint8 array of shape (H, W, 3),
    and `mask` data as bool array of shape (H, W).
    """

    @classmethod
    def load(cls, path: str) -> "RGBAImage":
        """Load an image from disk."""

        from cv2 import imread, IMREAD_UNCHANGED

        img = imread(path, IMREAD_UNCHANGED)
        image = img[..., :3]
        mask = img[..., 3] > 0 if cls.is_rgba(img) else ones(img.shape[:2], dtype=bool_)
        return cls(image, mask)


class IndexedImage(Image):
    """
    Image wrapper for 2-bit indexed images with transparency mask.

    Stores `image` data as 2D NumPy uint8 array of shape (H, W), each pixel is an index in range [0, 3],
    and `mask` data as bool array of shape (H, W).
    """

    def __init__(self, image: NDArray[uint8], mask: NDArray[bool_]) -> None:
        """
        Args:
            image: Input image RGB-like uint8 array to be quantized.
            mask: Boolean array of shape (H, W), where `True` indicates visible pixels.
        """

        super().__init__(self._to_indexed(image), mask)

    @classmethod
    def load(cls, path: str) -> "IndexedImage":
        """Load an image from disk."""

        from cv2 import imread, IMREAD_UNCHANGED

        img = imread(path, IMREAD_UNCHANGED)
        image = img[..., 0]
        mask = img[..., 3] > 0 if cls.is_rgba(img) else ones(img.shape[:2], dtype=bool_)
        return cls(image, mask)

    @staticmethod
    def _to_indexed(image: NDArray[uint8]) -> NDArray[uint8]:
        """Convert an image to 2-bit indexed format. If the image is already indexed, it is returned unchanged."""

        if Image.is_indexed(image):
            return image

        return (image // 85).astype(uint8)

    def invert(self) -> None:
        """Invert the colors of the image array."""
        self.image = 3 - self.image

    def to_RGBAImage(self, palette: Palette) -> RGBAImage:
        """Convert the indexed image to an RGBAImage, colorized using a Palette."""

        colors = array(palette.get_colors(4), dtype=uint8)[:, ::-1]
        return RGBAImage(colors[self.image], self.mask)

    def to_RGBImage(self, palette: Palette) -> RGBAImage:
        """Convert the indexed image to an RGBImage, colorized using a Palette."""

        colors = array(palette.get_colors(4), dtype=uint8)[:, ::-1]
        return RGBImage(colors[self.image])

    def display(self) -> None:
        """
        *Debug method:*
        Display the indexed image using a default grayscale palette.
        """

        from PIL import Image as PILImage

        colors = array(GRAYSCALE.get_colors(4))[:, ::-1]
        rgb = colors[self.image]
        img = PILImage.fromarray(rgb, mode="RGB")
        img.show()


class EmptyIndexedImage(IndexedImage):
    """
    Predefined empty indexed image with configurable mask.

    Can be initialized with width and height parameters to create image of specified dimensions.
    If either with or height is not provided or 0, Display resolution will be used.
    """

    def __init__(self, width: Optional[int] = 0, height: Optional[int] = 0) -> None:
        if width == 0 or height == 0:
            _w = D_WIDTH
            _h = D_HEIGHT
        else:
            _w = width
            _h = height

        self.image = zeros((_h, _w), dtype=uint8)
        self.mask = zeros((_h, _w), dtype=bool_)


class RGBImage(Image):
    """
    Image wrapper for 8-bit 3-channel color images.

    Stores image data as NumPy uint8 array of shape (H, W, 3).
    """

    def __init__(self, image: NDArray[uint8]) -> None:
        """
        Args:
            image: Input image RGB-like uint8 array to be quantized.
        """

        super().__init__(image, ones(image.shape, dtype=bool_))

    @classmethod
    def load(cls, path: str) -> "RGBImage":
        """Load an image from disk. Ignores orientation metadata."""

        from cv2 import imread, IMREAD_IGNORE_ORIENTATION, IMREAD_COLOR

        image = imread(path, IMREAD_COLOR | IMREAD_IGNORE_ORIENTATION)
        return cls(image)

    def to_RGB565(self) -> NDArray[uint16]:
        """
        Convert the image from RGB888 to RGB565 format.

        Applies per-channel gain correction using DisplaySettings before conversion.
        """

        image = self.image.copy()
        image[..., 0] = clip(image[..., 0] * D_BLUE, 0, 255).astype(uint8)
        image[..., 1] = clip(image[..., 1] * D_GREEN, 0, 255).astype(uint8)
        image[..., 2] = clip(image[..., 2] * D_RED, 0, 255).astype(uint8)

        b = (image[:, :, 0] >> 3).astype(uint16)
        g = (image[:, :, 1] >> 2).astype(uint16) << 5
        r = (image[:, :, 2] >> 3).astype(uint16) << 11

        return r | g | b

    def to_buffer(self) -> NDArray[uint16]:
        """
        Convert the image to a flattened RGB565 buffer.

        Returns 1D uint16 array suitable for direct framebuffer writes, e.g. `buffer[:] = image.to_buffer()`.
        """

        return self.to_RGB565().flatten()

    def save(self, output_dir: str, orientation: int = 1) -> str | None:
        """
        Save the image as a PNG file with EXIF orientation metadata.

        Image is converted from BGR to RGB before saving.
        Filename is generated from the current timestamp.
        """

        from PIL import Image as PILImage
        import piexif  # type: ignore
        from datetime import datetime
        from os import makedirs

        makedirs(output_dir, exist_ok=True)
        file_path = f"{output_dir}/{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        img = PILImage.fromarray(self.image[..., ::-1], mode="RGB")

        exif_dict = {"0th": {piexif.ImageIFD.Orientation: orientation}}
        exif_bytes = piexif.dump(exif_dict)

        img.save(file_path, exif=exif_bytes)
        return file_path


class CameraFrame(RGBImage):
    """
    Image captured from a camera source.

    Inherits from RGBImage, stores image data as NumPy uint8 array of shape (H, W, 3).
    """

    def dither(self, ditherer: "Ditherer", palette: Palette) -> None:
        """
        Apply dithering to the image using a given Ditherer and Palette.

        Replaces the internal image with a dithered and colorized version in-place.
        """

        self.image = ditherer.dither(self.image, palette)

    def save(self, output_dir: str, orientation: int = 1) -> str | None:
        """
        Save the image as a PNG file with EXIF orientation metadata.

        Image is converted from BGR to RGB before saving.
        Filename is generated from the current timestamp.
        """

        from PIL import Image as PILImage
        import piexif  # type: ignore
        from datetime import datetime
        from os import makedirs

        makedirs(output_dir, exist_ok=True)
        file_path = f"{output_dir}/{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        img = PILImage.fromarray(self.image[..., ::-1], mode="RGB")

        exif_dict = {"0th": {piexif.ImageIFD.Orientation: orientation}}
        exif_bytes = piexif.dump(exif_dict)

        img.save(file_path, exif=exif_bytes)
        return file_path

from core.image import IndexedImage, EmptyIndexedImage
from numpy.typing import NDArray
from numpy import uint8, bool_, ones, ndenumerate

from core.settings import AppSettings

ASSETS_PATH = AppSettings.assets_path
"""Path to image assets for the app UI"""


class Spritesheet(IndexedImage):
    """
    Indexed image containing tileset of sprite images accessible by their index.

    Sprite width and height must be constant across the entire loaded Spritesheet.
    Use `to_lookup()` method to preload all sprites from the Spritesheet in a dictionary.
    """

    def __init__(self, image: NDArray[uint8], mask: NDArray[uint8], sprite_width: int, sprite_height: int) -> None:
        """
        Args:
            image: Input image RGB-like uint8 array to be quantized.
            mask: Boolean array of shape (H, W), where `True` indicates visible pixels.
            sprite_width: width of the single sprite in the Spritesheet
            sprite_height: height of the single sprite in the Spritesheet
        """
        super().__init__(image, mask)

        self.sw = sprite_width
        self.sh = sprite_height

        h, w = self.image.shape[:2]
        self.rows = h / self.sh
        self.cols = w / self.sw

        if not self.rows.is_integer() or not self.cols.is_integer():
            raise ValueError(f"Spritesheet size is not dividable by sprite width and height)")

        self.lookup = {idx: self.get_indexed_image(idx) for idx in range(int(self.rows * self.cols))}

    def get(self, index: int) -> IndexedImage:
        """Extract a single sprite from the spritesheet lookup as an IndexedImage. Index is interpreted in row-major order."""
        return self.lookup.get(index)

    def get_indexed_image(self, index: int) -> IndexedImage:
        """Extract a single sprite from the spritesheet imgae as an IndexedImage. Index is interpreted in row-major order."""
        x = index % int(self.cols) * self.sw
        y = index // int(self.cols) * self.sh

        return IndexedImage(
            self.image[y : y + self.sh, x : x + self.sw].copy(),
            self.mask[y : y + self.sh, x : x + self.sw].copy(),
        )

    def to_lookup(self) -> dict[int, IndexedImage]:
        """Return dictionary with IndexedImage objects mapped to integer keys. Stores additional `width` and `height` items defining single sprite shape."""
        lookup = {idx: self.get_indexed_image(idx) for idx in range(len(self.rows) * len(self.col))}
        return lookup

    @classmethod
    def load(cls, path: str, sprite_width: int, sprite_height: int) -> "Spritesheet":
        """Load an image from disk."""

        from cv2 import imread, IMREAD_UNCHANGED

        img = imread(path, IMREAD_UNCHANGED)
        image = img[..., 0]
        mask = img[..., 3] > 0 if cls.is_rgba(img) else ones(img.shape[:2], dtype=bool_)

        return cls(image, mask, sprite_width, sprite_height)


class CombinedSprite(IndexedImage):
    EMPTY = 255
    """Reserved Empty sprite index value"""

    @classmethod
    def compose(cls, spritesheet: Spritesheet, indexes: NDArray[uint8]) -> "CombinedSprite":
        if indexes.ndim != 2:
            raise ValueError("Sprite indexes must be an 2D array")

        _spritesheet = spritesheet
        _sh = _spritesheet.sh
        _sw = _spritesheet.sw

        _container = EmptyIndexedImage(_sw * indexes.shape[1], _sh * indexes.shape[0])

        for (row, col), idx in ndenumerate(indexes):
            if idx == cls.EMPTY:
                continue
            sprite = _spritesheet.get(idx)
            _container.merge(sprite, _sw * col, _sh * row)

        return cls(_container.image, _container.mask)

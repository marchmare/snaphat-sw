"""Color palettes definitions"""

from numpy import uint8, array, array_equal
from numpy.typing import NDArray
from typing import Optional

Color = tuple[int, int, int]
"""RGB color type"""


class Palette:
    """Single color palette for indexed images."""

    colors: tuple[Color, Color, Color, Color]
    """Color tuple with 4 Color values from darkest to lightest."""

    def __init__(self, color1: Color, color2: Color, color3: Color, color4: Color, id: Optional[str] = None) -> None:
        self._colors: tuple[NDArray[uint8], NDArray[uint8], NDArray[uint8], NDArray[uint8]] = (
            self.color2uint8(color1),
            self.color2uint8(color2),
            self.color2uint8(color3),
            self.color2uint8(color4),
        )
        self.id = id

    def get_colors(self, levels: int) -> tuple[NDArray[uint8], NDArray[uint8], NDArray[uint8], NDArray[uint8]]:
        """Get colors list of the palette. Returned list can be 2 or 4 elements, depending on the Bayer level integer passed."""

        if levels == 2:
            # for palettes with BLACK and WHITE first and last colors, return first and second color unless its 'Grayscale' palette.
            if (
                array_equal(self._colors[0], _BLACK)
                and array_equal(self._colors[3], _WHITE)
                and not self.id == _GRAYSCALE_ID
            ):
                return self._colors[0], self._colors[1]
            return self._colors[0], self._colors[-1]

        return self._colors

    def __repr__(self) -> str:
        colors = tuple(tuple(c.tolist()) for c in self._colors)
        return f"{type(self).__name__}{colors}"

    @staticmethod
    def color2uint8(color: tuple[int, int, int]) -> NDArray[uint8]:
        """Convert an RGB tuple to an uint8 array."""

        return array(color, dtype=uint8)


_GRAYSCALE_ID = "Grayscale"
GRAYSCALE = Palette((0, 0, 0), (85, 85, 85), (171, 171, 171), (255, 255, 255), id=_GRAYSCALE_ID)
"""Default grayscale palette"""

_BLACK = Palette.color2uint8((0, 0, 0))
"""Black color uint8"""
_WHITE = Palette.color2uint8((255, 255, 255))
"""White color uint8"""


class Palettes:
    """Palettes cycling lookup class"""

    def __init__(self) -> None:

        self._items: list[Palette] = [
            Palette((0, 0, 0), (113, 88, 156), (223, 149, 167), (255, 255, 255), id="Pastel 1"),
            Palette((146, 97, 202), (209, 72, 186), (248, 151, 182), (181, 209, 249), id="Pastel 2"),
            Palette((41, 65, 57), (57, 88, 73), (90, 121, 66), (123, 130, 16), id="Gameboy DMG"),
            Palette((24, 24, 24), (74, 80, 56), (140, 146, 107), (198, 203, 165), id="Gameboy Pocket"),
            Palette((0, 81, 56), (0, 105, 74), (0, 154, 116), (0, 177, 132), id="Gameboy Light"),
            GRAYSCALE,
            Palette((0, 0, 0), (206, 0, 49), (239, 190, 82), (255, 255, 255), id="Orange"),
            Palette((57, 0, 0), (132, 0, 156), (214, 130, 214), (181, 203, 206), id="Purple"),
            Palette((0, 32, 49), (123, 89, 140), (222, 162, 123), (247, 211, 165), id="Gameboy Color 4E"),
            Palette((33, 32, 90), (0, 177, 247), (222, 162, 198), (247, 243, 123), id="Pastel Tricolor"),
        ]
        self._index = 0
        self.current: Palette = self._items[self._index]

    def set_current(self, palette: Palette) -> None:
        """Set current color palette"""

        self.current = palette

    def next(self) -> None:
        """Iterate over Palettes list while setting `current`"""
        self._index = (self._index + 1) % len(self._items)
        self.current = self._items[self._index]

    def previous(self) -> None:
        """Iterate over Palettes list while setting `current`"""
        self._index = (self._index - 1) % len(self._items)
        self.current = self._items[self._index]

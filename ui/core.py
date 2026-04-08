from __future__ import annotations

from core.settings import DisplaySettings
from core.image import EmptyIndexedImage, IndexedImage, ImageLike
from abc import ABC, abstractmethod
from typing import TypedDict, Optional, TYPE_CHECKING
from time import monotonic
from uuid import uuid4
from enum import Enum

if TYPE_CHECKING:
    from core.image import RGBImage, RGBAImage, Palette


class UIContainerImage(EmptyIndexedImage):
    """Empty transparent image base to serve as a container for UI components."""

    ...


class CombinedElement(IndexedImage):
    """UIElement baked into IndexedImage"""

    ...


class AlignY(Enum):
    TOP = 0
    BOTTOM = 1
    CENTER = 2


class AlignX(Enum):
    LEFT = 0
    RIGHT = 1
    CENTER = 2


class UITarget:
    """
    UI layer composed of UIElement objects.
    After composing, serves as single completely rendered UI overlay.
    Intended to be merged onto RGBImage-like (e.g. CameraFrame).
    """

    def __init__(self) -> None:
        self.shape = DisplaySettings.resolution[::-1]  # check if used
        self.elements: dict[str, UIElement] = {}

    def add(self, element: "UIElement") -> None:
        """
        Add a UIElement, storing it in `elements` dictionary by its `id` string and
        setting an attribute using the same string.
        """

        self.elements[element.id] = element
        setattr(self, element.id, element)

    def _update_container(self, _container: UIContainerImage) -> None:
        """
        Iterate over elements added to UITarget and add them to UI container.
        Resolves element's vertical and horizontal align in relation to Display.
        """

        for elem in self.elements.values():
            combined_elem = elem.combine()

            if not elem.visible or elem._empty:
                continue

            x = self._resolve_x(elem, combined_elem)
            y = self._resolve_y(elem, combined_elem)

            _container.merge(combined_elem, int(x), int(y))

    def to_RGBImage(self, palette: Palette) -> RGBImage:
        """Update UITarget's container with added UIElments and convert the overlay to RGBImage using a Palette."""

        _container = UIContainerImage()
        self._update_container(_container)
        return _container.to_RGBImage(palette)

    def to_RGBAImage(self, palette: Palette) -> RGBAImage:
        """Update UITarget's container with added UIElments and convert the overlay to RGBAImage using a Palette."""

        _container = UIContainerImage()
        self._update_container(_container)
        return _container.to_RGBAImage(palette)

    def _resolve_x(self, element: UIElement, combined_element: CombinedElement) -> int | float:
        """Calculate horizontal coordinate based on `x_align` attribute of the UIElement."""

        _, target_width = self.shape
        _, elem_width = combined_element.image.shape[:2]

        match element.x_align:
            case AlignX.LEFT:
                return element.x
            case AlignX.CENTER:
                return (target_width / 2) - (elem_width / 2)
            case AlignX.RIGHT:
                return target_width - elem_width - element.x
            case _:
                return element.x

    def _resolve_y(self, element: UIElement, combined_element: CombinedElement) -> int | float:
        """Calculate vertical coordinate based on `y_align` attribute of the UIElement."""

        target_height, _ = self.shape
        elem_height, _ = combined_element.image.shape[:2]

        match element.y_align:
            case AlignY.TOP:
                return element.y
            case AlignY.CENTER:
                return (target_height / 2) - (elem_height / 2)
            case AlignY.BOTTOM:
                return target_height - elem_height - element.y
            case _:
                return element.y


class UIElementKwargs(TypedDict):
    id: str
    x: int
    y: int
    x_align: AlignX
    y_align: AlignY


class UIElement(ABC):
    """
    UI element with defined graphic components and logic.

    Graphic components are trimmed to non-alpha pixels.
    """

    def __init__(
        self,
        *,
        id: Optional[str] = None,
        x: int = 0,
        y: int = 0,
        x_align: AlignX = AlignX.LEFT,
        y_align: AlignY = AlignY.TOP,
    ) -> None:
        """
        Args:
            id: identificator string for UIElement instnace
            x: UIElement container's position on display in x axis
            y: UIElement container's position on display in y axis
            x_align: UIElement container horizontal alignment on the screen
            y_align: UIElement container vertical alignment on the screen

        By default Display origin point is upper-left corner (`x_align = "LEFT"`, `y_align="TOP"`).
        """

        self._container = UIContainerImage()
        """UIElement container for composed element components, flushed every rendered frame"""

        self.id = id if id else "_" + str(uuid4())[:8]
        self.x = x
        self.y = y
        self.x_align = x_align
        self.y_align = y_align

        self.visible: bool = True
        self._empty: bool = False

    @abstractmethod
    def compose(self) -> None:
        """UI element layout and logic definition. Override in child classes."""
        ...

    def _update_container(self) -> None:
        """
        Run `compose()` method and update this element's container.
        Checks if container's mask has any pixels afterwards and sets `_empty` flag accordingly.
        """

        self._container = UIContainerImage()

        self.compose()

        if self._container.mask.any():
            self._container.trim()
            self._empty = False
        else:
            self._empty = True

    def combine(self) -> CombinedElement:
        """Prepare container with element and return element as CombinedElement."""

        self._update_container()
        return CombinedElement(self._container.image, self._container.mask)

    def merge(self, asset: ImageLike | "UIElement", x: int = 0, y: int = 0) -> None:
        """
        Composite another image or UIElement onto this UIElement's container at a given position, performed in-place.
        Position is applied from origin point in upper-left corner.
        Use within `compose()` method.
        """

        if isinstance(asset, UIElement):
            asset = asset.combine()

        self._container.merge(asset, x, y)


class UITimer:
    """
    Class handling timing for UI animation frames.
    Advances the current frame at a fixed time interval when accessed.
    """

    def __init__(self, interval: float = 0.5, frames: int = 2) -> None:
        """
        Initialize the timer.

        Args:
            interval: Time in seconds between frame updates.
            frames: Total number of frames in the animation loop.
        """
        self._interval = interval
        self._frames = frames

        self._current_frame = 0
        self._last_step = monotonic()

    def _step(self) -> None:
        """Update the current frame if enough time has elapsed."""

        now = monotonic()
        if now - self._last_step >= self._interval:
            self._current_frame = (self._current_frame + 1) % self._frames
            self._last_step = now

    @property
    def frame(self) -> int:
        """Return the current frame index, advancing the timer if needed."""
        self._step()
        return self._current_frame

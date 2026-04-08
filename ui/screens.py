from ui.core import UITarget, UIElement, AlignY, AlignX
from ui.elements import ShutdownScreen, GalleryEmptyScreen, ImageLoadFailedScreen
from core.image import RGBImage
from core.palette import GRAYSCALE


def build_screen(template: UIElement) -> RGBImage:
    target = UITarget()
    target.add(template)
    return target.to_RGBImage(GRAYSCALE)


# Preloaded screens:

SCR_shutdown = build_screen(ShutdownScreen(id="SCR_shutdown", x=10, y_align=AlignY.CENTER, x_align=AlignX.CENTER))
SCR_gallery_empty = build_screen(
    GalleryEmptyScreen(id="SCR_gallery_empty", x=10, y_align=AlignY.CENTER, x_align=AlignX.CENTER)
)
SCR_img_load_failed = build_screen(
    ImageLoadFailedScreen(id="SCR_img_load_failed", x=10, y_align=AlignY.CENTER, x_align=AlignX.CENTER)
)

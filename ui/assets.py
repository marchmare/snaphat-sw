from ui.sprites import Spritesheet, CombinedSprite
from numpy import array

from core.settings import AppSettings

ASSETS_PATH = AppSettings.assets_path
"""Path to image assets for the app UI"""

# Preloaded spritesheets:
FONT_8x11 = Spritesheet.load(f"{ASSETS_PATH}/font_8x11.png", 8, 11)
UI_8x11 = Spritesheet.load(f"{ASSETS_PATH}/ui_8x11.png", 8, 11)

# Preloaded sprites:
SP_heart_empty = CombinedSprite.compose(UI_8x11, array([[0, 1]]))
SP_heart_full = CombinedSprite.compose(UI_8x11, array([[2, 3]]))
SP_sad_smiley = CombinedSprite.compose(UI_8x11, array([[4, 5]]))
SP_happy_smiley = CombinedSprite.compose(UI_8x11, array([[6, 7]]))

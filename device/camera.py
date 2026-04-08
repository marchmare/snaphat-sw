from picamera2 import Picamera2, Preview  # type: ignore
from core.image import CameraFrame
from core.settings import DisplaySettings


class Camera:
    """Camera management class."""

    def __init__(self) -> None:
        self._camera = Picamera2()
        cam_cfg = self._camera.create_preview_configuration({"size": DisplaySettings.resolution, "format": "RGB888"})
        self._camera.configure(cam_cfg)
        self.apply_settings()
        self._camera.start_preview(Preview.NULL)
        self._camera.start()

    def capture(self) -> CameraFrame:
        """Returns frame from the camera as an array."""

        return CameraFrame(self._camera.capture_array())

    def stop(self) -> None:
        """Disable camera."""

        self._camera.stop_preview()

    def apply_settings(self) -> None:
        """Update camera controls."""

        controls = {
            "Brightness": 0.0,
            "Contrast": 1.0,
        }
        self._camera.set_controls(controls)

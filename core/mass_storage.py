from core.settings import AppSettings

from pathlib import Path
from os import sync
from subprocess import run
from shutil import copy2

# pathlib AppSetiings paths:
MASS_STORAGE = Path(AppSettings.mass_storage_path)
CAMERA_OUTPUT = Path(AppSettings.output_path)
MOUNT_POINT = Path(AppSettings.mass_storage_mount_path)


class MassStorage:
    """USB mass storage emulation class."""

    def __init__(self) -> None:
        """
        Initialize USB mass storage (RaspberryPi USB OTG gadget).
        """

        self.create_storage_file()
        self.is_exposed = False
        self.expose_allowed = True

    def create_storage_file(self) -> None:
        """
        Create virtual mass storage disk file, format as FAT32.
        Skips this step if storage file already exists.
        """

        if MASS_STORAGE.exists():
            print("Storage already exists.")
            return

        print("Allocating space for storage virtual disk")
        with MASS_STORAGE.open("wb") as f:
            f.truncate(AppSettings.mass_storage_size)

        run(
            ["mkfs.vfat", "-F", "32", "-I", str(MASS_STORAGE)],
            check=True,
        )

    def expose(self) -> None:
        """Expose mass storage image over USB"""

        self._stop_module()
        run(
            ["/sbin/modprobe", "g_mass_storage", f"file={str(MASS_STORAGE)}", "stall=0", "ro=1", "removable=1"],
            check=True,
        )
        self.is_exposed = True

    def unexpose(self) -> None:
        """Unexpose mass storage image over USB."""

        self._stop_module()
        run(
            ["/sbin/modprobe", "g_mass_storage", "stall=0", "ro=1", "removable=1"],
            check=True,
        )
        self.is_exposed = False

    def _stop_module(self) -> None:
        """Disable g_mass_storage."""

        run(["/sbin/rmmod", "g_mass_storage"], check=True)

    def _update_storage(self) -> None:
        """Sync current camera output directory with the mass storage image."""

        MOUNT_POINT.mkdir(exist_ok=True, parents=True)
        self._mount()

        try:
            # purge previous session
            for file in MOUNT_POINT.iterdir():
                if not file.is_file():
                    continue
                file.unlink()

            # copy current state
            for file in CAMERA_OUTPUT.iterdir():
                if not file.is_file():
                    continue
                copy2(file, MOUNT_POINT)

        finally:
            sync()
            self._umount()

    @staticmethod
    def _mount() -> None:
        """Mount mass storage image in mount point."""

        run(
            ["mount", "-o", "loop", str(MASS_STORAGE), str(MOUNT_POINT)],
            check=True,
        )

    @staticmethod
    def _umount() -> None:
        """Unmount mass storage image."""

        run(
            ["umount", MOUNT_POINT],
            check=True,
        )

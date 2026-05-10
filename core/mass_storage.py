from core.settings import AppSettings

from os.path import exists
from subprocess import run


class MassStorage:
    """USB mass storage emulation class."""

    def __init__(self) -> None:
        """
        Initialize USB mass storage (RaspberryPi USB OTG gadget).
        """

        self.create_storage_file()
        self.is_exposed = False

    def create_storage_file(self) -> None:
        """
        Create virtual mass storage disk file, format as FAT32.
        Skips this step if storage file already exists.
        """

        if self.check_storage_file_exists():
            print("Storage already exists.")
            return

        print("Allocating space for storage virtual disk")
        with open(AppSettings.mass_storage_path, "wb") as f:
            f.truncate(AppSettings.mass_storage_size)

        run(
            [
                "mkfs.vfat",
                "-F",
                "32",
                "-I",
                AppSettings.mass_storage_path,
            ],
            check=True,
        )

    def check_storage_file_exists(self) -> bool:
        """Check if storage file already exists at set path"""

        return exists(AppSettings.mass_storage_path)

    def expose(self) -> None:
        print("EXPOSE USB")
        self._stop_module()
        run(
            [
                "sudo",
                "/sbin/modprobe",
                "g_mass_storage",
                f"file={AppSettings.mass_storage_path}",
                "stall=0",
                "ro=1",
                "removable=1",
            ],
            check=True,
        )
        self.is_exposed = True

    def unexpose(self) -> None:
        print("UNEXPOSE USB")
        self._stop_module()
        run(
            [
                "sudo",
                "/sbin/modprobe",
                "g_mass_storage",
                "stall=0",
                "ro=1",
                "removable=1",
            ],
            check=True,
        )
        self.is_exposed = False

    def _stop_module(self) -> None:
        print("STOP MODULE")
        run(["sudo", "/sbin/rmmod", "g_mass_storage"], check=True)

    def _update_storage(self):
        pass

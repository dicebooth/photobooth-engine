import os
import shutil

from photobooth.logic.printing.ports import PrintFailed


class HotfolderPrinter:
    """
    HotfolderPrinter is the print transport for printers that watch a hotfolder
    (e.g. DNP): printing means copying the file into that folder.
    """

    def __init__(self, hotfolder_path: str):
        self._hotfolder_path = hotfolder_path

    def supported_options(self) -> str:
        """A hotfolder has no printer options to negotiate."""

        return ''

    def send(self, file_path: str, options: list[str]) -> None:
        """
        Method which copies the file into the hotfolder (options are ignored).
        :param file_path: file to print
        :param options: ignored, kept for the PrinterPort signature
        :raises PrintFailed: if the hotfolder does not exist
        """

        if not self._hotfolder_path or not os.path.isdir(self._hotfolder_path):
            raise PrintFailed(f"Hotfolder directory does not exist: {self._hotfolder_path}")

        target_path = os.path.join(self._hotfolder_path, os.path.basename(file_path))
        shutil.copy(file_path, target_path)
        try:
            os.chmod(target_path, 0o777)
        except OSError:
            pass

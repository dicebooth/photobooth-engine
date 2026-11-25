# NOTE
# sometimes the format can cause some errors, bitmap are preferred in such cases
# lp uses cups underneath
# alternative to lp is pycups which has some nice features to control the print flow (we don't need these features)
# both have a way to determine the additional settings of the printer
# for lp is : lpoptions -p name_printer -l
# to know the printer name: lpstat -p
# then we use the flag StpiShrinkOutput=Shrink to make the image use all the paper
# *Shrink Crop Expand
# the preceding flag is present in the gutenprint set (gutenprint is not installed in minimal distro), otherwise similar ones are:
# fit-to-page / scaling=X / fitplot
# it is possible to check if the printer is supported by gutenprint here: https://gimp-print.sourceforge.io/p_Supported_Printers.php
# warning: if the printer is supported by gutenprint it does not mean that has the flag StpiShrinkOutput=Shrink
import subprocess

from photobooth.logic.printing.ports import PrintFailed, PrinterNotFound


class CupsPrinter:
    """
    CupsPrinter is the print transport based on lp/CUPS.

    It only delivers a file with the given options: which options to use is a
    decision of the logic layer (PrintOptionsResolver).
    """

    def __init__(self, printer_name: str):
        self._printer_name = printer_name

    def supported_options(self) -> str:
        """
        Method which returns the raw option listing of the printer (lpoptions -p <printer> -l).
        :return: the listing, or an empty string if lpoptions is missing or fails
        (e.g. macOS or non-CUPS environments)
        """

        try:
            result = subprocess.run(
                ["lpoptions", "-p", self._printer_name, "-l"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ''

    def send(self, file_path: str, options: list[str]) -> None:
        """
        Method which sends the file to the printer with lp.
        :param file_path: file to print
        :param options: lp arguments, e.g. ['-o', 'media=dnp4x6']
        :raises PrinterNotFound: if the lp command is not available
        :raises PrintFailed: if lp fails
        """

        command = ['lp', '-d', self._printer_name] + options + [file_path]
        try:
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            raise PrintFailed(f"An error occurred while printing: {e}") from e
        except FileNotFoundError as e:
            raise PrinterNotFound("The 'lp' command was not found. Ensure CUPS is installed.") from e

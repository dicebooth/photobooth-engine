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
import os
import shutil
import subprocess

from photobooth import consts


class Printer:
    """
    Printer is the adapter of the printing subsystem (lp/CUPS or DNF hotfolder).

    It receives plain values from the composition root: it does not depend on the
    core layer (Settings) nor on any other layer.
    """

    def __init__(self, printer_name, user_options=None, print_size=None, enable_hotfolder=False,
                 hotfolder_path=''):
        self.printer_name = printer_name
        self.print_size = print_size or consts.DEFAULT_PRINT_SIZE
        self.enable_hotfolder = enable_hotfolder
        self.hotfolder_path = hotfolder_path
        self._filling_command = ""
        if user_options:
            self._filling_command = " ".join(f"-o {key}={value}" for key, value in user_options.items()) + " "

    def prepare(self) -> None:

        # NOTE: the media sent below is 4x6 (dnp4x6), but the condition checks
        # print_size == '4x3': on a QW410 a 4x3 job is printed on 4x6 media and
        # cut in two, hence media=dnp4x6 + Cutter=2Inch. The previous comment
        # said "4x6" and was misleading; the code behaviour is unchanged.
        if self.print_size == '4x3' and 'qw410' in self.printer_name.lower():
            self._filling_command = "-o media=dnp4x6 -o Cutter=2Inch "
            return

        if self._filling_command == "":
            # here we check which command to execute to fill the corner
            # check for
            possible_printer_options = consts.POSSIBLE_PRINTER_OPTIONS
            best_option_value = consts.BEST_OPTION_VALUE

            supported_options = self.get_printer_options(self.printer_name)

            for possible_option in possible_printer_options.keys():
                if possible_option in supported_options:
                    self._filling_command += f"-o {possible_option}={best_option_value[possible_option]} "
                    break

    def get_printer_options(self, printer_name):
        try:
            # Esegue il comando lpoptions -p <stampante> -l e ottiene l'output
            result = subprocess.run(
                ["lpoptions", "-p", printer_name, "-l"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            # FileNotFoundError: lpoptions is missing from $PATH (e.g. macOS or
            # non-CUPS environments): return an error string instead of crashing
            # Printer.prepare() at startup.
            return f"Errore: {e}"

    def print_image(self, file_path, printed_photos_number=0):
        if self.enable_hotfolder:
            if not self.hotfolder_path or not os.path.isdir(self.hotfolder_path):
                raise FileNotFoundError(f"Hotfolder directory does not exist: {self.hotfolder_path}")
            target_path = os.path.join(self.hotfolder_path, os.path.basename(file_path))
            print(f"Hotfolder enabled: copying {file_path} to {target_path}")
            shutil.copy(file_path, target_path)
            try:
                os.chmod(target_path, 0o777)
            except OSError:
                pass
            return

        command = [
                      'lp', '-d', self.printer_name
                  ] + self._filling_command.split() + [file_path]

        try:
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f'printed photos n.{printed_photos_number} and {printed_photos_number + 1}')
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while printing: {e}")
            print(f"The issued photo was: {file_path}")
        except FileNotFoundError:
            print("The 'lp' command was not found. Ensure CUPS is installed.")
            print(f"The issued photo was: {file_path}")
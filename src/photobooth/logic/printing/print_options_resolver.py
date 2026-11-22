from typing import Callable, Optional

from photobooth import consts


class PrintOptionsResolver:
    """
    PrintOptionsResolver decides which options the print job is sent with.

    The rules, in order:
    1. a QW410 printing a 4x3 size gets media=dnp4x6 + Cutter=2Inch;
    2. otherwise the options set by the user in settings.yaml are used;
    3. otherwise the first "fit the image to the paper" option supported by the
       printer is used (see consts.POSSIBLE_PRINTER_OPTIONS).

    It never talks to the printer: the option listing is provided by the caller.
    """

    def __init__(self, printer_name: str, print_size: Optional[str] = None, user_options: Optional[dict] = None):
        self._printer_name = printer_name
        self._print_size = print_size or consts.DEFAULT_PRINT_SIZE
        self._user_options = user_options or {}

    def resolve(self, supported_options: Callable[[], str]) -> list[str]:
        """
        Method which returns the lp arguments for the print jobs.
        :param supported_options: callable returning the printer option listing, invoked only if needed
        :return: lp arguments, e.g. ['-o', 'media=dnp4x6']
        """

        # NOTE: the media sent below is 4x6 (dnp4x6), but the condition checks
        # print_size == '4x3': on a QW410 a 4x3 job is printed on 4x6 media and
        # cut in two, hence media=dnp4x6 + Cutter=2Inch.
        if self._print_size == '4x3' and 'qw410' in self._printer_name.lower():
            return ['-o', 'media=dnp4x6', '-o', 'Cutter=2Inch']

        if self._user_options:
            return self._as_arguments(self._user_options)

        # check which option fills the paper corners
        listing = supported_options()
        for possible_option in consts.POSSIBLE_PRINTER_OPTIONS:
            if possible_option in listing:
                return self._as_arguments({possible_option: consts.BEST_OPTION_VALUE[possible_option]})
        return []

    @staticmethod
    def _as_arguments(options: dict) -> list[str]:
        arguments = []
        for key, value in options.items():
            arguments += ['-o', f'{key}={value}']
        return arguments

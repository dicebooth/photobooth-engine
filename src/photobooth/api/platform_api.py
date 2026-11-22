import platform


class Platform:
    """
    Platform models the operating system where the photobooth is running.
    """

    def __init__(self, platform_name):
        self._platform = platform_name

    def is_wsl(self):
        return self._platform == 'WSL'

    def is_linux(self):
        return self._platform == 'Linux'

    def is_macos(self):
        return self._platform == 'macOS'


def detect_os() -> Platform:
    """
    Method which detects the operating system where the photobooth is running.
    :return: Platform instance
    """

    os_name = platform.system()

    output_obj = None
    if os_name == 'Linux':
        # check if wsl
        if 'microsoft' in platform.release().lower():
            output_obj = Platform('WSL')
        else:
            output_obj = Platform('Linux')
    elif os_name == 'Darwin':
        output_obj = Platform('macOS')
    elif os_name == 'Windows':
        output_obj = Platform('Windows')

    return output_obj

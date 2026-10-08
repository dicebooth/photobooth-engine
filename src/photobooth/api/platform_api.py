import platform
import subprocess


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


def camera_is_connected(camera_name: str) -> bool:
    """
    Method which verifies if the camera set in the settings.yaml file is connected to the PC.
    :param camera_name: camera name to look for in the gphoto2 autodetect output
    :return: True if the camera is connected, False if not
    """

    output = subprocess.run(['gphoto2', '--auto-detect'], capture_output=True, text=True)
    for line in output.stdout.split('\n'):
        if camera_name in line:
            return True

    return False
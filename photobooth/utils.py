import os
import platform
import subprocess

from photobooth.settings_manager import Settings


def get_asset_path_from_name(asset_name : str) -> str:
    """
    Method which returns the effect path starting from its name.
    :return: effect path
    """

    # WARNING: if this function is not in the main folder of the project,
    # it will not work properly
    current_working_dir = os.getcwd()
    output_path = os.path.join(current_working_dir, 'Assets')
    output_path = os.path.join(output_path, asset_name)
    return output_path


def get_name_from_path(file_path :str) -> str:
    """
    Method which returns the last path part
    :return: last path part
    """

    return os.path.basename(file_path)


class Platform:

    def __init__(self, platform_name):
        self._platform = platform_name

    def is_wsl(self):
        if self._platform == 'WSL':
            return True
        else:
            return False

    def is_linux(self):
        if self._platform == 'Linux':
            return True
        else:
            return False

    def is_macos(self):
        if self._platform == 'macOS':
            return True
        else:
            return False


def detect_os():
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

def get_string_from_photo_number(photo_number):
    """
    Method which returns the photo number as string.
    :return: photo number as string
    """

    if len(str(photo_number)) == 1:
        return f"0{photo_number}"

    return photo_number

def get_string_from_session_number(session_number):
    """
    Method which returns the session number as string.
    :return: session number as string
    """

    if len(str(session_number)) == 1:
        return f"000{session_number}"
    elif len(str(session_number)) == 2:
        return f"00{session_number}"
    elif len(str(session_number)) == 3:
        return f"0{session_number}"

    return session_number

def camera_is_connected(settings_manager: Settings) -> bool:
    """
    Method which verifies if the camera set in the settings.yaml file is connected to the PC.
    :return: True if the camera is connected, No if not
    """

    output = subprocess.run(['gphoto2', '--auto-detect'], capture_output=True, text=True)
    for line in output.stdout.split('\n'):
        if settings_manager.get_cam_name() in line:
            return True

    return False


def check_hardware_status(settings_manager: Settings) -> tuple:
    """
    Method which verifies camera and printer availability according to settings.yaml (mocks and hotfolders included).
    :return: (camera_ok, printer_ok)
    """

    try:
        cam_ok = settings_manager.get_mock_camera() or settings_manager.get_camera_connection() == 'wifi' \
            or camera_is_connected(settings_manager)
    except Exception:
        cam_ok = False
    printer_ok = True
    if not settings_manager.get_mock_printer():
        if settings_manager.get_enable_hotfolder():
            hotfolder_path = settings_manager.get_printer_hotfolder_path()
            printer_ok = bool(hotfolder_path and os.path.exists(hotfolder_path))
        else:
            try:
                res = subprocess.run(["lpstat", "-p", settings_manager.get_printer_name()], capture_output=True, text=True)
                printer_ok = res.returncode == 0
            except Exception:
                printer_ok = True

    return cam_ok, printer_ok

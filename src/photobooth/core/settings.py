import os

import yaml

from photobooth import consts


class Settings:
    """
    Settings is the class which manages the settings.yaml file.

    The settings path is injected by the composition root (main.py), so the
    application can be pointed at any project root without relying on the CWD.

    The file is read once in the constructor: every getter works on the
    in-memory dictionary, so no further disk access happens during the session.
    """

    def __init__(self, settings_path: str = None):
        self._settings_path = settings_path or consts.SETTINGS_FILENAME
        self._data = self._load()

    def _load(self) -> dict:
        if not os.path.exists(self._settings_path):
            raise FileNotFoundError(
                f"Settings file not found: '{self._settings_path}'. "
                f"Copy settings-example.yaml to settings.yaml (or set {consts.PHOTOBOOTH_HOME_ENV})."
            )
        with open(self._settings_path, 'r') as yaml_file:
            return yaml.safe_load(yaml_file) or {}

    def get_main_folder_path(self) -> str:
        """
        Method which returns the main folder path set in settings.yaml file.
        :return: main folder path
        """

        return self._data['main_folder_path']

    def get_printer_name(self) -> str:
        """
        Method which returns the printer name set in settings.yaml file.
        :return: printer name
        """

        return self._data['printer_name']

    def get_printer_options(self) -> dict:
        return self._data.get('printer_options', {})

    def get_cam_name(self) -> str:
        """
        Method which returns the camera name set in settings.yaml file.
        :return: camera name
        """

        return self._data['cam_name']

    def get_backend_url(self) -> str:
        return self._data['backend']

    def get_event_name(self) -> str:
        """
        Method which returns the event name set in settings.yaml file.
        :return: event name
        """

        return self._data['event_name']

    def get_print_size(self) -> str:
        """
        Method which returns the print size set in settings.yaml file.
        :return: print size
        """

        return self._data.get('print_size', consts.DEFAULT_PRINT_SIZE)  # Defaults to 4x6 if not specified

    def get_client_secret(self) -> str:
        """
        Method which returns the client secret set in settings.yaml file.
        :return: client secret
        """

        return self._data.get('client_secret', '')

    def get_capture_mode(self) -> str:
        """
        Method which returns the capture mode (pc or camera) set in settings.yaml file.
        :return: capture mode
        """

        return self._data.get('capture_mode', consts.DEFAULT_CAPTURE_MODE)  # Defaults to pc if not specified

    def get_enable_hotfolder(self) -> bool:
        return self._data.get('enable_hotfolder', consts.DEFAULT_ENABLE_HOTFOLDER)

    def get_printer_hotfolder_path(self) -> str:
        return self._data.get('printer_hotfolder_path', '')

    def get_min_num_photos(self) -> int:
        return self._data.get('min_num_photos', consts.DEFAULT_MIN_NUM_PHOTOS)

    def get_max_num_photos(self) -> int:
        return self._data.get('max_num_photos', consts.DEFAULT_MAX_NUM_PHOTOS)

    def get_camera_connection(self) -> str:
        return self._data.get('camera_connection', consts.DEFAULT_CAMERA_CONNECTION)

    def get_camera_hotfolder_path(self) -> str:
        return self._data.get('camera_hotfolder_path', '')

    def get_frame_name(self) -> str:
        return self._data.get('frame_name', '')

    def get_preview_pre_frame(self) -> bool:
        return self._data.get('preview_pre_frame', consts.DEFAULT_PREVIEW_PRE_FRAME)

    def get_preview_post_frame(self) -> bool:
        return self._data.get('preview_post_frame', consts.DEFAULT_PREVIEW_POST_FRAME)

    def get_terminal_preview(self) -> bool:
        return self._data.get('terminal_preview', consts.DEFAULT_TERMINAL_PREVIEW)

    def get_terminal_preview_rows(self) -> int:
        return int(self._data.get('terminal_preview_rows', consts.DEFAULT_TERMINAL_PREVIEW_ROWS))

    def get_warn_num_photos(self) -> int:
        return self._data.get('warn_num_photos', consts.DEFAULT_WARN_NUM_PHOTOS)
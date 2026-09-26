import yaml

"""
Settings is the class which manages the settings.yaml file.
"""


class Settings:

    def __init__(self):
        from photobooth.consts import SETTINGS_PATH
        self._settings_path = SETTINGS_PATH

    def get_main_folder_path(self) -> str:
        """
        Method which returns the main folder path set in settings.yaml file.
        :return: main folder path
        """

        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
        return yaml_dict['main_folder_path']

    def get_printer_name(self) -> str:
        """
        Method which returns the printer name set in settings.yaml file.
        :return: printer name
        """

        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
        return yaml_dict['printer_name']

    def get_printer_options(self) -> dict:
        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
        return yaml_dict.get('printer_options', {})

    def get_cam_name(self) -> str:
        """
        Method which returns the camera name set in settings.yaml file.
        :return: camera name
        """

        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)

        return yaml_dict['cam_name']

    def get_backend_url(self) -> str:
        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)

        return yaml_dict['backend']

    def get_event_name(self) -> str:
        """
        Method which returns the event name set in settings.yaml file.
        :return: event name
        """

        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)

        return yaml_dict['event_name']

    def get_print_size(self) -> str:
        """
        Method which returns the print size set in settings.yaml file.
        :return: print size
        """
        from photobooth.consts import DEFAULT_PRINT_SIZE

        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)

        return yaml_dict.get('print_size', DEFAULT_PRINT_SIZE)  # Defaults to 4x6 if not specified

    def get_client_secret(self) -> str:
        """
        Method which returns the client secret set in settings.yaml file.
        :return: client secret
        """

        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)

        return yaml_dict.get('client_secret', '')

    def get_capture_mode(self) -> str:
        """
        Method which returns the capture mode (pc or camera) set in settings.yaml file.
        :return: capture mode
        """
        from photobooth.consts import DEFAULT_CAPTURE_MODE

        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)

        return yaml_dict.get('capture_mode', DEFAULT_CAPTURE_MODE)  # Defaults to pc if not specified

    def get_mock_camera(self) -> bool:
        from photobooth.consts import DEFAULT_MOCK_CAMERA
        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
        return yaml_dict.get('mock_camera', DEFAULT_MOCK_CAMERA)

    def get_mock_printer(self) -> bool:
        from photobooth.consts import DEFAULT_MOCK_PRINTER
        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
        return yaml_dict.get('mock_printer', DEFAULT_MOCK_PRINTER)

    def get_enable_hotfolder(self) -> bool:
        from photobooth.consts import DEFAULT_ENABLE_HOTFOLDER
        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
        return yaml_dict.get('enable_hotfolder', DEFAULT_ENABLE_HOTFOLDER)

    def get_printer_hotfolder_path(self) -> str:
        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
        return yaml_dict.get('printer_hotfolder_path', '')

    def get_min_num_photos(self) -> int:
        from photobooth.consts import DEFAULT_MIN_NUM_PHOTOS
        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
        return yaml_dict.get('min_num_photos', DEFAULT_MIN_NUM_PHOTOS)

    def get_max_num_photos(self) -> int:
        from photobooth.consts import DEFAULT_MAX_NUM_PHOTOS
        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
        return yaml_dict.get('max_num_photos', DEFAULT_MAX_NUM_PHOTOS)

    def get_camera_connection(self) -> str:
        from photobooth.consts import DEFAULT_CAMERA_CONNECTION
        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
        return yaml_dict.get('camera_connection', DEFAULT_CAMERA_CONNECTION)

    def get_camera_hotfolder_path(self) -> str:
        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
        return yaml_dict.get('camera_hotfolder_path', '')

    def get_frame_name(self) -> str:
        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
        return yaml_dict.get('frame_name', '')

    def get_preview_pre_frame(self) -> bool:
        from photobooth.consts import DEFAULT_PREVIEW_PRE_FRAME
        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
        return yaml_dict.get('preview_pre_frame', DEFAULT_PREVIEW_PRE_FRAME)

    def get_preview_post_frame(self) -> bool:
        from photobooth.consts import DEFAULT_PREVIEW_POST_FRAME
        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
        return yaml_dict.get('preview_post_frame', DEFAULT_PREVIEW_POST_FRAME)

    def get_terminal_preview(self) -> bool:
        from photobooth.consts import DEFAULT_TERMINAL_PREVIEW
        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
        return yaml_dict.get('terminal_preview', DEFAULT_TERMINAL_PREVIEW)

    def get_terminal_preview_rows(self) -> int:
        from photobooth.consts import DEFAULT_TERMINAL_PREVIEW_ROWS
        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
        return int(yaml_dict.get('terminal_preview_rows', DEFAULT_TERMINAL_PREVIEW_ROWS))

    def get_warn_num_photos(self) -> int:
        from photobooth.consts import DEFAULT_WARN_NUM_PHOTOS
        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
        return yaml_dict.get('warn_num_photos', DEFAULT_WARN_NUM_PHOTOS)

    def get_ui_mode(self) -> str:
        """
        Method which returns the UI mode (gui or cli) set in settings.yaml file.
        :return: UI mode ('gui' or 'cli')
        """
        from photobooth.consts import DEFAULT_UI_MODE
        with open(self._settings_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
        return yaml_dict.get('ui_mode', DEFAULT_UI_MODE).strip().lower()


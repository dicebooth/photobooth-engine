import os

import yaml

from photobooth import consts
from photobooth.logic.settings.settings_models import (
    CaptureSettings, FrameSettings, InteractionSettings, PrintSettings, StorageSettings, UploadSettings,
)


class Settings:
    """
    Settings is the class which manages the settings.yaml file.

    The settings path is injected by the composition root (main.py), so the
    application can be pointed at any project root without relying on the CWD.

    The file is read once in the constructor and exposed as one small typed
    slice per theme (storage, capture, frames, printing, uploads, interaction):
    every service receives only the slice it needs. Missing optional keys fall
    back to the defaults of the slice.
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

    def _slice(self, model, required: dict, optional: dict):
        """
        Builds a settings slice from the yaml data.
        :param model: dataclass of the slice
        :param required: {field: yaml key} which must be present (KeyError otherwise)
        :param optional: {field: yaml key} which fall back to the dataclass default
        """

        values = {field: self._data[key] for field, key in required.items()}
        values.update({field: self._data[key] for field, key in optional.items() if key in self._data})
        return model(**values)

    @property
    def storage(self) -> StorageSettings:
        return self._slice(StorageSettings,
                           required={'main_folder_path': 'main_folder_path', 'event_name': 'event_name'},
                           optional={})

    @property
    def capture(self) -> CaptureSettings:
        return self._slice(CaptureSettings,
                           required={'cam_name': 'cam_name'},
                           optional={'capture_mode': 'capture_mode',
                                     'camera_connection': 'camera_connection',
                                     'camera_hotfolder_path': 'camera_hotfolder_path',
                                     'preview_pre_frame': 'preview_pre_frame',
                                     'retry_delay_sec': 'camera_retry_delay_sec'})

    @property
    def frames(self) -> FrameSettings:
        return self._slice(FrameSettings,
                           required={},
                           optional={'frame_name': 'frame_name', 'preview_post_frame': 'preview_post_frame'})

    @property
    def printing(self) -> PrintSettings:
        return self._slice(PrintSettings,
                           required={'printer_name': 'printer_name'},
                           optional={'printer_options': 'printer_options',
                                     'print_size': 'print_size',
                                     'enable_hotfolder': 'enable_hotfolder',
                                     'printer_hotfolder_path': 'printer_hotfolder_path'})

    @property
    def uploads(self) -> UploadSettings:
        return self._slice(UploadSettings,
                           required={'backend_url': 'backend'},
                           optional={'client_secret': 'client_secret'})

    @property
    def interaction(self) -> InteractionSettings:
        settings = self._slice(InteractionSettings,
                               required={},
                               optional={'terminal_preview': 'terminal_preview',
                                         'terminal_preview_rows': 'terminal_preview_rows',
                                         'min_num_photos': 'min_num_photos',
                                         'max_num_photos': 'max_num_photos',
                                         'warn_num_photos': 'warn_num_photos'})
        return InteractionSettings(**{**settings.__dict__, 'terminal_preview_rows': int(settings.terminal_preview_rows)})

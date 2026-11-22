import os

import pytest
import yaml

from photobooth import consts
from photobooth.logic.session.folder_manager import FolderManager
from photobooth.logic.session.originals_archiver import OriginalsArchiver
from photobooth.logic.session.recovery_service import RecoveryService
from photobooth.logic.settings.settings import Settings


# ------------------------------------------------------------------ recovery

def _recovery(tmp_path):
    folders = FolderManager(str(tmp_path))
    return RecoveryService(folders, OriginalsArchiver(folders)), folders


def test_pending_photos_are_sorted_naturally(tmp_path):
    recovery, folders = _recovery(tmp_path)
    for name in ('EV_0001_10.jpg', 'EV_0001_2.jpg', 'EV_0001_1.jpg'):
        (tmp_path / 'user_data' / 'current' / name).write_bytes(b'x')

    assert [os.path.basename(p) for p in recovery.pending_photos()] == \
           ['EV_0001_1.jpg', 'EV_0001_2.jpg', 'EV_0001_10.jpg']


def test_no_pending_photos_in_a_clean_session(tmp_path):
    recovery, _ = _recovery(tmp_path)

    assert recovery.pending_photos() == []


def test_discard_pending_moves_everything_to_originals(tmp_path):
    recovery, folders = _recovery(tmp_path)
    (tmp_path / 'user_data' / 'current' / 'a.jpg').write_bytes(b'x')

    recovery.discard_pending()

    assert recovery.pending_photos() == []
    assert os.listdir(folders.get_originals_path()) == ['a.jpg']


# ------------------------------------------------------------------ settings

def _settings(tmp_path, data):
    path = tmp_path / consts.SETTINGS_FILENAME
    path.write_text(yaml.dump(data))
    return Settings(str(path))


MINIMAL = {
    'main_folder_path': '/storage', 'event_name': 'EV', 'cam_name': 'cam',
    'printer_name': 'printer', 'backend': 'http://backend',
}


def test_optional_keys_fall_back_to_the_defaults(tmp_path):
    settings = _settings(tmp_path, MINIMAL)

    assert settings.storage.main_folder_path == '/storage'
    assert settings.capture.capture_mode == consts.DEFAULT_CAPTURE_MODE
    assert settings.capture.camera_connection == consts.DEFAULT_CAMERA_CONNECTION
    assert settings.capture.retry_delay_sec == consts.CAMERA_RETRY_DELAY_SEC
    assert settings.frames.frame_name == ''
    assert settings.printing.print_size == consts.DEFAULT_PRINT_SIZE
    assert settings.printing.printer_options == {}
    assert settings.uploads.client_secret == ''
    assert settings.interaction.max_num_photos == consts.DEFAULT_MAX_NUM_PHOTOS


def test_configured_values_are_exposed_in_their_slice(tmp_path):
    settings = _settings(tmp_path, {
        **MINIMAL, 'capture_mode': 'camera', 'camera_connection': 'wifi', 'camera_hotfolder_path': '/hot',
        'frame_name': 'f', 'preview_post_frame': False, 'print_size': '4x3', 'enable_hotfolder': True,
        'printer_options': {'a': 1}, 'client_secret': 's', 'terminal_preview_rows': '12',
    })

    assert (settings.capture.capture_mode, settings.capture.camera_connection) == ('camera', 'wifi')
    assert settings.capture.camera_hotfolder_path == '/hot'
    assert settings.frames.frame_name == 'f' and settings.frames.preview_post_frame is False
    assert settings.printing.print_size == '4x3' and settings.printing.enable_hotfolder is True
    assert settings.printing.printer_options == {'a': 1}
    assert settings.uploads.backend_url == 'http://backend' and settings.uploads.client_secret == 's'
    assert settings.interaction.terminal_preview_rows == 12


def test_missing_required_key_raises(tmp_path):
    settings = _settings(tmp_path, {'event_name': 'EV'})

    with pytest.raises(KeyError, match='main_folder_path'):
        settings.storage


def test_missing_settings_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match='settings-example.yaml'):
        Settings(str(tmp_path / 'nope.yaml'))

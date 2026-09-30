import os
import shutil

import pytest
import yaml
from PIL import Image, ImageChops

from photobooth import consts
from photobooth.api.camera.camera_service import CameraService
from photobooth.api.printer_api import Printer
from photobooth.core.settings import Settings
from photobooth.main import build_gateway
from photobooth.presentation.cli.session_cli import SessionCli

ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
SAMPLE_PHOTO = os.path.join(ASSETS_DIR, 'mock', 'photo.jpg')
EXPECTED_PRINT = os.path.join(ASSETS_DIR, 'edits_to_print.jpg')


def images_equal(a, b):
    a = a.convert("RGB")
    b = b.convert("RGB")
    return a.size == b.size and ImageChops.difference(a, b).getbbox() is None


class ScriptedInteraction:
    """
    Test double of the CLI interaction layer: it answers every prompt
    automatically, so the session flow can be exercised without a terminal.
    """

    def __init__(self, times_to_print: int = 1, accept_preview: bool = True):
        self._times_to_print = times_to_print
        self._accept_preview = accept_preview
        self.prompted = []

    def ask_resume_session(self):
        self.prompted.append('ask_resume_session')
        return False

    def choose_pending_photo(self, photo_paths):
        self.prompted.append('choose_pending_photo')
        return photo_paths[0]

    def confirm_shot(self, photo_path):
        self.prompted.append('confirm_shot')
        return self._accept_preview

    def wait_for_camera_shutter(self):
        self.prompted.append('wait_for_camera_shutter')

    def press_to_shoot(self):
        self.prompted.append('press_to_shoot')

    def notify_shot_taken(self):
        self.prompted.append('notify_shot_taken')

    def notify_photo_rejected(self):
        self.prompted.append('notify_photo_rejected')

    def show_preview_image(self, preview_img):
        self.prompted.append('show_preview_image')
        return self._accept_preview

    def choose_polaroid_effect(self, frame_list):
        self.prompted.append('choose_polaroid_effect')
        return frame_list[0] + '.png'

    def choose_times_to_print(self):
        self.prompted.append('choose_times_to_print')
        return self._times_to_print


@pytest.fixture
def fake_hardware(monkeypatch):
    """
    Replaces the camera and the printer adapters with test doubles, so the
    session flow can be exercised without real hardware (monkey patching).

    :return: list of the files "printed" during the test
    """
    printed_files = []

    def fake_capture(self, path, photo_name):
        target = os.path.join(path, photo_name)
        shutil.copyfile(SAMPLE_PHOTO, target)
        return target

    monkeypatch.setattr(CameraService, 'init_camera', lambda self: None)
    monkeypatch.setattr(CameraService, 'stop_camera', lambda self: None)
    monkeypatch.setattr(CameraService, 'capture_via_camera', fake_capture)
    monkeypatch.setattr(CameraService, 'capture_via_pc', fake_capture)

    monkeypatch.setattr(Printer, 'prepare', lambda self: None)
    monkeypatch.setattr(
        Printer, 'print_image',
        lambda self, file_path, printed_photos_number=0: printed_files.append(file_path),
    )

    return printed_files


def _build_home(home: str) -> str:
    """
    Creates a temporary photobooth home: settings.yaml and Assets with a
    single frame. The camera and the printer are patched by the tests.
    """
    settings = {
        'main_folder_path': os.path.join(home, 'storage'),
        'event_name': 'TEST',
        'cam_name': 'test',
        'capture_mode': 'pc',
        'printer_name': 'test',
        'print_size': '4x6',
        'backend': 'http://localhost:9999',
        'client_secret': '',
        'min_num_photos': 1,
        'max_num_photos': 9,
        'warn_num_photos': 5,
        'preview_pre_frame': True,
        'preview_post_frame': True,
    }
    with open(os.path.join(home, consts.SETTINGS_FILENAME), 'w') as settings_file:
        yaml.dump(settings, settings_file, default_flow_style=False, allow_unicode=True)

    assets_dir = os.path.join(home, consts.ASSETS_DIRNAME)
    os.makedirs(assets_dir)
    shutil.copyfile(os.path.join(ASSETS_DIR, 'frame.png'), os.path.join(assets_dir, 'frame1.png'))

    return home


def test_full_session_flow(tmp_path, fake_hardware):
    home = _build_home(str(tmp_path))
    settings = Settings(os.path.join(home, consts.SETTINGS_FILENAME))
    gateway = build_gateway(home, settings)

    # No backend in this test: replace the fire-and-forget upload with a spy
    sent_to_backend = []
    gateway.send_to_backend = lambda photo_path, frame_name: sent_to_backend.append((photo_path, frame_name))

    interaction = ScriptedInteraction(times_to_print=1)
    session = SessionCli(gateway, interaction)

    gateway.prepare()

    # The frame strategy is 'single' (only one frame in the temporary Assets)
    assert gateway.frame_strategy() == 'single'
    assert gateway.available_frames() == ['frame1']

    # One session is not enough to print: the queue starts from the second photo
    session.main_execution()
    assert not gateway.prints_pending()

    session.main_execution()
    assert not gateway.prints_pending()  # both queued photos have been printed

    storage = os.path.join(home, 'storage', 'user_data')
    originals = os.path.join(storage, 'originals')
    output = os.path.join(storage, 'output')
    current = os.path.join(storage, 'current')

    # Both accepted shots have been moved to the originals folder
    assert len(os.listdir(originals)) == 2
    # The current folder has been emptied at the end of every session
    assert os.listdir(current) == []
    # The two photos have been edited together and printed
    assert len(os.listdir(output)) == 1

    # The interaction has been driven by the presentation layer, not by the core
    assert 'press_to_shoot' in interaction.prompted
    assert 'confirm_shot' in interaction.prompted
    assert 'show_preview_image' in interaction.prompted
    assert 'choose_times_to_print' in interaction.prompted

    # Both accepted photos have been sent to the backend through the gateway
    assert len(sent_to_backend) == 2
    assert all(frame_name == 'frame1.png' for _, frame_name in sent_to_backend)

    # The printer received exactly one file, and it is a correct merged photo
    assert len(fake_hardware) == 1
    printed_image = Image.open(fake_hardware[0])
    expected_image = Image.open(EXPECTED_PRINT)
    assert images_equal(printed_image, expected_image)


def test_pending_session_is_detected_and_discarded(tmp_path, fake_hardware):
    home = _build_home(str(tmp_path))
    settings = Settings(os.path.join(home, consts.SETTINGS_FILENAME))
    gateway = build_gateway(home, settings)
    gateway.prepare()

    storage = os.path.join(home, 'storage', 'user_data')
    current = os.path.join(storage, 'current')

    # Simulate a photo left by an interrupted session
    shutil.copyfile(
        SAMPLE_PHOTO,
        os.path.join(current, 'TEST_0001_01.jpg'),
    )

    pending = gateway.pending_photos()
    assert len(pending) == 1
    assert pending[0].endswith('TEST_0001_01.jpg')

    gateway.discard_pending_session()

    assert gateway.pending_photos() == []
    assert len(os.listdir(os.path.join(storage, 'originals'))) == 1
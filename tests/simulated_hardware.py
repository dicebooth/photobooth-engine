"""
Test doubles used to run the photobooth without real hardware.

The camera double replaces every shot with a sample photo, while the printer
double "prints" by handing the edited file to a callback. They are shared by the
pytest session-flow test and by the interactive simulator
(tests/run_simulated_session.py), so both exercise the very same pipeline.

Both functions receive a ``setattr_func`` compatible with ``setattr`` and with
``pytest.MonkeyPatch.setattr``: the test passes the monkeypatch function (so the
original methods are restored automatically), the simulator passes the built-in
``setattr``.
"""

import os
import shutil

from photobooth.api.camera.camera_service import CameraService
from photobooth.api.printer_api import Printer

ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
SAMPLE_PHOTO = os.path.join(ASSETS_DIR, 'mock', 'photo.jpg')
SAMPLE_FRAME = os.path.join(ASSETS_DIR, 'frame.png')


def patch_camera(setattr_func, sample_photo: str = SAMPLE_PHOTO):
    """
    Method which replaces the CameraService methods with test doubles: every
    capture copies the given sample photo instead of talking to a real camera.
    :param setattr_func: function used to override the methods (setattr or monkeypatch.setattr)
    :param sample_photo: path of the photo returned by every simulated shot
    """

    def fake_capture(self, path, photo_name):
        target = os.path.join(path, photo_name)
        shutil.copyfile(sample_photo, target)
        return target

    setattr_func(CameraService, 'init_camera', lambda self: None)
    setattr_func(CameraService, 'stop_camera', lambda self: None)
    setattr_func(CameraService, 'capture_via_camera', fake_capture)
    setattr_func(CameraService, 'capture_via_pc', fake_capture)


def patch_printer(setattr_func, on_print):
    """
    Method which replaces the Printer methods with test doubles: nothing is sent
    to a real printer, the edited file is handed to the given callback instead.
    :param setattr_func: function used to override the methods (setattr or monkeypatch.setattr)
    :param on_print: callback invoked with the path of every "printed" file
    """

    setattr_func(Printer, 'prepare', lambda self: None)
    setattr_func(
        Printer, 'print_image',
        lambda self, file_path, printed_photos_number=0: on_print(file_path),
    )

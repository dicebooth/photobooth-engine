import os

import pytest

from photobooth.api.camera.hotfolder_camera import HotfolderCamera
from photobooth.logic.capture.capture_service import CaptureService
from photobooth.logic.capture.photo_id_sequencer import PhotoIdSequencer
from photobooth.logic.capture.ports import CameraError, CameraNotFound, CameraPort
from photobooth.logic.editing.naming_service import NamingService
from photobooth.logic.session.folder_manager import FolderManager
from photobooth.logic.session.originals_archiver import OriginalsArchiver
from photobooth.logic.settings.settings_models import CaptureSettings

ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
SAMPLE_PHOTO = os.path.join(ASSETS_DIR, 'mock', 'photo.jpg')


class FakeWifiState:
    def __init__(self, wifi_id=None):
        self.wifi_id = wifi_id

    def load_wifi_id(self):
        return self.wifi_id

    def save_wifi_id(self, wifi_id):
        self.wifi_id = wifi_id


# ------------------------------------------------------------ PhotoIdSequencer

@pytest.mark.parametrize('filename, expected', [
    ('IMG_0042.JPG', 42), ('DSC00007.jpg', 7), ('a12b34.png', 34), ('nodigits.jpg', 0),
])
def test_photo_id_is_the_last_digit_sequence(filename, expected):
    assert PhotoIdSequencer.get_photo_id(filename) == expected


def test_first_run_starts_after_the_highest_existing_photo():
    state = FakeWifiState()
    sequencer = PhotoIdSequencer(state)

    assert sequencer.next_candidate(['IMG_0001.jpg', 'IMG_0005.jpg', 'notes.txt']) is None
    assert state.wifi_id == 5


def test_next_candidate_is_the_lowest_new_id_and_ignores_non_images():
    sequencer = PhotoIdSequencer(FakeWifiState(wifi_id=5))

    assert sequencer.next_candidate(['IMG_0008.jpg', 'IMG_0006.JPG', 'IMG_0004.jpg', 'IMG_0007.txt']) \
           == (6, 'IMG_0006.JPG')


def test_mark_read_is_persisted_and_moves_the_cursor():
    state = FakeWifiState(wifi_id=5)
    sequencer = PhotoIdSequencer(state)

    sequencer.mark_read(6)

    assert state.wifi_id == 6
    assert sequencer.next_candidate(['IMG_0006.jpg']) is None
    assert PhotoIdSequencer(state).next_candidate(['IMG_0006.jpg', 'IMG_0007.jpg']) == (7, 'IMG_0007.jpg')


def test_hotfolder_camera_copies_the_new_photo_and_marks_it_read(tmp_path):
    hotfolder = tmp_path / 'hot'
    hotfolder.mkdir()
    destination = tmp_path / 'dest'
    destination.mkdir()
    state = FakeWifiState(wifi_id=1)
    camera = HotfolderCamera(str(hotfolder), PhotoIdSequencer(state))
    with open(SAMPLE_PHOTO, 'rb') as src:
        (hotfolder / 'IMG_0002.jpg').write_bytes(src.read())

    target = camera.capture_via_pc(str(destination), 'shot.jpg')

    assert target == os.path.join(str(destination), 'shot.jpg')
    assert os.path.exists(target)
    assert state.wifi_id == 2


# ------------------------------------------------------------- CaptureService

class ScriptedCamera:
    """Fails with the given errors (one per call, init and capture share the script), then succeeds."""

    def __init__(self, failures=()):
        self.failures = list(failures)
        self.calls = []

    def _maybe_fail(self, name):
        self.calls.append(name)
        if self.failures:
            raise self.failures.pop(0)

    def init(self):
        self._maybe_fail('init')

    def stop(self):
        self.calls.append('stop')

    def capture_via_camera(self, path, photo_name):
        self._maybe_fail('capture_via_camera')
        return os.path.join(path, photo_name)

    def capture_via_pc(self, path, photo_name):
        self._maybe_fail('capture_via_pc')
        return os.path.join(path, photo_name)


class InMemoryNaming:
    def __init__(self):
        self.session = 0

    def load_naming_session_string(self):
        return f'{self.session:04d}'

    def save_naming_session_string(self, session):
        self.session = int(session)


def _capture_service(tmp_path, camera, sleeps, **settings):
    folders = FolderManager(str(tmp_path))
    naming_state = InMemoryNaming()
    naming = NamingService(naming_state, 'EV', folders)
    capture_settings = CaptureSettings(cam_name='cam', retry_delay_sec=3, **settings)
    service = CaptureService(camera, folders, OriginalsArchiver(folders), naming, capture_settings,
                             sleep=sleeps.append)
    return service, folders, naming_state


def test_camera_adapters_satisfy_the_camera_port(tmp_path):
    assert isinstance(ScriptedCamera(), CameraPort)
    assert isinstance(HotfolderCamera(str(tmp_path), PhotoIdSequencer(FakeWifiState())), CameraPort)


def test_prepare_waits_for_the_camera_forever(tmp_path):
    camera = ScriptedCamera([CameraNotFound('no camera')] * 4)
    sleeps = []
    service, _, _ = _capture_service(tmp_path, camera, sleeps)

    service.prepare()

    assert camera.calls == ['init'] * 5
    assert sleeps == [3] * 4


def test_capture_uses_the_configured_mode_and_the_current_folder(tmp_path):
    camera = ScriptedCamera()
    service, folders, _ = _capture_service(tmp_path, camera, [], capture_mode='camera')

    photo = service.capture()

    assert camera.calls == ['capture_via_camera']
    assert photo == os.path.join(folders.get_current_path(), 'EV_0001_01.jpg')


def test_capture_reinitializes_and_retries_after_a_camera_error(tmp_path):
    class Camera(ScriptedCamera):
        """The first shot fails, then the camera needs two failed inits before it is back."""

        def _maybe_fail(self, name):
            self.calls.append(name)
            if name == 'capture_via_pc' and self.calls.count(name) == 1:
                raise CameraError('shot')
            if name == 'init' and self.calls.count(name) <= 2:
                raise CameraError('init')

    camera = Camera()
    sleeps = []
    service, _, _ = _capture_service(tmp_path, camera, sleeps)

    photo = service.capture()

    assert photo.endswith('EV_0001_01.jpg')
    assert camera.calls == ['capture_via_pc', 'init', 'init', 'init', 'capture_via_pc']
    assert sleeps == [3, 3]


def test_request_stop_breaks_the_retry_loop(tmp_path):
    class AlwaysFailing(ScriptedCamera):
        def _maybe_fail(self, name):
            self.calls.append(name)
            raise CameraError('down')

    camera = AlwaysFailing()
    sleeps = []
    service, _, _ = _capture_service(tmp_path, camera, sleeps)
    # the operator quits while the service is sleeping between two attempts
    original_sleep = service._sleep
    service._sleep = lambda seconds: (original_sleep(seconds), service.request_stop())

    assert service.capture() == ''
    assert len(sleeps) == 1


def test_hint_depends_on_mode_and_connection(tmp_path):
    def hint(**settings):
        return _capture_service(tmp_path, ScriptedCamera(), [], **settings)[0].hint()

    assert hint(capture_mode='pc', camera_connection='usb') == 'press'
    assert hint(capture_mode='camera', camera_connection='usb') == 'shutter'
    assert hint(capture_mode='pc', camera_connection='wifi') == 'shutter'


def test_accept_moves_the_session_counter_and_reject_archives_the_shot(tmp_path):
    service, folders, naming_state = _capture_service(tmp_path, ScriptedCamera(), [])
    shot = os.path.join(folders.get_current_path(), 'EV_0001_01.jpg')
    with open(shot, 'w') as f:
        f.write('x')

    service.reject(shot)
    assert os.listdir(folders.get_originals_path()) == ['EV_0001_01.jpg']

    service.accept()
    assert naming_state.session == 1

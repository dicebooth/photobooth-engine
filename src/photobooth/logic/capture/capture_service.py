import logging
import threading
import time
from typing import Callable

from photobooth.api.camera_api import CameraAPI
from photobooth.logic.capture.ports import CameraError
from photobooth.logic.editing.naming_service import NamingService
from photobooth.logic.session.folder_manager import FolderManager
from photobooth.logic.session.originals_archiver import OriginalsArchiver
from photobooth.logic.settings.settings_models import CaptureSettings

logger = logging.getLogger(__name__)


class CaptureService:
    """
    CaptureService takes the photos of the session.

    It is completely headless: the presentation layer shows the hint before the
    shot and asks the user to confirm it afterwards.

    Camera drivers make one attempt per call: while the camera is missing or a
    shot fails, this service keeps re-initializing and retrying, forever, until
    it succeeds or request_stop() is called.
    """

    def __init__(self, camera: CameraAPI, folders: FolderManager, archiver: OriginalsArchiver,
                 naming: NamingService, settings: CaptureSettings,
                 sleep: Callable[[float], None] = time.sleep):
        self._camera = camera
        self._folders = folders
        self._archiver = archiver
        self._naming = naming
        self._settings = settings
        self._sleep = sleep
        self._stop_requested = threading.Event()

    # ---------------------------------------------------------------- lifecycle

    def prepare(self) -> None:
        """
        Method which initializes the camera, waiting for it to be available.
        """

        self._connect()

    def stop(self) -> None:
        """
        Method which releases the camera.
        """

        self._camera.stop()

    def request_stop(self) -> None:
        """
        Method which makes any pending retry loop give up (e.g. the operator quits).
        """

        self._stop_requested.set()

    def stop_requested(self) -> bool:
        return self._stop_requested.is_set()

    # ------------------------------------------------------------------- capture

    def hint(self) -> str:
        """
        Method which returns the hint to show before the shot:
        'shutter' if the user has to press the shutter button on the camera,
        'press' if the user has to press a key on the keyboard.
        """

        if self._settings.capture_mode == 'camera' or self._settings.camera_connection == 'wifi':
            return 'shutter'
        return 'press'

    def should_preview(self) -> bool:
        """
        Method which returns True if the shot photo has to be confirmed by the user before going on.
        """

        return self._settings.preview_pre_frame

    def capture(self) -> str:
        """
        Method which takes a photo and saves it in the current folder.
        :return: shot photo path (empty string if a stop was requested before a shot succeeded)
        """

        file_name = self._naming.get_photo_name()
        current_path = self._folders.get_current_path()

        while not self.stop_requested():
            try:
                if self._settings.capture_mode == 'camera':
                    return self._camera.capture_via_camera(current_path, file_name)
                return self._camera.capture_via_pc(current_path, file_name)
            except CameraError as e:
                logger.warning(f'something went wrong ({e}), re-initializing camera')
                self._connect()
        return ''

    def accept(self) -> None:
        """
        Method which marks the shot photo as accepted and moves the session counter on.
        """

        self._naming.increment_session_number()

    def reject(self, photo_path: str) -> None:
        """
        Method which rejects the shot photo, moving it to the originals folder.
        :param photo_path: rejected photo path
        """

        self._archiver.archive_photo(photo_path)

    # ------------------------------------------------------------------ internal

    def _connect(self) -> None:
        while not self.stop_requested():
            try:
                self._camera.init()
                logger.info('camera ready')
                return
            except CameraError as e:
                logger.warning(f"camera not available: {e}. check if it's connected, retrying")
                self._sleep(self._settings.retry_delay_sec)

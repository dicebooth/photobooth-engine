import logging
import os
import shutil
import time

from PIL import Image

from photobooth import consts
from photobooth.logic.capture.photo_id_sequencer import PhotoIdSequencer
from photobooth.logic.capture.ports import CameraError

logger = logging.getLogger(__name__)


class HotfolderCamera:
    """
    HotfolderCamera is the WiFi camera driver (it implements CameraPort).

    It waits for a new photo to appear in the camera hotfolder (for example a
    camera with wireless transfer enabled) and copies it to the destination.
    Which photo is the new one is decided by the PhotoIdSequencer.
    """

    def __init__(self, hotfolder_path: str, sequencer: PhotoIdSequencer):
        self._hotfolder_path = hotfolder_path
        self._sequencer = sequencer

    def init(self):
        logger.info("WiFi camera enabled. Skipping real camera initialization.")

    def stop(self):
        return

    def capture_via_camera(self, path: str, photo_name: str) -> str:
        return self._wait_for_photo(path, photo_name)

    def capture_via_pc(self, path: str, photo_name: str) -> str:
        return self._wait_for_photo(path, photo_name)

    @staticmethod
    def is_image_complete(file_path) -> bool:
        """
        Verifies if the image is valid and not truncated by loading its pixel data.
        """
        try:
            with Image.open(file_path) as img:
                img.load()
            return True
        except Exception:
            return False

    def _wait_for_transfer(self, source_path: str) -> None:
        """
        Method which waits for the file transfer to complete (size stops changing and image is complete).
        """

        last_size = -1
        while True:
            try:
                current_size = os.path.getsize(source_path)
                if current_size == last_size and current_size > 0:
                    if self.is_image_complete(source_path):
                        return
                last_size = current_size
            except OSError:
                pass
            time.sleep(consts.WIFI_POLL_DELAY_SEC)

    def _wait_for_photo(self, path: str, photo_name: str) -> str:
        """
        Method which waits for a new photo to appear in the camera-hotfolder and copies it to the given path with the given name.
        :param path: the path where the photo has to be saved
        :param photo_name: the name of the photo to be saved
        :return: shot photo path
        :raises CameraError: if the hotfolder is not configured
        """

        hotfolder = self._hotfolder_path
        if not hotfolder:
            raise CameraError("camera_hotfolder_path is not configured.")

        os.makedirs(hotfolder, exist_ok=True)
        logger.info(f"Waiting for a new photo in hotfolder: {hotfolder}")

        while True:
            candidate = self._sequencer.next_candidate(os.listdir(hotfolder))
            if candidate:
                photo_id, new_image_name = candidate
                source_path = os.path.join(hotfolder, new_image_name)
                self._wait_for_transfer(source_path)

                target = os.path.join(path, photo_name)
                shutil.copyfile(source_path, target)
                os.chmod(target, 0o777)

                self._sequencer.mark_read(photo_id)
                return target

            time.sleep(consts.WIFI_POLL_DELAY_SEC)

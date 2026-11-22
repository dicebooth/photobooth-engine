import logging
import threading
import time
from typing import Callable

from PIL import Image

from photobooth import consts
from photobooth.logic.editing.photo_encoder import PhotoEncoder
from photobooth.logic.uploads.ports import BackendPort, BackendUnavailable

logger = logging.getLogger(consts.LOGGER_NAME)


class UploadService:
    """
    UploadService uploads the edited photos to the backend without ever
    blocking the caller.

    The upload runs in a background thread and, while the backend is
    unreachable, it is retried forever every few seconds. Any other error is
    final: it is logged and the photo is dropped.
    """

    def __init__(self, backend: BackendPort, encoder: PhotoEncoder,
                 retry_delay_sec: float = consts.UPLOAD_RETRY_DELAY_SEC,
                 sleep: Callable[[float], None] = time.sleep):
        self._backend = backend
        self._encoder = encoder
        self._retry_delay_sec = retry_delay_sec
        self._sleep = sleep

    def send_photo(self, edited_photo: Image.Image, photo_name: str) -> threading.Thread:
        """
        Method which sends the edited photo to the backend (fire-and-forget).
        :param edited_photo: edited photo (PIL image)
        :param photo_name: name of the photo
        :return: the background thread (the caller is free to ignore it)
        """

        thread = threading.Thread(target=self.upload_until_done, args=(edited_photo, photo_name), daemon=True)
        thread.start()
        return thread

    def upload_until_done(self, edited_photo: Image.Image, photo_name: str) -> None:
        """
        Method which uploads the photo, retrying while the backend is unreachable.
        It blocks: send_photo runs it in a background thread.
        """

        try:
            payload = self._encoder.to_png_base64(edited_photo)
        except Exception:
            logger.exception(f"Photo encoding failed for '{photo_name}'")
            return

        while True:
            try:
                self._backend.upload(payload, photo_name)
                return
            except BackendUnavailable:
                logger.info(f"The upload of '{photo_name}' will be retried in {self._retry_delay_sec} seconds")
                self._sleep(self._retry_delay_sec)
            except Exception:
                logger.exception(f"[UploadService] Background upload failed for '{photo_name}'")
                return

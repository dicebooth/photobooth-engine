import os
import re
from typing import Iterable, Optional

from photobooth.logic.capture.ports import PhotoIdStatePort

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png')


class PhotoIdSequencer:
    """
    PhotoIdSequencer decides which photo of a WiFi camera hotfolder is the next one to read.

    The camera numbers its photos: the ID of a photo is the last sequence of
    digits of its file name. A photo is "new" when its ID is higher than the
    last ID read, which is persisted so that a restart does not re-read old photos.
    On the very first run the highest ID already in the hotfolder is taken as
    the starting point.
    """

    def __init__(self, state: PhotoIdStatePort):
        self._state = state
        self._last_read_id: Optional[int] = None

    @staticmethod
    def get_photo_id(filename: str) -> int:
        """
        Extracts the last sequence of digits from a filename (excluding extension) as an integer ID.
        """

        name, _ = os.path.splitext(filename)
        digits = re.findall(r'\d+', name)
        if digits:
            return int(digits[-1])
        return 0

    def next_candidate(self, filenames: Iterable[str]) -> Optional[tuple[int, str]]:
        """
        Method which returns the next photo to read.
        :param filenames: names of the files currently in the hotfolder
        :return: (photo id, file name) of the new photo with the lowest ID, None if there is none
        """

        images = [f for f in filenames if f.lower().endswith(IMAGE_EXTENSIONS)]
        self._ensure_last_read_id(images)

        candidates = sorted((self.get_photo_id(f), f) for f in images if self.get_photo_id(f) > self._last_read_id)
        return candidates[0] if candidates else None

    def mark_read(self, photo_id: int) -> None:
        """
        Method which records that the photo with the given ID has been read.
        """

        self._last_read_id = photo_id
        self._state.save_wifi_id(photo_id)

    def _ensure_last_read_id(self, images: list[str]) -> None:
        if self._last_read_id is not None:
            return

        self._last_read_id = self._state.load_wifi_id()
        if self._last_read_id is None:
            # Initialize with the maximum ID currently in the hotfolder
            self._last_read_id = max((self.get_photo_id(f) for f in images), default=0)
            self._state.save_wifi_id(self._last_read_id)

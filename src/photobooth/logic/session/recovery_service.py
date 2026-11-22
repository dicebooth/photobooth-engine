import os
import re

from photobooth.logic.session.folder_manager import FolderManager
from photobooth.logic.session.originals_archiver import OriginalsArchiver


def natural_sort_key(name: str):
    """
    Helper function to sort alphanumeric strings naturally.
    """
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', name)]


class RecoveryService:
    """
    RecoveryService implements the disaster recovery: it finds the photos left
    in the current folder by a previous, interrupted session and discards them
    when the user does not want to resume it.
    """

    def __init__(self, folders: FolderManager, archiver: OriginalsArchiver):
        self._folders = folders
        self._archiver = archiver

    def pending_photos(self) -> list:
        """
        Method which returns the photos left in the current folder from the last session,
        sorted with a natural order.
        :return: list of photo paths
        """

        current_path = self._folders.get_current_path()
        photos = sorted(os.listdir(current_path), key=natural_sort_key)
        return [os.path.join(current_path, photo) for photo in photos]

    def discard_pending(self) -> None:
        """
        Method which discards the photos left by a previous interrupted session,
        moving them from the current folder to the originals folder.
        """

        self._archiver.archive_current()

import os
import shutil

from photobooth.logic.session.folder_manager import FolderManager


class OriginalsArchiver:
    """
    OriginalsArchiver moves the shots from the current folder to the originals
    folder when they are not needed there anymore (session ended, aborted,
    discarded or the shot rejected).
    """

    def __init__(self, folders: FolderManager):
        self._folders = folders

    def archive_current(self, chosen_photo_path: str = '') -> str:
        """
        Move all files from the current folder to the originals folder but save the new path of the chosen shot
        :param chosen_photo_path: old path of the photo which we will hold (empty if there is none)
        :return: chosen photo new path (empty if there is no chosen photo)
        """

        current_path = self._folders.get_current_path()
        originals_path = self._folders.get_originals_path()
        new_photo_path = ''

        for filename in os.listdir(current_path):
            original_file_complete_path = os.path.join(current_path, filename)
            destination_path = os.path.join(originals_path, filename)
            shutil.move(original_file_complete_path, destination_path)

            if original_file_complete_path == chosen_photo_path:
                new_photo_path = destination_path

        return new_photo_path

    def archive_photo(self, photo_path: str) -> str:
        """
        Move a single photo to the originals folder (e.g. a rejected shot).
        :param photo_path: photo to archive
        :return: photo new path
        """

        destination_path = os.path.join(self._folders.get_originals_path(), os.path.basename(photo_path))
        shutil.move(photo_path, destination_path)
        return destination_path

import os
import time

from photobooth import consts
from photobooth.api.camera.camera_abc import CameraABC


class HotfolderCamera(CameraABC):
    """
    HotfolderCamera is the WiFi camera driver.

    It waits for a new photo to appear in the camera hotfolder (for example a
    camera with wireless transfer enabled) and copies it to the destination.
    """

    def __init__(self, hotfolder_path: str, state_store):
        self._hotfolder_path = hotfolder_path
        self._state_store = state_store
        self._last_read_wifi_id = None

    def init(self):
        print("WiFi camera enabled. Skipping real camera initialization.")

    def stop(self):
        return

    def capture_via_camera(self, path: str, photo_name: str) -> str:
        return self._wait_for_photo(path, photo_name)

    def capture_via_pc(self, path: str, photo_name: str) -> str:
        return self._wait_for_photo(path, photo_name)

    @staticmethod
    def _get_photo_id(filename: str) -> int:
        """
        Extracts the last sequence of digits from a filename (excluding extension) as an integer ID.
        """
        import re
        name, _ = os.path.splitext(filename)
        digits = re.findall(r'\d+', name)
        if digits:
            return int(digits[-1])
        return 0

    def _ensure_last_read_id(self):
        if self._last_read_wifi_id is not None:
            return

        self._last_read_wifi_id = self._state_store.load_wifi_id()
        if self._last_read_wifi_id is None:
            # Initialize with the maximum ID currently in the hotfolder
            existing_files = os.listdir(self._hotfolder_path)
            existing_ids = [self._get_photo_id(f) for f in existing_files if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            self._last_read_wifi_id = max(existing_ids) if existing_ids else 0
            self._state_store.save_wifi_id(self._last_read_wifi_id)

    @staticmethod
    def is_image_complete(file_path) -> bool:
        """
        Verifies if the image is valid and not truncated by loading its pixel data.
        """
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                img.load()
            return True
        except Exception:
            return False

    def _wait_for_photo(self, path: str, photo_name: str) -> str:
        """
        Method which waits for a new photo to appear in the camera-hotfolder and copies it to the given path with the given name.
        :param path: the path where the photo has to be saved
        :param photo_name: the name of the photo to be saved
        :return: shot photo path
        """
        import shutil

        hotfolder = self._hotfolder_path
        if not hotfolder:
            print("Warning: camera_hotfolder_path is not configured.")
            return None

        if not os.path.exists(hotfolder):
            os.makedirs(hotfolder, exist_ok=True)

        self._ensure_last_read_id()

        print(f"Waiting for photo in hotfolder: {hotfolder} with ID > {self._last_read_wifi_id}")

        while True:
            current_files = os.listdir(hotfolder)
            new_candidates = []
            for f in current_files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    photo_id = self._get_photo_id(f)
                    if photo_id > self._last_read_wifi_id:
                        new_candidates.append((photo_id, f))

            # Sort by ID progressively
            new_candidates.sort(key=lambda x: x[0])

            if new_candidates:
                chosen_id, new_image_name = new_candidates[0]
                source_path = os.path.join(hotfolder, new_image_name)

                # Wait for file transfer to complete (size stops changing and image is complete)
                last_size = -1
                while True:
                    try:
                        current_size = os.path.getsize(source_path)
                        if current_size == last_size and current_size > 0:
                            if self.is_image_complete(source_path):
                                break
                        last_size = current_size
                    except OSError:
                        pass
                    time.sleep(consts.WIFI_POLL_DELAY_SEC)

                target = os.path.join(path, photo_name)
                shutil.copyfile(source_path, target)
                os.chmod(target, 0o777)

                self._last_read_wifi_id = chosen_id
                self._state_store.save_wifi_id(self._last_read_wifi_id)

                return target

            time.sleep(consts.WIFI_POLL_DELAY_SEC)
import os
import time

from photobooth import consts
from photobooth.api.camera.camera_abc import CameraABC
from photobooth.api.platform_api import camera_is_connected


class GPhoto2Camera(CameraABC):
    """
    GPhoto2Camera is the USB camera driver based on the gphoto2 library.

    This driver is the only place where gphoto2 is used: swapping the camera
    library means writing a new driver which implements CameraABC, without
    touching the rest of the application.
    """

    def __init__(self, camera_name: str):
        self._camera_name = camera_name
        self._camera = None

    def _reinitialize(self):
        print('something went wrong, re-initializing camera')
        self.init()

    def init(self):
        """
        Method which initializes the camera.
        If something goes wrong, it retries by recursion until the camera is connected.
        """

        from gphoto2 import GPhoto2Error

        while not camera_is_connected(self._camera_name):
            print('camera not found. check if it\'s connected and try again')
            time.sleep(consts.CAMERA_RETRY_DELAY_SEC)

        print('camera found')

        try:
            import gphoto2 as gp
            _, camera = gp.gp_camera_new()
            self._camera = camera
            self._camera.init()
        except GPhoto2Error as e:
            print(e)
            self.init()

    def stop(self):
        if self._camera is not None:
            self._camera.exit()

    def capture_via_camera(self, path: str, photo_name: str) -> str:
        """
        Method which waits for a photo to be taken from the camera and saves it in the given path with the given name.
        If something goes wrong, the camera is re-initialized and the shot is tried again by recursion.
        :param path: the path where the photo has to be saved
        :param photo_name: the name of the photo to be saved
        :return: shot photo path
        """

        from gphoto2 import GPhoto2Error
        import gphoto2 as gp

        try:
            timeout = consts.CAMERA_EVENT_TIMEOUT_MS  # wait 1s for each event loop

            while True:
                # waits for a camera event
                event_type, event_data = self._camera.wait_for_event(timeout)

                if event_type == gp.GP_EVENT_FILE_ADDED:
                    # a new file is added in the camera
                    folder, file_name = event_data.folder, event_data.name
                    print(f"New photo detected: {file_name} in the folder {folder}")

                    # get the file
                    target = os.path.join(path, photo_name)
                    camera_file = self._camera.file_get(folder, file_name, gp.GP_FILE_TYPE_NORMAL)
                    camera_file.save(target)
                    os.chmod(target, 0o777)

                    return target
        except GPhoto2Error as e:
            print(e)
            self._reinitialize()
            return self.capture_via_camera(path, photo_name)

    def capture_via_pc(self, path: str, photo_name: str) -> str:
        """
        Method which allows taking a photo from the connected camera and saving it in the given path with the given name.
        If something goes wrong, the camera is re-initialized and the shot is tried again by recursion.
        :param path: the path where the photo has to be saved
        :param photo_name: the name of the photo to be saved
        :return: shot photo path
        """

        from gphoto2 import GPhoto2Error
        import gphoto2 as gp

        try:
            file_path = self._camera.capture(gp.GP_CAPTURE_IMAGE)
            target = os.path.join(path, photo_name)

            camera_file = self._camera.file_get(
                file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL)
            camera_file.save(target)
            os.chmod(target, 0o777)

            return target
        except GPhoto2Error as e:
            print(e)
            self._reinitialize()
            return self.capture_via_pc(path, photo_name)
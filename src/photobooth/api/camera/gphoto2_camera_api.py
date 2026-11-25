import os
import subprocess

from photobooth import consts
from photobooth.api.camera_api import CameraAPI
from photobooth.logic.capture.ports import CameraError, CameraNotFound


class GPhoto2CameraAPI(CameraAPI):
    """
    GPhoto2CameraAPI is the USB camera driver based on the gphoto2 library
    (it implements CameraAPI).

    This driver is the only place where gphoto2 is used: swapping the camera
    library means writing a new driver, without touching the rest of the
    application. Every call makes ONE attempt and raises CameraError on failure:
    retrying is a policy of CaptureService.
    """

    def __init__(self, camera_name: str):
        self._camera_name = camera_name
        self._camera = None

    def is_connected(self) -> bool:
        """
        Method which verifies if the camera set in the settings.yaml file is connected to the PC.
        :return: True if the camera is listed by gphoto2 --auto-detect
        """

        output = subprocess.run(['gphoto2', '--auto-detect'], capture_output=True, text=True)
        return any(self._camera_name in line for line in output.stdout.split('\n'))

    def init(self):
        """
        Method which initializes the camera.
        :raises CameraNotFound: if the camera is not connected
        :raises CameraError: if gphoto2 fails to initialize it
        """

        from gphoto2 import GPhoto2Error
        import gphoto2 as gp

        if not self.is_connected():
            raise CameraNotFound(f"camera '{self._camera_name}' not found")

        try:
            _, camera = gp.gp_camera_new()
            camera.init()
            self._camera = camera
        except GPhoto2Error as e:
            raise CameraError(str(e)) from e

    def stop(self):
        if self._camera is not None:
            self._camera.exit()

    def capture_via_camera(self, path: str, photo_name: str) -> str:
        """
        Method which waits for a photo to be taken from the camera and saves it in the given path with the given name.
        :param path: the path where the photo has to be saved
        :param photo_name: the name of the photo to be saved
        :return: shot photo path
        :raises CameraError: if gphoto2 fails
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
                    return self._save_camera_file(event_data.folder, event_data.name, path, photo_name)
        except GPhoto2Error as e:
            raise CameraError(str(e)) from e

    def capture_via_pc(self, path: str, photo_name: str) -> str:
        """
        Method which allows taking a photo from the connected camera and saving it in the given path with the given name.
        :param path: the path where the photo has to be saved
        :param photo_name: the name of the photo to be saved
        :return: shot photo path
        :raises CameraError: if gphoto2 fails
        """

        from gphoto2 import GPhoto2Error
        import gphoto2 as gp

        try:
            file_path = self._camera.capture(gp.GP_CAPTURE_IMAGE)
            return self._save_camera_file(file_path.folder, file_path.name, path, photo_name)
        except GPhoto2Error as e:
            raise CameraError(str(e)) from e

    def _save_camera_file(self, folder: str, file_name: str, path: str, photo_name: str) -> str:
        import gphoto2 as gp

        target = os.path.join(path, photo_name)
        camera_file = self._camera.file_get(folder, file_name, gp.GP_FILE_TYPE_NORMAL)
        camera_file.save(target)
        os.chmod(target, 0o777)
        return target

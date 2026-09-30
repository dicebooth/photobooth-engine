from photobooth.api.camera.gphoto2_camera import GPhoto2Camera
from photobooth.api.camera.hotfolder_camera import HotfolderCamera


class CameraService:
    """
    CameraService selects the right camera driver according to the settings
    (WiFi hotfolder or gphoto2 USB) and exposes a single API to the core.

    The core only knows this service and the CameraAPI interface: it is fully
    agnostic about gphoto2 and about how the photos are taken.
    """

    def __init__(self, camera_name: str, connection: str,
                 hotfolder_path: str = '', state_store=None):
        if connection == 'wifi':
            if not hotfolder_path or state_store is None:
                raise ValueError(
                    "WiFi camera connection requires 'camera_hotfolder_path' in settings.yaml "
                    "and a state store: check the camera configuration."
                )
            self._driver = HotfolderCamera(hotfolder_path, state_store)
        else:
            self._driver = GPhoto2Camera(camera_name)

    def init_camera(self):
        self._driver.init()

    def stop_camera(self):
        self._driver.stop()

    def capture_via_camera(self, path: str, photo_name: str) -> str:
        return self._driver.capture_via_camera(path, photo_name)

    def capture_via_pc(self, path: str, photo_name: str) -> str:
        return self._driver.capture_via_pc(path, photo_name)
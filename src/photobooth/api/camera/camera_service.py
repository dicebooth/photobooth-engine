from photobooth.api.camera.camera_api import CameraAPI
from photobooth.api.camera.gphoto2_camera import GPhoto2Camera
from photobooth.api.camera.hotfolder_camera import HotfolderCamera


def build_camera(camera_name: str, connection: str,
                 hotfolder_path: str = '', state_store=None) -> CameraAPI:
    """
    Factory which selects the right camera driver according to the settings
    (WiFi hotfolder or gphoto2 USB) and returns it through the CameraAPI
    interface.

    The core only knows this interface: it is fully agnostic about gphoto2
    and about how the photos are taken.
    """
    if connection == 'wifi':
        if not hotfolder_path or state_store is None:
            raise ValueError(
                "WiFi camera connection requires 'camera_hotfolder_path' in settings.yaml "
                "and a state store: check the camera configuration."
            )
        return HotfolderCamera(hotfolder_path, state_store)
    return GPhoto2Camera(camera_name)
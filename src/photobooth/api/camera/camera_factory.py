from photobooth.api.camera.gphoto2_camera import GPhoto2Camera
from photobooth.api.camera.hotfolder_camera import HotfolderCamera
from photobooth.logic.capture.photo_id_sequencer import PhotoIdSequencer
from photobooth.logic.capture.ports import CameraPort


def build_camera(camera_name: str, connection: str,
                 hotfolder_path: str = '', sequencer: PhotoIdSequencer = None) -> CameraPort:
    """
    Factory which selects the right camera driver according to the settings
    (WiFi hotfolder or gphoto2 USB) and returns it through the CameraPort
    interface.

    The logic layer only knows this interface: it is fully agnostic about gphoto2
    and about how the photos are taken.
    """
    if connection == 'wifi':
        if not hotfolder_path or sequencer is None:
            raise ValueError(
                "WiFi camera connection requires 'camera_hotfolder_path' in settings.yaml "
                "and a photo id sequencer: check the camera configuration."
            )
        return HotfolderCamera(hotfolder_path, sequencer)
    return GPhoto2Camera(camera_name)

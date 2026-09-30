from abc import ABC, abstractmethod


class CameraAPI(ABC):
    """
    CameraAPI is the abstract interface of the camera adapter.

    Every camera driver (gphoto2 USB, WiFi hotfolder, ...) implements this
    interface, so the application is agnostic about how the photos are taken
    and a future driver can be plugged in without touching the core.

    Methods are fully headless: user prompts belong to the presentation layer.
    """

    @abstractmethod
    def init(self):
        """
        Method which initializes the camera, waiting for it to be available.
        """

    @abstractmethod
    def stop(self):
        """
        Method which releases the camera.
        """

    @abstractmethod
    def capture_via_camera(self, path: str, photo_name: str) -> str:
        """
        Method which takes a photo waiting for the camera-side trigger
        (the user presses the shutter button on the camera).
        :param path: the path where the photo has to be saved
        :param photo_name: the name of the photo to be saved
        :return: shot photo path
        """

    @abstractmethod
    def capture_via_pc(self, path: str, photo_name: str) -> str:
        """
        Method which takes a photo triggered from the PC.
        :param path: the path where the photo has to be saved
        :param photo_name: the name of the photo to be saved
        :return: shot photo path
        """
from abc import ABC, abstractmethod


class CameraAPI(ABC):
    """
    Abstract base class for camera drivers.

    Every implementation (gphoto2 USB, WiFi hotfolder, ...) makes ONE attempt
    per call and raises CameraError on failure: retries are a policy of
    CaptureService.
    """

    @abstractmethod
    def init(self) -> None:
        """Initialize the camera. Raises CameraError if it is not available."""

    @abstractmethod
    def stop(self) -> None:
        """Release the camera."""

    @abstractmethod
    def capture_via_camera(self, path: str, photo_name: str) -> str:
        """Take a photo waiting for the camera-side trigger. Returns the saved photo path."""

    @abstractmethod
    def capture_via_pc(self, path: str, photo_name: str) -> str:
        """Take a photo triggered from the PC. Returns the saved photo path."""

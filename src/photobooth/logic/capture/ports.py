from typing import Optional, Protocol, runtime_checkable


class CameraError(Exception):
    """A camera driver failed to complete one attempt (connection lost, shot failed, ...)."""


class CameraNotFound(CameraError):
    """The configured camera is not connected."""


@runtime_checkable
class CameraPort(Protocol):
    """
    CameraPort is what the logic layer needs from a camera driver.

    Every driver (gphoto2 USB, WiFi hotfolder, ...) makes ONE attempt per call
    and raises CameraError on failure: retries are a policy of CaptureService.
    """

    def init(self) -> None:
        """Initialize the camera. Raises CameraError if it is not available."""

    def stop(self) -> None:
        """Release the camera."""

    def capture_via_camera(self, path: str, photo_name: str) -> str:
        """Take a photo waiting for the camera-side trigger. Returns the saved photo path."""

    def capture_via_pc(self, path: str, photo_name: str) -> str:
        """Take a photo triggered from the PC. Returns the saved photo path."""


class PhotoIdStatePort(Protocol):
    """Persistence of the last photo ID read from the WiFi camera hotfolder."""

    def load_wifi_id(self) -> Optional[int]: ...

    def save_wifi_id(self, wifi_id: int) -> None: ...

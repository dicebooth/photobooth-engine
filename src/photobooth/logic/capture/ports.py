from typing import Optional, Protocol


class CameraError(Exception):
    """A camera driver failed to complete one attempt (connection lost, shot failed, ...)."""


class CameraNotFound(CameraError):
    """The configured camera is not connected."""


class PhotoIdStatePort(Protocol):
    """Persistence of the last photo ID read from the WiFi camera hotfolder."""

    def load_wifi_id(self) -> Optional[int]: ...

    def save_wifi_id(self, wifi_id: int) -> None: ...

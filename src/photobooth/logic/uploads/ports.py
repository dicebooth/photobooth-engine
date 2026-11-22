from typing import Protocol
from uuid import UUID


class BackendUnavailable(Exception):
    """The backend cannot be reached right now (connection, timeout or read error): worth retrying."""


class BackendPort(Protocol):
    """
    BackendPort is what the logic layer needs from the backend client.

    The client makes ONE attempt per call: raises BackendUnavailable for network
    problems (retry is a policy of UploadService), any other error is final.
    """

    def upload(self, png_base64: str, photo_name: str) -> UUID:
        """Upload an already encoded photo. Returns the new photo id."""

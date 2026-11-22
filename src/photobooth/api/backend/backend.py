from __future__ import annotations

import io
import logging
import threading
from typing import Tuple
from urllib.parse import urljoin
from uuid import UUID

import httpx
from PIL import Image

from photobooth.consts import LOGGER_NAME, DEFAULT_BACKEND_URL, DEFAULT_CLIENT_ID, DEFAULT_TIMEOUT
from photobooth.logic.uploads.ports import BackendUnavailable

# Use logger configured in main (coherent name)
logger = logging.getLogger(LOGGER_NAME)

# Network problems that are worth retrying: the backend may come back
_NETWORK_ERRORS = (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError)


class PhotoAPIClient:
    """
    PhotoAPIClient is the HTTP client of the photo backend.

    It makes ONE attempt per call (plus a single re-login on 401) and works on
    already encoded data: image conversion and retries are logic concerns.
    Network problems are raised as BackendUnavailable.
    """

    def __init__(
            self,
            base_url: str = DEFAULT_BACKEND_URL,
            client_id: str = DEFAULT_CLIENT_ID,
            client_secret: str = None,
            timeout: Tuple[float, float] = DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret

        # httpx requires all four fields or a single default
        self.timeout = httpx.Timeout(
            connect=timeout[0],
            read=timeout[1],
            write=timeout[1],
            pool=timeout[0],
        )

        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self._lock = threading.Lock()

    def login(self, force: bool = False):
        """Perform login to get JWT Bearer token."""
        if not self.client_secret:
            return

        with self._lock:
            # Check if another request already refreshed the token
            if not force and self.headers.get("Authorization"):
                return

            logger.info("Attempting login to backend...")
            payload = {"client_id": self.client_id, "client_secret": self.client_secret}
            with httpx.Client(timeout=self.timeout) as client:
                try:
                    r = client.post(f"{self.base_url}/oauth/token", json=payload)
                    r.raise_for_status()
                    token = r.json()["access_token"]
                    self.headers["Authorization"] = f"Bearer {token}"
                    logger.info("Login successful")
                except Exception as e:
                    logger.error(f"Login failed: {e}")
                    raise

    def upload(self, png_base64: str, photo_name: str = "unnamed_photo") -> UUID:
        """
        Send an already encoded photo (PNG base64) to POST /photos and return the new photo UUID.
        :raises BackendUnavailable: on connection, timeout or read errors
        """

        logger.info(f"Uploading '{photo_name}' started")

        try:
            self.login()

            with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
                r = client.post(f"{self.base_url}/photos", json={"data": png_base64})

                if r.status_code == 401 and self.client_secret:
                    logger.warning(f"401 Unauthorized for '{photo_name}', retrying login")
                    self.login(force=True)
                    with httpx.Client(timeout=self.timeout, headers=self.headers) as retry_client:
                        r = retry_client.post(f"{self.base_url}/photos", json={"data": png_base64})

                r.raise_for_status()

                photo_id = UUID(r.json()["id"])
                logger.info(f"Upload OK '{photo_name}' -> {photo_id}")
                return photo_id

        except _NETWORK_ERRORS as e:
            logger.error(f"Upload FAILED ({type(e).__name__}) for '{photo_name}'")
            raise BackendUnavailable(str(e)) from e

        except Exception:
            logger.exception(f"Unhandled error while uploading '{photo_name}'")
            raise

    # just for test purposes
    def download_image_by_id(self, photo_id: UUID):
        self.login()

        with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
            r = client.get(f"{self.base_url}/photos/{photo_id}")

            if r.status_code == 401 and self.client_secret:
                logger.warning(f"401 Unauthorized for GET photo {photo_id}, retrying")
                self.login(force=True)
                with httpx.Client(
                        timeout=self.timeout, headers=self.headers
                ) as retry_client:
                    r = retry_client.get(f"{self.base_url}/photos/{photo_id}")

            r.raise_for_status()

            raw_url = r.json()["url"]
            raw_url = urljoin(self.base_url, raw_url)

            r = client.get(raw_url)
            if r.status_code == 401 and self.client_secret:
                self.login(force=True)
                with httpx.Client(
                        timeout=self.timeout, headers=self.headers
                ) as retry_client:
                    r = retry_client.get(raw_url)
            r.raise_for_status()

        img = Image.open(io.BytesIO(r.content))
        img.load()
        return img

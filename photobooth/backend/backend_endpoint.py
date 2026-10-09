from __future__ import annotations
import base64
import io
import asyncio
import threading
from typing import Tuple
from uuid import UUID
import httpx
from PIL import Image
from urllib.parse import urljoin
import logging

from photobooth.consts import LOGGER_NAME, DEFAULT_BACKEND_URL, DEFAULT_CLIENT_ID, DEFAULT_TIMEOUT

# Use logger configured in main (coherent name)
logger = logging.getLogger(LOGGER_NAME)


class PhotoAPIClient:
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
        self._async_lock = asyncio.Lock()
        self._sync_lock = threading.Lock()

    async def login(self, force: bool = False):
        """Perform login to get JWT Bearer token (async)."""
        if not self.client_secret:
            return

        async with self._async_lock:
            # Check if another request already refreshed the token
            if not force and self.headers.get("Authorization"):
                return

            logger.info("Attempting login to backend (async)...")
            payload = {"client_id": self.client_id, "client_secret": self.client_secret}
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                try:
                    r = await client.post(f"{self.base_url}/oauth/token", json=payload)
                    r.raise_for_status()
                    token = r.json()["access_token"]
                    self.headers["Authorization"] = f"Bearer {token}"
                    logger.info("Login successful (async)")
                except Exception as e:
                    logger.error(f"Login failed (async): {e}")
                    raise

    def login_sync(self, force: bool = False):
        """Perform login to get JWT Bearer token (sync)."""
        if not self.client_secret:
            return

        with self._sync_lock:
            if not force and self.headers.get("Authorization"):
                return

            logger.info("Attempting login to backend (sync)...")
            payload = {"client_id": self.client_id, "client_secret": self.client_secret}
            with httpx.Client(timeout=self.timeout) as client:
                try:
                    r = client.post(f"{self.base_url}/oauth/token", json=payload)
                    r.raise_for_status()
                    token = r.json()["access_token"]
                    self.headers["Authorization"] = f"Bearer {token}"
                    logger.info("Login successful (sync)")
                except Exception as e:
                    logger.error(f"Login failed (sync): {e}")
                    raise

    async def upload_pil(self, img: Image.Image, photo_name: str = "unnamed_photo") -> UUID:
        """
        Send a PIL image as PNG base64 to POST /photos and return the new photo UUID (async).
        """
        logger.info(f"Uploading '{photo_name}' started")

        if img.mode not in ("RGB", "RGBA", "L", "LA"):
            img = img.convert("RGBA")

        b64 = await asyncio.to_thread(self._to_b64, img)

        if self.client_secret:
            await self.login()

        async with httpx.AsyncClient(
                timeout=self.timeout, headers=self.headers
        ) as client:
            try:
                payload = {"data": b64, "filename": photo_name}
                r = await client.post(f"{self.base_url}/photos", json=payload)

                if r.status_code == 401 and self.client_secret:
                    logger.warning(
                        f"401 Unauthorized for '{photo_name}', retrying login"
                    )
                    await self.login(force=True)
                    async with httpx.AsyncClient(
                            timeout=self.timeout, headers=self.headers
                    ) as retry_client:
                        r = await retry_client.post(
                            f"{self.base_url}/photos", json=payload
                        )

                r.raise_for_status()

                photo_id = UUID(r.json()["id"])
                logger.info(f"Upload OK '{photo_name}' -> {photo_id}")

                return photo_id

            except httpx.TimeoutException:
                logger.error(f"Upload FAILED (timeout) for '{photo_name}'")
                raise

            except httpx.ConnectError:
                logger.error(
                    f"Upload FAILED (backend unreachable) for '{photo_name}'. Connection Error"
                )
                raise

            except httpx.ReadError:
                logger.error(
                    f"Upload FAILED (backend unreachable) for '{photo_name}'. Read Error"
                )
                raise

            except Exception:
                logger.exception(f"Unhandled error while uploading '{photo_name}'")
                raise

    # ---------- BACKGROUND ----------
    def upload_pil_background(self, img: Image.Image, photo_name: str = "unnamed_photo") -> None:
        """Fire-and-forget upload that never blocks the caller."""

        def _worker():
            not_sent = True

            while not_sent:
                try:
                    asyncio.run(self.upload_pil(img, photo_name))
                    not_sent = False

                except httpx.ConnectError:
                    logger.info(
                        f"The upload of '{photo_name}' will be retried in 5 seconds"
                    )
                    import time

                    time.sleep(5)
                except httpx.TimeoutException:
                    logger.info(
                        f"The upload of '{photo_name}' will be retried in 5 seconds"
                    )
                    import time

                    time.sleep(5)
                except httpx.ReadError:
                    logger.info(
                        f"The upload of '{photo_name}' will be retried in 5 seconds"
                    )
                    import time

                    time.sleep(5)
                except Exception:
                    logger.exception(
                        f"[PhotoAPIClient] Background upload failed for '{photo_name}'"
                    )
                    not_sent = False

        threading.Thread(target=_worker, daemon=True).start()

    # ---------- SYNC VERSION ----------
    def upload_pil_sync(self, img: Image.Image, photo_name: str = "unnamed_photo") -> UUID:
        """Blocking version (no asyncio)."""

        logger.info(f"Uploading '{photo_name}' started")

        if img.mode not in ("RGB", "RGBA", "L", "LA"):
            img = img.convert("RGBA")

        b64 = self._to_b64(img)

        if self.client_secret:
            self.login_sync()

        with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
            try:
                payload = {"data": b64, "filename": photo_name}
                r = client.post(f"{self.base_url}/photos", json=payload)

                if r.status_code == 401 and self.client_secret:
                    logger.warning(
                        f"401 Unauthorized for '{photo_name}' (sync), retrying login"
                    )
                    self.login_sync(force=True)
                    with httpx.Client(
                            timeout=self.timeout, headers=self.headers
                    ) as retry_client:
                        r = retry_client.post(
                            f"{self.base_url}/photos", json=payload
                        )

                r.raise_for_status()

                photo_id = UUID(r.json()["id"])
                logger.info(f"Upload OK '{photo_name}' → {photo_id}")

                return photo_id

            except httpx.TimeoutException:
                logger.error(f"Upload FAILED (timeout) for '{photo_name}'")
                raise

            except httpx.ConnectError:
                logger.error(f"Upload FAILED (backend unreachable) for '{photo_name}'")
                raise

            except Exception:
                logger.exception(f"Unhandled error while uploading '{photo_name}'")
                raise

    # just for test purposes
    def download_image_by_id(self, photo_id: UUID):
        if self.client_secret:
            self.login_sync()

        with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
            r = client.get(f"{self.base_url}/photos/{photo_id}")

            if r.status_code == 401 and self.client_secret:
                logger.warning(f"401 Unauthorized for GET photo {photo_id}, retrying")
                self.login_sync(force=True)
                with httpx.Client(
                        timeout=self.timeout, headers=self.headers
                ) as retry_client:
                    r = retry_client.get(f"{self.base_url}/photos/{photo_id}")

            r.raise_for_status()

            raw_url = r.json()["url"]
            raw_url = urljoin(self.base_url, raw_url)

            r = client.get(raw_url)
            if r.status_code == 401 and self.client_secret:
                self.login_sync(force=True)
                with httpx.Client(
                        timeout=self.timeout, headers=self.headers
                ) as retry_client:
                    r = retry_client.get(raw_url)
            r.raise_for_status()

        img = Image.open(io.BytesIO(r.content))
        img.load()
        return img

    def _to_b64(self, img: Image.Image) -> str:
        if img.mode not in ("RGB", "RGBA", "L", "LA"):
            img = img.convert("RGBA")

        img.load()
        img = img.copy()

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return encoded

"""
Shared state between the engine thread and the web portal.
The engine updates the session through WebUserInterface, while HTTP handlers read it and submit user responses.
"""
import io
import os
import queue
import re
import threading

from PIL import Image

from photobooth.settings_manager import Settings

PHASE_IDLE = "idle"
PHASE_WAITING_SHOT = "waiting_shot"
PHASE_APPROVAL = "approval"
PHASE_COPIES = "copies"
PHASE_PROCESSING = "processing"

PREVIEW_MAX_SIZE = (1600, 1600)
THUMB_MAX_SIZE = (360, 360)
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png')


def _natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def _encode_jpeg(img: Image.Image, max_size) -> bytes:
    img = img.copy()
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


class WebSession:

    def __init__(self, framed_photos_path: str):
        self._settings = Settings()
        self._framed_photos_path = framed_photos_path

        self._lock = threading.Lock()
        self._changed = threading.Condition(self._lock)
        self._version = 0

        self._phase = PHASE_IDLE
        self._status = "Avvio in corso..."
        self._preview_kind = None
        self._preview_img = None
        self._preview_id = 0
        self._preview_jpeg = None
        self._camera_ok = None
        self._printer_ok = None

        # Responses are delivered either to our own queue (headless mode) or to a delegate (e.g. the Tkinter GUI)
        self._responses = queue.Queue()
        self._responder = None
        self._reprint_handler = None

        self._thumb_cache = {}

        # these settings are read once: the snapshot is built on every state change
        self._copies_limits = {
            "min": self._settings.get_min_num_photos(),
            "max": self._settings.get_max_num_photos(),
            "warn": self._settings.get_warn_num_photos(),
        }
        self._event_name = self._settings.get_event_name()

    # ---------- engine side ----------

    def set_responder(self, responder):
        """
        Routes web responses to an external handler instead of the internal queue.
        :param responder: callable(kind, value) -> bool, returns False if the response was not accepted
        """
        self._responder = responder

    def set_reprint_handler(self, handler):
        """
        :param handler: callable(photo name, copies) -> photos still waiting in the print queue
        """
        self._reprint_handler = handler

    def set_phase(self, phase: str, status: str = None):
        with self._lock:
            self._phase = phase
            if status is not None:
                self._status = status
            self._bump()

    def set_status(self, status: str):
        with self._lock:
            self._status = status
            self._bump()

    def set_hardware_status(self, camera_ok: bool, printer_ok: bool):
        with self._lock:
            self._camera_ok = camera_ok
            self._printer_ok = printer_ok
            self._bump()

    def set_preview(self, image_or_path, kind: str):
        img = None
        try:
            if isinstance(image_or_path, Image.Image):
                img = image_or_path.copy()
            elif isinstance(image_or_path, str) and os.path.exists(image_or_path):
                with Image.open(image_or_path) as src:
                    img = src.copy()
        except Exception as e:
            print(f"Error loading web preview: {e}")

        with self._lock:
            self._preview_img = img
            self._preview_jpeg = None
            self._preview_kind = kind
            self._preview_id += 1
            self._bump()

    def clear_preview(self):
        with self._lock:
            self._preview_img = None
            self._preview_jpeg = None
            self._preview_kind = None
            self._preview_id += 1
            self._bump()

    def wait_response(self):
        return self._responses.get()

    # ---------- web side ----------

    def submit(self, kind: str, value) -> bool:
        """
        Delivers a user response coming from the portal if the engine is currently waiting for it.
        :param kind: PHASE_APPROVAL or PHASE_COPIES
        :param value: bool for approval, int for copies
        :return: True if the response has been accepted
        """
        with self._lock:
            if self._phase != kind:
                return False
            if self._responder is None:
                self._phase = PHASE_PROCESSING
                self._status = "Elaborazione..."
                self._bump()
                self._responses.put(value)
                return True

        # the delegate has its own guard against duplicate answers
        return self._responder(kind, value)

    def snapshot(self) -> dict:
        with self._lock:
            return self._snapshot_locked()

    def wait_for_change(self, last_version: int, timeout: float) -> dict:
        with self._changed:
            self._changed.wait_for(lambda: self._version != last_version, timeout=timeout)
            return self._snapshot_locked()

    def get_preview_jpeg(self):
        with self._lock:
            if self._preview_img is None:
                return None
            if self._preview_jpeg is None:
                self._preview_jpeg = _encode_jpeg(self._preview_img, PREVIEW_MAX_SIZE)
            return self._preview_jpeg

    def list_gallery(self) -> list:
        """
        :return: framed photos, newest first, as {name, version}: version changes with the file,
                 so that browsers never show a cached image of a different photo with the same name
        """
        if not os.path.isdir(self._framed_photos_path):
            return []
        photos = [f for f in os.listdir(self._framed_photos_path) if f.lower().endswith(IMAGE_EXTENSIONS)]
        photos.sort(key=_natural_sort_key, reverse=True)
        return [{"name": name, "version": int(os.path.getmtime(os.path.join(self._framed_photos_path, name)))}
                for name in photos]

    def reprint(self, name: str, copies: int) -> int:
        """
        Prints again a photo of the gallery.
        :return: photos still waiting in the print queue
        """
        if self._reprint_handler is None:
            raise RuntimeError("reprint not available")
        return self._reprint_handler(name, copies)

    def get_gallery_image(self, name: str, thumbnail: bool):
        """
        :return: (bytes, content type) or None if the file does not exist
        """
        if name != os.path.basename(name) or not name.lower().endswith(IMAGE_EXTENSIONS):
            return None
        path = os.path.join(self._framed_photos_path, name)
        if not os.path.isfile(path):
            return None

        if not thumbnail:
            with open(path, 'rb') as f:
                data = f.read()
            content_type = "image/png" if name.lower().endswith(".png") else "image/jpeg"
            return data, content_type

        mtime = os.path.getmtime(path)
        cached = self._thumb_cache.get(name)
        if cached and cached[0] == mtime:
            return cached[1], "image/jpeg"
        with Image.open(path) as img:
            data = _encode_jpeg(img, THUMB_MAX_SIZE)
        self._thumb_cache[name] = (mtime, data)
        return data, "image/jpeg"

    # ---------- internals ----------

    def _bump(self):
        self._version += 1
        self._changed.notify_all()

    def _snapshot_locked(self) -> dict:
        return {
            "version": self._version,
            "phase": self._phase,
            "status": self._status,
            "preview": {
                "id": self._preview_id,
                "kind": self._preview_kind,
                "available": self._preview_img is not None,
            },
            "copies": self._copies_limits,
            "hardware": {
                "camera": self._camera_ok,
                "printer": self._printer_ok,
            },
            "event_name": self._event_name,
        }

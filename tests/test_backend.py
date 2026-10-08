import os
import socket

import pytest
from PIL import Image, ImageChops

from photobooth.api.backend.backend import PhotoAPIClient
from photobooth.consts import DEFAULT_BACKEND_URL

ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')

# This is an integration test: it runs only when explicitly enabled, so the
# default test suite never depends on an external service.
RUN_BACKEND_TESTS_ENV = 'PHOTOBOOTH_RUN_BACKEND_TESTS'


def backend_is_reachable(url: str = DEFAULT_BACKEND_URL) -> bool:
    """
    Helper function which verifies if a backend is listening on the given URL.
    """
    from urllib.parse import urlparse
    parsed = urlparse(url)
    host = parsed.hostname or 'localhost'
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(
    os.environ.get(RUN_BACKEND_TESTS_ENV) != '1' or not backend_is_reachable(),
    reason=(
        f"Backend integration test disabled by default: start a backend on {DEFAULT_BACKEND_URL} "
        f"and set {RUN_BACKEND_TESTS_ENV}=1 to run it."
    ),
)


def images_equal(a, b):
    a = a.convert("RGB")
    b = b.convert("RGB")
    return a.size == b.size and ImageChops.difference(a, b).getbbox() is None


def test_backend():
    test_image_path = os.path.join(ASSETS_DIR, 'test.png')
    image = Image.open(test_image_path)
    backend = PhotoAPIClient()

    uuid = backend.upload_pil_sync(image)
    server_image = backend.download_image_by_id(uuid)

    assert images_equal(image, server_image)
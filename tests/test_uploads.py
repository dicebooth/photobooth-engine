import base64
import io
from uuid import uuid4

import pytest
from PIL import Image

from photobooth.logic.editing.photo_encoder import PhotoEncoder
from photobooth.logic.uploads.ports import BackendUnavailable
from photobooth.logic.uploads.upload_service import UploadService


# ------------------------------------------------------------------- encoder

def _decode(png_base64: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(png_base64)))


@pytest.mark.parametrize('mode', ['RGB', 'RGBA', 'L', 'LA'])
def test_encoder_keeps_png_compatible_modes(mode):
    decoded = _decode(PhotoEncoder().to_png_base64(Image.new(mode, (4, 3))))

    assert decoded.format == 'PNG'
    assert decoded.mode == mode
    assert decoded.size == (4, 3)


@pytest.mark.parametrize('mode', ['CMYK', 'P', '1'])
def test_encoder_converts_exotic_modes_to_rgba(mode):
    decoded = _decode(PhotoEncoder().to_png_base64(Image.new(mode, (4, 3))))

    assert decoded.mode == 'RGBA'


def test_encoder_does_not_modify_the_given_image():
    image = Image.new('CMYK', (2, 2))

    PhotoEncoder().to_png_base64(image)

    assert image.mode == 'CMYK'


# ------------------------------------------------------------ upload service

class FlakyBackend:
    def __init__(self, failures):
        self._failures = list(failures)
        self.calls = []

    def upload(self, png_base64, photo_name):
        self.calls.append((png_base64, photo_name))
        if self._failures:
            raise self._failures.pop(0)
        return uuid4()


def _service(backend, sleeps):
    return UploadService(backend, PhotoEncoder(), retry_delay_sec=7, sleep=sleeps.append)


def test_upload_is_retried_forever_while_the_backend_is_unreachable():
    backend = FlakyBackend([BackendUnavailable()] * 5)
    sleeps = []

    _service(backend, sleeps).upload_until_done(Image.new('RGB', (2, 2)), 'a.jpg')

    assert len(backend.calls) == 6
    assert sleeps == [7] * 5
    # the same encoded payload is sent every time
    assert len({payload for payload, _ in backend.calls}) == 1


def test_other_errors_are_final():
    backend = FlakyBackend([ValueError('rejected')])
    sleeps = []

    _service(backend, sleeps).upload_until_done(Image.new('RGB', (2, 2)), 'a.jpg')

    assert len(backend.calls) == 1
    assert sleeps == []


def test_send_photo_runs_in_the_background_and_returns_the_thread():
    backend = FlakyBackend([])

    thread = _service(backend, []).send_photo(Image.new('RGB', (2, 2)), 'a.jpg')
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert backend.calls[0][1] == 'a.jpg'

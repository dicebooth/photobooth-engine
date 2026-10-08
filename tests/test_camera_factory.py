import pytest

from photobooth.api.camera.camera_api import CameraAPI
from photobooth.api.camera.camera_service import build_camera
from photobooth.api.camera.gphoto2_camera import GPhoto2Camera
from photobooth.api.camera.hotfolder_camera import HotfolderCamera
from photobooth.db.state_store import StateStore


def test_build_camera_usb_returns_gphoto2_driver(tmp_path):
    camera = build_camera(camera_name='test', connection='usb')

    assert isinstance(camera, GPhoto2Camera)
    assert isinstance(camera, CameraAPI)


def test_build_camera_wifi_returns_hotfolder_driver(tmp_path):
    state_store = StateStore(str(tmp_path / 'temp_data.yaml'))
    hotfolder = str(tmp_path / 'hotfolder')

    camera = build_camera(
        camera_name='test', connection='wifi',
        hotfolder_path=hotfolder, state_store=state_store,
    )

    assert isinstance(camera, HotfolderCamera)
    assert isinstance(camera, CameraAPI)


def test_build_camera_wifi_without_hotfolder_raises():
    with pytest.raises(ValueError, match='camera_hotfolder_path'):
        build_camera(camera_name='test', connection='wifi', state_store=None)


def test_build_camera_wifi_without_state_store_raises(tmp_path):
    with pytest.raises(ValueError, match='state store'):
        build_camera(
            camera_name='test', connection='wifi',
            hotfolder_path=str(tmp_path / 'hotfolder'), state_store=None,
        )

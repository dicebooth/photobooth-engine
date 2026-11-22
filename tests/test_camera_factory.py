import pytest

from photobooth.api.camera.camera_factory import build_camera
from photobooth.api.camera.gphoto2_camera import GPhoto2Camera
from photobooth.api.camera.hotfolder_camera import HotfolderCamera
from photobooth.db.state_store import StateStore
from photobooth.logic.capture.photo_id_sequencer import PhotoIdSequencer
from photobooth.logic.capture.ports import CameraPort


def test_build_camera_usb_returns_gphoto2_driver(tmp_path):
    camera = build_camera(camera_name='test', connection='usb')

    assert isinstance(camera, GPhoto2Camera)
    assert isinstance(camera, CameraPort)


def test_build_camera_wifi_returns_hotfolder_driver(tmp_path):
    state_store = StateStore(str(tmp_path / 'temp_data.yaml'))
    hotfolder = str(tmp_path / 'hotfolder')

    camera = build_camera(
        camera_name='test', connection='wifi',
        hotfolder_path=hotfolder, sequencer=PhotoIdSequencer(state_store),
    )

    assert isinstance(camera, HotfolderCamera)
    assert isinstance(camera, CameraPort)


def test_build_camera_wifi_without_hotfolder_raises():
    with pytest.raises(ValueError, match='camera_hotfolder_path'):
        build_camera(camera_name='test', connection='wifi', sequencer=None)


def test_build_camera_wifi_without_sequencer_raises(tmp_path):
    with pytest.raises(ValueError, match='sequencer'):
        build_camera(
            camera_name='test', connection='wifi',
            hotfolder_path=str(tmp_path / 'hotfolder'), sequencer=None,
        )

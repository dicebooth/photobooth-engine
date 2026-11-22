import pytest

from photobooth.logic.frames.frame_catalog import FrameCatalog
from photobooth.logic.frames.frame_chooser_service import FrameChooserService


def _frames_dir(tmp_path, names):
    for name in names:
        (tmp_path / name).write_bytes(b'png')
    return str(tmp_path)


def test_catalog_lists_only_png_frames_sorted(tmp_path):
    catalog = FrameCatalog(_frames_dir(tmp_path, ['b.png', 'a.png', '.DS_Store', 'Thumbs.db']))

    assert catalog.names() == ['a', 'b']
    assert not catalog.is_single()


def test_catalog_is_single_ignores_metadata_files(tmp_path):
    catalog = FrameCatalog(_frames_dir(tmp_path, ['only.png', '.DS_Store']))

    assert catalog.is_single()


@pytest.mark.parametrize('name', ['frame', 'frame.png'])
def test_catalog_resolves_path_with_or_without_extension(tmp_path, name):
    catalog = FrameCatalog(str(tmp_path))

    assert catalog.path_of(name) == str(tmp_path / 'frame.png')


def test_chooser_strategies(tmp_path):
    several = FrameCatalog(_frames_dir(tmp_path, ['a.png', 'b.png']))

    assert FrameChooserService(several, 'a').strategy() == 'configured'
    assert FrameChooserService(several).strategy() == 'random'
    assert FrameChooserService(several, fallback_strategy='manual').strategy() == 'manual'


def test_chooser_single_frame_strategy(tmp_path):
    single = FrameCatalog(_frames_dir(tmp_path, ['a.png']))
    chooser = FrameChooserService(single)

    assert chooser.strategy() == 'single'
    assert chooser.next_frame_name() == 'a.png'


def test_chooser_rotates_frames_round_robin(tmp_path):
    chooser = FrameChooserService(FrameCatalog(_frames_dir(tmp_path, ['a.png', 'b.png'])))

    assert [chooser.next_frame_name() for _ in range(3)] == ['a.png', 'b.png', 'a.png']


def test_chooser_configured_frame_gets_png_extension(tmp_path):
    chooser = FrameChooserService(FrameCatalog(_frames_dir(tmp_path, ['a.png', 'b.png'])), 'b')

    assert chooser.next_frame_name() == 'b.png'

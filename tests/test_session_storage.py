import os

from photobooth.logic.session.folder_manager import FolderManager
from photobooth.logic.session.originals_archiver import OriginalsArchiver


def _touch(path):
    with open(path, 'w') as f:
        f.write('x')


def test_folder_manager_creates_the_folder_tree(tmp_path):
    folders = FolderManager(str(tmp_path / 'storage'))

    for path in (folders.get_current_path(), folders.get_originals_path(), folders.get_output_folder_path()):
        assert os.path.isdir(path)
    assert folders.get_current_path().endswith(os.path.join('user_data', 'current'))


def test_archive_current_moves_everything_and_returns_chosen_new_path(tmp_path):
    folders = FolderManager(str(tmp_path))
    archiver = OriginalsArchiver(folders)
    chosen = os.path.join(folders.get_current_path(), 'a.jpg')
    other = os.path.join(folders.get_current_path(), 'b.jpg')
    _touch(chosen)
    _touch(other)

    new_path = archiver.archive_current(chosen)

    assert new_path == os.path.join(folders.get_originals_path(), 'a.jpg')
    assert os.listdir(folders.get_current_path()) == []
    assert sorted(os.listdir(folders.get_originals_path())) == ['a.jpg', 'b.jpg']


def test_archive_current_without_chosen_photo_returns_empty_string(tmp_path):
    folders = FolderManager(str(tmp_path))
    archiver = OriginalsArchiver(folders)
    _touch(os.path.join(folders.get_current_path(), 'a.jpg'))

    assert archiver.archive_current() == ''
    assert os.listdir(folders.get_current_path()) == []


def test_archive_photo_moves_only_that_photo(tmp_path):
    folders = FolderManager(str(tmp_path))
    archiver = OriginalsArchiver(folders)
    rejected = os.path.join(folders.get_current_path(), 'a.jpg')
    kept = os.path.join(folders.get_current_path(), 'b.jpg')
    _touch(rejected)
    _touch(kept)

    archiver.archive_photo(rejected)

    assert os.listdir(folders.get_originals_path()) == ['a.jpg']
    assert os.listdir(folders.get_current_path()) == ['b.jpg']

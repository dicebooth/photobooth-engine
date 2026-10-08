import os

from PIL import Image, ImageChops

from photobooth.core.editor_service import EditorService

ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')


def images_equal(a, b):
    a = a.convert("RGB")
    b = b.convert("RGB")
    return a.size == b.size and ImageChops.difference(a, b).getbbox() is None


def test_photo_edit():
    photo_path = os.path.join(ASSETS_DIR, 'mock', 'photo.jpg')
    frame_path = os.path.join(ASSETS_DIR, 'frame.png')
    test_path = os.path.join(ASSETS_DIR, 'test.png')

    editor = EditorService()
    edited = editor.prepare_single_photo(photo_path, frame_path)

    expected = Image.open(test_path)

    assert images_equal(edited, expected)


def test_edits_to_print(tmp_path):
    photo_path = os.path.join(ASSETS_DIR, 'mock', 'photo.jpg')
    frame_path = os.path.join(ASSETS_DIR, 'frame.png')
    test_path = os.path.join(ASSETS_DIR, 'edits_to_print.jpg')

    tmp_path = str(tmp_path)

    editor = EditorService()
    output_path = editor.edit([photo_path, photo_path], [frame_path, frame_path], tmp_path)

    output_image = Image.open(output_path)
    expected_image = Image.open(test_path)

    assert images_equal(output_image, expected_image)
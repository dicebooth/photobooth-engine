from photobooth.core.photo_edit_manager import Tailor as Editor
from PIL import Image, ImageChops
import os

def images_equal(a, b):
    a = a.convert("RGB")
    b = b.convert("RGB")
    return a.size == b.size and ImageChops.difference(a, b).getbbox() is None

def test_photo_edit():
    photo_path = './test/assets/mock/photo.jpg'
    frame_path = './test/assets/frame.png'
    test_path = './test/assets/test.png'

    editor = Editor()
    edited = editor.prepare_single_photo(photo_path, frame_path)

    expected = Image.open(test_path)

    assert images_equal(edited, expected)


def test_edits_to_print():
    photo_path = './test/assets/mock/photo.jpg'
    frame_path = './test/assets/frame.png'
    test_path = './test/assets/edits_to_print.jpg'
    tmp_path = './test/tmp'

    os.makedirs(tmp_path)

    editor = Editor()
    editor.set_infos([photo_path, photo_path], [frame_path, frame_path], tmp_path)
    output_path = editor.edit()

    output_image = Image.open(output_path)
    expected_image = Image.open(test_path)

    os.remove(output_path)
    os.rmdir(tmp_path)

    assert images_equal(output_image,expected_image)




# test_edits_to_print()
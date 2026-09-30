import argparse
import os
import re

from tqdm import tqdm

from photobooth.core.editor_service import EditorService

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def natural_sort_key(s):
    """Helper function to sort alphanumeric strings naturally."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def find_photos(directory):
    """Finds all image files in a directory sorted naturally (case-insensitive)."""
    photos = []
    # filter files first
    img_files = [f for f in os.listdir(directory) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
    # sort them naturally
    for f in sorted(img_files, key=natural_sort_key):
        photos.append(os.path.join(directory, f))
    return photos


def check_effect(effect_path):
    return os.path.isfile(effect_path) & effect_path.lower().endswith('.png')


def main():
    parser = argparse.ArgumentParser(description='Bulk edit photos from a directory.')
    parser.add_argument(
        '--input_dir',
        help='Directory containing photos to edit.',
        default=os.path.join(PROJECT_ROOT, 'tests/assets/in')
    )
    parser.add_argument(
        '--output_dir',
        help='Directory to save edited photos.',
        default=os.path.join(PROJECT_ROOT, 'tests/assets/out')
    )
    parser.add_argument(
        '--frame_path',
        help='Effect (frame file) path.',
        default=os.path.join(PROJECT_ROOT, 'Assets/frame1.png')
    )
    parser.add_argument(
        '--vertical_alignment',
        help="Vertical alignment of photo inside the frame ('center', 'top', 'bottom').",
        default='bottom'
    )
    parser.add_argument(
        '--auto_orientation',
        action='store_false',
        dest='auto_orientation',
        help="Enable EXIF-based photo orientation correction."
    )
    parser.set_defaults(keep_orientation=True)
    args = parser.parse_args()

    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory not found at {args.input_dir}")
        return

    os.makedirs(args.output_dir, exist_ok=True)

    photos = find_photos(args.input_dir)
    if len(photos) < 1:
        print("Error: Empty input directory.")
        return

    effect = args.frame_path
    if not check_effect(effect):
        print(f"Error: No effect found in {args.frame_path}.")
        return

    tailor = EditorService()

    progress_bar = tqdm(photos, desc="Processing photos")
    for photo in progress_bar:
        progress_bar.set_description(f"Processing {os.path.basename(photo)} with effect {os.path.basename(effect)}")
        edited_path = tailor.prepare_single_photo(
            photo,
            effect,
            vertical_alignment=args.vertical_alignment,
            auto_orientation=args.auto_orientation
        )
        save_path = os.path.join(args.output_dir, os.path.basename(photo))
        # progress_bar.set_description(f"Processing {os.path.basename(photo)} with effect {os.path.basename(effect)} to {save_path} \n") #log mode
        edited_path.save(save_path)


if __name__ == '__main__':
    main()
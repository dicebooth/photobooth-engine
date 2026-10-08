import argparse
import os
import re
import sys

from PIL import Image, ImageOps
from tqdm import tqdm


def natural_sort_key(s):
    """Helper function to sort alphanumeric strings naturally."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def find_photos(directory):
    """Finds all image files in a directory sorted naturally (case-insensitive)."""
    photos = []
    # filter files first
    img_files = [f for f in os.listdir(directory) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'))]
    # sort them naturally
    for f in sorted(img_files, key=natural_sort_key):
        photos.append(os.path.join(directory, f))
    return photos


def crop_to_aspect_ratio(img, target_ratio):
    """Crops an image from the center to match the target aspect ratio."""
    w, h = img.size
    current_ratio = w / h
    if abs(current_ratio - target_ratio) < 0.01:
        return img

    if current_ratio > target_ratio:
        # Too wide, crop sides
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        return img.crop((left, 0, left + new_w, h))
    else:
        # Too tall, crop top/bottom
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        return img.crop((0, top, w, top + new_h))


def process_image(photo_path, target_ratio, strict=False):
    """Loads, corrects orientation, and crops/checks aspect ratio of an image."""
    img = Image.open(photo_path)
    img = ImageOps.exif_transpose(img)
    
    # Check strict ratio if requested
    w, h = img.size
    current_ratio = w / h
    
    if strict and abs(current_ratio - target_ratio) > 0.01:
        raise ValueError(
            f"Photo {os.path.basename(photo_path)} aspect ratio {current_ratio:.3f} "
            f"does not satisfy the required 4:3 aspect ratio."
        )

    # Convert to RGB mode (to drop alpha channel if any, preventing JPEG save errors)
    if img.mode != 'RGB':
        img = img.convert('RGB')

    return crop_to_aspect_ratio(img, target_ratio)


def main():
    parser = argparse.ArgumentParser(
        description="Merge pairs of 4x3 photos into 4x6 sheets for DNP QW410 printing."
    )
    parser.add_argument(
        'input_dir',
        help='Directory containing photos to process.'
    )
    parser.add_argument(
        'output_dir',
        help='Directory where the merged 4x6 photos will be saved.'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Fail if any photo aspect ratio does not satisfy 4x3 ratio.'
    )
    parser.add_argument(
        '--border-width',
        type=int,
        default=0,
        help='Border width between photos in pixels (default: 0).'
    )
    parser.add_argument(
        '--border-color',
        default='white',
        help='Border color (name or RGB e.g. "white", "black", "rgb(240,240,240)").'
    )
    parser.add_argument(
        '--orientation',
        choices=['auto', 'landscape', 'portrait'],
        default='auto',
        help='Force layout orientation. "auto" detects based on the first photo in each pair.'
    )
    parser.add_argument(
        '--dpi',
        type=int,
        default=300,
        help='Output DPI for the 4x6 print. Standard is 300 (gives 1200x1800 or 1800x1200). '
             'Set to 0 to dynamically resize to match the original source photo dimensions.'
    )

    args = parser.parse_args()

    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory not found at {args.input_dir}")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    photos = find_photos(args.input_dir)
    if not photos:
        print(f"Error: No photos found in input directory: {args.input_dir}")
        sys.exit(1)

    print(f"Found {len(photos)} photos to process.")

    # Group into pairs
    pairs = [photos[i:i + 2] for i in range(0, len(photos), 2)]
    
    progress = tqdm(pairs, desc="Merging photos")
    for idx, pair in enumerate(progress):
        p1_path = pair[0]
        p2_path = pair[1] if len(pair) > 1 else None
        
        try:
            # Load first image to inspect orientation
            img1_raw = Image.open(p1_path)
            img1_raw = ImageOps.exif_transpose(img1_raw)
            w1, h1 = img1_raw.size
            
            # Determine orientation
            if args.orientation == 'landscape':
                is_landscape = True
            elif args.orientation == 'portrait':
                is_landscape = False
            else:
                is_landscape = w1 >= h1
                
            # Define target ratio (4:3 for landscape, 3:4 for portrait)
            target_ratio = 4/3 if is_landscape else 3/4
            
            # Process first photo
            img1 = process_image(p1_path, target_ratio, args.strict)
            
            # Process second photo if it exists, or create a blank placeholder
            if p2_path:
                img2 = process_image(p2_path, target_ratio, args.strict)
            else:
                # Odd number of photos. Create blank canvas matching img1 size
                img2 = Image.new('RGB', img1.size, args.border_color)
                print(f"\nWarning: Odd number of photos. Paired {os.path.basename(p1_path)} with a blank image.")

            # Determine resizing dimensions
            if args.dpi > 0:
                # Standardized output size based on DPI
                # A 4x6 print at args.dpi DPI:
                # - Landscape paper (6x4): 6 * DPI wide, 4 * DPI high.
                #   This corresponds to two portrait (3x4) photos side-by-side.
                #   Each photo has width = 3 * DPI, height = 4 * DPI.
                # - Portrait paper (4x6): 4 * DPI wide, 6 * DPI high.
                #   This corresponds to two landscape (4x3) photos stacked vertically.
                #   Each photo has width = 4 * DPI, height = 3 * DPI.
                if is_landscape:
                    # Stacked vertically. Output target: (4 * DPI) x (6 * DPI)
                    # Individual photo target: (4 * DPI) x (3 * DPI)
                    photo_w = 4 * args.dpi
                    photo_h = 3 * args.dpi
                else:
                    # Side-by-side. Output target: (6 * DPI) x (4 * DPI)
                    # Individual photo target: (3 * DPI) x (4 * DPI)
                    photo_w = 3 * args.dpi
                    photo_h = 4 * args.dpi
            else:
                # Dynamic sizing to preserve maximum resolution
                if is_landscape:
                    photo_w = max(img1.width, img2.width)
                    photo_h = int(photo_w * 3 / 4)
                else:
                    photo_h = max(img1.height, img2.height)
                    photo_w = int(photo_h * 3 / 4)

            # Resize both photos to the target size
            img1 = img1.resize((photo_w, photo_h), Image.Resampling.LANCZOS)
            img2 = img2.resize((photo_w, photo_h), Image.Resampling.LANCZOS)

            # Create the merged canvas
            if is_landscape:
                # Stacked vertically (4x6 portrait orientation)
                canvas_w = photo_w
                canvas_h = (photo_h * 2) + args.border_width
                canvas = Image.new('RGB', (canvas_w, canvas_h), args.border_color)
                canvas.paste(img1, (0, 0))
                canvas.paste(img2, (0, photo_h + args.border_width))
            else:
                # Side-by-side (6x4 landscape orientation)
                canvas_w = (photo_w * 2) + args.border_width
                canvas_h = photo_h
                canvas = Image.new('RGB', (canvas_w, canvas_h), args.border_color)
                canvas.paste(img1, (0, 0))
                canvas.paste(img2, (photo_w + args.border_width, 0))

            # Build filename: base1_base2.jpg or base1_solo.jpg
            base1 = os.path.splitext(os.path.basename(p1_path))[0]
            if p2_path:
                base2 = os.path.splitext(os.path.basename(p2_path))[0]
                out_name = f"{base1}_{base2}.jpg"
            else:
                out_name = f"{base1}_solo.jpg"
                
            out_path = os.path.join(args.output_dir, out_name)
            
            # Save the final image
            canvas.save(out_path, 'JPEG', quality=95)
            # Make the output file writeable/executable by other tools/users
            try:
                os.chmod(out_path, 0o777)
            except OSError:
                pass
                
        except Exception as e:
            print(f"\nError processing pair starting with {os.path.basename(p1_path)}: {e}")
            continue

    print(f"\nSuccessfully processed all pairs. Merged files saved to: {args.output_dir}")


if __name__ == '__main__':
    main()

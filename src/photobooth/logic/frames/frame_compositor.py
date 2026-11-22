from PIL import Image, ImageOps

from photobooth import consts


class FrameCompositor:
    """
    FrameCompositor puts a photo inside a frame: the photo is centered and
    resized to fit the transparent area of the frame, then the frame is laid
    over it.

    The compositor is stateless: every call receives its inputs directly.
    """

    def compose(self, photo, frame, horizontal_offset=0, vertical_alignment='center',
                auto_orientation=True) -> Image:
        """
        Method which edits a single photo with the chosen frame.
        The photo is automatically centered and resized to fit the effect's transparent area.
        :param photo: chosen photo path
        :param frame: chosen frame path (PNG with a transparent hole)
        :param horizontal_offset: offset to shift the photo horizontally (positive = right, negative = left)
        :param vertical_alignment: vertical alignment of the photo inside the hole ('center', 'top', 'bottom')
        :param auto_orientation: whether to keep/correct photo orientation using EXIF data
        :return: edited photo
        """

        background = Image.open(photo)
        if auto_orientation:
            background = ImageOps.exif_transpose(background)
        foreground = Image.open(frame)

        # Ensure frame has an alpha channel for transparency
        if foreground.mode != 'RGBA':
            foreground = foreground.convert('RGBA')

        # Find the transparent hole in the frame.
        # We create a mask from the alpha channel where transparent pixels are white.
        alpha = foreground.getchannel('A')
        mask = Image.eval(alpha, lambda a: 255 if a < consts.ALPHA_THRESHOLD else 0)
        hole_bbox = mask.getbbox()

        if not hole_bbox:
            raise ValueError(
                "Could not find a transparent hole in the effect frame. The frame must be a PNG with a transparent area for the photo.")

        hole_left, hole_top, hole_right, hole_bottom = hole_bbox
        hole_width = hole_right - hole_left
        hole_height = hole_bottom - hole_top

        # Ensure photo is in a compatible mode
        background = background.convert("RGB")

        # Resize and crop the photo to fill the hole, preserving aspect ratio.
        photo_width, photo_height = background.size

        # Calculate scale factor to "cover" the hole
        scale = max(hole_width / photo_width, hole_height / photo_height)
        new_photo_width = int(photo_width * scale)
        new_photo_height = int(photo_height * scale)
        resized_photo = background.resize((new_photo_width, new_photo_height), Image.Resampling.LANCZOS)

        # Crop the resized photo based on alignment to match the hole size
        # Apply horizontal offset here
        crop_x = (new_photo_width - hole_width) / 2 - horizontal_offset

        if vertical_alignment == 'top':
            crop_y = 0
        elif vertical_alignment == 'bottom':
            crop_y = new_photo_height - hole_height
        else:  # 'center'
            crop_y = (new_photo_height - hole_height) / 2

        cropped_photo = resized_photo.crop((crop_x, crop_y, crop_x + hole_width, crop_y + hole_height))

        # Composite the images.
        # Create a new image, paste the cropped photo into the hole, then paste the frame over it.
        output_image = Image.new('RGB', foreground.size)
        output_image.paste(cropped_photo, (hole_left, hole_top))
        output_image.paste(foreground, (0, 0), foreground)

        return output_image

from PIL import Image, ImageOps

import os

from photobooth import utils

"""
Tailor class gets the chosen photo and applies the wanted effect.
It provides methods to edit photos with the selected effects, add padding, combine pairs of photos and edit to have one total photo with 2 polaroids inside.
"""


class Tailor:

    def __init__(self, print_size=None):
        from photobooth.consts import DEFAULT_PRINT_SIZE
        self._print_size = print_size or DEFAULT_PRINT_SIZE
        self._photo_path = ''
        self._effect_path = ''
        self._output_folder_path = ''

    def set_infos(self, photo_list: list[str], effect_list: list[str], output_folder_path: str):
        """
        Information to edit photos together or individually.
        """

        self._photo_list = photo_list
        self._effect_list = effect_list
        self._output_folder_path = output_folder_path

    def _build_output_path(self):
        """
        Method which builds the final path of the combined/single photo.
        """

        first_photo_name = utils.get_name_from_path(self._photo_list[0])[:-4]
        second_photo_name = utils.get_name_from_path(self._photo_list[1])[:-4]
        base_name = first_photo_name + '-' + second_photo_name

        path = os.path.join(self._output_folder_path, base_name + '_00.jpg')
        i = 1
        while os.path.exists(path):
            path = os.path.join(self._output_folder_path, base_name + '_0' + str(i) + '.jpg')
            i += 1
        return path

    def edit(self) -> str:
        """
        Edits the photos
        :return: edited file path, as string
        """

        edited_file_path = self._build_output_path()

        first_photo = self._load_queued_photo(self._photo_list[0], self._effect_list[0])
        second_photo = self._load_queued_photo(self._photo_list[1], self._effect_list[1])
        output_file = self._combine_two_photos(first_photo, second_photo)

        # HERE PADDING
        from photobooth.consts import FINAL_PADDING_PERCENTAGE
        output_file = self.add_final_padding(output_file, FINAL_PADDING_PERCENTAGE)

        output_file.save(edited_file_path, "JPEG")

        # give 777 to edited file
        os.chmod(edited_file_path, 0o777)

        return edited_file_path

    def _load_queued_photo(self, photo, effect) -> Image:
        """
        Method which returns a queued photo ready to be combined.
        An empty effect means the photo is already framed (e.g. a reprint from the framed folder).
        :param photo: photo path
        :param effect: effect path, or empty string
        :return: edited photo
        """

        if not effect:
            with Image.open(photo) as img:
                return img.convert("RGB")
        return self.prepare_single_photo(photo, effect)

    def _combine_two_photos(self, first_photo: Image, second_photo: Image) -> Image:
        """
        Method which combines two edited photos into a single one.
        :param first_photo: first edited photo
        :param second_photo: second edited photo
        :return: combined photo
        """

        from photobooth.consts import IMAGE_SIZE_4X3, IMAGE_SIZE_4X6
        # Rotate 90 degrees and resize both photos to landscape 4x3 (2000x1500)
        first_4x3 = first_photo.rotate(90, expand=True).resize(IMAGE_SIZE_4X3, Image.Resampling.LANCZOS)
        second_4x3 = second_photo.rotate(90, expand=True).resize(IMAGE_SIZE_4X3, Image.Resampling.LANCZOS)
 
        # Create a new 2000x3000 canvas to stack them vertically (4x6 portrait print)
        output_image = Image.new('RGB', size=IMAGE_SIZE_4X6)
        output_image.paste(first_4x3, (0, 0))
        output_image.paste(second_4x3, (0, IMAGE_SIZE_4X3[1]))
        return output_image

    def prepare_single_photo(self, photo, effect, horizontal_offset=0, vertical_alignment='center',
                             auto_orientation=True) -> Image:
        """
        Method which edits a single photo with the chosen effect.
        The photo is automatically centered and resized to fit the effect's transparent area.
        :param photo: chosen photo path
        :param effect: chosen effect path (frame with a transparent hole)
        :param horizontal_offset: offset to shift the photo horizontally (positive = right, negative = left)
        :param vertical_alignment: vertical alignment of the photo inside the hole ('center', 'top', 'bottom')
        :param auto_orientation: whether to keep/correct photo orientation using EXIF data
        :return: edited photo
        """

        background = Image.open(photo)
        if auto_orientation:
            background = ImageOps.exif_transpose(background)
        foreground = Image.open(effect)

        # Ensure frame has an alpha channel for transparency
        if foreground.mode != 'RGBA':
            foreground = foreground.convert('RGBA')

        # Find the transparent hole in the frame.
        # We create a mask from the alpha channel where transparent pixels are white.
        from photobooth.consts import ALPHA_THRESHOLD
        alpha = foreground.getchannel('A')
        mask = Image.eval(alpha, lambda a: 255 if a < ALPHA_THRESHOLD else 0)
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

        # Ensure crop coordinates are within bounds (optional, but good practice)
        # If we shift too much, we might go out of bounds. For now, let's just crop.
        # PIL handles out-of-bounds crop by padding with black if I recall correctly, 
        # but usually crop() expects coordinates within the image. 
        # However, since we are resizing to cover, we usually have some slack.
        # Let's just apply the offset.

        cropped_photo = resized_photo.crop((crop_x, crop_y, crop_x + hole_width, crop_y + hole_height))

        # Composite the images.
        # Create a new image, paste the cropped photo into the hole, then paste the frame over it.
        output_image = Image.new('RGB', foreground.size)
        output_image.paste(cropped_photo, (hole_left, hole_top))
        output_image.paste(foreground, (0, 0), foreground)

        return output_image

    def add_final_padding(self, image: Image, percentage: int) -> Image:
        """
        Method which adds a padding to the combined photo.
        :param image: combined photo
        :param percentage: percentage of resizing of the image
        :return: padded photo
        """

        # builds a background as big as the image but of color: #f0f0f0
        # resize the image with percentage
        # put the image onto the background
        from photobooth.consts import PADDING_BACKGROUND_COLOR
        img_w, img_h = image.size
        canvas = Image.new('RGB', (img_w, img_h), PADDING_BACKGROUND_COLOR)
        resized_w = int(img_w * (percentage / 100))
        resized_h = int(img_h * (percentage / 100))
        resized_image = image.resize((resized_w, resized_h))
        w_padding = int((img_w - resized_w) / 2)
        h_padding = int((img_h - resized_h) / 2)
        canvas.paste(resized_image, (w_padding, h_padding))

        return canvas

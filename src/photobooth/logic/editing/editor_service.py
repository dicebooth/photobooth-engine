import os

from PIL import Image, ImageOps

from photobooth import consts


class EditorService:
    """
    EditorService gets the chosen photo and applies the wanted effect.
    It provides methods to edit photos with the selected effects, add padding,
    combine pairs of photos and edit to have one total photo with 2 polaroids inside.

    The service is stateless: every edit receives its inputs directly.
    """

    def _build_output_path(self, photo_list: list[str], output_folder_path: str):
        """
        Method which builds the final path of the combined/single photo.
        """

        first_photo_name = os.path.splitext(os.path.basename(photo_list[0]))[0]
        second_photo_name = os.path.splitext(os.path.basename(photo_list[1]))[0]
        base_name = first_photo_name + '-' + second_photo_name

        path = os.path.join(output_folder_path, base_name + '_00.jpg')
        i = 1
        while os.path.exists(path):
            path = os.path.join(output_folder_path, base_name + '_0' + str(i) + '.jpg')
            i += 1
        return path

    def edit(self, photo_list: list[str], effect_list: list[str], output_folder_path: str) -> str:
        """
        Edits the photos
        :param photo_list: paths of the two photos to combine
        :param effect_list: path of the effect (frame) for each photo
        :param output_folder_path: folder where the edited file is saved
        :return: edited file path, as string
        """

        edited_file_path = self._build_output_path(photo_list, output_folder_path)

        first_photo = self.prepare_single_photo(photo_list[0], effect_list[0])
        second_photo = self.prepare_single_photo(photo_list[1], effect_list[1])
        output_file = self._combine_two_photos(first_photo, second_photo)

        # HERE PADDING
        output_file = self.add_final_padding(output_file, consts.FINAL_PADDING_PERCENTAGE)

        output_file.save(edited_file_path, "JPEG")

        # give 777 to edited file
        os.chmod(edited_file_path, 0o777)

        return edited_file_path

    def _combine_two_photos(self, first_photo: Image, second_photo: Image) -> Image:
        """
        Method which combines two edited photos into a single one.
        :param first_photo: first edited photo
        :param second_photo: second edited photo
        :return: combined photo
        """

        # Rotate 90 degrees and resize both photos to landscape 4x3 (2000x1500)
        first_4x3 = first_photo.rotate(90, expand=True).resize(consts.IMAGE_SIZE_4X3, Image.Resampling.LANCZOS)
        second_4x3 = second_photo.rotate(90, expand=True).resize(consts.IMAGE_SIZE_4X3, Image.Resampling.LANCZOS)

        # Create a new 2000x3000 canvas to stack them vertically (4x6 portrait print)
        output_image = Image.new('RGB', size=consts.IMAGE_SIZE_4X6)
        output_image.paste(first_4x3, (0, 0))
        output_image.paste(second_4x3, (0, consts.IMAGE_SIZE_4X3[1]))
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
        img_w, img_h = image.size
        canvas = Image.new('RGB', (img_w, img_h), consts.PADDING_BACKGROUND_COLOR)
        resized_w = int(img_w * (percentage / 100))
        resized_h = int(img_h * (percentage / 100))
        resized_image = image.resize((resized_w, resized_h))
        w_padding = int((img_w - resized_w) / 2)
        h_padding = int((img_h - resized_h) / 2)
        canvas.paste(resized_image, (w_padding, h_padding))

        return canvas
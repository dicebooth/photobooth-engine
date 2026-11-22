import os

from PIL import Image

from photobooth import consts
from photobooth.logic.frames.frame_compositor import FrameCompositor


class EditorService:
    """
    EditorService builds the printable sheet: it frames two photos, combines
    them into one 4x6 photo with 2 polaroids inside and adds the final padding.

    The service is stateless: every edit receives its inputs directly.
    """

    def __init__(self, compositor: FrameCompositor):
        self._compositor = compositor

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

        first_photo = self._compositor.compose(photo_list[0], effect_list[0])
        second_photo = self._compositor.compose(photo_list[1], effect_list[1])
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
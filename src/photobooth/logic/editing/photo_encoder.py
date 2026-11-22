import base64
import io

from PIL import Image


class PhotoEncoder:
    """
    PhotoEncoder turns a PIL image into the PNG base64 string the backend expects.
    """

    # modes PNG can store without losing information
    _PNG_MODES = ("RGB", "RGBA", "L", "LA")

    def to_png_base64(self, img: Image.Image) -> str:
        """
        Method which encodes an image as PNG base64.
        Images in an exotic mode (e.g. CMYK, P) are converted to RGBA first.
        The given image is never modified.
        :param img: image to encode
        :return: ASCII base64 of the PNG
        """

        if img.mode not in self._PNG_MODES:
            img = img.convert("RGBA")

        img.load()
        img = img.copy()

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")

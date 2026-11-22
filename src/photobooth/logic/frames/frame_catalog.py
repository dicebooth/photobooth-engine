import os


class FrameCatalog:
    """
    FrameCatalog knows which frames (PNG overlays) are available in the Assets folder.
    It provides the names of the available frames, tells if there is only one
    and resolves a frame name to its path.
    """

    def __init__(self, frames_path: str):
        self._frames_path = frames_path

    def names(self) -> list:
        """
        Method which returns the names of the available frames, without extension.
        Only PNG files count: OS metadata files (.DS_Store, Thumbs.db) are not frames.
        :return: frame names list
        """

        return [filename.replace(".png", "")
                for filename in sorted(os.listdir(self._frames_path))
                if filename.endswith(".png")]

    def is_single(self) -> bool:
        """
        Method which checks if the frames folder contains only one frame.
        :return: True if only one frame is present, False otherwise
        """

        return len(self.names()) == 1

    def path_of(self, frame_name: str) -> str:
        """
        Method which returns the frame path starting from its name.
        :param frame_name: frame name (with or without .png extension)
        :return: frame path
        """

        if not frame_name.endswith('.png'):
            frame_name += '.png'
        return os.path.join(self._frames_path, frame_name)

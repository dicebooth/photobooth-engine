import os
import shutil


class FolderManager:
    """
    FolderManager manages the folders where photos are stored.
    It ensures the consistency of the folders and provides methods to get the paths of the sub-folders.

    FOLDERS EXPLANATION

       user_data
          |___________> current       [ here the current shots: in future the user would choose from different shots]
          |___________> originals     [ all the originals chosen shots                                              ]
          |___________> output        [ all the outputs: cropped and cornered                                       ]
    """

    def __init__(self, main_folder_path: str):
        self._main_folder_path = main_folder_path
        # now the paths of all the sub-folders
        user_data_path = os.path.join(main_folder_path, 'user_data')
        self._current_folder_path = os.path.join(user_data_path, 'current')
        self._originals_folder_path = os.path.join(user_data_path, 'originals')
        self._output_folder_path = os.path.join(user_data_path, 'output')

        # then we check the folders consistency
        self._folder_consistency_assurance()

    def _folder_consistency_assurance(self):
        """
        Method which checks if the main folder and the sub-folders exist.
        If not, they will be created.
        """

        # if the sub-folders are missing, they will be created
        user_data_path = os.path.join(self._main_folder_path, 'user_data')
        folder_list = [self._main_folder_path, user_data_path, self._current_folder_path,
                       self._originals_folder_path, self._output_folder_path]
        for folder in folder_list:
            if not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)
                os.chmod(folder, 0o777)

    def get_current_path(self) -> str:
        """
        Method which returns the current folder path.
        :return: current folder path"""

        return self._current_folder_path

    def get_originals_path(self) -> str:
        """
        Method which returns the originals folder path.
        :return: originals folder path"""

        return self._originals_folder_path

    def get_output_folder_path(self) -> str:
        """
        Method which returns the output folder path.
        :return: output folder path"""

        return self._output_folder_path

    def clean_current_path(self, chosen_photo_path: str) -> str:
        """
        Move all files from the current folder to the originals folder but save the new path of the chosen shot
        :param chosen_photo_path: old path of the photo which we will hold
        :return: pointed photo new path
        """

        new_photo_path = ''

        for filename in os.listdir(self._current_folder_path):

            original_file_complete_path = os.path.join(self._current_folder_path, filename)
            destination_path = os.path.join(self._originals_folder_path, filename)
            shutil.move(original_file_complete_path, destination_path)

            if original_file_complete_path == chosen_photo_path:
                new_photo_path = destination_path

        return new_photo_path


class AssetManager:
    """
    AssetManager manages the assets used in the photobooth, such as corners.
    It provides methods to get the names of the available corners and to check if there is only one available.
    """

    def __init__(self, assets_path: str):
        self._assets_path = assets_path

    def is_frame_single(self) -> bool:
        """
        Method which checks if the assets folder contains only one effect.
        :return: True if only one effect is present, False otherwise
        """

        # check if the assets folder contains only one frame
        # if so, then we can skip the user choice
        return len(os.listdir(self._assets_path)) == 1

    def get_corners_names(self) -> list:
        """
        Method which returns the names of the available corners in the assets folder.
        :return: corner names list
        """

        # get the names of the corners
        corner_list = []
        for filename in sorted(os.listdir(self._assets_path)):
            if filename.endswith(".png"):
                corner_list.append(filename.replace(".png", ""))
        return corner_list

    def get_frame_path(self, frame_name: str) -> str:
        """
        Method which returns the frame path starting from its name.
        :param frame_name: frame name (with or without .png extension)
        :return: frame path
        """

        if not frame_name.endswith('.png'):
            frame_name += '.png'
        return os.path.join(self._assets_path, frame_name)
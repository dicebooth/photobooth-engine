import os
import shutil
import yaml

from photobooth.settings_manager import Settings
from photobooth import utils

# FOLDERS EXPLANATION
#
#    user_data
#       |___________> current       [ here the current shots: in future the user would choose from different shots]
#       |___________> originals     [ all the originals chosen shots                                              ]
#       |___________> output        [ all the outputs: cropped and cornered                                       ]
#


"""
FolderManager class manages the folders where photos are stored.
It ensures the consistency of the folders and provides methods to get the paths of the sub-folders.
"""


class FolderManager:

    def __init__(self, main_folder_path: str):
        self._main_folder_path = main_folder_path
        # now the paths of all the sub-folders
        user_data_path = os.path.join(main_folder_path, 'user_data')
        self._current_folder_path = os.path.join(user_data_path, 'current')
        self._originals_folder_path = os.path.join(user_data_path, 'originals')
        self._output_folder_path = os.path.join(user_data_path, 'output')
        self._framed_photos_folder_path = os.path.join(user_data_path, 'framed')

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
                       self._originals_folder_path, self._output_folder_path, self._framed_photos_folder_path]
        for folder in folder_list:
            if not os.path.exists(folder):
                os.makedirs(folder)
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

    def get_framed_photos_path(self) -> str:
        """
        Method which returns the framed photos folder path.
        :return: framed photos folder path"""

        return self._framed_photos_folder_path


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


"""
FileNaming class manages the photo naming convention.
It provides methods to get the photo name according to the convention and to increment the session number.
"""


class FileNaming:

    def __init__(self):
        from photobooth.consts import TEMP_DATA_PATH
        self._temp_data_path = TEMP_DATA_PATH
        self._settings = Settings()
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(self._temp_data_path):
            with open(self._temp_data_path, 'w') as f:
                yaml.dump({'photos': [], 'edits': [], 'session': '0000'}, f, default_flow_style=False,
                          allow_unicode=True)

    def get_photo_name(self) -> str:
        """
        Method which returns the photo name according to the naming convention.
        Photo number in the current folder is considered.
        :return: photo name
        """

        with open(self._temp_data_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)

        session_number = yaml_dict["session"]

        folder = FolderManager(self._settings.get_main_folder_path())
        photo_number = utils.get_string_from_photo_number(len(os.listdir(folder.get_current_path())) + 1)

        return f"{self._settings.get_event_name()}_{utils.get_string_from_session_number(int(session_number) + 1)}_{photo_number}.jpg"

    def increment_session_number(self):
        """
        Method which increments the session number in the temp_data.yaml file.
        Then it updates the yaml file.
        :return: new session number
        """

        with open(self._temp_data_path, 'r') as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)

        yaml_dict["session"] = utils.get_string_from_session_number(int(yaml_dict["session"]) + 1)

        with open(self._temp_data_path, 'w') as f:
            yaml.dump(yaml_dict, f, default_flow_style=False, allow_unicode=True)

        return yaml_dict["session"]


"""
AssetManager class manages the assets used in the photobooth, such as corners.
It provides methods to get the names of the available corners and to check if there is only one available.
"""


class AssetManager:

    def __init__(self):
        self.assets_path = str(os.path.join(os.getcwd(), "Assets"))

    def is_frame_single(self) -> bool:
        """
        Method which checks if the assets folder contains only one effect.
        :return: True if only one effect is present, False otherwise
        """

        # check if the assets folder contains only one frame
        # if so, then we can skip the user choice
        if len(os.listdir(self.assets_path)) == 1:
            return True
        else:
            return False

    def get_corners_names(self) -> list:
        """
        Method which returns the names of the available corners in the assets folder.
        :return: corner names list
        """

        # get the names of the corners
        corner_list = []
        for filename in os.listdir(self.assets_path):
            if filename.endswith(".png"):
                filename = filename.replace(".png", "")
                corner_list.append(filename)
        return corner_list

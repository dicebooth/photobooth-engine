import os


class FolderManager:
    """
    FolderManager knows where the photos are stored.
    It ensures the consistency of the folders and provides the paths of the sub-folders.

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

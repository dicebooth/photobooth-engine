from photobooth import utils
from photobooth.core.folder_manager import FolderManager, AssetManager
from photobooth.core.photo_edit_manager import Tailor
from photobooth.settings_manager import Settings
from photobooth.user_interaction import UserInterface


class FrameChooser():

    def __init__(self, ui_adapter=None) -> None:
        self._settings = Settings()
        self._folders = FolderManager(self._settings.get_main_folder_path())
        self._assets = AssetManager()
        self._frame_list = self._assets.get_corners_names()
        if ui_adapter is not None:
            self._ui = ui_adapter
        else:
            self._ui = UserInterface(self._frame_list)
        self._editor = Tailor()

        # 
        self._SINGLE_FRAME = False
        self._RANDOM_FRAME = True
        self._random_frame_index = 0

    def choose_frame(self, photo_path):
        # effect_name = self._ui.choose_polaroid_effect()
        # effect_path = utils.get_asset_path_from_name(effect_name)
        configured_frame = self._settings.get_frame_name()
        if configured_frame:
            effect_name = configured_frame
            if not effect_name.endswith('.png'):
                effect_name += '.png'
            effect_path = utils.get_asset_path_from_name(effect_name)
            if not self._settings.get_preview_post_frame() or self._ui.show_preview_image(self._editor.prepare_single_photo(photo_path, effect_path)):
                return [effect_path, True]
            else:
                return ['', False]

        if self._SINGLE_FRAME:
            [effect_path, accepted] = self.show_single_edit(photo_path)
        elif self._RANDOM_FRAME:
            [effect_path, accepted] = self.show_random_edit(photo_path)
        else:
            [effect_path, accepted] = self.choice_edit_with_preview(photo_path)

        return [effect_path, accepted]

    def show_random_edit(self, photo_path):

        # TRUE RANDOM
        # frames = self._assets.get_corners_names()
        # random_frame = random.choice(frames)

        # CONSECUTIVE R
        random_frame = self._frame_list[self._random_frame_index]
        self._random_frame_index = (self._random_frame_index + 1) % len(self._frame_list)

        effect_name = random_frame + ".png"
        effect_path = utils.get_asset_path_from_name(effect_name)
        # ugly application to get faster
        # self._ui.show_preview_without_response(self._editor.prepare_single_photo(photo_path,effect_path))
        if not self._settings.get_preview_post_frame() or self._ui.show_preview_image(self._editor.prepare_single_photo(photo_path, effect_path)):
            return [effect_path, True]
        else:
            return ['', False]

    def show_single_edit(self, photo_path):
        """
        Method which shows the preview of the edited photo with the single effect and returns the effect path if accepted or False if not.
        :param photo_path: photo path to edit
        :return: effect path or False
        """

        effect_name = self._assets.get_corners_names()[0] + ".png"
        effect_path = utils.get_asset_path_from_name(effect_name)
        # ugly application to get faster
        # self._ui.show_preview_without_response(self._editor.prepare_single_photo(photo_path,effect_path))
        if not self._settings.get_preview_post_frame() or self._ui.show_preview_image(self._editor.prepare_single_photo(photo_path, effect_path)):
            return [effect_path, True]
        else:
            return ['', False]

    def choice_edit_with_preview(self, photo_path):
        """
        Method which allows the user to choose the effect to apply to the shot photo with a preview.
        Returns the effect path when the edited photo is accepted.
        :param photo_path: photo path to edit
        :return: effect path
        """
        # in this case the photo was already accepted in the runner method, so only the edit will be chosen
        # in other words: here the logic to change the photo is not implemented
        while True:
            effect_name = self._ui.choose_polaroid_effect()
            effect_path = utils.get_asset_path_from_name(effect_name)
            if not self._settings.get_preview_post_frame() or self._ui.show_preview_image(self._editor.prepare_single_photo(photo_path, effect_path)):
                return [effect_path, True]

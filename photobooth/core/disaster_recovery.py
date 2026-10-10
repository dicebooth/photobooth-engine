from photobooth.core.folder_manager import FolderManager, AssetManager
from photobooth.settings_manager import Settings
from photobooth.user_interaction import UserInterface
import os


def resume_old_session(current_path, ui_adapter=None):
    """
    This method implements disaster recovery procedure.
    If in the current folder there are some photos, the user is asked if they want to resume the old session.
    If yes, the photos in the current folder are returned.
    If no, the current folder is cleaned.
    When the framed preview is enabled no question is asked here: the photo is returned and its framed preview
    is approved (or discarded, cleaning the current folder) in the normal flow.
    :param current_path: the path of the current folder
    :param ui_adapter: user interface adapter
    :return: the list of the photos in the current folder if the user wants to resume the old session, False otherwise
    """

    if len(os.listdir(current_path)) != 0:
        if ui_adapter is not None:
            ui = ui_adapter
        else:
            assets = AssetManager()
            ui = UserInterface(assets.get_corners_names())

        photos_list = [f for f in os.listdir(current_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if not photos_list:
            return False

        photo_to_recover = os.path.join(current_path, photos_list[0])
        from photobooth.utils import detect_os, get_asset_path_from_name
        from photobooth.core.photo_edit_manager import Tailor

        settings = Settings()
        if settings.get_preview_post_frame():
            # the framed preview shown right after by the frame chooser is the approval of the recovered photo:
            # asking here too would make the user approve the same photo twice
            return photo_to_recover

        # Ask user if they want to recover the photo found in session
        frame_name = settings.get_frame_name() or "cometocode-2026.png"
        if not frame_name.endswith('.png'):
            frame_name += '.png'
        frame_path = get_asset_path_from_name(frame_name)

        try:
            editor = Tailor()
            framed_img = editor.prepare_single_photo(photo_to_recover, frame_path)
            accepted = ui.show_preview_image(framed_img)
        except Exception as e:
            print(f"Error applying frame for preview: {e}")
            accepted = ui.confirm_shot(photo_to_recover, detect_os())

        if accepted:
            return photo_to_recover
        else:
            folder = FolderManager(settings.get_main_folder_path())
            folder.clean_current_path('')
            return False


    return False


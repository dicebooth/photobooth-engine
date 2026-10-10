from photobooth.core.folder_manager import FolderManager, FileNaming, AssetManager
from photobooth.core.camera_manager import PhotoManager
from photobooth.core.disaster_recovery import resume_old_session
from photobooth.core.photo_edit_manager import Tailor
from photobooth.core.queue_manager import QueueManager
from photobooth.settings_manager import Settings
from photobooth.user_interaction import UserInterface
from photobooth.core.printer_manager import Printer
from photobooth.core.frame_chooser import FrameChooser
from photobooth.backend.backend_manager import BackendManager
from photobooth.backend.logger import setup_logging

import os
import shutil
import threading
from photobooth import utils

"""
Runner is the principal class that coordinates all the components of the application.
Here all the managers are instantiated and the main execution loop is implemented.
It provides methods to manage the life cycle of camera, editing and printing.
"""


class Runner:

    def __init__(self, gui_adapter=None):
        """
        Constructor method.
        """

        self._settings = Settings()
        self._print_size = self._settings.get_print_size()
        self._folders = FolderManager(self._settings.get_main_folder_path())
        self._camera = PhotoManager()
        self._editor = Tailor(self._print_size)
        self._queue = QueueManager(self._print_size)
        self._continue = True
        self._file_naming = FileNaming()
        self._assets = AssetManager()
        if gui_adapter is not None:
            self._ui = gui_adapter
        else:
            self._ui = UserInterface(self._assets.get_corners_names())
        self._frame_chooser = FrameChooser(ui_adapter=self._ui)


        # if in asset only one corner is present,
        # there is no need to ask the user every time which one apply
        self._SINGLE_FRAME = False
        self._printer = Printer(self._settings.get_printer_name(), self._settings.get_printer_options(),
                                print_size=self._print_size, mock=self._settings.get_mock_printer(),
                                enable_hotfolder=self._settings.get_enable_hotfolder(),
                                hotfolder_path=self._settings.get_printer_hotfolder_path())
        self._backend = BackendManager(self._settings.get_backend_url(), self._settings.get_client_secret())
        # the print queue is shared between the main loop and reprints requested by the web portal
        self._print_lock = threading.Lock()

    def prepare(self):
        """
        Method which allows to prepare camera, initialize printing and editing queue and prepare the printer.
        """

        self._camera.init_camera()
        self._queue.load_queue()
        self._printer.prepare()
        # if not self._settings.verify_logs_existence():
        #     self._settings.create_logs_file()

        # now check how many corners are present in the assets
        self._SINGLE_FRAME = self._assets.is_frame_single()

        # initialize logger file
        setup_logging()

    def main_execution(self):
        """
        Method where disaster recovery is applied if something strange happened in the last session, allowing to resume it.
        If there are many effects in the Assets folder, the user is allowed to choose which one to apply.
        Then the edited photo is shown to the user for confirmation.
        Then the user is asked how many copies of the photo he wants to print: the user interface may return None
        to go back and review the framed photo again.
        At the end if there are 2 or more photos in the printing queue the printing process starts.
        """

        disaster_has_happened = resume_old_session(self._folders.get_current_path(), self._ui)
        photo_path = ''
        if isinstance(disaster_has_happened, str):
            photo_path = disaster_has_happened
        else:
            [photo_path, _] = self.choice_photo_with_preview()

        [effect_path, photo_accepted] = self._frame_chooser.choose_frame(photo_path)
        times = None
        while photo_accepted:
            times = self._ui.choose_times_to_print()
            if times is not None:
                break
            # the user went back from the copies selection: show the same framed photo again
            photo_accepted = self._frame_chooser.confirm_frame(photo_path, effect_path)

        if not photo_accepted:
            self._folders.clean_current_path(photo_path)
            return

        # framed photo and upload happen only once the copies are confirmed, so going back leaves no trace
        # Save single framed photo to user_data/framed folder
        try:
            framed_img = self._editor.prepare_single_photo(photo_path, effect_path)
            framed_folder = self._folders.get_framed_photos_path()
            framed_file_name = os.path.basename(photo_path)
            framed_save_path = os.path.join(framed_folder, framed_file_name)
            framed_img.save(framed_save_path)
            os.chmod(framed_save_path, 0o777)
        except Exception as e:
            print(f"Error saving single framed photo: {e}")


        # ----   send to the server  ----
        self._backend.send_photo_and_edit(photo_path, effect_path)

        # -------------------------------

        # the photo is added to the queue and the folder get cleared
        self._enqueue_and_print(self._folders.clean_current_path(photo_path), effect_path, times)

    def reprint(self, photo_name: str, times: int) -> int:
        """
        Method which prints again a photo of the framed folder, as it is (frame already applied).
        Thread-safe: it is called by the web portal while the main loop may be waiting for a shot.
        :param photo_name: file name of the photo in the framed folder
        :param times: number of copies
        :return: number of photos still waiting in the queue (prints are made in pairs)
        """

        photo_path = os.path.join(self._folders.get_framed_photos_path(), os.path.basename(photo_name))
        if not os.path.isfile(photo_path):
            raise FileNotFoundError(photo_path)

        # an empty effect tells the editor that the photo is already framed
        return self._enqueue_and_print(photo_path, '', times)

    def _enqueue_and_print(self, photo_path: str, effect_path: str, times: int) -> int:
        """
        Method which adds a photo to the print queue and prints every ready pair.
        :return: number of photos still waiting in the queue
        """

        with self._print_lock:
            self._queue.add_photo(photo_path, times)
            self._queue.add_edit(effect_path, times)

            while self._queue.queue_is_ready():  # if there are 2 or more photos in queue then start to edit
                path_to_print = self.edit()  # actually there is no more the need to declare here this paths
                self._printer.print_image(path_to_print)

            return self._queue.pending_count()

    def choice_photo_with_preview(self):
        """
        Method which allows the user to take a photo.
        :return: shot photo path
        """

        # shooted_photos_number = self._settings.get_shooted_photos_number()
        # counter = 1

        while True:
            file_name = self._file_naming.get_photo_name()
            if self._settings.get_capture_mode() == 'camera':
                photo_path = self._camera.get_shoot_from_camera(self._folders.get_current_path(), file_name, self._ui)
            else:
                photo_path = self._camera.get_shoot_from_pc(self._folders.get_current_path(), file_name, self._ui)
            # photo_path = self._camera.get_fake_shoot(self._folders.get_current_path(),self._file_naming.get_photo_name() ,self._ui)

            # photo_path, photo_name = utils.get_the_file_in_dir(self._folders.get_current_path())
            # ATTENTION
            # up to now to make the pipeline faster, the user will not confirm the shoot here but only after the polaroid edit
            # in the future, granularity will be added
            if not self._settings.get_preview_pre_frame() or self._ui.confirm_shot(photo_path, utils.detect_os()):
                # the photo is accepted, we can go on
                # session has ended
                self._file_naming.increment_session_number()
                # self._settings.update_logs(counter, 's')
                return [photo_path, '']
            else:
                # counter += 1
                shutil.move(os.path.join(self._folders.get_current_path(), file_name),
                            os.path.join(self._folders.get_originals_path(), file_name))
                print('Photo rejected, retrying...')

    def edit(self):
        """
        Method which gets photos and their effects from the queues and sends to the editor manager to edit them.
        :return: edited photo path
        """
        photo_list = self._queue.get_photos()
        edit_list = self._queue.get_edits()
        self._editor.set_infos(photo_list, edit_list, self._folders.get_output_folder_path())
        joined_photo = self._editor.edit()
        print(joined_photo)
        return joined_photo

    def keep_going(self):
        # here in the future a more complex solution
        return self._continue

    def final_cleaning(self):
        self._camera.stop_camera()
        self._queue.dismiss()

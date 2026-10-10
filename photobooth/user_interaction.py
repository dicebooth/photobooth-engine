from PIL import Image
from photobooth.utils import Platform, detect_os
import os
import subprocess
from photobooth.settings_manager import Settings

"""
UserInterface class offers methods to manage user interaction through choices about photo goodness, effects to apply and so on.
"""


class UserInterface:

    def __init__(self, polaroid_effect_list: list):
        self.effect_list = polaroid_effect_list
        self._settings = Settings()

    def choose_polaroid_effect(self) -> str:
        """
        Method which shows a menu in order to allow the user to choose the wanted effect (if there are more than one in the asset folder).
        :return: effect path
        """

        print('Choose which effect to apply')

        while True:
            index = 1
            for effect_name in self.effect_list:
                print(f'[{index}]: {effect_name}')
                index = index + 1

            chosen_edit = input('pick a number: ')
            if chosen_edit.isdigit():
                chosen_edit = int(chosen_edit)
                if 0 < chosen_edit <= 10:
                    print('alright')
                    break

            print('Some error occurred, please try again')

        file_name = self.effect_list[chosen_edit - 1] + '.png'
        return file_name

    def confirm_shot(self, photo_path, os_platform: Platform) -> bool:
        """
        Method which shows the preview of the shot photo in order to allow the user to choose if it's good or not.
        :param photo_path: photo path
        :param os_platform: os where photobooth is running
        :return: True if the photo is good, False if not
        """

        if self._settings.get_terminal_preview():
            self._show_terminal_preview(photo_path)
        else:
            if os_platform.is_linux():
                # image = Image.open(photo_path)
                # image.show()
                subprocess.run(["xdg-open", photo_path])
            elif os_platform.is_wsl():
                windows_path = subprocess.check_output(['wslpath', '-w', photo_path]).decode().strip()
                subprocess.run(['powershell.exe', 'Start-Process', windows_path])
            elif os_platform.is_macos():
                # On macOS, the best way to open a file is using the 'open' command.
                # If running as root (via sudo), we try to open it in the context of the original user
                # to ensure it appears in their GUI session.
                abs_photo_path = os.path.abspath(photo_path)
                if os.geteuid() == 0:
                    try:
                        # SUDO_USER gives the name of the user who invoked sudo.
                        # os.getlogin() might return root or raise an error in non-TTY contexts.
                        user = os.environ.get('SUDO_USER') or os.getlogin()
                        subprocess.run(["sudo", "-u", user, "open", abs_photo_path])
                    except Exception:
                        # Graceful fallback: just try 'open' directly if user detection fails.
                        subprocess.run(["open", abs_photo_path])
                else:
                    subprocess.run(["open", abs_photo_path])

        while True:
            print('Do you like it? [y]/n')

            decision = input('choose: ')

            decision_clean = decision.strip().lower()
            if decision_clean in ('y', ''):
                return True
            elif decision_clean == 'n':
                return False

            print('Some error occurred, please try again')

    def choose_times_to_print(self):
        """
        Method which shows a menu in order to allow the user to insert the number of photos to print.
        :return: times number to print the photo, or None to go back to the photo approval
        """

        min_num = self._settings.get_min_num_photos()
        max_num = self._settings.get_max_num_photos()

        print('How many copies of the photo do you want to print?')
        while True:
            times = input(f'choose between {min_num} up to {max_num} (b to go back): ')
            if times.strip().lower() == 'b':
                return None
            if times.isdigit():
                times = int(times)
                if min_num <= times <= max_num:
                    warn_limit = self._settings.get_warn_num_photos()
                    while True:
                        if times >= warn_limit:
                            print(f'WARNING: You selected a high number of copies ({times} copies).')
                            print('you choose ' + str(times) + ' copies, is it correct?')
                            ui_input = input('[y]/n: ')
                            ui_input_clean = ui_input.strip().lower()
                            if ui_input_clean == 'n':
                                break
                        else:
                            print('all right')
                            return times
            print('Some error occurred, please try again')

    def wait_for_camera_shutter(self):
        """
        Method which notifies the user to press the shutter button on the camera.
        """
        print('Ready! Press the shutter button on the camera to take the photo.')

    def press_to_shoot(self):
        """
        Method which allows the user to press a key on the keyboard in order to take a photo.
        """

        input('press any key to shoot')

    def notify_shot_taken(self):
        """
        Method which prints a message to notify the user that a shot happened.
        """

    def show_preview_image(self, preview_img: Image) -> bool:
        """
        Method which shows the preview of the shot photo in order to allow the user to choose if it's good or not.
        :param photo_path: photo path
        :param os_platform: os where photobooth is running
        :return: True if the photo is good, False if not
        """

        print('here the edit')
        self._show_image(preview_img)
        print('do you like it?')
        while True:
            choiche = input('[y]/n: ')
            choiche_clean = choiche.strip().lower()
            if choiche_clean in ('y', ''):
                return True
            elif choiche_clean == 'n':
                return False
            else:
                print('some error occurred')

    def visualize_current_photos(self, path):
        """
        Method used in case of disaster recovery procedure execution.
        Shows a menu in order to allow the user to choose the photo they want to recover.
        :param path: current folder path
        """

        photos_list = os.listdir(path)
        import re
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

        photos_list.sort(key=natural_sort_key)

        # subprocess.run(["nautilus", path]) #TODO make it cross platform

        while True:
            for i in range(0, len(photos_list)):
                print(f"{i + 1}. Visualize {photos_list[i]}")
            choice = int(input("Enter your choice: "))
            if 1 <= choice <= (len(photos_list)):
                op_sys = detect_os()
                result = self.confirm_shot(os.path.join(path, photos_list[choice - 1]), op_sys)
                if result is True:
                    return os.path.join(path, photos_list[choice - 1])

            print("Please enter a valid choice")

    def _show_image(self, img: Image):
        """
        Helper method to show an image in a native viewer.
        On macOS, if running as root, it ensures the temporary file has correct permissions for the logged-in user.
        """
        if self._settings.get_terminal_preview():
            self._show_terminal_preview(img)
            return

        import tempfile
        os_platform = detect_os()

        if os_platform.is_macos() and os.geteuid() == 0:
            # On macOS as root, PIL .show() creates a file that the user GUI cannot read.
            # We manually save to a world-readable temp file and use native 'open'.
            fd, temp_path = tempfile.mkstemp(suffix='.png')
            os.close(fd)
            img.save(temp_path)
            os.chmod(temp_path, 0o777)

            user = os.environ.get('SUDO_USER') or os.getlogin()
            try:
                subprocess.run(["sudo", "-u", user, "open", temp_path])
            except Exception:
                subprocess.run(["open", temp_path])
        else:
            img.show()

    def _show_terminal_preview(self, image_or_path):
        """
        Shows a preview of the photo in the terminal directly using timg.
        """
        import timg
        import shutil

        try:
            obj = timg.Renderer()
            if isinstance(image_or_path, str):
                obj.load_image_from_file(image_or_path)
            elif isinstance(image_or_path, Image.Image):
                obj.load_image(image_or_path)
            else:
                raise ValueError("Unsupported image type")

            columns, lines = shutil.get_terminal_size()
            width, height = obj.image.size

            # Determine dimension bounds in terminal characters/cells (rows).
            # Columns are automatically calculated based on the photo's aspect ratio.
            # If terminal_preview_rows is 0 or not set, it falls back to auto-fitting current terminal size.
            custom_rows = self._settings.get_terminal_preview_rows()

            if custom_rows > 0:
                new_h = custom_rows
                new_w = int(new_h * (width / height))
            else:
                max_w = max(10, columns - 4)
                max_h = max(10, lines - 6)
                scale = min(max_w / width, max_h / height)
                new_w = int(width * scale)
                new_h = int(height * scale)

            obj.resize(new_w, new_h)
            obj.render(timg.Ansi24HblockMethod)
        except Exception as e:
            print(f"Error rendering terminal preview: {e}")

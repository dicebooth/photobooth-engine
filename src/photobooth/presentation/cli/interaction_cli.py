import os
import subprocess
import tempfile

from PIL import Image

from photobooth.api.platform_api import detect_os


class CliInteraction:
    """
    CliInteraction is the CLI implementation of the user interactions:
    it only handles prompts, choices and visualizations.

    It never talks to the core services directly: the session script
    (SessionCli) orchestrates the gateway and delegates here every prompt.
    """

    def __init__(self, settings):
        self._settings = settings

    # ------------------------------------------------------------------ choices

    def _ask_yes_no(self, prompt: str) -> bool:
        """
        Method which asks a yes/no question, re-asking until the answer is valid.
        Empty input and 'y' mean yes, 'n' means no.
        :param prompt: question to show
        :return: True for yes, False for no
        """

        while True:
            answer = input(prompt).strip().lower()
            if answer in ('y', ''):
                return True
            if answer == 'n':
                return False
            print('Some error occurred, please try again')

    def ask_resume_session(self) -> bool:
        """
        Method which asks the user if the interrupted session has to be resumed.
        :return: True if the session has to be resumed, False otherwise
        """

        print('maybe some error occurred in the last session')
        choice = input('do you want to resume it? [y]/n: ')
        return choice.strip().lower() in ('y', '')

    def choose_pending_photo(self, photo_paths: list) -> str:
        """
        Method used in case of disaster recovery procedure execution.
        Shows a menu in order to allow the user to choose the photo they want to recover.
        :param photo_paths: paths of the photos left by the interrupted session
        :return: chosen photo path
        """

        while True:
            for i in range(0, len(photo_paths)):
                print(f"{i + 1}. Visualize {os.path.basename(photo_paths[i])}")
            choice = input("Enter your choice: ")
            if choice.isdigit():
                choice = int(choice)
                if 1 <= choice <= len(photo_paths):
                    chosen_path = photo_paths[choice - 1]
                    if self.confirm_shot(chosen_path):
                        return chosen_path

            print("Please enter a valid choice")

    def confirm_shot(self, photo_path) -> bool:
        """
        Method which shows the preview of the shot photo in order to allow the user to choose if it's good or not.
        :param photo_path: photo path
        :return: True if the photo is good, False if not
        """

        if self._settings.get_terminal_preview():
            self._show_terminal_preview(photo_path)
        else:
            os_platform = detect_os()
            if os_platform.is_linux():
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

        return self._ask_yes_no('Do you like it? [y]/n: ')

    def choose_polaroid_effect(self, frame_list: list) -> str:
        """
        Method which shows a menu in order to allow the user to choose the wanted effect.
        :param frame_list: names of the available frames
        :return: chosen frame name
        """

        print('Choose which effect to apply')

        while True:
            index = 1
            for effect_name in frame_list:
                print(f'[{index}]: {effect_name}')
                index = index + 1

            chosen_edit = input('pick a number: ')
            if chosen_edit.isdigit():
                chosen_edit = int(chosen_edit)
                if 0 < chosen_edit <= len(frame_list):
                    print('alright')
                    break

            print('Some error occurred, please try again')

        return frame_list[chosen_edit - 1] + '.png'

    def choose_times_to_print(self) -> int:
        """
        Method which shows a menu in order to allow the user to insert the number of photos to print.
        :return: times number to print the photo
        """

        min_num = self._settings.get_min_num_photos()
        max_num = self._settings.get_max_num_photos()

        print('How many copies of the photo do you want to print?')
        while True:
            times = input(f'choose between {min_num} up to {max_num}: ')
            if times.isdigit():
                times = int(times)
                if min_num <= times <= max_num:
                    warn_limit = self._settings.get_warn_num_photos()
                    if times < warn_limit:
                        print('all right')
                        return times
                    print(f'WARNING: You selected a high number of copies ({times} copies).')
                    print('you choose ' + str(times) + ' copies, is it correct?')
                    if self._ask_yes_no('[y]/n: '):
                        return times
                    # 'n': fall through and re-ask the number of copies
            print('Some error occurred, please try again')

    # ------------------------------------------------------------------- hints

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
        Method which notifies the user that a shot happened.
        """

    def notify_photo_rejected(self):
        """
        Method which notifies the user that the photo has been rejected and the
        shot will be retried.
        """

        print('Photo rejected, retrying...')

    # ----------------------------------------------------------------- previews

    def show_preview_image(self, preview_img: Image) -> bool:
        """
        Method which shows the preview of the edited photo in order to allow the user to choose if it's good or not.
        :param preview_img: edited photo
        :return: True if the photo is good, False if not
        """

        print('here the edit')
        self._show_image(preview_img)
        print('do you like it?')
        return self._ask_yes_no('[y]/n: ')

    def _show_image(self, img: Image):
        """
        Helper method to show an image in a native viewer.
        On macOS, if running as root, it ensures the temporary file has correct permissions for the logged-in user.
        """
        if self._settings.get_terminal_preview():
            self._show_terminal_preview(img)
            return

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
        import shutil
        import timg

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
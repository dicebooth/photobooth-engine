import os

from photobooth.logic.printing.print_service import PrintResult
from photobooth.logic.session import disaster_recovery


class Gateway:
    """
    Gateway is the single entry point of the logic layer for the presentation layer.

    It exposes operations only: it never shows previews, never asks questions and
    never depends on the presentation layer. The CLI (and the future GUI) drives
    the photobooth session by orchestrating these calls and handling all the
    user interactions.
    """

    def __init__(self, settings, folders, archiver, catalog, capture, editor, printing, frame_chooser, backend):
        self._settings = settings
        self._folders = folders
        self._archiver = archiver
        self._catalog = catalog
        self._capture = capture
        self._editor = editor
        self._printing = printing
        self._frame_chooser = frame_chooser
        self._backend = backend
        self._continue = True

    # ---------------------------------------------------------------- lifecycle

    def prepare(self):
        """
        Method which prepares camera, queue and printer.
        """

        self._capture.prepare()
        self._printing.prepare()

    def keep_going(self) -> bool:
        # here in the future a more complex solution
        return self._continue

    def final_cleaning(self):
        self._capture.stop()
        self._printing.dismiss()

    # ------------------------------------------------------------------ recovery

    def pending_photos(self) -> list:
        """
        Method which returns the photos left in the current folder by a previous,
        interrupted session (disaster recovery).
        :return: list of photo paths
        """

        return disaster_recovery.pending_photos(self._folders.get_current_path())

    def discard_pending_session(self):
        """
        Method which discards the photos left by a previous interrupted session,
        moving them from the current folder to the originals folder.
        """

        self._archiver.archive_current()

    # ------------------------------------------------------------------- capture

    def capture_mode(self) -> str:
        """
        Method which returns the capture mode set in settings ('camera' or 'pc').
        """

        return self._settings.get_capture_mode()

    def capture_hint(self) -> str:
        """
        Method which returns the hint to show before the shot:
        'shutter' if the user has to press the shutter button on the camera,
        'press' if the user has to press a key on the keyboard.
        """

        return self._capture.hint()

    def should_preview_capture(self) -> bool:
        """
        Method which returns True if the shot photo has to be confirmed by the user
        before going on.
        """

        return self._capture.should_preview()

    def capture_photo(self) -> str:
        """
        Method which takes a photo (headless: the presentation layer shows the
        appropriate hint before calling it) and saves it in the current folder.
        :return: shot photo path
        """

        return self._capture.capture()

    def accept_capture(self, photo_path: str):
        """
        Method which marks the shot photo as accepted and moves the session on.
        """

        self._capture.accept()

    def reject_capture(self, photo_path: str):
        """
        Method which rejects the shot photo, moving it to the originals folder.
        :param photo_path: rejected photo path
        """

        self._capture.reject(photo_path)

    # --------------------------------------------------------------------- frame

    def frame_strategy(self) -> str:
        """
        Method which returns the frame selection strategy:
        'configured', 'single', 'random' or 'manual'.
        """

        return self._frame_chooser.strategy()

    def available_frames(self) -> list:
        """
        Method which returns the names of the available frames.
        """

        return self._frame_chooser.available_frames()

    def next_frame(self) -> str:
        """
        Method which returns the next frame name according to the strategy.
        :return: frame name
        """

        return self._frame_chooser.next_frame_name()

    def should_preview_frame(self) -> bool:
        """
        Method which returns True if the edited photo has to be confirmed by the
        user before going on.
        """

        return self._settings.get_preview_post_frame()

    def preview(self, photo_path: str, frame_name: str):
        """
        Method which returns the photo edited with the given frame, without saving it.
        :param photo_path: photo path
        :param frame_name: frame name
        :return: edited photo (PIL image)
        """

        effect_path = self._catalog.path_of(frame_name)
        return self._editor.prepare_single_photo(photo_path, effect_path)

    def abort_session(self, photo_path: str):
        """
        Method which aborts the current session, moving all the files of the
        current folder to the originals folder.
        :param photo_path: photo path of the aborted session
        """

        self._archiver.archive_current(photo_path)

    # ------------------------------------------------------------------- backend

    def send_to_backend(self, photo_path: str, frame_name: str):
        """
        Method which sends the edited photo to the backend (non blocking).
        :param photo_path: photo path
        :param frame_name: frame name
        """

        effect_path = self._catalog.path_of(frame_name)
        edited_photo = self._editor.prepare_single_photo(photo_path, effect_path)
        self._backend.send_photo(edited_photo, os.path.basename(photo_path))

    # --------------------------------------------------------------------- queue

    def enqueue(self, photo_path: str, frame_name: str, copies: int):
        """
        Method which adds the photo and its frame to the printing queues and
        moves the current folder files to the originals folder.
        :param photo_path: photo path
        :param frame_name: frame name
        :param copies: number of copies to print
        """

        effect_path = self._catalog.path_of(frame_name)
        new_photo_path = self._archiver.archive_current(photo_path)
        self._printing.enqueue(new_photo_path, effect_path, copies)

    def prints_pending(self) -> bool:
        """
        Method which returns True if there are enough photos in the queue to print.
        """

        return self._printing.prints_pending()

    def print_next(self) -> PrintResult:
        """
        Method which edits the next pair of photos in the queue and prints them.
        """

        return self._printing.print_next()
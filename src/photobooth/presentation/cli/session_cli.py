import os


class SessionCli:
    """
    SessionCli orchestrates a photobooth session: it is the CLI "session script"
    which drives the logic services and delegates every user interaction to
    CliInteraction.

    The same script can be reused (or mirrored) by a future GUI controller:
    the services expose operations only, so the orchestration is the only
    piece which changes between presentation frontends.
    """

    def __init__(self, capture, frames, recovery, archiver, printing, uploads, interaction):
        self._capture = capture
        self._frames = frames
        self._recovery = recovery
        self._archiver = archiver
        self._printing = printing
        self._uploads = uploads
        self._interaction = interaction

    def run(self):
        """
        Method which prepares the application and runs the main execution loop
        until the operator quits (Ctrl+C).
        """

        self._capture.prepare()
        self._printing.prepare()
        try:
            while not self._capture.stop_requested():
                self.main_execution()
        except KeyboardInterrupt:
            pass
        finally:
            self._capture.request_stop()
            self._capture.stop()

    def main_execution(self):
        """
        Method where disaster recovery is applied if something strange happened in the last session, allowing to resume it.
        If there are many effects in the Assets folder, the user is allowed to choose which one to apply.
        Then the edited photo is shown to the user for confirmation.
        Then the user is asked how many copies of the photo he wants to print.
        At the end if there are 2 or more photos in the printing queue the printing process starts.
        """

        photo_path = self._recover_or_capture()
        if not photo_path:
            return

        frame_name, photo_accepted = self._choose_frame(photo_path)
        if not photo_accepted:
            self._archiver.archive_current(photo_path)
            return

        # ----   send to the server (non blocking)  ----
        self._uploads.send_photo(self._frames.compose(photo_path, frame_name), os.path.basename(photo_path))
        # ------------------------------------------------

        times = self._interaction.choose_times_to_print()
        # the photo is added to the queue and the folder gets cleared
        queued_photo_path = self._archiver.archive_current(photo_path)
        self._printing.enqueue(queued_photo_path, self._frames.frame_path(frame_name), times)

        while self._printing.prints_pending():  # if there are 2 or more photos in queue then start to edit
            self._interaction.show_print_result(self._printing.print_next())

    def _recover_or_capture(self) -> str:
        """
        Method which applies the disaster recovery procedure and, if there is
        nothing to recover, takes a new photo.
        :return: path of the photo to use for the session (empty string to skip the session)
        """

        pending = self._recovery.pending_photos()
        if pending:
            if self._interaction.ask_resume_session():
                return self._interaction.choose_pending_photo(pending)
            self._recovery.discard_pending()

        return self._capture_photo_with_preview()

    def _capture_photo_with_preview(self) -> str:
        """
        Method which allows the user to take a photo, retrying while the user
        rejects the shot.
        :return: shot photo path (empty string if the shot cannot be taken)
        """

        while True:
            if self._capture.hint() == 'shutter':
                self._interaction.wait_for_camera_shutter()
            else:
                self._interaction.press_to_shoot()

            photo_path = self._capture.capture()
            if not photo_path:
                return ''

            self._interaction.notify_shot_taken()

            # up to now to make the pipeline faster, the user will not confirm the shoot here but only after the polaroid edit
            # in the future, granularity will be added
            if not self._capture.should_preview() or self._interaction.confirm_shot(photo_path):
                # the photo is accepted, we can go on
                # session has ended
                self._capture.accept()
                return photo_path
            else:
                self._capture.reject(photo_path)
                self._interaction.notify_photo_rejected()

    def _choose_frame(self, photo_path: str):
        """
        Method which chooses the frame to apply according to the frame strategy
        ('configured', 'single', 'random' or 'manual') and shows its preview if
        requested by the settings.
        :param photo_path: photo path to edit
        :return: tuple (frame name, accepted)
        """

        if self._frames.strategy() == 'manual':
            return self._choose_frame_manually(photo_path)

        frame_name = self._frames.next_frame_name()
        if not self._frames.should_preview() or self._interaction.show_preview_image(
                self._frames.compose(photo_path, frame_name)):
            return frame_name, True
        return '', False

    def _choose_frame_manually(self, photo_path: str):
        """
        Method which allows the user to choose the effect to apply to the shot photo with a preview.
        Returns the effect name when the edited photo is accepted.
        :param photo_path: photo path to edit
        :return: tuple (frame name, accepted)
        """

        # in this case the photo was already accepted in the runner method, so only the edit will be chosen
        # in other words: here the logic to change the photo is not implemented
        while True:
            frame_name = self._interaction.choose_polaroid_effect(self._frames.available_frames())
            if not self._frames.should_preview() or self._interaction.show_preview_image(
                    self._frames.compose(photo_path, frame_name)):
                return frame_name, True

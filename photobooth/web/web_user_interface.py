"""
User interface adapter which mirrors the engine interactions on the web portal.
It can run standalone (the portal is the only interface) or wrap another adapter (e.g. the Tkinter GUI):
in that case both interfaces show the same state and the first answer wins.
"""
import os

from photobooth.web.session import (WebSession, PHASE_APPROVAL, PHASE_COPIES, PHASE_PROCESSING,
                                    PHASE_WAITING_SHOT)


class WebUserInterface:

    def __init__(self, session: WebSession, polaroid_effect_list: list, delegate=None):
        """
        :param session: shared web session
        :param polaroid_effect_list: available frame names
        :param delegate: optional adapter (with the same interface) which keeps working alongside the portal
        """
        self._session = session
        self.effect_list = polaroid_effect_list
        self._delegate = delegate

    def set_reprint_handler(self, handler):
        """
        Enables reprinting gallery photos from the portal.
        :param handler: callable(photo name, copies) -> photos still waiting in the print queue (e.g. Runner.reprint)
        """
        self._session.set_reprint_handler(handler)

    def confirm_shot(self, photo_path, os_platform) -> bool:
        return self._ask_approval(photo_path, "shot",
                                  lambda: self._delegate.confirm_shot(photo_path, os_platform))

    def show_preview_image(self, preview_img) -> bool:
        return self._ask_approval(preview_img, "framed",
                                  lambda: self._delegate.show_preview_image(preview_img))

    def choose_times_to_print(self):
        """
        :return: number of copies, or None if the user went back to the photo approval
        """
        self._session.set_phase(PHASE_COPIES, "Scegli il numero di copie da stampare.")
        if self._delegate is not None:
            times = self._delegate.choose_times_to_print()
        else:
            times = self._session.wait_response()
        if times is None:
            self._session.set_phase(PHASE_PROCESSING, "Torno all'anteprima...")
        else:
            self._session.set_phase(PHASE_PROCESSING, f"{times} {'copia' if times == 1 else 'copie'} in stampa...")
        return times

    def choose_polaroid_effect(self) -> str:
        if self._delegate is not None:
            return self._delegate.choose_polaroid_effect()
        if not self.effect_list:
            return ""
        return self.effect_list[0] + ".png"

    def wait_for_camera_shutter(self):
        if self._delegate is not None:
            self._delegate.wait_for_camera_shutter()
        self._session.set_phase(PHASE_WAITING_SHOT, "Pronto! Premi il pulsante sulla fotocamera per scattare.")

    def press_to_shoot(self):
        if self._delegate is not None:
            self._delegate.press_to_shoot()
        self._session.set_phase(PHASE_WAITING_SHOT, "Scatto in corso...")

    def notify_shot_taken(self):
        if self._delegate is not None:
            self._delegate.notify_shot_taken()
        self._session.set_phase(PHASE_PROCESSING, "Foto acquisita, applico la cornice...")

    def visualize_current_photos(self, path):
        if self._delegate is not None:
            return self._delegate.visualize_current_photos(path)
        photos_list = os.listdir(path)
        if photos_list:
            return os.path.join(path, photos_list[0])
        return ""

    def _ask_approval(self, image_or_path, kind: str, delegate_call) -> bool:
        self._session.set_preview(image_or_path, kind)
        self._session.set_phase(PHASE_APPROVAL, "Approva o scarta la foto.")
        if self._delegate is not None:
            accepted = delegate_call()
        else:
            accepted = self._session.wait_response()

        if accepted:
            self._session.set_phase(PHASE_PROCESSING, "Foto approvata.")
        else:
            self._session.clear_preview()
            self._session.set_phase(PHASE_PROCESSING, "Foto scartata, si riparte.")
        return accepted

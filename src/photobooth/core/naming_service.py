import os


class NamingService:
    """
    NamingService manages the photo naming convention (event_session_photo.jpg)
    and the session counter, persisted through the injected StateStore.
    """

    def __init__(self, state_store, event_name: str, folders):
        self._state_store = state_store
        self._event_name = event_name
        self._folders = folders

    def get_photo_name(self) -> str:
        """
        Method which returns the photo name according to the naming convention.
        Photo number in the current folder is considered.
        :return: photo name
        """

        session_number = int(self._state_store.load_naming_session_string()) + 1
        photo_number = len(os.listdir(self._folders.get_current_path())) + 1

        return f"{self._event_name}_{session_number:04d}_{photo_number:02d}.jpg"

    def increment_session_number(self):
        """
        Method which increments the session number in the state store.
        :return: new session number
        """

        new_session = f"{int(self._state_store.load_naming_session_string()) + 1:04d}"
        self._state_store.save_naming_session_string(new_session)

        return new_session
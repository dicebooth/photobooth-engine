import os


def get_string_from_photo_number(photo_number):
    """
    Method which returns the photo number as string.
    :return: photo number as string
    """

    if len(str(photo_number)) == 1:
        return f"0{photo_number}"

    return photo_number


def get_string_from_session_number(session_number):
    """
    Method which returns the session number as string.
    :return: session number as string
    """

    if len(str(session_number)) == 1:
        return f"000{session_number}"
    elif len(str(session_number)) == 2:
        return f"00{session_number}"
    elif len(str(session_number)) == 3:
        return f"0{session_number}"

    return session_number


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

        session_number = self._state_store.load_naming_session_string()
        photo_number = get_string_from_photo_number(len(os.listdir(self._folders.get_current_path())) + 1)

        return f"{self._event_name}_{get_string_from_session_number(int(session_number) + 1)}_{photo_number}.jpg"

    def increment_session_number(self):
        """
        Method which increments the session number in the state store.
        :return: new session number
        """

        new_session = get_string_from_session_number(int(self._state_store.load_naming_session_string()) + 1)
        self._state_store.save_naming_session_string(new_session)

        return new_session
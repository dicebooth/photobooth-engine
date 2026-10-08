from photobooth.api.backend.backend import PhotoAPIClient


class BackendService:
    """
    BackendService dispatches the photo upload to the backend.

    It receives the already edited photo (PIL image) from the core gateway:
    the re-editing step is no more needed here, as the gateway is the single
    owner of the editing pipeline.
    """

    def __init__(self, backend_url: str, client_secret: str = None) -> None:
        self._backend = PhotoAPIClient(base_url=backend_url, client_secret=client_secret)

    def send_photo(self, edited_photo, photo_name: str):
        """
        Method which sends the edited photo to the backend (fire-and-forget,
        it never blocks the caller).
        :param edited_photo: edited photo (PIL image)
        :param photo_name: name of the photo
        """

        self._backend.upload_pil_background(edited_photo, photo_name)
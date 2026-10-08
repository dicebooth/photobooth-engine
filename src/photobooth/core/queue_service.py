class QueueService:
    """
    QueueService manages the photo and edit queues (logic only, persistence
    delegated to the injected StateStore).
    It provides methods to add photos and edits to the queues, check if the
    photo queue is ready, and get photos and edits from the queues.
    """

    def __init__(self, state_store):
        self._state_store = state_store
        self._dict = {'photos': [], 'edits': []}
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        queues = self._state_store.load_queues()
        self._dict['photos'] = queues.get('photos', [])
        self._dict['edits'] = queues.get('edits', [])

    def _update_state(self):
        """
        Method which persists the current queues.
        """

        self._state_store.save_queues(self._dict['photos'], self._dict['edits'])

    def queue_is_ready(self):
        """
        Method which checks if there are enough photos in the photo queue.
        :return: True if ready, False otherwise
        """

        return len(self._dict['photos']) >= 2

    def add_photo(self, photo_path, times):
        """
        Method which adds a photo to the photo queue according to the number of prints required.
        Then it persists the updated state.
        :param photo_path: photo path to add
        :param times: times number to add the photo
        """

        for _ in range(times):
            self._dict['photos'].append(photo_path)
        self._update_state()

    def add_edit(self, edit_path, times):
        """
        Method which adds an edit to the edit queue according to the number of prints required.
        Then it persists the updated state.
        :param edit_path: edit path to add
        :param times: times number to add the edit
        """

        for _ in range(times):
            self._dict['edits'].append(edit_path)
        self._update_state()

    def get_photos(self) -> list[str]:
        """
        Method which gets the photos from the queue and removes them.
        """
        num = 2
        photos = self._dict['photos'][:num]
        del self._dict['photos'][:num]
        self._update_state()
        return photos

    def get_edits(self) -> list[str]:
        """
        Method which gets the edits from the queue and removes them.
        """
        num = 2
        edits = self._dict['edits'][:num]
        del self._dict['edits'][:num]
        self._update_state()
        return edits

    def load_queue(self):
        """
        Method which loads photo and edit queues from the state store.
        """

        queues = self._state_store.load_queues()
        self._dict['photos'] = queues.get('photos', [])
        self._dict['edits'] = queues.get('edits', [])

    def dismiss(self):
        """
        Method which clears the photo and edit queues and persists the state.
        """

        self._dict = {'photos': [], 'edits': []}
        self._update_state()
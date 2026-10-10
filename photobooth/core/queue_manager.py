import os
import yaml

"""
QueueManager class manages the photo and edit queues.
It provides methods to add photos and edits to the queues, check if the photo queue is ready, and get photos and edits from the queues.
"""


class QueueManager:

    def __init__(self, print_size=None):
        from photobooth.consts import DEFAULT_PRINT_SIZE, TEMP_DATA_PATH
        self._print_size = print_size or DEFAULT_PRINT_SIZE
        self._queue_path = TEMP_DATA_PATH
        self._dict = {'photos': [], 'edits': []}
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(self._queue_path):
            with open(self._queue_path, 'w') as f:
                yaml.dump({'photos': [], 'edits': [], 'session': '0000'}, f, default_flow_style=False,
                          allow_unicode=True)

    def _update_yaml(self):
        """
        Method which updates the yaml file with the current queues.
        """

        with open(self._queue_path, 'r') as f:
            yaml_dict = yaml.safe_load(f)
        yaml_dict['photos'] = self._dict['photos']
        yaml_dict['edits'] = self._dict['edits']
        with open(self._queue_path, 'w') as f:
            yaml.dump(yaml_dict, f, default_flow_style=False, allow_unicode=True)

    def queue_is_ready(self):
        """
        Method which checks if there are enough photos in the photo queue.
        :return: True if ready, False otherwise
        """

        return len(self._dict['photos']) >= 2

    def add_photo(self, photo_path, times):
        """
        Method which adds a photo to the photo queue according to the number of prints required.
        Then it updates the temp_data.yaml file.
        :param photo_path: photo path to add
        :param times: times number to add the photo
        """

        for _ in range(times):
            self._dict['photos'].append(photo_path)
        self._update_yaml()

    def add_edit(self, edit_path, times):
        """
        Method which adds an edit to the edit queue according to the number of prints required.
        Then it updates the temp_data.yaml file.
        :param edit_path: edit path to add
        :param times: times number to add the edit
        """

        for _ in range(times):
            self._dict['edits'].append(edit_path)
        self._update_yaml()

    def pending_count(self) -> int:
        """
        Method which returns how many photos are waiting in the queue to be printed.
        :return: number of queued photos
        """

        return len(self._dict['photos'])

    def get_photos(self) -> list[str]:
        """
        Method which gets the photos from the queue and removes them.
        """
        num = 2
        photos = self._dict['photos'][:num]
        del self._dict['photos'][:num]
        self._update_yaml()
        return photos

    def get_edits(self) -> list[str]:
        """
        Method which gets the edits from the queue and removes them.
        """
        num = 2
        edits = self._dict['edits'][:num]
        del self._dict['edits'][:num]
        self._update_yaml()
        return edits

    def load_queue(self):
        """
        Method which loads photo and edit queues from the temp_data.yaml file.
        """

        with open(self._queue_path, 'r') as file:
            yaml_dict = yaml.load(file, Loader=yaml.FullLoader)
        if yaml_dict is not None:
            self._dict['photos'] = yaml_dict['photos']
            self._dict['edits'] = yaml_dict['edits']

    def dismiss(self):
        """
        Method which clears the photo and edit queues and updates the temp_data.yaml file.
        """

        self._dict = {'photos': [], 'edits': []}
        self._update_yaml()

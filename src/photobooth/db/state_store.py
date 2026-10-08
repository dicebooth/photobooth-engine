import os

import yaml


class StateStore:
    """
    StateStore is the infrastructure component which persists the runtime state
    (photo/edit queues and session counters) on the temp_data.yaml file.

    The path is injected by the composition root, so tests can point it to a
    temporary directory without touching the real project files.
    """

    _DEFAULT_STATE = {'photos': [], 'edits': [], 'session': '0000'}

    def __init__(self, path: str):
        self._path = path
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        folder = os.path.dirname(self._path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        if not os.path.exists(self._path):
            self._write(dict(self._DEFAULT_STATE))

    def _read(self) -> dict:
        with open(self._path, 'r') as yaml_file:
            return yaml.safe_load(yaml_file) or {}

    def _write(self, data: dict):
        # Atomic write: dump to a sibling temp file, fsync it, then rename it
        # over the state file. A crash or power loss mid-write can never leave
        # a truncated/corrupted temp_data.yaml behind.
        tmp_path = self._path + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as yaml_file:
            yaml.dump(data, yaml_file, default_flow_style=False, allow_unicode=True)
            yaml_file.flush()
            os.fsync(yaml_file.fileno())

        os.replace(tmp_path, self._path)

        # Durability of the rename itself: fsync the containing directory,
        # otherwise a power loss right after the replace could still roll it back.
        dir_path = os.path.dirname(os.path.abspath(self._path)) or '.'
        if hasattr(os, 'O_DIRECTORY'):
            dir_fd = os.open(dir_path, os.O_DIRECTORY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)

    def _update(self, **updates):
        data = self._read()
        data.update(updates)
        self._write(data)

    # ---- photo/edit queues ----
    def load_queues(self) -> dict:
        data = self._read()
        return {
            'photos': data.get('photos', []),
            'edits': data.get('edits', []),
        }

    def save_queues(self, photos: list, edits: list):
        self._update(photos=photos, edits=edits)

    # ---- session counter ----
    def load_naming_session_string(self) -> str:
        return str(self._read().get('session', '0000'))

    def save_naming_session_string(self, session: str):
        self._update(session=session)

    # ---- wifi camera state ----
    def load_wifi_id(self):
        return self._read().get('last_read_wifi_id', None)

    def save_wifi_id(self, wifi_id):
        data = self._read()
        data.pop('processed_wifi_photos', None)
        data['last_read_wifi_id'] = wifi_id
        self._write(data)
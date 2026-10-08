import os

import pytest
import yaml

from photobooth.db.state_store import StateStore


@pytest.fixture
def state_path(tmp_path):
    return str(tmp_path / 'temp_data.yaml')


def test_initial_state_is_created(state_path):
    store = StateStore(state_path)

    assert os.path.exists(state_path)
    assert store.load_queues() == {'photos': [], 'edits': []}
    assert store.load_naming_session_string() == '0000'


def test_write_produces_valid_yaml_and_no_leftover_tmp(state_path):
    store = StateStore(state_path)
    store.save_queues(['a.jpg', 'b.jpg'], ['frame.png', 'frame.png'])

    with open(state_path, encoding='utf-8') as state_file:
        data = yaml.safe_load(state_file)

    assert data['photos'] == ['a.jpg', 'b.jpg']
    assert data['edits'] == ['frame.png', 'frame.png']
    # the temp file is renamed away by os.replace: nothing must be left behind
    assert not os.path.exists(state_path + '.tmp')


def test_update_preserves_other_keys(state_path):
    store = StateStore(state_path)
    store.save_queues(['a.jpg'], ['frame.png'])
    store.save_naming_session_string('0042')

    data = yaml.safe_load(open(state_path, encoding='utf-8'))

    assert data['photos'] == ['a.jpg']
    assert data['session'] == '0042'


def test_interrupted_write_keeps_previous_state(state_path, monkeypatch):
    """A crash while dumping must not corrupt the previous state file."""
    store = StateStore(state_path)
    store.save_queues(['old.jpg'], ['frame.png'])
    before = open(state_path, encoding='utf-8').read()

    def exploding_dump(data, stream, **kwargs):
        stream.write('half a yaml document')
        raise OSError('simulated power loss')

    monkeypatch.setattr(yaml, 'dump', exploding_dump)
    with pytest.raises(OSError):
        store.save_queues(['new.jpg'], ['frame.png'])

    # the real state file still holds the last complete write
    assert open(state_path, encoding='utf-8').read() == before
    assert store.load_queues()['photos'] == ['old.jpg']


def test_empty_file_reads_fall_back_to_defaults(state_path):
    open(state_path, 'w', encoding='utf-8').close()
    store = StateStore(state_path)

    assert store.load_queues() == {'photos': [], 'edits': []}
    assert store.load_naming_session_string() == '0000'

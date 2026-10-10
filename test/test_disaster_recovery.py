import photobooth.core.disaster_recovery as recovery


class FakeSettings:
    def get_preview_post_frame(self):
        return True


class FailingUI:
    def show_preview_image(self, preview_img):
        raise AssertionError("the recovered photo must be approved only once, in the frame chooser")

    confirm_shot = show_preview_image


def test_recovered_photo_is_not_approved_twice(tmp_path, monkeypatch):
    monkeypatch.setattr(recovery, "Settings", FakeSettings)
    (tmp_path / "Event_0001_01.jpg").write_bytes(b"photo")

    assert recovery.resume_old_session(str(tmp_path), FailingUI()) == str(tmp_path / "Event_0001_01.jpg")


def test_empty_session_has_nothing_to_recover(tmp_path):
    assert recovery.resume_old_session(str(tmp_path), FailingUI()) is False

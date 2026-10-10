import json
import threading
import urllib.error
import urllib.request

import pytest
from PIL import Image

import photobooth.web.session as session_module
from photobooth.web.server import start_portal_server
from photobooth.web.session import WebSession, PHASE_APPROVAL, PHASE_COPIES
from photobooth.web.web_user_interface import WebUserInterface

TOKEN = "secret"


class FakeSettings:
    def get_min_num_photos(self):
        return 1

    def get_max_num_photos(self):
        return 10

    def get_warn_num_photos(self):
        return 5

    def get_event_name(self):
        return "Test"


@pytest.fixture
def session(tmp_path, monkeypatch):
    monkeypatch.setattr(session_module, "Settings", FakeSettings)
    Image.new("RGB", (40, 30), "red").save(tmp_path / "Test_0001_01.jpg")
    return WebSession(str(tmp_path))


@pytest.fixture
def server(session):
    srv = start_portal_server(session, "127.0.0.1", 0, TOKEN)
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def call(url, body=None, token=TOKEN):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"X-Photobooth-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            return res.status, res.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_answers_are_accepted_only_when_requested(session):
    assert not session.submit(PHASE_APPROVAL, True)

    session.set_phase(PHASE_APPROVAL)
    assert session.submit(PHASE_APPROVAL, True)
    # a second tap (or a second phone) must not leak an answer into the next request
    assert not session.submit(PHASE_APPROVAL, False)
    assert session.wait_response() is True


def test_web_interface_flow(session):
    ui = WebUserInterface(session, ["frame"])
    results = []
    engine = threading.Thread(target=lambda: results.extend([ui.show_preview_image(Image.new("RGB", (10, 10))),
                                                             ui.choose_times_to_print()]))
    engine.start()

    for kind, value in ((PHASE_APPROVAL, True), (PHASE_COPIES, 3)):
        state = session.wait_for_change(-1, 1)
        while state["phase"] != kind:
            state = session.wait_for_change(state["version"], 1)
        assert session.submit(kind, value)

    engine.join(timeout=5)
    assert results == [True, 3]


def test_api_requires_token(server):
    assert call(f"{server}/api/state", token="wrong")[0] == 401
    status, body = call(f"{server}/api/state")
    assert status == 200
    assert json.loads(body)["copies"] == {"min": 1, "max": 10, "warn": 5}


def test_api_validates_answers(server, session):
    assert call(f"{server}/api/approval", {"accepted": True})[0] == 409
    session.set_phase(PHASE_COPIES)
    assert call(f"{server}/api/copies", {"copies": 11})[0] == 400
    assert call(f"{server}/api/copies", {"copies": True})[0] == 400
    assert call(f"{server}/api/copies", {"copies": 2})[0] == 200
    assert session.wait_response() == 2


def test_gallery(server):
    status, body = call(f"{server}/api/gallery")
    photos = json.loads(body)["photos"]
    assert [p["name"] for p in photos] == ["Test_0001_01.jpg"]
    assert call(f"{server}/api/gallery/Test_0001_01.jpg?thumb=1")[0] == 200
    assert call(f"{server}/api/gallery/..%2Fsecret.jpg")[0] == 404


def test_https_portal(session, tmp_path):
    import ssl
    from photobooth.web.certificate import ensure_certificate

    cert_files = ensure_certificate(["192.168.1.10"], str(tmp_path / "cert"))
    # the certificate is reused, so phones that accepted it are not asked again
    assert ensure_certificate([], str(tmp_path / "cert")) == cert_files

    srv = start_portal_server(session, "127.0.0.1", 0, TOKEN, cert_files)
    try:
        ctx = ssl.create_default_context(cafile=cert_files[0])
        req = urllib.request.Request(f"https://localhost:{srv.server_address[1]}/api/state",
                                     headers={"X-Photobooth-Token": TOKEN})
        with urllib.request.urlopen(req, timeout=5, context=ctx) as res:
            assert res.status == 200
    finally:
        srv.shutdown()


def test_https_client_disconnect_is_silent(session, tmp_path, capsys):
    import socket
    import ssl
    import time
    from photobooth.web.certificate import ensure_certificate

    srv = start_portal_server(session, "127.0.0.1", 0, TOKEN, ensure_certificate([], str(tmp_path / "cert")))
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        # a phone dropping the connection without TLS close_notify while the server answers
        tls = ctx.wrap_socket(socket.create_connection(srv.server_address))
        tls.send(b"GET /api/state HTTP/1.1\r\nHost: x\r\n\r\n")
        socket.socket(fileno=tls.detach()).close()
        time.sleep(0.5)
    finally:
        srv.shutdown()
    assert "Traceback" not in capsys.readouterr().err


def test_back_from_copies(server, session):
    assert call(f"{server}/api/back", {})[0] == 409
    session.set_phase(PHASE_COPIES)
    assert call(f"{server}/api/back", {})[0] == 200
    assert session.wait_response() is None


def test_reprint(server, session):
    requests = []
    session.set_reprint_handler(lambda name, copies: requests.append((name, copies)) or 1)

    assert call(f"{server}/api/reprint", {"name": "Test_0001_01.jpg", "copies": 11})[0] == 400
    assert call(f"{server}/api/reprint", {"name": "missing.jpg", "copies": 1})[0] == 404

    status, body = call(f"{server}/api/reprint", {"name": "Test_0001_01.jpg", "copies": 2})
    assert status == 200 and json.loads(body) == {"ok": True, "pending": 1}
    assert requests == [("Test_0001_01.jpg", 2)]


def test_already_framed_photos_are_printed_as_they_are(tmp_path):
    from photobooth.core.photo_edit_manager import Tailor

    framed = tmp_path / "framed.jpg"
    Image.new("RGB", (300, 400), "blue").save(framed)
    editor = Tailor("4x3")
    editor.set_infos([str(framed), str(framed)], ["", ""], str(tmp_path))

    with Image.open(editor.edit()) as sheet:
        # two framed photos stacked on a 4x6 sheet, no frame applied on top
        r, g, b = sheet.convert("RGB").getpixel((sheet.width // 2, sheet.height // 4))
        assert b > 200 and r < 50 and g < 50

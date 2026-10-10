"""
Mobile web portal package: lets an operator drive the photobooth from a smartphone on the same local network.
"""
import secrets
import threading

from photobooth.core.folder_manager import FolderManager
from photobooth.settings_manager import Settings
from photobooth.utils import check_hardware_status
from photobooth.web.certificate import ensure_certificate
from photobooth.web.network import get_lan_ips, print_connection_info
from photobooth.web.server import start_portal_server
from photobooth.web.session import WebSession
from photobooth.web.web_user_interface import WebUserInterface


def setup_web_portal(effect_list: list, host: str, port: int, token: str = None, https: bool = True,
                     delegate=None, gui=None) -> WebUserInterface:
    """
    Creates the web session, starts the HTTP server and prints connection info on the terminal.
    :param effect_list: available frame names
    :param host: address to bind the server to
    :param port: port to bind the server to
    :param token: access token, randomly generated if not given
    :param https: serve the portal over HTTPS with a self-signed certificate (required by the QR scanner camera)
    :param delegate: optional UI adapter which keeps working alongside the portal
    :param gui: optional PhotoboothGUI instance: web answers are routed through it to keep both interfaces in sync
    :return: the UI adapter to give to the Runner
    """

    settings = Settings()
    session = WebSession(FolderManager(settings.get_main_folder_path()).get_framed_photos_path())
    if gui is not None:
        session.set_responder(gui.submit_response)

    def check_hardware():
        session.set_hardware_status(*check_hardware_status(settings))

    threading.Thread(target=check_hardware, daemon=True).start()

    token = token or secrets.token_urlsafe(6)
    cert_files = ensure_certificate(get_lan_ips()) if https else None
    start_portal_server(session, host, port, token, cert_files)
    print_connection_info(host, port, token, https)

    return WebUserInterface(session, effect_list, delegate=delegate)

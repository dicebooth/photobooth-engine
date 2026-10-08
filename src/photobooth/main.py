import os

from photobooth import consts
from photobooth.api.backend.backend_service import BackendService
from photobooth.api.backend.logger import setup_logging
from photobooth.api.camera.camera_service import build_camera
from photobooth.api.local_storage_api import AssetManager, FolderManager
from photobooth.api.printer_api import Printer
from photobooth.core.editor_service import EditorService
from photobooth.core.frame_chooser_service import FrameChooserService
from photobooth.core.gateway import Gateway
from photobooth.core.naming_service import NamingService
from photobooth.core.queue_service import QueueService
from photobooth.core.settings import Settings
from photobooth.db.state_store import StateStore
from photobooth.presentation.cli.interaction_cli import CliInteraction
from photobooth.presentation.cli.session_cli import SessionCli


def resolve_home() -> str:
    """
    Method which resolves the project home: the folder containing settings.yaml,
    Assets and the runtime state files.

    It can be overridden with the PHOTOBOOTH_HOME environment variable,
    otherwise the current working directory is used.
    """

    return os.environ.get(consts.PHOTOBOOTH_HOME_ENV) or os.getcwd()


def build_gateway(home: str, settings: Settings) -> Gateway:
    """
    Method which wires all the components (composition root) and returns the
    core gateway used by the presentation layer.
    :param home: project home folder
    :param settings: already loaded settings (single instance, read once)
    :return: Gateway instance
    """

    state_store = StateStore(os.path.join(home, consts.STATE_FILENAME))

    folders = FolderManager(settings.get_main_folder_path())
    assets = AssetManager(os.path.join(home, consts.ASSETS_DIRNAME))

    camera = build_camera(
        camera_name=settings.get_cam_name(),
        connection=settings.get_camera_connection(),
        hotfolder_path=settings.get_camera_hotfolder_path(),
        state_store=state_store,
    )

    editor = EditorService()
    queue = QueueService(state_store)
    naming = NamingService(state_store, settings.get_event_name(), folders)
    frame_chooser = FrameChooserService(assets, settings.get_frame_name())

    printer = Printer(
        settings.get_printer_name(),
        settings.get_printer_options(),
        print_size=settings.get_print_size(),
        enable_hotfolder=settings.get_enable_hotfolder(),
        hotfolder_path=settings.get_printer_hotfolder_path(),
    )

    backend = BackendService(
        backend_url=settings.get_backend_url(),
        client_secret=settings.get_client_secret(),
    )

    return Gateway(settings, folders, assets, camera, editor, queue, naming, frame_chooser, printer, backend)


def main():
    """
    This is the main entry point of the application.
    It wires all the components (composition root) and starts the CLI session loop.
    """

    home = resolve_home()
    setup_logging(os.path.join(home, consts.UPLOAD_LOG_FILENAME))

    settings = Settings(os.path.join(home, consts.SETTINGS_FILENAME))
    gateway = build_gateway(home, settings)

    interaction = CliInteraction(settings)
    session = SessionCli(gateway, interaction)
    session.run()


if __name__ == '__main__':
    main()
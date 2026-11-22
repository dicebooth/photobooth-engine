import logging
import os

from photobooth import consts
from photobooth.api.backend.backend import PhotoAPIClient
from photobooth.api.camera.camera_factory import build_camera
from photobooth.api.printing.cups_printer import CupsPrinter
from photobooth.api.printing.hotfolder_printer import HotfolderPrinter
from photobooth.logic.capture.capture_service import CaptureService
from photobooth.logic.capture.photo_id_sequencer import PhotoIdSequencer
from photobooth.logic.editing.editor_service import EditorService
from photobooth.logic.frames.frame_catalog import FrameCatalog
from photobooth.logic.frames.frame_chooser_service import FrameChooserService
from photobooth.logic.gateway import Gateway
from photobooth.logic.editing.naming_service import NamingService
from photobooth.logic.editing.photo_encoder import PhotoEncoder
from photobooth.logic.printing.print_options_resolver import PrintOptionsResolver
from photobooth.logic.printing.print_service import PrintService
from photobooth.logic.printing.queue_service import QueueService
from photobooth.logic.session.folder_manager import FolderManager
from photobooth.logic.session.originals_archiver import OriginalsArchiver
from photobooth.logic.settings.settings import Settings
from photobooth.logic.uploads.logger import setup_logging
from photobooth.logic.uploads.upload_service import UploadService
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


def setup_console_logging() -> None:
    """
    Method which shows on the terminal the messages of the drivers and services
    (camera waiting, retries, ...). The upload logger has its own file and does not propagate.
    """

    logger = logging.getLogger('photobooth')
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(handler)


def build_gateway(home: str, settings: Settings) -> Gateway:
    """
    Method which wires all the components (composition root) and returns the
    logic gateway used by the presentation layer.
    :param home: project home folder
    :param settings: already loaded settings (single instance, read once)
    :return: Gateway instance
    """

    state_store = StateStore(os.path.join(home, consts.STATE_FILENAME))

    folders = FolderManager(settings.get_main_folder_path())
    archiver = OriginalsArchiver(folders)
    catalog = FrameCatalog(os.path.join(home, consts.ASSETS_DIRNAME))

    capture_settings = settings.capture
    camera = build_camera(
        camera_name=capture_settings.cam_name,
        connection=capture_settings.camera_connection,
        hotfolder_path=capture_settings.camera_hotfolder_path,
        sequencer=PhotoIdSequencer(state_store),
    )

    editor = EditorService()
    queue = QueueService(state_store)
    naming = NamingService(state_store, settings.get_event_name(), folders)
    capture = CaptureService(camera, folders, archiver, naming, capture_settings)
    frame_chooser = FrameChooserService(catalog, settings.get_frame_name())

    print_settings = settings.printing
    if print_settings.enable_hotfolder:
        printer = HotfolderPrinter(print_settings.printer_hotfolder_path)
    else:
        printer = CupsPrinter(print_settings.printer_name)
    options_resolver = PrintOptionsResolver(
        print_settings.printer_name, print_settings.print_size, print_settings.printer_options)
    printing = PrintService(queue, editor, folders, printer, options_resolver)

    upload_settings = settings.uploads
    backend = UploadService(
        PhotoAPIClient(base_url=upload_settings.backend_url, client_secret=upload_settings.client_secret),
        PhotoEncoder(),
    )

    return Gateway(settings, folders, archiver, catalog, capture, editor, printing, frame_chooser, backend)


def main():
    """
    This is the main entry point of the application.
    It wires all the components (composition root) and starts the CLI session loop.
    """

    setup_console_logging()
    home = resolve_home()
    setup_logging(os.path.join(home, consts.UPLOAD_LOG_FILENAME))

    settings = Settings(os.path.join(home, consts.SETTINGS_FILENAME))
    gateway = build_gateway(home, settings)

    interaction = CliInteraction(settings)
    session = SessionCli(gateway, interaction)
    session.run()


if __name__ == '__main__':
    main()
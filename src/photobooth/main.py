import logging
import os
from dataclasses import dataclass

from photobooth import consts
from photobooth.api.backend.backend import PhotoAPIClient
from photobooth.api.camera.camera_factory import build_camera
from photobooth.api.platform_api import detect_os
from photobooth.api.printing.cups_printer import CupsPrinter
from photobooth.api.printing.hotfolder_printer import HotfolderPrinter
from photobooth.db.state_store import StateStore
from photobooth.logic.capture.capture_service import CaptureService
from photobooth.logic.capture.photo_id_sequencer import PhotoIdSequencer
from photobooth.logic.editing.editor_service import EditorService
from photobooth.logic.editing.naming_service import NamingService
from photobooth.logic.editing.photo_encoder import PhotoEncoder
from photobooth.logic.frames.frame_catalog import FrameCatalog
from photobooth.logic.frames.frame_compositor import FrameCompositor
from photobooth.logic.frames.frame_service import FrameService
from photobooth.logic.printing.print_options_resolver import PrintOptionsResolver
from photobooth.logic.printing.print_service import PrintService
from photobooth.logic.printing.queue_service import QueueService
from photobooth.logic.session.folder_manager import FolderManager
from photobooth.logic.session.originals_archiver import OriginalsArchiver
from photobooth.logic.session.recovery_service import RecoveryService
from photobooth.logic.settings.settings import Settings
from photobooth.logic.uploads.logger import setup_logging
from photobooth.logic.uploads.upload_service import UploadService
from photobooth.presentation.cli.interaction_cli import CliInteraction
from photobooth.presentation.cli.session_cli import SessionCli


@dataclass(frozen=True)
class Services:
    """The wired logic services a presentation frontend needs (no behaviour, just a handy bundle)."""

    capture: CaptureService
    frames: FrameService
    recovery: RecoveryService
    archiver: OriginalsArchiver
    printing: PrintService
    uploads: UploadService


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


def build_services(home: str, settings: Settings) -> Services:
    """
    Method which wires all the components (composition root) and returns the
    logic services used by the presentation layer.
    :param home: project home folder
    :param settings: already loaded settings (single instance, read once)
    :return: the wired services
    """

    state_store = StateStore(os.path.join(home, consts.STATE_FILENAME))

    storage_settings = settings.storage
    folders = FolderManager(storage_settings.main_folder_path)
    archiver = OriginalsArchiver(folders)
    recovery = RecoveryService(folders, archiver)
    naming = NamingService(state_store, storage_settings.event_name, folders)

    # ---- capture
    capture_settings = settings.capture
    camera = build_camera(
        camera_name=capture_settings.cam_name,
        connection=capture_settings.camera_connection,
        hotfolder_path=capture_settings.camera_hotfolder_path,
        sequencer=PhotoIdSequencer(state_store),
    )
    capture = CaptureService(camera, folders, archiver, naming, capture_settings)

    # ---- frames and editing
    compositor = FrameCompositor()
    frames = FrameService(FrameCatalog(os.path.join(home, consts.ASSETS_DIRNAME)), compositor, settings.frames)
    editor = EditorService(compositor)

    # ---- printing
    print_settings = settings.printing
    if print_settings.enable_hotfolder:
        printer = HotfolderPrinter(print_settings.printer_hotfolder_path)
    else:
        printer = CupsPrinter(print_settings.printer_name)
    options_resolver = PrintOptionsResolver(
        print_settings.printer_name, print_settings.print_size, print_settings.printer_options)
    printing = PrintService(QueueService(state_store), editor, folders, printer, options_resolver)

    # ---- uploads
    upload_settings = settings.uploads
    uploads = UploadService(
        PhotoAPIClient(base_url=upload_settings.backend_url, client_secret=upload_settings.client_secret),
        PhotoEncoder(),
    )

    return Services(capture, frames, recovery, archiver, printing, uploads)


def build_session(services: Services, interaction) -> SessionCli:
    """
    Method which builds the CLI session script on top of the given services.
    :param services: wired logic services
    :param interaction: user interaction implementation (CliInteraction, or a test double)
    """

    return SessionCli(services.capture, services.frames, services.recovery, services.archiver,
                      services.printing, services.uploads, interaction)


def main():
    """
    This is the main entry point of the application.
    It wires all the components (composition root) and starts the CLI session loop.
    """

    setup_console_logging()
    home = resolve_home()
    setup_logging(os.path.join(home, consts.UPLOAD_LOG_FILENAME))

    settings = Settings(os.path.join(home, consts.SETTINGS_FILENAME))
    services = build_services(home, settings)

    interaction = CliInteraction(settings.interaction, detect_os())
    build_session(services, interaction).run()


if __name__ == '__main__':
    main()

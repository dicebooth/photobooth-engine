from dataclasses import dataclass, field

from photobooth import consts


@dataclass(frozen=True)
class StorageSettings:
    """Where the photos are stored and how they are named."""

    main_folder_path: str
    event_name: str


@dataclass(frozen=True)
class CaptureSettings:
    """How a photo is taken."""

    cam_name: str
    capture_mode: str = consts.DEFAULT_CAPTURE_MODE
    camera_connection: str = consts.DEFAULT_CAMERA_CONNECTION
    camera_hotfolder_path: str = ''
    preview_pre_frame: bool = consts.DEFAULT_PREVIEW_PRE_FRAME
    retry_delay_sec: float = consts.CAMERA_RETRY_DELAY_SEC


@dataclass(frozen=True)
class FrameSettings:
    """Which frame is applied to the photos."""

    frame_name: str = ''
    preview_post_frame: bool = consts.DEFAULT_PREVIEW_POST_FRAME


@dataclass(frozen=True)
class PrintSettings:
    """How the edited photos are printed."""

    printer_name: str
    printer_options: dict = field(default_factory=dict)
    print_size: str = consts.DEFAULT_PRINT_SIZE
    enable_hotfolder: bool = consts.DEFAULT_ENABLE_HOTFOLDER
    printer_hotfolder_path: str = ''


@dataclass(frozen=True)
class UploadSettings:
    """Where the edited photos are uploaded."""

    backend_url: str
    client_secret: str = ''


@dataclass(frozen=True)
class InteractionSettings:
    """What the presentation layer needs to prompt the user."""

    terminal_preview: bool = consts.DEFAULT_TERMINAL_PREVIEW
    terminal_preview_rows: int = consts.DEFAULT_TERMINAL_PREVIEW_ROWS
    min_num_photos: int = consts.DEFAULT_MIN_NUM_PHOTOS
    max_num_photos: int = consts.DEFAULT_MAX_NUM_PHOTOS
    warn_num_photos: int = consts.DEFAULT_WARN_NUM_PHOTOS

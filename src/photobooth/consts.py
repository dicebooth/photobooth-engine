# Runtime files and directories.
# All these paths are resolved against the project root (PHOTOBOOTH_HOME, defaults to the CWD).
PHOTOBOOTH_HOME_ENV = "PHOTOBOOTH_HOME"
SETTINGS_FILENAME = "settings.yaml"
STATE_FILENAME = "temp_data.yaml"
ASSETS_DIRNAME = "Assets"
UPLOAD_LOG_FILENAME = "photobooth-upload.log"

# Default configuration values
DEFAULT_PRINT_SIZE = "4x6"
DEFAULT_CAPTURE_MODE = "pc"
DEFAULT_CAMERA_CONNECTION = "usb"
DEFAULT_ENABLE_HOTFOLDER = False
DEFAULT_PREVIEW_PRE_FRAME = True
DEFAULT_PREVIEW_POST_FRAME = True
DEFAULT_TERMINAL_PREVIEW = False
DEFAULT_TERMINAL_PREVIEW_ROWS = 0
DEFAULT_MIN_NUM_PHOTOS = 1
DEFAULT_MAX_NUM_PHOTOS = 99
DEFAULT_WARN_NUM_PHOTOS = 20

# Logger settings
LOGGER_NAME = "photobooth.upload"

# Backend defaults
DEFAULT_BACKEND_URL = "http://localhost:8000"
DEFAULT_CLIENT_ID = "agent"
DEFAULT_TIMEOUT = (5.0, 30.0)

# Camera/WiFi settings
CAMERA_EVENT_TIMEOUT_MS = 1000
CAMERA_RETRY_DELAY_SEC = 2
WIFI_POLL_DELAY_SEC = 0.5

# Image manipulation
FINAL_PADDING_PERCENTAGE = 98
IMAGE_SIZE_4X3 = (2000, 1500)
IMAGE_SIZE_4X6 = (2000, 3000)
ALPHA_THRESHOLD = 128
PADDING_BACKGROUND_COLOR = (240, 240, 240)

# Printer options mapping
POSSIBLE_PRINTER_OPTIONS = {
    "StpiShrinkOutput": ["Shrink", "Crop", "Expand"],  # Opzione Gutenprint (se disponibile)
    "fit-to-page": [True, False],  # Opzione CUPS standard
    "scaling": list(range(1, 201)),  # Percentuale di ridimensionamento (1-200)
    "ImageableArea": ["Auto", "Custom"],  # Area stampabile
    "fitplot": [True, False],  # Adattamento immagine alla pagina
    "crop-to-fit": [True, False],  # Ritaglio immagine per adattarla alla pagina
    "page-border": ["None", "Single", "Double", "Thick"],  # Aggiunta di bordi
}

BEST_OPTION_VALUE = {
    "StpiShrinkOutput": "Shrink",
    "fit-to-page": True,  # Opzione CUPS standard
    "scaling": 100,  # Percentuale di ridimensionamento (1-200)
    "ImageableArea": "Auto",  # Area stampabile
    "fitplot": True,  # Adattamento immagine alla pagina
    "crop-to-fit": False,  # Ritaglio immagine per adattarla alla pagina
    "page-border": "None",  # Aggiunta di bordi
}
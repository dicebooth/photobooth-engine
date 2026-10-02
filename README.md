# Photobooth Engine

The **Photobooth Engine** is a python-based core service designed to capture images via connected digital cameras, apply customizable graphical frame overlays, manage photo workflows, and send finalized compositions to connected printers.

---

## Key Features

- **Automated Image Capture**: Integrates with digital cameras via standard `gphoto2` bindings and CLI interfaces.
- **Custom Frame Overlay**: Composes captured photos with custom PNG overlays/frames for events and installations.
- **Automated Printing Integration**: Interfaces with system print queues and hotfolders (e.g., CUPS / Gutenprint / DNP printers).
- **Flexible Configuration**: Configurable execution parameters, camera settings, and paths managed via standard YAML configuration files.
- **Backend & Cloud Sync Support**: Supports uploading metadata and photo assets to backend endpoints.

---

## Technical Prerequisites

### Operating System & Dependencies
- **OS**: Linux (Debian/Ubuntu-based distributions recommended)
- **Python**: Version `3.12` or higher
- **System Packages**:
  - `gphoto2` (for camera control and capture)
  - `cups` / `gutenprint` (for printer queue management)
- **Package/Environment manager**: [`uv`](https://docs.astral.sh/uv/)

### Supported Hardware
- **Camera**: Any `gphoto2`-compatible DSLR/Mirrorless camera connected via USB.
- **Printer**: Standard photo printer or sub-dye printer supported via CUPS, Gutenprint, or DNP Hotfolder.

---

## Installation & Setup

1. **Install System Dependencies**
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv gphoto2 cups
   ```

2. **Clone the Repository**
   ```bash
   git clone https://github.com/gdgbari/photobooth-engine.git
   cd photobooth
   ```

3. **Set Up the Python Environment** (with `uv`)
   ```bash
   uv sync
   ```

4. **Verify Hardware Connections**
   - **Camera Detection**:
     ```bash
     gphoto2 --auto-detect
     ```
   - **Printer Status**:
     ```bash
     lpstat -p -d
     ```

---

## Configuration

Before running the engine, create an active `settings.yaml` configuration file by duplicating the provided example template:

```bash
cp settings-example.yaml settings.yaml
```

Update `settings.yaml` with your event and environment details:

```yaml
# Folder and Event Settings
main_folder_path: "/path/to/photobooth_storage"
event_name: "TechConference2026"

# Camera & Capture Mode
cam_name: "Canon EOS Rebel T6" # Match exact output from 'gphoto2 --auto-detect'
camera_connection: "usb"
capture_mode: "camera"        # Options: 'camera' or 'pc'

# Printer Settings
printer_name: "DNP_DS620"     # Match exact queue name from 'lpstat -p'
print_size: "4x3"             # Options: '4x3' or '4x6'
enable_hotfolder: false
```

---

## Running the Engine

### 1. Standard Interactive Execution
To launch the main photobooth execution loop with active hardware (camera & printer):

```bash
uv run photobooth
```

or equivalently:

```bash
uv run python -m photobooth.main
```

Both commands must be run from the project root (the folder with `settings.yaml` and `Assets/`).
Alternatively you can point the application at another folder with the `PHOTOBOOTH_HOME` environment variable:

```bash
PHOTOBOOTH_HOME=/path/to/photobooth_home uv run photobooth
```

### 2. Development without hardware
Running the engine itself always requires real hardware (or the camera/printer
hotfolders). To develop and test without hardware, use the test suite: the
tests replace the camera and printer adapters with test doubles through
monkeypatching, so the whole session flow can be exercised on any machine
(see the Tests section below).

The same doubles are available as an interactive simulator, which runs the real
CLI session loop with a **simulated shot and a simulated print** (the sample
photo in `tests/assets/mock/` is used as every shot):

```bash
uv run python tests/run_simulated_session.py
```

Run it from the project root so the project `settings.yaml` and `Assets/` are
found. The simulator **never writes into the project root**: it builds a
dedicated home under `tests/simulated_output/home/` (its own `settings.yaml`,
`Assets/`, `user_data/` and `temp_data.yaml`) and keeps every "printed" photo in
`tests/simulated_output/`. Set `PHOTOBOOTH_HOME` to use a custom home instead
(then it is used as-is). Each simulated shot copies the sample photo into the
session folder; the printing queue starts after two photos are queued, so either
shoot twice or choose `2` copies in a single session to see the simulated print.
Exit with `Ctrl+C`.

### 3. Executing Utility Scripts

The engine includes specialized utility scripts under `scripts/`:

- **Camera Discovery**:
  ```bash
  uv run python scripts/list_cameras.py
  ```

- **Batch Image Editing / Framing**:
  ```bash
  uv run python scripts/bulk_edit.py
  ```

- **Merge Photos to 4x6 Layout**:
  ```bash
  uv run python scripts/merge_to_4x6.py
  ```

---

## Tests

The test suite runs with `pytest` (configured in `pyproject.toml`):

```bash
uv run pytest tests/ -v
```

- `tests/test_image_edit.py` — image editing/composition unit tests.
- `tests/test_session_flow.py` — end-to-end session flow with the camera and
  printer adapters replaced by monkeypatching, a scripted interaction and a
  temporary project home. The fake hardware is defined in
  `tests/simulated_hardware.py` and reused by the interactive simulator
  `tests/run_simulated_session.py`.
- `tests/test_backend.py` — backend integration test, disabled by default. It
  runs only when a backend is available on `localhost:8000` and explicitly
  enabled:

  ```bash
  PHOTOBOOTH_RUN_BACKEND_TESTS=1 uv run pytest tests/test_backend.py -v
  ```

---

## Project Structure

```
docs/
└── architecture.md           # Layered architecture and dependency rules
src/
└── photobooth/
    ├── main.py               # Composition root + entry point
    ├── consts.py             # Shared constants
    ├── api/                  # Adapters: camera (gphoto2/wifi), printer, backend, storage, platform
    ├── core/                 # Application logic: gateway, editor, queue, naming, frames, recovery
    ├── db/                   # Infrastructure: state persistence (temp_data.yaml)
    └── presentation/         # CLI (interaction + session) and future GUI
tests/                        # pytest suite
scripts/                      # Standalone processing scripts
Assets/                       # Graphical overlays and frames (only the sample frame is tracked)
settings-example.yaml         # Template settings file
settings.yaml                 # Active runtime configuration file (git-ignored)
```

### Architecture in one sentence

`presentation → core → api/db`: the CLI (or a future GUI) orchestrates a session
by calling only the `core.gateway.Gateway`, which never interacts with the user;
adapters in `api/` talk to cameras, printers, backend and filesystem, while
`db/state_store.py` is the single persistence point.
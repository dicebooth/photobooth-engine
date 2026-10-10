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
- **Python**: Version `3.8` or higher
- **System Packages**:
  - `gphoto2` (for camera control and capture)
  - `cups` / `gutenprint` (for printer queue management)

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
   git clone https://github.com/gdgbari/photobooth.git
   cd photobooth/engine
   ```

3. **Set Up Python Virtual Environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
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

Before running the engine, create a active `settings.yaml` configuration file by duplicating the provided example template:

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
capture_mode: "camera"        # Options: 'camera' or 'pc' (for mock/local testing)
mock_camera: false            # Set to true for hardware-free development

# Printer Settings
printer_name: "DNP_DS620"     # Match exact queue name from 'lpstat -p'
print_size: "4x3"             # Options: '4x3' or '4x6'
mock_printer: false           # Set to true to bypass physical printing
enable_hotfolder: false
```

---

## Running the Engine

### 1. Standard Interactive Execution
To launch the main photobooth execution loop with active hardware (camera & printer):

```bash
python3 photobooth/main.py
```

### 2. Development & Simulation Mode (Mock Hardware)
To run the engine locally for testing without physical camera or printer connected:

1. Enable mock options in `settings.yaml`:
   ```yaml
   mock_camera: true
   mock_printer: true
   capture_mode: "pc"
   ```
2. Execute the engine:
   ```bash
   python3 photobooth/main.py
   ```

### 3. Mobile Web Portal

The engine can start a mobile-first web portal to drive the photobooth from a smartphone connected to the **same local network**. It offers the same features of the desktop GUI: framed photo preview, approve/discard, number of copies selection and print (with a back button to undo the approval), plus a (hidden) gallery of the photos already taken, from which any photo can be reprinted.

Reprints use the framed photo as it is in `user_data/framed/`. Prints are made in pairs, so a single reprinted copy waits in the queue for the next photo.

1. Build the portal once (requires Node.js 18+):
   ```bash
   cd webapp
   npm install
   npm run build
   cd ..
   ```
2. Start the engine with the `--web` flag:
   ```bash
   python3 photobooth/main.py --web
   ```
   The terminal shows the portal address (IP and port) and a QR code to scan with the smartphone. The URL contains an access token, randomly generated at every start.

| Flag | Default | Description |
|------|---------|-------------|
| `--web` | off | Start the web portal |
| `--web-port` | `8080` | Portal port |
| `--web-host` | `0.0.0.0` | Address the portal binds to |
| `--web-token` | random | Fixed access token (useful to keep the same QR code across restarts) |
| `--web-http` | off | Serve plain HTTP instead of HTTPS (disables the QR scanner camera) |

If the page is opened without the token (e.g. from a bookmark or a home screen shortcut), the access screen offers a **Scansiona QR** button with a live in-page scanner (`@yudiel/react-qr-scanner`, decoder bundled so it works without internet).

Browsers expose the camera only on HTTPS, so the portal is served over HTTPS by default with a self-signed certificate, generated with `openssl` on first start and stored in `web-cert/`. The first time a phone opens the portal it shows a security warning to accept (on iPhone: *Show Details* → *visit this website*). Use `--web-http` to serve plain HTTP (the QR scanner is then disabled).

With `ui_mode: gui` the portal runs alongside the desktop GUI and both stay in sync (the first answer wins). With `ui_mode: cli` the portal replaces the terminal prompts.

To work on the portal UI, run the engine with `--web` and start the Vite dev server (it proxies the API to port 8080):
```bash
cd webapp && npm run dev
```

### 4. Executing Utility Scripts

The engine includes specialized utility scripts under `scripts/`:

- **Camera Discovery**:
  ```bash
  python3 scripts/list_cameras.py
  ```

- **Batch Image Editing / Framing**:
  ```bash
  python3 scripts/bulk_edit.py
  ```

- **Merge Photos to 4x6 Layout**:
  ```bash
  python3 scripts/merge_to_4x6.py
  ```

---

## Project Structure

```
engine/
├── assets/                 # Graphical overlays, backgrounds, and assets
├── photobooth/             # Engine core package
│   ├── core/               # Main runner logic and state management
│   ├── backend/            # API integration & uploads
│   ├── gui/                # Tkinter desktop GUI
│   ├── web/                # Mobile web portal server (HTTP API + SSE)
│   ├── main.py             # Application entry point
│   └── settings_manager.py # YAML configuration loader
├── scripts/                # Standalone processing scripts
├── webapp/                 # Mobile web portal UI (React + Vite)
├── settings-example.yaml   # Template settings file
└── settings.yaml           # Active runtime configuration file
```
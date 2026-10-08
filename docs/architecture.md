# Photobooth Engine — Architecture

## Layered structure

```
src/photobooth/
├── main.py                 # Composition root: wiring + CLI entry point
├── consts.py               # Shared constants (paths, defaults, sizes)
├── api/                    # Adapters to the outside world
│   ├── local_storage_api.py    # FolderManager (user_data tree), AssetManager (frames)
│   ├── printer_api.py          # Printer (lp/CUPS or DNP hotfolder)
│   ├── platform_api.py         # Platform, detect_os, camera_is_connected
│   ├── backend/                # Backend HTTP integration
│   │   ├── backend_api.py      # PhotoAPIClient (login, upload, download)
│   │   ├── backend_service.py  # BackendService (fire-and-forget upload)
│   │   └── logger.py           # setup_logging(log_file)
│   └── camera/                 # Camera adapters (gphoto2-agnostic)
│       ├── camera_api.py       # CameraAPI abstract interface
│       ├── gphoto2_camera.py   # USB driver (gphoto2)
│       ├── hotfolder_camera.py # WiFi driver (hotfolder polling)
│       └── camera_service.py   # Driver selection + single API for the core
├── core/                   # Application logic
│   ├── gateway.py              # Gateway: the only core entry point for presentation
│   ├── settings.py             # Settings (settings.yaml)
│   ├── editor_service.py       # EditorService (frame application, composition, padding)
│   ├── frame_chooser_service.py# Frame strategy (configured/single/random/manual)
│   ├── queue_service.py        # Photo/edit print queues logic
│   ├── naming_service.py       # Photo naming + session counter
│   └── disaster_recovery.py    # Pending session detection
├── db/                     # Infrastructure / persistence
│   └── state_store.py          # StateStore (temp_data.yaml: queues, session, wifi id)
└── presentation/           # User-facing layer
    ├── cli/
    │   ├── interaction_cli.py  # CliInteraction: prompts and previews only
    │   └── session_cli.py      # SessionCli: session orchestration via the gateway
    └── gui/                    # Placeholder for the future GUI
```

## Dependency rule

Dependencies only point downwards:

```
presentation  →  core  →  api / db
```

- **Presentation never bypasses the gateway.** `SessionCli` (or the future GUI
  controller) orchestrates a session by calling only `Gateway` methods, and
  delegates every prompt/preview to its interaction implementation
  (`CliInteraction`).
- **The core never talks to the user.** It has no `input()`, no previews, no
  knowledge of the CLI: every choice is a parameter, every output is a value.
- **The api layer never imports the core.** Adapters receive plain values
  (names, paths, options, booleans) from `main.py`; the only shared modules are
  `consts.py` and the persistence interfaces they are handed (for example the
  WiFi camera receives the `StateStore` instance to persist `last_read_wifi_id`).
- **db is infrastructure.** `StateStore` is the single persistence point of
  `temp_data.yaml`; services receive it, they never open state files directly.

## Session flow (CLI)

```
main.py (wiring)
  └── SessionCli.run()
        gateway.prepare()
        loop:
          SessionCli.main_execution()
            ├─ Gateway.pending_photos() / discard_pending_session()   # disaster recovery
            ├─ CliInteraction.ask_resume_session() / choose_pending_photo()
            ├─ Gateway.capture_hint()  →  CliInteraction hint
            ├─ Gateway.capture_photo()
            ├─ CliInteraction.confirm_shot()  →  Gateway.accept_capture() / reject_capture()
            │     (on reject: CliInteraction.notify_photo_rejected())
            ├─ Gateway.frame_strategy() / next_frame() / preview()
            ├─ CliInteraction.show_preview_image()  →  Gateway.abort_session()
            ├─ Gateway.send_to_backend()  (non blocking)
            ├─ CliInteraction.choose_times_to_print()
            ├─ Gateway.enqueue()
            └─ while Gateway.prints_pending(): Gateway.print_next()
```

## Configuration and paths

- `PHOTOBOOTH_HOME` (environment variable, default: current working directory)
  is resolved by `main.py` and points at the folder containing `settings.yaml`,
  `Assets/`, `temp_data.yaml` and the log file.
- Every component receives its paths from the composition root: `Settings(path)`,
  `StateStore(path)`, `AssetManager(assets_path)`,
  `setup_logging(log_file)`. Tests inject a temporary home and clean it up.
- Launch from the project root (as before): `uv run photobooth` or
  `uv run python -m photobooth.main`.

## Documented exceptions

- `presentation/cli/interaction_cli.py` imports `detect_os` from
  `photobooth.api.platform_api`: this is the **only** allowed exception to the
  `presentation → core` rule. Launching the OS image viewer is a presentation
  concern and it reuses the platform adapter already available in `api/`;
  injecting it through `main.py` was considered but discarded as overkill for a
  small, read-only helper.

## Utilities kept for future use

These are intentionally unused for now and are kept (not dead code to delete):

- `core/disaster_recovery.py::has_pending_session()` — not called yet; it is
  the boolean counterpart of `pending_photos()`.
- `Gateway.next_frame(photo_path)` — the `photo_path` parameter is currently
  ignored; it exists for symmetry with the other gateway calls and for future
  frame-per-photo logic.
- `FrameChooserService.DEFAULT_STRATEGY = 'random'` — historical behaviour: the
  `'manual'` strategy is reachable by passing `fallback_strategy='manual'` to
  the constructor (configuration of the strategy from settings is a possible
  future improvement).

## Known technical debt

- `api/backend/backend_api.py` duplicates the same upload/login flow for the
  async and sync variants (`upload_pil` / `upload_pil_sync`). This pre-dates
  the layered refactoring; a future cleanup could keep a single implementation
  with a thin async wrapper.
- `api/local_storage_api.py::AssetManager` assumes that the `Assets/` folder
  exists: a missing folder raises `FileNotFoundError` (from `os.listdir`).
  A folder without PNG files makes `is_frame_single()` return `False` and
  `get_corners_names()` return an empty list, so the `'random'` strategy
  reaches `FrameChooserService.next_frame_name` and raises `IndexError`.
  (`is_frame_single()` counts only PNG frames, so OS metadata files such as
  `.DS_Store` are ignored.)
- `api/camera/gphoto2_camera.py` `capture_via_camera`/`capture_via_pc` call
  themselves again on `GPhoto2Error` with no limit nor backoff: a persistent
  error can lead to unbounded recursion.
- `core/editor_service.py::EditorService._build_output_path` strips a fixed
  four-character extension (`[:-4]`): it assumes `.jpg`, so `.jpeg`/`.png`
  names would be truncated incorrectly.

## Platform notes

- `api/printer_api.py::Printer.get_printer_options` handles a missing
  `lpoptions` binary (e.g. macOS or non-CUPS environments) by catching
  `FileNotFoundError` and returning an error string, so `Printer.prepare()`
  degrades gracefully instead of crashing. This fix was developed and verified
  on Linux only; it could not be tested on macOS.

## Conventions

- `*_api.py` — adapters to external systems (in `api/`).
- `*_service.py` — application services (in `core/`, or `api/backend/` for the
  backend service which is only an orchestrator of the HTTP client).
- `interaction_cli.py` — prompt/render implementations;
  `session_cli.py` — the CLI session script.
- `Gateway` has no suffix: it is the core facade.

## Possible future improvements

- A `PHOTOBOOTH_HOME`-aware asset/settings migration to move configuration out
  of CWD entirely (the injection points already support it).
- An extra `api/` driver for a different camera library (only `camera_api.py`
  and `camera_service.py` would change).
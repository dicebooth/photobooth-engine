# Photobooth Engine — Architecture

## Layered structure

```
src/photobooth/
├── api/                            # Adapters to the outside world: ONE call to the outside per method
│   ├── platform_api.py             # Platform, detect_os
│   ├── backend/
│   │   └── backend.py              # PhotoAPIClient (login, upload of an encoded photo, download)
│   ├── camera/                     # Camera drivers (one attempt per call, raise CameraError)
│   │   ├── camera_factory.py       # build_camera(): driver selection factory
│   │   ├── gphoto2_camera.py       # USB driver (gphoto2)
│   │   └── hotfolder_camera.py     # WiFi driver (hotfolder polling and copy)
│   └── printing/                   # Print transports (raise PrinterError)
│       ├── cups_printer.py         # CupsPrinter (lp / lpoptions)
│       └── hotfolder_printer.py    # HotfolderPrinter (DNP hotfolder copy)
├── logic/                          # Everything that decides or transforms, one package per theme
│   ├── capture/
│   │   ├── ports.py                # CameraPort, PhotoIdStatePort, CameraError
│   │   ├── capture_service.py      # CaptureService: hints, shots, infinite re-init/retry loop
│   │   └── photo_id_sequencer.py   # PhotoIdSequencer: which hotfolder photo is the next one
│   ├── frames/
│   │   ├── frame_catalog.py        # FrameCatalog: frames available in Assets/
│   │   ├── frame_compositor.py     # FrameCompositor: photo inside a frame
│   │   └── frame_service.py        # FrameService: strategy, next frame, preview
│   ├── editing/
│   │   ├── ports.py                # NamingStatePort
│   │   ├── editor_service.py       # EditorService: two framed photos -> one 4x6 sheet
│   │   ├── photo_encoder.py        # PhotoEncoder: image mode normalization + PNG base64
│   │   └── naming_service.py       # NamingService: photo naming + session counter
│   ├── printing/
│   │   ├── ports.py                # PrinterPort, QueueStatePort, PrinterError
│   │   ├── print_options_resolver.py  # PrintOptionsResolver: which lp options to use
│   │   ├── print_service.py        # PrintService: queue + print, returns PrintResult
│   │   └── queue_service.py        # QueueService: photo/edit print queues
│   ├── uploads/
│   │   ├── ports.py                # BackendPort, BackendUnavailable
│   │   ├── upload_service.py       # UploadService: background upload, infinite retry
│   │   └── logger.py               # setup_logging(log_file)
│   ├── session/
│   │   ├── folder_manager.py       # FolderManager: user_data/{current,originals,output}
│   │   ├── originals_archiver.py   # OriginalsArchiver: current -> originals
│   │   └── recovery_service.py     # RecoveryService: disaster recovery
│   └── settings/
│       ├── settings.py             # Settings: reads settings.yaml once
│       └── settings_models.py      # Storage/Capture/Frame/Print/Upload/InteractionSettings
├── db/                             # Infrastructure / persistence
│   └── state_store.py              # StateStore (temp_data.yaml: queues, session, wifi id)
├── presentation/                   # User-facing layer
│   ├── cli/                        # Command line interface
│   │   ├── interaction_cli.py      # CliInteraction: prompts and previews only
│   │   └── session_cli.py          # SessionCli: session orchestration via the services
│   └── gui/                        # Placeholder for the future GUI
├── main.py                         # Composition root: wiring + CLI entry point
└── consts.py                       # Shared constants (paths, defaults, sizes)
```

## Dependency rule

```
presentation  →  logic  ←  api
                   ↑
                  db
```

- **`logic` imports nothing from `api`, `db` or `presentation`.** It declares
  what it needs from the outside as `typing.Protocol` ports (`ports.py` inside
  the theme that uses it: `CameraPort`, `PrinterPort`, `BackendPort`,
  `QueueStatePort`, ...). `api` and `db` implement them structurally.
- **`api` only does I/O.** Each method makes one call to the outside world
  (one HTTP request, one `lp`, one gphoto2 shot, one hotfolder read) and takes
  or returns primitives. It has no retry policy, no image conversion, no
  domain message: it raises the typed errors defined in the ports
  (`CameraError`, `PrinterError`, `BackendUnavailable`). It imports `logic` only
  for those ports and exceptions (and `PhotoIdSequencer`, handed to the WiFi
  driver).
- **`presentation` never imports `api` or `db`.** `main.py` hands it what it
  needs (for example the `Platform` detected by `detect_os()`).
- **The logic layer never talks to the user.** No `input()`, no `print()`, no
  previews: every choice is a parameter, every output is a value
  (`PrintResult`) or a log message.
- **`SessionCli` orchestrates the services directly**: there is no facade.
  Each service has a single theme and few collaborators.
- **db is infrastructure.** `StateStore` is the single persistence point of
  `temp_data.yaml`; services receive it, they never open state files directly.

## Policies worth knowing

- **Camera:** drivers make one attempt. `CaptureService` keeps re-initializing
  and retrying forever (pause: `camera_retry_delay_sec`, default 2s) until it
  succeeds or `request_stop()` is called; `SessionCli.run()` does it on Ctrl+C.
- **Upload:** `UploadService` encodes the photo once and uploads it from a
  daemon thread, retrying forever every 5 seconds while the backend is
  unreachable (`BackendUnavailable`). Any other error is logged and final.
- **Print options** (`PrintOptionsResolver`): QW410 + `4x3` → `media=dnp4x6
  Cutter=2Inch`; otherwise the `printer_options` of `settings.yaml`; otherwise
  the first fit-to-page option reported by the printer.
- **Print queue:** it survives restarts on purpose (loaded in `prepare()`).

## Session flow (CLI)

```
main.py (wiring: build_services + build_session)
  └── SessionCli.run()
        capture.prepare() / printing.prepare()
        loop (until Ctrl+C):
          SessionCli.main_execution()
            ├─ RecoveryService.pending_photos() / discard_pending()      # disaster recovery
            ├─ CliInteraction.ask_resume_session() / choose_pending_photo()
            ├─ CaptureService.hint()  →  CliInteraction hint
            ├─ CaptureService.capture()
            ├─ CliInteraction.confirm_shot()  →  CaptureService.accept() / reject()
            │     (on reject: CliInteraction.notify_photo_rejected())
            ├─ FrameService.strategy() / next_frame_name() / compose()
            ├─ CliInteraction.show_preview_image()  →  OriginalsArchiver.archive_current() on refusal
            ├─ UploadService.send_photo()  (non blocking)
            ├─ CliInteraction.choose_times_to_print()
            ├─ OriginalsArchiver.archive_current()  →  PrintService.enqueue()
            └─ while PrintService.prints_pending(): CliInteraction.show_print_result(print_next())
```

## Configuration and paths

- `PHOTOBOOTH_HOME` (environment variable, default: current working directory)
  is resolved by `main.py` and points at the folder containing `settings.yaml`,
  `Assets/`, `temp_data.yaml` and the log file.
- Every component receives its paths from the composition root: `Settings(path)`,
  `StateStore(path)`, `FrameCatalog(frames_path)`, `setup_logging(log_file)`.
  Tests inject a temporary home and clean it up.
- `Settings` is read once and exposed as typed slices (`settings.capture`,
  `settings.printing`, ...): each service receives only the slice it needs.
- Launch from the project root (as before): `uv run photobooth` or
  `uv run python -m photobooth.main`.

## Known technical debt

- `FrameCatalog` assumes that the `Assets/` folder exists: a missing folder
  raises `FileNotFoundError` (from `os.listdir`). A folder without PNG files
  makes `is_single()` return `False` and `names()` return an empty list, so the
  `'random'` strategy reaches `FrameService.next_frame_name` and raises
  `IndexError`.
- `FrameService.DEFAULT_STRATEGY = 'random'`: the `'manual'` strategy is
  reachable by passing `fallback_strategy='manual'` to the constructor
  (configuring it from settings is a possible future improvement).
- `HotfolderCamera` polls and waits for the file transfer in a loop: waiting is
  I/O, but a bounded wait with a stop flag would be cleaner.

## Platform notes

- `api/platform_api.py` keeps the small `Platform` class (with `is_linux()`,
  `is_wsl()`, `is_macos()`) instead of exposing raw `sys.platform ==
  'darwin'`-style checks at the call sites. The photobooth is a multi-platform
  system and WSL detection needs `platform.release()`, so it is not expressible
  with `sys.platform` alone. `main.py` injects the detected `Platform` into
  `CliInteraction`.
- `CupsPrinter.supported_options` handles a missing `lpoptions` binary (e.g.
  macOS or non-CUPS environments) by returning an empty listing, so
  `PrintService.prepare()` degrades gracefully instead of crashing. This was
  developed and verified on Linux only; it could not be tested on macOS.

## Conventions

- `*_api.py` — entry points to external systems in `api/` (`platform_api.py`);
  drivers and transports are named after what they drive (`CupsPrinter`).
- `*_service.py` — application services (in `logic/`).
- `ports.py` — the Protocols and typed errors a theme needs from the outside.
- `interaction_cli.py` — prompt/render implementations;
  `session_cli.py` — the CLI session script.

## Possible future improvements

- A `PHOTOBOOTH_HOME`-aware asset/settings migration to move configuration out
  of CWD entirely (the injection points already support it).
- An extra `api/camera` driver for a different camera library: only a new
  driver and `camera_factory.py` change.

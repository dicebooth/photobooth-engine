"""
Interactive simulator: runs the whole photobooth (real CLI session loop) with the
camera and the printer replaced by test doubles, so a full session can be
exercised without any hardware.

Usage (from the project root):
    uv run python tests/run_simulated_session.py

Run it from the project root (or set PHOTOBOOTH_HOME) so settings.yaml and
Assets/ are found. Every "shot" is the sample photo in tests/assets/mock, every
"print" is kept in tests/simulated_output/. Exit with Ctrl+C.
"""

import os
import shutil
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC_DIR = os.path.join(PROJECT_ROOT, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from photobooth import consts
from photobooth.core.settings import Settings
from photobooth.main import build_gateway, resolve_home
from photobooth.presentation.cli.interaction_cli import CliInteraction
from photobooth.presentation.cli.session_cli import SessionCli

import simulated_hardware

OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'tests', 'simulated_output')


def _ensure_frame(home: str):
    """
    Method which makes sure at least one frame is available in the Assets
    folder, so the simulated session can apply an effect out of the box.
    :param home: project home folder
    """

    assets_dir = os.path.join(home, consts.ASSETS_DIRNAME)
    os.makedirs(assets_dir, exist_ok=True)
    frames = [f for f in os.listdir(assets_dir) if f.lower().endswith('.png')]
    if not frames:
        shutil.copyfile(simulated_hardware.SAMPLE_FRAME, os.path.join(assets_dir, 'frame1.png'))
        print(f"[SIMULATED SETUP] Added a sample frame to {assets_dir}")


def simulated_print(file_path: str):
    """
    Method which simulates the print of a photo: the edited file is copied to the
    simulated output folder instead of being sent to a real printer.
    :param file_path: path of the edited photo to "print"
    """

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    target = os.path.join(OUTPUT_DIR, os.path.basename(file_path))
    shutil.copyfile(file_path, target)
    print(f"[SIMULATED PRINT] {file_path} -> {target}")


def main():
    """
    This is the entry point of the simulator: it installs the fake hardware and
    starts the real interactive CLI session loop.
    """

    home = resolve_home()  # PHOTOBOOTH_HOME, defaults to the current working directory
    _ensure_frame(home)

    # Monkey patching: swap the real camera and printer adapters with test doubles
    simulated_hardware.patch_camera(setattr)
    simulated_hardware.patch_printer(setattr, simulated_print)

    settings = Settings(os.path.join(home, consts.SETTINGS_FILENAME))
    gateway = build_gateway(home, settings)

    # No backend in simulation: log the upload instead of sending it
    gateway.send_to_backend = lambda photo_path, frame_name: print(
        f"[SIMULATED UPLOAD] {os.path.basename(photo_path)} frame={frame_name}")

    session = SessionCli(gateway, CliInteraction(settings))
    print(f"Simulated photobooth started (home: {home}). Exit with Ctrl+C.")
    try:
        session.run()
    except KeyboardInterrupt:
        gateway.final_cleaning()
        print('\nSimulation stopped.')


if __name__ == '__main__':
    main()

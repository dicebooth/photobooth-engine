"""
Interactive simulator: runs the whole photobooth (real CLI session loop) with the
camera and the printer replaced by test doubles, so a full session can be
exercised without any hardware.

Usage (from the project root):
    uv run python tests/run_simulated_session.py

By default the simulator never writes into the project root: it builds a
dedicated home under tests/simulated_output/home (settings.yaml, Assets,
user_data and temp_data.yaml all live there) and keeps the "printed" photos in
tests/simulated_output/. The simulation settings are derived from the project
settings.yaml, only main_folder_path is redirected to the simulation home.
Set PHOTOBOOTH_HOME to use a custom home instead: it is then used as-is.

Every "shot" is the sample photo in tests/assets/mock. Exit with Ctrl+C.
"""

import os
import shutil
import sys

import yaml

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC_DIR = os.path.join(PROJECT_ROOT, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from photobooth import consts
from photobooth.core.settings import Settings
from photobooth.main import build_gateway
from photobooth.presentation.cli.interaction_cli import CliInteraction
from photobooth.presentation.cli.session_cli import SessionCli

import simulated_hardware

OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'tests', 'simulated_output')
DEFAULT_SIM_HOME = os.path.join(OUTPUT_DIR, 'home')


def _ensure_frame(source_home: str, sim_home: str):
    """
    Method which makes sure at least one frame is available in the simulation
    Assets folder: it copies the project frames when present, otherwise it falls
    back to the sample frame shipped with the tests.
    :param source_home: project home the Assets are read from
    :param sim_home: dedicated simulation home
    """

    source_assets = os.path.join(source_home, consts.ASSETS_DIRNAME)
    sim_assets = os.path.join(sim_home, consts.ASSETS_DIRNAME)
    os.makedirs(sim_assets, exist_ok=True)

    frames = []
    if os.path.isdir(source_assets):
        frames = sorted(f for f in os.listdir(source_assets) if f.lower().endswith('.png'))

    if not frames:
        shutil.copyfile(simulated_hardware.SAMPLE_FRAME, os.path.join(sim_assets, 'frame1.png'))
        print(f"[SIMULATED SETUP] Added a sample frame to {sim_assets}")
        return

    for frame in frames:
        shutil.copyfile(os.path.join(source_assets, frame), os.path.join(sim_assets, frame))


def _prepare_sim_home(source_home: str, sim_home: str):
    """
    Method which builds the dedicated simulation home: it derives settings.yaml
    from the project one (only main_folder_path is redirected) and prepares its
    Assets folder. The project root is never written to.
    :param source_home: project home the settings/Assets are read from
    :param sim_home: dedicated simulation home to create/refresh
    """

    source_settings = os.path.join(source_home, consts.SETTINGS_FILENAME)
    if not os.path.exists(source_settings):
        raise FileNotFoundError(
            f"No {consts.SETTINGS_FILENAME} found in '{source_home}': "
            f"copy settings-example.yaml there before running the simulator."
        )

    with open(source_settings, 'r') as settings_file:
        settings_data = yaml.safe_load(settings_file) or {}
    settings_data['main_folder_path'] = sim_home

    os.makedirs(sim_home, exist_ok=True)
    with open(os.path.join(sim_home, consts.SETTINGS_FILENAME), 'w') as settings_file:
        yaml.dump(settings_data, settings_file, default_flow_style=False, allow_unicode=True)

    _ensure_frame(source_home, sim_home)
    print(f"[SIMULATED SETUP] Simulation home ready: {sim_home}")


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

    override_home = os.environ.get(consts.PHOTOBOOTH_HOME_ENV)
    if override_home:
        # explicit override: settings are used as-is, only a frame is guaranteed
        home = override_home
        if not os.path.exists(os.path.join(home, consts.SETTINGS_FILENAME)):
            print(f"Error: no {consts.SETTINGS_FILENAME} found in '{home}'. "
                  f"Copy settings-example.yaml there or run without {consts.PHOTOBOOTH_HOME_ENV}.")
            sys.exit(1)
        _ensure_frame(PROJECT_ROOT, home)
    else:
        home = DEFAULT_SIM_HOME
        _prepare_sim_home(PROJECT_ROOT, home)

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

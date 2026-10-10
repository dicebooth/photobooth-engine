import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from photobooth.core.runner import Runner
from photobooth.settings_manager import Settings

"""
This is the main entry point of the application.
It initializes the Runner class and consequently the necessary management instances.
At the end starts the main execution loop according to ui_mode in settings.yaml.
With --web a mobile web portal is started alongside the selected UI.
"""


def parse_args():
    parser = argparse.ArgumentParser(description="Photobooth Engine")
    parser.add_argument('--web', action='store_true',
                        help="start the mobile web portal, reachable from devices on the same local network")
    parser.add_argument('--web-host', default='0.0.0.0', help="address the web portal binds to (default: 0.0.0.0)")
    parser.add_argument('--web-port', type=int, default=8080, help="web portal port (default: 8080)")
    parser.add_argument('--web-token', default=None,
                        help="web portal access token (default: randomly generated at every start)")
    parser.add_argument('--web-http', action='store_true',
                        help="serve the web portal over plain HTTP (the QR scanner camera requires HTTPS)")
    return parser.parse_args()


def main():
    args = parse_args()
    settings = Settings()
    ui_mode = settings.get_ui_mode()

    if ui_mode == "gui":
        import tkinter as tk
        import threading
        from photobooth.gui.photobooth_gui import PhotoboothGUI, GUIUserInterface
        from photobooth.core.folder_manager import AssetManager

        root = tk.Tk()
        assets = AssetManager()
        gui = PhotoboothGUI(root, assets.get_corners_names())
        gui_adapter = GUIUserInterface(gui, assets.get_corners_names())

        if args.web:
            from photobooth.web import setup_web_portal
            gui_adapter = setup_web_portal(assets.get_corners_names(), args.web_host, args.web_port, args.web_token,
                                           https=not args.web_http, delegate=gui_adapter, gui=gui)

        runner = Runner(gui_adapter=gui_adapter)
        if args.web:
            gui_adapter.set_reprint_handler(runner.reprint)
        runner.prepare()

        def engine_thread_func():
            while runner.keep_going():
                try:
                    runner.main_execution()
                except Exception as e:
                    print(f"Error in engine main execution loop: {e}")
                    break

        engine_thread = threading.Thread(target=engine_thread_func, daemon=True)
        engine_thread.start()

        root.mainloop()
    else:
        ui_adapter = None
        if args.web:
            # in cli mode the portal replaces the terminal prompts
            from photobooth.web import setup_web_portal
            from photobooth.core.folder_manager import AssetManager
            ui_adapter = setup_web_portal(AssetManager().get_corners_names(), args.web_host, args.web_port,
                                          args.web_token, https=not args.web_http)

        runner = Runner(gui_adapter=ui_adapter)
        if ui_adapter is not None:
            ui_adapter.set_reprint_handler(runner.reprint)
        runner.prepare()
        while runner.keep_going():
            runner.main_execution()


if __name__ == '__main__':
    main()

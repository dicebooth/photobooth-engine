import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from photobooth.core.runner import Runner
from photobooth.settings_manager import Settings

"""
This is the main entry point of the application.
It initializes the Runner class and consequently the necessary management instances.
At the end starts the main execution loop according to ui_mode in settings.yaml.
"""


def main():
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

        runner = Runner(gui_adapter=gui_adapter)
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
        runner = Runner()
        runner.prepare()
        while runner.keep_going():
            runner.main_execution()


if __name__ == '__main__':
    main()


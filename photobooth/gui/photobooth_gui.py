"""
Photobooth GUI module using Tkinter.
"""
import tkinter as tk
from tkinter import ttk
import os
import threading
import queue
from PIL import Image, ImageTk

from photobooth.settings_manager import Settings
from photobooth.utils import camera_is_connected


class PhotoboothGUI:
    """
    Graphical User Interface for the Photobooth Engine.
    Provides camera and printer status indicators, last photo preview,
    photo approval/rejection controls, copy count selector, and a bottom gallery carousel.
    """

    def __init__(self, root: tk.Tk, effect_list: list = None):
        self.root = root
        self.root.title("Photobooth Engine")
        self.root.geometry("1024x720")
        self.root.minsize(850, 600)

        self._settings = Settings()
        self.effect_list = effect_list or []

        # Inter-thread communication queues
        self.action_queue = queue.Queue()
        self.response_queue = queue.Queue()

        # Internal state variables
        self.camera_connected = False
        self.printer_connected = False
        self.current_photo_path = None
        self._photo_image_ref = None

        # Carousel photo gallery list: stores items as (image_or_path, thumbnail_photo_ref)
        self.gallery_items = []
        self.selected_item_index = None

        # Build UI layout
        self._setup_styles()
        self._build_header()
        self._build_main_area()
        self._build_carousel()
        self._build_statusbar()

        # Start background hardware status checker
        self._start_status_checker()

        # Load existing framed photos from user_data/framed folder
        self._load_existing_framed_photos()

    def _load_existing_framed_photos(self):
        try:
            from photobooth.core.folder_manager import FolderManager
            folder_mgr = FolderManager(self._settings.get_main_folder_path())
            framed_dir = folder_mgr.get_framed_photos_path()
            if os.path.exists(framed_dir):
                files = [f for f in os.listdir(framed_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                import re
                def natural_sort_key(s):
                    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
                files.sort(key=natural_sort_key)

                # Add files so newest (last sorted) ends up at index 0 on left
                for f in files:
                    full_p = os.path.join(framed_dir, f)
                    self.add_photo_to_carousel(full_p)
        except Exception as e:
            print(f"Error loading existing framed photos into carousel: {e}")


    def _setup_styles(self):
        self.root.configure(bg="#1E1E24")
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.style.configure("Header.TFrame", background="#121216")
        self.style.configure("Main.TFrame", background="#1E1E24")
        self.style.configure("Sidebar.TFrame", background="#282830")
        self.style.configure("Carousel.TFrame", background="#18181F")

        self.style.configure("Title.TLabel", background="#121216", foreground="#FFFFFF", font=("Helvetica", 16, "bold"))
        self.style.configure("HeaderStatus.TLabel", background="#121216", foreground="#E0E0E0", font=("Helvetica", 11))
        self.style.configure("Section.TLabel", background="#282830", foreground="#FFFFFF", font=("Helvetica", 13, "bold"))
        self.style.configure("Sidebar.TLabel", background="#282830", foreground="#B0B0C0", font=("Helvetica", 11))

        self.style.configure("Approve.TButton", font=("Helvetica", 12, "bold"), background="#2E7D32", foreground="#FFFFFF")
        self.style.map("Approve.TButton", background=[("active", "#388E3C"), ("disabled", "#1B3E1E")])

        self.style.configure("Reject.TButton", font=("Helvetica", 12, "bold"), background="#C62828", foreground="#FFFFFF")
        self.style.map("Reject.TButton", background=[("active", "#D32F2F"), ("disabled", "#5C1313")])

        self.style.configure("Print.TButton", font=("Helvetica", 12, "bold"), background="#0288D1", foreground="#FFFFFF")
        self.style.map("Print.TButton", background=[("active", "#039BE5"), ("disabled", "#01456B")])

    def _build_header(self):
        header = ttk.Frame(self.root, style="Header.TFrame", padding=(16, 12))
        header.pack(side=tk.TOP, fill=tk.X)

        title_lbl = ttk.Label(header, text="PHOTOBOOTH ENGINE", style="Title.TLabel")
        title_lbl.pack(side=tk.LEFT)

        indicators_frame = ttk.Frame(header, style="Header.TFrame")
        indicators_frame.pack(side=tk.RIGHT)

        # Camera Indicator
        self.cam_indicator = tk.Canvas(indicators_frame, width=16, height=16, bg="#121216", highlightthickness=0)
        self.cam_indicator.pack(side=tk.LEFT, padx=(0, 6))
        self.cam_dot = self.cam_indicator.create_oval(2, 2, 14, 14, fill="#D32F2F", outline="")

        cam_text = ttk.Label(indicators_frame, text="Fotocamera", style="HeaderStatus.TLabel")
        cam_text.pack(side=tk.LEFT, padx=(0, 20))

        # Printer Indicator
        self.print_indicator = tk.Canvas(indicators_frame, width=16, height=16, bg="#121216", highlightthickness=0)
        self.print_indicator.pack(side=tk.LEFT, padx=(0, 6))
        self.print_dot = self.print_indicator.create_oval(2, 2, 14, 14, fill="#D32F2F", outline="")

        print_text = ttk.Label(indicators_frame, text="Stampante", style="HeaderStatus.TLabel")
        print_text.pack(side=tk.LEFT)

    def _build_main_area(self):
        main_frame = ttk.Frame(self.root, style="Main.TFrame", padding=12)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Left Panel: Image Preview
        left_panel = ttk.Frame(main_frame, style="Main.TFrame")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        preview_title = ttk.Label(left_panel, text="Anteprima Foto", font=("Helvetica", 14, "bold"), background="#1E1E24", foreground="#FFFFFF")
        preview_title.pack(side=tk.TOP, anchor=tk.W, pady=(0, 8))

        self.preview_container = tk.Frame(left_panel, bg="#101014", bd=2, relief=tk.SUNKEN)
        self.preview_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.preview_container.bind("<Configure>", self._on_preview_resize)

        self.preview_label = tk.Label(self.preview_container, bg="#101014", text="Nessuna foto da mostrare", fg="#606070", font=("Helvetica", 13))
        self.preview_label.pack(fill=tk.BOTH, expand=True)

        # Right Panel: Sidebar Controls
        sidebar = ttk.Frame(main_frame, style="Sidebar.TFrame", width=280, padding=16)
        sidebar.pack(side=tk.RIGHT, fill=tk.Y)
        sidebar.pack_propagate(False)

        side_title = ttk.Label(sidebar, text="Controlli", style="Section.TLabel")
        side_title.pack(side=tk.TOP, anchor=tk.W, pady=(0, 16))

        # Photo Decision Section
        decision_label = ttk.Label(sidebar, text="Approvazione Foto", style="Sidebar.TLabel")
        decision_label.pack(side=tk.TOP, anchor=tk.W, pady=(8, 4))

        self.btn_approve = ttk.Button(sidebar, text="✔ Approva (Y)", style="Approve.TButton", state=tk.DISABLED, command=self._on_approve)
        self.btn_approve.pack(side=tk.TOP, fill=tk.X, pady=4, ipady=6)

        self.btn_reject = ttk.Button(sidebar, text="✖ Scarta (N)", style="Reject.TButton", state=tk.DISABLED, command=self._on_reject)
        self.btn_reject.pack(side=tk.TOP, fill=tk.X, pady=4, ipady=6)

        ttk.Separator(sidebar, orient=tk.HORIZONTAL).pack(side=tk.TOP, fill=tk.X, pady=16)

        # Print Copies Section
        copies_label = ttk.Label(sidebar, text="Numero Copie da Stampare", style="Sidebar.TLabel")
        copies_label.pack(side=tk.TOP, anchor=tk.W, pady=(8, 4))

        copies_frame = ttk.Frame(sidebar, style="Sidebar.TFrame")
        copies_frame.pack(side=tk.TOP, fill=tk.X, pady=4)

        min_copies = self._settings.get_min_num_photos()
        max_copies = self._settings.get_max_num_photos()

        self.spin_copies = tk.Spinbox(copies_frame, from_=min_copies, to=max_copies, font=("Helvetica", 14), width=6, state="disabled", justify=tk.CENTER)
        self.spin_copies.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_confirm_copies = ttk.Button(sidebar, text="🖨 Conferma Stampa", style="Print.TButton", state=tk.DISABLED, command=self._on_confirm_copies)
        self.btn_confirm_copies.pack(side=tk.TOP, fill=tk.X, pady=(8, 4), ipady=6)

        ttk.Separator(sidebar, orient=tk.HORIZONTAL).pack(side=tk.TOP, fill=tk.X, pady=16)

        # Status / Instructions Info Box
        self.info_lbl = ttk.Label(sidebar, text="In attesa di scatto...", style="Sidebar.TLabel", wraplength=240)
        self.info_lbl.pack(side=tk.TOP, anchor=tk.W)

    def _build_carousel(self):
        self.carousel_container = ttk.Frame(self.root, style="Carousel.TFrame", padding=(12, 4))
        self.carousel_container.pack(side=tk.TOP, fill=tk.X)

        header_frame = ttk.Frame(self.carousel_container, style="Carousel.TFrame")
        header_frame.pack(side=tk.TOP, fill=tk.X)

        lbl = ttk.Label(header_frame, text="Galleria Scatti", font=("Helvetica", 10, "bold"), background="#18181F", foreground="#A0A0B0")
        lbl.pack(side=tk.LEFT)

        # Toggle Button (Center Arrow)
        self.carousel_expanded = False
        self.btn_toggle_carousel = tk.Button(
            header_frame,
            text="▲",
            font=("Helvetica", 11, "bold"),
            bg="#18181F",
            fg="#F57C00",
            activebackground="#282830",
            activeforeground="#FF9800",
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            command=self._toggle_carousel
        )
        self.btn_toggle_carousel.pack(side=tk.TOP, anchor=tk.CENTER)

        # Body frame containing scrollable canvas and scrollbar (collapsed by default)
        self.carousel_body = ttk.Frame(self.carousel_container, style="Carousel.TFrame")


        # Horizontal Scrollable Canvas
        self.carousel_canvas = tk.Canvas(self.carousel_body, height=95, bg="#18181F", highlightthickness=0)
        self.carousel_canvas.pack(side=tk.TOP, fill=tk.X, expand=True)

        self.carousel_scrollbar = ttk.Scrollbar(self.carousel_body, orient=tk.HORIZONTAL, command=self.carousel_canvas.xview)
        self.carousel_canvas.configure(xscrollcommand=self.carousel_scrollbar.set)
        self.carousel_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.carousel_inner = tk.Frame(self.carousel_canvas, bg="#18181F")
        self.carousel_canvas.create_window((0, 0), window=self.carousel_inner, anchor=tk.NW)

        self.carousel_inner.bind("<Configure>", lambda e: self.carousel_canvas.configure(scrollregion=self.carousel_canvas.bbox("all")))

    def _toggle_carousel(self):
        if self.carousel_expanded:
            self.carousel_body.pack_forget()
            self.btn_toggle_carousel.config(text="▲")
            self.carousel_expanded = False
        else:
            self.carousel_body.pack(side=tk.TOP, fill=tk.X, expand=True, pady=(4, 0))
            self.btn_toggle_carousel.config(text="▼")
            self.carousel_expanded = True


    def _build_statusbar(self):
        statusbar = ttk.Frame(self.root, style="Header.TFrame", padding=(12, 4))
        statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_text = ttk.Label(statusbar, text="Pronto", style="HeaderStatus.TLabel")
        self.status_text.pack(side=tk.LEFT)

    def add_photo_to_carousel(self, image_or_path):
        """
        Adds a new photo to the carousel at the leftmost position (index 0) and selects it automatically.
        """
        try:
            if isinstance(image_or_path, str) and os.path.exists(image_or_path):
                img = Image.open(image_or_path)
            elif isinstance(image_or_path, Image.Image):
                img = image_or_path
            else:
                return
        except Exception as e:
            print(f"Error loading carousel thumbnail: {e}")
            return

        # Generate 80x80 thumbnail
        thumb_img = img.copy()
        thumb_img.thumbnail((80, 80), Image.Resampling.LANCZOS)
        thumb_photo = ImageTk.PhotoImage(thumb_img)

        item = {
            "image_or_path": image_or_path,
            "thumb_photo": thumb_photo,
            "widget_frame": None,
            "label": None
        }

        # Insert at top/left (index 0)
        self.gallery_items.insert(0, item)
        self._rebuild_carousel_widgets()
        self.select_carousel_item(0)

    def _rebuild_carousel_widgets(self):
        for child in self.carousel_inner.winfo_children():
            child.destroy()

        for idx, item in enumerate(self.gallery_items):
            frame = tk.Frame(self.carousel_inner, bg="#282830", bd=2, relief=tk.RAISED, cursor="hand2")
            frame.pack(side=tk.LEFT, padx=4, pady=2)

            lbl = tk.Label(frame, image=item["thumb_photo"], bg="#101014")
            lbl.pack(fill=tk.BOTH, expand=True)

            item["widget_frame"] = frame
            item["label"] = lbl

            # Bind click events
            frame.bind("<Button-1>", lambda e, index=idx: self.select_carousel_item(index))
            lbl.bind("<Button-1>", lambda e, index=idx: self.select_carousel_item(index))

    def select_carousel_item(self, index: int):
        if not self.gallery_items or index < 0 or index >= len(self.gallery_items):
            return

        self.selected_item_index = index

        # Highlight selected thumbnail with yellow border
        for idx, item in enumerate(self.gallery_items):
            if idx == index:
                item["widget_frame"].config(bg="#F57C00", bd=3)
            else:
                item["widget_frame"].config(bg="#282830", bd=2)

        # Display preview of selected item
        selected_item = self.gallery_items[index]
        self.show_preview(selected_item["image_or_path"])

    def set_status_message(self, text: str):
        self.status_text.config(text=text)

    def update_camera_status(self, connected: bool):
        self.camera_connected = connected
        color = "#388E3C" if connected else "#D32F2F"
        self.cam_indicator.itemconfig(self.cam_dot, fill=color)

    def update_printer_status(self, connected: bool):
        self.printer_connected = connected
        color = "#388E3C" if connected else "#D32F2F"
        self.print_indicator.itemconfig(self.print_dot, fill=color)

    def _start_status_checker(self):
        def check_loop():
            cam_ok = self._settings.get_mock_camera() or self._settings.get_camera_connection() == 'wifi' or camera_is_connected(self._settings)
            printer_ok = True
            if not self._settings.get_mock_printer():
                if self._settings.get_enable_hotfolder():
                    hp = self._settings.get_printer_hotfolder_path()
                    printer_ok = bool(hp and os.path.exists(hp))
                else:
                    printer_name = self._settings.get_printer_name()
                    try:
                        import subprocess
                        res = subprocess.run(["lpstat", "-p", printer_name], capture_output=True, text=True)
                        printer_ok = res.returncode == 0
                    except Exception:
                        printer_ok = True

            self.root.after(0, lambda: self.update_camera_status(cam_ok))
            self.root.after(0, lambda: self.update_printer_status(printer_ok))

        threading.Thread(target=check_loop, daemon=True).start()

    def show_preview(self, image_or_path):
        if isinstance(image_or_path, str) and os.path.exists(image_or_path):
            self.current_photo_path = image_or_path
            try:
                img = Image.open(image_or_path)
            except Exception as e:
                print(f"Error loading image preview: {e}")
                return
        elif isinstance(image_or_path, Image.Image):
            img = image_or_path
            self.current_photo_path = None
        else:
            return

        self._current_pil_img = img.copy()
        self._render_preview()

    def _on_preview_resize(self, event):
        if hasattr(self, '_current_pil_img') and self._current_pil_img:
            self._render_preview()

    def _render_preview(self):
        if not hasattr(self, '_current_pil_img') or not self._current_pil_img:
            return

        w = self.preview_container.winfo_width()
        h = self.preview_container.winfo_height()

        if w <= 10 or h <= 10:
            w, h = 600, 450

        img = self._current_pil_img.copy()
        img.thumbnail((w - 8, h - 8), Image.Resampling.LANCZOS)

        photo = ImageTk.PhotoImage(img)
        self._photo_image_ref = photo
        self.preview_label.config(image=photo, text="")

    def enable_approval(self):
        self.btn_approve.config(state=tk.NORMAL)
        self.btn_reject.config(state=tk.NORMAL)
        self.info_lbl.config(text="Approva o scarta la foto scattata.")
        self.set_status_message("In attesa di approvazione foto...")

    def disable_approval(self):
        self.btn_approve.config(state=tk.DISABLED)
        self.btn_reject.config(state=tk.DISABLED)

    def enable_copies(self):
        self.spin_copies.config(state="normal")
        self.btn_confirm_copies.config(state=tk.NORMAL)
        self.info_lbl.config(text="Seleziona il numero di copie e conferma la stampa.")
        self.set_status_message("In attesa scelta numero copie...")

    def disable_copies(self):
        self.spin_copies.config(state="disabled")
        self.btn_confirm_copies.config(state=tk.DISABLED)

    def _on_approve(self):
        self.disable_approval()
        self.response_queue.put(True)

    def _on_reject(self):
        self.disable_approval()
        self.response_queue.put(False)

    def _on_confirm_copies(self):
        try:
            val = int(self.spin_copies.get())
            min_num = self._settings.get_min_num_photos()
            max_num = self._settings.get_max_num_photos()
            if min_num <= val <= max_num:
                self.disable_copies()
                self.response_queue.put(val)
            else:
                self.info_lbl.config(text=f"Numero copie deve essere tra {min_num} e {max_num}.")
        except ValueError:
            self.info_lbl.config(text="Inserisci un numero valido.")

    def remove_last_carousel_item(self):
        """
        Removes the most recent item (at index 0) from the carousel and resets preview if empty.
        """
        if self.gallery_items:
            self.gallery_items.pop(0)
            self._rebuild_carousel_widgets()
            if self.gallery_items:
                self.select_carousel_item(0)
            else:
                self.current_photo_path = None
                if hasattr(self, '_current_pil_img'):
                    self._current_pil_img = None
                self.preview_label.config(image="", text="Nessuna foto da mostrare")

    def request_approval(self, photo_path_or_img) -> bool:
        self.root.after(0, lambda: self.add_photo_to_carousel(photo_path_or_img))
        self.root.after(0, self.enable_approval)
        res = self.response_queue.get()
        if not res:
            self.root.after(0, self.remove_last_carousel_item)
        return res

    def request_copies(self) -> int:
        self.root.after(0, self.enable_copies)
        res = self.response_queue.get()
        return res



class GUIUserInterface:
    """
    Adapter class for UserInterface when running in GUI mode.
    Maintains compatibility with Runner and engine calls.
    """

    def __init__(self, gui: PhotoboothGUI, polaroid_effect_list: list):
        self.gui = gui
        self.effect_list = polaroid_effect_list
        self._settings = Settings()

    def confirm_shot(self, photo_path, os_platform) -> bool:
        return self.gui.request_approval(photo_path)

    def show_preview_image(self, preview_img) -> bool:
        return self.gui.request_approval(preview_img)

    def choose_times_to_print(self) -> int:
        self.gui.root.after(0, self.gui.enable_copies)
        times = self.gui.response_queue.get()
        return times

    def choose_polaroid_effect(self) -> str:
        if not self.effect_list:
            return ""
        return self.effect_list[0] + ".png"

    def wait_for_camera_shutter(self):
        self.gui.root.after(0, lambda: self.gui.set_status_message("Pronto! Premi il pulsante sulla fotocamera per scattare."))
        self.gui.root.after(0, lambda: self.gui.info_lbl.config(text="Premi il pulsante sulla fotocamera."))

    def press_to_shoot(self):
        self.gui.root.after(0, lambda: self.gui.set_status_message("Premi per scattare..."))
        self.gui.root.after(0, lambda: self.gui.info_lbl.config(text="In attesa di scatto..."))

    def notify_shot_taken(self):
        self.gui.root.after(0, lambda: self.gui.set_status_message("Foto acquisita con successo."))

    def visualize_current_photos(self, path):
        photos_list = os.listdir(path)
        if photos_list:
            return os.path.join(path, photos_list[0])
        return ""

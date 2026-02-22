import json
import logging
import os
import re
import sys
import threading
import traceback
import customtkinter as ctk
from tkinter import filedialog, messagebox

log = logging.getLogger(__name__)

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')


def _fix_tcl_paths():
    """Set TCL/TK library paths for venvs where they aren't auto-discovered."""
    if os.environ.get('TCL_LIBRARY'):
        return
    candidates = [
        sys.base_prefix,
        os.path.dirname(getattr(sys, '_base_executable', '')),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Python', 'Python312'),
    ]
    for base in candidates:
        tcl_dir = os.path.join(base, 'tcl', 'tcl8.6')
        tk_dir = os.path.join(base, 'tcl', 'tk8.6')
        if os.path.isdir(tcl_dir):
            os.environ['TCL_LIBRARY'] = tcl_dir
            os.environ['TK_LIBRARY'] = tk_dir
            return


_fix_tcl_paths()


# ── Tooltip Helper ──

_FOCUS_COLOR = "#3B8ED0"  # CustomTkinter default blue
_UNFOCUS_COLOR = ("gray75", "gray25")  # Subtle border that blends with background


def _add_focus_ring(widget):
    """Add a visible border when the widget receives keyboard focus, and activate on Enter."""
    widget.configure(border_width=2, border_color=_UNFOCUS_COLOR)
    widget.bind("<FocusIn>", lambda e: widget.configure(border_color=_FOCUS_COLOR))
    widget.bind("<FocusOut>", lambda e: widget.configure(border_color=_UNFOCUS_COLOR))
    if hasattr(widget, 'invoke'):
        widget.bind("<Return>", lambda e: widget.invoke())
    elif hasattr(widget, 'toggle'):
        widget.bind("<Return>", lambda e: widget.toggle())
    elif hasattr(widget, '_command'):
        widget.bind("<Return>", lambda e: widget._command() if widget._command else None)


class Tooltip:
    """Accessible tooltip that appears on hover and focus."""

    def __init__(self, widget, text, delay=3000):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._tip = None
        self._after_id = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)
        widget.bind("<FocusIn>", self._schedule)
        widget.bind("<FocusOut>", self._hide)

    def _schedule(self, event=None):
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show)

    def _cancel(self):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self, event=None):
        self._after_id = None
        if self._tip:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self._tip = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        tw.configure(fg_color="white")
        container = ctk.CTkFrame(tw, fg_color="white", corner_radius=8, border_width=1, border_color="gray70")
        container.pack(fill="both", expand=True)
        ctk.CTkLabel(
            container, text=self.text,
            font=ctk.CTkFont(size=12),
            text_color="gray15",
            fg_color="white",
        ).pack(padx=10, pady=6)

    def _hide(self, event=None):
        self._cancel()
        if self._tip:
            self._tip.destroy()
            self._tip = None


class TextRedirector:
    """Captures stdout/stderr writes and routes them to the GUI log textbox."""

    def __init__(self, text_widget, root, original_stream):
        self.text_widget = text_widget
        self.root = root
        self.original = original_stream
        self.encoding = getattr(original_stream, 'encoding', 'utf-8')

    def write(self, text):
        if self.original:
            self.original.write(text)
        if text:
            self.root.after(0, self._append, text)

    def _append(self, text):
        text = _ANSI_RE.sub('', text)
        if not text:
            return
        self.text_widget.configure(state="normal")
        # Handle \r — replace the current line (used by spinner animations)
        if '\r' in text:
            parts = text.split('\r')
            for i, part in enumerate(parts):
                if i > 0:
                    self.text_widget.delete("end-1c linestart", "end-1c lineend")
                if part:
                    self.text_widget.insert("end", part)
        else:
            self.text_widget.insert("end", text)
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")

    def flush(self):
        if self.original:
            self.original.flush()


class CanvasBotGUI:
    def __init__(self):
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("Canvas Bot v1.2.1")
        self.root.geometry("650x750")
        self.root.minsize(550, 600)

        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cb.ico')
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, 'cb.ico')
        if os.path.isfile(icon_path):
            self.root.iconbitmap(icon_path)

        self._center_window()

        # --- Variables ---
        self.var_course_id = ctk.StringVar()
        self.var_course_list = ctk.StringVar()
        self.var_download_folder = ctk.StringVar()
        self.var_excel_folder = ctk.StringVar()
        self.var_json_folder = ctk.StringVar()

        self.var_video = ctk.BooleanVar()
        self.var_audio = ctk.BooleanVar()
        self.var_image = ctk.BooleanVar()
        self.var_hidden = ctk.BooleanVar()
        self.var_flatten = ctk.BooleanVar()
        self.var_content_tree = ctk.BooleanVar()
        self.var_full_tree = ctk.BooleanVar()

        # Track which course input is active
        self._course_id_active = True
        self._running = False

        # --- Build UI ---
        self._build_title_bar()
        self._build_course_selection()
        self._build_output_folders()
        self._build_options()
        self._build_run_button()
        self._build_output_area()

        # --- Validation bindings ---
        self.var_course_id.trace_add("write", self._on_course_id_changed)
        self.var_course_list.trace_add("write", self._on_course_list_changed)
        self.var_download_folder.trace_add("write", self._validate_run)
        self.var_excel_folder.trace_add("write", self._validate_run)
        self.var_json_folder.trace_add("write", self._validate_run)

        # --- Keyboard shortcuts ---
        self.root.bind("<Alt-r>", lambda e: self._on_run() if self.run_btn.cget("state") == "normal" else None)
        self.root.bind("<Alt-v>", lambda e: self._view_config())
        self.root.bind("<Alt-c>", lambda e: self._reset_config())
        self.root.bind("<Alt-a>", lambda e: self._show_about())

        # --- Load saved settings ---
        self._load_settings()

        # --- Check configuration ---
        self._check_config()

        # --- Set initial focus ---
        self.entry_course_id.focus_set()

    def _settings_path(self):
        appdata = os.environ.get("APPDATA", "")
        return os.path.join(appdata, "canvas bot", "gui_settings.json")

    def _load_settings(self):
        try:
            with open(self._settings_path(), "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return

        self.var_course_id.set(data.get("course_id", ""))
        self.var_course_list.set(data.get("course_list", ""))
        self.var_download_folder.set(data.get("download_folder", ""))
        self.var_excel_folder.set(data.get("excel_folder", ""))
        self.var_json_folder.set(data.get("json_folder", ""))
        self.var_video.set(data.get("include_video", False))
        self.var_audio.set(data.get("include_audio", False))
        self.var_image.set(data.get("include_image", False))
        self.var_hidden.set(data.get("include_hidden", False))
        self.var_flatten.set(data.get("flatten", False))
        self.var_content_tree.set(data.get("content_tree", False))
        self.var_full_tree.set(data.get("full_tree", False))
        self._validate_run()

    def _save_settings(self):
        try:
            data = {
                "course_id": self.var_course_id.get(),
                "course_list": self.var_course_list.get(),
                "download_folder": self.var_download_folder.get(),
                "excel_folder": self.var_excel_folder.get(),
                "json_folder": self.var_json_folder.get(),
                "include_video": self.var_video.get(),
                "include_audio": self.var_audio.get(),
                "include_image": self.var_image.get(),
                "include_hidden": self.var_hidden.get(),
                "flatten": self.var_flatten.get(),
                "content_tree": self.var_content_tree.get(),
                "full_tree": self.var_full_tree.get(),
            }
            folder = os.path.dirname(self._settings_path())
            os.makedirs(folder, exist_ok=True)
            with open(self._settings_path(), "w") as f:
                json.dump(data, f, indent=4)
        except OSError:
            pass

    def _check_config(self):
        """Check if Canvas API configuration is functional and update status bar."""
        try:
            from network.cred import check_config_status
            ok, message = check_config_status()
            if ok:
                self.status_label.configure(text=f"Status: {message}", text_color=("gray10", "gray90"))
            else:
                self.status_label.configure(text=f"Status: {message}", text_color="orange")
        except Exception:
            self.status_label.configure(text="Status: Configuration check failed", text_color="orange")

    def _center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.root.geometry(f"+{x}+{y}")

    # ── Title Bar ──

    def _build_title_bar(self):
        title_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        title_frame.pack(fill="x", padx=15, pady=(10, 0))

        ctk.CTkLabel(
            title_frame,
            text="Canvas Bot",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(side="left")

        ctk.CTkLabel(
            title_frame,
            text="v1.2.1",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        ).pack(side="left", padx=(8, 0), pady=(4, 0))

        reset_btn = ctk.CTkButton(
            title_frame,
            text="Reset Config (Alt+C)",
            width=130,
            command=self._reset_config,
        )
        reset_btn.pack(side="right")
        _add_focus_ring(reset_btn)
        Tooltip(reset_btn, "Reset Canvas API or Studio credentials")

        view_btn = ctk.CTkButton(
            title_frame,
            text="View Config (Alt+V)",
            width=130,
            command=self._view_config,
        )
        view_btn.pack(side="right", padx=(0, 5))
        _add_focus_ring(view_btn)
        Tooltip(view_btn, "View current configuration status in a terminal")

        about_btn = ctk.CTkButton(
            title_frame,
            text="About (Alt+A)",
            width=100,
            command=self._show_about,
        )
        about_btn.pack(side="right", padx=(0, 5))
        _add_focus_ring(about_btn)
        Tooltip(about_btn, "About Canvas Bot and how to use this tool")

    # ── Course Selection ──

    def _build_course_selection(self):
        section = self._make_section("Course Selection")

        # Course ID row
        id_frame = ctk.CTkFrame(section, fg_color="transparent")
        id_frame.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(id_frame, text="Course ID:", width=110, anchor="w").pack(side="left")
        self.entry_course_id = ctk.CTkEntry(
            id_frame, textvariable=self.var_course_id,
            placeholder_text="Canvas course ID (e.g. 12345)",
        )
        self.entry_course_id.pack(side="left", fill="x", expand=True)
        Tooltip(self.entry_course_id, "Enter the Canvas course ID from the course URL: canvas.edu/courses/[ID]")

        # Separator
        ctk.CTkLabel(section, text="- or -", text_color="gray").pack(pady=2)

        # Course List row
        list_frame = ctk.CTkFrame(section, fg_color="transparent")
        list_frame.pack(fill="x")

        ctk.CTkLabel(list_frame, text="Course List:", width=110, anchor="w").pack(side="left")
        self.entry_course_list = ctk.CTkEntry(
            list_frame, textvariable=self.var_course_list,
            placeholder_text="Path to .txt file with course IDs (one per line)",
        )
        self.entry_course_list.pack(side="left", fill="x", expand=True, padx=(0, 5))
        Tooltip(self.entry_course_list, "Text file with one course ID per line for batch processing")

        browse_list_btn = ctk.CTkButton(list_frame, text="Browse", width=70, command=self._browse_course_list)
        browse_list_btn.pack(side="right")
        _add_focus_ring(browse_list_btn)
        Tooltip(browse_list_btn, "Browse for a course list text file")

    # ── Output Folders ──

    def _build_output_folders(self):
        section = self._make_section("Output Folders")

        self._make_folder_row(section, "Download Folder:", self.var_download_folder,
                              "Directory where downloaded files will be saved")
        self._make_folder_row(section, "Excel Folder:", self.var_excel_folder,
                              "Directory where Excel accessibility reports will be saved")
        self._make_folder_row(section, "JSON Folder:", self.var_json_folder,
                              "Directory where JSON content inventories will be saved")

    def _make_folder_row(self, parent, label_text, variable, tooltip_text):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)

        ctk.CTkLabel(row, text=label_text, width=120, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(row, textvariable=variable, placeholder_text="Select a folder...")
        entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        Tooltip(entry, tooltip_text)

        browse_btn = ctk.CTkButton(row, text="Browse", width=70, command=lambda: self._browse_folder(variable))
        browse_btn.pack(side="right")
        _add_focus_ring(browse_btn)
        Tooltip(browse_btn, f"Browse for {label_text.lower().replace(':', '')} location")

    # ── Options ──

    def _build_options(self):
        frame = ctk.CTkFrame(self.root)
        frame.pack(fill="x", padx=15, pady=(10, 0))

        # Two columns side by side
        columns = ctk.CTkFrame(frame, fg_color="transparent")
        columns.pack(fill="x", padx=10, pady=8)
        columns.columnconfigure(0, weight=1)
        columns.columnconfigure(1, weight=1)

        # Left column — Download Options
        left = ctk.CTkFrame(columns, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(left, text="Download Options", font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x", pady=(0, 4))

        cb_video = ctk.CTkCheckBox(left, text="Include video files", variable=self.var_video)
        cb_video.pack(anchor="w", pady=2)
        _add_focus_ring(cb_video)
        Tooltip(cb_video, "Also download video files (MP4, MOV, MKV, AVI, WebM)")

        cb_audio = ctk.CTkCheckBox(left, text="Include audio files", variable=self.var_audio)
        cb_audio.pack(anchor="w", pady=2)
        _add_focus_ring(cb_audio)
        Tooltip(cb_audio, "Also download audio files (MP3, M4A, WAV, OGG)")

        cb_image = ctk.CTkCheckBox(left, text="Include image files", variable=self.var_image)
        cb_image.pack(anchor="w", pady=2)
        _add_focus_ring(cb_image)
        Tooltip(cb_image, "Also download image files (JPG, PNG, GIF, SVG, WebP)")

        cb_hidden = ctk.CTkCheckBox(left, text="Include hidden content", variable=self.var_hidden)
        cb_hidden.pack(anchor="w", pady=2)
        _add_focus_ring(cb_hidden)
        Tooltip(cb_hidden, "Include content that is hidden or unpublished in Canvas")

        cb_flatten = ctk.CTkCheckBox(left, text="Flatten folder structure", variable=self.var_flatten)
        cb_flatten.pack(anchor="w", pady=2)
        _add_focus_ring(cb_flatten)
        Tooltip(cb_flatten, "Download all files to a single flat directory instead of preserving module structure")

        # Right column — Display Options
        right = ctk.CTkFrame(columns, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(15, 0))

        ctk.CTkLabel(right, text="Display Options", font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x", pady=(0, 4))

        self.cb_content_tree = ctk.CTkCheckBox(right, text="Print content tree", variable=self.var_content_tree, command=self._on_content_tree_toggled)
        self.cb_content_tree.pack(anchor="w", pady=2)
        _add_focus_ring(self.cb_content_tree)
        Tooltip(self.cb_content_tree, "Print course tree showing only resources that contain content (single course only)")

        self.cb_full_tree = ctk.CTkCheckBox(right, text="Print full course tree", variable=self.var_full_tree, command=self._on_full_tree_toggled)
        self.cb_full_tree.pack(anchor="w", pady=2)
        _add_focus_ring(self.cb_full_tree)
        Tooltip(self.cb_full_tree, "Print complete course tree including all resources (single course only)")

    # ── Run Button ──

    def _build_run_button(self):
        run_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        run_frame.pack(fill="x", padx=15, pady=(10, 0))

        self.run_btn = ctk.CTkButton(
            run_frame,
            text="Run (Alt+R)",
            height=36,
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled",
            command=self._on_run,
        )
        self.run_btn.pack(fill="x")
        _add_focus_ring(self.run_btn)
        Tooltip(self.run_btn, "Start processing the selected course(s) with the chosen options")

    # ── Output Area ──

    def _build_output_area(self):
        output_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        output_frame.pack(fill="both", expand=True, padx=15, pady=(10, 15))

        self.status_label = ctk.CTkLabel(
            output_frame,
            text="Status: Ready",
            anchor="w",
            font=ctk.CTkFont(size=12),
        )
        self.status_label.pack(fill="x", pady=(0, 5))

        self.log_text = ctk.CTkTextbox(
            output_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            state="disabled",
        )
        self.log_text.pack(fill="both", expand=True)

    # ── Section Helper ──

    def _make_section(self, title):
        frame = ctk.CTkFrame(self.root)
        frame.pack(fill="x", padx=15, pady=(10, 0))

        ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 4))

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill="x", padx=10, pady=(0, 8))
        return content

    # ── Browse Handlers ──

    def _browse_course_list(self):
        path = filedialog.askopenfilename(
            title="Select Course List",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self.var_course_list.set(path)

    def _browse_folder(self, variable):
        path = filedialog.askdirectory(title="Select Folder")
        if path:
            variable.set(path)

    # ── Validation ──

    def _on_course_id_changed(self, *_):
        if self.var_course_id.get().strip():
            self._course_id_active = True
            self.var_course_list.set("")
            self.cb_content_tree.configure(state="normal")
            self.cb_full_tree.configure(state="normal")
        self._validate_run()

    def _on_course_list_changed(self, *_):
        if self.var_course_list.get().strip():
            self._course_id_active = False
            self.var_course_id.set("")
            # Disable tree options for batch mode
            self.var_content_tree.set(False)
            self.var_full_tree.set(False)
            self.cb_content_tree.configure(state="disabled")
            self.cb_full_tree.configure(state="disabled")
        self._validate_run()

    def _on_content_tree_toggled(self):
        if self.var_content_tree.get():
            self.var_full_tree.set(False)
        self._validate_run()

    def _on_full_tree_toggled(self):
        if self.var_full_tree.get():
            self.var_content_tree.set(False)
        self._validate_run()

    def _validate_run(self, *_):
        if self._running:
            return
        has_course = self.var_course_id.get().strip() or self.var_course_list.get().strip()
        has_output = (self.var_download_folder.get().strip()
                      or self.var_excel_folder.get().strip()
                      or self.var_json_folder.get().strip()
                      or self.var_content_tree.get()
                      or self.var_full_tree.get())
        if has_course and has_output:
            self.run_btn.configure(state="normal")
        else:
            self.run_btn.configure(state="disabled")

    # ── Run Logic ──

    def _set_status(self, text):
        self.root.after(0, self.status_label.configure, {"text": f"Status: {text}"})

    def _on_run(self):
        if self._running:
            return

        self._save_settings()

        # Clear log
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        # Disable controls
        self._running = True
        self.run_btn.configure(state="disabled", text="Running...")
        self._set_status("Initializing...")

        # Redirect stdout/stderr to log textbox
        self._old_stdout = sys.stdout
        self._old_stderr = sys.stderr
        sys.stdout = TextRedirector(self.log_text, self.root, self._old_stdout)
        sys.stderr = TextRedirector(self.log_text, self.root, self._old_stderr)

        # Spawn worker thread
        thread = threading.Thread(target=self._run_worker, daemon=True)
        thread.start()

    def _run_worker(self):
        try:
            from canvas_bot import CanvasBot, read_course_list
            from network.cred import set_canvas_api_key_to_environment_variable, load_config_data_from_appdata

            # Check credentials
            if not load_config_data_from_appdata():
                self._set_status("Error - Not Configured")
                print("ERROR: Canvas Bot is not configured.")
                print("Click 'Reset Config' to configure your Canvas instance.")
                self._finish_run()
                return

            if not set_canvas_api_key_to_environment_variable():
                self._set_status("Error - No API Token")
                print("ERROR: No Canvas API access token found.")
                print("Click 'Reset Config' to set up your API token.")
                self._finish_run()
                return

            # Build and validate course list
            from gui.validation import validate_course_id, validate_course_list

            course_ids = []
            if self.var_course_id.get().strip():
                cid = self.var_course_id.get().strip()
                error = validate_course_id(cid)
                if error:
                    self._set_status("Error")
                    print(f"ERROR: {error}")
                    self._finish_run()
                    return
                course_ids = [cid]
            elif self.var_course_list.get().strip():
                raw_ids = read_course_list(self.var_course_list.get().strip())
                course_ids, warnings = validate_course_list(raw_ids)
                for w in warnings:
                    print(f"WARNING: {w}")

            if not course_ids:
                self._set_status("Error")
                print("ERROR: No valid course IDs to process.")
                self._finish_run()
                return

            # Build params
            params = {
                "include_video_files": self.var_video.get(),
                "include_audio_files": self.var_audio.get(),
                "include_image_files": self.var_image.get(),
                "download_hidden_files": self.var_hidden.get(),
                "flatten": self.var_flatten.get(),
            }

            download_folder = self.var_download_folder.get().strip() or None
            excel_folder = self.var_excel_folder.get().strip() or None
            json_folder = self.var_json_folder.get().strip() or None

            total = len(course_ids)
            for i, course_id in enumerate(course_ids, 1):
                self._set_status(f"Processing course {i}/{total} (ID: {course_id})...")
                print(f"\n{'='*50}")
                print(f"Course {i}/{total} — ID: {course_id}")
                print(f"{'='*50}\n")

                bot = CanvasBot(course_id)
                bot.start()

                if self.var_content_tree.get():
                    bot.print_content_tree()

                if self.var_full_tree.get():
                    bot.print_full_course()

                if download_folder:
                    bot.download_files(download_folder, **params)

                if json_folder:
                    bot.save_content_as_json(json_folder, download_folder, **params)

                if excel_folder:
                    bot.save_content_as_excel(excel_folder, **params)

            self._set_status("Complete")
            print(f"\nAll done — {total} course(s) processed.")

        except Exception as exc:
            log.exception(f"Unhandled error: {type(exc).__name__}: {exc}")
            self._set_status("Error")
            traceback.print_exc()

        finally:
            self._finish_run()

    def _finish_run(self):
        # Restore stdout/stderr
        sys.stdout = self._old_stdout
        sys.stderr = self._old_stderr

        # Re-enable controls on the main thread
        def _restore():
            self._running = False
            self.run_btn.configure(text="Run (Alt+R)")
            self._validate_run()

        self.root.after(0, _restore)

    # ── About ──

    def _show_about(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("About Canvas Bot")
        dialog.geometry("520x560")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # Center on parent
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 520) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 560) // 2
        dialog.geometry(f"+{x}+{y}")

        # Scrollable content
        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=15)

        def heading(text):
            ctk.CTkLabel(scroll, text=text, font=ctk.CTkFont(size=15, weight="bold"), anchor="w").pack(fill="x", pady=(12, 4))

        def body(text):
            ctk.CTkLabel(scroll, text=text, font=ctk.CTkFont(size=13), anchor="w", justify="left", wraplength=460).pack(fill="x", pady=(0, 2))

        # Title
        ctk.CTkLabel(scroll, text="Canvas Bot", font=ctk.CTkFont(size=20, weight="bold"), anchor="w").pack(fill="x")
        ctk.CTkLabel(scroll, text="v1.2.1", font=ctk.CTkFont(size=13), text_color="gray", anchor="w").pack(fill="x")

        # Intro
        heading("What is Canvas Bot?")
        body(
            "Canvas Bot connects to your institution's Canvas LMS and scans course content for "
            "embedded files, links, and media. It downloads documents, generates Excel accessibility "
            "reports, and exports content inventories as JSON. It is designed for instructional "
            "designers and accessibility specialists who need to audit courses at scale."
        )

        # GUI guide
        heading("Course Selection")
        body(
            "Enter a single Canvas course ID (the number from the course URL, e.g. canvas.edu/courses/12345), "
            "or select a .txt file containing one course ID per line for batch processing."
        )

        heading("Output Folders")
        body(
            "Download Folder \u2014 where course files (PDFs, DOCX, media, etc.) will be saved, "
            "organized into subfolders by module and resource type."
        )
        body(
            "Excel Folder \u2014 where accessibility audit workbooks (.xlsm) will be generated. "
            "Each workbook contains categorized sheets for documents, videos, audio, and images "
            "with tracking columns and conditional formatting."
        )
        body(
            "JSON Folder \u2014 where raw content inventories will be saved as .json files for "
            "further processing or integration with other tools."
        )
        body(
            "You can use any combination of output folders. At least one output folder or "
            "display option is required to run."
        )

        heading("Download Options")
        body(
            "By default, only document files (PDF, DOCX, PPTX, etc.) are downloaded. Use the "
            "checkboxes to also include video, audio, or image files. \"Include hidden content\" "
            "will pull unpublished items. \"Flatten folder structure\" puts all files in one "
            "directory instead of preserving the course module hierarchy."
        )

        heading("Display Options")
        body(
            "Available for single-course mode only. \"Print content tree\" shows a tree of course "
            "resources that contain downloadable content. \"Print full course tree\" shows every "
            "resource in the course including empty modules and pages."
        )

        heading("Configuration")
        body(
            "Before first use, click \"Reset Config\" to set up your Canvas instance URL and API "
            "access token. You can generate an API token in Canvas under Account > Settings > "
            "New Access Token. Use \"View Config\" to verify your current configuration."
        )

        # First-time setup
        heading("First-Time Setup")
        body("1.  Click \"Reset Config\" and choose \"Reset Canvas API Credentials\".")
        body("2.  Enter your institution identifier (e.g. \"sfsu\" for sfsu.instructure.com).")
        body("3.  Paste your Canvas API access token when prompted.")
        body("4.  Enter a course ID, choose an output folder, and click Run.")

        # Contact
        heading("Contact")
        body("Daniel Fontaine")
        body("fontaine@sfsu.edu")

        # Close button
        close_btn = ctk.CTkButton(dialog, text="Close", width=120, command=dialog.destroy)
        close_btn.pack(pady=(5, 15))
        close_btn.focus_set()

        # Escape key closes dialog
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    # ── Settings ──

    def _launch_cli(self, flag):
        import subprocess
        if getattr(sys, 'frozen', False):
            exe = sys.executable
            subprocess.Popen(['cmd', '/k', exe, flag], creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            script = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'canvas_bot.py')
            subprocess.Popen(['cmd', '/k', 'python', script, flag], creationflags=subprocess.CREATE_NEW_CONSOLE)

    def _view_config(self):
        self._launch_cli('--config_status')

    def _reset_config(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Reset Configuration")
        dialog.geometry("350x200")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # Center on parent
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 350) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 200) // 2
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(
            dialog,
            text="Choose what to reset:",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(20, 15))

        api_btn = ctk.CTkButton(
            dialog,
            text="Reset Canvas API Credentials",
            width=260,
            command=lambda: [dialog.destroy(), self._launch_cli('--reset_canvas_params')],
        )
        api_btn.pack(pady=5)
        api_btn.focus_set()
        Tooltip(api_btn, "Clear and reconfigure Canvas API token and instance URL")

        studio_btn = ctk.CTkButton(
            dialog,
            text="Reset Canvas Studio Credentials",
            width=260,
            command=lambda: [dialog.destroy(), self._launch_cli('--reset_canvas_studio_params')],
        )
        studio_btn.pack(pady=5)
        Tooltip(studio_btn, "Clear and reconfigure Canvas Studio OAuth credentials")

        cancel_btn = ctk.CTkButton(
            dialog,
            text="Cancel",
            width=260,
            fg_color="gray",
            command=dialog.destroy,
        )
        cancel_btn.pack(pady=(10, 0))

        # Escape key closes dialog
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def run(self):
        self.root.mainloop()

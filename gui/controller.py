import json
import logging
import os
import sys
import threading
import traceback
import customtkinter as ctk
from tkinter import filedialog

from gui.widgets import _add_focus_ring, _underline_char, Tooltip, TextRedirector

log = logging.getLogger(__name__)


class GUIController:
    """Controller for the Canvas Bot GUI (MVC pattern).

    Handles user actions, input validation, settings persistence,
    and orchestrates calls to the canvas_bot engine (model).
    """

    def __init__(self, view):
        self.view = view
        self._running = False
        self._course_id_active = True
        self._old_stdout = None
        self._old_stderr = None

    # ── Settings Persistence ──

    def settings_path(self):
        appdata = os.environ.get("APPDATA", "")
        return os.path.join(appdata, "canvas bot", "gui_settings.json")

    def load_settings(self):
        try:
            with open(self.settings_path(), "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return

        self.view.var_course_id.set(data.get("course_id", ""))
        self.view.var_course_list.set(data.get("course_list", ""))

        # Migrate from old 3-folder settings to single output_folder
        output_folder = data.get("output_folder", "")
        if not output_folder:
            output_folder = (data.get("download_folder", "")
                             or data.get("excel_folder", "")
                             or data.get("json_folder", ""))
        self.view.var_output_folder.set(output_folder)

        self.view.var_download.set(data.get("download", False))
        self.view.var_video.set(data.get("include_video", False))
        self.view.var_audio.set(data.get("include_audio", False))
        self.view.var_image.set(data.get("include_image", False))
        self.view.var_hidden.set(data.get("include_hidden", False))
        self.view.var_inactive.set(data.get("include_inactive", False))
        self.view.var_flatten.set(data.get("flatten", False))
        self.view.var_content_tree.set(data.get("content_tree", False))
        self.view.var_full_tree.set(data.get("full_tree", False))
        self.validate_run()

    def save_settings(self):
        try:
            data = {
                "course_id": self.view.var_course_id.get(),
                "course_list": self.view.var_course_list.get(),
                "output_folder": self.view.var_output_folder.get(),
                "download": self.view.var_download.get(),
                "include_video": self.view.var_video.get(),
                "include_audio": self.view.var_audio.get(),
                "include_image": self.view.var_image.get(),
                "include_hidden": self.view.var_hidden.get(),
                "include_inactive": self.view.var_inactive.get(),
                "flatten": self.view.var_flatten.get(),
                "content_tree": self.view.var_content_tree.get(),
                "full_tree": self.view.var_full_tree.get(),
            }
            folder = os.path.dirname(self.settings_path())
            os.makedirs(folder, exist_ok=True)
            with open(self.settings_path(), "w") as f:
                json.dump(data, f, indent=4)
        except OSError:
            pass

    # ── First Run ──

    def is_first_run(self):
        """Check if this is the first time the GUI has been launched."""
        try:
            with open(self.settings_path(), "r") as f:
                data = json.load(f)
            return data.get("first_run", True)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return True

    def _set_first_run_complete(self):
        """Mark first run as complete in settings."""
        try:
            try:
                with open(self.settings_path(), "r") as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError, OSError):
                data = {}
            data["first_run"] = False
            folder = os.path.dirname(self.settings_path())
            os.makedirs(folder, exist_ok=True)
            with open(self.settings_path(), "w") as f:
                json.dump(data, f, indent=4)
        except OSError:
            pass

    def show_welcome(self):
        """Show the first-run welcome and security dialog."""
        if not self.is_first_run():
            return

        dialog = ctk.CTkToplevel(self.view.root)
        dialog.title("Welcome to Canvas Bot")
        dialog.geometry("560x580")
        dialog.resizable(False, False)
        dialog.transient(self.view.root)
        dialog.grab_set()

        # Center on screen (parent may not be positioned yet at startup)
        dialog.update_idletasks()
        screen_w = dialog.winfo_screenwidth()
        screen_h = dialog.winfo_screenheight()
        x = (screen_w - 560) // 2
        y = (screen_h - 580) // 2
        dialog.geometry(f"+{x}+{y}")

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=15)

        # High-contrast heading color: red-orange in light mode, light coral in dark mode
        warn_color = ("#c0392b", "#e74c3c")

        def heading(text, color=None):
            lbl = ctk.CTkLabel(scroll, text=text,
                               font=ctk.CTkFont(size=15, weight="bold"), anchor="w")
            if color:
                lbl.configure(text_color=color)
            lbl.pack(fill="x", pady=(12, 4))

        def body(text):
            ctk.CTkLabel(scroll, text=text, font=ctk.CTkFont(size=13),
                         anchor="w", justify="left", wraplength=500).pack(fill="x", pady=(0, 2))

        # Welcome
        ctk.CTkLabel(scroll, text="Welcome to Canvas Bot",
                     font=ctk.CTkFont(size=20, weight="bold"), anchor="w").pack(fill="x")
        body(
            "Canvas Bot is a bridge between Canvas LMS and your desktop. It scans "
            "courses to discover content, downloads files, and lets you review items "
            "for accessibility."
        )

        # Security
        heading("Security & API Credentials", color=warn_color)
        body(
            "Canvas Bot requires a Canvas API access token to function. "
            "This token grants read access to course content on your behalf."
        )
        body("1.  Never share your API token with anyone.")
        body("2.  Generate a dedicated token for Canvas Bot. Do not reuse tokens from other applications.")
        body("3.  Set an expiration date on your token and rotate it periodically.")
        body(
            "4.  If your token is compromised, revoke it immediately in Canvas "
            "(Account > Settings > Approved Integrations)."
        )
        body(
            "5.  Your token is stored in the Windows Credential Vault (encrypted, "
            "per-user). It is never written to plaintext files or logs."
        )

        # Responsibility
        heading("Deployment & Responsibility", color=warn_color)
        body(
            "Canvas Bot has been hardened following a SOC 2-aligned security assessment. "
            "All API communication uses TLS certificate verification, credentials are "
            "stored encrypted in the Windows Credential Vault and never written to "
            "plaintext files, sensitive data is stripped from logs, and all inputs are "
            "validated before use."
        )
        body(
            "Canvas Bot is provided as-is under the MIT License. You are responsible "
            "for how this tool is deployed and used within your institution. Ensure "
            "that your use complies with your institution's data governance policies "
            "and any applicable regulations (FERPA, GDPR, etc.)."
        )

        # Accessibility
        heading("Accessibility")
        body(
            "The GUI supports full keyboard navigation with visible focus indicators, "
            "Alt+key shortcuts on all buttons, and arrow key navigation in tables and "
            "tab selectors. Color is never the sole means of conveying information. "
            "Due to limitations of the underlying framework (CustomTkinter), screen "
            "reader support is limited."
        )

        # Getting started
        heading("Getting Started")
        body("1.  Click \"Reset Config\" in the title bar to set up your Canvas instance URL and API token.")
        body("2.  Enter a course ID, choose an output folder, and check \"Download files\".")
        body("3.  Click Run to start scanning.")

        def _close():
            self._set_first_run_complete()
            dialog.destroy()

        close_btn = ctk.CTkButton(dialog, text="Get Started", width=140, command=_close)
        close_btn.pack(pady=(5, 15))
        _add_focus_ring(close_btn)
        _underline_char(close_btn, 0)  # G
        close_btn.focus_set()

        dialog.bind("<Escape>", lambda e: _close())
        dialog.protocol("WM_DELETE_WINDOW", _close)

    # ── Configuration ──

    def check_config(self):
        """Check if Canvas API configuration is functional and update status bar."""
        try:
            from network.cred import check_config_status
            ok, message = check_config_status()
            if ok:
                self.view.status_label.configure(text=f"Status: {message}", text_color=("gray10", "gray90"))
            else:
                self.view.status_label.configure(text=f"Status: WARNING — {message}", text_color="orange")
        except Exception:
            self.view.status_label.configure(text="Status: WARNING — Configuration check failed", text_color="orange")

    def launch_cli(self, flag):
        import subprocess
        if getattr(sys, 'frozen', False):
            exe = sys.executable
            subprocess.Popen(['cmd', '/k', exe, flag], creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            script = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'canvas_bot.py')
            subprocess.Popen(['cmd', '/k', 'python', script, flag], creationflags=subprocess.CREATE_NEW_CONSOLE)

    def view_config(self):
        self.launch_cli('--config_status')

    def reset_config(self):
        dialog = ctk.CTkToplevel(self.view.root)
        dialog.title("Reset Configuration")
        dialog.geometry("350x200")
        dialog.resizable(False, False)
        dialog.transient(self.view.root)
        dialog.grab_set()

        # Center on parent
        dialog.update_idletasks()
        x = self.view.root.winfo_x() + (self.view.root.winfo_width() - 350) // 2
        y = self.view.root.winfo_y() + (self.view.root.winfo_height() - 200) // 2
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
            command=lambda: [dialog.destroy(), self.launch_cli('--reset_canvas_params')],
        )
        api_btn.pack(pady=5)
        _add_focus_ring(api_btn)
        _underline_char(api_btn, 13)  # A in "API"
        api_btn.focus_set()
        Tooltip(api_btn, "Clear and reconfigure Canvas API token and instance URL")

        studio_btn = ctk.CTkButton(
            dialog,
            text="Reset Canvas Studio Credentials",
            width=260,
            command=lambda: [dialog.destroy(), self.launch_cli('--reset_canvas_studio_params')],
        )
        studio_btn.pack(pady=5)
        _add_focus_ring(studio_btn)
        _underline_char(studio_btn, 13)  # S in "Studio"
        Tooltip(studio_btn, "Clear and reconfigure Canvas Studio OAuth credentials")

        cancel_btn = ctk.CTkButton(
            dialog,
            text="Cancel",
            width=260,
            fg_color="gray",
            command=dialog.destroy,
        )
        cancel_btn.pack(pady=(10, 0))
        _add_focus_ring(cancel_btn)
        _underline_char(cancel_btn, 0)  # C

        dialog.bind("<Escape>", lambda e: dialog.destroy())

    # ── Browse Handlers ──

    def browse_course_list(self):
        path = filedialog.askopenfilename(
            title="Select Course List",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self.view.var_course_list.set(path)

    def browse_folder(self, variable):
        path = filedialog.askdirectory(title="Select Folder")
        if path:
            variable.set(path)

    # ── Input Validation ──

    def on_course_id_changed(self, *_):
        if self.view.var_course_id.get().strip():
            self._course_id_active = True
            self.view.var_course_list.set("")
            self.view.cb_content_tree.configure(state="normal")
            self.view.cb_full_tree.configure(state="normal")
        self.validate_run()

    def on_course_list_changed(self, *_):
        if self.view.var_course_list.get().strip():
            self._course_id_active = False
            self.view.var_course_id.set("")
            # Disable tree options for batch mode
            self.view.var_content_tree.set(False)
            self.view.var_full_tree.set(False)
            self.view.cb_content_tree.configure(state="disabled")
            self.view.cb_full_tree.configure(state="disabled")
        self.validate_run()

    def on_content_tree_toggled(self):
        if self.view.var_content_tree.get():
            self.view.var_full_tree.set(False)
        self.validate_run()

    def on_full_tree_toggled(self):
        if self.view.var_full_tree.get():
            self.view.var_content_tree.set(False)
        self.validate_run()

    def validate_run(self, *_):
        if self._running:
            return
        has_course = (self.view.var_course_id.get().strip()
                      or self.view.var_course_list.get().strip())

        output_folder = self.view.var_output_folder.get().strip()
        has_action = output_folder and self.view.var_download.get()
        has_tree = (self.view.var_content_tree.get()
                    or self.view.var_full_tree.get())

        if has_course and (has_action or has_tree):
            self.view.run_btn.configure(state="normal")
        else:
            self.view.run_btn.configure(state="disabled")

    # ── Run Logic ──

    def set_status(self, text):
        color = "orange" if text.startswith("Error") else ("gray10", "gray90")
        self.view.root.after(0, self.view.status_label.configure, {"text": f"Status: {text}", "text_color": color})

    def on_run(self):
        if self._running:
            return

        self.save_settings()

        # Clear log
        self.view.log_text.configure(state="normal")
        self.view.log_text.delete("1.0", "end")
        self.view.log_text.configure(state="disabled")

        # Disable controls
        self._running = True
        self.view.run_btn.configure(state="disabled", text="Running...")
        self.set_status("Initializing...")

        # Redirect stdout/stderr to log textbox
        self._old_stdout = sys.stdout
        self._old_stderr = sys.stderr
        sys.stdout = TextRedirector(self.view.log_text, self.view.root, self._old_stdout)
        sys.stderr = TextRedirector(self.view.log_text, self.view.root, self._old_stderr)

        # Spawn worker thread
        thread = threading.Thread(target=self._run_worker, daemon=True)
        thread.start()

    def _run_worker(self):
        try:
            import pythoncom
            pythoncom.CoInitialize()
            from canvas_bot import CanvasBot, read_course_list
            from network.cred import set_canvas_api_key_to_environment_variable, load_config_data_from_appdata

            # Check credentials
            if not load_config_data_from_appdata():
                self.set_status("Error - Not Configured")
                print("ERROR: Canvas Bot is not configured.")
                print("Click 'Reset Config' to configure your Canvas instance.")
                self._finish_run()
                return

            from sorters.sorters import reload_patterns
            reload_patterns()

            if not set_canvas_api_key_to_environment_variable():
                self.set_status("Error - No API Token")
                print("ERROR: No Canvas API access token found.")
                print("Click 'Reset Config' to set up your API token.")
                self._finish_run()
                return

            # Build and validate course list
            from gui.validation import validate_course_id, validate_course_list

            course_ids = []
            if self.view.var_course_id.get().strip():
                cid = self.view.var_course_id.get().strip()
                error = validate_course_id(cid)
                if error:
                    self.set_status("Error")
                    print(f"ERROR: {error}")
                    self._finish_run()
                    return
                course_ids = [cid]
            elif self.view.var_course_list.get().strip():
                raw_ids = read_course_list(self.view.var_course_list.get().strip())
                course_ids, warnings = validate_course_list(raw_ids)
                for w in warnings:
                    print(f"WARNING: {w}")

            if not course_ids:
                self.set_status("Error")
                print("ERROR: No valid course IDs to process.")
                self._finish_run()
                return

            # Build params
            params = {
                "include_video_files": self.view.var_video.get(),
                "include_audio_files": self.view.var_audio.get(),
                "include_image_files": self.view.var_image.get(),
                "download_hidden_files": self.view.var_hidden.get(),
                "only_active_files": not self.view.var_inactive.get(),
                "flatten": self.view.var_flatten.get(),
            }

            output_folder = self.view.var_output_folder.get().strip() or None
            do_download = self.view.var_download.get()

            total = len(course_ids)
            for i, course_id in enumerate(course_ids, 1):
                self.set_status(f"Processing course {i}/{total} (ID: {course_id})...")
                print(f"\n{'='*50}")
                print(f"Course {i}/{total} — ID: {course_id}")
                print(f"{'='*50}\n")

                bot = CanvasBot(course_id)
                bot.start()

                # Compute course subfolder once for all operations
                course_folder = None
                if output_folder and bot.exists:
                    from tools.string_checking.url_cleaning import sanitize_windows_filename
                    from config.yaml_io import create_download_manifest
                    course_folder = os.path.join(
                        os.path.normpath(output_folder),
                        f"{sanitize_windows_filename(bot.course_name)} - {bot.course_id}",
                    )

                # Save content.json to .manifest/ for Content Viewer
                if course_folder:
                    manifest_dir = create_download_manifest(course_folder)
                    bot.save_content_as_json(manifest_dir, course_folder, **params)

                if self.view.var_content_tree.get():
                    bot.print_content_tree()

                if self.view.var_full_tree.get():
                    bot.print_full_course()

                if output_folder and do_download:
                    bot.download_files(output_folder, **params)


            self.set_status("Complete")
            print(f"\nAll done — {total} course(s) processed.")
            self.view.root.after(0, self._on_scan_complete)

        except Exception as exc:
            log.exception(f"Unhandled error: {type(exc).__name__}: {exc}")
            self.set_status("Error")
            traceback.print_exc()

        finally:
            pythoncom.CoUninitialize()
            self._finish_run()

    def _on_scan_complete(self):
        """Called on the main thread after all courses have been processed."""
        # Refresh Content Viewer if it exists
        if hasattr(self.view, "content_viewer"):
            self.view.content_viewer.refresh_course_list()

    def _finish_run(self):
        # Restore stdout/stderr
        sys.stdout = self._old_stdout
        sys.stderr = self._old_stderr

        # Re-enable controls on the main thread
        def _restore():
            self._running = False
            self.view.run_btn.configure(text="Run")
            _underline_char(self.view.run_btn, 0)
            self.validate_run()

        self.view.root.after(0, _restore)

    # ── About ──

    def show_about(self):
        dialog = ctk.CTkToplevel(self.view.root)
        dialog.title("About Canvas Bot")
        dialog.geometry("620x580")
        dialog.resizable(False, False)
        dialog.transient(self.view.root)
        dialog.grab_set()

        # Center on parent
        dialog.update_idletasks()
        x = self.view.root.winfo_x() + (self.view.root.winfo_width() - 620) // 2
        y = self.view.root.winfo_y() + (self.view.root.winfo_height() - 580) // 2
        dialog.geometry(f"+{x}+{y}")

        wrap = 560

        def _heading(parent, text):
            ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=15, weight="bold"), anchor="w").pack(fill="x", pady=(12, 4))

        def _body(parent, text):
            ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=13), anchor="w", justify="left", wraplength=wrap).pack(fill="x", pady=(0, 2))

        # ── Tabview ──
        tabview = ctk.CTkTabview(dialog)
        tabview.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        tabview.add("About")
        tabview.add("Run")
        tabview.add("Content")
        tabview.add("Patterns")

        # Make tab selector buttons keyboard-navigable
        tab_names = ["About", "Run", "Content", "Patterns"]
        try:
            buttons = tabview._segmented_button._buttons_dict
            for name in tab_names:
                btn = buttons.get(name)
                if not btn:
                    continue
                _add_focus_ring(btn)

                def _nav(event, current=name, direction=0):
                    idx = tab_names.index(current) + direction
                    if 0 <= idx < len(tab_names):
                        target = tab_names[idx]
                        tabview.set(target)
                        buttons[target].focus_set()
                    return "break"

                btn.bind("<Left>", lambda e, n=name: _nav(e, n, -1))
                btn.bind("<Right>", lambda e, n=name: _nav(e, n, 1))
        except AttributeError:
            pass

        # ── About tab ──
        about_scroll = ctk.CTkScrollableFrame(tabview.tab("About"), fg_color="transparent")
        about_scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(about_scroll, text="Canvas Bot", font=ctk.CTkFont(size=20, weight="bold"), anchor="w").pack(fill="x")
        ctk.CTkLabel(about_scroll, text="v1.2.2", font=ctk.CTkFont(size=13), text_color="gray", anchor="w").pack(fill="x")

        _heading(about_scroll, "What is Canvas Bot?")
        _body(about_scroll,
            "Canvas Bot is a bridge between Canvas LMS and your desktop. It connects to your "
            "institution's Canvas and scans courses to discover all embedded files, links, and media. "
            "You can download course documents directly to your computer, browse content by type, "
            "and review items for accessibility. It is designed for instructional designers and "
            "accessibility specialists who need to audit courses at scale."
        )

        _heading(about_scroll, "Getting Started")
        _body(about_scroll, "1.  Click \"Reset Config\" and choose \"Reset Canvas API Credentials\".")
        _body(about_scroll, "2.  Enter your institution identifier (e.g. \"sfsu\" for sfsu.instructure.com).")
        _body(about_scroll, "3.  Paste your Canvas API access token when prompted.")
        _body(about_scroll, "4.  Enter a course ID, choose an output folder, and click Run.")

        _heading(about_scroll, "Configuration")
        _body(about_scroll,
            "Before first use, click \"Reset Config\" to set up your Canvas instance URL and API "
            "access token. You can generate an API token in Canvas under Account > Settings > "
            "New Access Token. Use \"View Config\" to verify your current configuration."
        )

        _heading(about_scroll, "Contact - Ideas & Issues")
        _body(about_scroll, "Daniel Fontaine")
        email = ctk.CTkLabel(about_scroll, text="fontaine@sfsu.edu",
                             font=ctk.CTkFont(size=13), anchor="w", text_color="#3B8ED0", cursor="hand2")
        email.pack(fill="x", pady=(0, 2))
        email.bind("<Button-1>", lambda e: __import__("webbrowser").open("mailto:fontaine@sfsu.edu"))
        link = ctk.CTkLabel(about_scroll, text="github.com/Fontaineconsult/canvas-bot-v2",
                            font=ctk.CTkFont(size=13), anchor="w", text_color="#3B8ED0", cursor="hand2")
        link.pack(fill="x", pady=(0, 2))
        link.bind("<Button-1>", lambda e: __import__("webbrowser").open("https://github.com/Fontaineconsult/canvas-bot-v2"))

        # ── Run tab ──
        run_scroll = ctk.CTkScrollableFrame(tabview.tab("Run"), fg_color="transparent")
        run_scroll.pack(fill="both", expand=True)

        _heading(run_scroll, "Course Selection")
        _body(run_scroll,
            "Enter a single Canvas course ID (the number from the course URL, e.g. canvas.edu/courses/12345), "
            "or select a .txt file containing one course ID per line for batch processing."
        )

        _heading(run_scroll, "Output")
        _body(run_scroll,
            "Select an output folder and check \"Download files\" to download course documents "
            "(PDFs, DOCX, media, etc.) organized into subfolders by module and resource type. "
            "After scanning, course content data is automatically saved so you can browse and "
            "review it in the Content tab."
        )

        _heading(run_scroll, "Download Options")
        _body(run_scroll,
            "By default, only document files (PDF, DOCX, PPTX, etc.) are downloaded. Use the "
            "checkboxes to also include video, audio, or image files. \"Include hidden content\" "
            "will pull unpublished items. \"Include inactive content\" downloads files not linked "
            "from any active page. \"Flatten folder structure\" puts all files in one "
            "directory instead of preserving the course module hierarchy."
        )

        _heading(run_scroll, "Display Options")
        _body(run_scroll,
            "Available for single-course mode only. \"Print content tree\" shows a tree of course "
            "resources that contain downloadable content. \"Print full course tree\" shows every "
            "resource in the course including empty modules and pages."
        )

        # ── Content tab ──
        content_scroll = ctk.CTkScrollableFrame(tabview.tab("Content"), fg_color="transparent")
        content_scroll.pack(fill="both", expand=True)

        _heading(content_scroll, "Content Viewer")
        _body(content_scroll,
            "Browse and review content from previously scanned courses. After running a scan "
            "with an output folder selected, course data is saved automatically and appears here."
        )

        _heading(content_scroll, "Course Selector")
        _body(content_scroll,
            "The dropdown at the top lists all courses found in your output folder. Select a "
            "course to load its content. Use the Refresh button to re-scan for new data, or "
            "Open Folder to view the course directory in File Explorer."
        )

        _heading(content_scroll, "Content Tables")
        _body(content_scroll,
            "Content is organized into tabs by type: Documents, Videos, Audio, Images, and Unsorted. "
            "Some tabs have nested sub-tabs for files vs. sites (e.g. downloadable video files vs. "
            "YouTube links). Click column headings to sort. Columns show title, type, source page, "
            "hidden status, download status, and review status."
        )

        _heading(content_scroll, "Review Status")
        _body(content_scroll,
            "Select a row and use the status buttons at the bottom to mark it as Passed, "
            "Needs Review, or Ignore. Status is saved per-course and persists across sessions. "
            "Rows are color-coded by status: green for Passed, yellow for Needs Review, "
            "and gray for Ignore."
        )

        _heading(content_scroll, "Action Buttons")
        _body(content_scroll,
            "Open File Location opens the folder containing a downloaded file. For site-type "
            "items (document sites, video sites, etc.), this button changes to Open Site and "
            "opens the URL in your browser. Open Source Page navigates to the Canvas page "
            "where the content was found."
        )

        _heading(content_scroll, "Filters")
        _body(content_scroll,
            "\"Show Inactive Content\" includes items that are not linked from any active "
            "Canvas page or are marked as hidden. By default, only active, visible content is shown."
        )

        # ── Patterns tab ──
        patterns_scroll = ctk.CTkScrollableFrame(tabview.tab("Patterns"), fg_color="transparent")
        patterns_scroll.pack(fill="both", expand=True)

        _heading(patterns_scroll, "Pattern Manager")
        _body(patterns_scroll,
            "View and edit the regex patterns that Canvas Bot uses to classify content URLs. "
            "Patterns determine whether a link is categorized as a document, video, audio, image, "
            "or other content type."
        )

        _heading(patterns_scroll, "Categories")
        _body(patterns_scroll,
            "The left panel lists all pattern categories (Documents, Video Sites, Ignore List, etc.). "
            "Click a category to view its patterns in the table on the right. The count next to each "
            "category shows how many patterns it contains."
        )

        _heading(patterns_scroll, "Editing Patterns")
        _body(patterns_scroll,
            "Select a category, then use Add Pattern to create a new regex pattern, or select "
            "an existing pattern and click Remove Pattern to delete it. Use Validate to check "
            "that a pattern's regex syntax is correct before saving."
        )

        _heading(patterns_scroll, "Test URL")
        _body(patterns_scroll,
            "Enter a URL or filename in the test box at the bottom and click Test to see which "
            "pattern categories match it. This is useful for verifying that your patterns "
            "correctly classify specific URLs."
        )

        _heading(patterns_scroll, "Reset to Defaults")
        _body(patterns_scroll,
            "The \"Reset All to Defaults\" button restores the bundled default patterns. "
            "Any custom patterns you have added will be lost."
        )

        # ── Close button ──
        close_btn = ctk.CTkButton(dialog, text="Close", width=120, command=dialog.destroy)
        close_btn.pack(pady=(5, 15))
        _add_focus_ring(close_btn)
        _underline_char(close_btn, 0)  # C
        close_btn.focus_set()

        dialog.bind("<Escape>", lambda e: dialog.destroy())
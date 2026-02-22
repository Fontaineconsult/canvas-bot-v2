import json
import logging
import os
import sys
import threading
import traceback
import customtkinter as ctk
from tkinter import filedialog

from gui.widgets import Tooltip, TextRedirector

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
        self.view.var_download_folder.set(data.get("download_folder", ""))
        self.view.var_excel_folder.set(data.get("excel_folder", ""))
        self.view.var_json_folder.set(data.get("json_folder", ""))
        self.view.var_video.set(data.get("include_video", False))
        self.view.var_audio.set(data.get("include_audio", False))
        self.view.var_image.set(data.get("include_image", False))
        self.view.var_hidden.set(data.get("include_hidden", False))
        self.view.var_flatten.set(data.get("flatten", False))
        self.view.var_content_tree.set(data.get("content_tree", False))
        self.view.var_full_tree.set(data.get("full_tree", False))
        self.validate_run()

    def save_settings(self):
        try:
            data = {
                "course_id": self.view.var_course_id.get(),
                "course_list": self.view.var_course_list.get(),
                "download_folder": self.view.var_download_folder.get(),
                "excel_folder": self.view.var_excel_folder.get(),
                "json_folder": self.view.var_json_folder.get(),
                "include_video": self.view.var_video.get(),
                "include_audio": self.view.var_audio.get(),
                "include_image": self.view.var_image.get(),
                "include_hidden": self.view.var_hidden.get(),
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

    # ── Configuration ──

    def check_config(self):
        """Check if Canvas API configuration is functional and update status bar."""
        try:
            from network.cred import check_config_status
            ok, message = check_config_status()
            if ok:
                self.view.status_label.configure(text=f"Status: {message}", text_color=("gray10", "gray90"))
            else:
                self.view.status_label.configure(text=f"Status: {message}", text_color="orange")
        except Exception:
            self.view.status_label.configure(text="Status: Configuration check failed", text_color="orange")

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
        api_btn.focus_set()
        Tooltip(api_btn, "Clear and reconfigure Canvas API token and instance URL")

        studio_btn = ctk.CTkButton(
            dialog,
            text="Reset Canvas Studio Credentials",
            width=260,
            command=lambda: [dialog.destroy(), self.launch_cli('--reset_canvas_studio_params')],
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
        has_course = self.view.var_course_id.get().strip() or self.view.var_course_list.get().strip()
        has_output = (self.view.var_download_folder.get().strip()
                      or self.view.var_excel_folder.get().strip()
                      or self.view.var_json_folder.get().strip()
                      or self.view.var_content_tree.get()
                      or self.view.var_full_tree.get())
        if has_course and has_output:
            self.view.run_btn.configure(state="normal")
        else:
            self.view.run_btn.configure(state="disabled")

    # ── Run Logic ──

    def set_status(self, text):
        self.view.root.after(0, self.view.status_label.configure, {"text": f"Status: {text}"})

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
                "flatten": self.view.var_flatten.get(),
            }

            download_folder = self.view.var_download_folder.get().strip() or None
            excel_folder = self.view.var_excel_folder.get().strip() or None
            json_folder = self.view.var_json_folder.get().strip() or None

            total = len(course_ids)
            for i, course_id in enumerate(course_ids, 1):
                self.set_status(f"Processing course {i}/{total} (ID: {course_id})...")
                print(f"\n{'='*50}")
                print(f"Course {i}/{total} — ID: {course_id}")
                print(f"{'='*50}\n")

                bot = CanvasBot(course_id)
                bot.start()

                if self.view.var_content_tree.get():
                    bot.print_content_tree()

                if self.view.var_full_tree.get():
                    bot.print_full_course()

                if download_folder:
                    bot.download_files(download_folder, **params)

                if json_folder:
                    bot.save_content_as_json(json_folder, download_folder, **params)

                if excel_folder:
                    bot.save_content_as_excel(excel_folder, **params)

            self.set_status("Complete")
            print(f"\nAll done — {total} course(s) processed.")

        except Exception as exc:
            log.exception(f"Unhandled error: {type(exc).__name__}: {exc}")
            self.set_status("Error")
            traceback.print_exc()

        finally:
            pythoncom.CoUninitialize()
            self._finish_run()

    def _finish_run(self):
        # Restore stdout/stderr
        sys.stdout = self._old_stdout
        sys.stderr = self._old_stderr

        # Re-enable controls on the main thread
        def _restore():
            self._running = False
            self.view.run_btn.configure(text="Run (Alt+R)")
            self.validate_run()

        self.view.root.after(0, _restore)

    # ── About ──

    def show_about(self):
        dialog = ctk.CTkToplevel(self.view.root)
        dialog.title("About Canvas Bot")
        dialog.geometry("520x560")
        dialog.resizable(False, False)
        dialog.transient(self.view.root)
        dialog.grab_set()

        # Center on parent
        dialog.update_idletasks()
        x = self.view.root.winfo_x() + (self.view.root.winfo_width() - 520) // 2
        y = self.view.root.winfo_y() + (self.view.root.winfo_height() - 560) // 2
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

import os
import sys
import customtkinter as ctk

from gui.widgets import _fix_tcl_paths, _add_focus_ring, Tooltip
from gui.controller import GUIController
from gui.content_viewer import ContentViewer

_fix_tcl_paths()


class CanvasBotGUI:
    def __init__(self):
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("Canvas Bot v1.2.2")
        self.root.geometry("900x800")
        self.root.minsize(700, 650)

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
        self.var_output_folder = ctk.StringVar()

        self.var_download = ctk.BooleanVar()
        self.var_excel = ctk.BooleanVar()
        self.var_json = ctk.BooleanVar()

        self.var_video = ctk.BooleanVar()
        self.var_audio = ctk.BooleanVar()
        self.var_image = ctk.BooleanVar()
        self.var_hidden = ctk.BooleanVar()
        self.var_flatten = ctk.BooleanVar()
        self.var_content_tree = ctk.BooleanVar()
        self.var_full_tree = ctk.BooleanVar()

        # --- Controller ---
        self.controller = GUIController(self)

        # --- Build UI ---
        self._build_title_bar()

        # Tabview
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        self.tabview.add("Run")
        self.tabview.add("Content")
        self.tabview.add("Patterns")

        run_tab = self.tabview.tab("Run")

        self._build_course_selection(run_tab)
        self._build_output_section(run_tab)
        self._build_options(run_tab)
        self._build_run_button(run_tab)
        self._build_output_area(run_tab)

        # Content Viewer tab
        self.content_viewer = ContentViewer(self.tabview.tab("Content"), self)

        ctk.CTkLabel(
            self.tabview.tab("Patterns"),
            text="Pattern Manager (coming soon)",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        ).pack(expand=True)

        # --- Validation bindings ---
        self.var_course_id.trace_add("write", self.controller.on_course_id_changed)
        self.var_course_list.trace_add("write", self.controller.on_course_list_changed)
        self.var_output_folder.trace_add("write", self.controller.validate_run)
        self.var_output_folder.trace_add("write", lambda *_: self.content_viewer.refresh_course_list())

        # --- Keyboard shortcuts ---
        self.root.bind("<Alt-r>", lambda e: self.controller.on_run() if self.run_btn.cget("state") == "normal" else None)
        self.root.bind("<Alt-v>", lambda e: self.controller.view_config())
        self.root.bind("<Alt-c>", lambda e: self.controller.reset_config())
        self.root.bind("<Alt-a>", lambda e: self.controller.show_about())
        self.root.bind("<Control-Key-1>", lambda e: self.tabview.set("Run"))
        self.root.bind("<Control-Key-2>", lambda e: self.tabview.set("Content"))
        self.root.bind("<Control-Key-3>", lambda e: self.tabview.set("Patterns"))

        # --- Load saved settings ---
        self.controller.load_settings()

        # --- Check configuration ---
        self.controller.check_config()

        # --- Set initial focus ---
        self.entry_course_id.focus_set()

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
            text="v1.2.2",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        ).pack(side="left", padx=(8, 0), pady=(4, 0))

        reset_btn = ctk.CTkButton(
            title_frame,
            text="Reset Config (Alt+C)",
            width=130,
            command=self.controller.reset_config,
        )
        reset_btn.pack(side="right")
        _add_focus_ring(reset_btn)
        Tooltip(reset_btn, "Reset Canvas API or Studio credentials")

        view_btn = ctk.CTkButton(
            title_frame,
            text="View Config (Alt+V)",
            width=130,
            command=self.controller.view_config,
        )
        view_btn.pack(side="right", padx=(0, 5))
        _add_focus_ring(view_btn)
        Tooltip(view_btn, "View current configuration status in a terminal")

        about_btn = ctk.CTkButton(
            title_frame,
            text="About (Alt+A)",
            width=100,
            command=self.controller.show_about,
        )
        about_btn.pack(side="right", padx=(0, 5))
        _add_focus_ring(about_btn)
        Tooltip(about_btn, "About Canvas Bot and how to use this tool")

    # ── Course Selection ──

    def _build_course_selection(self, parent):
        section = self._make_section("Course Selection", parent)

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

        browse_list_btn = ctk.CTkButton(list_frame, text="Browse", width=70, command=self.controller.browse_course_list)
        browse_list_btn.pack(side="right")
        _add_focus_ring(browse_list_btn)
        Tooltip(browse_list_btn, "Browse for a course list text file")

    # ── Output Section (single folder + action checkboxes) ──

    def _build_output_section(self, parent):
        section = self._make_section("Output", parent)

        # Folder row
        folder_row = ctk.CTkFrame(section, fg_color="transparent")
        folder_row.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(folder_row, text="Output Folder:", width=110, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(folder_row, textvariable=self.var_output_folder,
                             placeholder_text="Select a folder...")
        entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        Tooltip(entry, "Directory where all output (downloads, Excel reports, JSON) will be saved")

        browse_btn = ctk.CTkButton(folder_row, text="Browse", width=70,
                                   command=lambda: self.controller.browse_folder(self.var_output_folder))
        browse_btn.pack(side="right")
        _add_focus_ring(browse_btn)
        Tooltip(browse_btn, "Browse for output folder location")

        # Action checkboxes row
        actions_row = ctk.CTkFrame(section, fg_color="transparent")
        actions_row.pack(fill="x")

        cb_download = ctk.CTkCheckBox(actions_row, text="Download files",
                                      variable=self.var_download,
                                      command=self.controller.validate_run)
        cb_download.pack(side="left", padx=(0, 15))
        _add_focus_ring(cb_download)
        Tooltip(cb_download, "Download course documents to the output folder")

        cb_excel = ctk.CTkCheckBox(actions_row, text="Export to Excel",
                                   variable=self.var_excel,
                                   command=self.controller.validate_run)
        cb_excel.pack(side="left", padx=(0, 15))
        _add_focus_ring(cb_excel)
        Tooltip(cb_excel, "Generate Excel accessibility report in the output folder")

        cb_json = ctk.CTkCheckBox(actions_row, text="Export to JSON",
                                  variable=self.var_json,
                                  command=self.controller.validate_run)
        cb_json.pack(side="left")
        _add_focus_ring(cb_json)
        Tooltip(cb_json, "Save content inventory as JSON in the output folder")

    # ── Options ──

    def _build_options(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=(10, 0))

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

        self.cb_content_tree = ctk.CTkCheckBox(right, text="Print content tree", variable=self.var_content_tree, command=self.controller.on_content_tree_toggled)
        self.cb_content_tree.pack(anchor="w", pady=2)
        _add_focus_ring(self.cb_content_tree)
        Tooltip(self.cb_content_tree, "Print course tree showing only resources that contain content (single course only)")

        self.cb_full_tree = ctk.CTkCheckBox(right, text="Print full course tree", variable=self.var_full_tree, command=self.controller.on_full_tree_toggled)
        self.cb_full_tree.pack(anchor="w", pady=2)
        _add_focus_ring(self.cb_full_tree)
        Tooltip(self.cb_full_tree, "Print complete course tree including all resources (single course only)")

    # ── Run Button ──

    def _build_run_button(self, parent):
        run_frame = ctk.CTkFrame(parent, fg_color="transparent")
        run_frame.pack(fill="x", pady=(10, 0))

        self.run_btn = ctk.CTkButton(
            run_frame,
            text="Run (Alt+R)",
            height=36,
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled",
            command=self.controller.on_run,
        )
        self.run_btn.pack(fill="x")
        _add_focus_ring(self.run_btn)
        Tooltip(self.run_btn, "Start processing the selected course(s) with the chosen options")

    # ── Output Area ──

    def _build_output_area(self, parent):
        output_frame = ctk.CTkFrame(parent, fg_color="transparent")
        output_frame.pack(fill="both", expand=True, pady=(10, 0))

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

    def _make_section(self, title, parent=None):
        if parent is None:
            parent = self.root
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=(10, 0))

        ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 4))

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill="x", padx=10, pady=(0, 8))
        return content

    def run(self):
        self.root.mainloop()
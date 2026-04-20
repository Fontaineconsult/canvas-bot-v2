import os
import sys
import customtkinter as ctk

from gui.widgets import _fix_tcl_paths, _add_focus_ring, _underline_char, Tooltip
from gui.controller import GUIController
from gui.content_viewer import ContentViewer
from gui.pattern_manager import PatternManager

_fix_tcl_paths()

# Tab name constants
TAB_RUN = "Run"           # Alt+U
TAB_CONTENT = "Content"   # Alt+N
TAB_PATTERNS = "Patterns" # Alt+P


class CanvasBotGUI:
    def __init__(self):
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("Canvas Bot v1.2.3")
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

        self.var_video = ctk.BooleanVar()
        self.var_audio = ctk.BooleanVar()
        self.var_image = ctk.BooleanVar()
        self.var_hidden = ctk.BooleanVar()
        self.var_inactive = ctk.BooleanVar()
        self.var_flatten = ctk.BooleanVar()
        self.var_content_tree = ctk.BooleanVar()
        self.var_full_tree = ctk.BooleanVar()

        # --- Controller ---
        self.controller = GUIController(self)

        # --- Build UI ---
        self._build_title_bar()

        # Tabview
        self.tabview = ctk.CTkTabview(self.root, command=self._on_tab_changed)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(2, 5))

        self.tabview.add(TAB_RUN)
        self.tabview.add(TAB_CONTENT)
        self.tabview.add(TAB_PATTERNS)

        # Make tab selector buttons keyboard-navigable
        self._setup_tab_keyboard_nav()

        # Reduce internal top padding of tab content area
        for tab_name in (TAB_RUN, TAB_CONTENT, TAB_PATTERNS):
            tab_frame = self.tabview.tab(tab_name)
            tab_frame.configure(height=0)

        run_tab = self.tabview.tab(TAB_RUN)

        self._build_course_selection(run_tab)
        self._build_output_section(run_tab)
        self._build_options(run_tab)
        self._build_run_button(run_tab)
        self._build_output_area(run_tab)

        # Content Viewer tab
        self.content_viewer = ContentViewer(self.tabview.tab(TAB_CONTENT), self)

        # Pattern Manager tab
        self.pattern_manager = PatternManager(self.tabview.tab(TAB_PATTERNS))

        # --- Validation bindings ---
        self.var_course_id.trace_add("write", self.controller.on_course_id_changed)
        self.var_course_list.trace_add("write", self.controller.on_course_list_changed)
        self.var_output_folder.trace_add("write", self.controller.validate_run)
        self.var_output_folder.trace_add("write", lambda *_: self.content_viewer.refresh_course_list())

        # --- Keyboard shortcuts ---
        # Buttons
        self.root.bind("<Alt-r>", lambda e: self.controller.on_run() if self.run_btn.cget("state") == "normal" else None)
        self.root.bind("<Alt-v>", lambda e: self.controller.view_config())
        self.root.bind("<Alt-a>", lambda e: self.controller.show_about())
        # Tab selectors
        self.root.bind("<Alt-u>", lambda e: self.tabview.set(TAB_RUN))
        self.root.bind("<Alt-n>", lambda e: self.tabview.set(TAB_CONTENT))
        self.root.bind("<Control-Key-1>", lambda e: self.tabview.set(TAB_RUN))
        self.root.bind("<Control-Key-2>", lambda e: self.tabview.set(TAB_CONTENT))
        self.root.bind("<Control-Key-3>", lambda e: self.tabview.set(TAB_PATTERNS))

        # Content tab shortcuts (active only when Content tab is showing)
        def _on_content(cb):
            return lambda e: cb() if self.tabview.get() == TAB_CONTENT else None
        self.root.bind("<Alt-f>", _on_content(self.content_viewer.refresh_course_list))
        self.root.bind("<Alt-o>", _on_content(self.content_viewer._open_course_folder))
        self.root.bind("<Alt-s>", _on_content(self.content_viewer._open_source_page))
        self.root.bind("<Alt-w>", _on_content(lambda: self.content_viewer._on_status_changed("Needs Review")))
        self.root.bind("<Alt-i>", _on_content(lambda: self.content_viewer._on_status_changed("Ignore")))

        # Patterns tab shortcuts (active only when Patterns tab is showing)
        def _on_patterns(cb):
            return lambda e: cb() if self.tabview.get() == TAB_PATTERNS else None
        self.root.bind("<Alt-m>", _on_patterns(self.pattern_manager._on_remove))
        self.root.bind("<Alt-l>", _on_patterns(self.pattern_manager._on_validate))
        self.root.bind("<Alt-t>", _on_patterns(self.pattern_manager._on_test))

        # Shared keys — dispatch based on active tab
        def _alt_d(e):
            tab = self.tabview.get()
            if tab == TAB_CONTENT:
                self.content_viewer._on_status_changed("Passed")
            elif tab == TAB_PATTERNS:
                self.pattern_manager._on_add()
        self.root.bind("<Alt-d>", _alt_d)

        def _alt_e(e):
            tab = self.tabview.get()
            if tab == TAB_CONTENT:
                self.content_viewer._open_file_or_site()
            elif tab == TAB_PATTERNS:
                self.pattern_manager._on_reset()
        self.root.bind("<Alt-e>", _alt_e)

        def _alt_p(e):
            tab = self.tabview.get()
            if tab == TAB_CONTENT:
                self.content_viewer._open_file_direct()
            else:
                self.tabview.set(TAB_PATTERNS)
        self.root.bind("<Alt-p>", _alt_p)

        def _alt_c(e):
            tab = self.tabview.get()
            if tab == TAB_CONTENT:
                self.content_viewer._open_in_canvas()
            else:
                self.controller.reset_config()
        self.root.bind("<Alt-c>", _alt_c)

        # --- Load saved settings ---
        self.controller.load_settings()

        # --- Check configuration ---
        self.controller.check_config()

        # --- First-run welcome ---
        self.controller.show_welcome()

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
        title_frame.pack(fill="x", padx=15, pady=(5, 0))

        title_left = ctk.CTkFrame(title_frame, fg_color="transparent")
        title_left.pack(side="left")

        top_row = ctk.CTkFrame(title_left, fg_color="transparent")
        top_row.pack(anchor="w")

        ctk.CTkLabel(
            top_row,
            text="Canvas Bot",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(side="left")

        ctk.CTkLabel(
            top_row,
            text="v1.2.3",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        ).pack(side="left", padx=(8, 0), pady=(4, 0))

        ctk.CTkLabel(
            title_left,
            text="A Content bridge between the Canvas LMS and your desktop",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            height=16,
        ).pack(anchor="w")

        reset_btn = ctk.CTkButton(
            title_frame,
            text="Reset Config",
            width=130,
            command=self.controller.reset_config,
        )
        reset_btn.pack(side="right")
        _add_focus_ring(reset_btn)
        _underline_char(reset_btn, 6)  # C in Config → Alt+C
        Tooltip(reset_btn, "Reset Canvas API or Studio credentials (Alt+C)")

        view_btn = ctk.CTkButton(
            title_frame,
            text="View Config",
            width=130,
            command=self.controller.view_config,
        )
        view_btn.pack(side="right", padx=(0, 5))
        _add_focus_ring(view_btn)
        _underline_char(view_btn, 0)  # V in View → Alt+V
        Tooltip(view_btn, "View current configuration status in a terminal (Alt+V)")

        about_btn = ctk.CTkButton(
            title_frame,
            text="About",
            width=100,
            command=self.controller.show_about,
        )
        about_btn.pack(side="right", padx=(0, 5))
        _add_focus_ring(about_btn)
        _underline_char(about_btn, 0)  # A in About → Alt+A
        Tooltip(about_btn, "About Canvas Bot and how to use this tool (Alt+A)")

    # ── Course Selection ──

    def _build_course_selection(self, parent):
        section = self._make_section("Course Selection", parent)

        row = ctk.CTkFrame(section, fg_color="transparent")
        row.pack(fill="x")

        # Course ID (left, compact)
        ctk.CTkLabel(row, text="Course ID:", anchor="w").pack(side="left")
        self.entry_course_id = ctk.CTkEntry(
            row, textvariable=self.var_course_id,
            placeholder_text="e.g. 12345", width=120,
        )
        self.entry_course_id.pack(side="left", padx=(5, 0))
        _add_focus_ring(self.entry_course_id)
        Tooltip(self.entry_course_id, "Enter the Canvas course ID from the course URL: canvas.edu/courses/[ID]")

        # Separator
        ctk.CTkLabel(row, text="or", text_color="gray").pack(side="left", padx=10)

        # Course List (right, expands)
        ctk.CTkLabel(row, text="Course List:", anchor="w").pack(side="left")
        self.entry_course_list = ctk.CTkEntry(
            row, textvariable=self.var_course_list,
            placeholder_text="Path to .txt file (one ID per line)",
        )
        self.entry_course_list.pack(side="left", fill="x", expand=True, padx=(5, 5))
        _add_focus_ring(self.entry_course_list)
        Tooltip(self.entry_course_list, "Text file with one course ID per line for batch processing")

        browse_list_btn = ctk.CTkButton(row, text="Browse", width=70, command=self.controller.browse_course_list)
        browse_list_btn.pack(side="right")
        _add_focus_ring(browse_list_btn)
        _underline_char(browse_list_btn, 0)  # B
        Tooltip(browse_list_btn, "Browse for a course list text file")

    # ── Output Section (single folder + action checkboxes) ──

    def _build_output_section(self, parent):
        section = self._make_section("Output", parent)

        # Folder row
        folder_row = ctk.CTkFrame(section, fg_color="transparent")
        folder_row.pack(fill="x", pady=(0, 1))

        ctk.CTkLabel(folder_row, text="Output Folder:", width=110, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(folder_row, textvariable=self.var_output_folder,
                             placeholder_text="Select a folder...")
        entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        _add_focus_ring(entry)
        Tooltip(entry, "Directory where all output (downloads, Excel reports, JSON) will be saved")

        browse_btn = ctk.CTkButton(folder_row, text="Browse", width=70,
                                   command=lambda: self.controller.browse_folder(self.var_output_folder))
        browse_btn.pack(side="right")
        _add_focus_ring(browse_btn)
        _underline_char(browse_btn, 0)  # B
        Tooltip(browse_btn, "Browse for output folder location")

        # Action checkboxes row
        actions_row = ctk.CTkFrame(section, fg_color="transparent")
        actions_row.pack(fill="x")

        cb_download = ctk.CTkCheckBox(actions_row, text="Download files",
                                      variable=self.var_download,
                                      command=self.controller.validate_run,
                                      checkbox_width=19, checkbox_height=19)
        cb_download.pack(side="left", padx=(0, 15))
        _add_focus_ring(cb_download)
        Tooltip(cb_download, "Download course documents to the output folder")


    # ── Options ──

    def _build_options(self, parent):
        # Outer two-column layout
        columns = ctk.CTkFrame(parent, fg_color="transparent", height=0)
        columns.pack(fill="x", pady=(2, 0))
        columns.pack_propagate(True)
        columns.columnconfigure(0, weight=1)
        columns.columnconfigure(1, weight=1)

        # ── Left: Download Options (3 rows x 2 inner columns) ──
        left = ctk.CTkFrame(columns, fg_color=("gray86", "gray20"), corner_radius=6, height=0)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
        left.grid_propagate(True)

        ctk.CTkLabel(left, text="Download Options", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray", anchor="w").grid(row=0, column=0, columnspan=2, sticky="w", padx=6, pady=(3, 1))
        left.columnconfigure(0, weight=1)
        left.columnconfigure(1, weight=1)

        cb_video = ctk.CTkCheckBox(left, text="Download video files", variable=self.var_video, checkbox_width=19, checkbox_height=19)
        cb_video.grid(row=1, column=0, sticky="w", padx=6, pady=1)
        _add_focus_ring(cb_video)
        Tooltip(cb_video, "Also download video files (MP4, MOV, MKV, AVI, WebM)")

        cb_audio = ctk.CTkCheckBox(left, text="Download audio files", variable=self.var_audio, checkbox_width=19, checkbox_height=19)
        cb_audio.grid(row=1, column=1, sticky="w", padx=6, pady=1)
        _add_focus_ring(cb_audio)
        Tooltip(cb_audio, "Also download audio files (MP3, M4A, WAV, OGG)")

        cb_image = ctk.CTkCheckBox(left, text="Download image files", variable=self.var_image, checkbox_width=19, checkbox_height=19)
        cb_image.grid(row=2, column=0, sticky="w", padx=6, pady=1)
        _add_focus_ring(cb_image)
        Tooltip(cb_image, "Also download image files (JPG, PNG, GIF, SVG, WebP)")

        cb_hidden = ctk.CTkCheckBox(left, text="Include hidden/locked", variable=self.var_hidden, checkbox_width=19, checkbox_height=19)
        cb_hidden.grid(row=2, column=1, sticky="w", padx=6, pady=1)
        _add_focus_ring(cb_hidden)
        Tooltip(cb_hidden, "Include content that is hidden or unpublished in Canvas")

        cb_inactive = ctk.CTkCheckBox(left, text="Include unlinked", variable=self.var_inactive, checkbox_width=19, checkbox_height=19)
        cb_inactive.grid(row=3, column=0, sticky="w", padx=6, pady=(1, 4))
        _add_focus_ring(cb_inactive)
        Tooltip(cb_inactive, "Also download files not linked from any active Canvas page")

        cb_flatten = ctk.CTkCheckBox(left, text="Flatten folder structure", variable=self.var_flatten, checkbox_width=19, checkbox_height=19)
        cb_flatten.grid(row=3, column=1, sticky="w", padx=6, pady=(1, 4))
        _add_focus_ring(cb_flatten)
        Tooltip(cb_flatten, "Download all files to a single flat directory instead of preserving module structure")

        # ── Right: Display Options (1 row x 2 inner columns) ──
        right = ctk.CTkFrame(columns, fg_color=("gray86", "gray20"), corner_radius=6, height=0)
        right.grid(row=0, column=1, sticky="nsew", padx=(3, 0))
        right.grid_propagate(True)

        ctk.CTkLabel(right, text="Display Options", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray", anchor="w").grid(row=0, column=0, columnspan=2, sticky="w", padx=6, pady=(3, 1))
        right.columnconfigure(0, weight=1)
        right.columnconfigure(1, weight=1)

        self.cb_content_tree = ctk.CTkCheckBox(right, text="Print content tree", variable=self.var_content_tree, command=self.controller.on_content_tree_toggled, checkbox_width=19, checkbox_height=19)
        self.cb_content_tree.grid(row=1, column=0, sticky="w", padx=6, pady=(1, 4))
        _add_focus_ring(self.cb_content_tree)
        Tooltip(self.cb_content_tree, "Print course tree showing only resources that contain content (single course only)")

        self.cb_full_tree = ctk.CTkCheckBox(right, text="Print full course tree", variable=self.var_full_tree, command=self.controller.on_full_tree_toggled, checkbox_width=19, checkbox_height=19)
        self.cb_full_tree.grid(row=1, column=1, sticky="w", padx=6, pady=(1, 4))
        _add_focus_ring(self.cb_full_tree)
        Tooltip(self.cb_full_tree, "Print complete course tree including all resources (single course only)")

    # ── Run Button ──

    def _build_run_button(self, parent):
        self.run_btn = ctk.CTkButton(
            parent,
            text="Run",
            height=32,
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled",
            command=self.controller.on_run,
        )
        self.run_btn.pack(fill="x", pady=(2, 0))
        _add_focus_ring(self.run_btn)
        _underline_char(self.run_btn, 0)  # R in Run → Alt+R
        Tooltip(self.run_btn, "Start processing the selected course(s) with the chosen options (Alt+R)")

    # ── Output Area ──

    def _build_output_area(self, parent):
        self.status_label = ctk.CTkLabel(
            parent,
            text="Status: Ready",
            anchor="w",
            font=ctk.CTkFont(size=12),
        )
        self.status_label.pack(fill="x", pady=(2, 0))

        self.log_text = ctk.CTkTextbox(
            parent,
            font=ctk.CTkFont(family="Consolas", size=12),
            state="disabled",
        )
        self.log_text.pack(fill="both", expand=True)

    # ── Section Helper ──

    def _make_section(self, title, parent=None):
        if parent is None:
            parent = self.root

        ctk.CTkLabel(
            parent,
            text=title,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray",
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        content = ctk.CTkFrame(parent, fg_color="transparent", height=0)
        content.pack(fill="x", pady=(0, 0))
        content.pack_propagate(True)
        return content

    def _on_tab_changed(self):
        if self.tabview.get() == TAB_CONTENT:
            self.content_viewer.refresh_course_list()

    def _setup_tab_keyboard_nav(self):
        """Make the tab selector buttons focusable with Left/Right arrow navigation."""
        tab_names = [TAB_RUN, TAB_CONTENT, TAB_PATTERNS]
        try:
            buttons = self.tabview._segmented_button._buttons_dict
        except AttributeError:
            return

        for name in tab_names:
            btn = buttons.get(name)
            if not btn:
                continue
            _add_focus_ring(btn)

            def _nav(event, current=name, direction=0):
                idx = tab_names.index(current) + direction
                if 0 <= idx < len(tab_names):
                    target = tab_names[idx]
                    self.tabview.set(target)
                    buttons[target].focus_set()
                return "break"

            btn.bind("<Left>", lambda e, n=name: _nav(e, n, -1))
            btn.bind("<Right>", lambda e, n=name: _nav(e, n, 1))

    def run(self):
        self.root.mainloop()
# CLAUDE.md - Canvas Bot v2 Project Guide

## Quick Reference

| | |
|---|---|
| **Project** | Canvas Bot v2 |
| **Version** | 0.1.6-alpha |
| **Language** | Python 3.12+ |
| **Platform** | Windows only |
| **Purpose** | CLI tool for downloading and auditing Canvas LMS course content |

## What This Project Does

Canvas Bot is a command-line tool that:
1. Connects to Canvas LMS via REST API
2. Discovers all content in a course (modules, pages, assignments, quizzes, files, media)
3. Extracts and categorizes embedded links (documents, videos, audio, images)
4. Downloads files to organized folder structures
5. Exports content inventories to Excel/JSON for accessibility auditing

## Project Structure

```
canvas-bot-v2/
├── canvas_bot.py              # Main CLI entry point
├── config/
│   ├── config.yaml            # App settings, version
│   ├── re.yaml                # Regex patterns for content classification
│   ├── yaml_io.py             # YAML read/write with PyInstaller support
│   └── download_manifest.yaml # Template for tracking downloads
├── core/
│   ├── course_root.py         # Course initialization, tree building
│   ├── content_extractor.py   # Content filtering, JSON/Excel export
│   ├── content_scaffolds.py   # Dict builders for export
│   ├── downloader.py          # DownloaderMixin for file downloads
│   ├── manifest.py            # Deduplication tracker
│   └── node_factory.py        # Factory for creating node instances
├── resource_nodes/
│   ├── base_node.py           # Base class for Canvas resources
│   ├── base_content_node.py   # Base class for content items
│   ├── content_nodes.py       # Document, Video, Audio, Image nodes
│   ├── modules.py             # Module/ModuleItem handlers
│   ├── pages.py               # Page handler
│   ├── assignments.py         # Assignment handler
│   ├── quizzes.py             # Quiz handler
│   ├── discussions.py         # Discussion handler
│   ├── announcements.py       # Announcement handler
│   ├── files.py               # Canvas Files handler
│   ├── media_objects.py       # Canvas Media Objects handler
│   ├── canvas_studio.py       # Canvas Studio integration
│   └── scraper.py             # HTML parsing (BeautifulSoup)
├── external_content_nodes/
│   └── box.py                 # Box.com folder extraction
├── network/
│   ├── api.py                 # Canvas LMS API wrapper
│   ├── studio_api.py          # Canvas Studio API wrapper
│   ├── cred.py                # Credential management (keyring)
│   └── set_config.py          # Config file management
├── sorters/
│   └── sorters.py             # Compiled regex matchers
├── tools/
│   ├── export_to_excel.py     # Excel workbook generation
│   ├── canvas_tree.py         # Tree visualization (treelib)
│   ├── logger.py              # Rotating file logger
│   ├── captioning_check.py    # YouTube caption API
│   ├── course_extractor.py    # Course list export
│   └── vba/                   # Excel macro templates
└── claude/                    # Detailed documentation
```

## CLI Reference

### Course Processing
```bash
# Basic - download documents from a course
python canvas_bot.py --course_id 12345 --download_folder ./downloads

# Export to Excel for accessibility audit
python canvas_bot.py --course_id 12345 --output_as_excel ./reports

# Include all media types
python canvas_bot.py --course_id 12345 --download_folder ./downloads \
    --include_video_files --include_audio_files --include_image_files

# Batch processing multiple courses
python canvas_bot.py --course_id_list courses.txt --output_as_excel ./reports
```

### Pattern Management (re.yaml CRUD)
```bash
# List all pattern categories
python canvas_bot.py --patterns-list

# List patterns in a specific category
python canvas_bot.py --patterns-list document_content_regex

# Add a pattern (with confirmation)
python canvas_bot.py --patterns-add document_content_regex ".*\.odt"

# Add without confirmation
python canvas_bot.py --patterns-add document_content_regex ".*\.odt" -y

# Remove a pattern
python canvas_bot.py --patterns-remove document_content_regex ".*\.odt" -y

# Test what categories match a URL/filename
python canvas_bot.py --patterns-test "myfile.pdf"
python canvas_bot.py --patterns-test "https://youtube.com/watch?v=abc123"

# Validate regex syntax
python canvas_bot.py --patterns-validate ".*\.pdf"

# Reset patterns to bundled defaults
python canvas_bot.py --patterns-reset -y
```

### Configuration
```bash
# Show current configuration status
python canvas_bot.py --config_status

# Reset Canvas API credentials
python canvas_bot.py --reset_canvas_params

# Reset Canvas Studio OAuth
python canvas_bot.py --reset_canvas_studio_params

# Export course list to CSV
python canvas_bot.py --export_course_list --semester_filter fa24
```

---

## Architecture Deep Dive

### Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLI (canvas_bot.py)                           │
│  Click parses args → Pattern mgmt OR config OR course processing       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        ┌─────────────────────┐         ┌─────────────────────┐
        │ Pattern Management  │         │ Course Processing   │
        │ (early exit)        │         │                     │
        └─────────────────────┘         └──────────┬──────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────────────────┐
                    │                              │                              │
                    ▼                              ▼                              ▼
        ┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
        │ Load Credentials    │     │ Load Config         │     │ Canvas Studio OAuth │
        │ (keyring)           │     │ (AppData JSON)      │     │ (if enabled)        │
        └─────────────────────┘     └─────────────────────┘     └─────────────────────┘
                    │                              │                              │
                    └──────────────────────────────┼──────────────────────────────┘
                                                   ▼
                              ┌─────────────────────────────────┐
                              │ CanvasBot(course_id)            │
                              │   └── CanvasCourseRoot          │
                              │         └── ContentExtractor    │
                              │               └── DownloaderMixin│
                              └─────────────────────────────────┘
                                                   │
                                                   ▼
                              ┌─────────────────────────────────┐
                              │ initialize_course()             │
                              │   ├── Fetch course metadata     │
                              │   └── _init_modules_root()      │
                              └─────────────────────────────────┘
                                                   │
        ┌──────────────────────────────────────────┼──────────────────────────────────────────┐
        │                    │                     │                     │                    │
        ▼                    ▼                     ▼                     ▼                    ▼
   ┌─────────┐        ┌───────────┐         ┌───────────┐         ┌───────────┐        ┌───────────┐
   │ Modules │        │ Pages     │         │Assignments│         │ Quizzes   │        │Discussions│
   └────┬────┘        └─────┬─────┘         └─────┬─────┘         └─────┬─────┘        └─────┬─────┘
        │                   │                     │                     │                    │
        └───────────────────┴─────────────────────┴─────────────────────┴────────────────────┘
                                                   │
                                                   ▼
                              ┌─────────────────────────────────┐
                              │ For each resource:              │
                              │   1. API call → fetch items     │
                              │   2. Parse HTML body            │
                              │   3. Extract <a>, <iframe> URLs │
                              │   4. Classify via regex         │
                              │   5. Create content nodes       │
                              │   6. Add to Manifest            │
                              └─────────────────────────────────┘
                                                   │
                         ┌─────────────────────────┼─────────────────────────┐
                         ▼                         ▼                         ▼
              ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
              │ download_files()   │   │ save_content_as_    │   │ save_content_as_    │
              │   → Folder struct  │   │ json()              │   │ excel()             │
              │   → HTTP downloads │   │   → Nested dict     │   │   → Multi-sheet     │
              │   → .lnk shortcuts │   │   → JSON file       │   │   → Dropdowns       │
              └─────────────────────┘   └─────────────────────┘   └─────────────────────┘
```

### Node Hierarchy

```
Node (base_node.py) ─────────────────────────────────────────────────────────────────────┐
│  Base class for Canvas organizational resources                                        │
│  Properties: parent, root, children, item_id, title, is_resource=True                  │
│  Methods: add_node_to_tree(), add_data_api_link_to_children(),                        │
│           add_content_nodes_to_children()                                              │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│  Subclasses (resource_nodes/):                                                         │
│  ├── Modules        → Container for Module items                                       │
│  │   └── Module     → Individual module with children                                  │
│  ├── Pages          → Container for Page items                                         │
│  │   └── Page       → Individual page with HTML body                                   │
│  ├── Assignments    → Container for Assignment items                                   │
│  │   └── Assignment → Individual assignment with description                           │
│  ├── Quizzes        → Container for Quiz items                                         │
│  │   └── Quiz       → Individual quiz with description                                 │
│  ├── Discussions    → Container for Discussion items                                   │
│  │   └── Discussion → Individual discussion topic                                      │
│  ├── Announcements  → Container for Announcement items                                 │
│  │   └── Announcement → Individual announcement                                        │
│  ├── CanvasFiles    → Container for course files                                       │
│  ├── CanvasMediaObjects → Container for media objects                                  │
│  └── CanvasStudio   → Container for Canvas Studio videos                               │
└────────────────────────────────────────────────────────────────────────────────────────┘

BaseContentNode (base_content_node.py) ──────────────────────────────────────────────────┐
│  Base class for leaf content items (actual files/links)                                │
│  Properties: api_dict, url, title, parent, download_url, file_name, captioned          │
│  Auto-registers with Manifest and CanvasTree on creation                               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│  Subclasses (resource_nodes/content_nodes.py):                                         │
│  ├── Document           → Downloadable file (PDF, DOCX, PPTX, etc.)                    │
│  ├── DocumentSite       → Web document (Google Docs, OneDrive, etc.)                   │
│  ├── VideoFile          → Downloadable video (MP4, MOV, MKV, etc.)                     │
│  ├── VideoSite          → Web video (YouTube, Vimeo, etc.)                             │
│  ├── AudioFile          → Downloadable audio (MP3, M4A, WAV, etc.)                     │
│  ├── AudioSite          → Web audio (podcasts, etc.)                                   │
│  ├── ImageFile          → Downloadable image (JPG, PNG, GIF, etc.)                     │
│  ├── FileStorageSite    → Cloud storage (Box.com) - parent of BoxPage                  │
│  ├── CanvasMediaEmbed   → Canvas-hosted media (file embeds)                            │
│  ├── CanvasStudioEmbed  → Canvas Studio video embed                                    │
│  ├── DigitalTextbook    → E-textbook links                                             │
│  └── Unsorted           → Unclassified content                                         │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Content Classification Pipeline

```
URL discovered (from HTML parsing or API)
                │
                ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  node_factory.py :: identify_content_url(url)                             │
│                                                                           │
│  Tests URL against compiled regex patterns from sorters/sorters.py:       │
│                                                                           │
│  1. ignore_list_regex      → Return None (skip entirely)                  │
│  2. document_content_regex → Return "Document"                            │
│  3. image_content_regex    → Return "ImageFile"                           │
│  4. web_video_resources    → Return "VideoSite"                           │
│  5. video_file_resources   → Return "VideoFile"                           │
│  6. web_audio_resources    → Return "AudioSite"                           │
│  7. audio_file_resources   → Return "AudioFile"                           │
│  8. web_document_apps      → Return "DocumentSite"                        │
│  9. canvas_studio_embed    → Return "CanvasStudioEmbed"                   │
│ 10. canvas_file_embed      → Return "CanvasMediaEmbed"                    │
│ 11. canvas_media_embed     → Return "CanvasMediaEmbed"                    │
│ 12. file_storage_regex     → Return "FileStorageSite"                     │
│ 13. (no match)             → Return "Unsorted"                            │
└───────────────────────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  node_factory.py :: get_content_node(url, api_dict)                       │
│                                                                           │
│  Maps type string to class and instantiates:                              │
│  "Document" → Document(api_dict, parent, root)                            │
│  "VideoSite" → VideoSite(api_dict, parent, root)                          │
│  etc.                                                                     │
└───────────────────────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  Manifest.add(content_node)                                               │
│                                                                           │
│  Deduplication: Checks if item_id already exists                          │
│  If new → adds to manifest dict and tree                                  │
│  If duplicate → skips                                                     │
└───────────────────────────────────────────────────────────────────────────┘
```

### Regex Pattern Categories (config/re.yaml)

| Category | Purpose | Examples |
|----------|---------|----------|
| `document_content_regex` | Downloadable documents | `.*\.pdf`, `.*\.docx`, `.*\.pptx` |
| `image_content_regex` | Image files | `.*\.jpg`, `.*\.png`, `.*\.gif` |
| `web_video_resources_regex` | Web video hosts | `.*youtube.*`, `.*vimeo.*`, `.*zoom.us.*` |
| `video_file_resources_regex` | Video files | `.*\.mp4`, `.*\.mov`, `.*\.mkv` |
| `web_audio_resources_regex` | Web audio hosts | `.*\/podcast\/.*`, `.*\/audio\/.*` |
| `audio_file_resources_regex` | Audio files | `.*\.mp3`, `.*\.m4a`, `.*\.wav` |
| `web_document_applications_regex` | Cloud docs | `docs.google.com`, `acrobat.adobe.com` |
| `canvas_studio_embed` | Canvas Studio | `.*{CANVAS_STUDIO_DOMAIN}.*` |
| `canvas_file_embed` | Canvas file embeds | Canvas iframe patterns |
| `file_storage_regex` | Cloud storage | `.*box.com.*`, `.*drive.google.com.*` |
| `ignore_list_regex` | Skip entirely | Wikipedia, community forums |
| `force_to_shortcut` | Can't download directly | DocuSign, certain Box links |

**Note:** Patterns use `{PLACEHOLDER}` syntax for institution-specific domains (e.g., `{CANVAS_DOMAIN}`), substituted at runtime from environment variables.

### Download Flow Detail

```
DownloaderMixin.download(content_nodes, root_directory, **params)
                │
                ├── Load download_manifest.yaml (tracks completed downloads)
                │
                ├── Filter nodes based on params:
                │   ├── Always: Documents
                │   ├── --include_video_files: VideoFile, CanvasStudioEmbed, CanvasMediaEmbed
                │   ├── --include_audio_files: AudioFile
                │   ├── --include_image_files: ImageFile
                │   └── --download_hidden_files: Include hidden content
                │
                └── For each content node:
                        │
                        ├── Check manifest → Skip if already downloaded
                        │
                        ├── path_constructor(node) → Build full Windows path
                        │   │
                        │   ├── root_directory/
                        │   │   └── YYYY-MM-DD/
                        │   │       └── Module Name/
                        │   │           └── Assignment Name/
                        │   │               └── Documents/
                        │   │                   └── filename.pdf
                        │   │
                        │   ├── Sanitize: Remove invalid Windows chars
                        │   ├── Truncate: Handle 260-char path limit
                        │   └── Long path prefix: \\?\ for paths > 260
                        │
                        ├── derive_file_name(node) → Determine filename
                        │   │
                        │   ├── 1. Canvas Studio → node.title + .mp4
                        │   ├── 2. Has file_name attr → Use it
                        │   ├── 3. Has filename attr → Use it
                        │   ├── 4. Extract from URL
                        │   └── 5. Fallback → $$-prefix (forces shortcut)
                        │
                        ├── _download_file(url, path, force_to_shortcut)
                        │   │
                        │   ├── If force_to_shortcut=True:
                        │   │   └── create_windows_shortcut_from_url()
                        │   │
                        │   └── Else: HTTP GET with streaming
                        │       ├── Success → Write to file (8KB chunks)
                        │       └── Failure (401-406, SSL, etc.) → Create shortcut
                        │
                        └── Update download_manifest.yaml
```

---

## Configuration & Credentials

### Storage Locations

| Data | Location | Format |
|------|----------|--------|
| Canvas API Token | Windows Credential Vault | Encrypted |
| Studio Client ID/Secret | Windows Credential Vault | Encrypted |
| Studio Access/Refresh Tokens | Windows Credential Vault | Encrypted |
| Instance Config | `%APPDATA%\canvas bot\config.json` | JSON |
| User Patterns | `%APPDATA%\canvas bot\re.yaml` | YAML |
| Logs | `%APPDATA%\canvas bot\canvas_bot.log` | Text (rotating) |

### Environment Variables (set at runtime)

| Variable | Source | Purpose |
|----------|--------|---------|
| `ACCESS_TOKEN` | Credential Vault | Canvas API auth |
| `CANVAS_COURSE_PAGE_ROOT` | config.json | Canvas URL |
| `API_PATH` | config.json | API endpoint |
| `CANVAS_DOMAIN` | config.json | Institution subdomain |
| `CANVAS_STUDIO_DOMAIN` | config.json | Studio subdomain |
| `BOX_DOMAIN` | config.json | Box.com subdomain |
| `LIBRARY_PROXY_DOMAIN` | config.json | Library proxy |

---

## PyInstaller Compatibility

The application is designed to compile to a single .exe with PyInstaller.

### Key Considerations

1. **Bundled Resources**: `config.yaml`, `re.yaml`, `download_manifest.yaml` are bundled via spec file
2. **User-Editable Patterns**: `re.yaml` is copied to AppData on first run for user modifications
3. **Path Resolution**: `_get_bundled_path()` uses `sys._MEIPASS` when frozen

### How It Works

```
PyInstaller .exe (frozen)
        │
        ├── Bundled: config/re.yaml (default patterns)
        │   └── Read-only, in sys._MEIPASS temp directory
        │
        └── First run: Copy to %APPDATA%\canvas bot\re.yaml
            └── User-editable, persistent across runs

yaml_io.py:
├── _get_bundled_path(file) → sys._MEIPASS/config/file (if frozen)
│                           → source/config/file (if dev)
│
├── _get_user_re_path() → %APPDATA%\canvas bot\re.yaml
│   └── Auto-creates from bundled default if missing
│
├── read_re() → Reads from user path (creates if needed)
├── write_re() → Writes to user path
└── reset_re() → Deletes user copy (next read recreates from bundled)
```

---

## Design Patterns

| Pattern | Implementation | Purpose |
|---------|----------------|---------|
| **Factory** | `node_factory.py` | Dynamic node instantiation based on regex matching |
| **Mixin** | `DownloaderMixin` | Add download capability to ContentExtractor |
| **Decorator** | `@response` in api.py | Centralize API error handling and JSON parsing |
| **Template Method** | Node hierarchy | Base classes define structure, subclasses customize |
| **Composite** | CanvasTree | Hierarchical parent-child content organization |
| **Singleton-like** | Manifest | Global deduplication tracker |

---

## Common Development Tasks

### Add New Content Type
1. Add regex pattern to `config/re.yaml` under appropriate category
2. If new category: Create class in `resource_nodes/content_nodes.py`
3. Update `node_factory.py::identify_content_url()` if new category
4. Update `sorters/sorters.py` to compile new pattern

### Add New Canvas Resource Type
1. Create handler class in `resource_nodes/` (extend `Node`)
2. Initialize in `core/course_root.py::_init_modules_root()`
3. Add getter method in `core/content_extractor.py`

### Add New External Service
1. Create handler in `external_content_nodes/`
2. Add detection pattern to `config/re.yaml`
3. Update `node_factory.py` to return new class

### Modify Excel Export
1. Edit column definitions in `tools/export_to_excel.py`
2. Update `tracking_columns` dict for new tracking fields
3. Modify VBA templates in `tools/vba/` if needed

### Test Pattern Changes
```bash
# Validate syntax before adding
python canvas_bot.py --patterns-validate "your-pattern-here"

# Test matching
python canvas_bot.py --patterns-test "https://example.com/file.pdf"

# Add and verify
python canvas_bot.py --patterns-add category_name "pattern" -y
python canvas_bot.py --patterns-list category_name
```

---

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `requests` | HTTP client for API calls |
| `beautifulsoup4` | HTML parsing for link extraction |
| `click` | CLI framework |
| `openpyxl` | Excel workbook generation |
| `keyring` | Windows Credential Vault access |
| `pywin32` | Windows shortcuts (.lnk) creation |
| `treelib` | Tree visualization |
| `PyYAML` | YAML config parsing |
| `colorama` | Terminal color output |

---

## See Also

- `claude/ARCHITECTURE.md` - Detailed layer diagrams and data flows
- `claude/MODULES.md` - Complete module-by-module API reference
- `claude/CONFIG.md` - Configuration and setup guide
- `readme.md` - User documentation

# Architecture Documentation

## System Overview

Canvas Bot v2 is a layered application that discovers, categorizes, and exports content from Canvas LMS courses.

## Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLI Layer (canvas_bot.py)                    │
│                  Click commands, argument parsing               │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Core Layer (core/)                            │
│  ┌─────────────┐  ┌──────────────────┐  ┌──────────────┐       │
│  │ CourseRoot  │  │ ContentExtractor │  │  Downloader  │       │
│  └─────────────┘  └──────────────────┘  └──────────────┘       │
│  ┌─────────────┐  ┌──────────────────┐  ┌──────────────┐       │
│  │ NodeFactory │  │    Manifest      │  │   Scaffolds  │       │
│  └─────────────┘  └──────────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│               Resource Nodes Layer (resource_nodes/)            │
│  ┌─────────┐ ┌───────┐ ┌─────────────┐ ┌─────────┐ ┌─────────┐ │
│  │ Modules │ │ Pages │ │ Assignments │ │ Quizzes │ │ Files   │ │
│  └─────────┘ └───────┘ └─────────────┘ └─────────┘ └─────────┘ │
│  ┌─────────────┐ ┌───────────────┐ ┌─────────────────────────┐ │
│  │ Discussions │ │ Announcements │ │ Canvas Studio/Media     │ │
│  └─────────────┘ └───────────────┘ └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│               Content Nodes Layer (resource_nodes/)             │
│  ┌──────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────────┐│
│  │ Document │ │ VideoFile │ │ AudioFile │ │ ImageFile         ││
│  └──────────┘ └───────────┘ └───────────┘ └───────────────────┘│
│  ┌───────────┐ ┌───────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │ VideoSite │ │ AudioSite │ │ DocumentSite │ │ FileStorage  │ │
│  └───────────┘ └───────────┘ └──────────────┘ └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Network Layer (network/)                      │
│  ┌─────────┐  ┌─────────────┐  ┌─────────┐  ┌──────────────┐   │
│  │   API   │  │ Studio API  │  │  Cred   │  │  SetConfig   │   │
│  └─────────┘  └─────────────┘  └─────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                   External Services                             │
│  ┌────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Canvas LMS API │  │ Canvas Studio   │  │ YouTube API     │  │
│  └────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Initialization Flow

```
User runs CLI
      │
      ▼
┌─────────────────┐
│ Load credentials│ ─────► Windows Credential Vault (keyring)
│ from vault      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Load config     │ ─────► %APPDATA%\canvas bot\config.json
│ from AppData    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Set environment │ ─────► ACCESS_TOKEN, API_PATH, etc.
│ variables       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Initialize      │
│ CanvasCourseRoot│
└─────────────────┘
```

### 2. Content Discovery Flow

```
CanvasCourseRoot.initialize_course()
         │
         ├──► Fetch course metadata (API)
         │
         ├──► Initialize resource roots:
         │    ├── CanvasStudio (if enabled)
         │    ├── Modules
         │    ├── Quizzes
         │    ├── Assignments
         │    ├── Announcements
         │    ├── Discussions
         │    ├── Pages
         │    ├── CanvasFiles
         │    └── CanvasMediaObjects
         │
         ▼
Each resource root:
         │
         ├──► API call to fetch items
         │
         ├──► Parse HTML body for embedded links
         │    └── BeautifulSoup extracts <a>, <iframe>
         │
         ├──► Classify each URL via regex (re.yaml)
         │    └── NodeFactory.get_content_node()
         │
         └──► Add to Manifest (deduplication)
```

### 3. Content Classification Flow

```
URL discovered
      │
      ▼
┌─────────────────┐
│ NodeFactory.    │
│ identify_       │
│ content_url()   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────────┐
│ Match against   │ ──► │ Patterns from       │
│ regex patterns  │     │ config/re.yaml      │
└────────┬────────┘     └─────────────────────┘
         │
         ▼
┌─────────────────┐
│ Return content  │ ──► Document, VideoFile, VideoSite,
│ type identifier │     AudioFile, ImageFile, etc.
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ NodeFactory.    │
│ get_content_    │ ──► Instantiate appropriate class
│ node()          │
└─────────────────┘
```

### 4. Download Flow

```
ContentExtractor.download_files()
         │
         ├──► Get content nodes by type
         │    └── get_document_objects(), get_video_file_objects(), etc.
         │
         ▼
For each content node:
         │
         ├──► Build file path
         │    └── ContentScaffolds.build_path()
         │
         ├──► Check download manifest
         │    └── Skip if already downloaded
         │
         ├──► Download file
         │    └── requests.get() with streaming
         │
         ├──► Handle failures
         │    └── Create Windows shortcut (.lnk) as fallback
         │
         └──► Update download manifest
```

### 5. Export Flow

```
ContentExtractor.save_content_as_excel()
         │
         ├──► Get all content by type
         │
         ├──► Create workbook (openpyxl)
         │
         ├──► Create sheets:
         │    ├── Documents
         │    ├── Document Sites
         │    ├── Videos (files)
         │    ├── Video Sites
         │    ├── Audio (files)
         │    ├── Audio Sites
         │    ├── Images
         │    └── Unsorted
         │
         ├──► Add data validation (dropdowns)
         │
         ├──► Add conditional formatting
         │
         └──► Save as .xlsm (macro-enabled)
```

## Class Hierarchy

### Resource Nodes

```
BaseNode (abstract)
    │
    ├── Modules
    ├── ModuleItem
    ├── Page
    ├── Assignment
    ├── Quiz
    ├── Discussion
    ├── Announcement
    ├── CanvasFile
    ├── CanvasFolder
    ├── CanvasMediaObjects
    └── CanvasStudio
```

### Content Nodes

```
BaseContentNode (abstract)
    │
    ├── Document
    ├── VideoFile
    ├── VideoSite
    ├── AudioFile
    ├── AudioSite
    ├── ImageFile
    ├── DocumentSite
    ├── FileStorageSite
    ├── DigitalTextbook
    ├── CanvasMediaEmbed
    ├── CanvasStudioEmbed
    └── Unsorted
```

## Design Patterns

### Factory Pattern (node_factory.py)

```python
# Determines node type and instantiates appropriate class
node = NodeFactory.get_node(item_type, data)
content_node = NodeFactory.get_content_node(url, metadata)
```

**Purpose:** Centralizes object creation logic, allows easy extension of content types.

### Mixin Pattern (downloader.py)

```python
class DownloaderMixin:
    def download(self):
        # Download logic shared across classes

class CanvasCourseRoot(ContentExtractor, DownloaderMixin):
    pass
```

**Purpose:** Adds download capability to any class that needs it.

### Decorator Pattern (api.py)

```python
def response(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs).json()
        except HTTPError as e:
            # Error handling
    return wrapper

@response
def get_course(course_id):
    return requests.get(...)
```

**Purpose:** Centralizes API error handling and response parsing.

## Error Handling Strategy

1. **API Errors:** Logged and handled gracefully; operations continue with available data
2. **Download Failures:** Create shortcut to URL instead of failing completely
3. **Missing Content:** Logged as warning; skipped without stopping
4. **Credential Errors:** User prompted to reconfigure

## Security Considerations

- API tokens stored in Windows Credential Vault (encrypted)
- OAuth tokens auto-refresh without user intervention
- No credentials stored in code or config files
- Environment variables cleared after use

## Performance Considerations

- Streaming downloads for large files
- Deduplication via Manifest prevents re-processing
- Download manifest tracks completed downloads
- Rotating log files prevent disk space issues

## Extension Points

1. **New Content Types:** Add regex to re.yaml, class to content_nodes.py
2. **New Canvas Resources:** Add handler to resource_nodes/, init in course_root.py
3. **New Export Formats:** Add exporter to tools/
4. **New External Services:** Add handler to external_content_nodes/

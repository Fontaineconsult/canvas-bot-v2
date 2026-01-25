# Module Reference

## Entry Point

### canvas_bot.py
**Purpose:** Main CLI entry point and application bootstrapping

**Key Classes:**
- `CanvasBot` - Main application class

**Key Functions:**
- `cli()` - Click command group entry point
- `start()` - Initialize and run course processing

**CLI Flags:**
| Flag | Type | Description |
|------|------|-------------|
| `--course_id` | TEXT | Single course ID to process |
| `--course_id_list` | TEXT | File containing course IDs |
| `--download_folder` | TEXT | Destination for downloads |
| `--output_as_json` | TEXT | JSON export directory |
| `--output_as_excel` | TEXT | Excel export directory |
| `--include_video_files` | FLAG | Include video file downloads |
| `--include_audio_files` | FLAG | Include audio file downloads |
| `--include_image_files` | FLAG | Include image file downloads |
| `--flatten` | FLAG | Flatten directory structure |
| `--download_hidden_files` | FLAG | Include hidden content |
| `--show_content_tree` | FLAG | Display course tree |
| `--reset_canvas_params` | FLAG | Reset API credentials |
| `--reset_canvas_studio_params` | FLAG | Reset Studio OAuth |

---

## Core Module (core/)

### course_root.py
**Purpose:** Root class for course initialization and content tree building

**Key Classes:**
- `CanvasCourseRoot(ContentExtractor)` - Extends ContentExtractor with course initialization

**Key Methods:**
- `initialize_course()` - Fetch course data and build content tree
- `_init_modules_root()` - Initialize all resource type roots

**Usage:**
```python
root = CanvasCourseRoot(course_id, options)
root.initialize_course()
```

---

### content_extractor.py
**Purpose:** Organizes discovered content and provides export functionality

**Key Classes:**
- `ContentExtractor` - Mixin providing content organization methods

**Key Methods:**
- `get_document_objects()` - Returns list of Document nodes
- `get_video_file_objects()` - Returns list of VideoFile nodes
- `get_video_site_objects()` - Returns list of VideoSite nodes
- `get_audio_file_objects()` - Returns list of AudioFile nodes
- `get_image_file_objects()` - Returns list of ImageFile nodes
- `get_unsorted_objects()` - Returns list of Unsorted nodes
- `save_content_as_json(path)` - Export all content to JSON
- `save_content_as_excel(path)` - Export all content to Excel
- `download_files()` - Download all applicable content

---

### content_scaffolds.py
**Purpose:** Utility functions for path building and metadata extraction

**Key Functions:**
- `build_path(node, root_path)` - Construct full file path for download
- `is_hidden(node)` - Check if content is hidden in Canvas
- `get_order(node)` - Get sort order from module position
- `get_source_page_url(node)` - Get Canvas page URL where content was found
- `build_document_dict(node)` - Build metadata dict for document
- `build_video_dict(node)` - Build metadata dict for video
- `build_audio_dict(node)` - Build metadata dict for audio

---

### downloader.py
**Purpose:** File download functionality with fallback to shortcuts

**Key Classes:**
- `DownloaderMixin` - Mixin providing download capability

**Key Methods:**
- `download()` - Main download orchestrator
- `_download_file(url, path)` - Perform HTTP download
- `_create_shortcut(url, path)` - Create Windows .lnk shortcut
- `_derive_filename(url, content_node)` - Determine filename from URL/metadata
- `_construct_path(node)` - Build Windows-compatible file path

**Download Manifest:**
Tracks downloaded files in `config/download_manifest.yaml` to prevent re-downloads.

---

### node_factory.py
**Purpose:** Factory for creating resource and content node instances

**Key Functions:**
- `get_node(item_type, data)` - Create resource node (Module, Page, Assignment, etc.)
- `get_content_node(url, metadata)` - Create content node (Document, VideoFile, etc.)
- `identify_content_url(url)` - Classify URL into content type using regex

**Supported Resource Types:**
- `Module`, `Page`, `Assignment`, `Quiz`, `Discussion`, `File`, `SubHeader`

**Content Type Detection:**
Uses patterns from `config/re.yaml` to classify URLs.

---

### manifest.py
**Purpose:** In-memory storage of discovered content nodes

**Key Classes:**
- `Manifest` - Singleton-like storage for all discovered nodes

**Key Methods:**
- `add_node(node)` - Add node if not duplicate
- `get_all_nodes()` - Return all stored nodes
- `get_nodes_by_type(type)` - Filter nodes by content type

---

### scraper.py
**Purpose:** HTML parsing utilities for content extraction

**Key Functions:**
- `extract_links_from_html(html)` - Extract all links from HTML body
- `parse_canvas_page(html)` - Parse Canvas page HTML structure

---

## Network Module (network/)

### api.py
**Purpose:** Canvas LMS REST API wrapper

**Key Decorators:**
- `@response` - Handles HTTP errors and JSON parsing

**Key Functions:**
| Function | API Endpoint |
|----------|--------------|
| `get_course(id)` | GET /courses/{id} |
| `get_announcements(id)` | GET /courses/{id}/discussion_topics |
| `get_assignments(id)` | GET /courses/{id}/assignments |
| `get_discussions(id)` | GET /courses/{id}/discussion_topics |
| `get_modules(id)` | GET /courses/{id}/modules |
| `get_module_items(course_id, module_id)` | GET /courses/{id}/modules/{id}/items |
| `get_pages(id)` | GET /courses/{id}/pages |
| `get_page(course_id, page_url)` | GET /courses/{id}/pages/{url} |
| `get_quizzes(id)` | GET /courses/{id}/quizzes |
| `get_files(id)` | GET /courses/{id}/files |
| `get_folders(id)` | GET /courses/{id}/folders |
| `get_media_objects(id)` | GET /courses/{id}/media_objects |

---

### studio_api.py
**Purpose:** Canvas Studio API client with OAuth2

**Key Functions:**
- `authorize()` - Initiate OAuth flow
- `refresh_token()` - Refresh expired access token
- `get_collection(collection_id)` - Get Studio collection
- `get_media(media_id)` - Get media item details
- `get_captions(media_id)` - Get caption tracks
- `upload_captions(media_id, file_path)` - Upload caption file

---

### cred.py
**Purpose:** Credential management via Windows Credential Vault

**Key Functions:**
- `save_canvas_api_key(key)` - Store API token
- `get_canvas_api_key()` - Retrieve API token
- `get_canvas_studio_tokens()` - Get Studio OAuth tokens
- `save_canvas_studio_tokens(access, refresh)` - Store Studio tokens
- `set_canvas_api_key_to_environment_variable()` - Export to env var

**Storage Location:** Windows Credential Manager (via `keyring` library)

---

### set_config.py
**Purpose:** Application configuration storage

**Key Functions:**
- `save_config(config_dict)` - Save to config.json
- `load_config()` - Load from config.json
- `get_config_value(key)` - Get specific config value

**Config Location:** `%APPDATA%\canvas bot\config.json`

**Config Keys:**
- `CANVAS_COURSE_PAGE_ROOT` - Base URL for Canvas instance
- `API_PATH` - API endpoint path
- `CANVAS_STUDIO_TOKEN_URL` - Studio OAuth token endpoint
- `CANVAS_STUDIO_AUTHENTICATION_URL` - Studio OAuth auth endpoint

---

## Resource Nodes Module (resource_nodes/)

### base_node.py
**Purpose:** Abstract base class for organizational nodes

**Key Classes:**
- `BaseNode(ABC)` - Abstract base for Modules, Pages, Assignments, etc.

**Key Methods:**
- `add_data_api_link_to_children()` - Fetch additional data via API
- `add_content_nodes_to_children(html)` - Parse HTML and create content nodes

---

### base_content_node.py
**Purpose:** Abstract base class for content items

**Key Classes:**
- `BaseContentNode(ABC)` - Abstract base for Document, VideoFile, etc.

**Key Attributes:**
- `url` - Content URL
- `title` - Display title
- `file_name` - Derived filename
- `download_url` - Direct download URL
- `captioned` - Caption status (for media)
- `item_id` - Unique identifier

---

### modules.py
**Purpose:** Canvas course modules handler

**Key Classes:**
- `Modules` - Container for all course modules
- `ModuleItem` - Individual module item

---

### pages.py
**Purpose:** Canvas pages handler

**Key Classes:**
- `Page(BaseNode)` - Single Canvas page

**Content Extraction:** Parses `body` HTML field for embedded links

---

### assignments.py
**Purpose:** Canvas assignments handler

**Key Classes:**
- `Assignment(BaseNode)` - Single assignment

**Content Extraction:** Parses `description` HTML field

---

### quizzes.py
**Purpose:** Canvas quizzes handler

**Key Classes:**
- `Quiz(BaseNode)` - Single quiz

**Content Extraction:** Parses `description` HTML field

---

### discussions.py
**Purpose:** Canvas discussion topics handler

**Key Classes:**
- `Discussion(BaseNode)` - Single discussion topic

**Content Extraction:** Parses `message` HTML field

---

### announcements.py
**Purpose:** Canvas announcements handler

**Key Classes:**
- `Announcement(BaseNode)` - Single announcement

---

### canvasfiles.py
**Purpose:** Canvas Files and Folders handler

**Key Classes:**
- `CanvasFile(BaseContentNode)` - File uploaded to Canvas
- `CanvasFolder` - Folder in Canvas Files

---

### canvas_studio.py
**Purpose:** Canvas Studio media library integration

**Key Classes:**
- `CanvasStudio` - Container for Studio media
- `CanvasStudioMedia` - Individual Studio media item

---

### media_objects.py
**Purpose:** Canvas native media objects

**Key Classes:**
- `CanvasMediaObjects` - Container for media objects

---

### content_nodes.py
**Purpose:** Concrete content node implementations

**Key Classes:**
| Class | Description | Example URLs |
|-------|-------------|--------------|
| `Document` | Downloadable document files | .pdf, .docx, .pptx |
| `VideoFile` | Downloadable video files | .mp4, .mov, .mkv |
| `VideoSite` | Video hosting sites | youtube.com, vimeo.com |
| `AudioFile` | Downloadable audio files | .mp3, .m4a, .wav |
| `AudioSite` | Audio hosting/podcasts | podcast links |
| `ImageFile` | Image files | .jpg, .png, .gif |
| `DocumentSite` | Document hosting | docs.google.com |
| `FileStorageSite` | Cloud storage | box.com, drive.google.com |
| `DigitalTextbook` | eBook platforms | cengage.com |
| `CanvasMediaEmbed` | Canvas-hosted media | /media_objects/ |
| `CanvasStudioEmbed` | Canvas Studio embeds | studio embeds |
| `Unsorted` | Unclassified links | anything else |

---

## External Content Nodes (external_content_nodes/)

### box.py
**Purpose:** Box.com shared folder parsing

**Key Classes:**
- `BoxPage` - Parses Box shared folder page

**Functionality:**
- Extracts JSON metadata from Box HTML
- Recursively creates content nodes for files in shared folders

---

## Tools Module (tools/)

### export_to_excel.py
**Purpose:** Excel workbook generation for accessibility audits

**Key Functions:**
- `create_workbook(content_extractor, path)` - Generate complete workbook
- `add_documents_sheet(wb, docs)` - Add documents sheet
- `add_videos_sheet(wb, videos)` - Add videos sheet
- `add_validation(ws)` - Add dropdown validation
- `add_conditional_formatting(ws)` - Add color coding

**Output:** Macro-enabled workbook (.xlsm) with multiple sheets

---

### logger.py
**Purpose:** Application logging configuration

**Configuration:**
- Rotating file handler
- Max size: 10 MB
- Backup count: 5
- Location: `%APPDATA%\canvas bot\canvas_bot.log`

---

### canvas_tree.py
**Purpose:** Course structure visualization

**Key Functions:**
- `build_tree(root)` - Build treelib tree from course
- `display_tree(tree)` - Print tree to console

---

### captioning_check.py
**Purpose:** YouTube caption status checking

**Key Functions:**
- `check_youtube_captions(url)` - Query YouTube API for caption availability

---

### animation.py
**Purpose:** CLI progress animations

---

### stats.py
**Purpose:** Statistics generation for processed content

---

## Configuration Module (config/)

### yaml_io.py
**Purpose:** YAML file read/write utilities

**Key Functions:**
- `load_yaml(path)` - Load YAML file
- `save_yaml(data, path)` - Save data to YAML

---

### config.yaml
**Purpose:** Main application configuration

**Contents:**
- Version number
- HTML filter selectors
- API field mappings
- MIME type definitions
- Default paths

---

### re.yaml
**Purpose:** Regex patterns for content classification

**Pattern Categories:**
- `document_file` - Document extensions
- `video_file` - Video extensions
- `audio_file` - Audio extensions
- `image_file` - Image extensions
- `web_video` - Video site URLs
- `web_audio` - Audio site URLs
- `document_app` - Document app URLs
- `file_storage` - Cloud storage URLs
- `canvas_studio` - Studio embed patterns
- `ignore` - URLs to skip
- `force_to_shortcut` - URLs that can't be downloaded

---

## Sorters Module (sorters/)

### sorters.py
**Purpose:** Content categorization helpers

**Key Functions:**
- `sort_by_type(nodes)` - Group nodes by content type
- `sort_by_module(nodes)` - Group nodes by source module

---

## Pipeline Testing Module (test/pipeline_testing/)

### cli.py
**Purpose:** Click CLI interface for pipeline testing commands

**Commands:**
| Command | Description |
|---------|-------------|
| `collect` | Collect raw API data from a single course |
| `batch-collect` | Efficiently collect from many courses (1 API call per course) |
| `batch-test` | Test pipeline offline against collected corpus |
| `test` | Direct pipeline test against single raw data file |
| `test-all` | Test all raw data files in a directory |
| `compare` | Compare raw API data vs processed output |
| `compare-all` | Compare all raw/processed pairs in directory |
| `side-by-side` | Visual side-by-side comparison |
| `summary` | Show summary of collected test data |
| `samples` | Show sample entries from raw data |

**Usage:**
```bash
# Collect from course range
python -m test.pipeline_testing batch-collect --range 34000-35000 --output corpus.json

# Test offline
python -m test.pipeline_testing batch-test --corpus corpus.json
```

---

### batch_collector.py
**Purpose:** Efficient batch collection from many courses with minimal API usage

**Key Classes:**
- `BatchCollector` - Collects minimal data from courses

**Key Functions:**
- `extract_essential(raw)` - Extract only essential fields from API response
- `print_corpus_summary(corpus)` - Print collection statistics

**Essential Fields:**
Only these 4 fields are stored per file to minimize storage:
- `id` - File ID
- `display_name` - Human-readable filename
- `filename` - URL-encoded filename
- `mime_class` - File type classification

**Key Methods:**
- `collect_course(course_id)` - Collect from single course (1 API call)
- `collect_batch(course_ids, output_file)` - Collect from multiple courses
- `collect_from_range(start, end, output_file)` - Collect from ID range
- `collect_from_file(course_list_file, output_file)` - Collect from file of IDs

---

### batch_tester.py
**Purpose:** Offline batch testing against collected corpus

**Key Classes:**
- `FileTestResult` - Result of testing one file entry
- `MockNode` - Mock content node matching fixed pipeline logic
- `BatchTester` - Tests pipeline against batch-collected corpus

**Key Functions:**
- `derive_file_name_test(node)` - Test version of derive_file_name logic

**Key Methods:**
- `test_file(raw)` - Test single file entry
- `test_corpus(corpus_file)` - Test all files in corpus
- `get_summary()` - Get test summary statistics
- `print_report()` - Print formatted test report
- `save_report(output_file)` - Save detailed report to JSON

**Validation Rules:**
- Title should match display_name
- Derived filename should match display_name
- No unresolved URL encoding (+ signs from encoding)
- No empty filenames

---

### direct_tester.py
**Purpose:** Direct pipeline function testing against raw API data

**Key Classes:**
- `TestResult` - Result of testing one raw API item
- `MockNode` - Mock content node for testing derive_file_name
- `DirectPipelineTester` - Tests pipeline functions directly

**Key Methods:**
- `load_raw_data(raw_file)` - Load raw API data file
- `extract_files(data)` - Extract file entries from raw data
- `test_derive_file_name(raw_api)` - Test derive_file_name() directly
- `test_file(raw_api)` - Test single file through pipeline
- `test_raw_file(raw_file)` - Test all entries in raw file

**Imports actual pipeline code:**
```python
from core.downloader import derive_file_name
```

---

### collector.py
**Purpose:** Single-course raw data collector

**Key Classes:**
- `PipelineTestCollector` - Collects comprehensive raw data

**Key Methods:**
- `collect_from_course(course_id)` - Collect all data from one course
- `collect_from_range(start_id, end_id, output_dir)` - Collect from ID range
- `collect_from_file(course_file, output_dir)` - Collect from file of IDs

**Data Collected:**
- Files API response
- Media objects API response
- Summary statistics

---

### comparator.py
**Purpose:** Compare raw API data with pipeline output

**Key Classes:**
- `ComparisonResult` - Result of comparing one item
- `PipelineComparator` - Compares raw vs processed data

**Key Methods:**
- `compare(raw_file, processed_file)` - Compare two files
- `print_report()` - Print comparison report
- `save_report(output_file)` - Save comparison to JSON

---

### side_by_side.py
**Purpose:** Visual side-by-side comparison output

**Key Functions:**
- `print_comparison_table(raw_file, processed_file)` - Print comparison table
- `print_detailed_comparison(raw_file, processed_file, limit)` - Print detailed examples

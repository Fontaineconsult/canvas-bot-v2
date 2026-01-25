# CLAUDE.md - Canvas Bot v2 Project Guide

## Quick Reference

**Project:** Canvas Bot v2
**Version:** 0.1.6-alpha
**Language:** Python 3
**Platform:** Windows only
**Purpose:** CLI tool for downloading and auditing Canvas LMS course content with accessibility workflow support

## What This Project Does

Canvas Bot is a command-line tool that:
1. Connects to Canvas LMS via REST API
2. Discovers all content in a course (modules, pages, assignments, quizzes, files, media)
3. Extracts and categorizes embedded links (documents, videos, audio, images)
4. Downloads files to organized folder structures
5. Exports content inventories to Excel/JSON for accessibility auditing

## Project Structure Overview

```
canvas-bot-v2/
├── canvas_bot.py           # Main entry point (CLI)
├── config/                 # YAML configs and regex patterns
├── core/                   # Core business logic
├── resource_nodes/         # Canvas resource type handlers
├── external_content_nodes/ # External service handlers (Box)
├── network/                # API clients and credentials
├── sorters/                # Content categorization
├── tools/                  # Utilities (Excel export, logging, etc.)
└── claude/                 # Project documentation
```

## Key Entry Points

| File | Purpose |
|------|---------|
| `canvas_bot.py` | Main CLI entry point - start here |
| `core/course_root.py` | Course initialization and content tree building |
| `core/content_extractor.py` | Content categorization and export logic |
| `network/api.py` | Canvas LMS API wrapper |

## Running the Application

```bash
# Basic usage - download documents from a course
python canvas_bot.py --course_id 12345 --download_folder ./downloads

# Export to Excel for accessibility audit
python canvas_bot.py --course_id 12345 --output_as_excel ./reports

# Include all media types
python canvas_bot.py --course_id 12345 --download_folder ./downloads \
    --include_video_files --include_audio_files --include_image_files
```

## Architecture Summary

```
CLI (click) → CanvasBot → CanvasCourseRoot → Resource Nodes → Content Nodes
                              ↓
                    ContentExtractor → Downloader / Excel Export
```

**Design Patterns:**
- Factory Pattern: `node_factory.py` creates appropriate node types
- Mixin Pattern: `DownloaderMixin` adds download capability
- Tree Pattern: Hierarchical course content organization

## Credentials

Stored in Windows Credential Vault via `keyring`:
- Canvas API access token
- Canvas Studio OAuth credentials (client ID, secret, tokens)

Configuration stored in: `%APPDATA%\canvas bot\config.json`

## Content Classification

Content is classified via regex patterns in `config/re.yaml`:
- **Documents:** PDF, DOCX, PPTX, XLSX, etc.
- **Videos:** MP4, YouTube, Vimeo, Zoom recordings, etc.
- **Audio:** MP3, podcasts, etc.
- **Images:** JPG, PNG, GIF, etc.
- **External Services:** Box, Google Drive, Canvas Studio

## Key Dependencies

- `requests` - HTTP client
- `beautifulsoup4` - HTML parsing
- `click` - CLI framework
- `openpyxl` - Excel generation
- `keyring` - Windows credential storage
- `pywin32` - Windows shortcuts

## Development Notes

- Windows-only due to credential storage and shortcut creation
- All API calls go through `network/api.py` with error handling
- Regex patterns for content classification in `config/re.yaml`
- Logging to `%APPDATA%\canvas bot\canvas_bot.log`

## Common Tasks

**Add new content type:**
1. Add regex pattern to `config/re.yaml`
2. Create node class in `resource_nodes/content_nodes.py`
3. Update `node_factory.py` to recognize new type

**Add new Canvas resource:**
1. Create handler in `resource_nodes/`
2. Initialize in `core/course_root.py`
3. Add getter in `core/content_extractor.py`

**Modify Excel export:**
- Edit `tools/export_to_excel.py`

## See Also

- `claude/ARCHITECTURE.md` - Detailed architecture documentation
- `claude/MODULES.md` - Module-by-module reference
- `claude/CONFIG.md` - Configuration and setup guide
- `readme.md` - User documentation

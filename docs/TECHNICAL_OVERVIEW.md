# CanvasBot Technical Overview

*For award submission context - explains the technical implementation and unique value proposition*

---

## Executive Summary

CanvasBot is a Windows desktop application that automates the discovery, categorization, and download of educational content from Canvas LMS courses. It was built to solve a critical workflow problem in university accessibility operations: efficiently identifying and processing course materials that require format conversion (e.g., PDF remediation, video captioning).

**Key Innovation:** Unlike browser-based tools or manual processes, CanvasBot maintains persistent download state across sessions, enabling daily incremental scans that surface only new content requiring attention.

---

## The Problem It Solves

### The Accessibility Workflow Challenge

Universities are legally required to ensure course materials are accessible to students with disabilities. This typically requires:

1. **Document remediation** - Converting PDFs to accessible formats, adding alt text to images
2. **Video captioning** - Adding captions to lecture videos, YouTube embeds, Canvas Studio content
3. **Content auditing** - Tracking which materials have been reviewed and processed

### Why Existing Tools Fall Short

| Approach | Limitation |
|----------|------------|
| **Manual Canvas browsing** | Time-consuming; easy to miss embedded content; no state tracking |
| **Browser extensions** | Limited to current page; no batch processing; no persistent state |
| **Canvas Data exports** | Database-level access required; doesn't capture embedded links |
| **LTI integrations** | Require institutional deployment; limited customization |

**The gap:** No tool existed that could:
- Run on a desktop (no browser dependency)
- Scan entire courses programmatically
- Extract embedded content from HTML (not just file attachments)
- Track what has already been downloaded across sessions
- Organize output for efficient worker processing

---

## Technical Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CanvasBot Pipeline                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Canvas LMS API ──► Course Tree Builder ──► Content Extractor  │
│         │                    │                      │           │
│         ▼                    ▼                      ▼           │
│   [REST API calls]    [Hierarchical nodes]   [Categorized       │
│   - /courses          - Modules               content]          │
│   - /modules          - Pages                 - Documents       │
│   - /pages            - Assignments           - Videos          │
│   - /assignments      - Quizzes               - Audio           │
│   - /files            - Discussions           - Images          │
│                       - Announcements         - External links  │
│                                                                  │
│                              │                                   │
│                              ▼                                   │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │                    Output Options                         │  │
│   ├──────────────────────────────────────────────────────────┤  │
│   │  • Structured file downloads (mirroring course hierarchy) │  │
│   │  • Excel workbooks (for tracking/audit workflows)         │  │
│   │  • JSON export (for integration with other systems)       │  │
│   │  • Visual content tree (for inspection)                   │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Canvas API Integration (`network/api.py`)

- Authenticates via Canvas REST API using personal access tokens
- Handles pagination for courses with large amounts of content
- Respects rate limits to avoid API throttling
- Supports Canvas Studio OAuth for institutional video platforms

#### 2. Course Tree Builder (`core/course_root.py`)

Constructs a hierarchical representation of course content:

```
CanvasCourseRoot
├── Modules
│   └── Module
│       ├── Page
│       ├── Assignment
│       └── Quiz
├── Pages
├── Assignments
├── Quizzes
├── Discussions
├── Announcements
└── CanvasFiles
```

Each node type is a Python class that:
- Fetches its own data from the API
- Parses HTML content to extract embedded links
- Spawns child nodes recursively

#### 3. HTML Content Parser

**This is where significant value is created.** Canvas stores rich text content as HTML. A page might contain:

```html
<p>Please review the <a href="/courses/123/files/456/download">syllabus</a>
and watch this <iframe src="https://youtube.com/embed/abc123"></iframe></p>
```

CanvasBot parses this HTML using BeautifulSoup to extract:
- `<a href>` links to documents, files, external resources
- `<iframe>` embeds for YouTube, Vimeo, Canvas Studio
- `<img>` tags for images
- `<audio>` and `<video>` tags

#### 4. Content Classification Engine (`core/node_factory.py`, `sorters/sorters.py`)

Extracted URLs are classified into content types using configurable regex patterns:

| Category | Example Patterns |
|----------|------------------|
| Documents | `.*\.pdf`, `.*\.docx`, `.*\.pptx` |
| Video Sites | `.*youtube\.com.*`, `.*vimeo\.com.*`, `.*zoom\.us.*` |
| Video Files | `.*\.mp4`, `.*\.mov`, `.*\.mkv` |
| Audio Files | `.*\.mp3`, `.*\.m4a`, `.*\.wav` |
| Canvas Studio | `.*instructuremedia\.com.*` |
| Cloud Storage | `.*box\.com.*`, `.*drive\.google\.com.*` |

This classification determines:
- Which folder the file is downloaded to
- Which Excel sheet it appears on
- How it's displayed in the content tree

#### 5. Download State Management (`config/yaml_io.py`)

**Critical for daily workflow operations.**

Each course maintains a `download_manifest.yaml` file:

```yaml
downloaded_files:
  - https://canvas.edu/files/123/download
  - https://canvas.edu/files/456/download
  - https://youtube.com/watch?v=abc123
last_scan: 2026-01-28T14:30:00
```

On subsequent runs:
- URLs in the manifest are skipped
- Only new content is downloaded
- Workers see only what needs attention

#### 6. Output Generators

**File Downloader (`core/downloader.py`):**
- Downloads files to structured folder hierarchy
- Creates Windows shortcuts (.lnk) for content that can't be directly downloaded (authenticated URLs, streaming video)
- Handles Windows path length limitations (260 char limit)

**Excel Exporter (`tools/export_to_excel.py`):**
- Generates .xlsm workbooks with multiple sheets by content type
- Includes dropdown validation for status tracking
- Hyperlinks to source pages and download locations
- Conditional formatting for hidden/unpublished content

**JSON Exporter:**
- Full content metadata in machine-readable format
- Enables integration with other accessibility tools
- Archives course state at point in time

---

## Unique Technical Achievements

### 1. Deep Content Extraction

Most tools only see files attached at the course level. CanvasBot traverses:
- Module items → Page content → Embedded links
- Assignment descriptions → Embedded media
- Quiz questions → Inline images and links
- Discussion posts → Attached files

This captures content that would otherwise be missed by simpler scanning approaches.

### 2. Stateful Incremental Processing

The manifest system transforms the workflow from:
- ❌ "Scan everything, figure out what's new" (manual)
- ✅ "Show me only new content since last scan" (automated)

This is essential for daily operations where a student worker needs to process 10-20 new files, not re-review 500 existing ones.

### 3. Hierarchical Organization

Downloaded files preserve course structure:

```
Course Name - 12345/
├── 28-01-2026/                          ← Date of download
│   ├── Module 1 - Introduction/
│   │   ├── Week 1 Overview/
│   │   │   └── Documents/
│   │   │       └── syllabus.pdf
│   │   └── Lecture 1/
│   │       └── VideoFiles/
│   │           └── intro_lecture.mp4
│   └── Module 2 - Fundamentals/
│       └── Reading Assignment/
│           └── Documents/
│               └── chapter1.pdf
```

Workers can navigate to specific modules without searching through flat file lists.

### 4. Desktop-Native Operation

Running as a Windows executable provides:
- No browser required (works in background)
- Secure credential storage (Windows Credential Vault)
- Local file system access for organization
- Schedulable via Task Scheduler for automated daily runs

---

## Workflow Integration

### Daily Operation Cycle

```
┌─────────────────────────────────────────────────────────────────┐
│                    Daily Accessibility Workflow                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   6:00 AM   Task Scheduler runs CanvasBot                       │
│             → Scans configured courses                          │
│             → Downloads new content to dated folders            │
│             → Updates Excel tracking workbook                   │
│                                                                  │
│   9:00 AM   Student worker arrives                              │
│             → Opens today's download folder                     │
│             → Sees only files added since yesterday             │
│             → Processes documents (PDF remediation)             │
│             → Flags videos needing captions                     │
│                                                                  │
│   5:00 PM   Supervisor reviews                                  │
│             → Excel workbook shows completion status            │
│             → JSON export feeds reporting dashboard             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Scale of Operation

At San Francisco State University:
- Validated against **27,000+ files** across **499 courses**
- 99.7% accuracy on filename derivation
- Processes a typical course (200-500 content items) in under 60 seconds

---

## Technical Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12 |
| HTTP Client | `requests` |
| HTML Parsing | `BeautifulSoup4` |
| Excel Generation | `openpyxl` |
| CLI Framework | `click` |
| Credential Storage | `keyring` (Windows Credential Vault) |
| Shortcut Creation | `pywin32` |
| Distribution | PyInstaller (single-file .exe) |

---

## Why This Matters

### Before CanvasBot

1. Coordinator manually browses Canvas course
2. Downloads files one-by-one
3. Tracks progress in separate spreadsheet
4. Repeats daily, often missing new content
5. Student workers unsure what needs attention

### After CanvasBot

1. Automated daily scan captures all content
2. Incremental downloads show only new files
3. Organized folders match course structure
4. Excel workbook integrates tracking
5. Workers process exactly what's new

**Time savings:** What took 2-3 hours of manual work per course now takes minutes of automated processing.

**Accuracy improvement:** Embedded content that was frequently missed is now systematically captured.

**Worker efficiency:** Clear daily task list instead of "figure out what changed."

---

## Conclusion

CanvasBot represents a purpose-built solution to a workflow problem that existing tools don't address. By combining deep content extraction, stateful tracking, and structured output, it transforms accessibility remediation from a manual, error-prone process into an efficient, automated workflow.

The tool has been deployed in production at San Francisco State University, processing thousands of files across hundreds of courses with high reliability.

---

*Document prepared for award submission - January 2026*
*Contact: fontaine@sfsu.edu*

# Configuration Guide

## Overview

Canvas Bot uses a multi-layered configuration system:
1. **Windows Credential Vault** - Sensitive credentials (API tokens)
2. **AppData config.json** - Instance-specific settings (URLs)
3. **Project YAML files** - Application settings and patterns

---

## Credentials Setup

### Canvas API Token

**Storage:** Windows Credential Vault via `keyring`
**Key:** `canvas_api_key`

**First-time Setup:**
```bash
python canvas_bot.py --reset_canvas_params
```

You will be prompted for:
1. Canvas base URL (e.g., `https://yourschool.instructure.com`)
2. Canvas API path (e.g., `https://yourschool.instructure.com/api/v1`)
3. Canvas subdomain (e.g., `yourschool` for yourschool.instructure.com)
4. Canvas Studio domain (e.g., `yourschool.instructuremedia.com`)
5. Canvas API access token

**Getting an API Token:**
1. Log into Canvas
2. Go to Account > Settings
3. Scroll to "Approved Integrations"
4. Click "+ New Access Token"
5. Copy the generated token

**Programmatic Access:**
```python
from network.cred import get_canvas_api_key, save_canvas_api_key

# Save
save_canvas_api_key("your_token_here")

# Retrieve
token = get_canvas_api_key()
```

---

### Canvas Studio OAuth (Optional)

**Storage:** Windows Credential Vault
**Keys:** `canvas_studio_client_id`, `canvas_studio_client_secret`, `canvas_studio_access_token`, `canvas_studio_refresh_token`

**Setup:**
```bash
python canvas_bot.py --reset_canvas_studio_params
```

You will be prompted for:
1. Canvas Studio token URL
2. Canvas Studio authentication URL
3. Client ID
4. Client secret

**OAuth Flow:**
1. First run opens browser for authorization
2. User authorizes application
3. Tokens are stored in credential vault
4. Tokens auto-refresh on subsequent runs

---

## Application Configuration

### config.json

**Location:** `%APPDATA%\canvas bot\config.json`

**Structure:**
```json
{
  "CANVAS_COURSE_PAGE_ROOT": "https://yourschool.instructure.com",
  "API_PATH": "https://yourschool.instructure.com/api/v1",
  "CANVAS_DOMAIN": "yourschool",
  "CANVAS_STUDIO_DOMAIN": "yourschool.instructuremedia.com",
  "BOX_DOMAIN": "yourschool.app.box.com",
  "LIBRARY_PROXY_DOMAIN": "",
  "CANVAS_STUDIO_TOKEN_URL": "https://yourschool.instructuremedia.com/api/public/oauth/token",
  "CANVAS_STUDIO_AUTHENTICATION_URL": "https://yourschool.instructuremedia.com/api/public/oauth/authorize",
  "CANVAS_STUDIO_CALLBACK_URL": "urn:ietf:wg:oauth:2.0:oob"
}
```

**Key Settings:**

| Key | Description | Example |
|-----|-------------|---------|
| `CANVAS_COURSE_PAGE_ROOT` | Base Canvas URL | `https://yourschool.instructure.com` |
| `API_PATH` | Full API endpoint URL | `https://yourschool.instructure.com/api/v1` |
| `CANVAS_DOMAIN` | Institution subdomain | `yourschool` (from yourschool.instructure.com) |
| `CANVAS_STUDIO_DOMAIN` | Canvas Studio domain | `yourschool.instructuremedia.com` |
| `BOX_DOMAIN` | Box.com subdomain (optional) | `yourschool.app.box.com` |
| `LIBRARY_PROXY_DOMAIN` | Library proxy domain (optional) | Leave blank if not used |
| `CANVAS_STUDIO_TOKEN_URL` | Studio OAuth token endpoint | Full URL |
| `CANVAS_STUDIO_AUTHENTICATION_URL` | Studio OAuth auth endpoint | Full URL |
| `CANVAS_STUDIO_CALLBACK_URL` | OAuth callback | Usually `urn:ietf:wg:oauth:2.0:oob` |

---

## Project Configuration Files

### config/config.yaml

**Purpose:** Application-wide settings and mappings

**Key Sections:**

```yaml
# Application version
version: "0.1.6-alpha"

# HTML parsing selectors
html_filters:
  link_selector: "a[href]"
  iframe_selector: "iframe[src]"

# API response field mappings
api_fields:
  page_body: "body"
  assignment_description: "description"
  quiz_description: "description"
  discussion_message: "message"

# MIME type definitions
mime_types:
  pdf: "application/pdf"
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  # ... more types

# Default download path
default_download_path: "./downloads"
```

---

### config/re.yaml

**Purpose:** Regex patterns for content type classification

**Pattern Categories:**

#### Document Files
```yaml
document_file:
  - '\\.pdf$'
  - '\\.docx?$'
  - '\\.pptx?$'
  - '\\.xlsx?$'
  - '\\.txt$'
  - '\\.rtf$'
```

#### Video Files
```yaml
video_file:
  - '\\.mp4$'
  - '\\.mov$'
  - '\\.mkv$'
  - '\\.avi$'
  - '\\.webm$'
```

#### Video Sites
```yaml
web_video:
  - 'youtube\\.com/watch'
  - 'youtu\\.be/'
  - 'vimeo\\.com/'
  - 'zoom\\.us/rec/'
  - 'mediasite\\.'
  - 'tiktok\\.com/'
```

#### Audio Files
```yaml
audio_file:
  - '\\.mp3$'
  - '\\.m4a$'
  - '\\.wav$'
  - '\\.ogg$'
```

#### Image Files
```yaml
image_file:
  - '\\.jpe?g$'
  - '\\.png$'
  - '\\.gif$'
  - '\\.svg$'
  - '\\.webp$'
```

#### Canvas Studio Embeds
```yaml
canvas_studio:
  - 'instructuremedia\\.com/embed/'
  - 'studio\\.instructure\\.com/embed/'
```

#### Ignore Patterns
```yaml
ignore:
  - '#$'                    # Anchor-only links
  - 'javascript:'           # JavaScript links
  - 'mailto:'               # Email links
  - '/courses/\\d+$'        # Course home links
  - '/modules$'             # Module index
```

#### Force to Shortcut
```yaml
force_to_shortcut:
  - 'docusign\\.com'        # Cannot download
  - 'box\\.com/s/'          # Shared folders
```

**Adding New Patterns:**

To add a new content type:

1. Add pattern to appropriate section in `re.yaml`:
```yaml
web_video:
  # existing patterns...
  - 'newvideosite\\.com/'   # Add new pattern
```

2. Update `node_factory.py` if new content class needed:
```python
def identify_content_url(url):
    # Add handling for new pattern
    if re.search(patterns['new_type'], url):
        return 'NewType'
```

---

### config/download_manifest.yaml

**Purpose:** Tracks downloaded files to prevent re-downloads

**Structure:**
```yaml
downloads:
  - item_id: "abc123"
    url: "https://example.com/file.pdf"
    path: "C:/downloads/file.pdf"
    timestamp: "2024-01-15T10:30:00"
  - item_id: "def456"
    # ... more entries
```

**Behavior:**
- Checked before each download
- File skipped if item_id exists in manifest
- Updated after successful download

---

## Environment Variables

The application sets these environment variables at runtime:

| Variable | Source | Purpose |
|----------|--------|---------|
| `ACCESS_TOKEN` | Credential Vault | Canvas API authentication |
| `CANVAS_COURSE_PAGE_ROOT` | config.json | Base Canvas URL |
| `API_PATH` | config.json | API endpoint path |
| `CANVAS_DOMAIN` | config.json | Institution subdomain for regex matching |
| `CANVAS_STUDIO_DOMAIN` | config.json | Canvas Studio domain for API calls |
| `BOX_DOMAIN` | config.json | Box.com subdomain (optional) |
| `LIBRARY_PROXY_DOMAIN` | config.json | Library proxy domain (optional) |
| `CANVAS_STUDIO_TOKEN` | Credential Vault | Studio API authentication |
| `CANVAS_STUDIO_RE_AUTH_TOKEN` | Credential Vault | Studio token refresh |

---

## Logging Configuration

**Log Location:** `%APPDATA%\canvas bot\canvas_bot.log`

**Settings (in tools/logger.py):**
```python
handler = RotatingFileHandler(
    log_path,
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5
)
```

**Log Levels:**
- `DEBUG` - Detailed API calls and parsing
- `INFO` - Normal operations
- `WARNING` - Skipped content, fallbacks
- `ERROR` - Failed operations

---

## Troubleshooting Configuration

### Reset All Credentials
```bash
python canvas_bot.py --reset_canvas_params --reset_canvas_studio_params
```

### Verify Credentials
```python
from network.cred import get_canvas_api_key
print(get_canvas_api_key())  # Should print token or None
```

### Check Config Location
```python
import os
config_dir = os.path.join(os.environ['APPDATA'], 'canvas bot')
print(config_dir)  # Shows config directory path
```

### View Download Manifest
```python
from config.yaml_io import load_yaml
manifest = load_yaml('config/download_manifest.yaml')
print(len(manifest.get('downloads', [])))  # Count of downloaded items
```

---

## Quick Reference

| What | Where |
|------|-------|
| Canvas API token | Windows Credential Manager |
| Canvas Studio tokens | Windows Credential Manager |
| Instance URL | `%APPDATA%\canvas bot\config.json` |
| Content patterns | `config/re.yaml` |
| App settings | `config/config.yaml` |
| Download history | `config/download_manifest.yaml` |
| Logs | `%APPDATA%\canvas bot\canvas_bot.log` |

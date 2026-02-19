# Future: LTI / SCORM / External Tool Detection

## Why This Matters

ADA Title II requires accessible digital content. Third-party content embedded via LTI tools or SCORM packages is a compliance blind spot because the institution doesn't control it. Alt media teams need to know this content exists so they can flag it for the vendor or find accessible alternatives. They can't remediate it themselves.

## Current State

### What Exists (Unused)

Two API functions in `network/api.py` (lines 240-250) are defined but **never called**:

```python
@response_decorator
def get_external_tools(course_id):
    # GET /api/v1/courses/{course_id}/external_tools
    ...

@response_decorator
def get_external_tool(course_id, id):
    # GET /api/v1/courses/{course_id}/external_tools/sessionless_launch?url={id}
    ...
```

### What Happens Today

LTI/SCORM content enters the system through two paths:

1. **Module items of type `"ExternalTool"`** — `modules.py` processes these but `get_node('ExternalTool')` returns `None`, so they fall through to the `external_url` handler and become **Unsorted** content nodes.

2. **LTI iframes in HTML** — The scraper (`core/scraper.py`) extracts `<iframe>` tags from page/assignment/quiz HTML. LTI iframes pass through but match no regex pattern, so they also become **Unsorted**.

No regex patterns exist in `config/re.yaml` for LTI or SCORM content.

## Canvas API Research

### External Tools Endpoint

`GET /api/v1/courses/:course_id/external_tools` returns all LTI tools configured for a course.

**Key fields per tool:**

| Field | Purpose |
|---|---|
| `id` | Tool ID — referenced by module items via `content_id` |
| `name` | Human-readable name (e.g., "McGraw-Hill Connect", "Turnitin") |
| `url` / `domain` | Launch URL or domain |
| `version` | `"1.1"` or `"1.3"` (LTI version) |
| `privacy_level` | Data sharing level (`anonymous`, `name_only`, `email_only`, `public`) |
| `description` | Tool description |
| `developer_key_id` | Only present for LTI 1.3 tools |
| `deployment_id` | Unique deployment identifier |
| Placements (40+) | Where tool appears (`course_navigation`, `editor_button`, `assignment_menu`, etc.) |

**Query parameters:** `search_term`, `selectable`, `include_parents`, `placement`. Supports pagination.

### Module Item Cross-Reference

Module items of type `"ExternalTool"` have:
- `content_id` → maps to the tool `id` from `get_external_tools()`
- `external_url` → the launch URL
- `title` → module item title
- `html_url` → Canvas page URL

This means you can join module items to external tools metadata to get the tool name and provider for each usage.

### Important Limitation

**SCORM packages are indistinguishable from LTI tools in the API.** Canvas wraps SCORM in an LTI layer, so both return `type: "ExternalTool"`. The only way to identify SCORM specifically is by URL/domain (e.g., SCORM Cloud domains) or tool name.

`"ExternalUrl"` module items are plain links to external websites — not LTI tools.

## Implementation Approaches

### Approach A: API Inventory Only

Wire up `get_external_tools()` to get the full list of LTI tools configured for the course. Cross-reference with module items via `content_id` to show where each tool is used.

- **Pros:** Clean, reliable data. No regex maintenance. Gets tool names and metadata.
- **Cons:** Doesn't catch LTI iframes embedded directly in page/assignment HTML.

### Approach B: API + Iframe Detection

Approach A plus regex patterns for `/external_tools/` URLs and common LTI provider domains in `re.yaml`.

- **Pros:** Comprehensive — catches inline embeds too.
- **Cons:** Requires maintaining a list of LTI provider domain patterns.

### Approach C: Research First

Run `get_external_tools()` against a real course to see actual JSON responses before designing. This would validate our understanding of the data shape and inform the implementation.

## Architecture Notes

If implemented, the natural integration points are:

1. **New content node class** — `ExternalTool` in `resource_nodes/content_nodes.py` (extends `BaseContentNode`)
2. **Node factory update** — `core/node_factory.py` to recognize LTI patterns
3. **Module item handling** — `resource_nodes/modules.py` to check `item['type'] == 'ExternalTool'` explicitly
4. **Course root** — `core/course_root.py` to call `get_external_tools()` during initialization
5. **Excel export** — New "External Tools" sheet in `tools/export_to_excel.py`
6. **Content scaffolds** — New dict builder in `core/content_scaffolds.py` for export data

The existing tree, manifest, and download systems would handle the new node type automatically via inheritance.

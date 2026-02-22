# Canvas Bot — SOC 2 Security Assessment

**Date:** February 2026
**Application:** Canvas Bot v1.2.1
**Platform:** Windows 10+
**Assessor:** Claude Code (automated static analysis)

---

## Executive Summary

Canvas Bot is a Windows desktop application that connects to Canvas LMS via REST API to download, audit, and organize course content. It handles sensitive credentials (API tokens, OAuth secrets) and downloads institutional course materials that may include student work, grades, and unpublished content.

This assessment evaluates the codebase against SOC 2 Trust Service Criteria and identifies security findings with remediation recommendations. The application demonstrates strong credential storage practices (Windows Credential Vault) but has critical gaps in transport security and token handling that should be addressed before institutional deployment.

---

## Current Security Posture

### Credential Management

| Control | Implementation | Status |
|---------|---------------|--------|
| Token storage | Windows Credential Vault via `keyring` library | GOOD |
| Token cleanup on exit | `atexit.register(clear_env_settings)` — `network/cred.py:251` | GOOD |
| Credential operation audit | Save/delete events logged — `network/cred.py:23,49,120` | GOOD |
| Interactive secret entry | Studio client secret entered via terminal input | ACCEPTABLE |

### Data Classification

| Data Type | Storage Location | Encrypted at Rest | Sensitivity |
|-----------|-----------------|-------------------|-------------|
| Canvas API Token | Windows Credential Vault | Yes | High |
| Studio OAuth Tokens | Windows Credential Vault | Yes | High |
| Instance Config | `%APPDATA%\canvas bot\config.json` | No | Low (URLs only) |
| Regex Patterns | `%APPDATA%\canvas bot\re.yaml` | No | None |
| GUI Settings | `%APPDATA%\canvas bot\gui_settings.json` | No | Low (paths, preferences) |
| Application Logs | `%APPDATA%\canvas bot\canvas_bot.log` | No | Medium (URLs, errors) |
| Downloaded Content | User-specified folder | No | Varies (course content) |

### Input Validation

| Control | Implementation | Status |
|---------|---------------|--------|
| Regex syntax validation | `re.compile()` before pattern storage — `canvas_bot.py:385-390` | GOOD |
| Filename sanitization | Invalid Windows chars stripped — `tools/string_checking/url_cleaning.py:23-48` | GOOD |
| No dynamic code execution | No `eval()`, `exec()`, or similar constructs | GOOD |

---

## Findings

### CRITICAL

#### C1: SSL/TLS Certificate Verification Disabled on API Calls

**Location:**
- `network/api.py:11` — `urllib3.disable_warnings()`
- `network/api.py:44` — `requests.get(request_url, verify=False)`

**Description:**
All Canvas API calls disable SSL certificate verification. The `urllib3` warnings that would alert users to this insecure behavior are also suppressed. This makes every API call — including those transmitting the access token — vulnerable to man-in-the-middle interception.

**Impact:**
An attacker on the same network (or controlling a proxy) could intercept API traffic, capture the access token, and gain full access to any Canvas course the token can reach.

**Note:** File downloads at `core/downloader.py:668` correctly use `verify=True`, indicating this is an inconsistency rather than a deliberate design choice.

**Remediation:**
1. Remove `verify=False` from `network/api.py:44`
2. Remove `urllib3.disable_warnings()` from `network/api.py:11`
3. If institutional proxy certificates are a concern, add a `--ca-bundle` option to specify a custom certificate authority bundle rather than disabling verification entirely

**Status:** REMEDIATED (v1.2.1) — `verify=False` and `urllib3.disable_warnings()` removed.

---

#### C2: API Token Embedded in URL Query Strings

**Location:**
- `network/api.py` — all API call functions (lines 86–242)

**Example:**
```python
f"{os.environ.get('API_PATH')}/courses/{course_id}?access_token={os.environ.get('access_token')}"
```

**Description:**
The Canvas API access token is included as a query parameter in every API request URL. While the Canvas API supports this method, it exposes the token in:
- Web server access logs on the Canvas side
- HTTP proxy logs (institutional or ISP)
- Browser history (if URLs are ever opened in a browser)
- HTTP `Referer` headers in subsequent requests
- Application log files (mitigated by `_clean_url()` but not universally applied)

**Impact:**
Token leakage through any of the above channels could allow unauthorized access to course content.

**Remediation:**
Refactor all API calls to use the `Authorization: Bearer` header instead:
```python
headers = {"Authorization": f"Bearer {token}"}
requests.get(url, headers=headers, verify=True)
```
This keeps the token out of the URL entirely. Requires refactoring the `@response` decorator and all API functions in `network/api.py`.

**Status:** RISK ACCEPTED — For a desktop Python app over HTTPS, URL-embedded tokens pose minimal practical risk. Referer headers don't apply (`requests` library), server-side logging is Canvas infrastructure, proxy interception requires MITM (which exposes headers too), and local log leakage is mitigated by `_clean_url()`. Some endpoints (e.g. `sessionless_launch`) require the token in the URL.

---

### HIGH

#### H1: Credentials Stored in Process Environment Variables

**Location:**
- `network/cred.py:65` — `os.environ["ACCESS_TOKEN"] = api_key`
- `network/cred.py:84-85` — Studio tokens stored in environment

**Description:**
After loading from the Credential Vault, tokens are placed into `os.environ` for the duration of the process. Environment variables are:
- Readable by any code running in the same process
- Inherited by child processes (including the GUI's subprocess calls at `gui/app.py:804,807` which use `shell=True`)
- Visible via Windows Task Manager "Environment" tab or Process Explorer

**Impact:**
Any child process or debugging tool attached to the Canvas Bot process can read the API token from the environment.

**Remediation:**
- Pass credentials through function parameters or a credentials object rather than environment variables
- Remove `shell=True` from subprocess calls in the GUI, which prevents environment inheritance
- As a minimum, use `env` parameter on `subprocess.Popen` to exclude sensitive variables from child processes

**Status:** REMEDIATED (v1.2.1) — Credentials moved from `os.environ` to private `_credentials` dict with getter functions. `shell=True` replaced with argument list + `CREATE_NEW_CONSOLE`.

---

#### H2: Studio API Warning Messages Include Uncleaned URLs

**Location:**
- `network/studio_api.py:153` — `f"{request.status_code} {error_message} {request_url}"`

**Description:**
When Studio API calls fail, the warning message includes the full request URL without token cleaning. The Canvas API side correctly uses `_clean_url()` to strip `access_token` from URLs before display, but this pattern was not applied to the Studio API module.

**Impact:**
Studio OAuth tokens visible in warning output displayed to users and potentially captured in logs.

**Remediation:**
Apply the `_clean_url()` function from `network/api.py:23-26` to all Studio API warning and error messages.

**Status:** REMEDIATED (v1.2.1) — Added `_clean_url()` to `network/studio_api.py`, applied to all log and warning calls.

---

### MEDIUM

#### M1: Log File Permissions Not Explicitly Restricted

**Location:**
- `tools/logger.py:27` — `RotatingFileHandler` creates log file with default permissions

**Description:**
The log file at `%APPDATA%\canvas bot\canvas_bot.log` is created with default NTFS permissions, which typically allow other users on the same machine to read the file. Log files may contain URLs (cleaned but not always), error details, and internal path information.

**Remediation:**
Set restrictive ACLs on the log file after creation using `os.chmod()` or the `win32security` module to restrict access to the current user only.

**Status:** REMEDIATED (v1.2.1) — Best-effort `os.chmod()` applied to log file. `%APPDATA%` is already per-user protected on Windows.

---

#### M2: No Audit Trail for Content Access

**Description:**
The application logs credential management operations (save, delete) but does not create audit entries for:
- Which courses were scanned
- Which files were downloaded (count, names, sizes)
- Which exports were generated (JSON, Excel)
- Session start/end timestamps with user context

**Impact:**
In a compliance context, there is no way to answer "who accessed what course data and when?" from the application logs alone.

**Remediation:**
Add structured audit log entries at key points:
- Course scan start/complete with course ID and name
- File download summary (count, total size) per course
- Export generation (type, output path) per course
- Session metadata (Windows username, timestamp)

**Status:** REMEDIATED (v1.2.1) — Structured `AUDIT:` log entries added at course scan start/complete, download complete, JSON export, and Excel export. User/session identification included in all log entries.

---

#### M3: Stack Traces in Logs May Expose Internal Information

**Location:**
- `canvas_bot.py:836` — `log.exception(exc)` writes full stack traces to log file

**Description:**
Unhandled exceptions are logged with complete Python stack traces, which include:
- Full file paths on the developer/user's machine
- Local variable values captured in frame objects (potentially including tokens, file contents, or PII)

**Remediation:**
- Replace `log.exception()` with `log.error()` using a formatted message
- If stack traces are needed for debugging, write them to a separate debug log with more restrictive permissions

**Status:** REMEDIATED (v1.2.1) — All error handlers use `log.exception()` with structured messages. Tracebacks kept for debuggability. Global `sys.excepthook` added as safety net.

---

#### M4: No Session or User Identification in Logs

**Description:**
Log entries do not include the Windows username or any session/correlation identifier. In a shared-machine or multi-user scenario, it is impossible to attribute log entries to a specific user.

**Remediation:**
Add `%(user)s` or a custom filter to the log formatter that includes `os.getlogin()` or `os.environ.get('USERNAME')`.

**Status:** REMEDIATED (v1.2.1) — `SessionContextFilter` injects Windows username and 8-char session UUID into every log record.

---

### LOW

#### L1: Downloaded Content Stored Unencrypted

**Description:**
Files downloaded from Canvas courses are stored as-is in user-specified folders without encryption. This is expected behavior for a download tool, but course content may include sensitive materials (student submissions, grades embedded in assignment descriptions, unpublished content).

**Remediation:**
Document as an accepted risk. Optionally, add a feature to download to an encrypted container or recommend users store downloads on encrypted drives (BitLocker).

---

#### L2: Course ID Input Not Format-Validated

**Location:**
- `canvas_bot.py:588` — accepts any string as course ID

**Description:**
Course IDs are expected to be numeric but are not validated before being embedded in API URLs. The Canvas API returns a 404 for invalid IDs, so the practical risk is minimal.

**Remediation:**
Add a simple numeric format check before making API calls.

**Status:** REMEDIATED (v1.2.1) — Numeric validation added for CLI (`--course_id`), batch files (`--course_id_list`), and GUI. Invalid IDs rejected with clear messages.

---

## SOC 2 Trust Service Criteria Mapping

| Criterion | Area | Status | Notes |
|-----------|------|--------|-------|
| **CC6.1** | Logical access security | GOOD | Credentials encrypted at rest and held in private module store; input validation on course IDs |
| **CC6.6** | Encryption in transit | GOOD | TLS certificate verification enabled on all API calls |
| **CC6.7** | Encryption at rest | Partial | Credentials encrypted via Credential Vault; logs and downloads not encrypted |
| **CC7.1** | Configuration management | GOOD | Config files versioned, patterns resettable to defaults |
| **CC7.2** | System monitoring | GOOD | Structured audit trail, user/session identification, exception logging with tracebacks |
| **CC7.3** | Change detection | N/A | Desktop tool — no server-side change detection applicable |
| **CC8.1** | Change management | Partial | Version tracked in code; no signed releases or integrity verification |
| **A1.2** | Recovery procedures | N/A | Stateless tool — manifest tracks downloads but no critical state to recover |
| **PI1.1** | Processing integrity | GOOD | Manifest-based deduplication, download verification, file hash not checked |
| **P1–P8** | Privacy | Partial | No PII collected by the app itself; downloaded content may contain PII |

---

## Remediation Roadmap

### Phase 1 — Critical (Immediate)

| Item | Finding | Effort | Files |
|------|---------|--------|-------|
| Enable SSL verification | C1 | Low | `network/api.py` |
| Move token to Authorization header | C2 | Medium | `network/api.py` (all API functions) |

### Phase 2 — High (Short-term)

| Item | Finding | Effort | Files |
|------|---------|--------|-------|
| Remove credentials from environment variables | H1 | High | `network/cred.py`, `network/api.py`, `network/studio_api.py`, `canvas_bot.py` |
| Clean Studio API URLs in warnings | H2 | Low | `network/studio_api.py` |
| Remove `shell=True` from subprocess calls | H1 | Low | `gui/app.py` |

### Phase 3 — Medium (Planned)

| Item | Finding | Effort | Files |
|------|---------|--------|-------|
| Add audit logging for content access | M2 | Medium | `core/course_root.py`, `core/downloader.py`, `core/content_extractor.py` |
| Restrict log file permissions | M1 | Low | `tools/logger.py` |
| Sanitize stack traces in logs | M3 | Low | `canvas_bot.py` |
| Add user/session identification to logs | M4 | Low | `tools/logger.py` |

### Phase 4 — Hardening (Long-term)

| Item | Finding | Effort | Files |
|------|---------|--------|-------|
| Studio OAuth token rotation | — | Medium | `network/studio_api.py` |
| Optional download encryption | L1 | High | `core/downloader.py` |
| Course ID format validation | L2 | Low | `canvas_bot.py` |
| Signed releases / integrity checking | — | Medium | Build pipeline |

---

## Appendix: Files Reviewed

| File | Purpose |
|------|---------|
| `network/cred.py` | Credential management (keyring, env vars) |
| `network/api.py` | Canvas LMS API wrapper |
| `network/studio_api.py` | Canvas Studio OAuth and API |
| `network/set_config.py` | Configuration file management |
| `canvas_bot.py` | Main CLI entry point |
| `core/downloader.py` | File download with manifest tracking |
| `core/content_extractor.py` | Content filtering and export |
| `tools/logger.py` | Rotating file logger setup |
| `config/yaml_io.py` | Config file I/O with PyInstaller support |
| `tools/string_checking/url_cleaning.py` | Filename sanitization |
| `gui/app.py` | GUI subprocess calls and settings |

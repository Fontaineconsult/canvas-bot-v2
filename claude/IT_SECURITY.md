# Canvas Bot — IT Security Summary

**Product:** Canvas Bot v1.2.2
**Type:** Desktop application (Windows, standalone `.exe`)
**License:** MIT (open source)
**Contact:** Daniel Fontaine — fontaine@sfsu.edu
**Repository:** https://github.com/Fontaineconsult/canvas-bot-v2
**Date:** February 2026

---

## What It Does

Canvas Bot is a read-only content browser and downloader for Canvas LMS. It connects to Canvas via the REST API to discover course content (documents, videos, audio, images, links), download files to a local folder, and generate content inventories for accessibility auditing.

**Canvas Bot does not create, modify, or delete any content, grades, enrollments, or settings in Canvas.**

---

## What It Accesses

| Service | Access | Purpose |
|---------|--------|---------|
| Canvas REST API | Read-only | Courses, modules, pages, assignments, quizzes, discussions, files |
| Canvas Studio API | Read-only (optional) | Video metadata and download streams |

- No write operations are performed against Canvas
- No data is sent to third-party services
- No telemetry, analytics, or usage tracking

---

## Authentication

- Requires a **Canvas API access token** (user-generated or institutional service account)
- Token is stored in the **Windows Credential Vault** (DPAPI-encrypted, per-user)
- Token is **never** written to configuration files, log files, or environment variables
- Credentials are cleared from memory on application exit via `atexit` handler

---

## Network

- **HTTPS only** — all API calls use TLS with certificate verification enforced
- Connections are made to:
  - `*.instructure.com` (Canvas LMS)
  - Institution-specific Studio domain (optional, user-configured)
- **No outbound connections** to any other service
- No proxy auto-configuration — works with system proxy settings

---

## Data Storage

All application data is stored under `%APPDATA%\canvas bot\`, a per-user protected directory:

| Data | Location | Sensitivity |
|------|----------|-------------|
| API tokens | Windows Credential Vault | High (DPAPI-encrypted) |
| Instance config | `config.json` | Low (URLs only) |
| Application logs | `canvas_bot.log` | Medium (course IDs, errors — tokens stripped) |
| GUI settings | `gui_settings.json` | Low (folder paths, checkbox states) |
| User patterns | `re.yaml` | Low (regex patterns) |
| Downloaded content | User-specified folder | Varies (course documents, media) |

- **No data leaves the local machine** — all downloads stay in the user-specified output folder
- Logs contain course IDs, file counts, timestamps, and error messages. No file contents, student data, or credentials are recorded.

---

## Security Controls

Canvas Bot has undergone a SOC 2-aligned security assessment. All critical and high-severity findings have been remediated.

| Control | Implementation |
|---------|---------------|
| Credential storage | Windows Credential Vault (DPAPI encryption) |
| Transport security | TLS certificate verification on all API calls |
| Token handling | Never in config files, logs, or environment variables |
| Log sanitization | API tokens, emails, and sensitive query parameters stripped |
| Input validation | Course IDs validated as numeric; regex patterns validated with `re.compile()` |
| Filename sanitization | Invalid Windows characters removed; path length limits enforced |
| Process isolation | No `shell=True` in subprocess calls; no `eval()`/`exec()` |
| Audit trail | Structured logging with Windows username and session ID |
| Log permissions | Best-effort file permission restrictions on creation |

---

## Compliance Notes

- **FERPA** — Downloaded course content may include FERPA-protected information (student names in page titles, discussion references). Handle downloaded materials per your institution's data governance policy. Delete downloads when no longer needed.
- **Read-only access** — Canvas Bot cannot modify any Canvas data. Risk of unintended changes to the LMS is zero.
- **Open source** — Full source code is available for review at the GitHub repository.

---

## Deployment

- **Standalone** — single `.exe` file, no installation or admin rights required
- **Portable** — runs from any directory (USB drive, network share, local folder)
- **No registry modifications** — does not modify Windows registry
- **No system services** — runs only when launched by the user
- **Per-user data** — each Windows user has isolated config, credentials, and logs

### Institutional Deployment

- Add the executable to your endpoint management allow-list to suppress SmartScreen warnings
- For shared use, create a dedicated Canvas service account with read-only enrollment across target courses and distribute a single API token
- The application does not require Group Policy configuration or MSI packaging

### Uninstall

1. Delete the executable
2. Delete `%APPDATA%\canvas bot\` (config, logs, settings, patterns)
3. Remove stored credentials: Windows Credential Manager → search "canvas" entries → delete
4. Revoke the API token in Canvas (Account > Settings > Approved Integrations)
5. Delete downloaded course content from output folders

# v1.2.1 SOC 2 Remediation — Step-by-Step Plan

**Branch:** v1.2.1
**Scope:** All actionable findings from `claude/SOC2_ASSESSMENT.md`
**Approach:** One step at a time, test after each before moving on

---

## Step 1: Enable SSL Certificate Verification (C1)

**Finding:** All Canvas API calls disable SSL verification (`verify=False`), making every request vulnerable to man-in-the-middle interception.

**File:** `network/api.py`

**Changes:**
1. Remove `import urllib3` (line 10)
2. Remove `urllib3.disable_warnings()` (line 11)
3. Change `verify=False` to `verify=True` in `response_handler()` (line 44)

**Testing:**
- Run a course import against a live Canvas instance
- Verify all API calls succeed with SSL enabled
- If SSL errors occur, investigate certificate chain (institutional proxy)

**Status:** [x] Complete

---

## Step 2: Move API Token to Authorization Header (C2)

**Finding:** The Canvas API access token is embedded in every URL as a query parameter (`?access_token=...`), exposing it in server logs, proxy logs, and HTTP Referer headers.

**Status:** [x] Risk Accepted — Deferred

**Rationale:** For a desktop Python app using `requests` over HTTPS, this is unlikely to be an issue:
- Referer headers don't apply (`requests` library doesn't send them)
- Server-side logging is Canvas's infrastructure, not ours
- Proxy interception requires MITM SSL inspection, which exposes headers too
- Local log leakage is already mitigated by `_clean_url()` (Steps 1 & 5)
- The `get_url()` function requires the token in the URL for certain endpoints (e.g. `sessionless_launch`), which limits the effectiveness of a partial migration

---

## Step 3: Remove Credentials from Environment Variables (H1)

**Finding:** After loading from the Windows Credential Vault, tokens are placed in `os.environ` where they're visible to child processes, debugging tools, and any code in the process.

**File:** `network/cred.py`

**Changes:**
1. Add a module-level `_credentials = {}` dict (after line 9)
2. Add getter functions:
   - `get_access_token()` → returns `_credentials.get("ACCESS_TOKEN")`
   - `get_studio_token()` → returns `_credentials.get("CANVAS_STUDIO_TOKEN")`
   - `get_studio_refresh_token()` → returns `_credentials.get("CANVAS_STUDIO_RE_AUTH_TOKEN")`
3. `set_canvas_api_key_to_environment_variable()` (line 65): change `os.environ["ACCESS_TOKEN"] = api_key` → `_credentials["ACCESS_TOKEN"] = api_key`
4. `set_canvas_studio_api_key_to_environment_variable()` (lines 84-85): change `os.environ` → `_credentials` for both Studio tokens
5. `clear_env_settings()` (lines 216-222): change to `_credentials.clear()`
6. `load_config_data_from_appdata()` — NO CHANGE (API_PATH, CANVAS_DOMAIN, etc. are URLs, not secrets)

**File:** `network/api.py`
- Update `response_handler()` to import and use `get_access_token()` from `cred.py` instead of `os.environ.get('ACCESS_TOKEN')`

**File:** `network/studio_api.py`
- Replace `os.environ['CANVAS_STUDIO_TOKEN']` with `get_studio_token()` at lines 128, 164, 187

**Testing:**
- Run a course import — API calls should work using credential store instead of env vars
- After setup, verify `'ACCESS_TOKEN' not in os.environ` (can add a temporary print check)
- Test Studio integration if Studio credentials are configured
- Test GUI "View Config" and "Reset Config" buttons (subprocess calls)

**Status:** [x] Complete

---

## Step 4: Remove `shell=True` from GUI Subprocess Calls (H1)

**Finding:** GUI subprocess calls use `shell=True`, which enables shell injection and passes the full environment to child processes.

**File:** `gui/app.py`

**Changes:**
Replace the subprocess calls in `_launch_cli()` (lines 804, 807):

Before:
```python
subprocess.Popen(f'start cmd /k "{exe}" {flag}', shell=True)
```

After:
```python
subprocess.Popen(['cmd', '/k', exe, flag], creationflags=subprocess.CREATE_NEW_CONSOLE)
```

Apply to both the frozen (exe) and dev (python script) paths.

**Testing:**
- Click "View Config (Alt+V)" in GUI — should open a new console window with config status
- Click "Reset Config (Alt+C)" → Canvas API — should open a new console with reset prompts
- Click "Reset Config (Alt+C)" → Canvas Studio — should open a new console with Studio reset
- Verify the console window stays open after the command finishes (`cmd /k`)

**Status:** [x] Complete

---

## Step 5: Clean Studio API URLs in Warnings (H2)

**Finding:** Studio API error and warning messages include full request URLs without cleaning. While tokens are in headers (not URLs), email addresses from `search_user()` queries are exposed.

**File:** `network/studio_api.py`

**Changes:**
1. Add `_clean_url()` function after line 12 — strips sensitive query params (email, tokens)
2. Apply `_clean_url()` to all log and warning calls:
   - `response_handler()`: lines 135, 136, 139, 140, 143, 147, 151, 153
   - `post_handler()`: lines 169, 173, 177, 179

**Testing:**
- Trigger a Studio API error (e.g., invalid media ID) — warning should show cleaned URL
- Verify email addresses are masked in log output if `search_user()` fails

**Status:** [x] Complete

---

## Step 6: Add User/Session Identification to Logs (M4)

**Finding:** Log entries don't include the Windows username or session identifier. In shared-machine scenarios, log entries can't be attributed to a specific user.

**File:** `tools/logger.py`

**Changes:**
1. Add `import getpass, uuid` at top
2. Create `SessionContextFilter` class that injects `user` (from `getpass.getuser()`) and `session` (short UUID) into every log record
3. Update log format (line 14): `'%(asctime)s - %(user)s - %(session)s - %(name)s - %(levelname)s - %(message)s'`
4. Apply filter to all handlers after `dictConfig()` (after line 42)

**Testing:**
- Run any command and check `%APPDATA%\canvas bot\canvas_bot.log`
- Each line should now show username and an 8-char session ID
- Session ID should be the same across all entries in one run, different across runs

**Status:** [x] Complete

---

## Step 7: Restrict Log File Permissions (M1)

**Finding:** Log files are created with default NTFS permissions. Other users on the machine may be able to read them.

**File:** `tools/logger.py`

**Changes:**
1. After `dictConfig()` and filter setup, add `os.chmod()` on the log file path to restrict to owner-only
2. Note: `os.chmod` has limited effect on Windows (only toggles read-only). The `%APPDATA%` folder is already per-user, so this is largely mitigated by the storage location. Add as best-effort.

**Testing:**
- Verify the log file is still created and writable
- No errors from permission setting on startup

**Status:** [x] Complete

---

## Step 8: Add Audit Trail for Content Access (M2)

**Finding:** The application logs credential operations but has no audit trail for which courses were scanned, what was downloaded, or what exports were generated.

**File:** `core/course_root.py`
- Standardize course start log (line 56) with `AUDIT:` prefix
- Add course completion audit log after `_init_modules_root()` (after line 90) with item count from `len(self.manifest.content_list())`

**File:** `core/content_extractor.py`
- Add `log = logging.getLogger(__name__)` at module level (currently missing)
- Add audit log after JSON export write (after line 712): `AUDIT: JSON export | course_id=... | path=...`
- Add audit log after Excel export (after line 777): `AUDIT: Excel export | course_id=... | path=...`

**File:** `core/downloader.py`
- Add download completion audit log after manifest save (after line 601): `AUDIT: Download complete | downloaded=X | skipped=Y | shortcuts=Z | directory=...`

**Testing:**
- Run a course import with download + Excel export
- Check log file for `AUDIT:` entries covering: course start, course complete (with item count), download summary, Excel export path
- Run JSON export and verify JSON audit entry

**Status:** [x] Complete

---

## Step 9: Sanitize Stack Traces in Logs (M3)

**Finding:** `log.exception()` in the main error handler writes full Python stack traces to the log file, potentially exposing internal file paths and variable values.

**File:** `canvas_bot.py`

**Changes (revised):**
- All three error handlers (`canvas_bot.py` GUI entry, CLI entry, and `gui/app.py` worker thread) now use `log.exception(f"Unhandled error: {type(exc).__name__}: {exc}")`
- `log.exception()` logs the error message AND full traceback — kept for debuggability
- Added `sys.excepthook` in `tools/logger.py` as a global safety net for truly uncaught exceptions
- Added loggers to `gui/app.py` and `content_extractor.py` (both were missing)

**Deviation from original plan:** Tracebacks are kept in logs (via `log.exception`) rather than stripped (via `log.error`). This prioritizes debuggability over the original M3 recommendation.

**Status:** [x] Complete

---

## Step 10: Course ID Input Validation (L2)

**Finding:** Course IDs are expected to be numeric but are accepted as any string, embedding unvalidated input into API URLs.

**File:** `canvas_bot.py`

**Changes:**
1. Add `_validate_course_id(course_id)` function — checks `course_id.strip().isdigit()`, prints error and exits if not numeric
2. Apply before `run_bot()` call for single course ID
3. Apply inside batch loop for course ID lists

**Testing:**
- `python canvas_bot.py --course_id abc` → should print error and exit
- `python canvas_bot.py --course_id 12345` → should work normally
- Batch file with mix of valid/invalid IDs → invalid ones rejected with clear message

**Status:** [x] Complete

---

## Step 11: Version Bump + Changelog + Assessment Update

**File:** `canvas_bot.py`
- Change `__version__ = "1.2.0"` → `__version__ = "1.2.1"` (line 15)

**File:** `gui/app.py`
- Update version references in window title, title bar label, and about dialog

**File:** `CHANGELOG.md`
- Add v1.2.1 section documenting all SOC 2 remediations

**File:** `claude/SOC2_ASSESSMENT.md`
- Update status of remediated findings

**Testing:**
- `python canvas_bot.py --help` shows 1.2.1
- GUI title bar shows 1.2.1
- Full exe test harness passes

**Status:** [x] Complete

---

## Out of Scope (Deferred)

| Item | Reason |
|------|--------|
| L1: Download encryption | Accepted risk — document only |
| Studio OAuth token rotation | Future enhancement |
| Signed releases / integrity checking | Build pipeline change, not code |
| `--ca-bundle` CLI option | Add later if institutional proxy certs are an issue |

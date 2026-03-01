# Canvas Bot v1.3.3 — Trust & Distribution Plan

**Goal:** Make Canvas Bot feel safe, professional, and trustworthy for higher-ed IT staff, faculty, and accessibility coordinators.

---

## 1. Code Signing

**Status:** Guide written (`claude/CODE_SIGNING.md`), not yet purchased.

- [ ] Choose signing method (Microsoft Artifact Signing or traditional CA)
- [ ] Purchase certificate and complete identity validation
- [ ] Sign the built `.exe` before distribution
- [ ] Verify signature: `signtool verify /pa CanvasBot.exe`
- [ ] Update `RELEASE_CHECKLIST.md` with the actual signing command (replace the placeholder)

**Result:** "Unknown Publisher" replaced with verified name. SmartScreen reputation begins building.

---

## 2. First GitHub Release (with full trust artifacts)

**Status:** Release checklist exists but has never been executed.

- [ ] Build and sign the `.exe`
- [ ] Generate SHA-256 checksum (`certutil -hashfile CanvasBot.exe SHA256`)
- [ ] Upload to VirusTotal, save report URL
- [ ] Create GitHub Release:
  - Tag: `v1.3.3`
  - Body includes: changelog, SHA-256 checksum, VirusTotal link, link to IT_SECURITY.md
  - Attach: signed `CanvasBot.exe`
- [ ] Verify the download link works and the signature survives the download

---

## 3. Update Checker (in-app)

**Status:** Not started.

Notify users when a newer version is available, without forcing updates.

- [ ] On startup (or on-demand), query the GitHub Releases API:
  ```
  GET https://api.github.com/repos/Fontaineconsult/canvas-bot-v2/releases/latest
  ```
- [ ] Compare `tag_name` against current version in `config.yaml`
- [ ] If newer version exists, show a non-blocking banner or status bar message:
  `"Canvas Bot v1.4.0 is available — github.com/Fontaineconsult/canvas-bot-v2/releases"`
- [ ] Make the message clickable (opens releases page in browser)
- [ ] Fail silently — no error if offline or rate-limited
- [ ] Add a setting to disable update checks (`gui_settings.json`: `check_for_updates: true`)
- [ ] No auto-download, no auto-install — just a notification

**Scope note:** This touches `gui/controller.py` (startup hook) and possibly a small utility function. No `core/` changes.

---

## 4. Quick-Start Visuals (README screenshots)

**Status:** Not started.

Screenshots help first-time users know what to expect and signal that the software is polished.

- [ ] Capture screenshots of:
  - Main window (Run tab with options visible)
  - Content Viewer (populated with course data)
  - Pattern Manager (category list + pattern table)
  - First-run welcome dialog
- [ ] Add a "Screenshots" or "Quick Start" section to `readme.md` with inline images
- [ ] Host images in a `docs/images/` folder in the repo (or use GitHub-rendered relative paths)

---

## 5. Polished README Landing

**Status:** README is comprehensive but text-heavy.

- [ ] Add a one-line badge row at the top:
  - License badge (`MIT`)
  - Latest release badge (GitHub)
  - Platform badge (`Windows`)
- [ ] Add a brief "Why Canvas Bot?" blurb aimed at the higher-ed audience (2-3 sentences max)
- [ ] Review and tighten any verbose sections

---

## 6. IT Distribution Package

**Status:** IT_SECURITY.md exists. Could be more discoverable.

- [ ] Link to `IT_SECURITY.md` from the GitHub Release body
- [ ] Link to `WCAG_VPAT.md` from the GitHub Release body
- [ ] Consider adding both as PDF attachments to the release (so IT staff can download without navigating the repo)
- [ ] Add a "For IT Administrators" section to the README that links to:
  - IT Security Summary
  - WCAG/VPAT
  - Uninstall instructions
  - Service account setup

---

## 7. Logging Transparency

**Status:** Log sanitization is implemented. Could be more visible to users.

- [ ] Add a "View Logs" button or menu item in the GUI (opens `%APPDATA%\canvas bot\canvas_bot.log` in default text editor)
- [ ] Add a tooltip or help text: "Logs contain course IDs, timestamps, and errors. No credentials or file contents are recorded."

---

## 8. About Dialog Enhancements

**Status:** About dialog exists with version, contact, and license info.

- [ ] Add current version number prominently
- [ ] Add "Check for Updates" button (ties into item 3)
- [ ] Add link to IT Security Summary and VPAT (opens in browser or shows path)
- [ ] Show VirusTotal report link for current release

---

## Priority Order

| Priority | Item | Effort | Trust Impact |
|----------|------|--------|-------------|
| 1 | Code signing | Medium (one-time setup) | High |
| 2 | First GitHub release with artifacts | Low | High |
| 3 | Update checker | Medium | Medium |
| 4 | IT distribution links | Low | Medium |
| 5 | About dialog enhancements | Low | Medium |
| 6 | Quick-start screenshots | Low | Medium |
| 7 | README badges + polish | Low | Low |
| 8 | View Logs button | Low | Low |

---

## Out of Scope for v1.3.3

- Auto-update mechanism (too complex, not needed yet)
- MSI/MSIX installer packaging (no benefit for portable app)
- Telemetry or analytics (explicitly against project values)
- GitHub Pages site (nice-to-have, not a trust requirement)
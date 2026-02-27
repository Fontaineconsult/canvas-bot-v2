# Canvas Bot — Release Checklist

## Pre-Build

- [ ] Update version string in:
  - `config/config.yaml` (`version` field)
  - `gui/app.py` (window title: `"Canvas Bot v{X.Y.Z}"`)
  - `readme.md` (any version references)
  - `claude/WCAG_VPAT.md` (header)
  - `claude/IT_SECURITY.md` (header)
- [ ] Update `CHANGELOG.md` with release notes
- [ ] Merge feature branch into `master`

## Build

- [ ] Build executable: `pyinstaller canvas_bot.spec`
- [ ] Verify bundled resources: `config.yaml`, `re.yaml`, `download_manifest.yaml`, `cb.ico`
- [ ] Check output size is reasonable (compare to previous release)

## Test

- [ ] Test on a clean Windows machine (no Python installed):
  - [ ] First-run welcome dialog appears
  - [ ] SmartScreen warning → "More info" → "Run anyway" works
  - [ ] API credential setup flow completes
  - [ ] Single course scan + download succeeds
  - [ ] Content Viewer populates after scan
  - [ ] Pattern Manager loads categories
  - [ ] Keyboard navigation works across all tabs
- [ ] Run pipeline tests against corpus (if available):
  ```
  python -m test.pipeline_testing batch-test --corpus corpus.json
  ```

## Security

- [ ] Upload `.exe` to [VirusTotal](https://www.virustotal.com/) — save the report URL
- [ ] Generate SHA-256 checksum:
  ```
  certutil -hashfile CanvasBot.exe SHA256
  ```
- [ ] (Optional) Code-sign with certificate:
  ```
  signtool sign /f cert.pfx /p PASSWORD /tr http://timestamp.digicert.com /td sha256 /fd sha256 CanvasBot.exe
  ```

## Publish

- [ ] Create GitHub release:
  - Tag: `v{X.Y.Z}`
  - Title: `Canvas Bot v{X.Y.Z}`
  - Body: changelog entry + SHA-256 checksum + VirusTotal report link
  - Attach: `CanvasBot.exe`
- [ ] Verify download link works
- [ ] Update any external documentation or distribution channels

"""
Canvas Bot EXE Test Harness
============================
Runs the compiled .exe with every combination of CLI flags to verify
they parse correctly, produce expected output, and exit cleanly.

Usage:
    # Offline tests only (no Canvas API calls)
    python -m test.exe_test_harness

    # Include API tests against a real course
    python -m test.exe_test_harness --course_id 12345

    # Custom exe path
    python -m test.exe_test_harness --exe ./my_build/canvas_bot.exe

    # Verbose mode (show stdout/stderr for every test)
    python -m test.exe_test_harness --verbose

    # Run only a specific test group
    python -m test.exe_test_harness --group patterns

    # Run using python script instead of exe (dev mode)
    python -m test.exe_test_harness --dev
"""

import subprocess
import sys
import os
import tempfile
import shutil
import time
import argparse
from dataclasses import dataclass, field
from typing import Optional


# ── Result Tracking ─────────────────────────────────────────────────

@dataclass
class TestResult:
    name: str
    group: str
    command: list
    passed: bool
    exit_code: int
    duration: float
    stdout: str = ""
    stderr: str = ""
    reason: str = ""


@dataclass
class HarnessConfig:
    exe_path: str = os.path.join("dist", "canvas_bot.exe")
    course_id: Optional[str] = None
    verbose: bool = False
    group: Optional[str] = None
    dev_mode: bool = False
    timeout: int = 120  # seconds per command


# ── Test Definitions ────────────────────────────────────────────────

@dataclass
class TestCase:
    name: str
    group: str
    args: list
    expect_exit_code: int = 0
    expect_stdout_contains: list = field(default_factory=list)
    expect_stdout_not_contains: list = field(default_factory=list)
    expect_any_output: bool = False
    requires_api: bool = False
    timeout: Optional[int] = None
    setup: Optional[str] = None      # method name on Harness to call before
    teardown: Optional[str] = None   # method name on Harness to call after


class ExeTestHarness:
    def __init__(self, config: HarnessConfig):
        self.config = config
        self.results: list[TestResult] = []
        self.temp_dir = None
        self.temp_course_list = None

    # ── Helpers ──────────────────────────────────────────────────

    def _build_cmd(self, args: list) -> list:
        if self.config.dev_mode:
            return [sys.executable, "canvas_bot.py"] + args
        return [self.config.exe_path] + args

    def _run(self, test: TestCase) -> TestResult:
        cmd = self._build_cmd(test.args)
        timeout = test.timeout or self.config.timeout
        start = time.time()

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                # Pipe stdin to /dev/null so interactive prompts don't hang
                input="",
            )
            duration = time.time() - start
            exit_code = proc.returncode
            stdout = proc.stdout
            stderr = proc.stderr
        except subprocess.TimeoutExpired:
            duration = time.time() - start
            return TestResult(
                name=test.name,
                group=test.group,
                command=cmd,
                passed=False,
                exit_code=-1,
                duration=duration,
                reason=f"TIMEOUT after {timeout}s",
            )
        except FileNotFoundError:
            return TestResult(
                name=test.name,
                group=test.group,
                command=cmd,
                passed=False,
                exit_code=-1,
                duration=0,
                reason=f"EXE not found: {cmd[0]}",
            )

        # ── Evaluate pass/fail ──
        passed = True
        reasons = []

        if exit_code != test.expect_exit_code:
            passed = False
            reasons.append(f"exit code {exit_code} != expected {test.expect_exit_code}")

        for expected in test.expect_stdout_contains:
            if expected.lower() not in stdout.lower():
                passed = False
                reasons.append(f"stdout missing: '{expected}'")

        for unexpected in test.expect_stdout_not_contains:
            if unexpected.lower() in stdout.lower():
                passed = False
                reasons.append(f"stdout unexpectedly contains: '{unexpected}'")

        if test.expect_any_output and not stdout.strip() and not stderr.strip():
            passed = False
            reasons.append("no output produced")

        return TestResult(
            name=test.name,
            group=test.group,
            command=cmd,
            passed=passed,
            exit_code=exit_code,
            duration=duration,
            stdout=stdout,
            stderr=stderr,
            reason="; ".join(reasons),
        )

    # ── Setup / Teardown helpers ────────────────────────────────

    def setup_temp_dir(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cb_test_")

    def teardown_temp_dir(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir = None

    def setup_course_list_file(self):
        """Create a temp file with the test course ID for batch tests."""
        self.setup_temp_dir()
        self.temp_course_list = os.path.join(self.temp_dir, "course_list.txt")
        with open(self.temp_course_list, "w") as f:
            f.write(f"{self.config.course_id}\n")

    # ── Test Builders ───────────────────────────────────────────

    def get_help_tests(self) -> list[TestCase]:
        return [
            TestCase(
                name="help flag -h",
                group="help",
                args=["-h"],
                expect_stdout_contains=["canvas", "course_id"],
                expect_exit_code=0,
            ),
            TestCase(
                name="help flag --help",
                group="help",
                args=["--help"],
                expect_stdout_contains=["canvas", "course_id"],
                expect_exit_code=0,
            ),
        ]

    def get_config_tests(self) -> list[TestCase]:
        return [
            TestCase(
                name="config status",
                group="config",
                args=["--config_status"],
                expect_stdout_contains=["Configuration Status"],
                expect_exit_code=0,
            ),
        ]

    def get_pattern_tests(self) -> list[TestCase]:
        """Pattern management tests - fully offline, no API needed."""
        test_pattern = r".*\.test_harness_xyz"
        tests = [
            # ── List categories ──
            TestCase(
                name="patterns-list all categories",
                group="patterns",
                args=["--patterns-list"],
                expect_stdout_contains=["document_content_regex", "image_content_regex", "Pattern Categories"],
                expect_exit_code=0,
            ),

            # ── List each known category ──
            TestCase(
                name="patterns-list document_content_regex",
                group="patterns",
                args=["--patterns-list", "document_content_regex"],
                expect_stdout_contains=["pdf", "docx"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-list image_content_regex",
                group="patterns",
                args=["--patterns-list", "image_content_regex"],
                expect_stdout_contains=["jpg", "png"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-list web_video_resources_regex",
                group="patterns",
                args=["--patterns-list", "web_video_resources_regex"],
                expect_stdout_contains=["youtu"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-list video_file_resources_regex",
                group="patterns",
                args=["--patterns-list", "video_file_resources_regex"],
                expect_stdout_contains=["mp4"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-list web_audio_resources_regex",
                group="patterns",
                args=["--patterns-list", "web_audio_resources_regex"],
                expect_stdout_contains=["audio"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-list audio_file_resources_regex",
                group="patterns",
                args=["--patterns-list", "audio_file_resources_regex"],
                expect_stdout_contains=["mp3"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-list web_document_applications_regex",
                group="patterns",
                args=["--patterns-list", "web_document_applications_regex"],
                expect_stdout_contains=["google"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-list file_storage_regex",
                group="patterns",
                args=["--patterns-list", "file_storage_regex"],
                expect_any_output=True,
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-list ignore_list_regex",
                group="patterns",
                args=["--patterns-list", "ignore_list_regex"],
                expect_stdout_contains=["wikipedia"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-list force_to_shortcut",
                group="patterns",
                args=["--patterns-list", "force_to_shortcut"],
                expect_stdout_contains=["docusign"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-list canvas_studio_embed",
                group="patterns",
                args=["--patterns-list", "canvas_studio_embed"],
                expect_any_output=True,
                expect_exit_code=0,
            ),

            # ── List invalid category ──
            TestCase(
                name="patterns-list invalid category",
                group="patterns",
                args=["--patterns-list", "fake_category_xyz"],
                expect_stdout_contains=["not found"],
                expect_exit_code=1,
            ),

            # ── Validate regex ──
            TestCase(
                name="patterns-validate valid PDF regex",
                group="patterns",
                args=["--patterns-validate", r".*\.pdf"],
                expect_stdout_contains=["Valid regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-validate valid URL regex",
                group="patterns",
                args=["--patterns-validate", r"https?://.*example\.com.*"],
                expect_stdout_contains=["Valid regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-validate valid complex regex",
                group="patterns",
                args=["--patterns-validate", r"([a-f0-9]{8}-[a-f0-9]{4})"],
                expect_stdout_contains=["Valid regex", "Groups: 1"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-validate invalid regex (unclosed bracket)",
                group="patterns",
                args=["--patterns-validate", "[unclosed"],
                expect_stdout_contains=["Invalid regex"],
                expect_exit_code=1,
            ),
            TestCase(
                name="patterns-validate invalid regex (bad group)",
                group="patterns",
                args=["--patterns-validate", "(?P<bad"],
                expect_stdout_contains=["Invalid regex"],
                expect_exit_code=1,
            ),

            # ── Test pattern matching ──
            TestCase(
                name="patterns-test PDF file",
                group="patterns",
                args=["--patterns-test", "syllabus.pdf"],
                expect_stdout_contains=["MATCH", "document_content_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test DOCX file",
                group="patterns",
                args=["--patterns-test", "assignment.docx"],
                expect_stdout_contains=["MATCH", "document_content_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test PPTX file",
                group="patterns",
                args=["--patterns-test", "lecture_slides.pptx"],
                expect_stdout_contains=["MATCH", "document_content_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test XLSX file",
                group="patterns",
                args=["--patterns-test", "gradebook.xlsx"],
                expect_stdout_contains=["MATCH", "document_content_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test CSV file",
                group="patterns",
                args=["--patterns-test", "data.csv"],
                expect_stdout_contains=["MATCH", "document_content_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test ZIP file",
                group="patterns",
                args=["--patterns-test", "project.zip"],
                expect_stdout_contains=["MATCH", "document_content_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test TXT file",
                group="patterns",
                args=["--patterns-test", "readme.txt"],
                expect_stdout_contains=["MATCH", "document_content_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test JPG image",
                group="patterns",
                args=["--patterns-test", "photo.jpg"],
                expect_stdout_contains=["MATCH", "image_content_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test PNG image",
                group="patterns",
                args=["--patterns-test", "diagram.png"],
                expect_stdout_contains=["MATCH", "image_content_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test GIF image",
                group="patterns",
                args=["--patterns-test", "animation.gif"],
                expect_stdout_contains=["MATCH", "image_content_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test SVG image",
                group="patterns",
                args=["--patterns-test", "icon.svg"],
                expect_stdout_contains=["MATCH", "image_content_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test YouTube URL",
                group="patterns",
                args=["--patterns-test", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
                expect_stdout_contains=["MATCH", "web_video_resources_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test YouTube short URL",
                group="patterns",
                args=["--patterns-test", "https://youtu.be/dQw4w9WgXcQ"],
                expect_stdout_contains=["MATCH", "web_video_resources_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test Vimeo URL",
                group="patterns",
                args=["--patterns-test", "https://vimeo.com/123456789"],
                expect_stdout_contains=["MATCH", "web_video_resources_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test Zoom recording URL",
                group="patterns",
                args=["--patterns-test", "https://us02web.zoom.us/rec/share/abc123"],
                expect_stdout_contains=["MATCH", "web_video_resources_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test Loom URL",
                group="patterns",
                args=["--patterns-test", "https://www.loom.com/share/abc123def456"],
                expect_stdout_contains=["MATCH", "web_video_resources_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test TED talk URL",
                group="patterns",
                args=["--patterns-test", "https://www.ted.com/talks/some_speaker_title"],
                expect_stdout_contains=["MATCH", "web_video_resources_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test MP4 file",
                group="patterns",
                args=["--patterns-test", "lecture_recording.mp4"],
                expect_stdout_contains=["MATCH", "video_file_resources_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test MOV file",
                group="patterns",
                args=["--patterns-test", "screen_capture.mov"],
                expect_stdout_contains=["MATCH", "video_file_resources_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test WEBM file",
                group="patterns",
                args=["--patterns-test", "clip.webm"],
                expect_stdout_contains=["MATCH", "video_file_resources_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test MKV file",
                group="patterns",
                args=["--patterns-test", "movie.mkv"],
                expect_stdout_contains=["MATCH", "video_file_resources_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test MP3 file",
                group="patterns",
                args=["--patterns-test", "podcast_episode.mp3"],
                expect_stdout_contains=["MATCH", "audio_file_resources_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test WAV file",
                group="patterns",
                args=["--patterns-test", "recording.wav"],
                expect_stdout_contains=["MATCH", "audio_file_resources_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test M4A file",
                group="patterns",
                args=["--patterns-test", "voice_memo.m4a"],
                expect_stdout_contains=["MATCH", "audio_file_resources_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test podcast URL",
                group="patterns",
                args=["--patterns-test", "https://example.com/podcast/episode-1"],
                expect_stdout_contains=["MATCH", "web_audio_resources_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test audio URL",
                group="patterns",
                args=["--patterns-test", "https://example.com/audio/lecture-1"],
                expect_stdout_contains=["MATCH", "web_audio_resources_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test Google Doc URL",
                group="patterns",
                args=["--patterns-test", "https://docs.google.com/document/d/1abc123/edit"],
                expect_stdout_contains=["MATCH", "web_document_applications_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test Google Slides URL",
                group="patterns",
                args=["--patterns-test", "https://docs.google.com/presentation/d/1abc123/edit"],
                expect_stdout_contains=["MATCH", "web_document_applications_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test Google Sheets URL",
                group="patterns",
                args=["--patterns-test", "https://docs.google.com/spreadsheets/d/1abc123/edit"],
                expect_stdout_contains=["MATCH", "web_document_applications_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test Adobe Acrobat URL",
                group="patterns",
                args=["--patterns-test", "https://acrobat.adobe.com/link/track?uri=abc"],
                expect_stdout_contains=["MATCH", "web_document_applications_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test Padlet URL",
                group="patterns",
                args=["--patterns-test", "https://padlet.com/user/board123"],
                expect_stdout_contains=["MATCH", "web_document_applications_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test Google Drive URL",
                group="patterns",
                args=["--patterns-test", "https://drive.google.com/file/d/1abc123/view"],
                expect_stdout_contains=["MATCH", "file_storage_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test Wikipedia URL (should be ignored)",
                group="patterns",
                args=["--patterns-test", "https://en.wikipedia.org/wiki/Python"],
                expect_stdout_contains=["MATCH", "ignore_list_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test unmatched URL (Unsorted)",
                group="patterns",
                args=["--patterns-test", "https://some-random-site.example.com/page"],
                expect_stdout_contains=["Unsorted"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test plain text string",
                group="patterns",
                args=["--patterns-test", "hello world"],
                expect_stdout_contains=["Unsorted"],
                expect_exit_code=0,
            ),

            # ── Add / remove cycle ──
            # Add a unique test pattern, verify it shows in list, then remove it.
            TestCase(
                name="patterns-add new pattern (skip confirm)",
                group="patterns",
                args=["--patterns-add", "document_content_regex", test_pattern, "-y"],
                expect_stdout_contains=["Pattern added"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-list verify added pattern",
                group="patterns",
                args=["--patterns-list", "document_content_regex"],
                expect_stdout_contains=["test_harness_xyz"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-add duplicate (already exists)",
                group="patterns",
                args=["--patterns-add", "document_content_regex", test_pattern, "-y"],
                expect_stdout_contains=["already exists"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-test matches added pattern",
                group="patterns",
                args=["--patterns-test", "myfile.test_harness_xyz"],
                expect_stdout_contains=["MATCH", "document_content_regex"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-remove the test pattern (skip confirm)",
                group="patterns",
                args=["--patterns-remove", "document_content_regex", test_pattern, "-y"],
                expect_stdout_contains=["Pattern removed"],
                expect_exit_code=0,
            ),
            TestCase(
                name="patterns-list verify pattern removed",
                group="patterns",
                args=["--patterns-list", "document_content_regex"],
                expect_stdout_not_contains=["test_harness_xyz"],
                expect_exit_code=0,
            ),

            # ── Error cases ──
            TestCase(
                name="patterns-add to invalid category",
                group="patterns",
                args=["--patterns-add", "nonexistent_category", ".*\\.xyz", "-y"],
                expect_stdout_contains=["not found"],
                expect_exit_code=1,
            ),
            TestCase(
                name="patterns-add invalid regex",
                group="patterns",
                args=["--patterns-add", "document_content_regex", "[invalid(regex", "-y"],
                expect_stdout_contains=["Invalid regex"],
                expect_exit_code=1,
            ),
            TestCase(
                name="patterns-remove nonexistent pattern",
                group="patterns",
                args=["--patterns-remove", "document_content_regex", "this_pattern_does_not_exist_xyz", "-y"],
                expect_stdout_contains=["not found"],
                expect_exit_code=1,
            ),
            TestCase(
                name="patterns-remove from invalid category",
                group="patterns",
                args=["--patterns-remove", "nonexistent_category", ".*\\.pdf", "-y"],
                expect_stdout_contains=["not found"],
                expect_exit_code=1,
            ),
        ]
        return tests

    def get_api_tests(self) -> list[TestCase]:
        """Tests that require a live Canvas API connection."""
        cid = self.config.course_id
        if not cid:
            return []

        self.setup_temp_dir()
        dl_dir = os.path.join(self.temp_dir, "downloads")
        json_dir = os.path.join(self.temp_dir, "json_out")
        excel_dir = os.path.join(self.temp_dir, "excel_out")
        combo_dl = os.path.join(self.temp_dir, "combo_dl")
        combo_json = os.path.join(self.temp_dir, "combo_json")
        combo_excel = os.path.join(self.temp_dir, "combo_excel")
        flat_dir = os.path.join(self.temp_dir, "flat_dl")
        all_media_dir = os.path.join(self.temp_dir, "all_media")
        hidden_dir = os.path.join(self.temp_dir, "hidden_dl")
        flush_dir = os.path.join(self.temp_dir, "flush_dl")

        tests = [
            # ── Minimal course scan (no output) ──
            TestCase(
                name="course scan (no output flags)",
                group="api_basic",
                args=["--course_id", cid],
                expect_stdout_contains=["Starting Canvas Bot"],
                expect_exit_code=0,
                requires_api=True,
                timeout=180,
            ),

            # ── Print trees ──
            TestCase(
                name="print content tree",
                group="api_tree",
                args=["--course_id", cid, "--print_content_tree"],
                expect_any_output=True,
                expect_exit_code=0,
                requires_api=True,
                timeout=180,
            ),
            TestCase(
                name="print full course tree",
                group="api_tree",
                args=["--course_id", cid, "--print_full_course"],
                expect_any_output=True,
                expect_exit_code=0,
                requires_api=True,
                timeout=180,
            ),
            TestCase(
                name="print both trees",
                group="api_tree",
                args=["--course_id", cid, "--print_content_tree", "--print_full_course"],
                expect_any_output=True,
                expect_exit_code=0,
                requires_api=True,
                timeout=180,
            ),

            # ── Downloads ──
            TestCase(
                name="download documents only",
                group="api_download",
                args=["--course_id", cid, "--download_folder", dl_dir],
                expect_exit_code=0,
                requires_api=True,
                timeout=300,
            ),
            TestCase(
                name="download with --include_video_files",
                group="api_download",
                args=["--course_id", cid, "--download_folder", all_media_dir,
                       "--include_video_files"],
                expect_exit_code=0,
                requires_api=True,
                timeout=300,
            ),
            TestCase(
                name="download with --include_audio_files",
                group="api_download",
                args=["--course_id", cid, "--download_folder", all_media_dir,
                       "--include_audio_files"],
                expect_exit_code=0,
                requires_api=True,
                timeout=300,
            ),
            TestCase(
                name="download with --include_image_files",
                group="api_download",
                args=["--course_id", cid, "--download_folder", all_media_dir,
                       "--include_image_files"],
                expect_exit_code=0,
                requires_api=True,
                timeout=300,
            ),
            TestCase(
                name="download ALL media types",
                group="api_download",
                args=["--course_id", cid, "--download_folder", all_media_dir,
                       "--include_video_files", "--include_audio_files", "--include_image_files"],
                expect_exit_code=0,
                requires_api=True,
                timeout=600,
            ),
            TestCase(
                name="download with --download_hidden_files",
                group="api_download",
                args=["--course_id", cid, "--download_folder", hidden_dir,
                       "--download_hidden_files"],
                expect_exit_code=0,
                requires_api=True,
                timeout=300,
            ),
            TestCase(
                name="download with --flatten",
                group="api_download",
                args=["--course_id", cid, "--download_folder", flat_dir, "--flatten"],
                expect_exit_code=0,
                requires_api=True,
                timeout=300,
            ),
            TestCase(
                name="download with --flush_after_download",
                group="api_download",
                args=["--course_id", cid, "--download_folder", flush_dir,
                       "--flush_after_download"],
                expect_exit_code=0,
                requires_api=True,
                timeout=300,
            ),

            # ── JSON export ──
            TestCase(
                name="output as JSON",
                group="api_export",
                args=["--course_id", cid, "--output_as_json", json_dir],
                expect_exit_code=0,
                requires_api=True,
                timeout=180,
            ),

            # ── Excel export ──
            TestCase(
                name="output as Excel",
                group="api_export",
                args=["--course_id", cid, "--output_as_excel", excel_dir],
                expect_exit_code=0,
                requires_api=True,
                timeout=180,
            ),
            # ── Combined outputs ──
            TestCase(
                name="download + JSON export",
                group="api_combo",
                args=["--course_id", cid,
                       "--download_folder", combo_dl,
                       "--output_as_json", combo_json],
                expect_exit_code=0,
                requires_api=True,
                timeout=300,
            ),
            TestCase(
                name="download + Excel export",
                group="api_combo",
                args=["--course_id", cid,
                       "--download_folder", combo_dl,
                       "--output_as_excel", combo_excel],
                expect_exit_code=0,
                requires_api=True,
                timeout=300,
            ),
            TestCase(
                name="download + JSON + Excel (triple)",
                group="api_combo",
                args=["--course_id", cid,
                       "--download_folder", combo_dl,
                       "--output_as_json", combo_json,
                       "--output_as_excel", combo_excel],
                expect_exit_code=0,
                requires_api=True,
                timeout=300,
            ),
            TestCase(
                name="full kitchen sink",
                group="api_combo",
                args=["--course_id", cid,
                       "--download_folder", combo_dl,
                       "--output_as_json", combo_json,
                       "--output_as_excel", combo_excel,
                       "--include_video_files",
                       "--include_audio_files",
                       "--include_image_files",
                       "--download_hidden_files",
                       "--print_content_tree"],
                expect_exit_code=0,
                requires_api=True,
                timeout=600,
            ),

            # ── JSON + tree ──
            TestCase(
                name="JSON export + print tree",
                group="api_combo",
                args=["--course_id", cid,
                       "--output_as_json", json_dir,
                       "--print_content_tree"],
                expect_any_output=True,
                expect_exit_code=0,
                requires_api=True,
                timeout=180,
            ),

            # ── Excel + hidden ──
            TestCase(
                name="Excel export with hidden files",
                group="api_combo",
                args=["--course_id", cid,
                       "--output_as_excel", excel_dir,
                       "--download_hidden_files"],
                expect_exit_code=0,
                requires_api=True,
                timeout=180,
            ),
        ]
        return tests

    def get_batch_tests(self) -> list[TestCase]:
        """Batch processing tests (require API + course list file)."""
        cid = self.config.course_id
        if not cid:
            return []

        self.setup_course_list_file()
        batch_dl = os.path.join(self.temp_dir, "batch_dl")
        batch_json = os.path.join(self.temp_dir, "batch_json")
        batch_excel = os.path.join(self.temp_dir, "batch_excel")

        return [
            TestCase(
                name="batch download from course list",
                group="api_batch",
                args=["--course_id_list", self.temp_course_list,
                       "--download_folder", batch_dl],
                expect_exit_code=0,
                requires_api=True,
                timeout=300,
            ),
            TestCase(
                name="batch JSON export from course list",
                group="api_batch",
                args=["--course_id_list", self.temp_course_list,
                       "--output_as_json", batch_json],
                expect_exit_code=0,
                requires_api=True,
                timeout=300,
            ),
            TestCase(
                name="batch Excel export from course list",
                group="api_batch",
                args=["--course_id_list", self.temp_course_list,
                       "--output_as_excel", batch_excel],
                expect_exit_code=0,
                requires_api=True,
                timeout=300,
            ),
        ]

    def get_error_handling_tests(self) -> list[TestCase]:
        """Tests for error conditions and edge cases."""
        tests = [
            # Non-existent course list file
            TestCase(
                name="non-existent course list file",
                group="errors",
                args=["--course_id_list", "this_file_does_not_exist_xyz.txt",
                       "--download_folder", "."],
                expect_exit_code=1,  # should error
                requires_api=False,
                timeout=30,
            ),
        ]

        return tests

    # ── Runner ──────────────────────────────────────────────────

    def collect_all_tests(self) -> list[TestCase]:
        all_tests = []
        all_tests.extend(self.get_help_tests())
        all_tests.extend(self.get_config_tests())
        all_tests.extend(self.get_pattern_tests())
        all_tests.extend(self.get_error_handling_tests())

        # API tests (only if course_id provided)
        if self.config.course_id:
            all_tests.extend(self.get_api_tests())
            all_tests.extend(self.get_batch_tests())

        return all_tests

    def run(self):
        all_tests = self.collect_all_tests()

        # Filter by group if specified
        if self.config.group:
            all_tests = [t for t in all_tests if self.config.group in t.group]

        if not all_tests:
            print(f"No tests matched group filter: '{self.config.group}'")
            print(f"Available groups: {sorted(set(t.group for t in self.collect_all_tests()))}")
            return

        total = len(all_tests)
        print("=" * 70)
        print(f"  Canvas Bot EXE Test Harness")
        print(f"  EXE:       {self.config.exe_path if not self.config.dev_mode else 'python canvas_bot.py (dev)'}")
        print(f"  Course ID: {self.config.course_id or 'None (offline only)'}")
        print(f"  Tests:     {total}")
        print(f"  Groups:    {', '.join(sorted(set(t.group for t in all_tests)))}")
        print("=" * 70)
        print()

        for i, test in enumerate(all_tests, 1):
            # Skip API tests if no course ID
            if test.requires_api and not self.config.course_id:
                continue

            label = f"[{i}/{total}]"
            print(f"  {label:<10} {test.group:<20} {test.name:<45} ", end="", flush=True)

            result = self._run(test)
            self.results.append(result)

            status = "PASS" if result.passed else "FAIL"
            duration_str = f"({result.duration:.1f}s)"
            if result.passed:
                print(f"{status} {duration_str}")
            else:
                print(f"** {status} ** {duration_str}")
                print(f"{'':>12}Reason: {result.reason}")
                if result.exit_code != test.expect_exit_code:
                    print(f"{'':>12}Exit code: {result.exit_code}")

            if self.config.verbose:
                if result.stdout.strip():
                    for line in result.stdout.strip().split("\n")[:20]:
                        print(f"{'':>12}  stdout: {line}")
                    if result.stdout.strip().count("\n") > 20:
                        print(f"{'':>12}  ... ({result.stdout.strip().count(chr(10)) - 20} more lines)")
                if result.stderr.strip():
                    for line in result.stderr.strip().split("\n")[:10]:
                        print(f"{'':>12}  stderr: {line}")

        self._print_summary()
        self._cleanup()

    def _print_summary(self):
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)
        total_time = sum(r.duration for r in self.results)

        print()
        print("=" * 70)
        print(f"  RESULTS SUMMARY")
        print("=" * 70)
        print(f"  Total:   {total}")
        print(f"  Passed:  {passed}")
        print(f"  Failed:  {failed}")
        print(f"  Time:    {total_time:.1f}s")
        print()

        if failed:
            # Group by group
            groups = {}
            for r in self.results:
                if not r.passed:
                    groups.setdefault(r.group, []).append(r)

            print(f"  FAILURES:")
            print(f"  {'-' * 66}")
            for group, results in groups.items():
                print(f"  [{group}]")
                for r in results:
                    print(f"    - {r.name}")
                    print(f"      {r.reason}")
                    cmd_str = " ".join(r.command)
                    if len(cmd_str) > 80:
                        cmd_str = cmd_str[:77] + "..."
                    print(f"      cmd: {cmd_str}")
                print()

        # Per-group breakdown
        group_stats = {}
        for r in self.results:
            stats = group_stats.setdefault(r.group, {"passed": 0, "failed": 0, "time": 0.0})
            if r.passed:
                stats["passed"] += 1
            else:
                stats["failed"] += 1
            stats["time"] += r.duration

        print(f"  BY GROUP:")
        print(f"  {'-' * 66}")
        print(f"  {'Group':<25} {'Pass':>6} {'Fail':>6} {'Total':>7} {'Time':>8}")
        print(f"  {'-' * 66}")
        for group, stats in sorted(group_stats.items()):
            total_g = stats["passed"] + stats["failed"]
            print(f"  {group:<25} {stats['passed']:>6} {stats['failed']:>6} {total_g:>7} {stats['time']:>7.1f}s")
        print(f"  {'-' * 66}")
        print(f"  {'TOTAL':<25} {passed:>6} {failed:>6} {total:>7} {total_time:>7.1f}s")
        print("=" * 70)

        if failed == 0:
            print("\n  ALL TESTS PASSED\n")
        else:
            print(f"\n  {failed} TEST(S) FAILED\n")

    def _cleanup(self):
        self.teardown_temp_dir()
        # Clean up default csv that --export_course_list may create in cwd
        default_csv = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "canvas_courses.csv"
        )
        if os.path.exists(default_csv):
            try:
                os.remove(default_csv)
            except OSError:
                pass


# ── CLI Entry Point ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Canvas Bot EXE Test Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Offline tests only (patterns, config, help)
  python -m test.exe_test_harness

  # Include API tests with a real course
  python -m test.exe_test_harness --course_id 12345

  # Dev mode (run canvas_bot.py directly instead of exe)
  python -m test.exe_test_harness --dev --course_id 12345

  # Run only pattern tests
  python -m test.exe_test_harness --group patterns

  # Verbose output
  python -m test.exe_test_harness --verbose --course_id 12345

Available test groups:
  help                 Help flag tests
  config               Configuration status
  patterns             Pattern CRUD, validation, matching
  errors               Error handling edge cases
  api_basic            Minimal course scan
  api_tree             Tree display
  api_download         File download variations
  api_export           JSON/Excel export
  api_combo            Combined output flags
  api_batch            Batch course processing
        """,
    )
    parser.add_argument("--exe", default=os.path.join("dist", "canvas_bot.exe"),
                        help="Path to the compiled exe (default: dist/canvas_bot.exe)")
    parser.add_argument("--course_id", default=None,
                        help="Canvas course ID for API tests")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show stdout/stderr for every test")
    parser.add_argument("--group", "-g", default=None,
                        help="Only run tests in this group (substring match)")
    parser.add_argument("--dev", action="store_true",
                        help="Run canvas_bot.py directly instead of the exe")
    parser.add_argument("--timeout", type=int, default=120,
                        help="Default timeout per command in seconds (default: 120)")

    args = parser.parse_args()

    config = HarnessConfig(
        exe_path=args.exe,
        course_id=args.course_id,
        verbose=args.verbose,
        group=args.group,
        dev_mode=args.dev,
        timeout=args.timeout,
    )

    # Sanity check: does the exe exist?
    if not config.dev_mode and not os.path.exists(config.exe_path):
        print(f"ERROR: EXE not found at '{config.exe_path}'")
        print(f"  Use --exe to specify the path, or --dev to test canvas_bot.py directly.")
        sys.exit(1)

    harness = ExeTestHarness(config)
    harness.run()

    # Exit with non-zero if any failures
    failed = sum(1 for r in harness.results if not r.passed)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

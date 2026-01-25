"""
Direct pipeline tester - tests derive_file_name() and other functions
directly against raw API data without running the full canvas_bot scan.

This tests the data transformation logic in isolation.
"""

import json
import os
from typing import Dict, List, Any
from dataclasses import dataclass, field
from urllib.parse import unquote_plus


@dataclass
class TestResult:
    """Result of testing one raw API item."""
    file_id: int
    display_name: str
    filename: str
    mime_class: str
    derived_title: str
    derived_file_name: str
    issues: List[str] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0


class MockNode:
    """Mock content node for testing derive_file_name without full instantiation."""

    def __init__(self, raw_api: dict):
        self.api_dict = raw_api
        self.is_canvas_file = True
        self.is_canvas_studio_file = False
        self.file_name = None
        self.download_url = raw_api.get("url")
        self.download_url_is_manifest = False
        self.url = raw_api.get("url")

        # Simulate _expand_api_dict_to_class_attributes
        for key, value in raw_api.items():
            setattr(self, key, value)

        # Simulate title derivation (matches fixed base_content_node.py)
        # Priority: display_name -> title -> filename (decoded)
        if raw_api.get('display_name'):
            self.title = raw_api['display_name']
        elif raw_api.get('title'):
            self.title = raw_api['title']
        elif raw_api.get('filename'):
            self.title = unquote_plus(raw_api['filename'])


class DirectPipelineTester:
    """Tests pipeline functions directly against raw API data."""

    def __init__(self):
        self.results: List[TestResult] = []

    def load_raw_data(self, raw_file: str) -> Dict[str, Any]:
        """Load raw API data (supports both old and new collector formats)."""
        with open(raw_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data

    def extract_files(self, data: Dict) -> List[Dict]:
        """Extract file entries from raw data (handles nested 'raw' format)."""
        files = []
        for entry in data.get("files", []):
            if "raw" in entry:
                files.append(entry["raw"])
            else:
                files.append(entry)
        return files

    def test_derive_file_name(self, raw_api: dict) -> str:
        """Test derive_file_name() against raw API data."""
        # Import here to avoid circular imports
        from core.downloader import derive_file_name

        node = MockNode(raw_api)
        return derive_file_name(node)

    def test_file(self, raw_api: dict) -> TestResult:
        """Test a single file entry."""
        result = TestResult(
            file_id=raw_api.get("id", 0),
            display_name=raw_api.get("display_name", ""),
            filename=raw_api.get("filename", ""),
            mime_class=raw_api.get("mime_class", ""),
            derived_title="",
            derived_file_name=""
        )

        # Test title derivation
        node = MockNode(raw_api)
        result.derived_title = node.title or ""

        # Test file_name derivation
        try:
            result.derived_file_name = self.test_derive_file_name(raw_api) or ""
        except Exception as e:
            result.issues.append(f"DERIVE_ERROR: {e}")
            return result

        # Check for issues
        self._validate_result(raw_api, result)

        return result

    def _validate_result(self, raw_api: dict, result: TestResult):
        """Validate the derived values against raw API data."""

        # Issue: Title is filename instead of display_name
        display_name = raw_api.get("display_name", "")
        filename = raw_api.get("filename", "")

        if display_name and filename and display_name != filename:
            if result.derived_title == filename:
                result.issues.append(
                    f"TITLE_IS_FILENAME: title='{filename}' but display_name='{display_name}'"
                )

        # Issue: Extension mismatch between raw and derived
        if filename:
            raw_ext = os.path.splitext(filename)[1].lower()
            derived_ext = os.path.splitext(result.derived_file_name)[1].lower() if result.derived_file_name else ""

            if raw_ext and derived_ext and raw_ext != derived_ext:
                result.issues.append(
                    f"EXTENSION_MISMATCH: expected='{raw_ext}', got='{derived_ext}'"
                )

        # Issue: URL encoding not decoded
        if result.derived_file_name and "+" in result.derived_file_name:
            decoded = unquote_plus(result.derived_file_name)
            if decoded != result.derived_file_name:
                result.issues.append(
                    f"URL_ENCODED: '{result.derived_file_name}' contains unresolved encoding"
                )

        # Issue: No filename derived
        if not result.derived_file_name:
            result.issues.append("NO_FILENAME: derive_file_name returned empty")

        # Issue: Invalid Windows characters
        if result.derived_file_name:
            invalid = set(result.derived_file_name) & set('<>:"/\\|?*')
            if invalid:
                result.issues.append(f"INVALID_CHARS: {invalid}")

    def test_raw_file(self, raw_file: str) -> List[TestResult]:
        """Test all entries in a raw data file."""
        data = self.load_raw_data(raw_file)
        files = self.extract_files(data)

        self.results = []
        for raw_api in files:
            result = self.test_file(raw_api)
            self.results.append(result)

        return self.results

    def get_issues_summary(self) -> Dict[str, int]:
        """Get count of each issue type."""
        summary = {}
        for result in self.results:
            for issue in result.issues:
                issue_type = issue.split(":")[0]
                summary[issue_type] = summary.get(issue_type, 0) + 1
        return summary

    def get_items_with_issues(self) -> List[TestResult]:
        """Get only items with issues."""
        return [r for r in self.results if r.has_issues]

    def print_report(self):
        """Print test report."""
        issues = self.get_items_with_issues()
        summary = self.get_issues_summary()

        print("\n" + "=" * 70)
        print("DIRECT PIPELINE TEST REPORT")
        print("=" * 70)
        print(f"Total files tested: {len(self.results)}")
        print(f"Files with issues: {len(issues)} ({len(issues)*100//max(len(self.results),1)}%)")
        print(f"Files OK: {len(self.results) - len(issues)}")

        if summary:
            print("\nIssues by type:")
            for issue_type, count in sorted(summary.items(), key=lambda x: -x[1]):
                print(f"  {issue_type}: {count}")

        if issues:
            print("\n" + "-" * 70)
            print("SAMPLE ISSUES (first 10):")
            print("-" * 70)
            for result in issues[:10]:
                print(f"\nFile ID: {result.file_id}")
                print(f"  Raw display_name: {result.display_name}")
                print(f"  Raw filename: {result.filename}")
                print(f"  Raw mime_class: {result.mime_class}")
                print(f"  Derived title: {result.derived_title}")
                print(f"  Derived file_name: {result.derived_file_name}")
                print(f"  Issues:")
                for issue in result.issues:
                    print(f"    - {issue}")

        print("\n" + "=" * 70)

    def save_report(self, output_file: str):
        """Save report to JSON."""
        report = {
            "total_tested": len(self.results),
            "total_with_issues": len(self.get_items_with_issues()),
            "issues_summary": self.get_issues_summary(),
            "all_results": [
                {
                    "file_id": r.file_id,
                    "display_name": r.display_name,
                    "filename": r.filename,
                    "mime_class": r.mime_class,
                    "derived_title": r.derived_title,
                    "derived_file_name": r.derived_file_name,
                    "issues": r.issues,
                    "has_issues": r.has_issues
                }
                for r in self.results
            ]
        }
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to {output_file}")

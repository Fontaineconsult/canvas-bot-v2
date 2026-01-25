"""
Batch tester - runs pipeline tests against collected corpus.
No API calls needed - works entirely offline.
"""

import json
import os
from typing import Dict, List, Any
from dataclasses import dataclass, field
from urllib.parse import unquote_plus


@dataclass
class FileTestResult:
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
    """Mock node matching fixed pipeline logic."""

    def __init__(self, raw: dict):
        self.is_canvas_file = True
        self.is_canvas_studio_file = False
        self.file_name = None
        self.download_url = None
        self.download_url_is_manifest = False
        self.url = None

        # Set all raw attributes
        for key, value in raw.items():
            setattr(self, key, value)

        # Title derivation (matches fixed base_content_node.py)
        if raw.get('display_name'):
            self.title = raw['display_name']
        elif raw.get('title'):
            self.title = raw['title']
        elif raw.get('filename'):
            self.title = unquote_plus(raw['filename'])
        else:
            self.title = None


def derive_file_name_test(node: MockNode) -> str:
    """Test version of derive_file_name matching fixed logic."""
    if getattr(node, "display_name", None):
        return node.display_name

    if node.file_name:
        return node.file_name

    if getattr(node, "filename", None):
        return unquote_plus(getattr(node, "filename"))

    if node.title:
        return node.title

    return None


class BatchTester:
    """Tests pipeline against batch-collected corpus."""

    def __init__(self):
        self.results: List[FileTestResult] = []
        self.by_course: Dict[str, List[FileTestResult]] = {}

    def test_file(self, raw: dict) -> FileTestResult:
        """Test a single file entry."""
        node = MockNode(raw)
        derived_name = derive_file_name_test(node)

        result = FileTestResult(
            file_id=raw.get("id", 0),
            display_name=raw.get("display_name", ""),
            filename=raw.get("filename", ""),
            mime_class=raw.get("mime_class", ""),
            derived_title=node.title or "",
            derived_file_name=derived_name or ""
        )

        # Validate
        self._validate(raw, node, derived_name, result)
        return result

    def _validate(self, raw: dict, node: MockNode, derived_name: str, result: FileTestResult):
        """Check for issues."""
        display_name = raw.get("display_name", "")
        filename = raw.get("filename", "")

        # Check: Title should match display_name
        if display_name and node.title != display_name:
            result.issues.append(f"TITLE_MISMATCH: got '{node.title}', expected '{display_name}'")

        # Check: Derived filename should match display_name
        if display_name and derived_name != display_name:
            result.issues.append(f"FILENAME_MISMATCH: got '{derived_name}', expected '{display_name}'")

        # Check: URL encoding not decoded
        if derived_name and "+" in derived_name:
            result.issues.append(f"URL_ENCODED: '{derived_name}' contains '+'")

        # Check: No filename derived
        if not derived_name:
            result.issues.append("NO_FILENAME")

    def test_corpus(self, corpus_file: str) -> Dict[str, Any]:
        """
        Test all files in a batch corpus.

        Args:
            corpus_file: Path to JSON from batch_collector

        Returns:
            Summary dict with results
        """
        with open(corpus_file, 'r', encoding='utf-8') as f:
            corpus = json.load(f)

        self.results = []
        self.by_course = {}

        courses = corpus.get("courses", {})
        total_courses = len(courses)

        for i, (course_id, files) in enumerate(courses.items()):
            print(f"[{i+1}/{total_courses}] Testing course {course_id} ({len(files)} files)...", end=" ")

            course_results = []
            for file_data in files:
                result = self.test_file(file_data)
                course_results.append(result)
                self.results.append(result)

            self.by_course[course_id] = course_results

            issues_count = sum(1 for r in course_results if r.has_issues)
            if issues_count:
                print(f"{issues_count} issues")
            else:
                print("OK")

        return self.get_summary()

    def get_summary(self) -> Dict[str, Any]:
        """Get test summary."""
        issues_by_type = {}
        for r in self.results:
            for issue in r.issues:
                issue_type = issue.split(":")[0]
                issues_by_type[issue_type] = issues_by_type.get(issue_type, 0) + 1

        return {
            "total_files": len(self.results),
            "files_with_issues": sum(1 for r in self.results if r.has_issues),
            "files_ok": sum(1 for r in self.results if not r.has_issues),
            "total_courses": len(self.by_course),
            "issues_by_type": issues_by_type,
            "pass_rate": (len(self.results) - sum(1 for r in self.results if r.has_issues)) / max(len(self.results), 1) * 100
        }

    def print_report(self):
        """Print test report."""
        summary = self.get_summary()

        print("\n" + "=" * 60)
        print("BATCH TEST REPORT")
        print("=" * 60)
        print(f"Courses tested: {summary['total_courses']}")
        print(f"Files tested: {summary['total_files']}")
        print(f"Files OK: {summary['files_ok']} ({summary['pass_rate']:.1f}%)")
        print(f"Files with issues: {summary['files_with_issues']}")

        if summary['issues_by_type']:
            print("\nIssues by type:")
            for issue_type, count in sorted(summary['issues_by_type'].items(), key=lambda x: -x[1]):
                print(f"  {issue_type}: {count}")

        # Show sample issues
        issues = [r for r in self.results if r.has_issues]
        if issues:
            print("\n" + "-" * 60)
            print(f"SAMPLE ISSUES (first 5 of {len(issues)}):")
            for r in issues[:5]:
                print(f"\n  File {r.file_id}:")
                print(f"    display_name: {r.display_name}")
                print(f"    filename: {r.filename}")
                print(f"    derived: {r.derived_file_name}")
                for issue in r.issues:
                    print(f"    ! {issue}")

        print("\n" + "=" * 60)

    def save_report(self, output_file: str):
        """Save detailed report to JSON."""
        report = {
            "summary": self.get_summary(),
            "by_course": {
                course_id: {
                    "total": len(results),
                    "issues": sum(1 for r in results if r.has_issues),
                    "files_with_issues": [
                        {
                            "file_id": r.file_id,
                            "display_name": r.display_name,
                            "filename": r.filename,
                            "derived": r.derived_file_name,
                            "issues": r.issues
                        }
                        for r in results if r.has_issues
                    ]
                }
                for course_id, results in self.by_course.items()
            }
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to {output_file}")

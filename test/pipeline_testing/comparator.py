"""
Comparator module for validating pipeline output against raw API data.

Compares:
- --output_as_json results (what canvas_bot produced)
- raw API data (ground truth)

Identifies discrepancies in:
- title derivation
- file_name derivation
- file extensions
- mime_class mapping
"""

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from urllib.parse import unquote_plus


@dataclass
class ComparisonResult:
    """Result of comparing one item."""
    file_id: int
    raw_display_name: str
    raw_filename: str
    raw_mime_class: str
    processed_title: Optional[str]
    processed_file_name: Optional[str]
    processed_file_type: Optional[str]
    issues: List[str] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0


class PipelineComparator:
    """Compares pipeline output against raw API data."""

    def __init__(self):
        self.results: List[ComparisonResult] = []

    def load_raw_data(self, raw_file: str) -> Dict[str, Any]:
        """Load raw API data collected by collector."""
        with open(raw_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_processed_data(self, processed_file: str) -> Dict[str, Any]:
        """Load --output_as_json output from canvas_bot."""
        with open(processed_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def build_raw_lookup(self, raw_data: Dict) -> Dict[int, Dict]:
        """Build lookup dict by file ID from raw data."""
        lookup = {}
        for f in raw_data.get("files", []):
            if f.get("id"):
                lookup[f["id"]] = f
        return lookup

    def build_processed_lookup(self, processed_data: Dict) -> Dict[str, Dict]:
        """
        Build lookup by URL from processed data.
        Searches through all content types.
        """
        lookup = {}
        for content_type in ["documents", "video_files", "audio_files", "image_files",
                             "video_sites", "document_sites", "unsorted"]:
            for item in processed_data.get(content_type, []):
                url = item.get("url")
                if url:
                    lookup[url] = item
        return lookup

    def extract_file_id_from_url(self, url: str) -> Optional[int]:
        """Extract Canvas file ID from URL like /files/12345/..."""
        if not url:
            return None
        import re
        match = re.search(r'/files/(\d+)', url)
        if match:
            return int(match.group(1))
        return None

    def compare(self, raw_file: str, processed_file: str) -> List[ComparisonResult]:
        """
        Compare raw API data with processed output.

        Args:
            raw_file: Path to raw_COURSEID.json from collector
            processed_file: Path to --output_as_json output

        Returns:
            List of comparison results with any issues found
        """
        raw_data = self.load_raw_data(raw_file)
        processed_data = self.load_processed_data(processed_file)

        raw_lookup = self.build_raw_lookup(raw_data)
        processed_lookup = self.build_processed_lookup(processed_data)

        self.results = []

        # For each raw file, find corresponding processed item
        for file_id, raw in raw_lookup.items():
            # Find processed item by URL
            raw_url = raw.get("url", "")
            processed = None

            for url, item in processed_lookup.items():
                if str(file_id) in url or self.extract_file_id_from_url(url) == file_id:
                    processed = item
                    break

            result = ComparisonResult(
                file_id=file_id,
                raw_display_name=raw.get("display_name", ""),
                raw_filename=raw.get("filename", ""),
                raw_mime_class=raw.get("mime_class", ""),
                processed_title=processed.get("title") if processed else None,
                processed_file_name=processed.get("file_name") if processed else None,
                processed_file_type=processed.get("file_type") if processed else None,
            )

            # Check for issues
            if not processed:
                result.issues.append("NOT_FOUND_IN_OUTPUT")
            else:
                self._check_issues(raw, processed, result)

            self.results.append(result)

        return self.results

    def _check_issues(self, raw: Dict, processed: Dict, result: ComparisonResult):
        """Check for discrepancies between raw and processed."""

        # Issue: Title uses filename instead of display_name
        if raw.get("display_name") and raw.get("filename"):
            if result.processed_title == raw["filename"]:
                if raw["display_name"] != raw["filename"]:
                    result.issues.append(f"TITLE_IS_FILENAME: expected '{raw['display_name']}', got '{raw['filename']}'")

        # Issue: Extension mismatch
        if raw.get("filename") and result.processed_file_name:
            raw_ext = os.path.splitext(raw["filename"])[1].lower()
            proc_ext = os.path.splitext(result.processed_file_name)[1].lower()
            if raw_ext and proc_ext and raw_ext != proc_ext:
                result.issues.append(f"EXTENSION_MISMATCH: raw='{raw_ext}', processed='{proc_ext}'")

        # Issue: File name contains URL encoding
        if result.processed_file_name and "+" in result.processed_file_name:
            decoded = unquote_plus(result.processed_file_name)
            if decoded != result.processed_file_name:
                result.issues.append(f"URL_ENCODED: '{result.processed_file_name}' should be '{decoded}'")

        # Issue: mime_class not preserved
        if raw.get("mime_class") and result.processed_file_type:
            if raw["mime_class"] != result.processed_file_type:
                result.issues.append(f"MIME_MISMATCH: raw='{raw['mime_class']}', processed='{result.processed_file_type}'")

        # Issue: No file_name derived
        if not result.processed_file_name:
            result.issues.append("NO_FILENAME_DERIVED")

    def get_issues_summary(self) -> Dict[str, int]:
        """Get count of each issue type."""
        summary = {}
        for result in self.results:
            for issue in result.issues:
                issue_type = issue.split(":")[0]
                summary[issue_type] = summary.get(issue_type, 0) + 1
        return summary

    def get_items_with_issues(self) -> List[ComparisonResult]:
        """Get only items that have issues."""
        return [r for r in self.results if r.has_issues]

    def print_report(self):
        """Print comparison report."""
        issues = self.get_items_with_issues()
        summary = self.get_issues_summary()

        print("\n" + "=" * 70)
        print("PIPELINE COMPARISON REPORT")
        print("=" * 70)
        print(f"Total items compared: {len(self.results)}")
        print(f"Items with issues: {len(issues)} ({len(issues)*100//max(len(self.results),1)}%)")
        print(f"Items OK: {len(self.results) - len(issues)}")

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
                print(f"  Raw display_name: {result.raw_display_name}")
                print(f"  Raw filename: {result.raw_filename}")
                print(f"  Raw mime_class: {result.raw_mime_class}")
                print(f"  Processed title: {result.processed_title}")
                print(f"  Processed file_name: {result.processed_file_name}")
                print(f"  Issues:")
                for issue in result.issues:
                    print(f"    - {issue}")

        print("\n" + "=" * 70)

    def save_report(self, output_file: str):
        """Save detailed report to JSON."""
        report = {
            "total_compared": len(self.results),
            "total_with_issues": len(self.get_items_with_issues()),
            "issues_summary": self.get_issues_summary(),
            "items_with_issues": [
                {
                    "file_id": r.file_id,
                    "raw_display_name": r.raw_display_name,
                    "raw_filename": r.raw_filename,
                    "raw_mime_class": r.raw_mime_class,
                    "processed_title": r.processed_title,
                    "processed_file_name": r.processed_file_name,
                    "processed_file_type": r.processed_file_type,
                    "issues": r.issues
                }
                for r in self.get_items_with_issues()
            ]
        }
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to {output_file}")

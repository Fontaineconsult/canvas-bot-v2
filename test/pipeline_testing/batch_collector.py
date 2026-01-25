"""
Efficient batch collector for pipeline testing.
Minimizes API calls by only fetching files API with essential fields.

Usage:
    python -m test.pipeline_testing batch --file course_ids.txt --output ./test_corpus
"""

import json
import os
import time
from datetime import datetime
from typing import List, Dict, Any

from network.api import get_course, get_files
from network.cred import set_canvas_api_key_to_environment_variable, load_config_data_from_appdata


# Only the fields we need for testing
ESSENTIAL_FIELDS = ['id', 'display_name', 'filename', 'mime_class']


def extract_essential(raw: dict) -> dict:
    """Extract only essential fields to minimize storage."""
    return {k: raw.get(k) for k in ESSENTIAL_FIELDS}


class BatchCollector:
    """Efficiently collects test data from many courses."""

    def __init__(self, delay: float = 0.5):
        """
        Args:
            delay: Seconds between API calls to avoid rate limiting
        """
        self.delay = delay
        self.ensure_credentials()

    def ensure_credentials(self):
        set_canvas_api_key_to_environment_variable()
        load_config_data_from_appdata()

    def collect_course(self, course_id: str) -> Dict[str, Any]:
        """Collect minimal data from one course (1-2 API calls)."""
        result = {
            "course_id": course_id,
            "success": False,
            "files": [],
            "file_count": 0
        }

        # One API call: get files
        files = get_files(course_id)
        if files:
            result["success"] = True
            result["files"] = [extract_essential(f) for f in files]
            result["file_count"] = len(files)

        return result

    def collect_batch(self, course_ids: List[str], output_file: str,
                      progress_callback=None) -> Dict[str, Any]:
        """
        Collect from multiple courses, saving to single JSON file.

        Args:
            course_ids: List of course IDs
            output_file: Path to save results
            progress_callback: Optional function(current, total, course_id)
        """
        corpus = {
            "collected_at": datetime.now().isoformat(),
            "total_courses": len(course_ids),
            "successful_courses": 0,
            "failed_courses": [],
            "total_files": 0,
            "courses": {}
        }

        for i, course_id in enumerate(course_ids):
            if progress_callback:
                progress_callback(i + 1, len(course_ids), course_id)
            else:
                print(f"[{i+1}/{len(course_ids)}] Collecting {course_id}...", end=" ")

            try:
                result = self.collect_course(course_id)

                if result["success"]:
                    corpus["courses"][course_id] = result["files"]
                    corpus["successful_courses"] += 1
                    corpus["total_files"] += result["file_count"]
                    print(f"{result['file_count']} files")
                else:
                    corpus["failed_courses"].append(course_id)
                    print("failed")

            except Exception as e:
                corpus["failed_courses"].append(course_id)
                print(f"error: {e}")

            # Rate limiting delay
            if i < len(course_ids) - 1:
                time.sleep(self.delay)

        # Save corpus
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(corpus, f, indent=2)

        return corpus

    def collect_from_file(self, course_list_file: str, output_file: str) -> Dict[str, Any]:
        """Collect from courses listed in a file (one ID per line)."""
        with open(course_list_file, 'r') as f:
            course_ids = [line.strip() for line in f
                         if line.strip() and not line.startswith('#')]
        return self.collect_batch(course_ids, output_file)

    def collect_from_range(self, start: int, end: int, output_file: str) -> Dict[str, Any]:
        """Collect from a range of course IDs."""
        course_ids = [str(i) for i in range(start, end + 1)]
        return self.collect_batch(course_ids, output_file)


def print_corpus_summary(corpus: Dict[str, Any]):
    """Print summary of collected corpus."""
    print("\n" + "=" * 50)
    print("BATCH COLLECTION COMPLETE")
    print("=" * 50)
    print(f"Courses attempted: {corpus['total_courses']}")
    print(f"Courses successful: {corpus['successful_courses']}")
    print(f"Courses failed: {len(corpus['failed_courses'])}")
    print(f"Total files collected: {corpus['total_files']}")
    print(f"Average files/course: {corpus['total_files'] / max(corpus['successful_courses'], 1):.1f}")
    print("=" * 50)

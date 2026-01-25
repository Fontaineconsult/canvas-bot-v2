"""
Collector module for gathering minimal raw API data needed for pipeline validation.
Stores only the fields that matter for comparison with processed output.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any

from network.api import get_course, get_files, get_media_objects
from network.cred import set_canvas_api_key_to_environment_variable, load_config_data_from_appdata


# Fields we care about from raw API (used to validate pipeline output)
FILE_FIELDS = ['id', 'display_name', 'filename', 'mime_class', 'content-type', 'url', 'size']
MEDIA_FIELDS = ['media_id', 'title', 'media_type', 'media_sources']


def extract_relevant_fields(raw: dict, fields: list) -> dict:
    """Extract only the fields we need for comparison."""
    return {k: raw.get(k) for k in fields if k in raw}


class PipelineTestCollector:
    """Collects minimal raw API data for pipeline validation."""

    def __init__(self):
        self.ensure_credentials()

    def ensure_credentials(self):
        """Ensure API credentials are loaded."""
        set_canvas_api_key_to_environment_variable()
        load_config_data_from_appdata()

    def collect_from_course(self, course_id: str) -> Dict[str, Any]:
        """
        Collect minimal raw API data from a course.
        Only stores fields needed for pipeline validation.
        """
        print(f"Collecting from course {course_id}...")

        corpus = {
            "course_id": course_id,
            "collected_at": datetime.now().isoformat(),
            "course_name": None,
            "files": [],      # Minimal file data
            "media": [],      # Minimal media data
            "summary": {
                "total_files": 0,
                "total_media": 0,
                "by_mime_class": {}
            }
        }

        # Get course info
        course_info = get_course(course_id)
        if course_info:
            corpus["course_name"] = course_info.get("name")
        else:
            print(f"  Warning: Could not access course {course_id}")
            return corpus

        # Collect files - only relevant fields
        print(f"  Collecting files...")
        files = get_files(course_id)
        if files:
            for f in files:
                corpus["files"].append(extract_relevant_fields(f, FILE_FIELDS))
                mime = f.get("mime_class", "unknown")
                corpus["summary"]["by_mime_class"][mime] = corpus["summary"]["by_mime_class"].get(mime, 0) + 1

            corpus["summary"]["total_files"] = len(files)
            print(f"    Found {len(files)} files")

        # Collect media objects - only relevant fields
        print(f"  Collecting media objects...")
        media = get_media_objects(course_id)
        if media:
            for m in media:
                extracted = extract_relevant_fields(m, MEDIA_FIELDS)
                # Simplify media_sources to just URLs
                if m.get("media_sources"):
                    extracted["source_urls"] = [s.get("url") for s in m["media_sources"]]
                    del extracted["media_sources"]
                corpus["media"].append(extracted)

            corpus["summary"]["total_media"] = len(media)
            print(f"    Found {len(media)} media objects")

        return corpus

    def collect_from_courses(self, course_ids: List[str], output_dir: str) -> Dict[str, Any]:
        """Collect data from multiple courses."""
        os.makedirs(output_dir, exist_ok=True)

        summary = {
            "collected_at": datetime.now().isoformat(),
            "courses_requested": len(course_ids),
            "courses_successful": 0,
            "courses_failed": [],
            "totals": {"files": 0, "media": 0},
            "by_mime_class": {}
        }

        for course_id in course_ids:
            try:
                corpus = self.collect_from_course(course_id)

                if corpus["course_name"]:
                    output_path = os.path.join(output_dir, f"raw_{course_id}.json")
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(corpus, f, indent=2, default=str)

                    summary["courses_successful"] += 1
                    summary["totals"]["files"] += corpus["summary"]["total_files"]
                    summary["totals"]["media"] += corpus["summary"]["total_media"]

                    for mime, count in corpus["summary"]["by_mime_class"].items():
                        summary["by_mime_class"][mime] = summary["by_mime_class"].get(mime, 0) + count

                    print(f"  Saved to {output_path}")
                else:
                    summary["courses_failed"].append(course_id)

            except Exception as e:
                print(f"  Error: {e}")
                summary["courses_failed"].append(course_id)

        # Save summary
        summary_path = os.path.join(output_dir, "_raw_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        return summary

    def collect_from_range(self, start_id: int, end_id: int, output_dir: str) -> Dict[str, Any]:
        """Collect from a range of course IDs."""
        course_ids = [str(i) for i in range(start_id, end_id + 1)]
        return self.collect_from_courses(course_ids, output_dir)

    def collect_from_file(self, course_list_file: str, output_dir: str) -> Dict[str, Any]:
        """Collect from courses listed in a file."""
        with open(course_list_file, 'r') as f:
            course_ids = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return self.collect_from_courses(course_ids, output_dir)


def print_summary(summary: Dict[str, Any]):
    """Pretty print collection summary."""
    print("\n" + "=" * 50)
    print("RAW DATA COLLECTION SUMMARY")
    print("=" * 50)
    print(f"Courses: {summary['courses_successful']}/{summary['courses_requested']}")
    print(f"Files: {summary['totals']['files']}")
    print(f"Media: {summary['totals']['media']}")

    if summary['by_mime_class']:
        print("\nBy MIME class:")
        for mime, count in sorted(summary['by_mime_class'].items(), key=lambda x: -x[1])[:10]:
            print(f"  {mime}: {count}")
    print("=" * 50)

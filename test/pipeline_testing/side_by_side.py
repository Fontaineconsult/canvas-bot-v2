"""
Side-by-side comparison of raw API data vs processed output.
Shows exactly what goes in and what comes out.
"""

import json
import os
from typing import Dict, List, Any


def load_json(path: str) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_raw_files(raw_data: Dict) -> List[Dict]:
    """Extract files from raw collector format."""
    files = []
    for entry in raw_data.get("files", []):
        if "raw" in entry:
            files.append(entry["raw"])
        else:
            files.append(entry)
    return files


def extract_processed_documents(processed_data: Dict) -> List[Dict]:
    """Extract documents from --output_as_json format."""
    docs = []
    content = processed_data.get("content", {})
    documents = content.get("documents", {})
    docs.extend(documents.get("documents", []))
    return docs


def build_comparison_table(raw_file: str, processed_file: str) -> List[Dict]:
    """Build side-by-side comparison."""
    raw_data = load_json(raw_file)
    processed_data = load_json(processed_file)

    raw_files = extract_raw_files(raw_data)
    processed_docs = extract_processed_documents(processed_data)

    # Build lookup by file ID from URL
    processed_by_id = {}
    for doc in processed_docs:
        url = doc.get("url", "")
        # Extract file ID from URL like /files/12345/
        import re
        match = re.search(r'/files/(\d+)/', url)
        if match:
            processed_by_id[int(match.group(1))] = doc

    # Build comparison rows
    comparison = []
    for raw in raw_files:
        file_id = raw.get("id")
        processed = processed_by_id.get(file_id, {})

        row = {
            "file_id": file_id,
            "raw": {
                "display_name": raw.get("display_name"),
                "filename": raw.get("filename"),
                "mime_class": raw.get("mime_class"),
            },
            "processed": {
                "title": processed.get("title"),
                "file_type": processed.get("file_type"),
                "path_first": processed.get("path", [None])[0] if processed.get("path") else None,
            },
            "issues": []
        }

        # Check for issues
        if raw.get("display_name") != processed.get("title"):
            if raw.get("filename") == processed.get("title"):
                row["issues"].append("title=filename (not display_name)")

        if processed.get("title") and "+" in processed.get("title", ""):
            row["issues"].append("URL encoding not decoded")

        comparison.append(row)

    return comparison


def print_comparison_table(raw_file: str, processed_file: str):
    """Print formatted comparison table."""
    comparison = build_comparison_table(raw_file, processed_file)

    print("\n" + "=" * 100)
    print("SIDE-BY-SIDE COMPARISON: Raw API vs Processed Output")
    print("=" * 100)
    print(f"Raw data: {raw_file}")
    print(f"Processed: {processed_file}")
    print("-" * 100)

    # Header
    print(f"{'ID':<10} {'RAW display_name':<40} {'PROCESSED title':<40} {'Issues':<20}")
    print("-" * 100)

    for row in comparison:
        raw_name = (row["raw"]["display_name"] or "")[:38]
        proc_title = (row["processed"]["title"] or "(not found)")[:38]
        issues = ", ".join(row["issues"])[:18] if row["issues"] else "OK"

        print(f"{row['file_id']:<10} {raw_name:<40} {proc_title:<40} {issues:<20}")

    print("-" * 100)

    # Summary
    with_issues = sum(1 for r in comparison if r["issues"])
    print(f"\nTotal: {len(comparison)} files, {with_issues} with issues ({with_issues*100//max(len(comparison),1)}%)")

    print("\n" + "=" * 100)


def print_detailed_comparison(raw_file: str, processed_file: str, limit: int = 5):
    """Print detailed comparison for first N items."""
    comparison = build_comparison_table(raw_file, processed_file)

    print("\n" + "=" * 80)
    print("DETAILED COMPARISON (first {} items)".format(limit))
    print("=" * 80)

    for i, row in enumerate(comparison[:limit]):
        print(f"\n--- File {i+1}: ID {row['file_id']} ---")
        print(f"RAW API:")
        print(f"  display_name: {row['raw']['display_name']}")
        print(f"  filename:     {row['raw']['filename']}")
        print(f"  mime_class:   {row['raw']['mime_class']}")
        print(f"PROCESSED OUTPUT:")
        print(f"  title:        {row['processed']['title']}")
        print(f"  file_type:    {row['processed']['file_type']}")
        print(f"  path[0]:      {row['processed']['path_first']}")
        if row["issues"]:
            print(f"ISSUES:")
            for issue in row["issues"]:
                print(f"  - {issue}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        print_comparison_table(sys.argv[1], sys.argv[2])
        print_detailed_comparison(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python side_by_side.py <raw_file> <processed_file>")

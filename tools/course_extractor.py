"""
Course ID Extractor

Extracts course information from Canvas LMS and exports to CSV.
Can be used standalone or integrated with canvas_bot CLI.
"""

import csv
import time
import os
from datetime import datetime


def get_semester_key():
    """
    Returns a mapping of Canvas semester codes to readable semester names.
    This can be customized per institution or loaded from config.

    Format: Canvas term code -> short semester name
    """
    # Default semester mappings - can be extended
    return {
        # 2023-2024
        "2237": "fa23",
        "2243": "sp24",
        "2245": "su24",
        # 2024-2025
        "2247": "fa24",
        "2253": "sp25",
        "2255": "su25",
        "2257": "fa25",
        # 2025-2026
        "2263": "sp26",
        "2265": "su26",
        "2267": "fa26",
    }


def parse_course_code(course_code, semester_key):
    """
    Parse a Canvas course code into its components.

    Expected format: TERM-DEPT-NUMBER-SECTION-CAMPUS-CRN
    Examples:
        '2237-CHEM-180-A1-1-3347'
        '2237-AA S-898-03-1-1030'  (dept has space)
        '2237-E ED-747-01-1-4873'  (dept has space)

    Returns dict with parsed components or None if parsing fails.
    """
    try:
        parts = course_code.split("-")
        if len(parts) >= 4:
            term_code = parts[0]
            semester = semester_key.get(term_code)

            if semester:
                # Department is parts[1], but may have spaces
                # Course number is parts[2]
                # Section is parts[3]
                # Parts[4] and [5] are campus and CRN (optional)
                department = parts[1]
                course_number = parts[2]
                section = parts[3]

                # Handle optional campus and CRN
                campus = parts[4] if len(parts) > 4 else ""
                crn = parts[5] if len(parts) > 5 else ""

                return {
                    "term_code": term_code,
                    "semester": semester,
                    "department": department,
                    "course_number": course_number,
                    "section": section,
                    "campus": campus,
                    "crn": crn,
                }
    except (IndexError, AttributeError):
        pass

    return None


def generate_course_id(parsed_code):
    """
    Generate a unique course identifier from parsed course code.

    Format: {semester}{dept}{number}{section} (e.g., "fa24BIOL10001")
    Spaces are removed from department names (e.g., "AA S" -> "AAS")
    """
    if parsed_code:
        # Remove spaces from department
        dept_clean = parsed_code["department"].replace(" ", "")
        course_id = f"{parsed_code['semester']}{dept_clean}{parsed_code['course_number']}{parsed_code['section']}"
        return course_id.replace(" ", "")
    return None


def extract_courses(output_path, semester_filter=None, include_all=False, delay=0.3):
    """
    Extract all courses from Canvas and save to CSV.

    Args:
        output_path: Path to save the CSV file
        semester_filter: Optional semester code to filter by (e.g., "fa24")
        include_all: If True, include courses that don't match semester pattern
        delay: Delay between API calls in seconds (to avoid rate limiting)

    Returns:
        dict with extraction statistics
    """
    from network.api import get_active_accounts

    semester_key = get_semester_key()

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    stats = {
        "total_fetched": 0,
        "total_written": 0,
        "skipped_no_match": 0,
        "skipped_filter": 0,
        "errors": 0,
    }

    print()
    print("=" * 60)
    print("Canvas Course Extractor")
    print("=" * 60)
    print(f"  Output file:     {output_path}")
    if semester_filter:
        print(f"  Semester filter: {semester_filter}")
    else:
        print(f"  Semester filter: (none - all semesters)")
    print("=" * 60)
    print()
    print("Fetching courses from Canvas API...")
    print()

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)

        # Write header
        writer.writerow([
            "generated_id",
            "canvas_id",
            "semester",
            "department",
            "course_number",
            "section",
            "crn",
            "course_name",
            "course_code",
        ])

        page = 1
        last_semester = None

        while True:
            print(f"\r  Fetching page {page}...", end="", flush=True)
            courses = get_active_accounts(page)

            if not courses or len(courses) == 0:
                print(f"\r  Fetching page {page}... no more courses found.")
                break

            print(f"\r  Fetching page {page}... got {len(courses)} courses", flush=True)
            stats["total_fetched"] += len(courses)

            for course in courses:
                try:
                    course_code = course.get("course_code", "")
                    course_name = course.get("name", "")
                    canvas_id = course.get("id", "")

                    parsed = parse_course_code(course_code, semester_key)

                    if parsed:
                        # Apply semester filter if specified
                        if semester_filter and parsed["semester"] != semester_filter:
                            stats["skipped_filter"] += 1
                            continue

                        generated_id = generate_course_id(parsed)

                        # Print semester header when it changes
                        if parsed["semester"] != last_semester:
                            print()
                            print(f"  --- {parsed['semester'].upper()} ---")
                            last_semester = parsed["semester"]

                        writer.writerow([
                            generated_id,
                            canvas_id,
                            parsed["semester"],
                            parsed["department"],
                            parsed["course_number"],
                            parsed["section"],
                            parsed.get("crn", ""),
                            course_name,
                            course_code,
                        ])
                        stats["total_written"] += 1

                        # Truncate long course names for display
                        display_name = course_name[:45] + "..." if len(course_name) > 45 else course_name
                        print(f"  [+] {generated_id:<20} | {canvas_id:<6} | {display_name}")

                    elif include_all:
                        # Write courses that don't match pattern
                        writer.writerow([
                            "",  # no generated_id
                            canvas_id,
                            "",  # no semester
                            "",  # no department
                            "",  # no course_number
                            "",  # no section
                            "",  # no crn
                            course_name,
                            course_code,
                        ])
                        stats["total_written"] += 1
                        print(f"  [?] (no pattern match) | {canvas_id:<6} | {course_name[:45]}")
                    else:
                        stats["skipped_no_match"] += 1

                except Exception as e:
                    stats["errors"] += 1
                    print(f"  [ERROR] Failed to process course {canvas_id}: {e}")

            page += 1
            time.sleep(delay)

    # Print summary
    print()
    print()
    print("=" * 60)
    print("Extraction Complete")
    print("=" * 60)
    print()
    print(f"  Total courses fetched:    {stats['total_fetched']:,}")
    print(f"  Courses written to CSV:   {stats['total_written']:,}")
    print()
    if stats['skipped_no_match'] > 0:
        print(f"  Skipped (no pattern):     {stats['skipped_no_match']:,}")
    if stats['skipped_filter'] > 0:
        print(f"  Skipped (filtered out):   {stats['skipped_filter']:,}")
    if stats['errors'] > 0:
        print(f"  Errors:                   {stats['errors']:,}")
    print()
    print(f"  Output saved to: {output_path}")
    print()
    print("=" * 60)

    return stats


def extract_courses_cli(output_path=None, semester=None):
    """
    CLI wrapper for extract_courses with sensible defaults.
    """
    if output_path is None:
        # Default to current directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"canvas_courses_{timestamp}.csv"

    return extract_courses(
        output_path=output_path,
        semester_filter=semester,
        include_all=False,
        delay=0.3,
    )


if __name__ == "__main__":
    # Standalone usage
    from network.cred import set_canvas_api_key_to_environment_variable, load_config_data_from_appdata

    set_canvas_api_key_to_environment_variable()
    load_config_data_from_appdata()

    # Example: extract all courses
    extract_courses_cli()

    # Example: extract only Fall 2024 courses
    # extract_courses_cli(output_path="fa24_courses.csv", semester="fa24")
def validate_course_id(course_id):
    """Validate a single course ID is numeric. Returns error message or None."""
    if not course_id.strip().isdigit():
        return f"Invalid course ID '{course_id}' — must be numeric."
    return None


def validate_course_list(course_ids):
    """
    Validate a list of course IDs. Returns (valid_ids, warnings).
    Filters out blank and non-numeric entries.
    """
    valid = []
    warnings = []
    for i, cid in enumerate(course_ids, 1):
        stripped = cid.strip()
        if not stripped:
            continue
        if not stripped.isdigit():
            warnings.append(f"Skipping invalid course ID '{stripped}' at position {i} (must be numeric)")
            continue
        valid.append(stripped)
    return valid, warnings

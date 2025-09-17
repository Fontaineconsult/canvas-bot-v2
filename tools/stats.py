from canvas_bot import CanvasBot

from collections import defaultdict

import json
from collections import defaultdict

def count_course_content(id_range_x, id_range_y, write_out: str = None) -> dict:
    """
    Loops over course IDs, aggregates content counts, and optionally
    writes a checkpoint to `write_out` after each course.
    """
    running = {
        "total_courses_counted": 0,
        "content_counts": defaultdict(lambda: defaultdict(int)),
        "last_course_id": "0"
    }

    for course_id in range(id_range_x, id_range_y):
        bot = CanvasBot(str(course_id))
        bot.start()
        single = bot.count_content()  # e.g. {'documents': {'pdf': 22}, 'videos': {'video_sites': 21}}
        print(f"[{course_id}] got:", single)

        # 1) bump course count
        running["total_courses_counted"] += 1

        # 2) merge single into running totals
        for category, types in single.items():
            for content_type, cnt in types.items():
                running["content_counts"][category][content_type] += cnt

        bot.print_content_tree()

        # 3) checkpoint to disk if requested
        if write_out:
            # turn nested defaultdicts into regular dicts
            plain = {
                "total_courses_counted": running["total_courses_counted"],
                "last_course_id": str(course_id),
                "content_counts": {
                    cat: dict(types)
                    for cat, types in running["content_counts"].items()
                }
            }
            with open(write_out, 'w') as f:
                json.dump(plain, f, indent=2)

    # final return in plain dict form
    return {
        "total_courses_counted": running["total_courses_counted"],

        "content_counts": {
            cat: dict(types)
            for cat, types in running["content_counts"].items()
        }
    }

# example usage:
# count_course_content(47300, 63000, write_out="canvas_content_checkpoint.txt")

if __name__ == "__main__":


    print(count_course_content(50428, 63000, write_out=r"C:\Users\913678186\AppData\Roaming\JetBrains\IntelliJIdea2025.1\scratches\canvas_content_checkpoint.txt"))
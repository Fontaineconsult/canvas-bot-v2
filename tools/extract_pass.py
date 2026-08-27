"""
CLI for the OCR extraction post-pass.

Usage::

    python -m tools.extract_pass --course-folder ./downloads/123456 \
        --endpoint http://127.0.0.1:8077 [--excel ./downloads/123456/123456.xlsx]

Requires a completed scan: downloaded files plus the course JSON export in
the folder. Updates the Excel report's "Requires OCR" column when a report
is present (found automatically unless --excel is given).
"""

from __future__ import annotations

import os
import sys
from glob import glob

import click

from core.text_extraction import ExtractionClient, ExtractionPass, update_excel_requires_ocr


@click.command()
@click.option("--course-folder", required=True, type=click.Path(exists=True, file_okay=False))
@click.option("--endpoint", required=True, help="DocAble service URL")
@click.option("--excel", type=click.Path(exists=True, dir_okay=False),
              help="Excel report to update (default: auto-discover in course folder)")
def main(course_folder: str, endpoint: str, excel: str | None) -> None:
    results = ExtractionPass(ExtractionClient(endpoint), course_folder).run()

    ok = {u: v for u, v in results.items() if "error" not in v}
    flagged = [u for u, v in ok.items() if v.get("requires_ocr")]
    errors = {u: v["error"] for u, v in results.items() if "error" in v}

    click.echo(f"Extracted {len(ok)}/{len(results)} documents")
    click.echo(f"Requires OCR: {len(flagged)}")
    for url in flagged:
        click.echo(f"  YES  {url}  ({ok[url]['classification']}, "
                   f"pages {ok[url]['scanned_pages']})")
    for url, err in errors.items():
        click.echo(f"  SKIP {url}  ({err})")

    if not excel:
        candidates = glob(os.path.join(course_folder, "*.xlsx")) + \
                     glob(os.path.join(course_folder, "*.xlsm"))
        excel = candidates[0] if candidates else None
    if excel:
        updated = update_excel_requires_ocr(excel, results)
        click.echo(f"Excel: set {updated} 'Requires OCR' cell(s) in {excel}")
    else:
        click.echo("Excel: no report found in folder; skipped")

    sys.exit(1 if errors and not ok else 0)


if __name__ == "__main__":
    main()

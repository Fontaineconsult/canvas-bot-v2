"""
CLI interface for pipeline testing tools.

Usage:
    # Step 1: Collect raw API data
    python -m test.pipeline_testing collect --course_id 12345 --output ./test_data

    # Step 2: Run canvas_bot with --output_as_json on same course
    python canvas_bot.py --course_id 12345 --output_as_json ./test_data

    # Step 3: Compare raw vs processed
    python -m test.pipeline_testing compare --raw ./test_data/raw_12345.json --processed ./test_data/12345.json
"""

import click
import os
import json

from test.pipeline_testing.collector import PipelineTestCollector, print_summary
from test.pipeline_testing.comparator import PipelineComparator
from test.pipeline_testing.direct_tester import DirectPipelineTester
from test.pipeline_testing.side_by_side import print_comparison_table, print_detailed_comparison
from test.pipeline_testing.batch_collector import BatchCollector, print_corpus_summary
from test.pipeline_testing.batch_tester import BatchTester


@click.group()
def cli():
    """Pipeline testing CLI for canvas-bot."""
    pass


@cli.command()
@click.option('--course_id', type=str, help='Single course ID to collect')
@click.option('--range', 'course_range', type=str, help='Range of course IDs (e.g., 12345-12400)')
@click.option('--file', 'course_file', type=click.Path(exists=True), help='File containing course IDs')
@click.option('--output', '-o', required=True, type=click.Path(), help='Output directory')
def collect(course_id, course_range, course_file, output):
    """Collect raw API data from Canvas courses."""

    if not any([course_id, course_range, course_file]):
        raise click.UsageError("Must specify one of: --course_id, --range, or --file")

    collector = PipelineTestCollector()

    if course_id:
        click.echo(f"Collecting raw data from course {course_id}...")
        corpus = collector.collect_from_course(course_id)

        os.makedirs(output, exist_ok=True)
        output_path = os.path.join(output, f"raw_{course_id}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(corpus, f, indent=2, default=str)

        click.echo(f"\nSaved to {output_path}")
        click.echo(f"Files: {corpus['summary']['total_files']}")
        click.echo(f"Media: {corpus['summary']['total_media']}")

    elif course_range:
        try:
            start, end = course_range.split('-')
            start_id = int(start.strip())
            end_id = int(end.strip())
        except ValueError:
            raise click.UsageError("Range must be in format: START-END (e.g., 12345-12400)")

        click.echo(f"Collecting from courses {start_id} to {end_id}...")
        summary = collector.collect_from_range(start_id, end_id, output)
        print_summary(summary)

    elif course_file:
        click.echo(f"Collecting from courses in {course_file}...")
        summary = collector.collect_from_file(course_file, output)
        print_summary(summary)


@cli.command()
@click.option('--raw', '-r', required=True, type=click.Path(exists=True),
              help='Raw API data file (raw_COURSEID.json from collect)')
@click.option('--processed', '-p', required=True, type=click.Path(exists=True),
              help='Processed output file (from --output_as_json)')
@click.option('--output', '-o', type=click.Path(), help='Save report to JSON file')
def compare(raw, processed, output):
    """Compare raw API data with pipeline output."""

    comparator = PipelineComparator()
    click.echo(f"Comparing {raw} vs {processed}...")

    comparator.compare(raw, processed)
    comparator.print_report()

    if output:
        comparator.save_report(output)


@cli.command()
@click.option('--data_dir', '-d', required=True, type=click.Path(exists=True),
              help='Directory containing raw and processed files')
def compare_all(data_dir):
    """Compare all raw/processed pairs in a directory."""

    # Find all raw_*.json files
    raw_files = [f for f in os.listdir(data_dir) if f.startswith('raw_') and f.endswith('.json')]

    if not raw_files:
        click.echo("No raw data files found.")
        return

    all_issues = {}
    total_compared = 0
    total_with_issues = 0

    for raw_file in raw_files:
        course_id = raw_file.replace('raw_', '').replace('.json', '')
        raw_path = os.path.join(data_dir, raw_file)

        # Look for corresponding processed file
        processed_candidates = [
            f"{course_id}.json",
            f"course_{course_id}.json",
        ]

        processed_path = None
        for candidate in processed_candidates:
            path = os.path.join(data_dir, candidate)
            if os.path.exists(path):
                processed_path = path
                break

        if not processed_path:
            click.echo(f"  Skipping {course_id}: no processed file found")
            continue

        click.echo(f"\nComparing course {course_id}...")
        comparator = PipelineComparator()
        comparator.compare(raw_path, processed_path)

        total_compared += len(comparator.results)
        total_with_issues += len(comparator.get_items_with_issues())

        for issue_type, count in comparator.get_issues_summary().items():
            all_issues[issue_type] = all_issues.get(issue_type, 0) + count

    # Print overall summary
    click.echo("\n" + "=" * 70)
    click.echo("OVERALL COMPARISON SUMMARY")
    click.echo("=" * 70)
    click.echo(f"Courses compared: {len(raw_files)}")
    click.echo(f"Total items: {total_compared}")
    click.echo(f"Items with issues: {total_with_issues}")

    if all_issues:
        click.echo("\nAll issues by type:")
        for issue_type, count in sorted(all_issues.items(), key=lambda x: -x[1]):
            click.echo(f"  {issue_type}: {count}")


@cli.command()
@click.option('--data_dir', '-d', required=True, type=click.Path(exists=True),
              help='Directory containing collected data')
def summary(data_dir):
    """Show summary of collected test data."""

    raw_files = [f for f in os.listdir(data_dir) if f.startswith('raw_') and f.endswith('.json')]

    if not raw_files:
        click.echo("No raw data files found.")
        return

    totals = {"courses": len(raw_files), "files": 0, "media": 0, "by_mime_class": {}}

    for raw_file in raw_files:
        path = os.path.join(data_dir, raw_file)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        totals["files"] += data["summary"]["total_files"]
        totals["media"] += data["summary"]["total_media"]

        for mime, count in data["summary"].get("by_mime_class", {}).items():
            totals["by_mime_class"][mime] = totals["by_mime_class"].get(mime, 0) + count

    click.echo("\n" + "=" * 50)
    click.echo("RAW TEST DATA SUMMARY")
    click.echo("=" * 50)
    click.echo(f"Courses: {totals['courses']}")
    click.echo(f"Total files: {totals['files']}")
    click.echo(f"Total media: {totals['media']}")

    if totals['by_mime_class']:
        click.echo("\nBy MIME class:")
        for mime, count in sorted(totals['by_mime_class'].items(), key=lambda x: -x[1]):
            click.echo(f"  {mime}: {count}")
    click.echo("=" * 50)


@cli.command()
@click.option('--data_dir', '-d', required=True, type=click.Path(exists=True),
              help='Directory containing raw data')
@click.option('--limit', '-n', default=5, type=int, help='Number of samples to show')
def samples(data_dir, limit):
    """Show sample entries from collected raw data."""

    raw_files = [f for f in os.listdir(data_dir) if f.startswith('raw_') and f.endswith('.json')]

    if not raw_files:
        click.echo("No raw data files found.")
        return

    path = os.path.join(data_dir, raw_files[0])
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    click.echo(f"\nSamples from {raw_files[0]}:")
    click.echo("-" * 60)

    if data["files"]:
        click.echo(f"\nFILES (showing {min(limit, len(data['files']))} of {len(data['files'])}):")
        for entry in data["files"][:limit]:
            click.echo(f"  ID: {entry.get('id')}")
            click.echo(f"    display_name: {entry.get('display_name')}")
            click.echo(f"    filename: {entry.get('filename')}")
            click.echo(f"    mime_class: {entry.get('mime_class')}")
            click.echo("")


@cli.command()
@click.option('--raw', '-r', required=True, type=click.Path(exists=True),
              help='Raw API data file (from collector)')
@click.option('--processed', '-p', required=True, type=click.Path(exists=True),
              help='Processed output file (from --output_as_json)')
@click.option('--detailed', '-d', default=5, type=int, help='Number of detailed examples to show')
def side_by_side(raw, processed, detailed):
    """Show side-by-side comparison of raw vs processed data."""
    print_comparison_table(raw, processed)
    if detailed > 0:
        print_detailed_comparison(raw, processed, detailed)


@cli.command()
@click.option('--raw', '-r', required=True, type=click.Path(exists=True),
              help='Raw API data file to test')
@click.option('--output', '-o', type=click.Path(), help='Save report to JSON file')
def test(raw, output):
    """Test pipeline functions directly against raw API data."""

    tester = DirectPipelineTester()
    click.echo(f"Testing pipeline against {raw}...")

    tester.test_raw_file(raw)
    tester.print_report()

    if output:
        tester.save_report(output)


@cli.command()
@click.option('--data_dir', '-d', required=True, type=click.Path(exists=True),
              help='Directory containing raw data files')
@click.option('--output', '-o', type=click.Path(), help='Save combined report to JSON')
def test_all(data_dir, output):
    """Test pipeline against all raw data files in a directory."""

    # Find raw data files (both formats: raw_*.json and course_*.json)
    import os
    files = [f for f in os.listdir(data_dir)
             if f.endswith('.json') and not f.startswith('_')]

    if not files:
        click.echo("No data files found.")
        return

    all_results = []
    all_issues = {}
    total_tested = 0
    total_with_issues = 0

    for filename in files:
        path = os.path.join(data_dir, filename)
        click.echo(f"\nTesting {filename}...")

        tester = DirectPipelineTester()
        tester.test_raw_file(path)

        total_tested += len(tester.results)
        total_with_issues += len(tester.get_items_with_issues())

        for issue_type, count in tester.get_issues_summary().items():
            all_issues[issue_type] = all_issues.get(issue_type, 0) + count

        # Show per-file summary
        issues = tester.get_items_with_issues()
        click.echo(f"  Files: {len(tester.results)}, Issues: {len(issues)}")

    # Print overall summary
    click.echo("\n" + "=" * 70)
    click.echo("OVERALL TEST SUMMARY")
    click.echo("=" * 70)
    click.echo(f"Files processed: {len(files)}")
    click.echo(f"Total items tested: {total_tested}")
    click.echo(f"Items with issues: {total_with_issues} ({total_with_issues*100//max(total_tested,1)}%)")

    if all_issues:
        click.echo("\nAll issues by type:")
        for issue_type, count in sorted(all_issues.items(), key=lambda x: -x[1]):
            click.echo(f"  {issue_type}: {count}")

    click.echo("=" * 70)


@cli.command()
@click.option('--file', 'course_file', type=click.Path(exists=True), help='File with course IDs (one per line)')
@click.option('--range', 'course_range', type=str, help='Range of course IDs (e.g., 30000-30100)')
@click.option('--output', '-o', required=True, type=click.Path(), help='Output corpus file (JSON)')
@click.option('--delay', '-d', default=0.5, type=float, help='Delay between API calls (seconds)')
def batch_collect(course_file, course_range, output, delay):
    """
    Collect minimal test data from many courses.
    Only fetches files API - minimal API usage.

    Example:
        python -m test.pipeline_testing batch-collect --range 30000-30100 --output corpus.json
    """
    if not course_file and not course_range:
        raise click.UsageError("Must specify --file or --range")

    collector = BatchCollector(delay=delay)

    if course_file:
        click.echo(f"Collecting from courses in {course_file}...")
        corpus = collector.collect_from_file(course_file, output)
    else:
        start, end = course_range.split('-')
        start_id, end_id = int(start.strip()), int(end.strip())
        click.echo(f"Collecting from courses {start_id} to {end_id}...")
        corpus = collector.collect_from_range(start_id, end_id, output)

    print_corpus_summary(corpus)
    click.echo(f"\nCorpus saved to {output}")


@cli.command()
@click.option('--corpus', '-c', required=True, type=click.Path(exists=True), help='Corpus file from batch-collect')
@click.option('--output', '-o', type=click.Path(), help='Save detailed report to JSON')
def batch_test(corpus, output):
    """
    Test pipeline against collected corpus.
    No API calls - runs entirely offline.

    Example:
        python -m test.pipeline_testing batch-test --corpus corpus.json
    """
    tester = BatchTester()
    click.echo(f"Testing corpus: {corpus}\n")

    tester.test_corpus(corpus)
    tester.print_report()

    if output:
        tester.save_report(output)


if __name__ == '__main__':
    cli()

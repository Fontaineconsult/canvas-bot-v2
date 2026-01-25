"""
Entry point for running pipeline testing as a module.

Workflow:
    # Step 1: Collect raw API data
    python -m test.pipeline_testing collect --course_id 12345 --output ./test_data

    # Step 2: Run canvas_bot with --output_as_json on same course
    python canvas_bot.py --course_id 12345 --output_as_json ./test_data

    # Step 3: Compare raw vs processed
    python -m test.pipeline_testing compare --raw ./test_data/raw_12345.json --processed ./test_data/12345.json

    # Or compare all pairs in a directory
    python -m test.pipeline_testing compare-all --data_dir ./test_data
"""

from test.pipeline_testing.cli import cli

if __name__ == '__main__':
    cli()

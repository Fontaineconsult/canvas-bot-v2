"""
Web console tests. The scan pipeline is injected and faked — these prove
the HTTP layer: job lifecycle, credential hygiene, dashboard rendering.
"""
import json
import time

import pytest
from fastapi.testclient import TestClient

from webui.app import create_app


def fake_pipeline(params, job):
    job.update(stage="scanning")
    if params["course_id"] == "boom":
        raise RuntimeError("course does not exist")
    folder = params["work_root"] / params["course_id"]
    (folder / ".manifest").mkdir(parents=True)
    (folder / f"{params['course_id']}.json").write_text(json.dumps({
        "course_id": params["course_id"], "course_name": "Fake 101",
        "content": {"documents": {"documents": [
            {"title": "Doc A", "url": "https://x/files/1", "save_path": "a.pdf"},
        ], "document_sites": []}},
    }))
    (folder / ".manifest" / "extraction_results.json").write_text(json.dumps({
        "https://x/files/1": {"requires_ocr": True, "classification": "scanned",
                              "scanned_pages": [1], "scanned_page_count": 1,
                              "report_url": "/audits/a-12345678/report.html"},
    }))
    (folder / "999.xlsx").write_bytes(b"PK\x03\x04excel")
    job.update(stage="done", course_folder=str(folder))


@pytest.fixture()
def client(tmp_path):
    app = create_app(pipeline=fake_pipeline, work_root=tmp_path)
    return TestClient(app)


def _start_and_wait(client, course_id="999"):
    r = client.post("/audit", data={
        "canvas_domain": "myschool", "course_id": course_id,
        "api_token": "sekret-token-value", "extract_endpoint": "http://127.0.0.1:8077",
    })
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    for _ in range(50):
        state = client.get(f"/jobs/{job_id}").json()
        if state["stage"] in ("done", "error"):
            return job_id, state
        time.sleep(0.05)
    raise AssertionError("job never finished")


class TestConsole:
    def test_console_page_renders(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "Course audit" in r.text and "<main" in r.text

    def test_job_lifecycle_reaches_done(self, client):
        _, state = _start_and_wait(client)
        assert state["stage"] == "done"

    def test_failed_scan_reports_error_stage(self, client):
        _, state = _start_and_wait(client, course_id="boom")
        assert state["stage"] == "error"
        assert "course does not exist" in state["error"]

    def test_token_never_appears_in_job_state_or_pages(self, client):
        job_id, state = _start_and_wait(client)
        assert "sekret-token-value" not in json.dumps(state)
        assert "sekret-token-value" not in client.get("/").text
        assert "sekret-token-value" not in client.get(f"/jobs/{job_id}").text


class TestDashboard:
    def test_dashboard_lists_documents_with_verdicts(self, client):
        _start_and_wait(client)
        r = client.get("/course/999")
        assert r.status_code == 200
        assert "Doc A" in r.text
        assert "scanned" in r.text.lower()

    def test_dashboard_links_interactive_review(self, client):
        _start_and_wait(client)
        # Details points at the review-and-edit page, derived from the
        # audit folder in report_url
        assert "/?audit=a-12345678" in client.get("/course/999").text

    def test_excel_download_served(self, client):
        _start_and_wait(client)
        r = client.get("/course/999/excel")
        assert r.status_code == 200
        assert r.content.startswith(b"PK")

    def test_unknown_course_404s(self, client):
        assert client.get("/course/nope").status_code == 404

    def test_course_id_path_is_guarded(self, client):
        assert client.get("/course/../../etc").status_code in (404, 422)


class TestSecurityHardening:
    def test_hostile_canvas_domain_rejected(self, client):
        r = client.post("/audit", data={
            "canvas_domain": "attacker.example?x=", "course_id": "1",
            "api_token": "t", "extract_endpoint": "http://127.0.0.1:8077"})
        assert r.status_code == 422

    def test_traversal_course_id_rejected_before_any_mkdir(self, client, tmp_path):
        r = client.post("/audit", data={
            "canvas_domain": "myschool", "course_id": "../../etc",
            "api_token": "t", "extract_endpoint": "http://127.0.0.1:8077"})
        assert r.status_code == 422

    def test_token_scrubbed_from_error_state(self, tmp_path):
        def leaky_pipeline(params, job):
            raise RuntimeError(
                "ConnectionError: https://x/api?access_token=sekret-token-value&page=1")
        app = create_app(pipeline=leaky_pipeline, work_root=tmp_path)
        c = TestClient(app)
        job_id, state = None, None
        r = c.post("/audit", data={
            "canvas_domain": "myschool", "course_id": "1",
            "api_token": "sekret-token-value", "extract_endpoint": "http://x"})
        job_id = r.json()["job_id"]
        for _ in range(50):
            state = c.get(f"/jobs/{job_id}").json()
            if state["stage"] == "error":
                break
            time.sleep(0.05)
        assert state["stage"] == "error"
        assert "sekret-token-value" not in json.dumps(state)
        assert "access_token=***" in state["error"]

    def test_cross_origin_post_rejected(self, client):
        r = client.post("/audit", headers={"Origin": "https://evil.example"}, data={
            "canvas_domain": "myschool", "course_id": "1",
            "api_token": "t", "extract_endpoint": "http://127.0.0.1:8077"})
        assert r.status_code == 403

"""
Canvas Bot Web Console
======================

Browser front-end for the whole audit pipeline. Instructors and auditors
need nothing installed — the scan engine, extraction pass, and report
generation all run server-side, on any OS Canvas Bot's core runs on.

Flow
----
POST /audit starts a background job::

    configure Canvas creds (memory only) -> initialize_course()
    -> download_files() -> save_content_as_json() -> save_content_as_excel()
    -> ExtractionPass (doc-extract service) -> Excel Requires-OCR update

GET /jobs/{id} is polled by the console page; GET /course/{id} is the
results dashboard, linking each document's saved audit report.

Credential handling
-------------------
The API token arrives in the POST form, is held in process memory for the
duration of the job, and is never written to disk, logged, or echoed back
in any response. This console is single-operator: it binds to localhost by
default and has no user accounts — putting it on a network means putting
YOUR Canvas token's powers on that network. See webui/README note in
--host help before changing the bind address.
"""

from __future__ import annotations

import html
import json
import logging
import os
import re
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

log = logging.getLogger(__name__)

# Canvas subdomain: single DNS label, nothing that can smuggle a path or
# query into the URL we build from it (security review finding #2).
_DOMAIN_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
_COURSE_ID_RE = re.compile(r"^[A-Za-z0-9_]{1,64}$")

# Legacy Canvas auth rides in the query string, and requests exceptions can
# embed full URLs — scrub before an exception message reaches logs or
# clients (finding #1). The real fix is Authorization: Bearer upstream.
_TOKEN_RE = re.compile(r"access_token=[^&\s'\"]+")


def scrub_secrets(text: str) -> str:
    return _TOKEN_RE.sub("access_token=***", text)

DEFAULT_WORK_ROOT = Path.home() / "canvas-audits"

_VERDICT_LABEL = {"digital": "Digital", "scanned": "Scanned", "mixed": "Mixed",
                  "no_text": "No text"}


class Job:
    """Mutable state for one audit run, safe to render at any moment."""

    def __init__(self):
        self.id = uuid.uuid4().hex[:12]
        self.stage = "queued"
        self.detail = ""
        self.error = ""
        self.course_folder = ""

    def update(self, stage=None, detail=None, error=None, course_folder=None):
        if stage is not None:
            self.stage = stage
        if detail is not None:
            self.detail = detail
        if error is not None:
            self.error = error
        if course_folder is not None:
            self.course_folder = course_folder

    def as_dict(self) -> dict:
        return {"job_id": self.id, "stage": self.stage, "detail": self.detail,
                "error": self.error, "course_folder": self.course_folder}


def real_pipeline(params: dict, job: Job) -> None:
    """Drive Canvas Bot end to end. Runs in a worker thread."""
    domain = params["canvas_domain"]
    os.environ["CANVAS_DOMAIN"] = domain
    os.environ["CANVAS_COURSE_PAGE_ROOT"] = f"https://{domain}.instructure.com/courses"
    os.environ["API_PATH"] = f"https://{domain}.instructure.com/api/v1"

    # Token lives in cred's in-memory store only — never keyring, never disk.
    from network import cred
    cred._credentials["ACCESS_TOKEN"] = params["api_token"]

    from core.course_root import CanvasCourseRoot

    course_folder = Path(params["work_root"]) / params["course_id"]
    course_folder.mkdir(parents=True, exist_ok=True)

    job.update(stage="scanning", detail="reading course structure from Canvas")
    bot = CanvasCourseRoot(params["course_id"])
    bot.initialize_course()
    if not bot.exists:
        raise RuntimeError(
            f"Course {params['course_id']} could not be loaded — check the "
            f"course ID, domain, and token permissions.")

    job.update(stage="downloading", detail="downloading course files")
    bot.download_files(str(course_folder))

    job.update(stage="exporting", detail="writing JSON inventory and Excel report")
    bot.save_content_as_json(str(course_folder), str(course_folder))
    bot.save_content_as_excel(str(course_folder))

    job.update(stage="extracting", detail="OCR verdicts via doc-extract (~8s/page)")
    from core.text_extraction import ExtractionClient, ExtractionPass, update_excel_requires_ocr
    results = ExtractionPass(
        ExtractionClient(params["extract_endpoint"]), course_folder).run()

    from glob import glob
    workbooks = glob(str(course_folder / "*.xlsx")) + glob(str(course_folder / "*.xlsm"))
    if workbooks:
        update_excel_requires_ocr(workbooks[0], results)

    flagged = sum(1 for v in results.values() if v.get("requires_ocr"))
    job.update(stage="done", course_folder=str(course_folder),
               detail=f"{flagged} of {len(results)} documents require OCR")


def _load_course(work_root: Path, course_id: str) -> tuple[dict, dict]:
    if not course_id.replace("_", "").isalnum():
        raise HTTPException(status_code=404)
    folder = (work_root / course_id).resolve()
    if not (folder.is_relative_to(Path(work_root).resolve()) and folder.is_dir()):
        raise HTTPException(status_code=404)
    exports = sorted(folder.glob("*.json"))
    results_path = folder / ".manifest" / "extraction_results.json"
    course = {}
    for candidate in exports:
        data = json.loads(candidate.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "content" in data:
            course = data
            break
    if not course:
        raise HTTPException(status_code=404)
    results = (json.loads(results_path.read_text(encoding="utf-8"))
               if results_path.is_file() else {})
    return course, results


def create_app(pipeline=real_pipeline, work_root: Path | None = None,
               extract_base: str = "http://127.0.0.1:8077") -> FastAPI:
    app = FastAPI(title="canvas-bot web console")
    work_root = Path(work_root or DEFAULT_WORK_ROOT)
    jobs: dict[str, Job] = {}

    @app.get("/", response_class=HTMLResponse)
    def console() -> str:
        course_links = ""
        if work_root.is_dir():
            rows = []
            for folder in sorted(work_root.iterdir()):
                if folder.is_dir() and any(folder.glob("*.json")):
                    rows.append(f'<li><a href="/course/{html.escape(folder.name)}">'
                                f'{html.escape(folder.name)}</a></li>')
            course_links = "".join(rows)
        return _CONSOLE_HTML.replace("{{COURSES}}",
                                     course_links or "<li>No audited courses yet.</li>")

    @app.post("/audit")
    def start_audit(
        request: Request,
        canvas_domain: str = Form(...),
        course_id: str = Form(...),
        api_token: str = Form(...),
        extract_endpoint: str = Form("http://127.0.0.1:8077"),
    ) -> JSONResponse:
        # CSRF guard: browsers always send Origin on cross-site POSTs. A
        # same-origin fetch (or curl, which sends none) passes; a hostile
        # page POSTing at localhost does not. (finding #3)
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != f"{request.url.scheme}://{request.url.netloc}":
            raise HTTPException(status_code=403, detail="cross-origin request refused")

        canvas_domain = canvas_domain.strip().lower()
        course_id = course_id.strip()
        if not _DOMAIN_RE.match(canvas_domain):
            raise HTTPException(status_code=422, detail=(
                "Canvas domain must be the bare subdomain, e.g. 'myschool' "
                "for myschool.instructure.com"))
        if not _COURSE_ID_RE.match(course_id):
            raise HTTPException(status_code=422, detail="Course ID must be alphanumeric")

        job = Job()
        jobs[job.id] = job
        params = {
            "canvas_domain": canvas_domain,
            "course_id": course_id,
            "api_token": api_token,
            "extract_endpoint": extract_endpoint.strip(),
            "work_root": work_root,
        }

        def run():
            try:
                pipeline(params, job)
            except Exception as exc:  # noqa: BLE001 - job surface, not crash
                message = scrub_secrets(f"{type(exc).__name__}: {exc}")
                log.error(f"Audit job failed: {message}")
                job.update(stage="error", error=message)

        threading.Thread(target=run, daemon=True).start()
        return JSONResponse(job.as_dict())

    @app.get("/jobs/{job_id}")
    def job_state(job_id: str) -> JSONResponse:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404)
        return JSONResponse(job.as_dict())

    @app.get("/course/{course_id}", response_class=HTMLResponse)
    def dashboard(course_id: str) -> str:
        course, results = _load_course(work_root, course_id)
        docs = course["content"]["documents"]["documents"]
        rows = []
        for doc in docs:
            v = results.get(doc["url"], {})
            classification = v.get("classification", "unaudited")
            if "error" in v:
                classification = "unaudited"
            if "error" in v or not v:
                flag = "Not audited"
            elif v.get("score") is not None:
                flag = f"{v['score']}/100 ({html.escape(str(v.get('band', '')))})"
            else:
                flag = "Yes — requires OCR" if v.get("requires_ocr") else "OK"
            # Details = the interactive review page (edit figures, resubmit
            # conversions), not the static report — that lives inside it.
            if v.get("report_url"):
                audit_folder = v["report_url"].split("/")[2]
                report = (f'<a href="{extract_base}/?audit={html.escape(audit_folder)}">'
                          f'review &amp; edit</a>')
            else:
                report = "None"
            rows.append(
                f"<tr><td>{html.escape(doc['title'])}</td>"
                f"<td><span class='chip {html.escape(classification)}'>"
                f"{_VERDICT_LABEL.get(classification, html.escape(classification))}</span></td>"
                f"<td>{flag}</td><td>{report}</td>"
                f"<td><a href='{html.escape(doc['url'])}'>canvas</a></td></tr>")
        flagged = sum(1 for v in results.values() if v.get("requires_ocr"))
        name = html.escape(course.get("course_name", course_id))
        return _DASHBOARD_HTML \
            .replace("{{NAME}}", name) \
            .replace("{{COURSE_ID}}", html.escape(course_id)) \
            .replace("{{SUMMARY}}", f"{flagged} of {len(docs)} documents require OCR remediation.") \
            .replace("{{ROWS}}", "".join(rows))

    @app.get("/course/{course_id}/excel")
    def excel(course_id: str) -> FileResponse:
        _load_course(work_root, course_id)  # validates + guards the path
        folder = work_root / course_id
        books = sorted(folder.glob("*.xlsx")) + sorted(folder.glob("*.xlsm"))
        if not books:
            raise HTTPException(status_code=404)
        return FileResponse(books[0], filename=books[0].name)

    return app


_STYLE = """
:root { --paper:#faf8f4; --ink:#1a1712; --ink-soft:#5c564b; --rule:#d8d2c6;
  --accent:#7c2d12; --mono:ui-monospace,Menlo,monospace; }
@media (prefers-color-scheme: dark) { :root { --paper:#171512; --ink:#ece7dd;
  --ink-soft:#a89f8f; --rule:#3a352c; --accent:#fdba74; } }
body{margin:0;background:var(--paper);color:var(--ink);
  font:16px/1.55 Georgia,serif} header,main{max-width:46rem;margin:0 auto;
  padding:0 1.25rem} header{padding-top:2.5rem}
h1{font-size:1.8rem;margin:0} h1 .tag{font-family:var(--mono);font-size:.95rem;
  color:var(--accent);display:block} a{color:var(--accent)}
label{display:block;margin:1rem 0 .25rem;font-weight:bold}
input{font:inherit;width:100%;max-width:28rem;padding:.45rem .6rem;
  border:2px solid var(--rule);border-radius:3px;background:var(--paper);
  color:var(--ink)} input:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
button{font:inherit;margin-top:1.25rem;padding:.55rem 1.4rem;background:var(--ink);
  color:var(--paper);border:2px solid var(--ink);border-radius:3px;cursor:pointer}
button:focus-visible,a:focus-visible{outline:3px solid var(--accent);
  outline-offset:3px}
#status{font-family:var(--mono);font-size:.9rem;min-height:1.5rem;margin:1rem 0}
table{border-collapse:collapse;width:100%;font-size:.92rem;margin:1rem 0}
th,td{text-align:left;padding:.45rem .6rem;border-bottom:1px solid var(--rule)}
th{font-family:var(--mono);font-size:.75rem;text-transform:uppercase;
  letter-spacing:.06em}
.chip{font-family:var(--mono);font-size:.78rem;padding:.15rem .6rem;
  border-radius:999px;white-space:nowrap;background:var(--rule);
  border:1.5px solid var(--ink-soft);color:var(--ink)}
.chip.digital{background:#dcfce7;color:#14532d}
.chip.scanned{background:#fee2e2;color:#7f1d1d}
.chip.no_text,.chip.mixed{background:#fef9c3;color:#713f12}
.note{color:var(--ink-soft);font-size:.85rem}
"""

_CONSOLE_HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Canvas Bot — course audit console</title><style>{_STYLE}</style></head>
<body>
<header><h1><span class="tag">canvas-bot</span>Course audit console</h1>
<p>Scan a Canvas course, download its content, and get accessibility
verdicts for every document — all from the browser.</p></header>
<main>
<form id="form">
  <label for="canvas_domain">Canvas domain</label>
  <input id="canvas_domain" name="canvas_domain" required
         placeholder="myschool (as in myschool.instructure.com)">
  <label for="course_id">Course ID</label>
  <input id="course_id" name="course_id" required inputmode="numeric"
         placeholder="123456">
  <label for="api_token">Canvas API token</label>
  <input id="api_token" name="api_token" type="password" required
         autocomplete="off" aria-describedby="token-note">
  <p class="note" id="token-note">Held in memory for this audit only — never
  stored, logged, or sent anywhere but your Canvas instance.</p>
  <label for="extract_endpoint">doc-extract service</label>
  <input id="extract_endpoint" name="extract_endpoint"
         value="http://127.0.0.1:8077">
  <button>Start course audit</button>
</form>
<p id="status" role="status" aria-live="polite"></p>
<h2>Audited courses</h2>
<ul>{{{{COURSES}}}}</ul>
</main>
<script>
const form = document.getElementById("form");
const status = document.getElementById("status");
const button = form.querySelector("button");
let running = false, lastStage = "";

form.addEventListener("submit", async (e) => {{
  e.preventDefault();
  if (running) return;             // aria-disabled guard, no focus loss
  running = true;
  button.setAttribute("aria-disabled", "true");
  lastStage = "";
  status.textContent = "Starting audit…";
  let r;
  try {{
    r = await fetch("/audit", {{method: "POST", body: new FormData(form)}});
  }} catch (err) {{
    running = false; button.removeAttribute("aria-disabled");
    status.textContent = "Could not reach the console server."; return;
  }}
  if (!r.ok) {{
    running = false; button.removeAttribute("aria-disabled");
    let detail = r.statusText;
    try {{ detail = (await r.json()).detail ?? detail; }} catch {{}}
    status.textContent = "Could not start: " + detail; return;
  }}
  const job = await r.json();
  const poll = setInterval(async () => {{
    const s = await (await fetch("/jobs/" + job.job_id)).json();
    if (s.stage === "error") {{
      clearInterval(poll); running = false;
      button.removeAttribute("aria-disabled");
      status.textContent = "Audit failed: " + s.error;
    }} else if (s.stage === "done") {{
      clearInterval(poll); running = false;
      button.removeAttribute("aria-disabled");
      const id = form.course_id.value.trim();
      // No auto-redirect: announce, then hand the user a focused link so
      // AT gets to hear the completion before any navigation happens.
      status.textContent = "Audit complete — " + s.detail + ".";
      const link = document.createElement("a");
      link.href = "/course/" + encodeURIComponent(id);
      link.textContent = "Open the course dashboard";
      status.append(" ", link);
      link.focus();
    }} else if (s.stage !== lastStage) {{
      // Announce stage transitions only — a 2s-interval rewrite would
      // chatter at screen-reader users for the whole multi-minute run.
      lastStage = s.stage;
      status.textContent = s.stage + (s.detail ? " — " + s.detail : "");
    }}
  }}, 2000);
}});
</script>
</body></html>
"""

_DASHBOARD_HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Audit — {{{{NAME}}}}</title><style>{_STYLE}</style></head>
<body>
<header><h1><span class="tag">canvas-bot</span>{{{{NAME}}}}</h1>
<p>{{{{SUMMARY}}}}</p>
<p><a href="/course/{{{{COURSE_ID}}}}/excel">Download Excel report</a> ·
<a href="/">Back to console</a></p></header>
<main>
<table>
<caption class="note">documents and verdicts</caption>
<thead><tr><th scope="col">Document</th><th scope="col">Classification</th>
<th scope="col">Score</th><th scope="col">Details</th>
<th scope="col">Source</th></tr></thead>
<tbody>{{{{ROWS}}}}</tbody>
</table>
</main>
</body></html>
"""


def main() -> None:
    import argparse

    import uvicorn

    ap = argparse.ArgumentParser(description="Canvas Bot web console")
    ap.add_argument("--host", default="127.0.0.1",
                    help="Bind address. Localhost only by default — this "
                         "console has no authentication of its own.")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--work-root", default=str(DEFAULT_WORK_ROOT))
    args = ap.parse_args()
    uvicorn.run(create_app(work_root=Path(args.work_root)),
                host=args.host, port=args.port)


if __name__ == "__main__":
    main()

"""Verify analyze returns section scores and section rewrite works."""

from pathlib import Path
from urllib import request, error
import json

import fitz

SECTION_KEYS = ("summary", "experience", "projects", "skills")
JD = (
    "We need a Software Engineer with Python, FastAPI, React, and SQL. "
    "Build APIs and dashboards for SaaS products."
)


def make_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "Alex Chen\nSoftware Engineer\n"
        "Summary: Backend-focused engineer building APIs.\n"
        "Skills: Python, FastAPI, React, SQL\n"
        "Experience: Built APIs and dashboards for SaaS products.\n"
        "Projects: Internal analytics dashboard with React.",
    )
    doc.save(path)
    doc.close()


def upload(path: Path):
    data = path.read_bytes()
    boundary = "----BoundaryVerifyHeatmap"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = request.Request(
        "http://127.0.0.1:8000/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def post_json(url: str, payload: dict, timeout: int = 180):
    body = json.dumps(payload).encode()
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode())
    except error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


pdf_path = Path("_verify_heatmap.pdf")
make_pdf(pdf_path)

upload_result = upload(pdf_path)
filename = upload_result["filename"]
print("Upload OK:", filename)

status, analyze_data = post_json(
    "http://127.0.0.1:8000/analyze",
    {"filename": filename, "job_description": JD},
)
print("Analyze status:", status)
assert status == 200, analyze_data

analysis = analyze_data.get("analysis") or analyze_data
sections = analysis.get("sections")
assert isinstance(sections, dict), "sections missing"
for key in SECTION_KEYS:
    section = sections.get(key)
    assert isinstance(section, dict), f"missing section {key}"
    assert isinstance(section.get("score"), int), f"{key}.score not int"
    assert 0 <= section["score"] <= 100, f"{key}.score out of range"
    assert isinstance(section.get("issues"), list), f"{key}.issues not list"
    for issue in section["issues"]:
        assert isinstance(issue, dict)
        assert "type" in issue and "description" in issue and "severity" in issue
    print(f"  {key}: score={section['score']} issues={len(section['issues'])}")

print("Overall ATS:", analysis.get("ats_score"))

status, rewrite_data = post_json(
    "http://127.0.0.1:8000/rewrite",
    {
        "filename": filename,
        "job_description": JD,
        "section": "projects",
    },
)
print("Section rewrite status:", status)
assert status == 200, rewrite_data
rewrite = rewrite_data.get("rewrite") or rewrite_data
assert isinstance(rewrite.get("summary"), str) and rewrite["summary"]
assert isinstance(rewrite.get("projects"), list)
print("Projects rewritten bullets:", len(rewrite["projects"]))
print("Heatmap verify OK")

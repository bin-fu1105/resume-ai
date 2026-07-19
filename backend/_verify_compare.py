"""Verify compare uses parsed resume + rewrite without Claude."""

from pathlib import Path
from urllib import request, error
import json

import fitz

from services.compare_service import compare_resumes, structure_resume_text


def make_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "Alex Chen\n"
        "Summary\n"
        "Software engineer building SaaS products.\n"
        "Experience\n"
        "Built SaaS APIs and dashboards\n"
        "Improved deploy reliability with Docker\n"
        "Projects\n"
        "Inventory platform with React frontend and Python API\n"
        "Skills\n"
        "Python, React, Docker, PostgreSQL\n",
    )
    doc.save(path)
    doc.close()


def post_json(url: str, payload: dict):
    data = json.dumps(payload).encode()
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=180) as resp:
            return resp.status, json.loads(resp.read().decode())
    except error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def upload(path: Path):
    data = path.read_bytes()
    boundary = "----BoundaryCompareVerify"
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


sample = """
Alex Chen
Summary
Software engineer building SaaS products.
Experience
Built SaaS APIs and dashboards
Improved deploy reliability with Docker
Projects
Inventory platform with React frontend and Python API
Skills
Python, React, Docker, PostgreSQL
"""
structured = structure_resume_text(sample)
assert structured["summary"]
assert structured["experience"]
assert structured["projects"]
assert structured["skills"]
print("Structure OK:", {k: bool(v) for k, v in structured.items()})

local = compare_resumes(
    sample,
    {
        "summary": "Full stack engineer delivering SaaS products with Python and React.",
        "experience": [
            "Built SaaS APIs and interactive dashboards in Python and React",
            "Improved deploy reliability by containerizing services with Docker",
        ],
        "projects": [
            "Built an inventory platform with React frontend and Python API"
        ],
        "skills": ["Python", "React", "Docker", "PostgreSQL", "REST APIs"],
    },
)
assert len(local["sections"]) == 4
assert any(section["has_changes"] for section in local["sections"])
print("Local compare OK, changed sections:", sum(s["has_changes"] for s in local["sections"]))

pdf_path = Path("_verify_compare.pdf")
make_pdf(pdf_path)
uploaded = upload(pdf_path)
jd = "Hiring a Full Stack Engineer with Python, React, Docker, and PostgreSQL."

analyze_status, _ = post_json(
    "http://127.0.0.1:8000/analyze",
    {"filename": uploaded["filename"], "job_description": jd},
)
print("Analyze:", analyze_status)

rewrite_status, rewrite = post_json(
    "http://127.0.0.1:8000/rewrite",
    {"filename": uploaded["filename"], "job_description": jd},
)
print("Rewrite:", rewrite_status, bool(rewrite.get("summary")))

compare_status, compare = post_json(
    "http://127.0.0.1:8000/compare",
    {"filename": uploaded["filename"], "rewrite": rewrite},
)
print("Compare:", compare_status)
print("Sections:", [s["id"] for s in compare.get("sections", [])])
print("Has changes:", [s["id"] for s in compare.get("sections", []) if s.get("has_changes")])

pdf_path.unlink(missing_ok=True)

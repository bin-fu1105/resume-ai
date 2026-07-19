from pathlib import Path
from urllib import request, error
import json

import fitz


def make_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "Alex Chen\nFull Stack Engineer\nSkills: Python, React, Docker, PostgreSQL\n"
        "Experience: Built SaaS APIs and dashboards. Improved deploy reliability.\n"
        "Project: Inventory platform with React frontend and Python API.",
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
    boundary = "----BoundaryRewriteVerify"
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


pdf_path = Path("_verify_rewrite.pdf")
make_pdf(pdf_path)
uploaded = upload(pdf_path)
jd = "Hiring a Full Stack Engineer with Python, React, Docker, and PostgreSQL."

analyze_status, analyze_result = post_json(
    "http://127.0.0.1:8000/analyze",
    {"filename": uploaded["filename"], "job_description": jd},
)
print("Analyze:", analyze_status, "keys" if analyze_result.get("analysis") else analyze_result)

rewrite_status, rewrite_result = post_json(
    "http://127.0.0.1:8000/rewrite",
    {
        "filename": uploaded["filename"],
        "job_description": jd,
    },
)
print("Rewrite status:", rewrite_status)
required = ["summary", "experience", "projects", "skills"]
print("Has rewrite keys:", all(key in rewrite_result for key in required))
if rewrite_status == 200:
    print("summary length:", len(rewrite_result.get("summary") or ""))
    print("experience count:", len(rewrite_result.get("experience") or []))
    print("projects count:", len(rewrite_result.get("projects") or []))
    print("skills:", rewrite_result.get("skills"))
else:
    print("error:", rewrite_result.get("detail") or rewrite_result)

pdf_path.unlink(missing_ok=True)

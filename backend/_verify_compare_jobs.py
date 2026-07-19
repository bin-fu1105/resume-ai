"""Smoke-test upload → /compare-jobs → best_match recommendation."""

from pathlib import Path
from urllib import request, error
import json

import fitz


def make_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "Alex Chen\nSoftware Engineer\n"
        "Skills: Python, FastAPI, React, SQL, AWS\n"
        "Experience: Built SaaS APIs and dashboards at NovaTech.\n"
        "Projects: Analytics dashboard with React and FastAPI.",
    )
    doc.save(path)
    doc.close()


def upload(path: Path):
    data = path.read_bytes()
    boundary = "----BoundaryVerifyCompareJobs"
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


def post_json(url: str, payload: dict, timeout: int = 420):
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


pdf_path = Path("_verify_compare_jobs.pdf")
make_pdf(pdf_path)
upload_result = upload(pdf_path)
filename = upload_result["filename"]
print("Upload OK:", filename)

payload = {
    "filename": filename,
    "jobs": [
        {
            "company": "Google",
            "job_description": (
                "Software Engineer. Strong systems design, C++, distributed systems. "
                "Experience with large-scale infrastructure preferred."
            ),
        },
        {
            "company": "Amazon",
            "job_description": (
                "Software Engineer. Python, FastAPI, React, SQL, AWS. "
                "Build SaaS APIs and customer-facing dashboards."
            ),
        },
    ],
}

status, data = post_json("http://127.0.0.1:8000/compare-jobs", payload)
print("Compare status:", status)
assert status == 200, data

results = data.get("results") or []
assert len(results) == 2, results
for item in results:
    assert "company" in item and "score" in item
    assert isinstance(item["score"], int)
    assert "strengths" in item and "missing_skills" in item
    assert "summary" in item
    assert "resume_match" in item
    assert "recommendation" in item
    print(f"  {item['company']}: score={item['score']} match={item['resume_match']}")

best = data.get("best_match")
reason = data.get("reason")
assert best in {item["company"] for item in results}
assert reason
top = max(results, key=lambda item: item["score"])
assert best == top["company"]
print("Best match:", best)
print("Reason:", reason[:160])
print("Compare-jobs verify OK")

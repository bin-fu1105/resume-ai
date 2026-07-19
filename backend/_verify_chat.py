"""Smoke-test upload -> analyze -> chat multi-turn."""

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
    boundary = "----BoundaryChatVerify"
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


pdf_path = Path("_verify_chat.pdf")
make_pdf(pdf_path)
uploaded = upload(pdf_path)
jd = "Hiring a Full Stack Engineer with Python, React, Docker, and PostgreSQL."

analyze_status, analyze_result = post_json(
    "http://127.0.0.1:8000/analyze",
    {"filename": uploaded["filename"], "job_description": jd},
)
print("Analyze:", analyze_status, bool(analyze_result.get("analysis")))

analysis = analyze_result.get("analysis") or {}
chat1_status, chat1 = post_json(
    "http://127.0.0.1:8000/chat",
    {
        "filename": uploaded["filename"],
        "job_description": jd,
        "history": [],
        "message": "Why is my ATS score low?",
        "analysis": analysis,
        "rewrite": {},
    },
)
print("Chat1:", chat1_status, "reply_len", len((chat1.get("reply") or "")))
print("Chat1 knows score:", str(analysis.get("ats_score", "")) in (chat1.get("reply") or "") or "ATS" in (chat1.get("reply") or ""))

chat2_status, chat2 = post_json(
    "http://127.0.0.1:8000/chat",
    {
        "filename": uploaded["filename"],
        "job_description": jd,
        "history": [
            {"role": "user", "content": "Why is my ATS score low?"},
            {"role": "assistant", "content": chat1.get("reply") or ""},
        ],
        "message": "Give me one concrete project bullet I should add.",
        "analysis": analysis,
        "rewrite": {},
    },
)
print("Chat2:", chat2_status, "reply_len", len((chat2.get("reply") or "")))
print("Multi-turn ok:", chat2_status == 200 and bool(chat2.get("reply")))

pdf_path.unlink(missing_ok=True)

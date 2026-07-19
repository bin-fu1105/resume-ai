"""Smoke-test interview start → answer → summary."""

from pathlib import Path
from urllib import request, error
import json

import fitz

JD = (
    "Software Engineer role requiring Python, FastAPI, React, and SQL. "
    "Build APIs and dashboards for SaaS products."
)


def make_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "Alex Chen\nSoftware Engineer\n"
        "Summary: Backend-focused engineer building APIs and React dashboards.\n"
        "Skills: Python, FastAPI, React, SQL, Docker\n"
        "Experience: Built REST APIs and dashboards for SaaS products at NovaTech.\n"
        "Projects: Internal analytics dashboard with React and FastAPI.",
    )
    doc.save(path)
    doc.close()


def upload(path: Path):
    data = path.read_bytes()
    boundary = "----BoundaryVerifyInterview"
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


pdf_path = Path("_verify_interview.pdf")
make_pdf(pdf_path)

upload_result = upload(pdf_path)
filename = upload_result["filename"]
print("Upload OK:", filename)

status, start_data = post_json(
    "http://127.0.0.1:8000/interview/start",
    {"filename": filename, "job_description": JD},
)
print("Start status:", status)
assert status == 200, start_data
questions = start_data.get("questions") or []
assert 8 <= len(questions) <= 10, f"expected 8-10 questions, got {len(questions)}"
assert all("question" in q and "category" in q and "id" in q for q in questions)
categories = {q["category"] for q in questions}
assert "Behavioral" in categories and "Technical" in categories
print(f"Questions: {len(questions)}")
for q in questions[:3]:
    print(f"  {q['id']}. [{q['category']}] {q['question'][:80]}")

first = questions[0]
status, answer_data = post_json(
    "http://127.0.0.1:8000/interview/answer",
    {
        "history": [],
        "question": first["question"],
        "answer": (
            "I am a software engineer with experience building FastAPI services and "
            "React dashboards. At NovaTech I owned API endpoints and improved "
            "dashboard load times by optimizing SQL queries."
        ),
    },
)
print("Answer status:", status)
assert status == 200, answer_data
assert isinstance(answer_data.get("score"), int)
assert 0 <= answer_data["score"] <= 100
feedback = answer_data.get("feedback") or {}
assert isinstance(feedback.get("strengths"), list)
assert isinstance(feedback.get("weaknesses"), list)
assert isinstance(feedback.get("improvements"), list)
assert answer_data.get("follow_up")
print("Score:", answer_data["score"])
print("Follow-up:", str(answer_data["follow_up"])[:100])

# Mini multi-question loop for a stronger summary signal
turns = [
    {
        "question": first["question"],
        "answer": "I build APIs and dashboards with FastAPI and React.",
        "score": answer_data["score"],
        "feedback": feedback,
    }
]

for question in questions[1:3]:
    status, eval_data = post_json(
        "http://127.0.0.1:8000/interview/answer",
        {
            "history": [
                {"question": t["question"], "answer": t["answer"], "score": t["score"]}
                for t in turns
            ],
            "question": question["question"],
            "answer": (
                "In a recent project I used Python and SQL to ship a feature under "
                "deadline. Situation: slow reporting. Task: speed it up. Action: "
                "indexed queries and cached results. Result: faster dashboards."
            ),
        },
    )
    assert status == 200, eval_data
    turns.append(
        {
            "question": question["question"],
            "answer": "STAR-style project answer with measurable outcome.",
            "score": eval_data["score"],
            "feedback": eval_data.get("feedback") or {},
        }
    )
    print(f"Answered Q{question['id']} score={eval_data['score']}")

status, summary = post_json(
    "http://127.0.0.1:8000/interview/summary",
    {
        "filename": filename,
        "job_description": JD,
        "turns": turns,
    },
)
print("Summary status:", status)
assert status == 200, summary
assert isinstance(summary.get("overall_score"), int)
assert len(summary.get("improvements") or []) == 5
assert summary.get("learning_topics")
print("Overall:", summary["overall_score"])
print("Learning topics:", summary["learning_topics"][:3])
print("Interview verify OK")

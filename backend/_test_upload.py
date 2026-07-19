from pathlib import Path
from urllib import request, error

Path("_test_large.pdf").write_bytes(b"%PDF-1.1\n" + b"x" * (10 * 1024 * 1024))


def upload(path: str):
    data = Path(path).read_bytes()
    name = Path(path).name
    boundary = "----Boundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = request.Request(
        "http://127.0.0.1:8000/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with request.urlopen(req) as resp:
            return resp.status, resp.read().decode()
    except error.HTTPError as e:
        return e.code, e.read().decode()


cases = [
    ("PDF ok", "_test_resume.pdf", 200),
    ("DOCX ok", "_test_resume.docx", 200),
    ("TXT reject", "_test_bad.txt", 400),
    ("Large reject", "_test_large.pdf", 400),
]

for label, path, expect in cases:
    status, text = upload(path)
    ok = "OK" if status == expect else "FAIL"
    print(f"=== {label} ===")
    print(f"status {status} expected {expect} {ok}")
    print(text[:300])
    print()

print("uploads dir:")
for p in sorted(Path("uploads").glob("*"))[-8:]:
    print(p.name, p.stat().st_size)

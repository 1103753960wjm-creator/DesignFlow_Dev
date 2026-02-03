import json
import uuid
from pathlib import Path
from urllib.request import Request, urlopen


def post_json(url: str, data: dict) -> dict:
    payload = json.dumps(data).encode("utf-8")
    req = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def post_multipart(url: str, token: str, file_path: Path) -> dict:
    boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
    crlf = "\r\n"

    ext = file_path.suffix.lower()
    content_type = "application/octet-stream"
    if ext == ".dxf":
        content_type = "application/dxf"
    elif ext == ".png":
        content_type = "image/png"
    elif ext in (".jpg", ".jpeg"):
        content_type = "image/jpeg"

    fb = file_path.read_bytes()
    parts: list[bytes] = []
    parts.append(f"--{boundary}".encode())
    parts.append(f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"'.encode())
    parts.append(f"Content-Type: {content_type}".encode())
    parts.append(b"")
    parts.append(fb)
    parts.append(f"--{boundary}--".encode())

    data = crlf.encode().join(parts) + crlf.encode()
    req = Request(
        url,
        data=data,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    base = "http://127.0.0.1:8002/api/v1"
    email = f"img_{uuid.uuid4().hex[:8]}@studio.com"
    phone = "138" + str(uuid.uuid4().int)[0:8]

    reg = post_json(
        f"{base}/auth/register",
        {"email": email, "phone": phone, "password": "Password123", "nickname": "IMG"},
    )
    token = reg["access_token"]

    img = Path(__file__).resolve().parents[1] / "assets" / "mock" / "downloaded-image.png"
    if not img.exists():
        raise SystemExit("找不到 assets/mock/downloaded-image.png")

    resp = post_multipart(f"{base}/design/process-cad", token, img)
    print(json.dumps(resp, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


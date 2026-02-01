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

    fb = file_path.read_bytes()
    parts: list[bytes] = []
    parts.append(f"--{boundary}".encode())
    parts.append(f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"'.encode())
    parts.append(b"Content-Type: application/dxf")
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
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    base = "http://127.0.0.1:8002/api/v1"
    email = f"cad_{uuid.uuid4().hex[:8]}@studio.com"
    phone = "138" + str(uuid.uuid4().int)[0:8]

    reg = post_json(
        f"{base}/auth/register",
        {"email": email, "phone": phone, "password": "Password123", "nickname": "CAD"},
    )
    token = reg["access_token"]

    dxf = Path(__file__).resolve().parents[1] / "assets" / "mock" / "sample_room.dxf"
    resp = post_multipart(f"{base}/design/process-cad", token, dxf)
    print(json.dumps(resp, ensure_ascii=False, indent=2))

    png = Path(__file__).resolve().parents[1] / "assets" / "mock" / "test_room.png"
    if png.exists():
        resp2 = post_multipart(f"{base}/design/process-cad", token, png)
        print(json.dumps(resp2, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from types import ModuleType
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.modules.engineering.router import router as engineering_router


def _ensure_test_png() -> Path:
    p = Path(__file__).resolve().parents[1] / "assets" / "mock" / "test_room.png"
    if not p.exists():
        raise RuntimeError(f"Missing test asset: {p}")
    return p


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app = FastAPI()
    static_dir = tmp_path / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.include_router(engineering_router, prefix="/api/v1/engineering")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="test-user")

    import app.modules.engineering.router as eng_router

    monkeypatch.setattr(eng_router, "_backend_dir", lambda: tmp_path)
    monkeypatch.setenv("IMAGE_DXF_USE_LOCAL_SEG", "0")
    monkeypatch.setenv("IMAGE_DXF_MM_PER_PX", "10")
    monkeypatch.setenv("IMAGE_DXF_MIN_MERGED_LINES", "4")
    return TestClient(app)


def test_upload_image_returns_static_dxf_url_and_downloadable(client: TestClient):
    def _fake_convert_image_to_dxf(image_path: str, output_dxf_path: str):
        p = Path(output_dxf_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"0\nSECTION\n2\nENTITIES\n0\nLINE\n8\nWALL\n10\n0\n20\n0\n11\n1000\n21\n0\n0\nENDSEC\n0\nEOF\n")
        parts = [x.lower() for x in p.parts]
        session_id = None
        for i, name in enumerate(parts):
            if name == "sessions" and i + 1 < len(parts):
                session_id = p.parts[i + 1]
                break
        static_root = next((parent for parent in [p] + list(p.parents) if parent.name.lower() == "static"), None)
        if session_id and static_root:
            debug_dir = static_root / "debug" / session_id
            debug_dir.mkdir(parents=True, exist_ok=True)
            for name in ("debug_step1_gray.png", "debug_step2_ai_mask.png", "debug_step3_opencv_edges.png"):
                (debug_dir / name).write_bytes(b"\x89PNG\r\n\x1a\n")
        return p

    fake_worker = ModuleType("worker.image_to_dxf")
    fake_worker.ImageClarityError = type("ImageClarityError", (RuntimeError,), {})
    fake_worker.convert_image_to_dxf = _fake_convert_image_to_dxf

    with patch.dict(
        "sys.modules",
        {"worker.image_to_dxf": fake_worker},
    ), patch(
        "app.modules.engineering.router.convert_image_to_dxf",
        _fake_convert_image_to_dxf,
        create=True,
    ), patch(
        "app.modules.engineering.router.get_svg_preview",
        lambda _: "<svg>...</svg>",
    ):
        resp = client.post("/api/v1/engineering/upload/image", files={"file": ("room.png", b"fake", "image/png")})

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "converted"
    assert isinstance(data["dxf_url"], str)
    assert data["dxf_url"].startswith("/static/")
    assert data["svg_preview"] == "<svg>...</svg>"
    assert isinstance(data.get("debug_images"), list)
    assert len(data["debug_images"]) == 3
    for u in data["debug_images"]:
        assert isinstance(u, str) and u.startswith("/static/debug/")
        r3 = client.get(u)
        assert r3.status_code == 200

    r2 = client.get(data["dxf_url"])
    assert r2.status_code == 200
    assert len(r2.content) > 0

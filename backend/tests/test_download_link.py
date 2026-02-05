from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

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
    monkeypatch.setenv("IMAGE_DXF_MM_PER_PX", "10")
    monkeypatch.setenv("IMAGE_DXF_MIN_MERGED_LINES", "4")
    return TestClient(app)


def test_upload_image_returns_static_dxf_url_and_downloadable(client: TestClient):
    png_path = _ensure_test_png()
    with open(png_path, "rb") as f:
        resp = client.post("/api/v1/engineering/upload/image", files={"file": (png_path.name, f, "image/png")})

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "converted"
    assert isinstance(data["dxf_url"], str)
    assert data["dxf_url"].startswith("/static/")

    r2 = client.get(data["dxf_url"])
    assert r2.status_code == 200
    assert len(r2.content) > 0

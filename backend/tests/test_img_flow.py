from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import ezdxf
import pytest
from fastapi import FastAPI
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
    app.include_router(engineering_router, prefix="/api/v1/engineering")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="test-user")

    import app.modules.engineering.router as eng_router

    monkeypatch.setattr(eng_router, "_backend_dir", lambda: tmp_path)
    monkeypatch.setenv("IMAGE_DXF_USE_LOCAL_SEG", "0")
    monkeypatch.setenv("IMAGE_DXF_MM_PER_PX", "10")
    monkeypatch.setenv("IMAGE_DXF_MIN_MERGED_LINES", "4")
    yield TestClient(app)


def test_upload_image_converts_to_dxf_and_returns_svg(client: TestClient):
    png_path = _ensure_test_png()
    with open(png_path, "rb") as f:
        resp = client.post("/api/v1/engineering/upload/image", files={"file": (png_path.name, f, "image/png")})

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "converted"
    assert data["session_id"]
    assert isinstance(data["svg_preview"], str) and data["svg_preview"].strip()
    assert "<svg" in data["svg_preview"]

    assert isinstance(data["dxf_url"], str) and data["dxf_url"].startswith("/static/")
    assert isinstance(data.get("debug_images"), list)
    assert len(data["debug_images"]) == 3
    for u in data["debug_images"]:
        assert isinstance(u, str) and f"/static/debug/{data['session_id']}/" in u

    dxf_path = Path(data["dxf_file_path"])
    assert dxf_path.exists()
    assert dxf_path.suffix.lower() == ".dxf"
    debug_dir = dxf_path.parents[3] / "debug" / data["session_id"]
    for name in ("debug_step1_gray.png", "debug_step2_ai_mask.png", "debug_step3_opencv_edges.png"):
        assert (debug_dir / name).exists()

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    wall_entities = [e for e in msp if str(getattr(e.dxf, "layer", "")).upper() == "WALL"]
    seg_count = 0
    for e in wall_entities:
        t = e.dxftype()
        if t == "LINE":
            seg_count += 1
        elif t == "LWPOLYLINE":
            pts = list(e.get_points("xy"))
            if len(pts) >= 2:
                seg_count += len(pts) - 1
                if bool(getattr(e, "closed", False)) and len(pts) >= 3:
                    seg_count += 1
    assert seg_count >= 4

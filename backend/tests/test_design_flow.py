import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.modules.visual.router import router as visual_router


def _ensure_test_dxf() -> Path:
    dxf_path = Path(__file__).resolve().parent / "assets" / "test_room.dxf"
    if not dxf_path.exists():
        raise RuntimeError(f"Missing test asset: {dxf_path}")
    return dxf_path


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app = FastAPI()
    app.include_router(visual_router, prefix="/api/v1/visual")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="test-user")

    import app.modules.visual.router as visual_ep

    monkeypatch.setattr(visual_ep, "_backend_root", lambda: tmp_path)
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "true")
    monkeypatch.setenv("MOCK_3D", "true")

    yield TestClient(app)


def test_process_cad_upload_returns_task_id_and_outputs(client: TestClient, tmp_path: Path):
    dxf_path = _ensure_test_dxf()
    with open(dxf_path, "rb") as f:
        resp = client.post("/api/v1/visual/process-cad", files={"file": (dxf_path.name, f, "application/dxf")})

    assert resp.status_code == 200
    data = resp.json()
    assert data.get("task_id")
    assert data.get("status") == "done"
    assert data.get("output_dir")

    job_dir = Path(data["output_dir"])
    obj_path = job_dir / "model.obj"
    depth_path = job_dir / "depth_0.png"

    assert obj_path.exists()
    assert depth_path.exists()

    assert obj_path.stat().st_size > 0
    assert depth_path.stat().st_size > 0

    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)

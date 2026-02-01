import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.api import api_router
from app.core.deps import get_current_user


def _blender_available(blender_bin: str) -> bool:
    if Path(blender_bin).exists():
        return True
    return shutil.which(blender_bin) is not None


def _ensure_ezdxf():
    try:
        import ezdxf

        return ezdxf
    except Exception:
        env = os.environ.copy()
        env.setdefault("NO_PROXY", "*")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "ezdxf"], env=env)
        import ezdxf

        return ezdxf


def _ensure_test_dxf() -> Path:
    assets_dir = Path(__file__).resolve().parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    dxf_path = assets_dir / "test_room.dxf"
    if dxf_path.exists():
        return dxf_path

    ezdxf = _ensure_ezdxf()
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()
    pts = [(0, 0), (5000, 0), (5000, 4000), (0, 4000), (0, 0)]
    for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
        msp.add_line((x1, y1), (x2, y2))
    doc.saveas(str(dxf_path))
    return dxf_path


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="test-user")

    from app.api.v1.endpoints import design as design_ep

    monkeypatch.setattr(design_ep, "_backend_root", lambda: tmp_path)
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "true")
    monkeypatch.delenv("MOCK_3D", raising=False)

    yield TestClient(app)


def test_process_cad_upload_returns_task_id_and_outputs(client: TestClient, tmp_path: Path):
    blender_bin = os.getenv("BLENDER_PATH", "blender")
    if not _blender_available(blender_bin):
        pytest.skip("Blender executable not found, skipping integration test")

    dxf_path = _ensure_test_dxf()
    with open(dxf_path, "rb") as f:
        resp = client.post("/api/v1/design/process-cad", files={"file": (dxf_path.name, f, "application/dxf")})

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

    assert obj_path.stat().st_size > 1024
    assert depth_path.stat().st_size > 1024

    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)

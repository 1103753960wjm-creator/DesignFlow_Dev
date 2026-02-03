# 文件位置: backend/app/worker/tasks.py
import base64
import os
import shutil
import subprocess
import time
from pathlib import Path

from app.core.celery_app import celery_app
from app.core.camera_views import CAMERA_VIEW_KEYS_DEFAULT, LEGACY_DEPTH_KEY, depth_filename


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ensure_mock_assets() -> tuple[Path, Path]:
    assets_dir = _backend_root() / "assets" / "mock"
    assets_dir.mkdir(parents=True, exist_ok=True)

    obj_path = assets_dir / "sample_model.obj"
    depth_path = assets_dir / "sample_depth.png"

    if not obj_path.exists():
        obj_path.write_text("o Cube\nv 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf 1 2 3 4\n", encoding="utf-8")

    if not depth_path.exists():
        png_1x1 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=="
        )
        depth_path.write_bytes(base64.b64decode(png_1x1))

    return obj_path, depth_path


def _detect_blender_bin() -> str | None:
    env = (os.getenv("BLENDER_PATH", "") or os.getenv("BLENDER_BIN", "")).strip()
    if env:
        return env
    return shutil.which("blender") or shutil.which("blender.exe") or "blender"


def _blender_available(blender_bin: str | None) -> bool:
    if not blender_bin:
        return False
    if Path(blender_bin).exists():
        return True
    return shutil.which(blender_bin) is not None

def _safe_update_state(task, *, state: str, meta: dict):
    task_id = getattr(getattr(task, "request", None), "id", None)
    if not task_id:
        return
    task.update_state(state=state, meta=meta)


@celery_app.task(bind=True)
def generate_3d_assets(self, input_file_path: str, output_dir: str):
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    blender_bin = _detect_blender_bin()
    script_path = _backend_root() / "app" / "modules" / "visual" / "blender" / "blender_script.py"

    input_path = Path(input_file_path)
    ext = input_path.suffix.lower()
    dxf_path = input_path
    if ext in (".png", ".jpg", ".jpeg"):
        from worker.image_to_dxf import image_to_dxf

        dxf_path = out_dir / "input_from_image.dxf"
        image_to_dxf(image_path=input_path, dxf_path=dxf_path)

    if os.getenv("MOCK_3D", "").strip().lower() in ("1", "true", "yes"):
        print("Running in Mock Mode")
        obj_src, depth_src = _ensure_mock_assets()
        shutil.copyfile(obj_src, out_dir / "model.obj")
        for key in [*CAMERA_VIEW_KEYS_DEFAULT, LEGACY_DEPTH_KEY]:
            shutil.copyfile(depth_src, out_dir / depth_filename(key))
        return {"status": "done", "mode": "mock", "output_dir": str(out_dir)}

    if not _blender_available(blender_bin):
        print("Running in Mock Mode")
        obj_src, depth_src = _ensure_mock_assets()
        shutil.copyfile(obj_src, out_dir / "model.obj")
        for key in [*CAMERA_VIEW_KEYS_DEFAULT, LEGACY_DEPTH_KEY]:
            shutil.copyfile(depth_src, out_dir / depth_filename(key))
        return {"status": "done", "mode": "mock", "output_dir": str(out_dir)}

    cmd = [
        blender_bin,
        "--background",
        "--python",
        str(script_path),
        "--",
        "--input",
        str(dxf_path),
        "--output",
        str(out_dir),
    ]

    _safe_update_state(self, state="PROGRESS", meta={"progress": 5})
    try:
        proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        stdout = (e.stdout or "").strip()
        print("Running in Mock Mode")
        obj_src, depth_src = _ensure_mock_assets()
        shutil.copyfile(obj_src, out_dir / "model.obj")
        for key in [*CAMERA_VIEW_KEYS_DEFAULT, LEGACY_DEPTH_KEY]:
            shutil.copyfile(depth_src, out_dir / depth_filename(key))
        return {
            "status": "done",
            "mode": "mock",
            "output_dir": str(out_dir),
            "reason": f"Blender 执行失败: {stderr or stdout or e}",
        }

    expected = [out_dir / "model.obj", *[out_dir / depth_filename(k) for k in [*CAMERA_VIEW_KEYS_DEFAULT, LEGACY_DEPTH_KEY]]]
    if not all(p.exists() for p in expected):
        print("Running in Mock Mode")
        obj_src, depth_src = _ensure_mock_assets()
        shutil.copyfile(obj_src, out_dir / "model.obj")
        for key in [*CAMERA_VIEW_KEYS_DEFAULT, LEGACY_DEPTH_KEY]:
            shutil.copyfile(depth_src, out_dir / depth_filename(key))
        return {
            "status": "done",
            "mode": "mock",
            "output_dir": str(out_dir),
            "reason": "Blender 未生成完整输出（常见原因：Blender 内置 Python 缺少 ezdxf）",
            "stdout_tail": (proc.stdout or "")[-2000:],
            "stderr_tail": (proc.stderr or "")[-2000:],
        }

    _safe_update_state(self, state="PROGRESS", meta={"progress": 95})
    return {
        "status": "done",
        "mode": "blender",
        "output_dir": str(out_dir),
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
    }

@celery_app.task(bind=True)
def mock_rendering_task(self, prompt: str):
    """
    模拟一个耗时的渲染任务
    """
    print(f"👷 [Worker] 收到任务: 开始渲染 '{prompt}' ...")
    
    # 假装在努力工作 (每秒汇报一次进度)
    for i in range(1, 6):
        time.sleep(1) # 睡1秒
        self.update_state(state='PROGRESS', meta={'progress': i * 20}) # 更新进度 20%, 40%...
        print(f"⏳ [Worker] 渲染中... {i * 20}%")
    
    print(f"✅ [Worker] 任务完成!")
    return {"result_url": "http://fake-url.com/result.jpg", "status": "done"}

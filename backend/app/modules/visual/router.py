import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from app.core.config import settings
from app.core.camera_views import CAMERA_VIEW_KEYS_DEFAULT
from app.core.deps import get_current_user
from app.models.user import User
from app.modules.visual.models import (
    DesignGenerateRequest,
    DesignGenerateResponse,
    WhiteboxRequest,
    WhiteboxResponse,
    GalleryRequest,
    GalleryResponse,
    ProcessCadResponse,
)
from app.modules.visual.services import (
    backend_root,
    build_depth_urls,
    generate_plan_with_llm,
    mock_generate_gallery,
    mock_generate_whitebox,
)
from app.services.storage_service import decrypt_bytes, encrypt_bytes, read_file_bytes, write_file_bytes
from app.worker.tasks import generate_3d_assets


router = APIRouter()


def _backend_root() -> Path:
    return backend_root()


@router.post("/upload")
def upload_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    allowed_types = ["image/jpeg", "image/png", "application/acad", "image/vnd.dxf"]
    filename = file.filename.lower()
    if not any(filename.endswith(ext) for ext in [".jpg", ".png", ".jpeg", ".dxf", ".dwg"]):
        raise HTTPException(status_code=400, detail="不支持的文件格式")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{timestamp}_{file.filename}"
    backend_dir = _backend_root()
    save_dir = backend_dir / "static" / "uploads"
    save_dir.mkdir(parents=True, exist_ok=True)
    plain_path = save_dir / unique_filename
    ext = Path(file.filename).suffix.lower()
    is_cad = ext in (".dxf", ".dwg")
    secret = os.getenv("CAD_ENCRYPTION_SECRET", "").strip() or settings.SECRET_KEY
    try:
        if is_cad:
            encrypted_path = save_dir / f"{unique_filename}.enc"
            raw = file.file.read()
            token = encrypt_bytes(raw, secret)
            write_file_bytes(encrypted_path, token)
        else:
            with open(str(plain_path), "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {e}")
    base_url = str(request.base_url).rstrip("/")
    return {
        "filename": unique_filename,
        "url": f"{base_url}/api/v1/visual/cad/{unique_filename}" if is_cad else f"{base_url}/static/uploads/{unique_filename}",
        "encrypted": is_cad,
        "owner": str(current_user.id),
        "msg": "上传成功",
    }


@router.post("/process-cad", response_model=ProcessCadResponse)
def process_cad(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    filename = (file.filename or "").lower()
    if not any(filename.endswith(ext) for ext in (".dxf", ".png", ".jpg", ".jpeg")):
        raise HTTPException(status_code=400, detail="仅支持 .dxf / .png / .jpg 文件")
    backend_dir = _backend_root()
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + os.urandom(4).hex()
    job_dir = backend_dir / "static" / "processed" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix.lower()
    input_path = job_dir / f"input{ext}"
    try:
        with open(input_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {e}")
    eager = os.getenv("CELERY_TASK_ALWAYS_EAGER", "").strip().lower() in ("1", "true", "yes")
    eager = eager or os.getenv("USER_CELERY_ALWAYS_EAGER", "").strip().lower() in ("1", "true", "yes")
    if eager:
        result = generate_3d_assets.apply(args=(str(input_path), str(job_dir)), throw=True)
        base_url = str(request.base_url).rstrip("/")
        base = f"{base_url}/static/processed/{job_id}"
        depth_urls = build_depth_urls(base=base, output_dir=job_dir)
        return ProcessCadResponse(
            task_id=result.id,
            status="done",
            output_dir=str(job_dir),
            model_obj_url=f"{base}/model.obj",
            depth_urls=depth_urls,
        )
    try:
        task = generate_3d_assets.delay(str(input_path), str(job_dir))
        return ProcessCadResponse(task_id=task.id, status="processing")
    except Exception:
        base_url = str(request.base_url).rstrip("/")
        base = f"{base_url}/static/processed/{job_id}"
        return ProcessCadResponse(
            task_id=f"local-{job_id}",
            status="done",
            output_dir=str(job_dir),
            model_obj_url=f"{base}/model.obj",
            depth_urls=build_depth_urls(base=base, output_dir=job_dir),
        )


@router.get("/cad/{asset_id}")
def download_cad(asset_id: str, current_user: User = Depends(get_current_user)):
    if Path(asset_id).name != asset_id:
        raise HTTPException(status_code=400, detail="非法文件名")
    backend_dir = _backend_root()
    encrypted_path = backend_dir / "static" / "uploads" / f"{asset_id}.enc"
    if not encrypted_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    secret = os.getenv("CAD_ENCRYPTION_SECRET", "").strip() or settings.SECRET_KEY
    token = read_file_bytes(encrypted_path)
    raw = decrypt_bytes(token, secret)
    headers = {"Content-Disposition": f'attachment; filename="{asset_id}"'}
    return Response(content=raw, media_type="application/octet-stream", headers=headers)


@router.post("/generate", response_model=DesignGenerateResponse)
def generate_design(req: DesignGenerateRequest, current_user: User = Depends(get_current_user)):
    result = generate_plan_with_llm(req)
    return DesignGenerateResponse(
        provider=result["provider"],
        plan_markdown=result["plan_markdown"],
        sd_prompt=result["sd_prompt"],
        warnings=result["warnings"],
    )


@router.post("/whitebox", response_model=WhiteboxResponse)
def generate_whitebox(req: WhiteboxRequest, request: Request, current_user: User = Depends(get_current_user)):
    base_url = str(request.base_url).rstrip("/")
    result = mock_generate_whitebox(base_url=base_url)
    return WhiteboxResponse(whitebox_url=result.whitebox_url, depth_url=result.depth_url)


@router.post("/gallery", response_model=GalleryResponse)
def generate_gallery(req: GalleryRequest, request: Request, current_user: User = Depends(get_current_user)):
    base_url = str(request.base_url).rstrip("/")
    views = [v for v in (req.cameras or []) if v in CAMERA_VIEW_KEYS_DEFAULT]
    if not views:
        views = ["main", "top", "elev_n", "elev_s", "corner_ne", "corner_sw"]
    result = mock_generate_gallery(base_url=base_url, count=len(views))
    return GalleryResponse(images=result.images, views=views)

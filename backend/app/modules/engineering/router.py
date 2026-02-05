from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.deps import get_current_user
from app.models.user import User
from app.modules.engineering.schemas import ModifyCADRequest, ModifyCADResponse, UploadCadResponse, UploadImageConvertedResponse
from app.modules.engineering.services import get_svg_preview, modify_cad_structure


router = APIRouter()


def _backend_dir() -> Path:
    return Path(__file__).resolve().parents[3]


@router.get("/ping")
def ping():
    return {"status": "ok"}


@router.post("/upload", response_model=UploadCadResponse)
def upload(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    filename = (file.filename or "").lower()
    if not filename.endswith(".dxf"):
        raise HTTPException(status_code=400, detail="仅支持 .dxf 文件")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique = f"{stamp}_{Path(file.filename).name}"
    backend_dir = _backend_dir()
    save_dir = backend_dir / "static" / "engineering" / "uploads"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / unique
    try:
        content = file.file.read()
        with open(save_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件保存失败: {e}")
    svg_preview = get_svg_preview(str(save_path))
    return UploadCadResponse(status="success", dxf_file_path=str(save_path), svg_preview=svg_preview)


@router.post("/upload/image", response_model=UploadImageConvertedResponse)
def upload_image(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="仅支持 image/* 上传")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".jpg", ".jpeg", ".png"):
        raise HTTPException(status_code=400, detail="仅支持 .jpg/.jpeg/.png")

    backend_dir = _backend_dir()
    session_id = uuid4().hex
    save_dir = backend_dir / "static" / "engineering" / "sessions" / session_id
    save_dir.mkdir(parents=True, exist_ok=True)
    img_path = save_dir / f"source{suffix}"
    dxf_path = save_dir / "converted.dxf"

    try:
        content = file.file.read()
        with open(img_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件保存失败: {e}")

    try:
        from worker.image_to_dxf import ImageClarityError, convert_image_to_dxf

        convert_image_to_dxf(str(img_path), str(dxf_path))
    except ImageClarityError:
        raise HTTPException(status_code=422, detail="图片清晰度不足")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"矢量化失败: {e}")

    svg_preview = get_svg_preview(str(dxf_path))
    static_root = (backend_dir / "static").resolve()
    try:
        rel = dxf_path.resolve().relative_to(static_root).as_posix()
    except Exception:
        raise HTTPException(status_code=400, detail="生成的 DXF 不在静态目录下，无法下载")
    dxf_url = f"/static/{rel}"
    return UploadImageConvertedResponse(
        status="converted",
        dxf_file_path=str(dxf_path),
        dxf_url=dxf_url,
        svg_preview=svg_preview,
        session_id=session_id,
    )


@router.post("/modify", response_model=ModifyCADResponse)
def modify(req: ModifyCADRequest, current_user: User = Depends(get_current_user)):
    svg_preview, _ = modify_cad_structure(dxf_file_path=req.dxf_file_path, user_prompt=req.user_prompt)
    return ModifyCADResponse(status="success", svg_preview=svg_preview)

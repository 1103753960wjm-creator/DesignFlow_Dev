# 文件位置: backend/app/api/v1/endpoints/design.py
import json
import os
import shutil
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.deps import get_current_user
from app.models.user import User
from app.services.blender_svc import mock_generate_whitebox
from app.services.comfy_client import mock_generate_gallery
from app.services.storage_service import decrypt_bytes, encrypt_bytes, read_file_bytes, write_file_bytes
from app.worker.tasks import generate_3d_assets

router = APIRouter()


class DesignGenerateRequest(BaseModel):
    source_url: str | None = Field(default=None, description="上传后的素材 URL（图片/CAD）")
    room_type: str = Field(default="客厅", description="空间类型，例如：客厅/卧室/厨房/卫生间/全屋")
    style: str = Field(default="现代简约", description="设计风格，例如：现代简约/奶油风/原木风/新中式")
    area_sqm: float | None = Field(default=None, ge=0, description="面积（平方米）")
    requirements: str | None = Field(default=None, description="额外需求，例如：收纳/动线/预算/家庭成员等")
    output: Literal["plan"] = Field(default="plan", description="当前仅支持输出设计方案文本")


class DesignGenerateResponse(BaseModel):
    provider: str
    plan_markdown: str
    sd_prompt: str
    warnings: list[str] = []


class WhiteboxRequest(BaseModel):
    filename: str | None = Field(default=None, description="上传接口返回的 filename")
    source_url: str | None = Field(default=None, description="上传接口返回的 url")


class WhiteboxResponse(BaseModel):
    whitebox_url: str
    depth_url: str


class GalleryRequest(BaseModel):
    whitebox_url: str = Field(..., description="白模 URL")
    depth_url: str = Field(..., description="深度图 URL")
    prompt: str = Field(default="", description="提示词")


class GalleryResponse(BaseModel):
    images: list[str]


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[4]


class ProcessCadResponse(BaseModel):
    task_id: str
    status: Literal["processing", "done"]
    output_dir: str | None = None
    model_obj_url: str | None = None
    depth_urls: dict[str, str] | None = None


def _call_openai_compatible_chat(
    *,
    url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    temperature: float = 0.4,
    timeout_s: int = 60,
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"大模型调用失败: {e}")

    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        raise HTTPException(status_code=502, detail=f"大模型响应解析失败: {data}")


def _call_ollama_chat(
    *,
    model: str,
    messages: list[dict],
    temperature: float = 0.4,
    timeout_s: int = 60,
    base_url: str = "http://127.0.0.1:11434",
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "options": {"temperature": temperature},
        "stream": False,
    }

    req = urllib.request.Request(
        url=f"{base_url.rstrip('/')}/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama 调用失败: {e}")

    try:
        return data["message"]["content"]
    except Exception:
        raise HTTPException(status_code=502, detail=f"Ollama 响应解析失败: {data}")


def _generate_plan_with_llm(req: DesignGenerateRequest) -> DesignGenerateResponse:
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    warnings: list[str] = []

    source_text = req.source_url or "未提供"
    area_text = f"{req.area_sqm}㎡" if req.area_sqm is not None else "未提供"
    requirements_text = req.requirements or "无"

    system = (
        "你是资深室内设计师与施工图审查顾问。"
        "请用中文输出，结构清晰，可直接给用户执行。"
        "不要臆测尺寸，缺失信息请明确标注“需补充”。"
    )
    user = (
        f"请基于以下信息输出一份室内设计方案：\n"
        f"- 空间类型：{req.room_type}\n"
        f"- 风格：{req.style}\n"
        f"- 面积：{area_text}\n"
        f"- 参考素材 URL：{source_text}\n"
        f"- 额外需求：{requirements_text}\n\n"
        "输出要求：\n"
        "1) 一段总览（100-200字）\n"
        "2) 功能分区与动线（要点列表）\n"
        "3) 主材/配色/灯光建议（要点列表）\n"
        "4) 家具软装清单（分区列出）\n"
        "5) 可落地的预算分配建议（区间）\n"
        "6) 需要用户补充的信息清单\n"
        "7) 最后给出一条适合 Stable Diffusion 的英文提示词（prompt）\n"
    )
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]

    if provider in ("", "none"):
        warnings.append("未配置大模型（LLM_PROVIDER/KEY），当前返回示例方案。")
        plan_markdown = (
            f"## 方案总览\n"
            f"为{req.room_type}提供{req.style}方向的落地方案（面积：{area_text}）。\n\n"
            f"## 功能分区与动线\n"
            f"- 需补充：户型尺寸/开窗与承重墙位置\n\n"
            f"## 主材/配色/灯光建议\n"
            f"- 主色：米白/浅灰，点缀：木色\n\n"
            f"## 家具软装清单\n"
            f"- 需补充：家庭成员、收纳需求、预算上限\n\n"
            f"## 预算分配建议\n"
            f"- 硬装 45%-55%，软装 20%-30%，家电 15%-25%\n\n"
            f"## 需要补充的信息\n"
            f"- 房间尺寸、层高、采光方向、是否有中央空调/地暖\n"
        )
        sd_prompt = (
            f"{req.style} {req.room_type}, photorealistic interior design, soft lighting, "
            f"clean layout, high detail, 4k"
        )
        return DesignGenerateResponse(
            provider="none",
            plan_markdown=plan_markdown,
            sd_prompt=sd_prompt,
            warnings=warnings,
        )

    if provider in ("deepseek", "deepseek-chat"):
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise HTTPException(status_code=500, detail="缺少 DEEPSEEK_API_KEY")
        content = _call_openai_compatible_chat(
            url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions"),
            api_key=api_key,
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            messages=messages,
        )
        return DesignGenerateResponse(provider="deepseek", plan_markdown=content, sd_prompt="", warnings=warnings)

    if provider in ("qwen", "dashscope"):
        api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        if not api_key:
            raise HTTPException(status_code=500, detail="缺少 DASHSCOPE_API_KEY")
        content = _call_openai_compatible_chat(
            url=os.getenv(
                "DASHSCOPE_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            ),
            api_key=api_key,
            model=os.getenv("QWEN_MODEL", "qwen-plus"),
            messages=messages,
        )
        return DesignGenerateResponse(provider="qwen", plan_markdown=content, sd_prompt="", warnings=warnings)

    if provider in ("ollama",):
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
        content = _call_ollama_chat(model=model, messages=messages)
        warnings.append("本地模型效果与速度依赖机器与模型量化。")
        return DesignGenerateResponse(provider="ollama", plan_markdown=content, sd_prompt="", warnings=warnings)

    raise HTTPException(status_code=500, detail=f"不支持的 LLM_PROVIDER: {provider}")


@router.post("/upload", summary="上传设计素材")
def upload_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    接收前端上传的文件，保存到服务器本地
    """
    # 1. 检查文件类型 (安全起见，只允许图片和CAD)
    allowed_types = ["image/jpeg", "image/png", "application/acad", "image/vnd.dxf"]
    # 简单的后缀检查
    filename = file.filename.lower()
    if not any(filename.endswith(ext) for ext in ['.jpg', '.png', '.jpeg', '.dxf', '.dwg']):
         raise HTTPException(status_code=400, detail="不支持的文件格式")

    # 2. 生成一个唯一的文件名 (防止文件名冲突)
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
        "url": f"{base_url}/api/v1/design/cad/{unique_filename}" if is_cad else f"{base_url}/static/uploads/{unique_filename}",
        "encrypted": is_cad,
        "owner": str(current_user.id),
        "msg": "上传成功"
    }


@router.post("/process-cad", response_model=ProcessCadResponse, summary="处理 CAD（异步）")
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
        return ProcessCadResponse(
            task_id=result.id,
            status="done",
            output_dir=str(job_dir),
            model_obj_url=f"{base}/model.obj",
            depth_urls={
                "top": f"{base}/depth_top.png",
                "main": f"{base}/depth_main.png",
                "wall": f"{base}/depth_wall.png",
                "0": f"{base}/depth_0.png",
            },
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
            depth_urls={
                "top": f"{base}/depth_top.png",
                "main": f"{base}/depth_main.png",
                "wall": f"{base}/depth_wall.png",
                "0": f"{base}/depth_0.png",
            },
        )


@router.get("/cad/{asset_id}", summary="下载 CAD（解密后返回）")
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


@router.post("/generate", response_model=DesignGenerateResponse, summary="生成室内设计方案（文本）")
def generate_design(req: DesignGenerateRequest, current_user: User = Depends(get_current_user)):
    return _generate_plan_with_llm(req)


@router.post("/whitebox", response_model=WhiteboxResponse, summary="生成白模（Mock）")
def generate_whitebox(req: WhiteboxRequest, request: Request, current_user: User = Depends(get_current_user)):
    base_url = str(request.base_url).rstrip("/")
    result = mock_generate_whitebox(base_url=base_url)
    return WhiteboxResponse(whitebox_url=result.whitebox_url, depth_url=result.depth_url)


@router.post("/gallery", response_model=GalleryResponse, summary="生成画廊（Mock）")
def generate_gallery(req: GalleryRequest, request: Request, current_user: User = Depends(get_current_user)):
    base_url = str(request.base_url).rstrip("/")
    result = mock_generate_gallery(base_url=base_url, count=6)
    return GalleryResponse(images=result.images)

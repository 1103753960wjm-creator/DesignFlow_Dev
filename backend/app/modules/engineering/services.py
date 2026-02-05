from __future__ import annotations

import os
from pathlib import Path

import ezdxf
from fastapi import HTTPException

from app.modules.engineering.geometry import apply_cad_command, dxf_to_svg_preview
from app.modules.engineering.schemas import CADModificationCommand


def backend_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _normalize_openai_base_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if url.endswith("/chat/completions"):
        url = url[: -len("/chat/completions")]
    return url


def _provider_config() -> tuple[str, str, str]:
    provider = (os.getenv("LLM_PROVIDER", "none") or "none").strip().lower()
    if provider in ("none", ""):
        raise HTTPException(status_code=400, detail="未配置 LLM_PROVIDER（已强制 Instructor 模式）")
    if provider in ("deepseek",):
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise HTTPException(status_code=400, detail="缺少 DEEPSEEK_API_KEY")
        base_url = _normalize_openai_base_url(os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"))
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
        return (provider, api_key, f"{base_url}|{model}")
    if provider in ("qwen", "dashscope"):
        api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        if not api_key:
            raise HTTPException(status_code=400, detail="缺少 DASHSCOPE_API_KEY")
        base_url = _normalize_openai_base_url(
            os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        )
        model = os.getenv("QWEN_MODEL", "qwen-plus").strip() or "qwen-plus"
        return (provider, api_key, f"{base_url}|{model}")
    if provider in ("ollama",):
        base_url = _normalize_openai_base_url(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"))
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct").strip() or "qwen2.5:7b-instruct"
        return (provider, "ollama", f"{base_url}|{model}")
    raise HTTPException(status_code=400, detail=f"不支持的 LLM_PROVIDER: {provider}")

def _parse_with_instructor(user_prompt: str) -> CADModificationCommand:
    if not (user_prompt or "").strip():
        raise HTTPException(status_code=400, detail="user_prompt 不能为空")
    _, api_key, packed = _provider_config()
    base_url, model = packed.split("|", 1)
    try:
        import instructor
        from openai import OpenAI
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"LLM 依赖缺失: {e}")

    system = (
        "你是 CAD 修改指令解析器。请把用户自然语言解析为结构化命令。\n"
        "规则：所有长度单位统一为 mm。MOVE_WALL 输出 value(mm) 并尽量给出 delta_x/delta_y；"
        "DELETE_ITEM 输出 target_description；RESIZE_ROOM 输出 axis(x/y) 与 value(mm)。\n"
        "仅输出符合 schema 的结构化结果。"
    )
    client = instructor.from_openai(OpenAI(api_key=api_key, base_url=base_url))
    try:
        return client.chat.completions.create(
            model=model,
            response_model=CADModificationCommand,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            max_retries=2,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"LLM 解析失败: {e}")


def parse_cad_modification_command(user_prompt: str) -> CADModificationCommand:
    return _parse_with_instructor(user_prompt)


def _resolve_dxf_path(dxf_file_path: str) -> Path:
    p = Path(str(dxf_file_path)).expanduser()
    if not p.is_absolute():
        p = (backend_root() / p).resolve()
    else:
        p = p.resolve()
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=400, detail="DXF 文件不存在")
    if p.suffix.lower() != ".dxf":
        raise HTTPException(status_code=400, detail="仅支持 .dxf 文件")
    return p


def modify_cad_structure(dxf_file_path: str, user_prompt: str) -> tuple[str, str]:
    src_path = _resolve_dxf_path(dxf_file_path)
    try:
        cmd = parse_cad_modification_command(user_prompt)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"LLM 指令解析失败: {e}")
    try:
        doc = ezdxf.readfile(str(src_path))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"DXF 读取失败: {e}")
    try:
        apply_cad_command(doc, cmd)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"几何操作失败: {e}")
    out_path = src_path.with_name(f"{src_path.stem}_modified{src_path.suffix}")
    try:
        doc.saveas(str(out_path))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"DXF 保存失败: {e}")
    svg_preview = dxf_to_svg_preview(doc)
    return (svg_preview, str(out_path))


def get_svg_preview(dxf_file_path: str) -> str:
    src_path = _resolve_dxf_path(dxf_file_path)
    try:
        doc = ezdxf.readfile(str(src_path))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"DXF 读取失败: {e}")
    return dxf_to_svg_preview(doc)

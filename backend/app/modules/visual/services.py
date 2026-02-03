import json
import os
import urllib.request
from pathlib import Path
from dataclasses import dataclass
from fastapi import HTTPException
from app.core.camera_views import CAMERA_VIEW_KEYS_DEFAULT, LEGACY_DEPTH_KEY, depth_filename


def backend_root() -> Path:
    return Path(__file__).resolve().parents[4]


def build_depth_urls(*, base: str, output_dir: Path) -> dict[str, str] | None:
    urls: dict[str, str] = {}
    for key in [*CAMERA_VIEW_KEYS_DEFAULT, LEGACY_DEPTH_KEY]:
        filename = depth_filename(key)
        if (output_dir / filename).exists():
            urls[key] = f"{base}/{filename}"
    return urls or None


def call_openai_compatible_chat(
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


def call_ollama_chat(
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


def generate_plan_with_llm(req) -> dict:
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
        return {"provider": "none", "plan_markdown": plan_markdown, "sd_prompt": sd_prompt, "warnings": warnings}
    if provider in ("deepseek", "deepseek-chat"):
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise HTTPException(status_code=500, detail="缺少 DEEPSEEK_API_KEY")
        content = call_openai_compatible_chat(
            url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions"),
            api_key=api_key,
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            messages=messages,
        )
        return {"provider": "deepseek", "plan_markdown": content, "sd_prompt": "", "warnings": warnings}
    if provider in ("qwen", "dashscope"):
        api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        if not api_key:
            raise HTTPException(status_code=500, detail="缺少 DASHSCOPE_API_KEY")
        content = call_openai_compatible_chat(
            url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"),
            api_key=api_key,
            model=os.getenv("QWEN_MODEL", "qwen-plus"),
            messages=messages,
        )
        return {"provider": "qwen", "plan_markdown": content, "sd_prompt": "", "warnings": warnings}
    if provider in ("ollama",):
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
        content = call_ollama_chat(model=model, messages=messages)
        warnings.append("本地模型效果与速度依赖机器与模型量化。")
        return {"provider": "ollama", "plan_markdown": content, "sd_prompt": "", "warnings": warnings}
    raise HTTPException(status_code=500, detail=f"不支持的 LLM_PROVIDER: {provider}")


@dataclass(frozen=True)
class WhiteboxResult:
    whitebox_url: str
    depth_url: str


def mock_generate_whitebox(*, base_url: str) -> WhiteboxResult:
    base = base_url.rstrip("/")
    return WhiteboxResult(
        whitebox_url=f"{base}/static/mock/whitebox.obj",
        depth_url=f"{base}/static/mock/depth.png",
    )


@dataclass(frozen=True)
class GalleryResult:
    images: list[str]


def mock_generate_gallery(*, base_url: str, count: int = 6) -> GalleryResult:
    base = base_url.rstrip("/")
    pool_size = 6
    images = [f"{base}/static/mock/gallery/g{((i - 1) % pool_size) + 1}.png" for i in range(1, max(1, count) + 1)]
    return GalleryResult(images=images)

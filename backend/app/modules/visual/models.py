from typing import Literal
from pydantic import BaseModel, Field


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
    strength: float | None = Field(default=None, ge=0, le=1, description="控制强度")
    cameras: list[str] | None = Field(default=None, description="机位列表（viewKey）")
    depth_urls: dict[str, str] | None = Field(default=None, description="多机位深度图 URL 字典")


class GalleryResponse(BaseModel):
    images: list[str]
    views: list[str] | None = None


class ProcessCadResponse(BaseModel):
    task_id: str
    status: Literal["processing", "done"]
    output_dir: str | None = None
    model_obj_url: str | None = None
    depth_urls: dict[str, str] | None = None

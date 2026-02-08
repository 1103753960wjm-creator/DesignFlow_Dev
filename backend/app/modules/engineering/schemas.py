from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class CADActionType(str, Enum):
    MOVE_WALL = "MOVE_WALL"
    RESIZE_ROOM = "RESIZE_ROOM"
    DELETE_ITEM = "DELETE_ITEM"


class CADModificationCommand(BaseModel):
    action_type: CADActionType = Field(description="CAD 修改操作类型")
    target_description: str = Field(description="目标描述，例如：客厅的南墙")
    value: float | None = Field(default=None, description="操作参数值（统一单位：mm，例如 500）")
    delta_x: float | None = Field(default=None, description="X 方向偏移量（单位：mm，可选）")
    delta_y: float | None = Field(default=None, description="Y 方向偏移量（单位：mm，可选）")
    axis: str | None = Field(default=None, description="缩放/调整轴，x 或 y")

    @field_validator("target_description")
    @classmethod
    def _validate_target_description(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("target_description 不能为空")
        return v

    @field_validator("axis")
    @classmethod
    def _validate_axis(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().lower()
        if v not in ("x", "y"):
            raise ValueError("axis 仅支持 x 或 y")
        return v


class ModifyCADRequest(BaseModel):
    dxf_file_path: str = Field(description="服务端可访问的 DXF 文件路径")
    user_prompt: str = Field(description="自然语言修改指令")


class ModifyCADResponse(BaseModel):
    status: str = Field(description="处理状态", examples=["success"])
    svg_preview: str = Field(description="修改后的 SVG 预览字符串")


class UploadCadResponse(BaseModel):
    status: str = Field(description="处理状态", examples=["success"])
    dxf_file_path: str = Field(description="服务端保存的 DXF 文件路径")
    svg_preview: str = Field(description="初始 SVG 预览字符串")


class UploadImageConvertedResponse(BaseModel):
    status: str = Field(description="处理状态", examples=["converted"])
    dxf_file_path: str = Field(description="服务端保存的 DXF 文件路径（用于后续 modify）")
    dxf_url: str = Field(description="可下载的 DXF 相对/绝对 URL（用于浏览器下载）")
    svg_preview: str = Field(description="转换后的 SVG 预览字符串")
    session_id: str = Field(description="本次转换会话 ID")
    debug_images: list[str] = Field(default_factory=list, description="算法调试图片 URL 列表")

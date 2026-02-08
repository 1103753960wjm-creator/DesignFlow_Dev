# DesignFlow_Dev

## Backend（Python）

### 环境准备

在项目根目录（`E:\DesignFlow_Dev`）：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m ensurepip --upgrade
.\.venv\Scripts\python -m pip install -r backend/requirements.txt
.\.venv\Scripts\python -m pip install -r backend/requirements-dev.txt
```

### 运行测试

```powershell
cd backend
..\.\.venv\Scripts\python -m pytest -q
```

### 图片转 DXF（Image→CAD）

默认转换入口：`POST /api/v1/engineering/upload/image`

可用环境变量：

- `IMAGE_DXF_USE_LOCAL_SEG`：是否优先使用本地语义分割矢量化（`1/0`，默认 `1`）
- `IMAGE_DXF_MM_PER_PX`：像素到毫米比例（默认 `10.0`）
- `IMAGE_DXF_WALL_MIN_AREA_PX`：WALL 轮廓最小面积阈值（默认 `800`）
- `IMAGE_DXF_WALL_EPS_FRAC`：WALL 轮廓拟合精度（默认 `0.01`）

本地分割推理验证脚本：

```powershell
.\.venv\Scripts\python backend/scripts/test_local_inference.py
```


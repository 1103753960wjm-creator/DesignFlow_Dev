# 文件位置: backend/main.py
import sys
import os

# ==========================================
# 1. 路径修复 (必须放在最前面)
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# ==========================================
# 2. 导入必要的库
# ==========================================
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles          # 👈 负责静态文件
from fastapi.middleware.cors import CORSMiddleware   # 👈 负责跨域 (刚才报错就是因为缺了这个!)

from app.core.config import settings
from app.db.session import engine, Base
from app.api.v1.api import api_router

# ==========================================
# 3. 自动建表与初始化
# ==========================================
print("🔄 正在检查数据库连接...")
if os.getenv("RESET_DB", "").strip().lower() in ("1", "true", "yes"):
    Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("✅ 数据库表结构同步完成!")

app = FastAPI(
    title=settings.PROJECT_NAME if 'settings' in locals() else "Structura AI API",
    openapi_url="/api/v1/openapi.json"
)

# ==========================================
# 4. 配置 CORS (跨域)
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 5. 挂载静态文件目录 (存放上传图片)
# ==========================================
static_dir = os.path.join(current_dir, "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir) # 自动创建文件夹
# 访问 http://127.0.0.1:8002/static/xxx.jpg -> 指向 backend/static/xxx.jpg
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ==========================================
# 6. 挂载业务路由
# ==========================================
app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    # 统一使用 8002 端口
    uvicorn.run(app, host="127.0.0.1", port=8002)

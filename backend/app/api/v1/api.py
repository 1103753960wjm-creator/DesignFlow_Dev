# 文件位置: backend/app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import auth
from app.api.v1.endpoints import tasks

api_router = APIRouter()

# 把 auth.py 里的接口挂载到 /auth 路径下
# 最终访问地址变成: http://.../api/v1/auth/send-code
api_router.include_router(auth.router, prefix="/auth", tags=["用户认证"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["异步任务"])

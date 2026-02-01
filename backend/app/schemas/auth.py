# 文件位置: backend/app/schemas/auth.py
from pydantic import BaseModel, Field

# 1. 定义“发送验证码”时，前端必须传的数据
class PhoneRequest(BaseModel):
    # Field(...) 表示这个字段是必填的
    phone: str = Field(..., description="用户手机号", example="13800138000")

# 2. 定义“登录”时，前端必须传的数据
class LoginRequest(BaseModel):
    phone: str = Field(..., description="用户手机号")
    code: str = Field(..., description="6位短信验证码", min_length=6, max_length=6)

# 3. 定义“登录成功”后，后端返回的数据
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: str = Field(..., description="邮箱")
    phone: str = Field(..., description="手机号")
    password: str = Field(..., min_length=8, description="密码（至少8位）")
    nickname: str | None = Field(default=None, description="昵称")


class PasswordLoginRequest(BaseModel):
    email: str = Field(..., description="邮箱")
    password: str = Field(..., description="密码")


class UserOut(BaseModel):
    id: str
    email: str
    nickname: str | None = None

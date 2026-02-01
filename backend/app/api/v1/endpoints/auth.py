# 文件位置: backend/app/api/v1/endpoints/auth.py
import random
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.schemas.auth import (
    LoginRequest,
    PasswordLoginRequest,
    PhoneRequest,
    RegisterRequest,
    Token,
    UserOut,
)
from app.db.session import get_db
from app.models.user import User

router = APIRouter()

# 模拟短信数据库 (跟昨天一样)
fake_sms_db = {}

# 发送验证码接口 (跟昨天一样，没变)
@router.post("/send-code", summary="1. 发送短信验证码")
def send_verification_code(request: PhoneRequest):
    phone = request.phone
    code = str(random.randint(100000, 999999))
    fake_sms_db[phone] = code
    print(f"📧 [模拟短信] 发送给 {phone}: {code}")
    return {"msg": "验证码发送成功", "debug_code": code}

@router.post("/register", response_model=Token, summary="注册")
def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.email == request.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="邮箱已注册")

    phone_exists = db.query(User).filter(User.phone == request.phone).first()
    if phone_exists:
        raise HTTPException(status_code=400, detail="手机号已注册")

    user = User(
        email=request.email,
        phone=request.phone,
        nickname=request.nickname,
        password_hash=hash_password(request.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login", response_model=Token, summary="登录（密码）")
def login_with_password(request: PasswordLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="账号或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="用户已被禁用")
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=400, detail="账号或密码错误")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login-code", response_model=Token, summary="登录（短信验证码，兼容旧版）")
def login_with_code(request: LoginRequest, db: Session = Depends(get_db)):
    phone = request.phone
    input_code = request.code

    saved_code = fake_sms_db.get(phone)
    if not saved_code:
        raise HTTPException(status_code=400, detail="请先获取验证码")
    if saved_code != input_code:
        raise HTTPException(status_code=400, detail="验证码错误")
    del fake_sms_db[phone]

    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        user = User(
            email=f"{phone}@local.structura",
            phone=phone,
            nickname=f"用户{phone[-4:]}",
            password_hash=hash_password(saved_code + phone),
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut, summary="获取当前用户")
def get_me(current_user: User = Depends(get_current_user)):
    return UserOut(id=str(current_user.id), email=current_user.email, nickname=current_user.nickname)

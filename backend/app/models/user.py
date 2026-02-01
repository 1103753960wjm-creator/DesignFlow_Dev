# 文件位置: backend/app/models/user.py
import uuid

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base

class User(Base):
    # 表名
    __tablename__ = "users"

    # 列定义
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False, comment="邮箱")
    phone = Column(String, unique=True, index=True, nullable=True, comment="手机号")
    nickname = Column(String, nullable=True, comment="昵称")
    password_hash = Column(String, nullable=False, comment="密码哈希")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否启用")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

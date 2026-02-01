# 文件位置: backend/app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# 1. 创建数据库引擎 (这是连接的核心)
engine = create_engine(settings.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)

# 2. 创建会话工厂 (每次请求数据库都会从这里拿一个连接)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. 创建模型基类 (所有的表都要继承这个类)
Base = declarative_base()

# 4. 这是一个工具函数，给 API 用的
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
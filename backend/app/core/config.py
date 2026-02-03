# 文件位置: backend/app/core/config.py
import os


class Settings:
    PROJECT_NAME: str = "Structura AI API"
    API_V1_STR: str = "/api/v1"

    # 数据库连接地址
    # 格式: postgresql://用户名:密码@地址:端口/数据库名
    # ⚠️⚠️⚠️ 请务必把下面的 YOUR_PASSWORD 换成你安装 PostgreSQL 时设置的密码 (比如 123456)
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        "postgresql://postgres:123456@localhost:5432/structura_db",
    )

    # 这是加密 Token 用的密钥，真实项目中要是随机的一长串乱码，绝对不能告诉别人！
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-it-in-production")
    # Token 有效期 (分钟)，这里设为 7 天 (60 * 24 * 7)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7


settings = Settings()

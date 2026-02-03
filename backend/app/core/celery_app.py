from celery import Celery

# 1. 定义中间人 (Broker) 和 结果存储 (Backend) 的地址
# 都是指向我们要运行的 Redis
redis_url = "redis://127.0.0.1:6379/0"

celery_app = Celery("structura_worker", broker=redis_url, backend=redis_url)

# 3. 配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
)

# 4. 自动发现任务
# Celery 会自动去这些文件夹里找有没有标了 @task 的函数
# 我们明天会在 worker 文件夹里写具体的 Blender 任务
celery_app.conf.imports = ["app.worker.tasks"]

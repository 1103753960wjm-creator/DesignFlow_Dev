from pathlib import Path

from fastapi import APIRouter, Request
from celery.result import AsyncResult
from pydantic import BaseModel, Field
from app.worker.tasks import mock_rendering_task

router = APIRouter()


class TaskGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1)


@router.post("/generate", summary="1. 提交生成任务")
def submit_generation_task(payload: TaskGenerateRequest):
    """
    用户提交一个 Prompt，后端不等待，直接返回任务 ID
    """
    # 关键点：使用 .delay() 方法，这会把任务扔进 Redis，不阻塞当前线程
    task = mock_rendering_task.delay(payload.prompt)
    
    return {
        "task_id": task.id,
        "msg": "任务已提交后台，请使用 task_id 查询进度",
        "status_url": f"/api/v1/tasks/status/{task.id}"
    }

@router.get("/status/{task_id}", summary="2. 查询任务进度")
def get_task_status(task_id: str, request: Request):
    """
    前端轮询这个接口，查看任务是不是做完了
    """
    # 根据 ID 去 Redis 里查状态
    task_result = AsyncResult(task_id)
    
    response: dict = {
        "task_id": task_id,
        "status": task_result.status,
        "result": None,
    }

    # 如果任务正在进行中 (我们在 task.py 里写的 update_state)
    if task_result.state == "PROGRESS":
        try:
            response["progress"] = task_result.info.get("progress", 0)
        except Exception:
            response["progress"] = 0
    
    # 如果任务成功完成
    if task_result.successful():
        response["result"] = task_result.result
        if isinstance(task_result.result, dict) and task_result.result.get("output_dir"):
            out_dir = Path(str(task_result.result["output_dir"]))
            job_id = out_dir.name
            base_url = str(request.base_url).rstrip("/")
            base = f"{base_url}/static/processed/{job_id}"
            response["assets"] = {
                "model_obj_url": f"{base}/model.obj",
                "depth_urls": {
                    "top": f"{base}/depth_top.png",
                    "main": f"{base}/depth_main.png",
                    "wall": f"{base}/depth_wall.png",
                    "0": f"{base}/depth_0.png",
                },
            }
        
    return response


@router.get("/{task_id}", summary="2. 查询任务进度（简化路径）")
def get_task_status_short(task_id: str, request: Request):
    return get_task_status(task_id, request)
    

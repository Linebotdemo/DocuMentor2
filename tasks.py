import os
from celery import Celery

celery = Celery(
    "tasks",
    broker=os.getenv("REDIS_URL"),
    backend=os.getenv("REDIS_URL")
)

@celery.task
def transcribe_video_task(video_url, video_id):
    # Ngrok経由でWhisperマイクロサービスを叩く処理
    pass

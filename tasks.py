# tasks.py

import os
from celery import Celery
from dotenv import load_dotenv
import requests

# 環境変数の読み込み
load_dotenv()

# REDIS_URLは redis:// 付きのフルURLであることを前提
REDIS_URL = os.getenv("REDIS_URL")
WHISPER_API_URL = os.getenv("WHISPER_API_URL")

print("🔧 REDIS_URL =", REDIS_URL)

# Celeryインスタンス作成（backendは conf で別途設定する）
celery = Celery("documentor_worker", broker=REDIS_URL)
celery.conf.update(
    result_backend=REDIS_URL,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
)

@celery.task
def transcribe_video_task(video_url, video_id):
    print(f"🎬 Transcribing video {video_id} from {video_url}")
    try:
        response = requests.post(WHISPER_API_URL, json={"video_url": video_url})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        return {"error": str(e)}

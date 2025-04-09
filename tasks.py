# tasks.py

import os
import requests
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# RedisとWhisperの設定
REDIS_URL = os.getenv("REDIS_URL")
WHISPER_API_URL = os.getenv("WHISPER_API_URL")

print("🔧 REDIS_URL =", REDIS_URL)

# Celeryアプリ作成
celery = Celery("documentor_worker")

# brokerとbackendを明示的に設定
celery.conf.broker_url = REDIS_URL
celery.conf.result_backend = REDIS_URL   # ← ここも元に戻してOK、redisモジュールがインストールされたので動くはず！

# タスク定義
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

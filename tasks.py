# tasks.py

import os
import json
import requests
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# RedisとWhisperの設定
REDIS_URL = os.getenv("REDIS_URL")
WHISPER_API_URL = os.getenv("WHISPER_API_URL")

print("🔧 REDIS_URL =", REDIS_URL)
print("📡 WHISPER_API_URL =", WHISPER_API_URL)

# Celeryアプリ作成
celery = Celery("documentor_worker")

# brokerとbackendを設定
celery.conf.broker_url = REDIS_URL
celery.conf.result_backend = REDIS_URL

# タスク定義
@celery.task(bind=True, ignore_result=False)
def transcribe_video_task(self, video_url, video_id):
    print(f"🎬 Transcribing video {video_id} from {video_url}")
    try:
        response = requests.post(
            WHISPER_API_URL,
            json={"video_url": video_url},
            timeout=60  # 長めに取る
        )
        response.raise_for_status()
        result = response.json()

        print(f"✅ Transcription done for video {video_id}: {result}")
        return json.dumps(result)

    except requests.exceptions.RequestException as e:
        print(f"❌ RequestException: {e}")
        return json.dumps({"error": f"Request failed: {str(e)}"})

    except Exception as e:
        print(f"🔥 Unexpected error: {e}")
        return json.dumps({"error": f"Unexpected error: {str(e)}"})
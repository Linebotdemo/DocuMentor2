import os
from celery import Celery
import requests
from dotenv import load_dotenv

# .env 読み込み
load_dotenv()

# 環境変数から設定取得
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
WHISPER_API_URL = os.getenv("WHISPER_API_URL", "http://localhost:5000/transcribe")

# Celery設定
celery = Celery("documentor_worker", broker=REDIS_URL, backend=REDIS_URL)

# タスク定義
@celery.task
def transcribe_video_task(video_url, video_id):
    print(f"🎬 Transcribing video {video_id} from {video_url}")
    try:
        response = requests.post(WHISPER_API_URL, json={"video_url": video_url})
        response.raise_for_status()
        result = response.json()
        print(f"✅ Transcription done for video {video_id}")
        return result
    except Exception as e:
        print(f"❌ Error transcribing video {video_id}: {e}")
        return {"error": str(e)}

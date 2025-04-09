# tasks.py

import os
import requests
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

redis_url = os.getenv("REDIS_URL")
whisper_url = os.getenv("WHISPER_API_URL")

celery = Celery("documentor_worker", broker=redis_url)
celery.conf.result_backend = redis_url  # ✅ ここ重要！

@celery.task
def transcribe_video_task(video_url, video_id):
    print(f"🎬 Transcribing video {video_id} from {video_url}")
    try:
        response = requests.post(whisper_url, json={"video_url": video_url})
        response.raise_for_status()
        result = response.json()
        print(f"✅ Transcription done for video {video_id}")
        return result
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e)}

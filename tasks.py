# tasks.py
from dotenv import load_dotenv
load_dotenv()

import os
from celery import Celery



load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
WHISPER_API_URL = os.getenv("WHISPER_API_URL", "http://localhost:5000/transcribe")
celery = Celery("worker", broker=REDIS_URL, backend=REDIS_URL)

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

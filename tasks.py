import os
import json
import requests
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
WHISPER_API_URL = os.getenv("WHISPER_API_URL")

print("🔧 REDIS_URL =", REDIS_URL)
print("📡 WHISPER_API_URL =", WHISPER_API_URL)

celery = Celery("documentor_worker")
celery.conf.broker_url = REDIS_URL
celery.conf.result_backend = REDIS_URL

@celery.task(bind=True, ignore_result=False, name="app.transcribe_video_task")
def transcribe_video_task(self, video_url, video_id):
    print(f"🎬 Transcribing video {video_id} from {video_url}")
    try:
        response = requests.post(
            WHISPER_API_URL,
            json={"video_url": video_url},
            timeout=800
        )
        response.raise_for_status()
        result = response.json()
        text = result.get("text", "")

        print(f"✅ Transcription done for video {video_id}")

        # 🚫 DB更新はせず、Flask側に戻す
        return json.dumps({
            "video_id": video_id,
            "whisper_text": text
        })

    except requests.exceptions.RequestException as e:
        print(f"❌ RequestException: {e}")
        return json.dumps({
            "video_id": video_id,
            "error": f"Request failed: {str(e)}"
        })

    except Exception as e:
        print(f"🔥 Unexpected error: {e}")
        return json.dumps({
            "video_id": video_id,
            "error": f"Unexpected error: {str(e)}"
        })

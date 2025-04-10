import os
import json
import requests
from celery import Celery
from dotenv import load_dotenv

# FlaskのDBとモデルを使う準備
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import db, Video  # ← 追加

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

        print(f"✅ Transcription done for video {video_id}, saving to DB")

        # ✅ DBに保存
        video = Video.query.get(video_id)
        if video:
            video.whisper_text = text
            db.session.commit()
        else:
            print(f"❗Video ID {video_id} が見つかりませんでした")

        return json.dumps(result)

    except requests.exceptions.RequestException as e:
        print(f"❌ RequestException: {e}")
        return json.dumps({"error": f"Request failed: {str(e)}"})

    except Exception as e:
        print(f"🔥 Unexpected error: {e}")
        return json.dumps({"error": f"Unexpected error: {str(e)}"})

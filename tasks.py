# tasks.py（Railway側）
import os
import json
import requests
from celery import Celery
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Video  # モデルは別ファイルに分けて読み込む

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
WHISPER_API_URL = os.getenv("WHISPER_API_URL")
DATABASE_URL = os.getenv("FLASK_DATABASE_URI")  # RenderのDBと同じ

celery = Celery("documentor_worker")
celery.conf.broker_url = REDIS_URL
celery.conf.result_backend = REDIS_URL

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

@celery.task(bind=True, ignore_result=False, name="app.transcribe_video_task")
def transcribe_video_task(self, video_url, video_id):
    print(f"🎬 Transcribing video {video_id}")
    session = Session()
    try:
        response = requests.post(WHISPER_API_URL, json={"video_url": video_url}, timeout=800)
        response.raise_for_status()
        result = response.json()
        text = result.get("text", "")

        # DBに反映
        video = session.query(Video).get(video_id)
        if video:
            video.whisper_text = text
            session.commit()
            print("✅ 文字起こしをDBに保存完了")
        else:
            print("❗動画が見つかりませんでした")

        return result
    except Exception as e:
        session.rollback()
        print(f"🔥 Error: {e}")
        return {"error": str(e)}
    finally:
        session.close()

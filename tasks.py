import os
import requests
from celery import Celery
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Video  # Quiz はRenderにあるため不要


# .env 読み込み
load_dotenv()

# 環境変数から設定取得
REDIS_URL = os.getenv("REDIS_URL")
WHISPER_API_URL = os.getenv("WHISPER_API_URL")
DATABASE_URL = os.getenv("FLASK_DATABASE_URI")

# Celery設定
celery = Celery("documentor_worker")
celery.conf.broker_url = REDIS_URL
celery.conf.result_backend = REDIS_URL

# DB設定
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

@celery.task(bind=True, ignore_result=False, name="app.transcribe_video_task")
def transcribe_video_task(self, video_url, video_id):
    print(f"🎬 Transcribing video {video_id}")
    session = Session()
    try:
        video = session.query(Video).get(video_id)
        if not video:
            print(f"❗動画が見つかりません（video_id: {video_id}）")
            return {"error": "video not found"}

        response = requests.post(WHISPER_API_URL, json={"video_url": video_url}, timeout=800)
        response.raise_for_status()
        result = response.json()
        video.whisper_text = result.get("text", "")

        # Whisper結果だけ保存、要約・クイズ生成はRender側でやる
        session.commit()
        print("✅ Whisper結果をDBに保存しました")
        return result

    except Exception as e:
        session.rollback()
        print(f"🔥 Error: {e}")
        return {"error": str(e)}

    finally:
        session.close()

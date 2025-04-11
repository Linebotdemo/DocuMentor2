import os
import json
import requests
from celery import Celery
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Video  # models.py で SQLAlchemy モデルが定義されている前提

# .env 読み込み
load_dotenv()

# 環境変数から設定取得
FLASK_API_URL = os.getenv("FLASK_API_URL")  # Webhookを使う場合用（使ってない場合でも定義してOK）
REDIS_URL = os.getenv("REDIS_URL")
WHISPER_API_URL = os.getenv("WHISPER_API_URL")
DATABASE_URL = os.getenv("FLASK_DATABASE_URI")  # Renderと同じDB URI（PostgreSQL）

# Celeryアプリ設定
celery = Celery("documentor_worker")
celery.conf.broker_url = REDIS_URL
celery.conf.result_backend = REDIS_URL

# SQLAlchemyエンジンとセッション作成
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

@celery.task(bind=True, ignore_result=False, name="app.transcribe_video_task")
def transcribe_video_task(self, video_url, video_id):
    print(f"🎬 Transcribing video {video_id}")
    session = Session()
    try:
        # Whisper APIへ動画URLを送信
        response = requests.post(WHISPER_API_URL, json={"video_url": video_url}, timeout=800)
        response.raise_for_status()
        result = response.json()
        text = result.get("text", "")

        print(f"✅ 取得した文字起こし: {text[:100]}...")

        # DBに保存
        video = session.query(Video).get(video_id)
        if video:
            video.whisper_text = text
            session.commit()
            print("✅ 文字起こしをDBに保存完了")
        else:
            print("❗動画が見つかりませんでした（video_id: {video_id}）")

        return result

    except Exception as e:
        session.rollback()
        print(f"🔥 Error: {e}")
        return {"error": str(e)}

    finally:
        session.close()
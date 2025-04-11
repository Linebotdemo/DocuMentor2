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
        video = session.query(Video).get(video_id)
        if not video:
            print(f"❗動画が見つかりません（video_id: {video_id}）")
            return {"error": "video not found"}

        # 1. まずはWhisperでテキストを取得して保存（既存コード）
        response = requests.post(WHISPER_API_URL, json={"video_url": video_url}, timeout=800)
        response.raise_for_status()
        result = response.json()
        video.whisper_text = result.get("text", "")

        # 2. ↓ ここでGPT要約＆クイズ生成
        process_video(video, generation_mode="manual")  # 👈 これ追加！

        session.commit()
        print("✅ 全ての処理完了")
        return result

    except Exception as e:
        session.rollback()
        print(f"🔥 Error: {e}")
        return {"error": str(e)}

    finally:
        session.close()

    finally:
        session.close()
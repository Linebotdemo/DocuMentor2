import os
import json
import requests
from celery import Celery
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Video, Quiz  # Video, Quiz モデルがある前提
from process import process_video  # GPT要約＆クイズ処理を分けているならここ

# .env 読み込み
load_dotenv()

# 環境変数から設定取得
FLASK_API_URL = os.getenv("FLASK_API_URL")
REDIS_URL = os.getenv("REDIS_URL")
WHISPER_API_URL = os.getenv("WHISPER_API_URL")
DATABASE_URL = os.getenv("FLASK_DATABASE_URI")

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

        # Whisper APIへ動画URLを送信
        response = requests.post(WHISPER_API_URL, json={"video_url": video_url}, timeout=800)
        response.raise_for_status()
        result = response.json()
        text = result.get("text", "")
        print(f"✅ 取得した文字起こし: {text[:100]}...")

        # Whisper結果をDBに保存
        video.whisper_text = text

        # GPT要約＋クイズ生成処理
        process_video(video, generation_mode="manual")

        # コミット
        session.commit()
        print("✅ 全ての処理完了")
        return result

    except Exception as e:
        session.rollback()
        print(f"🔥 Error: {e}")
        return {"error": str(e)}

    finally:
        session.close()

# tasks.py
import os
import requests
from celery import Celery
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Video  # ここでは Quiz は不要（Render側で生成されるため）

# 環境変数を読み込む
load_dotenv()

# 環境変数から各種URLを取得
REDIS_URL = os.getenv("REDIS_URL")
WHISPER_API_URL = os.getenv("WHISPER_API_URL")
DATABASE_URL = os.getenv("FLASK_DATABASE_URI")

# Celeryの設定
celery = Celery("documentor_worker", broker=REDIS_URL, backend=REDIS_URL)
celery.conf.broker_url = REDIS_URL
celery.conf.result_backend = REDIS_URL

# DBの設定
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

@celery.task(bind=True, ignore_result=False, name="app.transcribe_video_task")
def transcribe_video_task(self, video_url, video_id):
    print(f"🎬 タスク開始: video_id={video_id}")
    print(f"📡 WHISPER_API_URL = {WHISPER_API_URL}")
    print(f"📤 POST予定: {WHISPER_API_URL} に video_url: {video_url}")

    session = Session()
    try:
        video = session.query(Video).get(video_id)
        if not video:
            print(f"❗動画が見つかりません（video_id: {video_id}）")
            return {"error": "video not found"}

        response = requests.post(
            WHISPER_API_URL,
            json={"video_url": video_url},
            timeout=60
        )

        print(f"📥 ステータス: {response.status_code}")
        print(f"📦 レスポンス本文: {response.text}")

        response.raise_for_status()
        result = response.json()
        video.whisper_text = result.get("text", "")
        session.commit()
        print("✅ 文字起こし完了 & DB保存成功")
        return result

    except Exception as e:
        session.rollback()
        print(f"🔥 Whisper POST中の例外: {e}")
        return {"error": str(e)}
    finally:
        session.close()

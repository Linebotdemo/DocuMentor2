import os
import requests
from celery import Celery
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Video  # QuizはRender側で生成されるので不要

# 環境変数の読み込み
load_dotenv()

# 環境変数から各種設定値を取得
REDIS_URL = os.getenv("REDIS_URL")
WHISPER_API_URL = os.getenv("WHISPER_API_URL")
DATABASE_URL = os.getenv("FLASK_DATABASE_URI")

print(f"[DEBUG] REDIS_URL: {REDIS_URL}", flush=True)
print(f"[DEBUG] WHISPER_API_URL: {WHISPER_API_URL}", flush=True)
print(f"[DEBUG] DATABASE_URL: {DATABASE_URL}", flush=True)

# Celery設定
celery = Celery("documentor_worker", broker=REDIS_URL, backend=REDIS_URL)
celery.conf.broker_url = REDIS_URL
celery.conf.result_backend = REDIS_URL

# SQLAlchemy設定
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

@celery.task(bind=True, name="tasks.transcribe_video_task")
def transcribe_video_task(self, video_url, video_id):
    print(f"[TASK] 🎬 タスク開始: video_id = {video_id}", flush=True)
    print(f"[TASK] 📡 Whisper API URL: {WHISPER_API_URL}", flush=True)
    print(f"[TASK] 📤 送信予定video_url: {video_url}", flush=True)

    session = Session()

    try:
        print("[TASK] 🔎 DBから動画情報を取得中...", flush=True)
        video = session.query(Video).get(video_id)
        if not video:
            print(f"[ERROR] ❗動画が見つかりません（video_id: {video_id}）", flush=True)
            return {"error": "Video not found in DB"}

        print("[TASK] ✅ 動画レコード取得完了", flush=True)

        print(f"[TASK] 📤 WhisperへPOST送信中...", flush=True)
        response = requests.post(
            WHISPER_API_URL,
            json={"video_url": video_url},
            timeout=300  # Whisper側の処理が長引くこともある
        )

        print(f"[TASK] 📥 Whisperレスポンス受信 - ステータス: {response.status_code}", flush=True)
        print(f"[TASK] 📝 Whisperレスポンス内容（先頭100文字）: {response.text[:100]}...", flush=True)

        response.raise_for_status()
        result = response.json()
        transcription_text = result.get("text", "")

        print(f"[TASK] ✍️ 文字起こし内容の先頭: {transcription_text[:100]}...", flush=True)

        print("[TASK] 🧠 DBへ文字起こし内容を保存中...", flush=True)
        video.whisper_text = transcription_text
        session.commit()

        print("[TASK] ✅ DB保存成功", flush=True)
        return result

    except Exception as e:
        session.rollback()
        print(f"[TASK ERROR] 🔥 Whisper POST or DB Error: {str(e)}", flush=True)
        return {"error": str(e)}

    finally:
        session.close()
        print("[TASK] 💾 セッションをクローズしました", flush=True)

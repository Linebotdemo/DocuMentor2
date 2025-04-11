import os
import requests
from celery import Celery
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Video  # Quiz は Render 側で生成

# .env 読み込み
load_dotenv()

# 環境変数取得
REDIS_URL = os.getenv("REDIS_URL")
WHISPER_API_URL = os.getenv("WHISPER_API_URL")
DATABASE_URL = os.getenv("FLASK_DATABASE_URI")
CALLBACK_URL = os.getenv("CALLBACK_URL")  # ← Render上のFlaskが受けるURL

# デバッグ出力
print(f"[DEBUG] REDIS_URL: {REDIS_URL}", flush=True)
print(f"[DEBUG] WHISPER_API_URL: {WHISPER_API_URL}", flush=True)
print(f"[DEBUG] DATABASE_URL: {DATABASE_URL}", flush=True)
print(f"[DEBUG] CALLBACK_URL: {CALLBACK_URL}", flush=True)

# Celery 設定
celery = Celery("documentor_worker", broker=REDIS_URL, backend=REDIS_URL)
celery.conf.broker_url = REDIS_URL
celery.conf.result_backend = REDIS_URL

# DB 設定
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

@celery.task(bind=True, name="tasks.transcribe_video_task")
def transcribe_video_task(self, video_url, video_id):
    print(f"[TASK] 🎬 タスク開始: video_id = {video_id}", flush=True)
    print(f"[TASK] 📡 Whisper API URL: {WHISPER_API_URL}", flush=True)
    print(f"[TASK] 📤 送信予定 video_url: {video_url}", flush=True)

    session = Session()

    try:
        print("[TASK] 🔎 DBから動画情報を取得中...", flush=True)
        video = session.query(Video).get(video_id)
        if not video:
            print(f"[ERROR] ❗動画が見つかりません（video_id: {video_id}）", flush=True)
            return {"error": "Video not found in DB"}

        print("[TASK] ✅ 動画レコード取得完了", flush=True)

        # Whisper API に渡すペイロード
        payload = {
            "video_url": video_url,
            "video_id": video_id,
            "callback_url": CALLBACK_URL  # Whisper が結果をPOSTする先
        }

        print(f"[TASK] 📤 WhisperへPOST送信中... payload: {payload}", flush=True)

        response = requests.post(
            WHISPER_API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},  # 明示的に追加
            timeout=300
        )

        print(f"[TASK] 📥 Whisperレスポンス受信 - ステータス: {response.status_code}", flush=True)
        print(f"[TASK] 📝 Whisperレスポンス内容（先頭100文字）: {response.text[:100]}...", flush=True)

        response.raise_for_status()
        result = response.json()

        print("[TASK] 🔁 WhisperがRenderにcallbackする設計のため、ここではDB保存しない", flush=True)
        return result

    except Exception as e:
        session.rollback()
        print(f"[TASK ERROR] 🔥 Whisper POST or DB Error: {str(e)}", flush=True)
        return {"error": str(e)}

    finally:
        session.close()
        print("[TASK] 💾 セッションをクローズしました", flush=True)

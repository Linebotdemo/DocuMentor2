from celery import Celery
import os
import requests
from dotenv import load_dotenv

load_dotenv()

celery = Celery(
    'tasks',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6380/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6380/0')
)

@celery.task
def transcribe_video_task(video_url, video_id):
    print(f"[DEBUG] タスク実行開始: video_url={video_url}, video_id={video_id}")
    
    whisper_api_url = os.getenv("WHISPER_API_URL", "http://localhost:8001/transcribe")
    callback_url = os.getenv("CALLBACK_URL")  # 例: https://documentor-xxxx.onrender.com/videos/whisper_callback

    try:
        # Whisper API へ POST（動画URLを送信）
        response = requests.post(whisper_api_url, json={"video_url": video_url}, timeout=600)
        print(f"[DEBUG] Whisper APIレスポンス status={response.status_code}")
        print(f"[DEBUG] Whisper APIレスポンス body={response.text}")

        # JSONパース試行
        try:
            data = response.json()
            text = data.get("text", "")
            if not text:
                print("[ERROR] Whisper APIから取得した text が空です")
                return None
        except Exception as e:
            print(f"[ERROR] Whisper APIレスポンスのJSON解析に失敗: {e}")
            return None

        # 成功したら Render 側の callback に送信
        payload = {
            "video_id": video_id,
            "text": text
        }

        cb_response = requests.post(callback_url, json=payload, timeout=30)
        print(f"[DEBUG] Callbackレスポンス status={cb_response.status_code}")
        print(f"[DEBUG] Callbackレスポンス body={cb_response.text}")

        return text

    except Exception as e:
        print(f"[ERROR] Whisperタスクエラー: {str(e)}")
        return None

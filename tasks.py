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
    callback_url = os.getenv("CALLBACK_URL")

    try:
        response = requests.post(whisper_api_url, json={"video_url": video_url}, timeout=600)
        text = response.json().get("text", "")
        print(f"[DEBUG] Whisper結果: {text[:100]}...")  # 長いので先頭100文字だけ表示
    except Exception as e:
        print(f"[ERROR] Whisperタスクエラー: {str(e)}")
        return None

    # ✅ Renderへのコールバック処理（CALLBACK_URL使用）
    try:
        if callback_url:
            res = requests.post(callback_url, json={
                "video_id": video_id,
                "text": text
            }, timeout=30)
            print(f"[DEBUG] Callback POST 成功 status={res.status_code}")
        else:
            print("[WARNING] CALLBACK_URL が未設定です")
    except Exception as e:
        print(f"[ERROR] Callback POST 失敗: {str(e)}")

    return text

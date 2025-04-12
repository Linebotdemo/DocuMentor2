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
    import os
    import requests
    from dotenv import load_dotenv
    load_dotenv()

    whisper_api_url = os.getenv("WHISPER_API_URL")
    callback_url = os.getenv("CALLBACK_URL")  # <= 必ず設定されている前提

    payload = {
        "video_url": video_url,
        "video_id": video_id,
        "callback_url": callback_url
    }

    try:
        print(f"[DEBUG] Whisper API呼び出し: {whisper_api_url}")
        response = requests.post(whisper_api_url, json=payload, timeout=10)
        print(f"[DEBUG] Whisper APIレスポンス status={response.status_code}")
        print(f"[DEBUG] Whisper APIレスポンス body={response.text[:500]}")
        return response.status_code
    except Exception as e:
        print(f"[ERROR] Whisper API呼び出し失敗: {str(e)}")
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

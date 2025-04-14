import os
from celery import Celery
import requests
from dotenv import load_dotenv
from flask import Flask
from models import db, Video, Quiz

# 環境変数読み込み
load_dotenv()

# Flaskアプリ
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///local.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Celery設定
celery = Celery(
    'tasks',
    broker=os.getenv('REDIS_URL'),
    backend=os.getenv('REDIS_URL')
)


@celery.task(bind=True)
def generate_summary_and_quiz_task(self, video_id, transcript):
    with app.app_context():
        video = Video.query.get(video_id)
        if not video:
            print(f"[ERROR] Video ID {video_id} not found")
            return False

        # Whisperコールバックで受け取ったtranscriptを保存（生成はWhisper側で完了してる）
        video.transcript = transcript
        db.session.commit()
        return True



@celery.task(name='tasks.transcribe_video_task')
def transcribe_video_task(video_url, video_id):
    whisper_api_url = os.getenv("WHISPER_API_URL")
    callback_url = os.getenv("CALLBACK_URL")

    payload = {
        "video_url": video_url,
        "video_id": video_id,
        "callback_url": callback_url
    }

    try:
        print(f"[DEBUG] Whisper API呼び出し: {whisper_api_url}")
        response = requests.post(whisper_api_url, json=payload, timeout=30)
        print(f"[DEBUG] Whisper APIレスポンス status={response.status_code}")
        print(f"[DEBUG] Whisper APIレスポンス body={response.text[:500]}")
        return response.status_code
    except Exception as e:
        print(f"[ERROR] Whisper API呼び出し失敗: {str(e)}")
        return None

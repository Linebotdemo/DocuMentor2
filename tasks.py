import os
from celery import Celery
import openai
import requests
from dotenv import load_dotenv

# FlaskアプリとSQLAlchemyをインポート
import app  # モジュール名（app.py）
from app import db, Video, Quiz  # モデル

# 環境変数読み込み
load_dotenv()

# Celery初期化
celery = Celery(
    'tasks',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6380/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6380/0')
)

# OpenAI APIキー設定
openai.api_key = os.getenv("OPENAI_API_KEY")


@celery.task(bind=True)
def transcribe_video_task(self, video_url, video_id):
    """
    Whisper APIにCloudinary動画URLを送信して文字起こしを依頼する。
    """
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


@celery.task(bind=True)
def generate_summary_and_quiz_task(self, video_id, transcript):
    """
    Whisper文字起こし結果から要約とクイズを生成し、DBに保存。
    """
    with app.app.app_context():  # Flaskアプリケーションコンテキスト
        video = Video.query.get(video_id)
        if not video:
            print(f"[ERROR] Video ID {video_id} not found")
            return

        mode = video.generation_mode or "manual"

        # === 要約生成 ===
        try:
            if mode == "manual":
                summary_prompt = f"""
以下の文字起こし内容を基に、誰でも理解できるような操作手順のマニュアルを日本語で作成してください。
見出しや番号を用いてステップごとに整理し、読みやすく構成してください。
---
{transcript}
---
"""
            else:
                summary_prompt = f"""
以下の内容は会議や講義の書き起こしです。主要な議題・発言内容・決定事項を整理し、議事録形式で日本語に要約してください。
文体はフォーマルで簡潔にまとめてください。
---
{transcript}
---
"""

            summary_response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "あなたはさまざまな業種に対応可能なプロのマニュアル・議事録作成AIです。"},
                    {"role": "user", "content": summary_prompt}
                ],
                timeout=90
            )
            video.summary_text = summary_response.choices[0].message.content.strip()
        except Exception as e:
            video.summary_text = f"要約失敗: {str(e)}"

        # === クイズ生成 ===
        try:
            quiz_prompt = f"""
以下の内容を元に、読み手の理解を確認するための日本語クイズを3問以上作成してください。
形式:
質問文: ...
選択肢:
1. ...
2. ...
3. ...
4. ...
正解番号: 数字
解説: なぜその選択肢が正解か簡潔に説明
---
{transcript}
---
"""

            quiz_response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "あなたは教育分野にも対応するクイズ作成AIです。"},
                    {"role": "user", "content": quiz_prompt}
                ],
                timeout=90
            )
            quiz_text = quiz_response.choices[0].message.content.strip()

            quiz = Quiz.query.filter_by(video_id=video.id).first()
            if not quiz:
                quiz = Quiz(video_id=video.id, title=f"Quiz for {video.title}")
                db.session.add(quiz)
            quiz.auto_quiz_text = quiz_text
        except Exception as e:
            quiz = Quiz.query.filter_by(video_id=video.id).first()
            if not quiz:
                quiz = Quiz(video_id=video.id, title=f"Quiz for {video.title}")
                db.session.add(quiz)
            quiz.auto_quiz_text = f"クイズ生成失敗: {str(e)}"

        db.session.commit()

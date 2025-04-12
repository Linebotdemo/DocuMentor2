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
def transcribe_video_task(self, video_url, video_id, generation_mode="manual"):
    import openai
    from models import Video, Quiz
    from sqlalchemy.orm import sessionmaker
    from celery_app import engine
    Session = sessionmaker(bind=engine)

    print(f"[TASK] 🎬 タスク開始: video_id = {video_id}", flush=True)
    session = Session()

    try:
        video = session.query(Video).get(video_id)
        if not video:
            return {"error": f"Video not found (id={video_id})"}

        # Whisper呼び出し
        response = requests.post(
            WHISPER_API_URL,
            json={"video_url": video_url},
            headers={"Content-Type": "application/json"},
            timeout=300
        )
        response.raise_for_status()
        result = response.json()
        video.whisper_text = result.get("text", "文字起こしが空でした")

        # OCR取得（空の可能性あり）
        ocr_text = video.ocr_text if video.ocr_text else ""

        # GPT要約生成
        if generation_mode == "minutes":
            prompt_header = "以下の動画書き起こしと画像OCR結果から、会議の議事録として、主要議題、決定事項、アクションアイテムを生成してください。"
        else:
            prompt_header = (
                "以下の動画書き起こしと画像OCR結果を元に、操作マニュアルを作成してください。\n"
                "各ステップを箇条書きで示し、見やすい改行とレイアウトを心がけてください。"
            )

        summary_prompt = (
            f"{prompt_header}\n\n"
            f"【音声書き起こし】\n{video.whisper_text}\n\n"
            f"【画像OCR結果】\n{ocr_text}\n\n要約:"
        )

        summary_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたはプロのマニュアル作成者です。"},
                {"role": "user", "content": summary_prompt}
            ],
            temperature=0.5,
            max_tokens=300
        )
        video.summary_text = summary_response.choices[0].message.content.strip()

        # クイズ生成
        quiz_prompt = (
            "以下の資料内容から、3問以上の日本語クイズを作成してください。\n"
            "出力形式は、各問題を「質問文、4つの選択肢、正解番号、解説」とし、改行区切りで出力してください。\n\n"
            f"【資料内容】\n{video.summary_text}\n\nクイズ:"
        )

        quiz_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたはプロの教材作成者です。"},
                {"role": "user", "content": quiz_prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )
        auto_quiz_text = quiz_response.choices[0].message.content.strip()

        quiz = session.query(Quiz).filter_by(video_id=video.id).first()
        if not quiz:
            quiz = Quiz(video_id=video.id, title=f"Quiz for {video.title}")
            session.add(quiz)
        quiz.auto_quiz_text = auto_quiz_text

        session.commit()
        print(f"[TASK] 🎉 要約・クイズ生成完了 video_id={video_id}", flush=True)
        return {"status": "success"}

    except Exception as e:
        session.rollback()
        print(f"[TASK ERROR] ❌ {str(e)}", flush=True)
        return {"error": str(e)}
    finally:
        session.close()

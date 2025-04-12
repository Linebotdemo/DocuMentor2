import os
import requests
import openai
from celery import Celery
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import Video, Quiz  # モデルファイルのパスが異なる場合は調整してください

# 環境変数
REDIS_URL = os.getenv("REDIS_URL")
DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URI")
WHISPER_API_URL = os.getenv("WHISPER_API_URL")
CALLBACK_URL = os.getenv("CALLBACK_URL")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Celery設定
celery = Celery(__name__, broker=REDIS_URL)

# SQLAlchemyセッション設定
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

@celery.task(bind=True, name="tasks.transcribe_video_task")
def transcribe_video_task(self, video_url, video_id, generation_mode="manual"):
    print(f"[TASK] 🎬 タスク開始: video_id = {video_id}", flush=True)
    session = Session()

    try:
        # DBから動画を取得
        video = session.query(Video).get(video_id)
        if not video:
            print(f"[ERROR] ❗動画が見つかりません: {video_id}", flush=True)
            return {"error": "Video not found"}

        # WhisperにPOSTして文字起こし
        print(f"[TASK] 📤 Whisperへ送信中: {WHISPER_API_URL}", flush=True)
        whisper_payload = {
            "video_url": video_url,
            "video_id": video_id,
            "callback_url": CALLBACK_URL
        }
        response = requests.post(WHISPER_API_URL, json=whisper_payload, timeout=300)
        response.raise_for_status()
        whisper_result = response.json()
        video.whisper_text = whisper_result.get("text", "文字起こしが空でした")

        # OCR結果
        ocr_text = video.ocr_text if video.ocr_text else ""

        # GPT要約
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

        # GPTクイズ
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
        quiz_text = quiz_response.choices[0].message.content.strip()
        video.quiz_text = quiz_text

        # Quizテーブルにも保存
        quiz = session.query(Quiz).filter_by(video_id=video.id).first()
        if not quiz:
            quiz = Quiz(video_id=video.id, title=f"Quiz for {video.title}")
            session.add(quiz)
        quiz.auto_quiz_text = quiz_text

        session.commit()
        print("[TASK] ✅ 要約・クイズ生成完了", flush=True)
        return {"status": "success"}

    except Exception as e:
        session.rollback()
        print(f"[TASK ERROR] ❌ {str(e)}", flush=True)
        return {"error": str(e)}

    finally:
        session.close()
        print("[TASK] 💾 セッション終了", flush=True)

from dotenv import load_dotenv
load_dotenv()

import os
import requests
import openai
from celery import Celery
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import Video, Quiz

# 環境変数読み込み
REDIS_URL = os.getenv("REDIS_URL")
DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URI")
WHISPER_API_URL = os.getenv("WHISPER_API_URL")
CALLBACK_URL = os.getenv("CALLBACK_URL")
openai.api_key = os.getenv("OPENAI_API_KEY")

if not DATABASE_URL:
    raise ValueError("環境変数 'SQLALCHEMY_DATABASE_URI' が定義されていません")

# SQLAlchemy セッション設定
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Celery アプリ定義
celery = Celery(__name__, broker=REDIS_URL)

@celery.task(bind=True, name="tasks.transcribe_video_task")
def transcribe_video_task(self, video_url, video_id, generation_mode="manual"):
    print(f"[TASK] 🎬 タスク開始: video_id = {video_id}", flush=True)
    session = Session()

    try:
        video = session.query(Video).get(video_id)
        if not video:
            print(f"[ERROR] Video not found: ID {video_id}", flush=True)
            return {"error": "Video not found in DB"}

        # Whisper 文字起こし
        print("[TASK] 🔊 Whisperへ送信中...", flush=True)
        whisper_response = requests.post(
            WHISPER_API_URL,
            json={"video_url": video_url},
            timeout=300
        )

        if whisper_response.status_code == 200:
            result = whisper_response.json()
            video.whisper_text = result.get("text", "文字起こしが空でした")
        else:
            video.whisper_text = f"Whisper failed: {whisper_response.text}"

        # OCR結果取得（video.ocr_text に事前格納されている想定）
        ocr_text = video.ocr_text or ""

        # GPT要約生成
        try:
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
        except Exception as e:
            video.summary_text = f"Summary generation failed: {str(e)}"

        # GPTクイズ生成
        try:
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
            video.quiz_text = auto_quiz_text  # Video側にコピーも可
        except Exception as e:
            quiz = session.query(Quiz).filter_by(video_id=video.id).first()
            if not quiz:
                quiz = Quiz(video_id=video.id, title=f"Quiz for {video.title}")
                session.add(quiz)
            quiz.auto_quiz_text = f"Quiz generation failed: {str(e)}"
            video.quiz_text = quiz.auto_quiz_text

        session.commit()
        print("[TASK] ✅ DB更新完了", flush=True)
        return {"status": "success", "video_id": video.id}

    except Exception as e:
        session.rollback()
        print(f"[TASK ERROR] ❌ 例外発生: {str(e)}", flush=True)
        return {"error": str(e)}

    finally:
        session.close()
        print("[TASK] 🔚 セッション終了", flush=True)

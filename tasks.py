import os
import requests
import openai
from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Video, Quiz  # 適宜調整

# ========================
# 環境変数取得（.envは使わない）
# ========================
DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URI")
REDIS_URL = os.getenv("REDIS_URL")
WHISPER_API_URL = os.getenv("WHISPER_API_URL")
CALLBACK_URL = os.getenv("CALLBACK_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DATABASE_URL:
    raise ValueError("環境変数 'SQLALCHEMY_DATABASE_URI' が定義されていません")
if not REDIS_URL:
    raise ValueError("環境変数 'REDIS_URL' が定義されていません")

# ========================
# Celery設定
# ========================
celery = Celery("tasks", broker=REDIS_URL)

# ========================
# DB接続（SQLAlchemy）
# ========================
engine = create_engine(DATABASE_URL)
Session = scoped_session(sessionmaker(bind=engine))

# ========================
# OpenAI設定
# ========================
openai.api_key = OPENAI_API_KEY


@celery.task(bind=True, name="tasks.transcribe_video_task")
def transcribe_video_task(self, video_url, video_id, generation_mode="manual"):
    print(f"[TASK] 🎬 タスク開始: video_id = {video_id}", flush=True)

    session = Session()
    try:
        # 動画取得
        video = session.query(Video).get(video_id)
        if not video:
            print(f"[ERROR] ❌ video_id={video_id} の動画が存在しません", flush=True)
            return {"error": "Video not found"}

        # Whisper文字起こし
        print(f"[TASK] 📡 Whisperへ送信中... {WHISPER_API_URL}", flush=True)
        whisper_payload = {"video_url": video_url}
        whisper_res = requests.post(WHISPER_API_URL, json=whisper_payload, timeout=300)
        whisper_res.raise_for_status()
        whisper_data = whisper_res.json()
        whisper_text = whisper_data.get("text", "文字起こしが空でした")
        video.whisper_text = whisper_text

        # OCRテキスト（空でなければ）
        ocr_text = video.ocr_text or ""

        # 要約プロンプト
        if generation_mode == "minutes":
            prompt_header = "以下の動画書き起こしと画像OCR結果から、会議の議事録を作成してください。"
        else:
            prompt_header = (
                "以下の動画書き起こしと画像OCR結果を元に、操作マニュアルを作成してください。\n"
                "各ステップを箇条書きで示し、見やすいレイアウトを心がけてください。"
            )

        summary_prompt = (
            f"{prompt_header}\n\n"
            f"【音声書き起こし】\n{whisper_text}\n\n"
            f"【画像OCR結果】\n{ocr_text}\n\n要約:"
        )

        # GPT要約生成
        summary_res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたはプロのマニュアル作成者です。"},
                {"role": "user", "content": summary_prompt}
            ],
            temperature=0.5,
            max_tokens=500
        )
        summary_text = summary_res.choices[0].message.content.strip()
        video.summary_text = summary_text

        # GPTクイズ生成
        quiz_prompt = (
            "以下の資料内容から、3問以上の日本語クイズを作成してください。\n"
            "出力形式は「質問文、4つの選択肢、正解番号、解説」。改行区切りで出力してください。\n\n"
            f"【資料内容】\n{summary_text}\n\nクイズ:"
        )

        quiz_res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたはプロの教材作成者です。"},
                {"role": "user", "content": quiz_prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )
        quiz_text = quiz_res.choices[0].message.content.strip()
        video.quiz_text = quiz_text

        # Quizモデル保存
        quiz = session.query(Quiz).filter_by(video_id=video.id).first()
        if not quiz:
            quiz = Quiz(video_id=video.id, title=f"Quiz for {video.title}")
            session.add(quiz)
        quiz.auto_quiz_text = quiz_text

        # DBコミット
        session.commit()
        print("[TASK] ✅ 要約・クイズ生成完了", flush=True)
        return {"status": "success"}

    except Exception as e:
        session.rollback()
        print(f"[TASK ERROR] ❌ {str(e)}", flush=True)
        return {"error": str(e)}

    finally:
        session.close()
        print("[TASK] 💾 セッションをクローズしました", flush=True)

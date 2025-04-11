import os
from celery import Celery
from flask import Flask

# Flaskアプリ（ダミー）
app = Flask(__name__)

@app.route("/")
def index():
    return "Celery Worker is alive!"

# Celeryインスタンス設定
celery = Celery(
    "documentor_worker",
    broker=os.getenv("REDIS_URL"),
    backend=os.getenv("REDIS_URL")
)

# ❌ NG: 自動探索（tasks.pyが単体ファイルなら使えない）
# celery.autodiscover_tasks(['tasks'])

# ✅ OK: 明示的にインポート
from tasks import transcribe_video_task  # ← 明示的にタスクを読み込む（登録される）

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

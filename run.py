import os
from flask import Flask
from tasks import transcribe_video_task  # タスク明示的に読み込む

# ダミーFlaskサーバ（確認用）
app = Flask(__name__)

@app.route("/")
def ping():
    return "Celery Worker is alive!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

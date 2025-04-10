# run.py

import os
import subprocess
from tasks import celery
from flask import Flask

# ダミーのFlaskアプリ（Railwayのポートチェック用）
app = Flask(__name__)

@app.route("/")
def ping():
    return "Celery Worker is alive!"

if __name__ == "__main__":
    # ✅ Celeryワーカーをバックグラウンドで起動（重要！）
    subprocess.Popen(["celery", "-A", "tasks", "worker", "--loglevel=info"])
    
    # ✅ Flaskサーバー起動（Railwayのため）
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

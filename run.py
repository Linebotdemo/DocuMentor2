# run.py (Celery + Dummy HTTP for Railway)

import os
from tasks import celery  # ← Celeryを起動するだけでOK
from flask import Flask

# ダミーFlaskサーバ（ポートを開くだけでOK）
app = Flask(__name__)

@app.route("/")
def ping():
    return "Celery Worker is alive!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

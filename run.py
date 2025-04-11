# run.py

import os
from celery import Celery
from flask import Flask

# Flask アプリ（ダミーサーバ）
app = Flask(__name__)

@app.route("/")
def ping():
    return "Celery Worker is alive!"


# Celeryインスタンス
celery = Celery(
    "documentor_worker",
    broker=os.getenv("REDIS_URL"),
    backend=os.getenv("REDIS_URL")
)

# Celeryタスク読み込み（tasks.py から）
celery.autodiscover_tasks(['tasks'])

if __name__ == "__main__":
    celery.worker_main(["worker", "--loglevel=info", "--concurrency=1"])

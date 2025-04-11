import os
from flask import Flask
from tasks import transcribe_video_task  # ← これだけでOK

from celery import Celery

app = Flask(__name__)

@app.route("/")
def ping():
    return "Celery Worker is alive!"

celery = Celery(
    "documentor_worker",
    broker=os.getenv("REDIS_URL"),
    backend=os.getenv("REDIS_URL")
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

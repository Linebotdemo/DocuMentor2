# run.py
import os
from flask import Flask

# ここでtasksモジュールをimportすることで、タスク登録が確実に行われる
import tasks

app = Flask(__name__)

@app.route("/")
def ping():
    return "Celery Worker is alive!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

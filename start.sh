#!/bin/bash

# Celeryワーカーをバックグラウンドでキュー名を明示して起動
celery -A tasks.celery worker --loglevel=info



# Flaskアプリを起動（Railway無料プランのスリープ防止）
python run.py

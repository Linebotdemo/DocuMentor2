#!/bin/bash

# Celeryワーカーをバックグラウンドでキュー名を明示して起動
celery -A tasks worker --loglevel=info -Q celery &

# Flaskアプリを起動（Railway無料プランのスリープ防止）
python run.py

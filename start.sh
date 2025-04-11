#!/bin/bash

# Celeryワーカーをバックグラウンドで起動（Railwayの監視対象ではない）
celery -A tasks worker --loglevel=info &

# Flaskをフォアグラウンドで起動（これがメイン＝停止対策になる）
python run.py

#!/bin/bash
celery -A tasks worker --loglevel=info -Q celery &  # ✅ ←キュー名を明示
python run.py

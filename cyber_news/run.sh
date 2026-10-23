#!/bin/bash
# ローカル(macOS launchd / cron)から日次実行するためのラッパ。
set -euo pipefail
cd "$(dirname "$0")"
LOG_DIR="state/logs"
mkdir -p "$LOG_DIR"
STAMP="$(date +%Y%m%d)"
# python3 は環境に合わせて調整
exec python3 main.py >> "$LOG_DIR/run-$STAMP.log" 2>&1

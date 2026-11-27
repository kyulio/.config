#!/bin/bash
# 패널 토글: panel.sh wifi|bluetooth|audio|battery|weather|calendar
# 상주 데몬(panels.py)에 FIFO 로 명령만 보냄 → 즉시 반응.
FIFO="${XDG_RUNTIME_DIR:-/tmp}/kyulio-panels.fifo"
DAEMON="$(dirname "$(readlink -f "$0")")/panels.py"

send() { [ -p "$FIFO" ] && timeout 0.3 bash -c 'echo "$1" > "$2"' _ "$1" "$FIFO" 2>/dev/null; }
running() { pgrep -f "python3 $DAEMON" >/dev/null; }

send "$1" && exit 0
# 데몬이 없으면 띄움 (재시작 중이면 그냥 기다림)
if ! running; then
    rm -f "$FIFO"
    setsid -f /usr/bin/python3 "$DAEMON" >/dev/null 2>&1
fi
for _ in $(seq 60); do
    sleep 0.05
    send "$1" && exit 0
done
exit 1

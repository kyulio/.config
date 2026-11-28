#!/bin/bash
# waybar 오디오 스펙트럼 (cava). 소리가 없으면 숨김.
command -v cava >/dev/null || { echo ""; exec sleep infinity; }

BARS=14
CONF=$(mktemp -t kyulio-cava.XXXXXX)
cleanup() {
    rm -f "$CONF"
    pkill -P $$ 2>/dev/null || true
}
trap cleanup EXIT
trap 'cleanup; exit 0' INT TERM
cat > "$CONF" <<EOF
[general]
bars = $BARS
framerate = 30
autosens = 0
sensitivity = 1800
sleep_timer = 0

[input]
method = pipewire
source = auto

[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = 7
bar_delimiter = 59
frame_delimiter = 10

[smoothing]
noise_reduction = 65
EOF

SILENT=$(printf '0;%.0s' $(seq $BARS))
while true; do
    cava -p "$CONF" 2>/dev/null | while IFS= read -r line; do
        if [ "$line" = "$SILENT" ]; then
            echo ""
        else
            echo "$line" | sed 's/;//g; y/01234567/▁▂▃▄▅▆▇█/'
        fi
    done
    echo ""
    sleep 1
done

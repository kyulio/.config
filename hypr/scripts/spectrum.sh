#!/bin/bash
# waybar 오디오 스펙트럼 (cava). 소리가 없으면 숨김.
command -v cava >/dev/null || { echo ""; exec sleep infinity; }

BARS=14
CONF=$(mktemp -t kyulio-cava.XXXXXX)
trap 'rm -f "$CONF"' EXIT
cat > "$CONF" <<EOF
[general]
bars = $BARS
framerate = 30
sleep_timer = 2

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
noise_reduction = 77
EOF

SILENT=$(printf '0;%.0s' $(seq $BARS))
cava -p "$CONF" | while IFS= read -r line; do
    if [ "$line" = "$SILENT" ]; then
        echo ""
    else
        echo "$line" | sed 's/;//g; y/01234567/▁▂▃▄▅▆▇█/'
    fi
done

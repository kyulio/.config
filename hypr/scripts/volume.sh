#!/bin/bash
SINK=@DEFAULT_AUDIO_SINK@

case "$1" in
    up)   wpctl set-volume -l 1 "$SINK" 5%+ ;;
    down) wpctl set-volume "$SINK" 5%- ;;
    mute) wpctl set-mute "$SINK" toggle ;;
esac

STATE=$(wpctl get-volume "$SINK")
PCT=$(awk '{printf "%d", $2 * 100 + 0.5}' <<< "$STATE")

if [[ "$STATE" == *MUTED* ]]; then
    TITLE="Muted"
    ICON=audio-volume-muted
else
    TITLE="Volume"
    ICON=audio-volume-high
fi

notify-send -t 1500 -h string:x-canonical-private-synchronous:volume \
            -h int:value:"$PCT" \
            -i "$ICON" \
            "$TITLE" "${PCT}%"

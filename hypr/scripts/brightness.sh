#!/bin/bash
ACTION=$1
STEP="5%"

if [ "$ACTION" == "up" ]; then
    brightnessctl -e4 -n2 set "$STEP"+
elif [ "$ACTION" == "down" ]; then
    brightnessctl -e4 -n2 set "$STEP"-
fi

CURRENT_PCT=$(brightnessctl -m | head -n 1 | cut -d, -f4)
notify-send -t 1500 -h string:x-canonical-private-synchronous:brightness \
            -h int:value:"${CURRENT_PCT//%/}" \
            "Brightness" "$CURRENT_PCT" \
            -i notification-display-brightness

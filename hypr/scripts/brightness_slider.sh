#!/bin/bash

# Kill existing instance to act as a toggle
if pkill -f "zenity --scale --title=Brightness"; then
    exit 0
fi

# Get current brightness percentage
CURRENT_PCT=$(brightnessctl -m | head -n 1 | cut -d, -f4 | tr -d '%')

# Open Zenity slider
zenity --scale \
       --title="Brightness" \
       --text="" \
       --value="$CURRENT_PCT" \
       --min-value=5 \
       --max-value=100 \
       --step=5 \
       --width=350 \
       --height=60 \
       --print-partial | while read -r val; do
    if [ -n "$val" ]; then
        brightnessctl set "${val}%" >/dev/null 2>&1
    fi
done

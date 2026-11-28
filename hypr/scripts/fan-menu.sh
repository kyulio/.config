#!/bin/bash
OPTIONS="󰌢 Quiet\n󰾆 Balanced\n󰈐 Performance"
CHOICE=$(echo -e "$OPTIONS" | rofi -dmenu -i -no-show-icons -p "Fan Profile" -theme ~/.config/rofi/panel.rasi)

case "$CHOICE" in
    *Quiet*)       asusctl profile set Quiet       && notify-send -i preferences-system-power "Profile" "Quiet Mode Set" ;;
    *Balanced*)    asusctl profile set Balanced    && notify-send -i preferences-system-power "Profile" "Balanced Mode Set" ;;
    *Performance*) asusctl profile set Performance && notify-send -i preferences-system-power "Profile" "Performance Mode Set" ;;
esac

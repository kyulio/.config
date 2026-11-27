#!/bin/bash
OPTIONS="󰢮 Integrated (Eco)\n󰢮 Hybrid (Standard)\n󰢮 Dedicated (Gaming)"
CHOICE=$(echo -e "$OPTIONS" | rofi -dmenu -no-show-icons -p "GPU Mode" -theme ~/.config/rofi/panel.rasi)

case "$CHOICE" in
    *Integrated*) supergfxctl -m Integrated && notify-send -i computer "GPU" "Integrated Mode Set\n(Applies after logout or reboot)" ;;
    *Hybrid*)     supergfxctl -m Hybrid     && notify-send -i computer "GPU" "Hybrid Mode Set\n(Applies after logout or reboot)" ;;
    *Dedicated*)  supergfxctl -m Dedicated  && notify-send -i computer "GPU" "Dedicated Mode Set\n(Applies after logout or reboot)" ;;
esac

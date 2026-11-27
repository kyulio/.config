#!/bin/bash
ICON=bluetooth

menu() {
    rofi -dmenu -no-show-icons -i -p "$1" -theme ~/.config/rofi/panel.rasi
}

notify() {
    notify-send -i "$ICON" -h string:x-canonical-private-synchronous:bluetooth "Bluetooth" "$1"
}

if pkill -x rofi; then
    exit 0
fi

if ! command -v bluetoothctl >/dev/null; then
    notify "bluetoothctl not found. Install bluez-utils."
    exit 1
fi

if ! bluetoothctl show | grep -q 'Powered: yes'; then
    CHOICE=$(printf '󰂯  Turn On Bluetooth\n' | menu "Bluetooth (Off)")
    if [ -n "$CHOICE" ]; then
        bluetoothctl power on >/dev/null && notify "Bluetooth On" || notify "Failed to turn on Bluetooth"
    fi
    exit 0
fi

declare -A DEVICES CONNECTED
ROWS=""

while read -r _ mac _; do
    [ -n "$mac" ] && CONNECTED[$mac]=1
done < <(bluetoothctl devices Connected)

while read -r _ mac name; do
    [ -z "$mac" ] && continue
    if [ -n "${CONNECTED[$mac]}" ]; then
        row="󰂱  $name  (Connected)"
        ROWS="$row"$'\n'"$ROWS"
    else
        row="󰂯  $name"
        ROWS="$ROWS$row"$'\n'
    fi
    DEVICES[$row]=$mac
done < <(bluetoothctl devices Paired)

CHOICE=$(printf '%s󰑐  Scan for Devices\n󰂲  Turn Off Bluetooth\n' "$ROWS" | menu "Bluetooth")
[ -z "$CHOICE" ] && exit 0

case "$CHOICE" in
    *"Turn Off Bluetooth")
        bluetoothctl power off >/dev/null && notify "Bluetooth Off"
        exit 0
        ;;
    *"Scan for Devices")
        notify "Scanning for 8 seconds..."
        bluetoothctl --timeout 8 scan on >/dev/null

        declare -A FOUND
        ROWS=""
        PAIRED=$(bluetoothctl devices Paired)
        while read -r _ mac name; do
            [ -z "$mac" ] && continue
            [[ "$name" =~ ^([0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}$ ]] && continue
            grep -q "$mac" <<< "$PAIRED" && continue
            row="󰂯  $name"
            FOUND[$row]=$mac
            ROWS="$ROWS$row"$'\n'
        done < <(bluetoothctl devices)

        if [ -z "$ROWS" ]; then
            notify "No new devices found"
            exit 0
        fi

        CHOICE=$(printf '%s' "$ROWS" | menu "Pair Device")
        [ -z "$CHOICE" ] && exit 0
        MAC=${FOUND[$CHOICE]}
        DEVICE=$(busctl --list tree org.bluez | grep "dev_${MAC//:/_}$")
        notify "Pairing..."
        if busctl --timeout=90 call org.bluez "$DEVICE" org.bluez.Device1 Pair >/dev/null && bluetoothctl trust "$MAC" >/dev/null && bluetoothctl connect "$MAC" >/dev/null; then
            notify "Connected"
        else
            notify "Failed to pair"
        fi
        exit 0
        ;;
esac

MAC=${DEVICES[$CHOICE]}
[ -z "$MAC" ] && exit 0

if [ -n "${CONNECTED[$MAC]}" ]; then
    bluetoothctl disconnect "$MAC" >/dev/null && notify "Disconnected" || notify "Failed to disconnect"
else
    notify "Connecting..."
    bluetoothctl connect "$MAC" >/dev/null && notify "Connected" || notify "Failed to connect"
fi

#!/bin/bash
if pkill -x rofi; then
    exit 0
fi

ROWS=$(python3 -I - <<'PY'
import json, subprocess

def load(kind):
    out = subprocess.run(["pactl", "-f", "json", "list", kind], capture_output=True, text=True).stdout
    return [d for d in json.loads(out or "[]") if not d["name"].endswith(".monitor")]

def icon(dev, kind):
    name = dev["name"]
    if kind == "sources":
        return "󰋎" if "bluez" in name else "󰍬"
    if "bluez" in name:
        return "󰋋"
    if "usb" in name:
        return "󰓃"
    return "󰓃" if "hdmi" in name else "󰕾"

for kind, label in (("sinks", "Output"), ("sources", "Input")):
    default = subprocess.run(["pactl", "get-default-" + kind[:-1]], capture_output=True, text=True).stdout.strip()
    for dev in load(kind):
        mark = "  (Active)" if dev["name"] == default else ""
        print(f"{dev['name']}\t{icon(dev, kind)}  {dev['description']}{mark}\t{label}")
PY
)

[ -z "$ROWS" ] && exit 0

MENU=$(awk -F'\t' '
    $3 != last { if (NR > 1) print "\x01"; print "\x02" $3; last = $3 }
    { print $1 "\t" $2 }
' <<< "$ROWS" | grep -v $'^\x01$')

LIST=$(sed $'s/^\x02\\(.*\\)/-\t── \\1 ──/' <<< "$MENU")
ACTIVE=$(grep -n '(Active)' <<< "$LIST" | head -1 | cut -d: -f1)
CHOICE=$(rofi -dmenu -i -no-show-icons -display-columns 2 -p "Audio" -selected-row "$(( ${ACTIVE:-2} - 1 ))" -theme ~/.config/rofi/panel.rasi <<< "$LIST")
NAME=${CHOICE%%$'\t'*}
[ -z "$CHOICE" ] || [ "$NAME" = "-" ] && exit 0

KIND=$(awk -F'\t' -v n="$NAME" '$1 == n { print $3 }' <<< "$ROWS")
DESC=$(awk -F'\t' -v n="$NAME" '$1 == n { sub(/^[^ ]+  /, "", $2); sub(/  \(Active\)$/, "", $2); print $2 }' <<< "$ROWS")

if [ "$KIND" = "Output" ]; then
    pactl set-default-sink "$NAME"
    for input in $(pactl list short sink-inputs | cut -f1); do
        pactl move-sink-input "$input" "$NAME" 2>/dev/null
    done
else
    pactl set-default-source "$NAME"
    for output in $(pactl list short source-outputs | cut -f1); do
        pactl move-source-output "$output" "$NAME" 2>/dev/null
    done
fi

notify-send -t 2000 -i audio-volume-high -h string:x-canonical-private-synchronous:audio-device "$KIND" "$DESC"

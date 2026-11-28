#!/bin/bash
THUMBS="$HOME/.cache/cliphist/thumbs"

if pkill -x rofi; then
    exit 0
fi

mkdir -p "$THUMBS"
chmod 700 "$THUMBS"

build_rows() {
    local id text ext size file
    while IFS=$'\t' read -r id text; do
        if [[ "$text" =~ ^\[\[\ binary\ data\ ([0-9.]+\ [A-Za-z]+)\ ([a-z]+)\ ([0-9]+x[0-9]+)\ \]\]$ ]]; then
            size="${BASH_REMATCH[1]}"
            ext="${BASH_REMATCH[2]}"
            file="$THUMBS/$id.$ext"
            [ -s "$file" ] || cliphist decode "$id" > "$file"
            printf '%s\tImage  %s  %s\0icon\x1f%s\n' "$id" "${BASH_REMATCH[3]}" "$size" "$file"
        else
            printf '%s\t%s\n' "$id" "$text"
        fi
    done
}

LIST=$(cliphist list | head -n 200)  # 최근 200개만 (전체는 수천 개라 느림)

CHOICE=$(build_rows <<< "$LIST" | rofi -dmenu -i -show-icons -display-columns 2 -p "Clipboard" -theme ~/.config/rofi/clipboard.rasi)
[ -n "$CHOICE" ] && cliphist decode "${CHOICE%%$'\t'*}" | wl-copy

find "$THUMBS" -type f | while read -r file; do
    id=$(basename "${file%.*}")
    grep -q "^$id"$'\t' <<< "$LIST" || rm -f "$file"
done

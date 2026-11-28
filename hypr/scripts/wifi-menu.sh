#!/bin/bash

if pkill -x rofi; then
    exit 0
fi

# Get Wi-Fi status (enabled/disabled)
WIFI_STATUS=$(nmcli radio wifi)

if [ "$WIFI_STATUS" = "disabled" ]; then
    OPTIONS="󰖩  Turn On Wifi\n󰑐  Rescan"
    CHOICE=$(echo -e "$OPTIONS" | rofi -dmenu -i -no-show-icons -p "Wi-Fi (Disabled)" -theme ~/.config/rofi/panel.rasi)
    case "$CHOICE" in
        *Turn*)
            nmcli radio wifi on
            notify-send -i network-wireless "Wi-Fi" "Wi-Fi Enabled"
            ;;
        *Rescan*)
            nmcli device wifi rescan
            ;;
    esac
    exit 0
fi

# Scan for fresh networks in the background
nmcli device wifi rescan &>/dev/null &

# Get list of Wi-Fi networks (terse mode, escape colons)
# Format: ACTIVE:SSID:SECURITY:BARS
# We filter out empty/hidden SSIDs and keep only the first occurrence (strongest/active) of each SSID.
RAW_LIST=$(nmcli -t -f ACTIVE,SSID,SECURITY,SIGNAL device wifi list --rescan no | grep -v '^[^:]*::')

# Build the options list for Rofi
OPTIONS=""
declare -A SEEN_SSIDS

while IFS=: read -r ACTIVE SSID SECURITY SIGNAL; do
    # Skip empty lines
    [ -z "$SSID" ] && continue
    
    # Unescape colons in SSID (nmcli escapes them as \:)
    SSID=$(echo "$SSID" | sed 's/\\:/:/g')
    
    # Keep only the strongest/first occurrence of each SSID
    if [ -n "${SEEN_SSIDS[$SSID]}" ]; then
        continue
    fi
    SEEN_SSIDS[$SSID]=1
    
    # Determine security icon
    SECURED="󰌾"
    if [ "$SECURITY" = "--" ] || [ -z "$SECURITY" ]; then
        SECURED="  "
    fi
    
    # Signal icon
    if   [ "${SIGNAL:-0}" -ge 80 ]; then BARS="󰤨"
    elif [ "${SIGNAL:-0}" -ge 60 ]; then BARS="󰤥"
    elif [ "${SIGNAL:-0}" -ge 40 ]; then BARS="󰤢"
    elif [ "${SIGNAL:-0}" -ge 20 ]; then BARS="󰤟"
    else BARS="󰤯"; fi

    # Format the line for Rofi
    if [ "$ACTIVE" = "yes" ]; then
        OPTIONS="󰄬 $SSID | $SECURED | $BARS (Connected)\n$OPTIONS"
    else
        OPTIONS="$OPTIONS$SSID | $SECURED | $BARS\n"
    fi
done <<< "$RAW_LIST"

# Add utility options
OPTIONS="${OPTIONS}󰖪  Turn Off Wifi\n󰑐  Rescan"

# Show Rofi menu
CHOICE=$(echo -e "$OPTIONS" | rofi -dmenu -i -no-show-icons -p "Wi-Fi" -theme ~/.config/rofi/panel.rasi)

# Exit if cancelled
[ -z "$CHOICE" ] && exit 0

if [[ "$CHOICE" == *"Turn Off Wifi"* ]]; then
    nmcli radio wifi off
    notify-send -i network-wireless-offline "Wi-Fi" "Wi-Fi Disabled"
elif [[ "$CHOICE" == *"Rescan"* ]]; then
    notify-send -i network-wireless "Wi-Fi" "Scanning for networks..."
    nmcli device wifi rescan
elif [[ "$CHOICE" == *"󰄬"* ]]; then
    # Clicked on already connected network
    SSID=$(echo "$CHOICE" | cut -d '|' -f 1 | sed 's/^󰄬 //g' | xargs)
    notify-send -i network-wireless "Wi-Fi" "Already connected to $SSID"
else
    # Extract SSID (everything before the first ' | ')
    SSID=$(echo "$CHOICE" | cut -d '|' -f 1 | xargs)
    
    # Find security type for this SSID
    # We look for the SSID in raw list to check if it has WPA/WEP/etc.
    SEC_TYPE=$(nmcli -t -f SSID,SECURITY device wifi list --rescan no | grep -F "$SSID" | head -n 1 | cut -d: -f2)
    
    if [ -n "$SEC_TYPE" ] && [ "$SEC_TYPE" != "--" ]; then
        # Secured network - ask for password
        PASS=$(rofi -dmenu -no-show-icons -password -p "Password for $SSID" -theme ~/.config/rofi/panel.rasi)
        
        # Exit if cancelled
        [ -z "$PASS" ] && exit 0
        
        notify-send -i network-wireless "Wi-Fi" "Connecting to $SSID..."
        if nmcli device wifi connect "$SSID" password "$PASS"; then
            notify-send -i network-wireless "Wi-Fi" "Connected to $SSID"
        else
            notify-send -i network-wireless-offline "Wi-Fi" "Failed to connect to $SSID"
        fi
    else
        # Unsecured network - connect directly
        notify-send -i network-wireless "Wi-Fi" "Connecting to $SSID..."
        if nmcli device wifi connect "$SSID"; then
            notify-send -i network-wireless "Wi-Fi" "Connected to $SSID"
        else
            notify-send -i network-wireless-offline "Wi-Fi" "Failed to connect to $SSID"
        fi
    fi
fi

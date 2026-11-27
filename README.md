# dotfiles

Arch Linux · Hyprland · waybar · monochrome.

`SUPER` = Windows key.

## Hyprland

### Apps

| Keys | Action |
|---|---|
| `SUPER` (tap) | Power menu |
| `SUPER + Space` | App launcher (rofi) |
| `SUPER + Q` | Terminal (kitty) |
| `SUPER + E` | File manager (yazi) |
| `SUPER + V` | Clipboard history |

### Windows

| Keys | Action |
|---|---|
| `SUPER + C` | Close window |
| `ALT + F4` | Force kill window |
| `SUPER + SHIFT + V` | Toggle floating |
| `SUPER + P` | Pseudo-tile |
| `SUPER + J` | Toggle split direction |
| `SUPER + ← → ↑ ↓` | Move focus |
| `SUPER + Left drag` | Move window |
| `SUPER + Right drag` | Resize window |

### Workspaces

| Keys | Action |
|---|---|
| `SUPER + 1 … 0` | Go to workspace 1–10 |
| `SUPER + SHIFT + 1 … 0` | Move window to workspace 1–10 |
| `SUPER + Scroll` | Next / previous workspace |
| `SUPER + S` | Toggle scratchpad (special:magic) |
| `SUPER + SHIFT + A` | Move window to scratchpad |

### System

| Keys | Action |
|---|---|
| `SUPER + M` | Log out |
| `SUPER + SHIFT + S` | Screenshot region → clipboard |
| `Print` | Screenshot full screen → `~/Pictures` |
| `SUPER + SHIFT + F` | Fan profile menu |
| `SUPER + SHIFT + G` | GPU mode menu |
| `Fn` profile key | Next power profile |
| Volume / mute / mic keys | Volume, mute, mic mute |
| Brightness keys | Screen brightness |

## waybar

| Item | Left click | Right click | Other |
|---|---|---|---|
| `⭘` | Power panel | | |
| Workspaces | Switch workspace | | |
| Clock | Calendar | | |
| Weather | Weather panel | | |
| `‹` (tray) | Hover to expand tray | | |
| Bluetooth | Bluetooth panel | Old rofi menu | |
| Wi-Fi | Wi-Fi panel | Old rofi menu | |
| Volume | Sound panel | pavucontrol | Middle: notifications · Scroll: volume |
| Brightness | Notification center | | |
| Battery | Battery panel | | |
| Bell | Notification center | Toggle do-not-disturb | |

## Panels

All panels: `Esc` or click outside to close, click the same icon again to toggle.

| Panel | Keys / mouse |
|---|---|
| Power | `L` lock · `E` log out · `U` suspend · `R` reboot · `S` shut down |
| Calendar | `←` `→` / scroll: change month · `Home` / `T` / click title: today |
| Wi-Fi | Click network: connect / disconnect · Right-click saved network: forget · Password field: `Enter` to connect, `Esc` to cancel |
| Bluetooth | Click device: connect / disconnect / pair · Right-click paired device: forget · `↻`: scan 20 s |
| Sound | Click device: make default (moves playing streams) · Icon left of slider: mute |
| Password (polkit) | `Enter` authenticate · `Esc` / click outside: cancel |

## yazi

Run with `y` in a terminal to `cd` into the last directory on quit.

### Navigation

| Keys | Action |
|---|---|
| `h` `j` `k` `l` | Parent / down / up / enter |
| `l` / `Enter` | Enter directory or open file |
| `g` `g` / `G` | Top / bottom |
| `g` `h` | `~` |
| `g` `c` | `~/.config` |
| `g` `d` | `~/Downloads` |
| `g` `p` | `~/Pictures` |
| `g` `v` | `~/Videos` |
| `g` `D` | `~/Documents` |
| `g` `s` | `~/.config/hypr/scripts` |
| `g` `t` | Trash |
| `z` | Find file (fzf) |
| `Z` | Jump directory (zoxide) |
| `/` / `n` / `N` | Find / next / previous |

### Files

| Keys | Action |
|---|---|
| `Space` | Select |
| `v` | Visual select |
| `y` / `x` / `p` | Copy / cut / paste |
| `d` / `D` | Trash / delete permanently |
| `a` | Create (end with `/` for folder) |
| `r` | Rename |
| `.` | Show hidden files |
| `c` `c` | Copy path |
| `c` `d` | Drag & drop (ripdrag) |
| `c` `m` | Change permissions |
| `M` | Mount / unmount drives |
| `!` | Open terminal here |

### View

| Keys | Action |
|---|---|
| `T` | Maximize / restore preview |
| `t` `p` | Show / hide preview |
| `t` `t` | New tab |
| `1` … `9` | Switch tab |
| `,` | Sort menu |
| `~` | All keybindings |
| `q` | Quit |

## License

Copyright (C) 2026 kyulio

Licensed under the [GNU General Public License v3.0](LICENSE) (GPL-3.0-or-later).

### Third-party

These parts come from other projects and keep their original licenses
(all GPL-compatible unless noted):

| Path | Source | License |
|---|---|---|
| `yazi/plugins/*` | [yazi-rs/plugins](https://github.com/yazi-rs/plugins) | MIT (see each `LICENSE`) |
| `nvim/` | [NvChad starter](https://github.com/NvChad/starter) | Unlicense |
| `cava/shaders/`, `cava/themes/` | [cava](https://github.com/karlstav/cava) | MIT |
| waybar layout | inspired by [Omarchy](https://github.com/basecamp/omarchy) | MIT |
| `sddm/themes/rose-lock/background*.jpg` | Photo by Gian D. on [Unsplash](https://unsplash.com) | [Unsplash License](https://unsplash.com/license) — **not** covered by the GPL |

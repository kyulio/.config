#!/usr/bin/python3
"""전원 패널 (⭘ 버튼 아래, 좌측 상단) — wlogout 대체. 단축키: L E U R S, Esc."""
import getpass
import os
import socket
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panel_base import Gdk, Gtk, Panel, label, main, sep  # noqa: E402

ICON_POWER = "\U000F0425"
ACTIONS = [
    # (키, 아이콘, 이름, 설명, 명령)
    ("l", "\U000F033E", "Lock", "화면 잠금", "hyprlock"),
    ("e", "\U000F0343", "Logout", "세션 종료",
     "command -v hyprshutdown >/dev/null 2>&1 && hyprshutdown || hyprctl dispatch 'hl.dsp.exit()'"),
    ("u", "\U000F04B2", "Suspend", "절전", "systemctl suspend"),
    ("r", "\U000F0709", "Reboot", "다시 시작", "systemctl reboot"),
    ("s", "\U000F0425", "Shutdown", "시스템 종료", "systemctl poweroff"),
]


def uptime():
    try:
        sec = int(float(open("/proc/uptime").read().split()[0]))
    except (OSError, ValueError):
        return ""
    d, rem = divmod(sec, 86400)
    h, m = divmod(rem // 60, 60)
    return (f"{d}D " if d else "") + f"{h}H {m:02d}M"


class PowerPanel(Panel):
    ANCHOR = "left"
    WIDTH = 300
    CSS = """
    .key-hint {
      color: #777777; font-size: 10px; min-width: 18px;
      border: 1px solid rgba(255, 255, 255, 0.14); border-radius: 5px; padding: 1px 5px;
    }
    """

    def __init__(self, app):
        super().__init__(app)
        card = self.card

        head = Gtk.Box(spacing=10)
        card.append(head)
        head.append(label(ICON_POWER, "hero-icon", xalign=0.5))
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        head.append(titles)
        titles.append(label(getpass.getuser(), "hero-name"))
        titles.append(label(f"{socket.gethostname().upper()} · UP {uptime()}", "hero-sub"))
        card.append(sep())

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        card.append(box)
        self.keys = {}
        for key, icon, name, desc, cmd in ACTIONS:
            btn = Gtk.Button(focusable=False)
            btn.add_css_class("row-btn")
            row = Gtk.Box(spacing=8)
            row.append(label(icon, "row-icon", xalign=0.5))
            names = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
            names.append(label(name, "row-name"))
            names.append(label(desc, "row-sub"))
            row.append(names)
            row.append(label(key.upper(), "key-hint", xalign=0.5, valign=Gtk.Align.CENTER))
            btn.set_child(row)
            btn.connect("clicked", lambda _b, c=cmd: self.run(c))
            box.append(btn)
            self.keys[getattr(Gdk, f"KEY_{key}")] = cmd

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self.on_key)
        self.add_controller(keys)

    def run(self, cmd):
        self.close()
        subprocess.Popen(["sh", "-c", cmd], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def on_key(self, _c, key, _code, _state):
        cmd = self.keys.get(key)
        if cmd:
            self.run(cmd)
            return True
        return False


if __name__ == "__main__":
    main("org.kyulio.PowerPanel", PowerPanel)

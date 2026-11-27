#!/usr/bin/python3
"""배터리 패널: 잔량 / 상태(용량·건강도·사이클·소비전력) / 전원 프로필 / 충전 제한 / GPU 모드."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panel_base import GLib, Gtk, Panel, label, main, run, sep, stat_grid  # noqa: E402

BAT = "/sys/class/power_supply/BAT1/"
ICONS = ["\U000F007A", "\U000F007B", "\U000F007C", "\U000F007D", "\U000F007E",
         "\U000F007F", "\U000F0080", "\U000F0081", "\U000F0082", "\U000F0079"]
ICON_CHARGING = "\U000F0084"

PROFILES = [("Quiet", "\U000F0322  Quiet"), ("Balanced", "\U000F0BE6  Balanced"),
            ("Performance", "\U000F04C5  Performance")]
LIMITS = [60, 80, 100]
GPU_LABELS = {"Integrated": "Integrated", "Hybrid": "Hybrid", "AsusMuxDgpu": "dGPU only"}


def read(name, default=""):
    try:
        return open(BAT + name).read().strip()
    except OSError:
        return default


def num(name):
    try:
        return int(read(name, "0"))
    except ValueError:
        return 0


def fmt_hours(h):
    if h <= 0 or h > 48:
        return ""
    return f"{int(h)}h {int(h * 60) % 60:02d}m"


class BatteryPanel(Panel):
    def __init__(self, app):
        super().__init__(app)
        card = self.card

        head = Gtk.Box(spacing=10)
        card.append(head)
        self.hero_icon = label(ICONS[-1], "hero-icon", xalign=0.5)
        head.append(self.hero_icon)
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        head.append(titles)
        titles.append(label("Battery", "hero-name"))
        self.hero_sub = label("", "hero-sub")
        titles.append(self.hero_sub)
        self.percent = label("", "hero-big", xalign=1)
        head.append(self.percent)

        self.bar = Gtk.ProgressBar()
        card.append(self.bar)

        grid, self.stats = stat_grid([
            ("size", "Capacity"), ("health", "Health"),
            ("cycles", "Charge cycles"), ("limit", "Charge limit"),
            ("power", "Power draw"), ("state", "State")])
        card.append(grid)
        card.append(sep())

        card.append(label("POWER PROFILE", "section"))
        self.profile_btns = self.segs(card, [(k, t) for k, t in PROFILES], self.set_profile)

        card.append(label("CHARGE LIMIT", "section"))
        self.limit_btns = self.segs(card, [(n, f"{n}%") for n in LIMITS], self.set_limit)

        card.append(label("GPU MODE  ·  재로그인 후 적용", "section"))
        self.gpu_box = Gtk.Box(spacing=6, homogeneous=True)
        card.append(self.gpu_box)
        self.gpu_btns = {}

        self.status = label("", "status", visible=False)
        card.append(self.status)

        self.refresh_sysfs()
        self.refresh_tools()
        GLib.timeout_add_seconds(3, lambda: self.refresh_sysfs() or True)

    def segs(self, parent, items, cb):
        box = Gtk.Box(spacing=6, homogeneous=True)
        parent.append(box)
        btns = {}
        for key, text in items:
            b = Gtk.Button(label=text, focusable=False)
            b.add_css_class("seg")
            b.connect("clicked", lambda _b, k=key: cb(k))
            box.append(b)
            btns[key] = b
        return btns

    @staticmethod
    def mark(btns, current):
        for k, b in btns.items():
            (b.add_css_class if k == current else b.remove_css_class)("on")

    def say(self, text):
        self.status.set_label(text)
        self.status.set_visible(bool(text))

    # ── sysfs (빠름) ──
    def refresh_sysfs(self):
        cap = num("capacity")
        status = read("status", "Unknown")
        volt = num("voltage_now") / 1e6
        vmin = num("voltage_min_design") / 1e6
        cur = num("current_now") / 1e6
        now, full, design = num("charge_now") / 1e6, num("charge_full") / 1e6, num("charge_full_design") / 1e6
        watts = cur * volt

        charging = status == "Charging"
        self.hero_icon.set_label(ICON_CHARGING if charging else ICONS[min(9, cap // 10)])
        self.percent.set_label(f"{cap}%")
        self.bar.set_fraction(cap / 100)

        if charging and cur > 0:
            sub = f"CHARGING · FULL IN {fmt_hours((full - now) / cur)}"
        elif status == "Discharging" and cur > 0:
            sub = f"ON BATTERY · {fmt_hours(now / cur)} LEFT"
        else:
            sub = status.upper().replace("NOT CHARGING", "PLUGGED IN")
        self.hero_sub.set_label(sub.rstrip(" ·"))

        self.stats["size"].set_label(f"{full * vmin:.0f} / {design * vmin:.0f} Wh")
        self.stats["health"].set_label(f"{full / design * 100:.0f}%" if design else "—")
        cycles = num("cycle_count")
        self.stats["cycles"].set_label(str(cycles) if cycles else "—")
        limit = num("charge_control_end_threshold") or 100
        self.stats["limit"].set_label(f"{limit}%")
        self.stats["power"].set_label(f"{watts:.1f} W" if watts > 0.05 else "—")
        self.stats["state"].set_label({"Not charging": "Holding"}.get(status, status))
        self.mark(self.limit_btns, limit)

    # ── asusctl / supergfxctl (느림) ──
    def refresh_tools(self):
        def work():
            _, prof, _ = run("asusctl", "profile", "get")
            m = re.search(r"Active profile:\s*(\w+)", prof)
            _, mode, _ = run("supergfxctl", "-g")
            _, modes, _ = run("supergfxctl", "-s")
            return (m.group(1) if m else None, mode.strip(),
                    [x.strip() for x in modes.strip("[] \n").split(",") if x.strip()])
        self.bg(work, self.render_tools)

    def render_tools(self, res):
        profile, gpu, gpus = res
        self.mark(self.profile_btns, profile)
        if not self.gpu_btns:
            for g in gpus:
                b = Gtk.Button(label=GPU_LABELS.get(g, g), focusable=False)
                b.add_css_class("seg")
                b.connect("clicked", lambda _b, k=g: self.set_gpu(k))
                self.gpu_box.append(b)
                self.gpu_btns[g] = b
        self.mark(self.gpu_btns, gpu)
        self.ready()

    def after(self, res):
        code, _, err = res
        self.say("" if code == 0 else (err.splitlines() or ["실패"])[-1][:80])
        self.refresh_sysfs()
        self.refresh_tools()

    def set_profile(self, name):
        self.mark(self.profile_btns, name)
        self.bg(lambda: run("asusctl", "profile", "set", name), self.after)

    def set_limit(self, n):
        self.mark(self.limit_btns, n)
        self.bg(lambda: run("asusctl", "battery", "limit", str(n)), self.after)

    def set_gpu(self, mode):
        self.mark(self.gpu_btns, mode)
        self.say(f"GPU 모드 → {GPU_LABELS.get(mode, mode)} (로그아웃 후 적용)")
        self.bg(lambda: run("supergfxctl", "-m", mode, timeout=30),
                lambda r: self.say(f"GPU 모드 → {GPU_LABELS.get(mode, mode)} · 로그아웃 후 적용") if r[0] == 0 else self.after(r))


if __name__ == "__main__":
    main("org.kyulio.BatteryPanel", BatteryPanel)

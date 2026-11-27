#!/usr/bin/python3
"""오디오 패널: 출력/입력 볼륨 · 장치 선택 · 앱별 볼륨 (pactl / PipeWire)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panel_base import GLib, Gtk, Panel, label, main, run, sep  # noqa: E402

ICON_VOL = ["\U000F057F", "\U000F0580", "\U000F057E"]
ICON_MUTE = "\U000F075F"
ICON_MIC, ICON_MIC_OFF = "\U000F036C", "\U000F036D"
ICON_HEADPHONE, ICON_HEADSET, ICON_SPEAKER, ICON_HDMI = "\U000F02CB", "\U000F02CE", "\U000F04C3", "\U000F0379"
ICON_APP = "\U000F075A"

CSS = """
.vol-btn {
  background: none; border: none; box-shadow: none; color: #ffffff;
  font-size: 18px; min-width: 32px; min-height: 30px; padding: 0; border-radius: 7px;
}
.vol-btn:hover { background: rgba(255, 255, 255, 0.1); }
.vol-btn.muted { color: #666666; }
.vol-pct { color: #ffffff; min-width: 42px; }
.slider-card {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px; padding: 6px 10px;
}
scale { padding: 0; }
scale trough { background: rgba(255, 255, 255, 0.14); border: none; border-radius: 6px; min-height: 6px; }
scale trough highlight { background: #ffffff; border: none; border-radius: 6px; }
scale slider {
  background: #ffffff; border: none; box-shadow: none;
  min-width: 14px; min-height: 14px; margin: -5px; border-radius: 50%;
}
.app-name { color: #dddddd; font-size: 11px; }
"""


def pct(vol):
    try:
        ch = next(iter(vol.values()))
        return int(str(ch["value_percent"]).rstrip("%"))
    except (StopIteration, KeyError, ValueError, AttributeError):
        return 0


def dev_icon(name, kind):
    if kind == "source":
        return ICON_HEADSET if "bluez" in name else ICON_MIC
    if "bluez" in name:
        return ICON_HEADPHONE
    if "hdmi" in name.lower():
        return ICON_HDMI
    return ICON_SPEAKER


def vol_icon(p, muted):
    if muted or p == 0:
        return ICON_MUTE
    return ICON_VOL[0 if p < 34 else 1 if p < 67 else 2]


class VolumeRow(Gtk.Box):
    """[음소거 버튼] [슬라이더] [xx%] — 드래그 중에는 외부 갱신을 무시."""

    def __init__(self, on_volume, on_mute, mic=False):
        super().__init__(spacing=6)
        self.add_css_class("slider-card")
        self.mic = mic
        self.on_volume = on_volume
        self.btn = Gtk.Button(focusable=False)
        self.btn.add_css_class("vol-btn")
        self.btn.connect("clicked", lambda *_: on_mute())
        self.append(self.btn)
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.scale.set_hexpand(True)
        self.scale.set_draw_value(False)
        self.scale.set_focusable(False)
        self.scale.connect("value-changed", self._changed)
        self.append(self.scale)
        self.pct = label("", "vol-pct", xalign=1)
        self.append(self.pct)
        self.setting = False
        self.dragging_until = 0

    def _changed(self, scale):
        v = int(scale.get_value())
        self.pct.set_label(f"{v}%")
        if not self.setting:
            self.dragging_until = GLib.get_monotonic_time() + 1_500_000
            self.on_volume(v)

    def update(self, p, muted):
        if GLib.get_monotonic_time() < self.dragging_until:
            return
        self.setting = True
        self.scale.set_value(min(p, 100))
        self.setting = False
        self.pct.set_label(f"{p}%")
        if self.mic:
            self.btn.set_label(ICON_MIC_OFF if muted else ICON_MIC)
        else:
            self.btn.set_label(vol_icon(p, muted))
        (self.btn.add_css_class if muted else self.btn.remove_css_class)("muted")


class AudioPanel(Panel):
    def __init__(self, app):
        super().__init__(app)
        self.state = None
        self.layout_key = None
        self.app_rows = {}
        self.pending = {}
        card = self.card

        head = Gtk.Box(spacing=10)
        card.append(head)
        self.hero_icon = label(ICON_VOL[2], "hero-icon", xalign=0.5)
        head.append(self.hero_icon)
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        head.append(titles)
        self.hero_name = label("Audio", "hero-name", ellipsize=3)
        self.hero_sub = label("", "hero-sub", ellipsize=3)
        titles.append(self.hero_name)
        titles.append(self.hero_sub)
        mixer = Gtk.Button(label="\U000F0493", focusable=False, valign=Gtk.Align.CENTER,
                           tooltip_text="pavucontrol 열기")
        mixer.add_css_class("icon-btn")
        mixer.connect("clicked", lambda *_: (GLib.spawn_command_line_async("pavucontrol"), self.close()))
        head.append(mixer)

        card.append(label("OUTPUT", "section"))
        self.out_vol = VolumeRow(lambda v: self.set_vol("sink", "@DEFAULT_SINK@", v),
                                 lambda: self.toggle_mute("sink", "@DEFAULT_SINK@"))
        card.append(self.out_vol)
        card.append(label("INPUT", "section"))
        self.in_vol = VolumeRow(lambda v: self.set_vol("source", "@DEFAULT_SOURCE@", v),
                                lambda: self.toggle_mute("source", "@DEFAULT_SOURCE@"), mic=True)
        card.append(self.in_vol)

        card.append(sep())
        scroller = Gtk.ScrolledWindow(propagate_natural_height=True, max_content_height=400,
                                      hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.lists = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        scroller.set_child(self.lists)
        card.append(scroller)

        self.refresh()
        GLib.timeout_add(1000, lambda: self.refresh() or True)

    # ── 데이터 ──
    def collect(self):
        def load(kind):
            _, out, _ = run("pactl", "-f", "json", "list", kind)
            try:
                return json.loads(out or "[]")
            except ValueError:
                return []
        sinks = load("sinks")
        sources = [s for s in load("sources") if not s["name"].endswith(".monitor")]
        inputs = load("sink-inputs")
        return {
            "sinks": sinks, "sources": sources, "inputs": inputs,
            "def_sink": run("pactl", "get-default-sink")[1],
            "def_source": run("pactl", "get-default-source")[1],
        }

    def refresh(self):
        self.bg(self.collect, self.render)

    def render(self, d):
        self.state = d
        sink = next((s for s in d["sinks"] if s["name"] == d["def_sink"]), None)
        src = next((s for s in d["sources"] if s["name"] == d["def_source"]), None)
        if sink:
            p = pct(sink["volume"])
            self.out_vol.update(p, sink["mute"])
            self.hero_icon.set_label(vol_icon(p, sink["mute"]))
            self.hero_name.set_label(sink["description"])
            self.hero_sub.set_label(("MUTED" if sink["mute"] else f"VOLUME {p}%")
                                    + (f" · MIC {pct(src['volume'])}%" if src else ""))
        if src:
            self.in_vol.update(pct(src["volume"]), src["mute"])

        key = (tuple((s["name"], s["description"]) for s in d["sinks"]), d["def_sink"],
               tuple((s["name"], s["description"]) for s in d["sources"]), d["def_source"],
               tuple(i["index"] for i in d["inputs"]))
        if key != self.layout_key:
            self.layout_key = key
            self.rebuild(d)
        for i in d["inputs"]:
            row = self.app_rows.get(i["index"])
            if row:
                row.update(pct(i["volume"]), i["mute"])

    def rebuild(self, d):
        while (c := self.lists.get_first_child()) is not None:
            self.lists.remove(c)
        self.app_rows = {}
        for title, kind, items, default in (("OUTPUT DEVICES", "sink", d["sinks"], d["def_sink"]),
                                            ("INPUT DEVICES", "source", d["sources"], d["def_source"])):
            if not items:
                continue
            self.lists.append(label(title, "section"))
            for dev in items:
                self.lists.append(self.device_row(kind, dev, dev["name"] == default))
        if d["inputs"]:
            self.lists.append(label("APPLICATIONS", "section"))
            for i in d["inputs"]:
                props = i.get("properties", {})
                name = props.get("application.name") or props.get("media.name") or f"Stream {i['index']}"
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, margin_top=2)
                box.append(label(f"{ICON_APP}  {name}", "app-name", ellipsize=3, margin_start=4))
                idx = str(i["index"])
                row = VolumeRow(lambda v, x=idx: self.set_vol("sink-input", x, v),
                                lambda x=idx: self.toggle_mute("sink-input", x))
                box.append(row)
                self.lists.append(box)
                self.app_rows[i["index"]] = row

    def device_row(self, kind, dev, active):
        btn = Gtk.Button(focusable=False)
        btn.add_css_class("row-btn")
        if active:
            btn.add_css_class("current")
        box = Gtk.Box(spacing=8)
        box.append(label(dev_icon(dev["name"], kind), "row-icon", xalign=0.5))
        names = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        names.append(label(dev["description"], "row-name", ellipsize=3))
        if active:
            names.append(label("Active", "row-sub"))
        box.append(names)
        btn.set_child(box)
        btn.connect("clicked", lambda *_: self.set_default(kind, dev["name"]))
        return btn

    # ── 동작 ──
    def set_vol(self, kind, target, v):
        # 드래그 중 너무 많은 pactl 호출을 막기 위해 50ms 묶음
        self.pending[(kind, target)] = v
        if len(self.pending) == 1:
            GLib.timeout_add(50, self._flush_vol)

    def _flush_vol(self):
        items, self.pending = self.pending, {}
        for (kind, target), v in items.items():
            GLib.spawn_async(["pactl", f"set-{kind}-volume", target, f"{v}%"],
                             flags=GLib.SpawnFlags.SEARCH_PATH)
        return False

    def toggle_mute(self, kind, target):
        self.bg(lambda: run("pactl", f"set-{kind}-mute", target, "toggle"), lambda _r: self.refresh())

    def set_default(self, kind, name):
        def work():
            run("pactl", f"set-default-{kind}", name)
            what = "sink-inputs" if kind == "sink" else "source-outputs"
            move = "move-sink-input" if kind == "sink" else "move-source-output"
            _, out, _ = run("pactl", "list", "short", what)
            for line in out.splitlines():
                run("pactl", move, line.split("\t")[0], name)
        self.bg(work, lambda _r: self.refresh())


if __name__ == "__main__":
    main("org.kyulio.AudioPanel", AudioPanel, CSS)

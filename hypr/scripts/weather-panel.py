#!/usr/bin/python3
"""날씨 패널 (시계 아래 가운데): 현재 기온 / 체감·바람·습도 / 3일 예보."""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panel_base import GLib, Gtk, Panel, label, main, sep  # noqa: E402
import weather  # noqa: E402

CSS = """
.w-icon  { font-size: 52px; color: #ffffff; min-width: 70px; }
.w-temp  { font-size: 52px; font-weight: 300; color: #ffffff; }
.w-unit  { font-size: 18px; color: #aaaaaa; margin-top: 10px; }
.w-place { font-size: 12px; color: #ffffff; }
.w-key   { font-size: 10px; color: #777777; letter-spacing: 1px; }
.w-val   { font-size: 15px; color: #ffffff; }
.d-name  { font-size: 10px; color: #777777; letter-spacing: 1px; }
.d-icon  { font-size: 22px; color: #dddddd; }
.d-max   { font-size: 13px; color: #ffffff; }
.d-min   { font-size: 13px; color: #777777; }
"""

ICON_PIN = "\U000F034E"
WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


class WeatherPanel(Panel):
    ANCHOR = "center"
    WIDTH = 460

    def __init__(self, app):
        super().__init__(app)
        card = self.card
        card.set_spacing(12)

        top = Gtk.Box(spacing=12)
        card.append(top)
        self.icon = label("", "w-icon", xalign=0.5)
        top.append(self.icon)
        temp_box = Gtk.Box(spacing=2, valign=Gtk.Align.CENTER)
        self.temp = label("—", "w-temp")
        temp_box.append(self.temp)
        temp_box.append(label("°C", "w-unit", valign=Gtk.Align.START))
        top.append(temp_box)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, hexpand=True,
                        valign=Gtk.Align.CENTER, margin_start=10)
        top.append(right)
        self.place = label("", "w-place")
        right.append(self.place)
        grid = Gtk.Grid(column_spacing=16, row_spacing=2, column_homogeneous=True)
        right.append(grid)
        self.vals = {}
        for i, (k, name) in enumerate([("feels", "FEELS"), ("wind", "WIND"), ("humidity", "HUMID")]):
            grid.attach(label(name, "w-key"), i, 0, 1, 1)
            v = label("—", "w-val")
            grid.attach(v, i, 1, 1, 1)
            self.vals[k] = v

        card.append(sep())
        self.days = Gtk.Box(spacing=8, homogeneous=True)
        card.append(self.days)

        self.load(False)

    def load(self, force):
        self.bg(lambda: weather.get(force), self.render)

    def render(self, d):
        if not d:
            self.place.set_label("날씨 정보를 가져올 수 없어요")
            self.ready()
            return
        self.icon.set_label(d["icon"])
        self.temp.set_label(str(d["temp"]))
        self.place.set_label(f"{ICON_PIN} {d['place']}  ·  {d['desc']}")
        self.vals["feels"].set_label(f"{d['feels']}°C")
        self.vals["wind"].set_label(f"{d['wind']} km/h")
        self.vals["humidity"].set_label(f"{d['humidity']}%")

        while (c := self.days.get_first_child()) is not None:
            self.days.remove(c)
        today = datetime.date.today()
        for day in d["days"]:
            date = datetime.date.fromisoformat(day["date"])
            name = "TODAY" if date == today else WEEKDAYS[date.weekday()]
            col = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
            col.append(label(day["icon"], "d-icon"))
            texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER)
            texts.append(label(name, "d-name"))
            temps = Gtk.Box(spacing=6)
            temps.append(label(f"{day['max']}°", "d-max"))
            temps.append(label(f"{day['min']}°", "d-min"))
            texts.append(temps)
            col.append(texts)
            self.days.append(col)
        self.ready()

        # 캐시가 오래됐으면 새로 받아옴
        if not d.get("_fresh") and GLib.get_real_time() / 1e6 - d.get("fetched", 0) > weather.MAX_AGE:
            self.bg(lambda: weather.get(True), lambda nd: nd and self.render(dict(nd, _fresh=True)))


if __name__ == "__main__":
    main("org.kyulio.WeatherPanel", WeatherPanel, CSS)

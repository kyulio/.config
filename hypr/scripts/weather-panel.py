#!/usr/bin/python3
"""날씨 패널 (시계 아래 가운데). 다른 패널과 같은 레이아웃.

캐시를 즉시 그리고, 오래됐으면 백그라운드에서 새로 받아 갱신.
"""
import datetime
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panel_base import Gtk, Panel, label, main, sep, stat_grid  # noqa: E402
import weather  # noqa: E402

ICON_REFRESH = "\U000F0450"
ICON_RAIN = "\U000F058C"
WEEKDAYS = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]

CSS = """
.day-max { color: #ffffff; min-width: 34px; }
.day-min { color: #777777; min-width: 34px; }
.day-rain { color: #888888; font-size: 11px; min-width: 52px; }
"""


def to_24h(t):
    try:
        return datetime.datetime.strptime(t, "%I:%M %p").strftime("%H:%M")
    except (TypeError, ValueError):
        return t or "—"


class WeatherPanel(Panel):
    ANCHOR = "center"
    def __init__(self, app):
        super().__init__(app)
        card = self.card

        head = Gtk.Box(spacing=10)
        card.append(head)
        self.hero_icon = label("", "hero-icon", xalign=0.5)
        head.append(self.hero_icon)
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        head.append(titles)
        self.hero_name = label("Weather", "hero-name", ellipsize=3)
        self.hero_sub = label("", "hero-sub", ellipsize=3)
        titles.append(self.hero_name)
        titles.append(self.hero_sub)
        self.refresh_btn = Gtk.Button(label=ICON_REFRESH, focusable=False, valign=Gtk.Align.CENTER,
                                      tooltip_text="새로고침")
        self.refresh_btn.add_css_class("icon-btn")
        self.refresh_btn.connect("clicked", lambda *_: self.fetch(True))
        head.append(self.refresh_btn)
        self.temp = label("", "hero-big", xalign=1)
        head.append(self.temp)

        card.append(sep())
        grid, self.stats = stat_grid([
            ("feels", "Feels like"), ("humidity", "Humidity"),
            ("wind", "Wind"), ("uv", "UV index"),
            ("sunrise", "Sunrise"), ("sunset", "Sunset")])
        card.append(grid)
        card.append(sep())

        card.append(label("FORECAST", "section"))
        self.days = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        card.append(self.days)

        self.status = label("", "status", visible=False)
        card.append(self.status)

        d = weather.cached()
        self.render(d)
        if weather.is_stale(d):
            self.fetch(True)

    def say(self, text):
        self.status.set_label(text)
        self.status.set_visible(bool(text))

    def fetch(self, force):
        self.say("업데이트 중…")
        self.refresh_btn.set_sensitive(False)

        def done(d):
            self.refresh_btn.set_sensitive(True)
            self.say("" if d else "날씨 정보를 가져올 수 없어요")
            if d:
                self.render(d)
        self.bg(lambda: weather.get(force), done)

    def render(self, d):
        if not d:
            self.hero_sub.set_label("NO DATA")
            return
        self.hero_icon.set_label(d["icon"])
        self.hero_name.set_label(d["place"])
        updated = time.strftime("%H:%M", time.localtime(d.get("fetched", 0)))
        self.hero_sub.set_label(f"{d['desc']} · UPDATED {updated}")
        self.temp.set_label(f"{d['temp']}°")
        self.stats["feels"].set_label(f"{d['feels']}°C")
        self.stats["humidity"].set_label(f"{d['humidity']}%")
        self.stats["wind"].set_label(f"{d['wind']} km/h")
        self.stats["uv"].set_label(str(d.get("uv", "—")))
        self.stats["sunrise"].set_label(to_24h(d.get("sunrise")))
        self.stats["sunset"].set_label(to_24h(d.get("sunset")))

        while (c := self.days.get_first_child()) is not None:
            self.days.remove(c)
        today = datetime.date.today()
        for day in d["days"]:
            date = datetime.date.fromisoformat(day["date"])
            name = "오늘" if date == today else "내일" if date == today + datetime.timedelta(1) \
                else WEEKDAYS[date.weekday()]
            row = Gtk.Box(spacing=8)
            row.add_css_class("row-btn")
            if date == today:
                row.add_css_class("current")
            row.append(label(day["icon"], "row-icon", xalign=0.5))
            names = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
            names.append(label(name, "row-name"))
            names.append(label(day.get("desc", ""), "row-sub"))
            row.append(names)
            if day.get("rain") is not None:
                row.append(label(f"{ICON_RAIN} {day['rain']}%", "day-rain", xalign=1))
            row.append(label(f"{day['max']}°", "day-max", xalign=1))
            row.append(label(f"{day['min']}°", "day-min", xalign=1))
            self.days.append(row)


if __name__ == "__main__":
    main("org.kyulio.WeatherPanel", WeatherPanel, CSS)

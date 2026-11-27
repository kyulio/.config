#!/usr/bin/python3
"""달력 패널 (시계 아래 가운데). ←/→ 또는 스크롤: 달 이동, Home/t 또는 제목 클릭: 오늘."""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panel_base import Gdk, Gtk, Panel, label, main, sep  # noqa: E402

ICON_CAL = "\U000F00ED"
ICON_PREV, ICON_NEXT = "\U000F0141", "\U000F0142"
WEEKDAYS = ("SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT")


class CalendarPanel(Panel):
    ANCHOR = "center"
    WIDTH = 360
    CSS = """
    .day { font-size: 13px; min-width: 40px; min-height: 34px; border-radius: 7px; color: #dddddd; }
    .day.weekend { color: #999999; }
    .day.outside { color: #3c3c3c; }
    .day.today { background: #ffffff; color: #000000; font-weight: 700; }
    .wd { color: #777777; font-size: 10px; font-weight: 700; letter-spacing: 1px; }
    .title-btn { background: none; border: none; box-shadow: none; padding: 0; min-height: 0; }
    """

    def __init__(self, app):
        super().__init__(app)
        today = datetime.date.today()
        self.year, self.month = today.year, today.month
        card = self.card

        head = Gtk.Box(spacing=10)
        card.append(head)
        head.append(label(ICON_CAL, "hero-icon", xalign=0.5))
        title_btn = Gtk.Button(focusable=False, hexpand=True, tooltip_text="오늘로")
        title_btn.add_css_class("title-btn")
        title_btn.connect("clicked", lambda *_: self.go_today())
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER)
        self.hero_name = label("", "hero-name")
        titles.append(self.hero_name)
        titles.append(label(today.strftime("TODAY · %a %d %b").upper(), "hero-sub"))
        title_btn.set_child(titles)
        head.append(title_btn)
        for glyph, step in ((ICON_PREV, -1), (ICON_NEXT, 1)):
            b = Gtk.Button(label=glyph, focusable=False, valign=Gtk.Align.CENTER)
            b.add_css_class("icon-btn")
            b.connect("clicked", lambda _b, s=step: self.shift(s))
            head.append(b)

        card.append(sep())
        grid = Gtk.Grid(column_spacing=2, row_spacing=2, column_homogeneous=True)
        card.append(grid)
        for col, name in enumerate(WEEKDAYS):
            grid.attach(label(name, "wd", xalign=0.5, margin_bottom=4), col, 0, 1, 1)
        self.cells = []
        for row in range(6):
            for col in range(7):
                cell = label("", "day", xalign=0.5)
                if col in (0, 6):
                    cell.add_css_class("weekend")
                grid.attach(cell, col, row + 1, 1, 1)
                self.cells.append(cell)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self.on_key)
        self.add_controller(keys)
        scroll = Gtk.EventControllerScroll(flags=Gtk.EventControllerScrollFlags.VERTICAL)
        scroll.connect("scroll", lambda _c, _x, y: self.shift(1 if y > 0 else -1) or True)
        self.add_controller(scroll)
        self.render()

    def shift(self, step):
        i = self.year * 12 + (self.month - 1) + step
        self.year, self.month = i // 12, i % 12 + 1
        self.render()

    def go_today(self):
        t = datetime.date.today()
        self.year, self.month = t.year, t.month
        self.render()

    def render(self):
        today = datetime.date.today()
        first = datetime.date(self.year, self.month, 1)
        self.hero_name.set_label(f"{self.year}년 {self.month}월")
        start = first - datetime.timedelta(days=(first.weekday() + 1) % 7)
        for i, cell in enumerate(self.cells):
            day = start + datetime.timedelta(days=i)
            cell.set_label(str(day.day))
            for c in ("outside", "today"):
                cell.remove_css_class(c)
            if day == today:
                cell.add_css_class("today")
            elif day.month != self.month:
                cell.add_css_class("outside")

    def on_key(self, _c, key, _code, _state):
        if key in (Gdk.KEY_Left, Gdk.KEY_Up):
            self.shift(-1)
        elif key in (Gdk.KEY_Right, Gdk.KEY_Down):
            self.shift(1)
        elif key in (Gdk.KEY_Home, Gdk.KEY_t):
            self.go_today()
        else:
            return False
        return True


if __name__ == "__main__":
    main("org.kyulio.CalendarPanel", CalendarPanel)

#!/usr/bin/python3
import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gtk

CSS = """
window { background: transparent; }

.card {
  background: rgba(8, 8, 8, 0.68);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 10px;
  padding: 16px;
  font-family: "Noto Sans CJK KR", "JetBrainsMono Nerd Font Propo";
  color: #e6e6e6;
}

.month {
  background: none;
  border: none;
  box-shadow: none;
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 7px;
  min-height: 0;
}

.nav {
  background: none;
  border: none;
  box-shadow: none;
  color: #aaaaaa;
  font-size: 18px;
  min-width: 32px;
  min-height: 32px;
  padding: 0;
  border-radius: 7px;
}

.month:hover, .nav:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.weekday {
  color: #777777;
  font-size: 12px;
  margin-bottom: 4px;
}

.day {
  font-size: 14px;
  min-width: 38px;
  min-height: 34px;
  border-radius: 7px;
  color: #dddddd;
}

.day.outside { color: #444444; }

.day.today {
  background: #ffffff;
  color: #000000;
  font-weight: 700;
}
"""

WEEKDAYS = ("Su", "Mo", "Tu", "We", "Th", "Fr", "Sa")


class CalendarWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Calendar", decorated=False, resizable=False)
        today = datetime.date.today()
        self.year, self.month = today.year, today.month
        self.was_active = False
        self.cells = []

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.add_css_class("card")
        self.set_child(card)

        header = Gtk.Box(spacing=4)
        card.append(header)
        header.append(self.nav_button("\U000f0141", -1))
        self.title_button = Gtk.Button(hexpand=True, focusable=False)
        self.title_button.add_css_class("month")
        self.title_button.set_tooltip_text("Back to today")
        self.title_button.connect("clicked", lambda *_: self.go_today())
        header.append(self.title_button)
        header.append(self.nav_button("\U000f0142", 1))

        grid = Gtk.Grid(column_spacing=2, row_spacing=2, column_homogeneous=True)
        card.append(grid)
        for col, name in enumerate(WEEKDAYS):
            label = Gtk.Label(label=name)
            label.add_css_class("weekday")
            grid.attach(label, col, 0, 1, 1)
        for row in range(6):
            for col in range(7):
                label = Gtk.Label()
                label.add_css_class("day")
                grid.attach(label, col, row + 1, 1, 1)
                self.cells.append(label)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self.on_key)
        self.add_controller(keys)

        scroll = Gtk.EventControllerScroll(flags=Gtk.EventControllerScrollFlags.VERTICAL)
        scroll.connect("scroll", lambda _c, _x, y: self.shift(1 if y > 0 else -1) or True)
        self.add_controller(scroll)

        self.connect("notify::is-active", self.on_active_changed)
        self.render()

    def nav_button(self, glyph, step):
        button = Gtk.Button(label=glyph, focusable=False)
        button.add_css_class("nav")
        button.connect("clicked", lambda *_: self.shift(step))
        return button

    def shift(self, step):
        index = self.year * 12 + (self.month - 1) + step
        self.year, self.month = index // 12, index % 12 + 1
        self.render()

    def go_today(self):
        today = datetime.date.today()
        self.year, self.month = today.year, today.month
        self.render()

    def render(self):
        today = datetime.date.today()
        first = datetime.date(self.year, self.month, 1)
        self.title_button.set_label(first.strftime("%B %Y"))
        start = first - datetime.timedelta(days=(first.weekday() + 1) % 7)
        for offset, cell in enumerate(self.cells):
            day = start + datetime.timedelta(days=offset)
            cell.set_label(str(day.day))
            cell.remove_css_class("outside")
            cell.remove_css_class("today")
            if day == today:
                cell.add_css_class("today")
            elif day.month != self.month:
                cell.add_css_class("outside")

    def on_key(self, _controller, key, _code, _state):
        if key == Gdk.KEY_Escape:
            self.close()
        elif key in (Gdk.KEY_Left, Gdk.KEY_Up):
            self.shift(-1)
        elif key in (Gdk.KEY_Right, Gdk.KEY_Down):
            self.shift(1)
        elif key in (Gdk.KEY_Home, Gdk.KEY_t):
            self.go_today()
        else:
            return False
        return True

    def on_active_changed(self, *_):
        if self.is_active():
            self.was_active = True
        elif self.was_active:
            self.close()


class CalendarApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.kyulio.Calendar")
        self.window = None

    def do_activate(self):
        if self.window:
            self.window.close()
            return
        provider = Gtk.CssProvider()
        provider.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        self.window = CalendarWindow(self)
        self.window.present()


if __name__ == "__main__":
    CalendarApp().run(None)

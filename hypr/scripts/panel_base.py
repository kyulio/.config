"""waybar 팝업 패널 공통 모듈 (Wi-Fi / 배터리 / 날씨 …).

- gtk4-layer-shell 로 화면 모서리에 고정 (swaync 알림센터와 같은 방식)
- 같은 스크립트를 다시 실행하면 닫힘(토글), 바깥을 클릭하면 닫힘
- 공통 CSS: swaync 와 같은 모노크롬 카드
"""
import os
import subprocess
import sys

_LIB = "/usr/lib/libgtk4-layer-shell.so"


def ensure_layer_shell():
    """gtk4-layer-shell 은 libwayland 보다 먼저 로드돼야 해서 LD_PRELOAD 로 재실행."""
    if os.environ.get("KYULIO_PANEL_PRELOADED") != "1":
        env = dict(os.environ, KYULIO_PANEL_PRELOADED="1",
                   LD_PRELOAD=(_LIB + " " + os.environ.get("LD_PRELOAD", "")).strip())
        os.execve(sys.executable, [sys.executable] + sys.argv, env)
    # 자식 프로세스(nmcli 등)에는 물려주지 않음
    os.environ.pop("LD_PRELOAD", None)


ensure_layer_shell()

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402
from gi.repository import Gtk4LayerShell as Layer  # noqa: E402

BASE_CSS = """
window { background: transparent; }
window.backdrop { background: rgba(0, 0, 0, 0.01); }
window.backdrop.dim { background: rgba(0, 0, 0, 0.45); }  /* 완전 투명이면 그려지지 않아 클릭을 못 받음 */

.card {
  transition: background 150ms ease-out;
  background: rgba(8, 8, 8, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 10px;
  padding: 14px;
  font-family: "GeistMono Nerd Font Propo", "Pretendard";
  font-size: 12px;
  color: #dddddd;
}
.card:hover { background: rgba(8, 8, 8, 0.95); }

.hero-icon { font-size: 26px; color: #ffffff; min-width: 36px; }
.hero-name { font-size: 16px; font-weight: 700; color: #ffffff; }
.hero-sub  { font-size: 10px; color: #888888; letter-spacing: 1px; }
.hero-big  { font-size: 30px; font-weight: 300; color: #ffffff; }

.icon-btn {
  background: none; border: none; box-shadow: none;
  color: #aaaaaa; font-size: 16px;
  min-width: 30px; min-height: 30px; padding: 0; border-radius: 7px;
}
.icon-btn:hover { background: rgba(255, 255, 255, 0.1); color: #ffffff; }

switch { background: #333333; border: none; border-radius: 12px; }
switch:checked { background: #ffffff; }
switch slider { background: #888888; border: none; border-radius: 12px; min-width: 18px; min-height: 18px; }
switch:checked slider { background: #000000; }

.sep { background: rgba(255, 255, 255, 0.10); min-height: 1px; margin: 4px 0; }

.stat-key { color: #777777; }
.stat-val { color: #ffffff; }

.section {
  color: #777777; font-size: 10px; font-weight: 700;
  letter-spacing: 1px; margin: 6px 2px 2px 2px;
}

.seg {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 7px; box-shadow: none;
  color: #bbbbbb; padding: 7px 0; min-height: 0;
}
.seg:hover { background: rgba(255, 255, 255, 0.10); color: #ffffff; }
.seg.on { background: rgba(255, 255, 255, 0.16); border-color: rgba(255, 255, 255, 0.35); color: #ffffff; }
.seg.primary { background: #ffffff; border-color: #ffffff; color: #000000; font-weight: 700; }
.seg.primary:hover { background: #dddddd; }
.seg:disabled { opacity: 0.4; }

.row-btn {
  background: none; border: 1px solid transparent; box-shadow: none;
  border-radius: 8px; padding: 8px 10px; color: #dddddd; min-height: 0;
}
.row-btn:hover { background: rgba(255, 255, 255, 0.08); }
.row-btn.current { background: rgba(255, 255, 255, 0.10); border-color: rgba(255, 255, 255, 0.14); }
.row-icon { font-size: 15px; min-width: 24px; color: #ffffff; }
.row-name { color: #ffffff; }
.row-sub  { color: #888888; font-size: 10px; }
.row-dim  { color: #777777; }

entry {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 7px; color: #ffffff; box-shadow: none;
  padding: 4px 8px; min-height: 26px;
}
entry:focus-within { border-color: rgba(255, 255, 255, 0.4); outline: none; }

progressbar trough {
  background: rgba(255, 255, 255, 0.14); border: none;
  border-radius: 6px; min-height: 8px;
}
progressbar progress {
  background: #ffffff; border: none;
  border-radius: 6px; min-height: 8px;
}

.status { color: #888888; font-size: 11px; }

/* 슬라이더 (사운드 패널 / 알림센터와 동일) */
scale { padding: 0; margin: 0 4px; }
scale trough { background: rgba(255, 255, 255, 0.14); border: none; border-radius: 6px; min-height: 6px; }
scale trough highlight { background: #ffffff; border: none; border-radius: 6px; }
scale slider {
  background: #ffffff; border: none; box-shadow: none;
  min-width: 14px; min-height: 14px; margin: -5px; border-radius: 50%;
}

scrollbar { background: transparent; }
scrollbar slider { background: rgba(255, 255, 255, 0.2); min-width: 4px; border-radius: 4px; }
"""


def run(*args, timeout=15):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:  # noqa: BLE001
        return 1, "", str(e)


def label(text="", css=None, xalign=0.0, **kw):
    lbl = Gtk.Label(label=text, xalign=xalign, **kw)
    for c in (css.split() if css else []):
        lbl.add_css_class(c)
    return lbl


def sep():
    s = Gtk.Box()
    s.add_css_class("sep")
    return s


def stat_grid(keys):
    """[(key, 표시이름), ...] → (Gtk.Grid, {key: 값 라벨}) 2열 그리드."""
    grid = Gtk.Grid(column_spacing=14, row_spacing=4, column_homogeneous=True)
    values = {}
    for i, (k, name) in enumerate(keys):
        row, col = divmod(i, 2)
        box = Gtk.Box()
        box.append(label(name, "stat-key", hexpand=True))
        v = label("—", "stat-val", xalign=1)
        box.append(v)
        grid.attach(box, col, row, 1, 1)
        values[k] = v
    return grid, values


class Panel(Gtk.ApplicationWindow):
    """layer-shell 카드 패널. 하위 클래스는 self.card 에 내용을 채움.

    주기 작업은 self.every() 로 등록 → 닫힐 때 자동 정리 (상시 실행 데몬에서 누수 방지).
    """

    ANCHOR = "right"  # "right"(우측 상단) | "left"(좌측 상단) | "center"(상단 가운데) | "middle"(화면 정중앙)
    WIDTH = 400
    CSS = ""
    LAYER = "top"     # "top" | "overlay"
    DIM = False       # True 면 뒤 화면을 어둡게

    def __init__(self, app):
        super().__init__(application=app, decorated=False, resizable=False)
        self.set_default_size(self.WIDTH, -1)
        self.set_size_request(self.WIDTH, -1)
        self.hold_open = False
        self.alive = True
        self._sources = []
        self._cleanups = []

        # 바깥 클릭을 받아 패널을 닫는 투명 전체화면 레이어 (swaync 의 cover-screen 과 같은 방식)
        self.backdrop = Gtk.Window(application=app, decorated=False)
        self.backdrop.add_css_class("backdrop")
        if self.DIM:
            self.backdrop.add_css_class("dim")
        layer = Layer.Layer.OVERLAY if self.LAYER == "overlay" else Layer.Layer.TOP
        Layer.init_for_window(self.backdrop)
        Layer.set_namespace(self.backdrop, "kyulio-backdrop")
        Layer.set_layer(self.backdrop, layer)
        if self.ANCHOR == "middle":
            Layer.set_exclusive_zone(self.backdrop, -1)  # waybar 위까지 덮음
        Layer.set_keyboard_mode(self.backdrop, Layer.KeyboardMode.NONE)
        for edge in (Layer.Edge.TOP, Layer.Edge.BOTTOM, Layer.Edge.LEFT, Layer.Edge.RIGHT):
            Layer.set_anchor(self.backdrop, edge, True)
        self.backdrop.set_child(Gtk.Box(hexpand=True, vexpand=True))
        click = Gtk.GestureClick(button=0)
        click.connect("pressed", lambda *_: self.close())
        self.backdrop.add_controller(click)

        Layer.init_for_window(self)
        Layer.set_namespace(self, "kyulio-panel")
        Layer.set_layer(self, layer)
        Layer.set_keyboard_mode(self, Layer.KeyboardMode.EXCLUSIVE)
        if self.ANCHOR != "middle":
            Layer.set_anchor(self, Layer.Edge.TOP, True)
            Layer.set_margin(self, Layer.Edge.TOP, 8)
        if self.ANCHOR == "right":
            Layer.set_anchor(self, Layer.Edge.RIGHT, True)
            Layer.set_margin(self, Layer.Edge.RIGHT, 8)
        elif self.ANCHOR == "left":
            Layer.set_anchor(self, Layer.Edge.LEFT, True)
            Layer.set_margin(self, Layer.Edge.LEFT, 8)

        self.card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.card.add_css_class("card")
        self.set_child(self.card)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)
        self.connect("close-request", self._on_close)

    # ── 수명 관리 ──
    def every(self, ms, fn):
        """ms 마다 fn() 실행 (패널이 닫히면 자동 해제)."""
        self._sources.append(GLib.timeout_add(ms, lambda: bool(self.alive and (fn() or True))))

    def on_cleanup(self, fn):
        self._cleanups.append(fn)

    def _on_close(self, *_):
        self.alive = False
        for sid in self._sources:
            GLib.source_remove(sid)
        self._sources.clear()
        for fn in self._cleanups:
            try:
                fn()
            except Exception:  # noqa: BLE001
                pass
        self.backdrop.destroy()
        return False

    def bg(self, fn, done=None):
        import threading

        def work():
            res = fn()
            if done and self.alive:
                GLib.idle_add(lambda: self.alive and done(res) and False)

        threading.Thread(target=work, daemon=True).start()

    def ready(self):
        if not self.get_visible():
            self.backdrop.present()  # 먼저 띄워야 패널 아래에 깔림
            self.present()

    def on_escape(self):
        self.close()

    def _on_key(self, _c, key, _code, _state):
        if key == Gdk.KEY_Escape:
            self.on_escape()
            return True
        return False


def load_css(css):
    provider = Gtk.CssProvider()
    provider.load_from_string(BASE_CSS + css)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)


class PanelApp(Gtk.Application):
    """패널 하나만 띄우는 단독 실행용 (디버깅). 평소엔 panels.py 데몬을 씀."""

    def __init__(self, app_id, window_cls):
        super().__init__(application_id=app_id)
        self.window_cls = window_cls
        self.window = None

    def do_activate(self):
        if self.window:
            self.window.close()
            return
        load_css(self.window_cls.CSS)
        self.window = self.window_cls(self)
        self.window.connect("close-request", lambda *_: self.quit() or False)
        self.window.ready()


def main(app_id, window_cls, css=""):
    if css:
        window_cls.CSS = css
    sys.exit(PanelApp(app_id, window_cls).run(None))

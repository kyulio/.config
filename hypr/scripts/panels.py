#!/usr/bin/python3
"""패널 데몬 — 모든 waybar 패널을 한 프로세스에 상주시켜 버튼 반응을 즉시로.

  panels.py            데몬 실행 (hyprland 시작 시 자동)
  panel.sh <이름>      열기/닫기 토글 (wifi, bluetooth, audio, battery, weather, calendar, power)

명령은 $XDG_RUNTIME_DIR/kyulio-panels.fifo 로 받음.
"""
import ctypes
import gc
import importlib.util
import os
import sys

# GTK 렌더러: GPU(ngl) 는 패널마다 GPU 버퍼를 잡아 메모리가 크게 늘어남 → cairo(CPU) 가 훨씬 가벼움
os.environ.setdefault("GSK_RENDERER", "cairo")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from panel_base import GLib, Gtk, load_css  # noqa: E402

IDLE_RESTART_SEC = 20  # 패널을 닫고 이만큼 안 쓰면 새 프로세스로 교체 → 메모리를 처음 상태로
try:
    _libc = ctypes.CDLL("libc.so.6")
except OSError:
    _libc = None

FIFO = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "kyulio-panels.fifo")
PANELS = {
    "wifi": ("wifi-panel.py", "WifiPanel"),
    "bluetooth": ("bluetooth-panel.py", "BluetoothPanel"),
    "audio": ("audio-panel.py", "AudioPanel"),
    "battery": ("battery-panel.py", "BatteryPanel"),
    "weather": ("weather-panel.py", "WeatherPanel"),
    "calendar": ("calendar-panel.py", "CalendarPanel"),
    "power": ("power-panel.py", "PowerPanel"),
}


def load_classes():
    classes, css = {}, ""
    for name, (fname, cls) in PANELS.items():
        spec = importlib.util.spec_from_file_location(fname[:-3].replace("-", "_"), os.path.join(HERE, fname))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        klass = getattr(mod, cls)
        classes[name] = klass
        css += (klass.CSS or "") + getattr(mod, "CSS", "")
    return classes, css


class PanelDaemon(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.kyulio.Panels")
        self.classes, self.css = {}, ""
        self.current = None  # (이름, 창)
        self.idle_timer = 0

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.hold()  # 창이 없어도 계속 실행
        self.classes, self.css = load_classes()
        load_css(self.css)
        self.open_fifo()

    def do_activate(self):
        pass

    def open_fifo(self):
        try:
            os.unlink(FIFO)
        except FileNotFoundError:
            pass
        os.mkfifo(FIFO, 0o600)
        fd = os.open(FIFO, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
        self._keep_writer = os.open(FIFO, os.O_WRONLY | os.O_NONBLOCK | os.O_CLOEXEC)  # EOF 루프 방지
        GLib.io_add_watch(fd, GLib.PRIORITY_HIGH, GLib.IOCondition.IN, self.on_fifo)

    def on_fifo(self, fd, _cond):
        try:
            data = os.read(fd, 4096).decode(errors="ignore")
        except BlockingIOError:
            return True
        for cmd in data.split():
            self.toggle(cmd.strip())
        return True

    def toggle(self, name):
        if name == "close":
            self.close_current()
            return
        if name not in self.classes:
            return
        if self.current and self.current[0] == name:
            self.close_current()
            return
        self.close_current()
        if self.idle_timer:
            GLib.source_remove(self.idle_timer)
            self.idle_timer = 0
        try:
            win = self.classes[name](self)
        except Exception as e:  # noqa: BLE001  패널 하나가 깨져도 데몬은 유지
            print(f"[panels] {name}: {e}", file=sys.stderr, flush=True)
            return
        self.current = (name, win)
        win.connect("close-request", lambda w: self._closed(w) or False)
        win.ready()

    def _closed(self, win):
        if self.current and self.current[1] is win:
            self.current = None
        GLib.timeout_add(300, self.trim)
        if self.idle_timer:
            GLib.source_remove(self.idle_timer)
        self.idle_timer = GLib.timeout_add_seconds(IDLE_RESTART_SEC, self.restart_if_idle)

    @staticmethod
    def trim():
        gc.collect()
        if _libc:
            _libc.malloc_trim(0)  # 해제된 C 메모리를 OS 에 반환
        return False

    def restart_if_idle(self):
        self.idle_timer = 0
        if self.current is None:
            # 같은 PID 로 새로 시작 (FIFO 는 새 프로세스가 다시 만듦)
            os.environ.pop("KYULIO_PANEL_PRELOADED", None)  # LD_PRELOAD 다시 걸리도록
            os.execv(sys.executable, [sys.executable] + sys.argv)
        return False

    def close_current(self):
        if self.current:
            _, win = self.current
            self.current = None
            win.close()


if __name__ == "__main__":
    sys.exit(PanelDaemon().run(None))

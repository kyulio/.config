#!/usr/bin/python3
"""블루투스 패널: 어댑터 on/off · 검색 / 연결된·페어링된·주변 기기 (BlueZ D-Bus 직접 사용)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panel_base import GLib, Gtk, Panel, label, main, sep  # noqa: E402
from gi.repository import Gio  # noqa: E402

BLUEZ = "org.bluez"
ICON_ON, ICON_OFF, ICON_CONN = "\U000F00AF", "\U000F00B2", "\U000F00B1"
ICON_SCAN = "\U000F0450"
ICON_BATT = "\U000F0079"
DEVICE_ICONS = {
    "audio-headset": "\U000F02CE", "audio-headphones": "\U000F02CB", "audio-card": "\U000F04C3",
    "input-mouse": "\U000F037D", "input-keyboard": "\U000F030C", "input-gaming": "\U000F0EB5",
    "input-tablet": "\U000F04F7", "phone": "\U000F011C", "computer": "\U000F0322",
    "video-display": "\U000F0379", "printer": "\U000F042A", "watch": "\U000F0598",
}
CSS = """
.scanning { color: #ffffff; }
"""


class BluetoothPanel(Panel):
    def __init__(self, app):
        super().__init__(app)
        self.bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        self.adapter = None
        self.adapter_props = {}
        self.devices = {}
        self.updating = False
        self.scanning = False
        self.busy = set()
        card = self.card

        head = Gtk.Box(spacing=10)
        card.append(head)
        self.hero_icon = label(ICON_ON, "hero-icon", xalign=0.5)
        head.append(self.hero_icon)
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        head.append(titles)
        titles.append(label("Bluetooth", "hero-name"))
        self.hero_sub = label("", "hero-sub")
        titles.append(self.hero_sub)
        self.scan_btn = Gtk.Button(label=ICON_SCAN, focusable=False, valign=Gtk.Align.CENTER,
                                   tooltip_text="주변 기기 검색")
        self.scan_btn.add_css_class("icon-btn")
        self.scan_btn.connect("clicked", lambda *_: self.toggle_scan())
        head.append(self.scan_btn)
        self.switch = Gtk.Switch(valign=Gtk.Align.CENTER, focusable=False)
        self.switch.connect("notify::active", self.on_switch)
        head.append(self.switch)

        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        card.append(sep())
        scroller = Gtk.ScrolledWindow(propagate_natural_height=True, max_content_height=460,
                                      hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroller.set_child(self.body)
        card.append(scroller)

        self.status = label("", "status", visible=False)
        card.append(self.status)

        self.refresh()
        subs = [
            self.bus.signal_subscribe(BLUEZ, "org.freedesktop.DBus.Properties", "PropertiesChanged",
                                      None, None, Gio.DBusSignalFlags.NONE, self.on_signal),
            self.bus.signal_subscribe(BLUEZ, "org.freedesktop.DBus.ObjectManager", None,
                                      None, None, Gio.DBusSignalFlags.NONE, self.on_signal),
        ]
        self.on_cleanup(lambda: [self.bus.signal_unsubscribe(s) for s in subs])
        self.on_cleanup(self.on_close)

    def say(self, text):
        self.status.set_label(text)
        self.status.set_visible(bool(text))

    # ── D-Bus ──
    def call(self, path, iface, method, params=None, done=None, timeout=30000):
        def cb(bus, res):
            try:
                bus.call_finish(res)
                err = None
            except GLib.Error as e:
                err = e.message.split(":")[-1].strip()
            if done:
                done(err)
        self.bus.call(BLUEZ, path, iface, method, params, None, Gio.DBusCallFlags.NONE,
                      timeout, None, cb)

    def set_prop(self, path, iface, name, variant, done=None):
        self.call(path, "org.freedesktop.DBus.Properties", "Set",
                  GLib.Variant("(ssv)", (iface, name, variant)), done)

    def refresh(self):
        def cb(bus, res):
            try:
                objs = bus.call_finish(res).unpack()[0]
            except GLib.Error as e:
                self.say(e.message)
                return
            self.adapter, self.adapter_props, self.devices = None, {}, {}
            for path, ifaces in objs.items():
                if "org.bluez.Adapter1" in ifaces and self.adapter is None:
                    self.adapter, self.adapter_props = path, ifaces["org.bluez.Adapter1"]
                if "org.bluez.Device1" in ifaces:
                    dev = dict(ifaces["org.bluez.Device1"])
                    dev["battery"] = ifaces.get("org.bluez.Battery1", {}).get("Percentage")
                    self.devices[path] = dev
            self.render()
        self.bus.call(BLUEZ, "/", "org.freedesktop.DBus.ObjectManager", "GetManagedObjects",
                      None, None, Gio.DBusCallFlags.NONE, 5000, None, cb)

    def on_signal(self, *_):
        # 신호가 몰려와도 한 번만 다시 그림
        if not getattr(self, "_pending", False):
            self._pending = True
            GLib.timeout_add(250, self._flush)

    def _flush(self):
        self._pending = False
        if self.alive:
            self.refresh()
        return False

    # ── 그리기 ──
    def render(self):
        powered = bool(self.adapter_props.get("Powered"))
        self.updating = True
        self.switch.set_active(powered)
        self.updating = False
        self.scan_btn.set_sensitive(powered)
        (self.scan_btn.add_css_class if self.scanning else self.scan_btn.remove_css_class)("scanning")

        devs = list(self.devices.items())
        connected = [d for d in devs if d[1].get("Connected")]
        paired = [d for d in devs if d[1].get("Paired") and not d[1].get("Connected")]
        nearby = [d for d in devs if not d[1].get("Paired") and not d[1].get("Connected")
                  and d[1].get("Name")]

        if not self.adapter:
            self.hero_icon.set_label(ICON_OFF)
            self.hero_sub.set_label("NO ADAPTER")
        elif not powered:
            self.hero_icon.set_label(ICON_OFF)
            self.hero_sub.set_label("OFF")
        else:
            self.hero_icon.set_label(ICON_CONN if connected else ICON_ON)
            name = self.adapter_props.get("Alias") or self.adapter_props.get("Name") or ""
            state = "SCANNING…" if self.scanning else f"{len(connected)} CONNECTED"
            self.hero_sub.set_label(f"{name.upper()} · {state}")

        while (c := self.body.get_first_child()) is not None:
            self.body.remove(c)
        if not powered:
            self.body.append(label("블루투스가 꺼져 있어요", "row-dim", margin_top=6, margin_bottom=6))
            return
        for title, items in (("CONNECTED", connected), ("PAIRED DEVICES", paired),
                             ("NEARBY DEVICES", nearby)):
            if items:
                self.body.append(label(title, "section"))
                for path, dev in sorted(items, key=lambda d: d[1].get("Alias", "").lower()):
                    self.body.append(self.row(path, dev))
        if not (connected or paired or nearby):
            self.body.append(label("기기가 없어요. 검색 버튼을 눌러보세요", "row-dim", margin_top=6))
        if self.scanning and not nearby:
            self.body.append(label("NEARBY DEVICES · 검색 중…", "section"))

    def row(self, path, dev):
        btn = Gtk.Button(focusable=False)
        btn.add_css_class("row-btn")
        if dev.get("Connected"):
            btn.add_css_class("current")
        box = Gtk.Box(spacing=8)
        box.append(label(DEVICE_ICONS.get(dev.get("Icon", ""), ICON_ON), "row-icon", xalign=0.5))
        names = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        names.append(label(dev.get("Alias") or dev.get("Name") or dev.get("Address"), "row-name", ellipsize=3))
        if path in self.busy:
            sub = "연결 중…"
        elif dev.get("Connected"):
            sub = "Connected"
        elif dev.get("Paired"):
            sub = "클릭해서 연결"
        else:
            sub = "클릭해서 페어링"
        names.append(label(sub, "row-sub"))
        box.append(names)
        if dev.get("battery") is not None:
            box.append(label(f"{ICON_BATT} {dev['battery']}%", "row-dim"))
        btn.set_child(box)
        btn.connect("clicked", lambda *_: self.on_device(path, dev))
        if dev.get("Paired"):
            forget = Gtk.GestureClick(button=3)
            forget.connect("pressed", lambda *_: self.forget(path, dev))
            btn.add_controller(forget)
            btn.set_tooltip_text("우클릭: 기기 삭제")
        return btn

    # ── 동작 ──
    def done(self, path, msg_ok=""):
        def cb(err):
            self.busy.discard(path)
            self.say(err or msg_ok)
            self.refresh()
        return cb

    def on_device(self, path, dev):
        name = dev.get("Alias") or dev.get("Address")
        self.busy.add(path)
        self.render()
        if dev.get("Connected"):
            self.say(f"{name} 연결 해제 중…")
            self.call(path, "org.bluez.Device1", "Disconnect", done=self.done(path))
        elif dev.get("Paired"):
            self.say(f"{name} 연결 중…")
            self.call(path, "org.bluez.Device1", "Connect", done=self.done(path))
        else:
            self.say(f"{name} 페어링 중…")

            def paired(err):
                if err:
                    self.done(path)(err)
                    return
                self.set_prop(path, "org.bluez.Device1", "Trusted", GLib.Variant("b", True))
                self.call(path, "org.bluez.Device1", "Connect", done=self.done(path))
            self.call(path, "org.bluez.Device1", "Pair", done=paired, timeout=90000)

    def forget(self, path, dev):
        if self.adapter:
            self.say(f"{dev.get('Alias')} 삭제 중…")
            self.call(self.adapter, "org.bluez.Adapter1", "RemoveDevice",
                      GLib.Variant("(o)", (path,)), done=self.done(path))

    def on_switch(self, sw, _p):
        if not self.updating and self.adapter:
            self.set_prop(self.adapter, "org.bluez.Adapter1", "Powered",
                          GLib.Variant("b", sw.get_active()), done=lambda e: (self.say(e or ""), self.refresh()))

    def toggle_scan(self):
        if not self.adapter:
            return
        self.scanning = not self.scanning
        method = "StartDiscovery" if self.scanning else "StopDiscovery"
        self.call(self.adapter, "org.bluez.Adapter1", method, done=lambda e: (self.say(e or ""), self.render()))
        if self.scanning:
            GLib.timeout_add_seconds(20, self._stop_scan)
        self.render()

    def _stop_scan(self):
        if self.alive and self.scanning:
            self.toggle_scan()
        return False

    def on_close(self, *_):
        if self.scanning and self.adapter:
            try:
                self.bus.call_sync(BLUEZ, self.adapter, "org.bluez.Adapter1", "StopDiscovery",
                                   None, None, Gio.DBusCallFlags.NONE, 1000, None)
            except GLib.Error:
                pass
        return False


if __name__ == "__main__":
    main("org.kyulio.BluetoothPanel", BluetoothPanel, CSS)

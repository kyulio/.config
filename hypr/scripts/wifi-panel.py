#!/usr/bin/python3
"""Wi-Fi 패널: 현재 네트워크 / 상태(핑·속도·누적·IP) / DNS / 저장된·주변 네트워크."""
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panel_base import GLib, Gtk, Panel, label, main, run, sep, stat_grid  # noqa: E402

ICON_WIFI = ["\U000F092F", "\U000F091F", "\U000F0922", "\U000F0925", "\U000F0928"]
ICON_OFF = "\U000F092E"
ICON_LOCK = "\U000F033E"
ICON_REFRESH = "\U000F0450"

DNS_PRESETS = {"DHCP": None, "Cloudflare": "1.1.1.1 1.0.0.1", "Google": "8.8.8.8 8.8.4.4"}


def nm_fields(line):
    return [p.replace("\\:", ":").replace("\\\\", "\\") for p in re.split(r"(?<!\\):", line)]


def signal_icon(sig):
    return ICON_WIFI[min(4, max(0, int(sig) // 20))]


def human_bytes(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.2f} {unit}"
        n /= 1024


def human_rate(n):
    if n < 1024:
        return f"{n:.0f} B/s"
    if n < 1024 ** 2:
        return f"{n / 1024:.1f} KB/s"
    return f"{n / 1024 ** 2:.1f} MB/s"


def band_of(mhz):
    return "6GHz" if mhz >= 5925 else "5GHz" if mhz >= 4900 else "2.4GHz"


class WifiPanel(Panel):
    def __init__(self, app):
        super().__init__(app)
        self.dev = self.find_device()
        self.prev_bytes = None
        self.updating = False
        self.expanded = None
        self.known = {}
        self.current_con = None
        card = self.card

        # 헤더
        head = Gtk.Box(spacing=10)
        card.append(head)
        self.hero_icon = label(ICON_OFF, "hero-icon", xalign=0.5)
        head.append(self.hero_icon)
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        head.append(titles)
        self.hero_name = label("Wi-Fi", "hero-name", ellipsize=3)
        self.hero_sub = label("", "hero-sub")
        titles.append(self.hero_name)
        titles.append(self.hero_sub)
        rescan = Gtk.Button(label=ICON_REFRESH, focusable=False, valign=Gtk.Align.CENTER,
                            tooltip_text="다시 검색")
        rescan.add_css_class("icon-btn")
        rescan.connect("clicked", lambda *_: self.rescan())
        head.append(rescan)
        self.switch = Gtk.Switch(valign=Gtk.Align.CENTER, focusable=False)
        self.switch.connect("notify::active", self.on_switch)
        head.append(self.switch)

        # 상태
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.append(self.body)
        self.body.append(sep())
        grid, self.stats = stat_grid([
            ("ping", "Ping"), ("loss", "Packet Loss"),
            ("rx", "Receiving"), ("tx", "Sending"),
            ("rxt", "Downloaded"), ("txt", "Uploaded"),
            ("ip", "IP Address"), ("gw", "Gateway")])
        self.body.append(grid)
        self.body.append(sep())
        band_row = Gtk.Box()
        self.band = label("", "section", hexpand=True)
        band_row.append(self.band)
        band_row.append(label("AUTO CONNECT", "section"))
        self.auto = Gtk.Switch(valign=Gtk.Align.CENTER, focusable=False, margin_start=8)
        self.auto.connect("notify::active", self.on_auto)
        band_row.append(self.auto)
        self.body.append(band_row)

        # DNS
        self.body.append(label("DNS PROVIDER", "section"))
        segs = Gtk.Box(spacing=6, homogeneous=True)
        self.body.append(segs)
        self.seg_buttons = {}
        for name in list(DNS_PRESETS) + ["Custom"]:
            b = Gtk.Button(label=name, focusable=False)
            b.add_css_class("seg")
            b.connect("clicked", self.on_dns, name)
            segs.append(b)
            self.seg_buttons[name] = b
        self.custom_dns = Gtk.Entry(placeholder_text="예: 9.9.9.9 149.112.112.112", visible=False)
        self.custom_dns.connect("activate", lambda e: self.apply_dns(e.get_text().strip()))
        self.body.append(self.custom_dns)

        # 목록
        scroller = Gtk.ScrolledWindow(propagate_natural_height=True, max_content_height=330,
                                      hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.lists = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        scroller.set_child(self.lists)
        self.body.append(scroller)

        self.status = label("", "status", visible=False)
        card.append(self.status)

        self.refresh_all()
        self.tick_rates()
        self.every(1000, self.tick_rates)
        self.every(4000, self.refresh_all)
        threading.Thread(target=self.ping_loop, daemon=True).start()

    def say(self, text):
        self.status.set_label(text)
        self.status.set_visible(bool(text))

    # ── 데이터 ──
    @staticmethod
    def find_device():
        _, out, _ = run("nmcli", "-t", "-f", "DEVICE,TYPE", "device")
        for line in out.splitlines():
            f = nm_fields(line)
            if len(f) >= 2 and f[1] == "wifi":
                return f[0]
        return "wlan0"

    def collect(self):
        d = {}
        _, radio, _ = run("nmcli", "radio", "wifi")
        d["enabled"] = radio == "enabled"
        nets = {}
        if d["enabled"]:
            _, out, _ = run("nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY,FREQ",
                            "device", "wifi", "list", "--rescan", "no")
            for line in out.splitlines():
                f = nm_fields(line)
                if len(f) < 5 or not f[1]:
                    continue
                inuse, ssid, sig = f[0] == "*", f[1], int(f[2] or 0)
                mhz = int(re.sub(r"\D", "", f[4]) or 0)
                old = nets.get(ssid)
                if old is None or inuse or (not old["inuse"] and sig > old["signal"]):
                    nets[ssid] = {"ssid": ssid, "signal": sig, "secure": f[3] not in ("", "--"),
                                  "inuse": inuse or bool(old and old["inuse"]), "mhz": mhz}
        d["nets"] = nets

        _, out, _ = run("nmcli", "-t", "-f", "NAME,TYPE", "connection", "show")
        names = [f[0] for f in map(nm_fields, out.splitlines()) if len(f) >= 2 and f[1] == "802-11-wireless"]
        with ThreadPoolExecutor(max_workers=16) as ex:
            ssids = list(ex.map(lambda n: run("nmcli", "-g", "802-11-wireless.ssid", "connection", "show", n)[1], names))
        d["known"] = {(ssid or name): name for name, ssid in zip(names, ssids)}

        _, out, _ = run("nmcli", "-t", "-f", "GENERAL.CONNECTION,IP4.ADDRESS,IP4.GATEWAY",
                        "device", "show", self.dev)
        info = {}
        for line in out.splitlines():
            k, _, v = line.partition(":")
            info.setdefault(k.split("[")[0], v)
        con = info.get("GENERAL.CONNECTION") or ""
        d["con"] = con if con and con != "--" else None
        d["ip"] = (info.get("IP4.ADDRESS") or "—").split("/")[0] or "—"
        d["gw"] = info.get("IP4.GATEWAY") or "—"

        d["dns_mode"], d["dns"], d["auto"] = None, "", True
        if d["con"]:
            _, dns, _ = run("nmcli", "-g", "ipv4.dns", "connection", "show", d["con"])
            _, auto, _ = run("nmcli", "-g", "connection.autoconnect", "connection", "show", d["con"])
            dns = dns.replace(",", " ").strip()
            d["dns"], d["auto"] = dns, auto == "yes"
            d["dns_mode"] = "DHCP" if not dns else next(
                (k for k, v in DNS_PRESETS.items() if v == dns), "Custom")
        return d

    def refresh_all(self):
        self.bg(self.collect, self.render)

    def render(self, d):
        self.known, self.current_con = d["known"], d["con"]
        self.updating = True
        self.switch.set_active(d["enabled"])
        self.auto.set_active(d["auto"])
        self.updating = False
        self.body.set_visible(d["enabled"])

        cur = next((n for n in d["nets"].values() if n["inuse"]), None)
        if not d["enabled"]:
            self.hero_icon.set_label(ICON_OFF)
            self.hero_name.set_label("Wi-Fi")
            self.hero_sub.set_label("OFF")
        elif cur:
            self.hero_icon.set_label(signal_icon(cur["signal"]))
            self.hero_name.set_label(cur["ssid"])
            self.hero_sub.set_label(f"CONNECTED · SIGNAL {cur['signal']}%")
            self.band.set_label(f"WI-FI BAND: {band_of(cur['mhz'])}")
        else:
            self.hero_icon.set_label(ICON_WIFI[0])
            self.hero_name.set_label("Not connected")
            self.hero_sub.set_label("SELECT A NETWORK")
            self.band.set_label("WI-FI BAND: —")
        self.stats["ip"].set_label(d["ip"])
        self.stats["gw"].set_label(d["gw"])

        for name, b in self.seg_buttons.items():
            (b.add_css_class if name == d["dns_mode"] else b.remove_css_class)("on")
        if d["dns_mode"] == "Custom" and not self.custom_dns.has_focus():
            self.custom_dns.set_text(d["dns"])
            self.custom_dns.set_visible(True)

        if self.expanded is None:
            self.render_lists(d["nets"])
        self.ready()

    def render_lists(self, nets):
        while (c := self.lists.get_first_child()) is not None:
            self.lists.remove(c)
        ordered = sorted(nets.values(), key=lambda n: (not n["inuse"], -n["signal"]))
        known = [n for n in ordered if n["ssid"] in self.known]
        other = [n for n in ordered if n["ssid"] not in self.known]
        if known:
            self.lists.append(label("KNOWN NETWORKS", "section"))
            for n in known:
                self.lists.append(self.net_row(n, True))
        if other:
            self.lists.append(label("OTHER NETWORKS", "section"))
            for n in other:
                self.lists.append(self.net_row(n, False))
        if not nets:
            self.lists.append(label("NO NETWORKS FOUND", "section"))

    def net_row(self, n, known):
        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        btn = Gtk.Button(focusable=False)
        btn.add_css_class("row-btn")
        if n["inuse"]:
            btn.add_css_class("current")
        row = Gtk.Box(spacing=8)
        row.append(label(signal_icon(n["signal"]), "row-icon", xalign=0.5))
        names = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        names.append(label(n["ssid"], "row-name", ellipsize=3))
        if n["inuse"]:
            names.append(label("Connected", "row-sub"))
        row.append(names)
        if n["secure"]:
            row.append(label(ICON_LOCK, "row-dim"))
        btn.set_child(row)
        btn.connect("clicked", lambda *_: self.on_net(n, known, wrap))
        if known and not n["inuse"]:
            forget = Gtk.GestureClick(button=3)
            forget.connect("pressed", lambda *_: self.forget(n["ssid"]))
            btn.add_controller(forget)
            btn.set_tooltip_text("우클릭: 저장된 네트워크 삭제")
        wrap.append(btn)
        return wrap

    # ── 동작 ──
    def on_net(self, n, known, wrap):
        if n["inuse"]:
            self.say(f"{n['ssid']} 연결 해제 중…")
            self.bg(lambda: run("nmcli", "device", "disconnect", self.dev), self.after)
        elif known:
            self.say(f"{n['ssid']} 연결 중…")
            con = self.known[n["ssid"]]
            self.bg(lambda: run("nmcli", "connection", "up", "id", con, timeout=40), self.after)
        elif n["secure"]:
            if self.expanded == n["ssid"]:
                return
            self.expanded = n["ssid"]
            self.hold_open = True
            entry = Gtk.Entry(visibility=False, placeholder_text=f"{n['ssid']} 비밀번호")
            entry.connect("activate", lambda e: self.connect_new(n["ssid"], e.get_text()))
            wrap.append(entry)
            entry.grab_focus()
        else:
            self.connect_new(n["ssid"], None)

    def connect_new(self, ssid, password):
        self.say(f"{ssid} 연결 중…")
        args = ["nmcli", "device", "wifi", "connect", ssid] + (["password", password] if password else [])
        self.expanded, self.hold_open = None, False
        self.bg(lambda: run(*args, timeout=40), self.after)

    def forget(self, ssid):
        con = self.known.get(ssid)
        if con:
            self.say(f"{ssid} 삭제 중…")
            self.bg(lambda: run("nmcli", "connection", "delete", "id", con), self.after)

    def after(self, res):
        code, _, err = res
        self.say("" if code == 0 else (err.splitlines() or ["실패"])[-1][:80])
        self.refresh_all()

    def rescan(self):
        self.say("검색 중…")
        self.bg(lambda: run("nmcli", "device", "wifi", "rescan"), lambda _r: (self.say(""), self.refresh_all()))

    def on_switch(self, sw, _p):
        if not self.updating:
            state = "on" if sw.get_active() else "off"
            self.bg(lambda: run("nmcli", "radio", "wifi", state), self.after)

    def on_auto(self, sw, _p):
        if self.updating or not self.current_con:
            return
        con, val = self.current_con, "yes" if sw.get_active() else "no"
        self.bg(lambda: run("nmcli", "connection", "modify", con, "connection.autoconnect", val), self.after)

    def on_dns(self, _b, name):
        if name == "Custom":
            self.custom_dns.set_visible(True)
            self.custom_dns.grab_focus()
            return
        self.custom_dns.set_visible(False)
        self.apply_dns(DNS_PRESETS[name])

    def apply_dns(self, servers):
        if not self.current_con:
            self.say("연결된 네트워크가 없어요")
            return
        con, dev = self.current_con, self.dev

        def work():
            if servers:
                r = run("nmcli", "connection", "modify", con, "ipv4.dns",
                        servers.replace(" ", ","), "ipv4.ignore-auto-dns", "yes")
            else:
                r = run("nmcli", "connection", "modify", con, "ipv4.dns", "", "ipv4.ignore-auto-dns", "no")
            return r if r[0] != 0 else run("nmcli", "device", "reapply", dev)

        self.say("DNS 적용 중…")
        self.bg(work, self.after)

    # ── 주기 갱신 ──
    def tick_rates(self):
        try:
            base = f"/sys/class/net/{self.dev}/statistics/"
            rx, tx = int(open(base + "rx_bytes").read()), int(open(base + "tx_bytes").read())
        except OSError:
            return True
        now = time.monotonic()
        if self.prev_bytes:
            prx, ptx, pt = self.prev_bytes
            dt = max(now - pt, 0.001)
            self.stats["rx"].set_label(human_rate((rx - prx) / dt))
            self.stats["tx"].set_label(human_rate((tx - ptx) / dt))
        self.stats["rxt"].set_label(human_bytes(rx))
        self.stats["txt"].set_label(human_bytes(tx))
        self.prev_bytes = (rx, tx, now)
        return True

    def ping_loop(self):
        while self.alive:
            _, out, _ = run("ping", "-c", "3", "-i", "0.3", "-W", "1", "1.1.1.1", timeout=8)
            loss = re.search(r"([\d.]+)% packet loss", out)
            avg = re.search(r"= [\d.]+/([\d.]+)/", out)
            GLib.idle_add(self.stats["ping"].set_label, f"{float(avg.group(1)):.0f} ms" if avg else "—")
            GLib.idle_add(self.stats["loss"].set_label, f"{float(loss.group(1)):.0f}%" if loss else "—")
            time.sleep(4)

    def on_escape(self):
        if self.expanded is not None:
            self.expanded, self.hold_open = None, False
            self.refresh_all()
        else:
            self.close()


if __name__ == "__main__":
    main("org.kyulio.WifiPanel", WifiPanel)

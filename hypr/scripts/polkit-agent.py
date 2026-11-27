#!/usr/bin/python3
"""polkit 인증 에이전트 — 비밀번호 창을 패널과 같은 디자인으로 (hyprpolkitagent 대체).

polkit 의 D-Bus 에이전트 인터페이스(org.freedesktop.PolicyKit1.AuthenticationAgent)를
직접 구현하고, 실제 비밀번호 확인은 PolkitAgent.Session(공식 helper)에 맡김.
평소엔 GTK 를 불러오지 않아 가볍고(~25MB), 창을 닫고 잠시 뒤 새 프로세스로 교체해 메모리 회수.
"""
import os
import sys

# gtk4-layer-shell 은 libwayland 보다 먼저 로드돼야 함 (GTK 는 필요할 때만 import)
_LIB = "/usr/lib/libgtk4-layer-shell.so"
if os.environ.get("KYULIO_PANEL_PRELOADED") != "1":
    env = dict(os.environ, KYULIO_PANEL_PRELOADED="1",
               LD_PRELOAD=(_LIB + " " + os.environ.get("LD_PRELOAD", "")).strip(),
               GSK_RENDERER=os.environ.get("GSK_RENDERER", "cairo"))
    os.execve(sys.executable, [sys.executable] + sys.argv, env)
os.environ.pop("LD_PRELOAD", None)

import gi  # noqa: E402

gi.require_version("Polkit", "1.0")
gi.require_version("PolkitAgent", "1.0")
from gi.repository import Gio, GLib, Polkit, PolkitAgent  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OBJECT_PATH = "/org/kyulio/PolkitAgent"
IDLE_RESTART_SEC = 30
POLKIT = "org.freedesktop.PolicyKit1"

IFACE_XML = """
<node>
  <interface name="org.freedesktop.PolicyKit1.AuthenticationAgent">
    <method name="BeginAuthentication">
      <arg type="s" name="action_id" direction="in"/>
      <arg type="s" name="message" direction="in"/>
      <arg type="s" name="icon_name" direction="in"/>
      <arg type="a{ss}" name="details" direction="in"/>
      <arg type="s" name="cookie" direction="in"/>
      <arg type="a(sa{sv})" name="identities" direction="in"/>
    </method>
    <method name="CancelAuthentication">
      <arg type="s" name="cookie" direction="in"/>
    </method>
  </interface>
</node>
"""

ICON_LOCK = "\U000F033E"


def log(*a):
    print("[polkit-agent]", *a, file=sys.stderr, flush=True)


def build_dialog_class():
    """GTK 는 첫 요청 때만 불러옴."""
    sys.path.insert(0, HERE)
    from panel_base import Gtk, Panel, label, load_css, sep

    css = """
    .auth-msg { color: #dddddd; }
    .auth-cmd {
      color: #aaaaaa; font-size: 11px;
      background: rgba(255, 255, 255, 0.05); border-radius: 7px; padding: 6px 10px;
    }
    .auth-err { color: #ffffff; font-weight: 700; }
    """
    load_css(css)

    class AuthDialog(Panel):
        ANCHOR = "middle"
        LAYER = "overlay"
        DIM = True

        def __init__(self, req):
            super().__init__(None)
            self.req = req
            card = self.card
            card.set_spacing(10)

            head = Gtk.Box(spacing=10)
            card.append(head)
            head.append(label(ICON_LOCK, "hero-icon", xalign=0.5))
            titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
            head.append(titles)
            titles.append(label("Authentication", "hero-name"))
            titles.append(label(req.action_id.upper(), "hero-sub", ellipsize=3))

            card.append(sep())
            card.append(label(req.message, "auth-msg", wrap=True, max_width_chars=44))
            cmd = req.details.get("command_line") or req.details.get("program")
            if cmd:
                card.append(label(cmd, "auth-cmd", wrap=True, selectable=False, max_width_chars=50))

            self.prompt = label(f"PASSWORD FOR {req.user_name.upper()}", "section")
            card.append(self.prompt)
            self.entry = Gtk.PasswordEntry(show_peek_icon=True, sensitive=False)
            self.entry.connect("activate", lambda *_: self.submit())
            card.append(self.entry)
            self.error = label("", "auth-err", visible=False, wrap=True)
            card.append(self.error)

            btns = Gtk.Box(spacing=6, homogeneous=True, margin_top=2)
            card.append(btns)
            cancel = Gtk.Button(label="Cancel", focusable=False)
            cancel.add_css_class("seg")
            cancel.connect("clicked", lambda *_: self.close())
            btns.append(cancel)
            self.ok = Gtk.Button(label="Authenticate", focusable=False, sensitive=False)
            self.ok.add_css_class("seg")
            self.ok.add_css_class("primary")
            self.ok.connect("clicked", lambda *_: self.submit())
            btns.append(self.ok)
            self.on_cleanup(lambda: req.dialog_closed())

        def ask(self, prompt, echo):
            p = prompt.strip().rstrip(":").strip()
            if p and p.lower() not in ("password", "비밀번호", "암호"):
                self.prompt.set_label(p.upper())
            self.entry.set_text("")
            self.entry.set_sensitive(True)
            self.ok.set_sensitive(True)
            self.entry.grab_focus()

        def show_error(self, text):
            self.error.set_label(text)
            self.error.set_visible(bool(text))

        def submit(self):
            if not self.entry.get_sensitive():
                return
            self.entry.set_sensitive(False)
            self.ok.set_sensitive(False)
            self.show_error("")
            self.req.respond(self.entry.get_text())

    return AuthDialog


class Request:
    """BeginAuthentication 한 건."""

    def __init__(self, agent, invocation, action_id, message, details, cookie, identities):
        self.agent, self.invocation = agent, invocation
        self.action_id, self.message, self.details, self.cookie = action_id, message, details, cookie
        self.session = None
        self.dialog = None
        self.done = False
        self.identity = self.pick_identity(identities)
        self.user_name = self.identity.get_name() if isinstance(self.identity, Polkit.UnixUser) else "user"

    @staticmethod
    def pick_identity(identities):
        uid = os.getuid()
        users = []
        for kind, props in identities:
            if kind == "unix-user":
                users.append(Polkit.UnixUser.new(int(props["uid"])))
        for u in users:  # 내 계정 우선, 없으면 root 등 첫 번째
            if u.get_uid() == uid:
                return u
        return users[0] if users else Polkit.UnixUser.new(0)

    def start(self):
        if self.agent.Dialog is None:
            self.agent.Dialog = build_dialog_class()
        self.dialog = self.agent.Dialog(self)
        self.dialog.ready()
        self.new_session()

    def new_session(self):
        s = PolkitAgent.Session.new(self.identity, self.cookie)
        s.connect("request", lambda _s, prompt, echo: self.dialog and self.dialog.ask(prompt, echo))
        s.connect("show-error", lambda _s, t: self.dialog and self.dialog.show_error(t))
        s.connect("show-info", lambda _s, t: self.dialog and self.dialog.show_error(t))
        s.connect("completed", self.on_completed)
        self.session = s
        s.initiate()

    def respond(self, password):
        if self.session:
            self.session.response(password)

    def on_completed(self, _s, gained):
        if self.done:
            return
        if gained:
            self.finish(True)
        else:  # 비밀번호 틀림 → 다시 시도
            if self.dialog:
                self.dialog.show_error("비밀번호가 맞지 않아요")
            self.new_session()

    def finish(self, ok):
        if self.done:
            return
        self.done = True
        if self.session:
            try:
                self.session.cancel()
            except Exception:  # noqa: BLE001
                pass
            self.session = None
        if ok:
            self.invocation.return_value(None)
        else:
            self.invocation.return_dbus_error(f"{POLKIT}.Error.Cancelled", "Authentication dialog was dismissed")
        d, self.dialog = self.dialog, None
        if d:
            d.close()
        self.agent.request_finished(self)

    def dialog_closed(self):
        self.dialog = None
        if not self.done:
            self.finish(False)


class Agent:
    def __init__(self):
        self.Dialog = None
        self.requests = {}
        self.idle_timer = 0
        self.bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        node = Gio.DBusNodeInfo.new_for_xml(IFACE_XML)
        self.bus.register_object(OBJECT_PATH, node.interfaces[0], self.on_method, None, None)
        self.register()

    def register(self):
        session_id = Polkit.UnixSession.new_for_process_sync(os.getpid(), None).get_session_id()
        subject = ("unix-session", {"session-id": GLib.Variant("s", session_id)})
        locale = os.environ.get("LANG", "en_US.UTF-8")
        self.bus.call_sync(POLKIT, "/org/freedesktop/PolicyKit1/Authority", f"{POLKIT}.Authority",
                           "RegisterAuthenticationAgent",
                           GLib.Variant("((sa{sv})ss)", (subject, locale, OBJECT_PATH)),
                           None, Gio.DBusCallFlags.NONE, -1, None)
        log(f"registered for session {session_id}")

    def polkit_owner(self):
        try:
            r = self.bus.call_sync("org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus",
                                   "GetNameOwner", GLib.Variant("(s)", (POLKIT,)),
                                   None, Gio.DBusCallFlags.NONE, 1000, None)
            return r.unpack()[0]
        except GLib.Error:
            return None

    def on_method(self, _conn, sender, _path, _iface, method, params, invocation):
        if sender != self.polkit_owner():  # polkitd 외의 호출은 거부
            invocation.return_dbus_error(f"{POLKIT}.Error.NotAuthorized", "only polkitd may call this")
            return
        if method == "BeginAuthentication":
            action_id, message, _icon, details, cookie, identities = params.unpack()
            if self.idle_timer:
                GLib.source_remove(self.idle_timer)
                self.idle_timer = 0
            req = Request(self, invocation, action_id, message, details, cookie, identities)
            self.requests[cookie] = req
            try:
                req.start()
            except Exception as e:  # noqa: BLE001
                log("failed to show dialog:", e)
                req.finish(False)
        elif method == "CancelAuthentication":
            (cookie,) = params.unpack()
            req = self.requests.get(cookie)
            if req:
                req.finish(False)
            invocation.return_value(None)

    def request_finished(self, req):
        self.requests.pop(req.cookie, None)
        if not self.requests:
            if self.idle_timer:
                GLib.source_remove(self.idle_timer)
            self.idle_timer = GLib.timeout_add_seconds(IDLE_RESTART_SEC, self.restart_if_idle)

    def restart_if_idle(self):
        self.idle_timer = 0
        if not self.requests:  # GTK 를 내려놓고 가벼운 상태로 재시작
            os.environ.pop("KYULIO_PANEL_PRELOADED", None)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        return False


if __name__ == "__main__":
    try:
        Agent()
    except GLib.Error as e:
        log("could not register (another agent running?):", e.message)
        sys.exit(1)
    GLib.MainLoop().run()

#!/usr/bin/python3
import subprocess
import sys
import threading

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

AGENT_PATH = "/org/kyulio/bluetooth_agent"
AGENT_XML = """
<node>
  <interface name="org.bluez.Agent1">
    <method name="Release"/>
    <method name="RequestPinCode">
      <arg type="o" direction="in"/>
      <arg type="s" direction="out"/>
    </method>
    <method name="DisplayPinCode">
      <arg type="o" direction="in"/>
      <arg type="s" direction="in"/>
    </method>
    <method name="RequestPasskey">
      <arg type="o" direction="in"/>
      <arg type="u" direction="out"/>
    </method>
    <method name="DisplayPasskey">
      <arg type="o" direction="in"/>
      <arg type="u" direction="in"/>
      <arg type="q" direction="in"/>
    </method>
    <method name="RequestConfirmation">
      <arg type="o" direction="in"/>
      <arg type="u" direction="in"/>
    </method>
    <method name="RequestAuthorization">
      <arg type="o" direction="in"/>
    </method>
    <method name="AuthorizeService">
      <arg type="o" direction="in"/>
      <arg type="s" direction="in"/>
    </method>
    <method name="Cancel"/>
  </interface>
</node>
"""

current_prompt = None
registration = None


def rofi(prompt, message, rows=None):
    global current_prompt
    subprocess.run(["pkill", "-x", "rofi"], check=False)
    args = ["rofi", "-dmenu", "-no-show-icons", "-p", prompt,
            "-mesg", GLib.markup_escape_text(message),
            "-theme-str", 'window { width: 420px; } entry { placeholder: ""; }']
    if rows is None:
        args += ["-l", "0"]
    current_prompt = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    output, _ = current_prompt.communicate("\n".join(rows or []))
    code = current_prompt.returncode
    current_prompt = None
    return output.strip() if code == 0 else None


def confirm(message):
    return rofi("Bluetooth", message, ["Yes", "No"]) == "Yes"


def notify(message):
    subprocess.run(["notify-send", "-i", "bluetooth", "-t", "30000",
                    "-h", "string:x-canonical-private-synchronous:bluetooth-agent",
                    "Bluetooth Pairing", message], check=False)


def device_name(conn, path):
    try:
        result = conn.call_sync("org.bluez", path, "org.freedesktop.DBus.Properties", "Get",
                                GLib.Variant("(ss)", ("org.bluez.Device1", "Alias")),
                                GLib.VariantType("(v)"), Gio.DBusCallFlags.NONE, 3000, None)
        return result.unpack()[0]
    except GLib.Error:
        return path.rsplit("/", 1)[-1]


def reject(invocation):
    invocation.return_dbus_error("org.bluez.Error.Rejected", "Rejected by user")


def handle_pin(conn, device, invocation):
    pin = rofi("PIN", f"Enter the PIN for {device_name(conn, device)}")
    if pin and pin.isalnum() and len(pin) <= 16:
        invocation.return_value(GLib.Variant("(s)", (pin,)))
    else:
        reject(invocation)


def handle_passkey(conn, device, invocation):
    key = rofi("Passkey", f"Enter the passkey for {device_name(conn, device)}")
    if key and key.isdigit() and int(key) <= 999999:
        invocation.return_value(GLib.Variant("(u)", (int(key),)))
    else:
        reject(invocation)


def handle_yes_no(message, invocation):
    if confirm(message):
        invocation.return_value(None)
    else:
        reject(invocation)


def on_method_call(conn, _sender, _path, _iface, method, params, invocation):
    args = params.unpack()

    if method == "RequestPinCode":
        target, call = handle_pin, (conn, args[0], invocation)
    elif method == "RequestPasskey":
        target, call = handle_passkey, (conn, args[0], invocation)
    elif method == "RequestConfirmation":
        message = f"Does {device_name(conn, args[0])} show passkey {args[1]:06d}?"
        target, call = handle_yes_no, (message, invocation)
    elif method == "RequestAuthorization":
        target, call = handle_yes_no, (f"Pair with {device_name(conn, args[0])}?", invocation)
    elif method == "AuthorizeService":
        target, call = handle_yes_no, (f"Allow {device_name(conn, args[0])} to connect?", invocation)
    elif method == "DisplayPinCode":
        notify(f"Type {args[1]} on {device_name(conn, args[0])}, then press Enter")
        invocation.return_value(None)
        return
    elif method == "DisplayPasskey":
        notify(f"Type {args[1]:06d} on {device_name(conn, args[0])}, then press Enter")
        invocation.return_value(None)
        return
    else:
        if method == "Cancel" and current_prompt:
            current_prompt.terminate()
        invocation.return_value(None)
        return

    threading.Thread(target=target, args=call, daemon=True).start()


def on_bluez_appeared(conn, _name, _owner):
    global registration
    if registration is None:
        node = Gio.DBusNodeInfo.new_for_xml(AGENT_XML)
        registration = conn.register_object(AGENT_PATH, node.interfaces[0], on_method_call)
    for method, params in (("RegisterAgent", GLib.Variant("(os)", (AGENT_PATH, "KeyboardDisplay"))),
                           ("RequestDefaultAgent", GLib.Variant("(o)", (AGENT_PATH,)))):
        conn.call_sync("org.bluez", "/org/bluez", "org.bluez.AgentManager1", method, params,
                       None, Gio.DBusCallFlags.NONE, 5000, None)
    print("agent registered", flush=True)


def main():
    loop = GLib.MainLoop()
    system = Gio.bus_get_sync(Gio.BusType.SYSTEM)
    Gio.bus_own_name(Gio.BusType.SESSION, "org.kyulio.BluetoothAgent",
                     Gio.BusNameOwnerFlags.ALLOW_REPLACEMENT | Gio.BusNameOwnerFlags.REPLACE,
                     None, None, lambda *_: sys.exit(0))
    Gio.bus_watch_name_on_connection(system, "org.bluez", Gio.BusNameWatcherFlags.NONE,
                                     on_bluez_appeared, None)
    loop.run()


if __name__ == "__main__":
    main()

"""System page: time & language, accessibility, security, about."""

from pathlib import Path

from gi.repository import Adw, Gtk

from helpers import launch, run, run_async, run_ok, toast


def _disk_usage() -> str:
    try:
        lines = run("df", "-h", "/", "--output=used,size,pcent,target"
                    ).splitlines()
        return " ".join(lines[-1].split()) if len(lines) > 1 else "Unknown"
    except Exception:
        return "Unknown"


def _timezone() -> str:
    try:
        return run("timedatectl", "show", "-p", "Timezone", "--value")
    except Exception:
        return "Unknown"


def _weather() -> str:
    try:
        return run("omarchy", "weather", "location")
    except Exception:
        return "Unknown"


def _version() -> str:
    try:
        return run("omarchy", "version")
    except Exception:
        return "Unknown"


def _sudo_pwless() -> bool:
    return run_ok("sudo", "-n", "true")


def build(overlay: Adw.ToastOverlay) -> Adw.PreferencesPage:
    page = Adw.PreferencesPage(title="System & Security",
                               icon_name="emblem-system-symbolic")
    loading = {"v": True}

    # ---- Time & Language ----
    tl = Adw.PreferencesGroup(title="Time & Language")
    page.add(tl)

    tz_row = Adw.ActionRow(title="Timezone", subtitle=_timezone())
    tz_btn = Gtk.Button(label="Change", valign="center")
    tz_btn.connect("clicked", lambda _b: toast(
        overlay, "Opening timezone picker…"
        if run_ok("omarchy", "menu", "timezone")
        else "Timezone picker failed"))
    tz_row.add_suffix(tz_btn)
    tl.add(tz_row)

    ts_row = Adw.ActionRow(title="Time sync",
                           subtitle="Restart system time synchronization")
    ts_btn = Gtk.Button(label="Repair", valign="center")
    ts_btn.connect("clicked", lambda _b: toast(
        overlay, "Time sync restarted"
        if run_ok("omarchy", "update", "time")
        else "Time sync failed (may need a password)"))
    ts_row.add_suffix(ts_btn)
    tl.add(ts_row)

    w_row = Adw.EntryRow(title="Weather location", text=_weather())
    w_row.connect("apply", lambda _r: _apply_weather(overlay, w_row))
    tl.add(w_row)

    # ---- Accessibility ----
    ax = Adw.PreferencesGroup(title="Accessibility")
    page.add(ax)

    tx_row = Adw.ActionRow(title="Text size",
                           subtitle="Global shell, app and terminal scaling")
    tx_box = Gtk.Box(spacing=6, valign="center")

    def text_bump(_b, delta: int) -> None:
        try:
            import re
            m = re.search(r"text size:\s*(\d+)",
                          run("omarchy", "display", "text", "size"))
            if m:
                run("omarchy", "display", "text", "size",
                    str(max(8, int(m.group(1)) + delta)))
                toast(overlay, "Text size updated")
        except Exception as exc:  # noqa: BLE001
            toast(overlay, f"Text size failed: {exc}")
    tx_down = Gtk.Button(label="−")
    tx_up = Gtk.Button(label="+")
    tx_down.connect("clicked", text_bump, -1)
    tx_up.connect("clicked", text_bump, 1)
    tx_box.append(tx_down)
    tx_box.append(tx_up)
    tx_row.add_suffix(tx_box)
    ax.add(tx_row)

    ax.add(Adw.ActionRow(
        title="Honest gaps",
        subtitle="No screen reader, magnifier or sticky-keys backend "
                 "ships with Hyprland — these are not faked here"))

    # ---- Security ----
    sec = Adw.PreferencesGroup(title="Security")
    page.add(sec)

    for label, args in (
            ("Fingerprint login", ["setup", "security", "fingerprint"]),
            ("FIDO2 security key", ["setup", "security", "fido2"]),
            ("SSH server", ["setup", "security", "sshd"])):
        r = Adw.ActionRow(title=label,
                          subtitle="Opens the interactive setup wizard")
        b = Gtk.Button(label="Set up", valign="center")
        b.connect("clicked",
                  lambda _x, a=args: _wizard(overlay, a))
        r.add_suffix(b)
        sec.add(r)

    sudo_row = Adw.ActionRow(
        title="Passwordless sudo",
        subtitle="On" if _sudo_pwless() else "Off")
    sudo_box = Gtk.Box(spacing=6, valign="center")
    sudo_go = Gtk.Button(label="Change")
    sudo_go.connect("clicked", lambda _b: toast(
        overlay, "Opening sudo settings…"
        if launch("omarchy-launch-terminal", "omarchy", "sudo",
                  "passwordless")
        else "Could not open terminal"))
    sudo_ref = Gtk.Button(label="Refresh")
    sudo_ref.connect("clicked", lambda _b: sudo_row.set_subtitle(
        "On" if _sudo_pwless() else "Off"))
    sudo_box.append(sudo_go)
    sudo_box.append(sudo_ref)
    sudo_row.add_suffix(sudo_box)
    sec.add(sudo_row)

    # ---- About ----
    ab = Adw.PreferencesGroup(title="About this PC")
    page.add(ab)
    ab.add(Adw.ActionRow(title="Omarchy version", subtitle=_version()))
    ab.add(Adw.ActionRow(title="Timezone", subtitle=_timezone()))
    info_row = Adw.ActionRow(title="System info",
                             subtitle="Full fastfetch report")
    info_btn = Gtk.Button(label="Open", valign="center")
    info_btn.connect("clicked", lambda _b: toast(
        overlay, "Opening system info…"
        if launch("omarchy-launch-terminal", "omarchy", "launch", "about")
        else "Could not open system info"))
    info_row.add_suffix(info_btn)
    ab.add(info_row)

    # ---- Storage & Snapshots ----
    st = Adw.PreferencesGroup(title="Storage & Snapshots")
    page.add(st)

    du_row = Adw.ActionRow(title="Disk usage (/)", subtitle=_disk_usage())
    du_btn = Gtk.Button(label="Refresh", valign="center")
    du_btn.connect("clicked",
                   lambda _b: du_row.set_subtitle(_disk_usage()))
    du_row.add_suffix(du_btn)
    st.add(du_row)

    sp_row = Adw.ActionRow(title="Disk speed",
                           subtitle="Measure read/write speed")
    sp_btn = Gtk.Button(label="Test", valign="center")

    def on_sp(_b) -> None:
        sp_row.set_subtitle("Testing…")

        def done(ok: bool, msg: str) -> None:
            sp_row.set_subtitle(
                msg.strip().splitlines()[-1] if ok and msg.strip()
                else "Speed test failed")
        run_async(["omarchy", "disk", "speedtest",
                   str(Path.home())], done, timeout=180)
    sp_btn.connect("clicked", on_sp)
    sp_row.add_suffix(sp_btn)
    st.add(sp_row)

    for label, action in (("Create snapshot", "create"),
                          ("Restore snapshot", "restore")):
        r = Adw.ActionRow(title=f"System snapshots — {label.lower()}",
                          subtitle="Needs your password")
        b = Gtk.Button(label="Open", valign="center")
        b.connect("clicked",
                  lambda _x, a=action, l=label: _confirm(
                      overlay, f"{l}?",
                      "Snapshots protect your system. Continue?",
                      ["omarchy-launch-terminal", "omarchy",
                       "snapshot", a]))
        r.add_suffix(b)
        st.add(r)

    # ---- Diagnostics ----
    dg = Adw.PreferencesGroup(title="Diagnostics")
    page.add(dg)

    pid_row = Adw.EntryRow(title="Crashed process ID",
                           subtitle="Find it in the crash notification")
    pid_btn = Gtk.Button(label="Diagnose", valign="center")

    def on_diag(_b) -> None:
        pid = pid_row.get_text().strip()
        if not pid.isdigit():
            toast(overlay, "Enter a numeric process ID")
            return
        if launch("omarchy-launch-terminal", "omarchy", "agent",
                  "crash", pid):
            toast(overlay, "Opening crash diagnosis…")
        else:
            toast(overlay, "Could not start diagnosis")
    pid_btn.connect("clicked", on_diag)
    pid_row.add_suffix(pid_btn)
    dg.add(pid_row)

    loading["v"] = False
    return page


def _confirm(overlay: Adw.ToastOverlay, heading: str, body: str,
             cmd: list) -> None:
    dlg = Adw.MessageDialog(transient_for=overlay.get_root(),
                            heading=heading, body=body)
    dlg.add_response("cancel", "Cancel")
    dlg.add_response("go", "Continue")
    dlg.set_response_appearance("go", Adw.ResponseAppearance.DESTRUCTIVE)

    def on_resp(_d, resp: str) -> None:
        if resp != "go":
            return
        if launch(*cmd):
            toast(overlay, "Opening…")
        else:
            toast(overlay, "Could not start")
    dlg.connect("response", on_resp)
    dlg.present()


def _apply_weather(overlay: Adw.ToastOverlay, row: Adw.EntryRow) -> None:
    name = row.get_text().strip()
    if not name:
        return
    try:
        run("omarchy", "weather", "location", "--set", name)
        toast(overlay, f"Weather → {name}")
    except Exception as exc:  # noqa: BLE001
        toast(overlay, f"Weather change failed: {exc}")


def _wizard(overlay: Adw.ToastOverlay, args: list) -> None:
    if launch("omarchy-launch-terminal", "omarchy", *args):
        toast(overlay, "Opening setup wizard…")
    else:
        toast(overlay, "Could not open setup wizard")

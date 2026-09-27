"""Notifications page: do-not-disturb, history, test ping."""

from gi.repository import Adw, Gtk

from helpers import run, run_ok, toast


def _dnd() -> bool:
    try:
        return run("omarchy-shell", "notifications",
                   "isDnd").strip().lower() == "on"
    except Exception:
        return False


def build(overlay: Adw.ToastOverlay) -> Adw.PreferencesPage:
    page = Adw.PreferencesPage(title="Notifications",
                               icon_name="notifications-symbolic")
    loading = {"v": True}

    grp = Adw.PreferencesGroup(title="Notifications")
    page.add(grp)

    dnd_row = Adw.SwitchRow(title="Do not disturb",
                            subtitle="Silence all notifications")
    dnd_row.set_active(_dnd())

    def on_dnd(_r, _p) -> None:
        if loading["v"]:
            return
        want = dnd_row.get_active()

        def revert() -> None:
            loading["v"] = True
            dnd_row.set_active(not want)
            loading["v"] = False

        try:
            if _dnd() == want:
                return
        except Exception as exc:  # noqa: BLE001
            revert()
            toast(overlay, f"DND read failed: {exc}")
            return
        # toggleDnd flips unconditionally: only call when needed.
        if not run_ok("omarchy", "toggle", "notification-silencing"):
            revert()
            toast(overlay, "DND toggle failed")
            return
        try:
            ok = _dnd() == want
        except Exception:
            ok = False
        if ok:
            toast(overlay, "Do not disturb on" if want
                  else "Notifications allowed")
        else:
            revert()
            toast(overlay, "DND out of sync, reverted")
    dnd_row.connect("notify::active", on_dnd)
    grp.add(dnd_row)

    hist_row = Adw.ActionRow(title="History",
                             subtitle="Open past notifications")
    hist_btn = Gtk.Button(label="Open", valign="center")
    hist_btn.connect("clicked", lambda _b: toast(
        overlay, "Opening history…"
        if run_ok("omarchy-shell", "notifications", "showHistory")
        else "History failed"))
    hist_row.add_suffix(hist_btn)
    grp.add(hist_row)

    test_row = Adw.ActionRow(title="Test notification",
                             subtitle="Send yourself a ping")
    test_btn = Gtk.Button(label="Send", valign="center")
    test_btn.connect("clicked", lambda _b: toast(
        overlay, "Ping sent — look for it"
        if run_ok("omarchy", "notification", "send", "Settings test",
                  "This is a test notification", "-u", "low")
        else "Test ping failed"))
    test_row.add_suffix(test_btn)
    grp.add(test_row)

    loading["v"] = False
    return page

"""Updates page: check, apply, firmware, post-update actions."""

from gi.repository import Adw, Gtk

from helpers import launch, run_async_raw, toast


def build(overlay: Adw.ToastOverlay) -> Adw.PreferencesPage:
    page = Adw.PreferencesPage(title="System Updates",
                               icon_name="software-update-available-symbolic")

    grp = Adw.PreferencesGroup(
        title="Updates",
        description="Checking is instant; applying opens a terminal "
                    "and may ask for your password")
    page.add(grp)

    st_row = Adw.ActionRow(title="Status",
                           subtitle="Press Check for the latest state")
    st_btn = Gtk.Button(label="Check", valign="center")

    def on_check(_b) -> None:
        st_row.set_subtitle("Checking…")

        def done(_rc: int, msg: str) -> None:
            # `update available` exits 1 with "up to date" — output,
            # not failure. Show whatever it said.
            st_row.set_subtitle(
                msg.strip().splitlines()[0] if msg.strip()
                else "Check failed")
        run_async_raw(["omarchy", "update", "available"], done, timeout=120)
    st_btn.connect("clicked", on_check)
    st_row.add_suffix(st_btn)
    grp.add(st_row)

    for label, sub, cmd in (
            ("Apply updates", "System + Omarchy packages",
             ["omarchy-launch-terminal", "omarchy", "update", "-y"]),
            ("Firmware", "Update device firmware via fwupd",
             ["omarchy-launch-terminal", "omarchy", "update", "firmware"]),
            ("Post-update actions", "Reboot or restart services if needed",
             ["omarchy-launch-terminal", "omarchy", "update", "restart"]),
            ("Clean up", "Prune package cache and review orphans",
             ["omarchy-launch-terminal", "omarchy", "update", "pkg",
              "prune"])):
        r = Adw.ActionRow(title=label, subtitle=sub)
        b = Gtk.Button(label="Open", valign="center")
        b.connect("clicked",
                  lambda _x, c=cmd, l=label: _confirm(overlay, l, c))
        r.add_suffix(b)
        grp.add(r)

    return page


def _confirm(overlay: Adw.ToastOverlay, label: str, cmd: list) -> None:
    dlg = Adw.MessageDialog(transient_for=overlay.get_root(),
                            heading=f"{label}?",
                            body="This runs in a terminal and may take "
                                 "a while. Continue?")
    dlg.add_response("cancel", "Cancel")
    dlg.add_response("go", "Continue")
    dlg.set_response_appearance("go", Adw.ResponseAppearance.SUGGESTED)

    def on_resp(_d, resp: str) -> None:
        if resp != "go":
            return
        if launch(*cmd):
            toast(overlay, "Opening…")
        else:
            toast(overlay, "Could not start")
    dlg.connect("response", on_resp)
    dlg.present()

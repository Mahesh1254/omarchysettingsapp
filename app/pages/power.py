"""Power & Battery page: profiles, suspend, stay-awake, battery, hibernation."""

from gi.repository import Adw, Gtk

from helpers import launch, parse_json_flag, run, run_ok, toast


def _profiles() -> tuple[list[str], int]:
    try:
        names, active = [], 0
        for i, ln in enumerate(
                run("omarchy", "powerprofiles", "list",
                    "--active-state").splitlines()):
            parts = ln.split()
            if not parts:
                continue
            names.append(parts[0])
            if len(parts) > 1 and parts[1] == "1":
                active = i
        return (names or ["balanced"], active)
    except Exception:
        return (["balanced"], 0)


def _suspend() -> bool:
    # flag suspend-off present = removed from menu
    return not run_ok("omarchy", "toggle", "enabled", "suspend-off")


def _stay_awake() -> bool:
    try:
        return parse_json_flag(run("omarchy", "toggle", "idle", "status"),
                               "enabled")
    except Exception:
        return False


def _battery() -> str:
    try:
        return run("omarchy", "battery", "status")
    except Exception:
        return "Unknown"


def _hibernation() -> bool:
    return run_ok("omarchy", "hibernation", "available")


def build(overlay: Adw.ToastOverlay) -> Adw.PreferencesPage:
    page = Adw.PreferencesPage(title="Power & Battery",
                               icon_name="battery-good-symbolic")
    loading = {"v": True}

    grp = Adw.PreferencesGroup(title="Power")
    page.add(grp)

    names, active = _profiles()
    prof = Adw.ComboRow(title="Power profile",
                        subtitle="Applies to the current power source",
                        model=Gtk.StringList.new(names))
    prof.set_selected(active)

    def on_prof(_r, _p) -> None:
        if loading["v"]:
            return
        name = names[prof.get_selected()]
        try:
            run("omarchy", "powerprofiles", "set", "autodetect", name)
            toast(overlay, f"Power profile → {name}")
        except Exception as exc:  # noqa: BLE001
            loading["v"] = True
            prof.set_selected(active)
            loading["v"] = False
            toast(overlay, f"Profile change failed: {exc}")
    prof.connect("notify::selected", on_prof)
    grp.add(prof)

    ppanel = Adw.ActionRow(title="Power panel",
                           subtitle="Native quick-settings popup")
    ppanel_btn = Gtk.Button(label="Open", valign="center")
    ppanel_btn.connect("clicked", lambda _b: toast(
        overlay, "Panel failed to open")
        if not run_ok("omarchy-shell", "shell", "toggle", "omarchy.power")
        else None)
    ppanel.add_suffix(ppanel_btn)
    grp.add(ppanel)

    sp_row = Adw.SwitchRow(title="Suspend in system menu",
                           subtitle="Show the suspend option")
    sp_row.set_active(_suspend())

    def on_sp(_r, _p) -> None:
        if loading["v"]:
            return
        want = sp_row.get_active()

        def revert() -> None:
            loading["v"] = True
            sp_row.set_active(not want)
            loading["v"] = False

        # toggle binary takes no on/off: flip only when needed, then verify.
        if _suspend() == want:
            return
        if not run_ok("omarchy", "toggle", "suspend"):
            revert()
            toast(overlay, "Suspend toggle failed")
            return
        if _suspend() == want:
            toast(overlay, "Suspend in menu" if want
                  else "Suspend hidden")
        else:
            revert()
            toast(overlay, "Suspend out of sync, reverted")
    sp_row.connect("notify::active", on_sp)
    grp.add(sp_row)

    sa_row = Adw.SwitchRow(title="Stay awake",
                           subtitle="Prevent idle sleep and lock")
    sa_row.set_active(_stay_awake())

    def on_sa(_r, _p) -> None:
        if loading["v"]:
            return
        action = "stay-awake" if sa_row.get_active() else "allow-idle"
        if run_ok("omarchy", "toggle", "idle", action):
            toast(overlay, "Staying awake" if sa_row.get_active()
                  else "Idle sleep allowed")
        else:
            loading["v"] = True
            sa_row.set_active(not sa_row.get_active())
            loading["v"] = False
            toast(overlay, "Idle toggle failed")
    sa_row.connect("notify::active", on_sa)
    grp.add(sa_row)

    batt = Adw.PreferencesGroup(title="Battery")
    page.add(batt)

    b_row = Adw.ActionRow(title="Status", subtitle=_battery())
    b_ref = Gtk.Button(label="Refresh", valign="center")
    b_ref.connect("clicked",
                  lambda _b: b_row.set_subtitle(_battery()))
    b_row.add_suffix(b_ref)
    batt.add(b_row)

    hib_ok = _hibernation()
    h_row = Adw.ActionRow(title="Hibernation",
                          subtitle="Supported on this machine" if hib_ok
                          else "Not available on this machine")
    if hib_ok:
        h_btn = Gtk.Button(label="Set up", valign="center")
        h_btn.connect("clicked", lambda _b: toast(
            overlay, "Opening setup wizard…"
            if launch("omarchy-launch-terminal", "omarchy",
                      "hibernation", "setup")
            else "Could not open setup wizard"))
        h_row.add_suffix(h_btn)
    batt.add(h_row)

    loading["v"] = False
    return page

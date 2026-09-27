"""Apps & Recovery page: defaults, web apps, startup, config resets."""

from pathlib import Path

from gi.repository import Adw, Gtk

from helpers import launch, run, run_ok, toast

BROWSERS = ["brave", "brave-origin", "chrome", "chromium", "edge",
            "firefox", "zen"]
EDITORS = ["code", "cursor", "zed", "sublime_text", "helix", "vim",
           "emacs", "nvim"]
TERMINALS = ["alacritty", "foot", "ghostty", "kitty"]

REFRESH_AREAS = [
    ("Hyprland config", "hyprland",
     "Overwrites ~/.config/hypr (backed up first)"),
    ("Shell / bar", "shell", "Resets shell.json (backed up first)"),
    ("Night light config", "hyprsunset", "Resets hyprsunset.conf"),
    ("Terminal configs", "terminal", "Reloads supported terminals"),
]


def _current(kind: str, options: list[str]) -> int:
    try:
        cur = run("omarchy", "default", kind).strip().lower()
        for i, name in enumerate(options):
            if name.lower() == cur:
                return i
    except Exception:
        pass
    return 0


def build(overlay: Adw.ToastOverlay) -> Adw.PreferencesPage:
    page = Adw.PreferencesPage(title="Apps & Recovery",
                               icon_name="application-x-executable-symbolic")
    loading = {"v": True}

    apps = Adw.PreferencesGroup(title="Default apps")
    page.add(apps)

    for label, kind, options in (
            ("Web browser", "browser", BROWSERS),
            ("Editor", "editor", EDITORS),
            ("Terminal", "terminal", TERMINALS)):
        row = Adw.ComboRow(title=label,
                           model=Gtk.StringList.new(options))
        row.set_selected(_current(kind, options))

        def on_change(_r, _p, k=kind, opts=options, rr=row) -> None:
            if loading["v"]:
                return
            name = opts[rr.get_selected()]
            try:
                run("omarchy", "default", k, name)
                toast(overlay, f"Default {k} → {name}")
            except Exception as exc:  # noqa: BLE001
                toast(overlay, f"Default change failed: {exc}")
        row.connect("notify::selected", on_change)
        apps.add(row)

    for label, sub, cmd in (
            ("Install a web app", "Name + URL, guided",
             ["omarchy-launch-terminal", "omarchy", "webapp", "install"]),
            ("Remove a web app", "Pick from your installed list",
             ["omarchy-launch-terminal", "omarchy", "webapp", "remove"]),
            ("Install a terminal app", "TUI launcher creator",
             ["omarchy-launch-terminal", "omarchy", "tui", "install"]),
            ("Remove a terminal app", "Pick from your installed list",
             ["omarchy-launch-terminal", "omarchy", "tui", "remove"]),
            ("Startup apps", "Edit what launches at login",
             ["omarchy-launch-terminal", "omarchy", "launch",
              "config", "editor",
              str(Path.home() / ".config/hypr/autostart.lua")])):
        r = Adw.ActionRow(title=label, subtitle=sub)
        b = Gtk.Button(label="Open", valign="center")
        b.connect("clicked",
                  lambda _x, c=cmd: toast(
                      overlay, "Opening…"
                      if launch(*c) else "Could not open"))
        r.add_suffix(b)
        apps.add(r)

    rec = Adw.PreferencesGroup(
        title="Recovery",
        description="Resets back up your config first — nothing is lost")
    page.add(rec)

    for label, area, sub in REFRESH_AREAS:
        r = Adw.ActionRow(title=f"Reset {label}", subtitle=sub)
        b = Gtk.Button(label="Reset", valign="center")
        b.connect("clicked",
                  lambda _x, a=area, l=label: _confirm(
                      overlay, f"Reset {l}?",
                      "Your current config is backed up first.", False,
                      ["omarchy", "refresh", a]))
        r.add_suffix(b)
        rec.add(r)

    for label, sub, cmd in (
            ("Restart shell", "Reload the bar and widgets",
             ["omarchy", "restart", "shell"]),
            ("Reload Hyprland config", "Re-read all Hyprland settings",
             ["omarchy", "restart", "hyprctl"])):
        r = Adw.ActionRow(title=label, subtitle=sub)
        b = Gtk.Button(label="Run", valign="center")
        b.connect("clicked",
                  lambda _x, c=cmd, l=label: _confirm(
                      overlay, f"{l}?",
                      "Safe to run any time.", False, c, background=True))
        r.add_suffix(b)
        rec.add(r)

    fr = Adw.ActionRow(title="Factory reset",
                       subtitle="Return to freshly-installed state")
    fr_btn = Gtk.Button(label="Reset…", valign="center")
    fr_btn.connect("clicked", lambda _b: _factory_step1(overlay))
    fr.add_suffix(fr_btn)
    rec.add(fr)

    loading["v"] = False
    return page


def _confirm(overlay: Adw.ToastOverlay, heading: str, body: str,
             destructive: bool, cmd: list,
             background: bool = False) -> None:
    dlg = Adw.MessageDialog(transient_for=overlay.get_root(),
                            heading=heading, body=body)
    dlg.add_response("cancel", "Cancel")
    dlg.add_response("go", "Continue")
    dlg.set_response_appearance(
        "go", Adw.ResponseAppearance.DESTRUCTIVE if destructive
        else Adw.ResponseAppearance.SUGGESTED)

    def on_resp(_d, resp: str) -> None:
        if resp != "go":
            return
        if background:
            if run_ok(*cmd):
                toast(overlay, "Done")
            else:
                toast(overlay, "Failed")
        else:
            if launch("omarchy-launch-terminal", *cmd):
                toast(overlay, "Opening…")
            else:
                toast(overlay, "Could not start")
    dlg.connect("response", on_resp)
    dlg.present()


def _factory_step1(overlay: Adw.ToastOverlay) -> None:
    dlg = Adw.MessageDialog(
        transient_for=overlay.get_root(),
        heading="Factory reset?",
        body="This erases your personalizations and returns Omarchy "
             "to its freshly-installed state. This is the last resort.")
    dlg.add_response("cancel", "Cancel")
    dlg.add_response("go", "I understand, continue")
    dlg.set_response_appearance("go", Adw.ResponseAppearance.DESTRUCTIVE)
    dlg.connect("response",
                lambda _d, r: _factory_step2(overlay) if r == "go" else None)
    dlg.present()


def _factory_step2(overlay: Adw.ToastOverlay) -> None:
    dlg = Adw.MessageDialog(
        transient_for=overlay.get_root(), heading="Are you really sure?",
        body="Second and final confirmation. Your configs should already "
             "be backed up elsewhere.")
    dlg.add_response("cancel", "Cancel")
    dlg.add_response("go", "Factory reset")
    dlg.set_response_appearance("go", Adw.ResponseAppearance.DESTRUCTIVE)

    def on_resp(_d, resp: str) -> None:
        if resp != "go":
            return
        if launch("omarchy-launch-terminal", "omarchy", "setup",
                  "factory", "reset"):
            toast(overlay, "Opening factory reset…")
        else:
            toast(overlay, "Could not start")
    dlg.connect("response", on_resp)
    dlg.present()

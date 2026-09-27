"""Personalization page: theme, background, bar position."""

from gi.repository import Adw, Gtk

from helpers import launch, run, run_async, run_ok, toast


def _themes() -> list[str]:
    try:
        return [t for t in run("omarchy", "theme", "list").splitlines()
                if t.strip()]
    except Exception:
        return []


def _fonts() -> list[str]:
    try:
        return [f for f in run("omarchy", "font", "list").splitlines()
                if f.strip()]
    except Exception:
        return []


def _font_idx(fonts: list[str]) -> int:
    try:
        cur = run("omarchy", "font", "current").strip().lower()
        for i, name in enumerate(fonts):
            if name.strip().lower() == cur:
                return i
    except Exception:
        pass
    return 0


def _splashes() -> list[str]:
    try:
        return [s for s in run("omarchy", "plymouth", "list").splitlines()
                if s.strip()]
    except Exception:
        return []


def _splash_idx(splashes: list[str]) -> int:
    try:
        cur = run("omarchy", "plymouth", "current").strip().lower()
        for i, name in enumerate(splashes):
            if name.strip().lower() == cur:
                return i
    except Exception:
        pass
    return 0


def _flag_on(flag: str) -> bool:
    """Omarchy *-off flags: file present means DISABLED."""
    return not run_ok("omarchy", "toggle", "enabled", f"{flag}-off")


def _current_theme(themes: list[str]) -> int:
    try:
        cur = run("omarchy", "theme", "current").strip().lower()
        for i, name in enumerate(themes):
            if name.strip().lower() == cur:
                return i
    except Exception:
        pass
    return 0


def build(overlay: Adw.ToastOverlay) -> Adw.PreferencesPage:
    page = Adw.PreferencesPage(title="Personalization",
                               icon_name="preferences-desktop-wallpaper-symbolic")
    loading = {"v": True}

    appear = Adw.PreferencesGroup(title="Appearance")
    page.add(appear)

    themes = _themes() or ["Ethereal"]
    theme_row = Adw.ComboRow(title="Theme",
                             subtitle="Applying takes a few seconds",
                             model=Gtk.StringList.new(themes))
    theme_row.set_selected(_current_theme(themes))

    def on_theme_done(ok: bool, msg: str, row=theme_row) -> None:
        row.set_sensitive(True)
        toast(overlay, f"Theme applied" if ok else f"Theme failed: {msg}")

    def on_theme(_r, _p) -> None:
        if loading["v"]:
            return
        name = themes[theme_row.get_selected()]
        theme_row.set_sensitive(False)
        toast(overlay, f"Applying {name}…")
        run_async(["omarchy", "theme", "set", name], on_theme_done)
    theme_row.connect("notify::selected", on_theme)
    appear.add(theme_row)

    bg_row = Adw.ActionRow(title="Background",
                           subtitle="Cycle to the next wallpaper")
    bg_btn = Gtk.Button(label="Next", valign="center")
    bg_btn.connect("clicked", lambda _b: toast(
        overlay, "Background changed" if run_ok("omarchy", "theme",
                                                "bg", "next")
        else "Background change failed"))
    bg_row.add_suffix(bg_btn)
    appear.add(bg_row)

    bar = Adw.PreferencesGroup(title="Top bar")
    page.add(bar)

    pos_row = Adw.ComboRow(title="Bar position",
                           model=Gtk.StringList.new(["top", "bottom"]))
    pos_row.set_selected(0)

    def on_pos(_r, _p) -> None:
        if loading["v"]:
            return
        pos = "top" if pos_row.get_selected() == 0 else "bottom"
        if run_ok("omarchy", "bar", "position", pos):
            toast(overlay, f"Bar → {pos}")
        else:
            toast(overlay, "Bar move failed")
    pos_row.connect("notify::selected", on_pos)
    bar.add(pos_row)

    vis_row = Adw.SwitchRow(title="Bar visible")
    vis_row.set_active(not _flag_on("bar"))

    def on_vis(_r, _p) -> None:
        if loading["v"]:
            return
        # flag file present = bar hidden; invert for the switch
        state = "off" if vis_row.get_active() else "on"
        if run_ok("omarchy", "toggle", "bar", state):
            toast(overlay, "Bar shown" if vis_row.get_active()
                  else "Bar hidden")
        else:
            loading["v"] = True
            vis_row.set_active(not vis_row.get_active())
            loading["v"] = False
            toast(overlay, "Bar toggle failed")
    vis_row.connect("notify::active", on_vis)
    bar.add(vis_row)

    fonts = _fonts()
    if fonts:
        font_row = Adw.ComboRow(title="Monospace font",
                                model=Gtk.StringList.new(fonts))
        font_row.set_selected(_font_idx(fonts))

        def on_font(_r, _p) -> None:
            if loading["v"]:
                return
            name = fonts[font_row.get_selected()]
            try:
                run("omarchy", "font", "set", name)
                toast(overlay, f"Font → {name}")
            except Exception as exc:  # noqa: BLE001
                toast(overlay, f"Font change failed: {exc}")
        font_row.connect("notify::selected", on_font)
        appear.add(font_row)

    splashes = _splashes()
    if splashes:
        sp_row = Adw.ComboRow(title="Boot splash",
                              subtitle="Needs your password — opens a terminal",
                              model=Gtk.StringList.new(splashes))
        sp_row.set_selected(_splash_idx(splashes))

        def on_splash(_r, _p) -> None:
            if loading["v"]:
                return
            name = splashes[sp_row.get_selected()]
            if launch("omarchy-launch-terminal", "omarchy", "plymouth",
                      "set", "by", "theme", name):
                toast(overlay, f"Applying splash in terminal…")
            else:
                toast(overlay, "Could not open terminal")
        sp_row.connect("notify::selected", on_splash)
        appear.add(sp_row)

    ss_row = Adw.SwitchRow(title="Screensaver")
    ss_row.set_active(not _flag_on("screensaver"))

    def on_ss(_r, _p) -> None:
        if loading["v"]:
            return
        want = ss_row.get_active()

        def revert() -> None:
            loading["v"] = True
            ss_row.set_active(not want)
            loading["v"] = False

        # toggle binary takes no on/off: flip only when needed, then verify.
        if _flag_on("screensaver") == want:
            return
        if not run_ok("omarchy", "toggle", "screensaver"):
            revert()
            toast(overlay, "Screensaver toggle failed")
            return
        if _flag_on("screensaver") == want:
            toast(overlay, "Screensaver on" if want else "Screensaver off")
        else:
            revert()
            toast(overlay, "Screensaver out of sync, reverted")
    ss_row.connect("notify::active", on_ss)
    appear.add(ss_row)

    kbd_row = Adw.ActionRow(title="Keyboard backlight")
    kbd_box = Gtk.Box(spacing=6, valign="center")
    for label, arg in (("Up", "up"), ("Down", "down"), ("Off", "off")):
        b = Gtk.Button(label=label)
        b.connect("clicked", lambda _x, a=arg: toast(
            overlay, "Backlight adjusted"
            if run_ok("omarchy", "brightness", "keyboard", a)
            else "Backlight failed"))
        kbd_box.append(b)
    kbd_row.add_suffix(kbd_box)
    appear.add(kbd_row)

    loading["v"] = False
    return page

"""Sound + Display page: volume, mute, brightness, night light."""

from gi.repository import Adw, Gtk

from helpers import parse_volume_percent, run, run_ok, toast


def _volume() -> int:
    try:
        return parse_volume_percent(run("pactl", "get-sink-volume",
                                        "@DEFAULT_SINK@"))
    except Exception:
        return -1


def _muted() -> bool:
    try:
        return "yes" in run("pactl", "get-sink-mute", "@DEFAULT_SINK@")
    except Exception:
        return False


def _brightness() -> int:
    try:
        return int(run("omarchy-brightness-display"))
    except Exception:
        return -1


def _nightlight() -> bool:
    try:
        import json
        return bool(json.loads(run("omarchy", "toggle", "nightlight",
                                   "--status")).get("enabled", False))
    except Exception:
        return False


def _sinks() -> list[tuple[str, str]]:
    try:
        return [(p[0], p[1]) for ln in
                run("pactl", "list", "sinks", "short").splitlines()
                if (p := ln.split()) and len(p) >= 2]
    except Exception:
        return []


def _mic_sources() -> list[tuple[str, str]]:
    try:
        return [(p[0], p[1]) for ln in
                run("pactl", "list", "sources", "short").splitlines()
                if (p := ln.split()) and len(p) >= 2
                and not p[1].endswith(".monitor")]
    except Exception:
        return []


def _default_sink() -> str:
    try:
        return run("pactl", "get-default-sink")
    except Exception:
        return ""


def _default_source() -> str:
    try:
        return run("pactl", "get-default-source")
    except Exception:
        return ""


def _mic_muted() -> bool:
    srcs = _mic_sources()
    if not srcs:
        return False
    try:
        return "yes" in run("pactl", "get-source-mute", srcs[0][1])
    except Exception:
        return False


def _tuning_summary() -> str:
    try:
        for ln in run("omarchy", "audio", "tuning", "status").splitlines():
            if ln.startswith("Matches:"):
                return ln.split(":", 1)[1].strip()
    except Exception:
        pass
    return "unknown"


def _scaling() -> str:
    try:
        return run("omarchy", "hyprland", "monitor", "scaling")
    except Exception:
        return "?"


def _text_size() -> int:
    try:
        import re
        m = re.search(r"text size:\s*(\d+)", run("omarchy", "display",
                                                "text", "size"))
        return int(m.group(1)) if m else -1
    except Exception:
        return -1


def build(overlay: Adw.ToastOverlay) -> Adw.PreferencesPage:
    page = Adw.PreferencesPage(title="Sound + Display",
                               icon_name="audio-volume-high-symbolic")
    loading = {"v": True}

    # ---- Sound ----
    sound = Adw.PreferencesGroup(title="Sound")
    page.add(sound)

    vol = _volume()
    adj = Gtk.Adjustment(value=vol if vol >= 0 else 50, lower=0, upper=100,
                         step_increment=1, page_increment=5)
    vol_row = Adw.ActionRow(title="Output volume")
    scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL,
                      adjustment=adj, digits=0, hexpand=True, valign="center",
                      width_request=220)
    scale.set_draw_value(True)
    vol_row.add_suffix(scale)
    vol_row.set_subtitle("Drag for exact level" if vol < 0
                         else f"Currently {vol}%")

    def on_vol_changed(_s: Gtk.Scale) -> None:
        if loading["v"]:
            return
        v = int(adj.get_value())
        try:
            run("pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{v}%")
            vol_row.set_subtitle(f"Currently {v}%")
        except Exception as exc:  # noqa: BLE001
            toast(overlay, f"Volume failed: {exc}")
    scale.connect("value-changed", on_vol_changed)
    sound.add(vol_row)

    mute_row = Adw.SwitchRow(title="Mute output")
    mute_row.set_active(_muted())

    def on_mute(_r, _p) -> None:
        if loading["v"]:
            return
        if run_ok("omarchy-audio-output-volume", "mute-toggle"):
            toast(overlay, "Muted" if mute_row.get_active() else "Unmuted")
        else:
            loading["v"] = True
            mute_row.set_active(not mute_row.get_active())
            loading["v"] = False
            toast(overlay, "Mute toggle failed")
    mute_row.connect("notify::active", on_mute)
    sound.add(mute_row)

    out_row = Adw.ActionRow(title="Audio output",
                            subtitle="Switch speaker / headphones / HDMI")
    out_btn = Gtk.Button(label="Switch", valign="center")
    out_btn.connect("clicked", lambda _b: toast(
        overlay, "Switched" if run_ok("omarchy-audio-output-switch")
        else "Output switch failed"))
    out_row.add_suffix(out_btn)
    sound.add(out_row)

    panel_row = Adw.ActionRow(title="Audio panel",
                              subtitle="Native quick-settings popup")
    panel_btn = Gtk.Button(label="Open", valign="center")
    panel_btn.connect("clicked", lambda _b: toast(
        overlay, "Panel failed to open")
        if not run_ok("omarchy-shell", "shell", "toggle", "omarchy.audio")
        else None)
    panel_row.add_suffix(panel_btn)
    sound.add(panel_row)

    # ---- Devices ----
    dev = Adw.PreferencesGroup(
        title="Devices",
        description="New outputs (headphones, HDMI) appear here when plugged in")
    page.add(dev)

    sinks = _sinks()
    if sinks:
        cur_sink = _default_sink()
        out_pick = Adw.ComboRow(
            title="Output device",
            model=Gtk.StringList.new([n for _, n in sinks]))
        out_pick.set_selected(next(
            (i for i, (_, n) in enumerate(sinks) if n == cur_sink), 0))

        def on_sink(_r, _p) -> None:
            if loading["v"]:
                return
            nid, name = sinks[out_pick.get_selected()]
            try:
                run("omarchy", "audio", "output", "set", "default",
                    nid, name)
                toast(overlay, f"Output → {name}")
            except Exception as exc:  # noqa: BLE001
                toast(overlay, f"Output switch failed: {exc}")
        out_pick.connect("notify::selected", on_sink)
        dev.add(out_pick)
    else:
        dev.add(Adw.ActionRow(title="Output device",
                              subtitle="No sinks found"))

    srcs = _mic_sources()
    if srcs:
        cur_src = _default_source()
        in_pick = Adw.ComboRow(
            title="Input device",
            model=Gtk.StringList.new([n for _, n in srcs]))
        in_pick.set_selected(next(
            (i for i, (_, n) in enumerate(srcs) if n == cur_src), 0))

        def on_src(_r, _p) -> None:
            if loading["v"]:
                return
            nid, name = srcs[in_pick.get_selected()]
            try:
                run("omarchy", "audio", "input", "set", "default", nid, name)
                toast(overlay, f"Input → {name}")
            except Exception as exc:  # noqa: BLE001
                toast(overlay, f"Input switch failed: {exc}")
        in_pick.connect("notify::selected", on_src)
        dev.add(in_pick)

    mic_row = Adw.SwitchRow(title="Mute microphone",
                            subtitle="Also drives the mic-mute LED, if present")
    mic_row.set_active(_mic_muted())

    def on_mic(_r, _p) -> None:
        if loading["v"]:
            return
        want = mic_row.get_active()

        def revert() -> None:
            loading["v"] = True
            mic_row.set_active(not want)
            loading["v"] = False

        try:
            if _mic_muted() == want:
                return
        except Exception as exc:  # noqa: BLE001
            revert()
            toast(overlay, f"Mic read failed: {exc}")
            return
        # `audio input mute` is toggle-only: call it only when needed.
        if not run_ok("omarchy", "audio", "input", "mute"):
            revert()
            toast(overlay, "Mic toggle failed")
            return
        try:
            ok = _mic_muted() == want
        except Exception:
            ok = False
        if ok:
            toast(overlay, f"Microphone {'muted' if want else 'live'}")
        else:
            revert()
            toast(overlay, "Mic out of sync, reverted")
    mic_row.connect("notify::active", on_mic)
    dev.add(mic_row)

    dev.add(Adw.ActionRow(title="Speaker tuning",
                          subtitle=_tuning_summary()))

    # ---- Display ----
    disp = Adw.PreferencesGroup(title="Display")
    page.add(disp)

    br = _brightness()
    badj = Gtk.Adjustment(value=br if br >= 0 else 50, lower=1, upper=100,
                          step_increment=1, page_increment=5)
    br_row = Adw.ActionRow(title="Brightness")
    bscale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL,
                       adjustment=badj, digits=0, hexpand=True,
                       valign="center", width_request=220)
    bscale.set_draw_value(True)
    br_row.add_suffix(bscale)
    br_row.set_subtitle("Unknown" if br < 0 else f"Currently {br}%")

    def on_br_changed(_s: Gtk.Scale) -> None:
        if loading["v"]:
            return
        v = int(badj.get_value())
        if run_ok("omarchy-brightness-display", f"{v}%"):
            br_row.set_subtitle(f"Currently {v}%")
        else:
            toast(overlay, "Brightness failed")
    bscale.connect("value-changed", on_br_changed)
    disp.add(br_row)

    nl_row = Adw.SwitchRow(title="Night light",
                           subtitle="Warm screen temperature at night")
    nl_row.set_active(_nightlight())

    def on_nl(_r, _p) -> None:
        if loading["v"]:
            return
        want = nl_row.get_active()

        def revert() -> None:
            loading["v"] = True
            nl_row.set_active(not want)
            loading["v"] = False

        try:
            if _nightlight() == want:
                return
        except Exception as exc:  # noqa: BLE001
            revert()
            toast(overlay, f"Night light read failed: {exc}")
            return
        # NOTE: `omarchy toggle nightlight` takes no on/off argument —
        # bare invocation flips the state, so only call it when needed.
        if not run_ok("omarchy", "toggle", "nightlight"):
            revert()
            toast(overlay, "Night light failed")
            return
        try:
            ok = _nightlight() == want
        except Exception:
            ok = False
        if ok:
            toast(overlay, f"Night light {'on' if want else 'off'}")
        else:
            revert()
            toast(overlay, "Night light out of sync, reverted")
    nl_row.connect("notify::active", on_nl)
    disp.add(nl_row)

    # ---- Monitors ----
    mon = Adw.PreferencesGroup(title="Monitors")
    page.add(mon)

    sc_row = Adw.ActionRow(title="Display scaling",
                           subtitle=f"Currently {_scaling()}")
    sc_box = Gtk.Box(spacing=6, valign="center")
    sc_down = Gtk.Button(label="−")
    sc_up = Gtk.Button(label="+")

    def bump_scale(_b, direction: str) -> None:
        if run_ok("omarchy", "hyprland", "monitor", "scaling", direction):
            sc_row.set_subtitle(f"Currently {_scaling()}")
        else:
            toast(overlay, "Scaling change failed")
    sc_down.connect("clicked", bump_scale, "down")
    sc_up.connect("clicked", bump_scale, "up")
    sc_box.append(sc_down)
    sc_box.append(sc_up)
    sc_row.add_suffix(sc_box)
    mon.add(sc_row)

    ts = _text_size()
    ts_row = Adw.ActionRow(title="Text size",
                           subtitle="Unknown" if ts < 0 else f"Currently {ts} px")
    ts_box = Gtk.Box(spacing=6, valign="center")
    ts_down = Gtk.Button(label="−")
    ts_up = Gtk.Button(label="+")
    ts_reset = Gtk.Button(label="Reset")

    def set_text(size: int) -> None:
        if run_ok("omarchy", "display", "text", "size", str(size)):
            ts_row.set_subtitle(f"Currently {_text_size()} px")
        else:
            toast(overlay, "Text size change failed")

    def bump_text(_b, delta: int) -> None:
        cur = _text_size()
        if cur > 0:
            set_text(max(8, cur + delta))

    def reset_text(_b) -> None:
        if run_ok("omarchy", "display", "text", "size", "reset"):
            ts_row.set_subtitle(f"Currently {_text_size()} px")
        else:
            toast(overlay, "Text size reset failed")
    ts_down.connect("clicked", bump_text, -1)
    ts_up.connect("clicked", bump_text, 1)
    ts_reset.connect("clicked", reset_text)
    ts_box.append(ts_down)
    ts_box.append(ts_up)
    ts_box.append(ts_reset)
    ts_row.add_suffix(ts_box)
    mon.add(ts_row)

    int_row = Adw.ActionRow(
        title="Laptop display",
        subtitle="This is your only monitor — turning it off blanks the screen")
    int_box = Gtk.Box(spacing=6, valign="center")
    int_on = Gtk.Button(label="On")
    int_off = Gtk.Button(label="Off")
    int_on.connect("clicked", lambda _b: toast(
        overlay, "Display on" if run_ok("omarchy", "hyprland", "monitor",
                                        "internal", "on")
        else "Failed"))

    def confirm_off(_b) -> None:
        dlg = Adw.MessageDialog(transient_for=overlay.get_root(),
                                heading="Turn off the only display?",
                                body="Your screen will go black. Only proceed "
                                     "with an external monitor connected.")
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("off", "Turn off")
        dlg.set_response_appearance("off", Adw.ResponseAppearance.DESTRUCTIVE)

        def on_resp(_d, resp: str) -> None:
            if resp != "off":
                return
            if run_ok("omarchy", "hyprland", "monitor", "internal", "off"):
                toast(overlay, "Display off — use recover if needed")
            else:
                toast(overlay, "Failed")
        dlg.connect("response", on_resp)
        dlg.present()
    int_off.connect("clicked", confirm_off)
    int_box.append(int_on)
    int_box.append(int_off)
    int_row.add_suffix(int_box)
    mon.add(int_row)

    mir_row = Adw.ActionRow(title="Display mirroring",
                            subtitle="Mirror internal display to external")
    mir_box = Gtk.Box(spacing=6, valign="center")
    mir_on = Gtk.Button(label="On")
    mir_off = Gtk.Button(label="Off")
    mir_on.connect("clicked", lambda _b: toast(
        overlay, "Mirroring on" if run_ok("omarchy", "hyprland", "monitor",
                                          "internal", "mirror", "on")
        else "Failed"))
    mir_off.connect("clicked", lambda _b: toast(
        overlay, "Mirroring off" if run_ok("omarchy", "hyprland", "monitor",
                                           "internal", "mirror", "off")
        else "Failed"))
    mir_box.append(mir_on)
    mir_box.append(mir_off)
    mir_row.add_suffix(mir_box)
    mon.add(mir_row)

    loading["v"] = False
    return page

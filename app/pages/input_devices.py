"""Input devices page: touchpad, natural scroll, CapsLock behavior."""

import re
from pathlib import Path

from gi.repository import Adw, Gtk

from helpers import run, run_ok, toast

INPUT_LUA = Path.home() / ".config" / "hypr" / "input.lua"
COMPOSE_OPTS = "compose:caps,shift:both_capslock_cancel"


def _active_lines() -> list[str]:
    """Non-comment lines of input.lua (comments may contain examples)."""
    try:
        text = INPUT_LUA.read_text()
    except OSError:
        return []
    return [ln for ln in text.splitlines()
            if not ln.lstrip().startswith("--")]


def _natural_scroll() -> bool:
    for ln in _active_lines():
        m = re.search(r"natural_scroll\s*=\s*(true|false)", ln)
        if m:
            return m.group(1) == "true"
    return False  # Omarchy default


def _caps_mode() -> int:
    """0 = standard CapsLock, 1 = Compose-on-Caps (Omarchy default)."""
    for ln in _active_lines():
        m = re.search(r'kb_options\s*=\s*"([^"]*)"', ln)
        if m:
            return 1 if "compose:caps" in m.group(1) else 0
    return 1  # Omarchy default


def _set_lua(key: str, value: str) -> bool:
    """Rewrite key = value on its active line, else append an override."""
    try:
        lines = INPUT_LUA.read_text().splitlines()
    except OSError as exc:
        raise RuntimeError(f"Cannot read input.lua: {exc}") from exc
    pat = re.compile(rf"^(\s*{key}\s*=\s*).*$")
    done = False
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("--"):
            continue
        if pat.match(ln):
            lines[i] = pat.sub(rf"\g<1>{value},", ln)
            done = True
            break
    if not done:
        lines.append("hl.config({")
        lines.append("  input = {")
        lines.append(f"    {key} = {value},")
        lines.append("  },")
        lines.append("})")
    INPUT_LUA.write_text("\n".join(lines) + "\n")
    return run_ok("hyprctl", "reload")


def _touchpad_on() -> bool:
    # input devices persist DISABLE with a name file; absent = enabled.
    return not (Path.home() / ".local" / "state" / "omarchy" / "toggles"
                / "hypr" / "touchpad-disabled-name").exists()


def _live(opt: str, default: str = "") -> str:
    """Read a live Hyprland option value (e.g. 'input:repeat_rate')."""
    try:
        out = run("hyprctl", "getoption", opt).splitlines()[0]
        return out.split(":", 1)[1].strip()
    except Exception:
        return default


def _set_touchpad(key: str, value: str) -> bool:
    """Set input.touchpad.<key>, creating the block if needed."""
    try:
        lines = INPUT_LUA.read_text().splitlines()
    except OSError as exc:
        raise RuntimeError(f"Cannot read input.lua: {exc}") from exc
    key_pat = re.compile(rf"^(\s*{key}\s*=\s*).*$")
    tp_pat = re.compile(r"^(\s*)touchpad\s*=\s*\{\s*$")
    tp_indent: str | None = None
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("--"):
            continue
        if tp_indent is None:
            m = tp_pat.match(ln)
            if m:
                tp_indent = m.group(1)
            continue
        if key_pat.match(ln):
            lines[i] = key_pat.sub(rf"\g<1>{value},", ln)
            break
        if ln.strip() == "}," and not ln.startswith(tp_indent + " "):
            pad = tp_indent + "  "
            lines.insert(i, f"{pad}{key} = {value},")
            break
    else:
        lines.append("hl.config({")
        lines.append("  input = {")
        lines.append("    touchpad = {")
        lines.append(f"      {key} = {value},")
        lines.append("    },")
        lines.append("  },")
        lines.append("})")
    INPUT_LUA.write_text("\n".join(lines) + "\n")
    return run_ok("hyprctl", "reload")


def _touchscreen_on() -> bool:
    return not (Path.home() / ".local" / "state" / "omarchy" / "toggles"
                / "hypr" / "touchscreen-disabled-name").exists()


def _apply_layout(overlay: Adw.ToastOverlay, lay_row: Adw.EntryRow,
                  var_row: Adw.EntryRow) -> None:
    layout = lay_row.get_text().strip() or "us"
    variant = var_row.get_text().strip()
    try:
        _set_lua("kb_layout", f'"{layout}"')
        _set_lua("kb_variant", f'"{variant}"')
        toast(overlay, f"Layout → {layout or variant or 'us'}")
    except Exception as exc:  # noqa: BLE001
        toast(overlay, f"Failed: {exc}")


def _stepper(overlay: Adw.ToastOverlay, title: str, subtitle: str,
             get, set, step, lo: float, hi: float,
             fmt=None) -> Adw.ActionRow:
    """A −/value/+ row. Applies on every click with a reload."""
    fmt = fmt or (lambda v: str(v if float(v).is_integer() else v))
    row = Adw.ActionRow(title=title, subtitle=subtitle)
    box = Gtk.Box(spacing=6, valign="center")
    val_label = Gtk.Label(label=fmt(get()), width_request=64)
    down = Gtk.Button(label="−")
    up = Gtk.Button(label="+")

    def bump(_b, delta: float) -> None:
        try:
            cur = get()
            new = min(hi, max(lo, round(cur + delta, 2)))
            set(new)
            val_label.set_label(fmt(new))
        except Exception as exc:  # noqa: BLE001
            toast(overlay, f"Failed: {exc}")
    down.connect("clicked", bump, -step)
    up.connect("clicked", bump, step)
    box.append(down)
    box.append(val_label)
    box.append(up)
    row.add_suffix(box)
    return row


def build(overlay: Adw.ToastOverlay) -> Adw.PreferencesPage:
    page = Adw.PreferencesPage(title="Input Devices",
                               icon_name="input-keyboard-symbolic")
    loading = {"v": True}

    grp = Adw.PreferencesGroup(
        title="Touchpad",
        description="Changes apply instantly via Hyprland reload")
    page.add(grp)

    tp_row = Adw.SwitchRow(title="Touchpad enabled")
    tp_row.set_active(_touchpad_on())

    def on_tp(_r, _p) -> None:
        if loading["v"]:
            return
        state = "on" if tp_row.get_active() else "off"
        if run_ok("omarchy", "toggle", "touchpad", state):
            toast(overlay, f"Touchpad {state}")
        else:
            loading["v"] = True
            tp_row.set_active(not tp_row.get_active())
            loading["v"] = False
            toast(overlay, "Touchpad toggle failed")
    tp_row.connect("notify::active", on_tp)
    grp.add(tp_row)

    ns_row = Adw.SwitchRow(title="Natural scroll",
                           subtitle="Inverse, macOS-style scrolling")
    ns_row.set_active(_natural_scroll())

    def on_ns(_r, _p) -> None:
        if loading["v"]:
            return
        val = "true" if ns_row.get_active() else "false"
        try:
            _set_lua("natural_scroll", val)
            toast(overlay, f"Natural scroll {'on' if val == 'true' else 'off'}")
        except Exception as exc:  # noqa: BLE001
            loading["v"] = True
            ns_row.set_active(not ns_row.get_active())
            loading["v"] = False
            toast(overlay, f"Failed: {exc}")
    ns_row.connect("notify::active", on_ns)
    grp.add(ns_row)

    grp.add(_stepper(overlay, "Scroll speed",
                     "Touchpad scroll factor",
                     lambda: round(float(
                         _live("input:touchpad:scroll_factor", "0.4")
                         or 0.4), 1),
                     lambda v: _set_touchpad("scroll_factor", f"{v:.1f}"),
                     0.1, 0.1, 1.0, fmt=lambda v: f"{v:.1f}x"))

    tap_row = Adw.SwitchRow(title="Tap to click")
    tap_row.set_active(_live("input:touchpad:tap_to_click",
                             "true") == "true")

    def on_tap(_r, _p) -> None:
        if loading["v"]:
            return
        val = "true" if tap_row.get_active() else "false"
        try:
            _set_touchpad("tap_to_click", val)
            toast(overlay, f"Tap to click {'on' if val == 'true' else 'off'}")
        except Exception as exc:  # noqa: BLE001
            loading["v"] = True
            tap_row.set_active(not tap_row.get_active())
            loading["v"] = False
            toast(overlay, f"Failed: {exc}")
    tap_row.connect("notify::active", on_tap)
    grp.add(tap_row)

    ts_row = Adw.SwitchRow(title="Touchscreen",
                           subtitle="Touch input on the display")
    ts_row.set_active(_touchscreen_on())

    def on_ts(_r, _p) -> None:
        if loading["v"]:
            return
        state = "on" if ts_row.get_active() else "off"
        if run_ok("omarchy", "toggle", "touchscreen", state):
            toast(overlay, f"Touchscreen {state}")
        else:
            loading["v"] = True
            ts_row.set_active(not ts_row.get_active())
            loading["v"] = False
            toast(overlay, "Touchscreen toggle failed")
    ts_row.connect("notify::active", on_ts)
    grp.add(ts_row)

    kb = Adw.PreferencesGroup(title="Keyboard")
    page.add(kb)

    caps = Adw.ComboRow(title="CapsLock key",
                        subtitle="Compose gives accented characters (é, ü)",
                        model=Gtk.StringList.new([
                            "Standard CapsLock",
                            "Compose key (Omarchy default)",
                        ]))
    caps.set_selected(_caps_mode())

    def on_caps(_r, _p) -> None:
        if loading["v"]:
            return
        opts = COMPOSE_OPTS if caps.get_selected() == 1 else ""
        try:
            _set_lua("kb_options", f'"{opts}"')
            toast(overlay, "CapsLock updated (Shift+Shift clears "
                           "accidental Caps in Compose mode)")
        except Exception as exc:  # noqa: BLE001
            toast(overlay, f"Failed: {exc}")
    caps.connect("notify::selected", on_caps)
    kb.add(caps)

    lay_row = Adw.EntryRow(title="Keyboard layout",
                           text=_live("input:kb_layout", "us"))
    lay_row.connect("apply", lambda _r: _apply_layout(
        overlay, lay_row, var_row))
    kb.add(lay_row)

    var_row = Adw.EntryRow(title="Layout variant",
                           text=_live("input:kb_variant", ""))
    var_row.connect("apply", lambda _r: _apply_layout(
        overlay, lay_row, var_row))
    kb.add(var_row)

    kb.add(_stepper(overlay, "Key repeat rate",
                    "Keys per second while held",
                    lambda: int(_live("input:repeat_rate", "40") or 40),
                    lambda v: _set_lua("repeat_rate", str(v)), 5, 10, 60))
    kb.add(_stepper(overlay, "Key repeat delay",
                    "Milliseconds before repeat starts",
                    lambda: int(_live("input:repeat_delay", "250") or 250),
                    lambda v: _set_lua("repeat_delay", str(v)), 25, 100, 600))

    cur_accel = _live("input:accel_profile", "")
    accel = Adw.ComboRow(title="Mouse acceleration",
                         model=Gtk.StringList.new(["Adaptive", "Flat"]))
    accel.set_selected(1 if cur_accel == "flat" else 0)

    def on_accel(_r, _p) -> None:
        if loading["v"]:
            return
        val = "flat" if accel.get_selected() == 1 else "adaptive"
        try:
            _set_lua("accel_profile", f'"{val}"')
            toast(overlay, f"Acceleration → {val}")
        except Exception as exc:  # noqa: BLE001
            toast(overlay, f"Failed: {exc}")
    accel.connect("notify::selected", on_accel)
    kb.add(accel)

    kb.add(_stepper(overlay, "Pointer sensitivity",
                    "−1 (slow) to 1 (fast)",
                    lambda: round(float(
                        _live("input:sensitivity", "0") or 0), 1),
                    lambda v: _set_lua("sensitivity",
                                       f"{v:.1f}"), 0.1, -1.0, 1.0,
                    fmt=lambda v: f"{v:+.1f}"))

    gest = Adw.PreferencesGroup(title="Touchpad gestures")
    page.add(gest)
    gest.add(Adw.ActionRow(
        title="3 fingers",
        subtitle="Down: play/pause · Left/right: prev/next track"))
    gest.add(Adw.ActionRow(
        title="4 fingers",
        subtitle="Left/right: switch workspaces · Up/down: notifications"))
    gest.add(Adw.ActionRow(
        title="Edit gestures",
        subtitle="~/.config/hypr/input.lua (hl.gesture blocks)"))

    loading["v"] = False
    return page

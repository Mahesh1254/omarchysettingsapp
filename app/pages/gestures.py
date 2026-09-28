"""Gesture editor page: visual 3/4-finger mapper for ~/.config/hypr/input.lua.

Reads active hl.gesture blocks, lets you reassign each from a fixed
palette, add new ones, or delete them. Every write is backed up and
written atomically via mkstemp (random name, O_EXCL) + fsync +
os.replace, so a pre-planted symlink cannot redirect it; symlinked
input.lua/backup files are refused instead of followed. Validated with
`hyprctl reload` + `hyprctl configerrors`.
"""

import re
from pathlib import Path

from gi.repository import Adw, Gtk

from helpers import (atomic_write_text, run, run_ok, secure_backup,
                     secure_restore, toast)

INPUT_LUA = Path.home() / ".config" / "hypr" / "input.lua"

# action-key -> (label, lua-code for the action slot)
ACTIONS: dict[str, tuple[str, str]] = {
    "launcher": ("App launcher",
                 'function() hl.dispatch(hl.dsp.exec_cmd('
                 '"omarchy-menu toggle")) end'),
    "playpause": ("Play / pause",
                  'function() hl.dispatch(hl.dsp.exec_cmd('
                  '"omarchy-shell media playPause")) end'),
    "next": ("Next track",
             'function() hl.dispatch(hl.dsp.exec_cmd('
             '"omarchy-shell media next")) end'),
    "prev": ("Previous track",
             'function() hl.dispatch(hl.dsp.exec_cmd('
             '"omarchy-shell media previous")) end'),
    "volup": ("Volume up",
              'function() hl.dispatch(hl.dsp.exec_cmd('
              '"omarchy-audio-output-volume raise")) end'),
    "voldn": ("Volume down",
              'function() hl.dispatch(hl.dsp.exec_cmd('
              '"omarchy-audio-output-volume lower")) end'),
    "notif": ("Notification history",
              'function() hl.dispatch(hl.dsp.exec_cmd('
              '"omarchy-shell notifications showHistory")) end'),
    "dismiss": ("Dismiss notifications",
                'function() hl.dispatch(hl.dsp.exec_cmd('
                '"omarchy-shell notifications dismissAll")) end'),
    "scratch": ("Scratchpad",
                'function() hl.dispatch('
                'hl.dsp.workspace.toggle_special("scratchpad")) end'),
    "winnext": ("Next window",
                'function() hl.dispatch(hl.dsp.window.cycle_next()) end'),
    "winprev": ("Previous window",
                'function() hl.dispatch('
                'hl.dsp.window.cycle_next({ next = false })) end'),
    "workspace": ("Workspace swipe (smooth, needs horizontal)",
                  '"workspace"'),
}
ORDER = ["launcher", "playpause", "next", "prev", "volup", "voldn",
         "notif", "dismiss", "scratch", "winnext", "winprev", "workspace"]

# substring of the lua action -> action-key (first match wins)
REVERSE = [
    ("toggle_special(\"scratchpad\")", "scratch"),
    ("cycle_next({ next = false })", "winprev"),
    ("cycle_next()", "winnext"),
    ("media playPause", "playpause"),
    ("media next", "next"),
    ("media previous", "prev"),
    ("output-volume raise", "volup"),
    ("output-volume lower", "voldn"),
    ("notifications showHistory", "notif"),
    ("notifications dismissAll", "dismiss"),
    ("omarchy-menu toggle", "launcher"),
    ('"workspace"', "workspace"),
]

ARROWS = {"up": "↑", "down": "↓", "left": "←", "right": "→",
          "horizontal": "↔", "vertical": "↕"}

GESTURE_RE = re.compile(
    r"hl\.gesture\(\{\s*fingers\s*=\s*(\d+)\s*,\s*"
    r'direction\s*=\s*"([^"]+)"\s*,\s*action\s*=\s*(.+?)\s*\}\)\s*$')


def _read_lines() -> list[str]:
    return INPUT_LUA.read_text().splitlines()


def _parse_lines(lines: list[str]) -> list[dict]:
    out = []
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("--"):
            continue
        m = GESTURE_RE.search(ln)
        if not m:
            continue
        fingers, direction, action = m.group(1), m.group(2), m.group(3)
        out.append({"line": i, "fingers": fingers, "direction": direction,
                    "key": _action_key(action)})
    return out


def _parse() -> list[dict]:
    """Active (non-comment) gestures with their file line numbers."""
    return _parse_lines(_read_lines())


def _action_key(action: str) -> str:
    for sub, k in REVERSE:
        if sub in action:
            return k
    return "custom"


def _drop_conflicts(lines: list[str], fingers: str,
                    keep: str) -> list[str]:
    """Remove same-finger rows clashing with `keep`.

    `keep` is 'discrete' (drop smooth horizontal) or 'smooth'
    (drop discrete left/right).
    """
    out = []
    for ln in lines:
        s = ln.lstrip()
        if (s.startswith("hl.gesture")
                and f"fingers = {fingers}" in ln):
            if keep == "discrete" and 'direction = "horizontal"' in ln:
                continue
            if keep == "smooth" and ('direction = "left"' in ln
                                     or 'direction = "right"' in ln):
                continue
        out.append(ln)
    return out


def _write(lines: list[str], what: str, overlay) -> bool:
    """Backup, symlink-safe atomic-write, reload, validate."""
    backup = INPUT_LUA.parent / "input.lua.bak.settings-app"
    had_backup = False
    try:
        if INPUT_LUA.is_symlink() or backup.is_symlink():
            raise RuntimeError(
                "input.lua or its backup is a symlink, refusing to "
                "overwrite (edit the real file manually)")
        try:
            mode = INPUT_LUA.stat().st_mode & 0o777
        except OSError:
            mode = 0o644
        had_backup = secure_backup(INPUT_LUA, backup)
        atomic_write_text(INPUT_LUA, "\n".join(lines) + "\n", mode=mode)
        run("hyprctl", "reload")
        errs = run("hyprctl", "configerrors")
        if errs.strip():
            if had_backup:
                secure_restore(backup, INPUT_LUA)
                run("hyprctl", "reload")
            toast(overlay, f"Hyprland rejected it, restored: {errs[:120]}")
            return False
        toast(overlay, what)
        return True
    except Exception as exc:  # noqa: BLE001
        try:
            if had_backup:
                secure_restore(backup, INPUT_LUA)
                run_ok("hyprctl", "reload")
        except Exception:
            pass
        toast(overlay, f"Failed: {exc}")
        return False


def _make_line(fingers: str, direction: str, key: str) -> str:
    if key == "workspace":
        direction = "horizontal"
    code = ACTIONS[key][1]
    return (f'hl.gesture({{ fingers = {fingers}, direction = '
            f'"{direction}", action = {code} }})')


def build(overlay: Adw.ToastOverlay) -> Adw.PreferencesPage:
    page = Adw.PreferencesPage(title="Touchpad Gestures",
                               icon_name="input-touchpad-symbolic")
    loading = {"v": True}

    lst = Adw.PreferencesGroup(
        title="Current gestures",
        description="Discrete swipes fire once; the smooth swipe follows "
                    "your fingers. Discrete left/right and the smooth "
                    "horizontal swipe conflict per finger count — picking "
                    "one removes the other.")
    page.add(lst)

    shown: list = []  # rows we added (group has internal children too)

    def refresh() -> None:
        for r in shown:
            lst.remove(r)
        shown.clear()
        for g in _parse():
            r = _gesture_row(g)
            shown.append(r)
            lst.add(r)

    def _gesture_row(g: dict) -> Adw.ComboRow:
        arrow = ARROWS.get(g["direction"], g["direction"])
        row = Adw.ComboRow(
            title=f'{g["fingers"]} fingers {arrow} ({g["direction"]})',
            model=Gtk.StringList.new([ACTIONS[k][0] for k in ORDER]
                                     + (["Custom (edit file)"]
                                        if g["key"] == "custom" else [])))
        try:
            row.set_selected(ORDER.index(g["key"]))
        except ValueError:
            row.set_selected(len(ORDER))

        def on_change(_r, _p) -> None:
            if loading["v"]:
                return
            sel = row.get_selected()
            if sel >= len(ORDER):
                return
            new_key = ORDER[sel]
            if new_key == g["key"]:
                return
            direction = g["direction"]
            if new_key == "workspace":
                direction = "horizontal"  # smooth swipe needs it
            lines = _read_lines()
            if direction in ("left", "right"):
                lines = _drop_conflicts(lines, g["fingers"], "discrete")
            elif direction == "horizontal":
                lines = _drop_conflicts(lines, g["fingers"], "smooth")
            match = next((c for c in _parse_lines(lines)
                          if c["fingers"] == g["fingers"]
                          and c["direction"] == g["direction"]
                          and c["key"] == g["key"]), None)
            if match is None:
                toast(overlay, "Row moved — reopen the page")
                refresh()
                return
            lines[match["line"]] = _make_line(g["fingers"], direction,
                                              new_key)
            if _write(lines, f'Gesture → {ACTIONS[new_key][0]}', overlay):
                g["key"] = new_key
                g["direction"] = direction
                refresh()
        row.connect("notify::selected", on_change)

        if g["key"] != "custom":
            trash = Gtk.Button(icon_name="user-trash-symbolic",
                               valign="center",
                               tooltip_text="Delete this gesture")
            trash.connect("clicked", lambda _b: _delete(g))
            row.add_suffix(trash)
        return row

    def _delete(g: dict) -> None:
        lines = _read_lines()
        match = next((c for c in _parse_lines(lines)
                      if c["fingers"] == g["fingers"]
                      and c["direction"] == g["direction"]
                      and c["key"] == g["key"]), None)
        if match is None:
            toast(overlay, "Already gone — reopen the page")
            return
        del lines[match["line"]]
        if _write(lines, "Gesture deleted", overlay):
            refresh()

    add_grp = Adw.PreferencesGroup(title="Add gesture")
    page.add(add_grp)
    add_row = Adw.ActionRow(title="New swipe")
    f_combo = Gtk.DropDown(model=Gtk.StringList.new(["3 fingers",
                                                     "4 fingers"]),
                           valign="center")
    d_combo = Gtk.DropDown(model=Gtk.StringList.new(
        ["up", "down", "left", "right"]), valign="center")
    add_btn = Gtk.Button(label="Add", valign="center")

    def on_add(_b) -> None:
        fingers = "3" if f_combo.get_selected() == 0 else "4"
        direction = ["up", "down", "left", "right"][d_combo.get_selected()]
        lines = _read_lines()
        # adding discrete L/R drops the conflicting smooth swipe
        if direction in ("left", "right"):
            lines = [ln for ln in lines
                     if not ("hl.gesture" in ln
                             and f"fingers = {fingers}" in ln
                             and 'direction = "horizontal"' in ln
                             and not ln.lstrip().startswith("--"))]
        lines.append(_make_line(fingers, direction, "playpause"
                                if direction == "down" else "launcher"))
        if _write(lines, f"Added {fingers}-finger {direction} "
                         "(reassign it above)", overlay):
            refresh()
    add_btn.connect("clicked", on_add)
    box = Gtk.Box(spacing=6, valign="center")
    box.append(f_combo)
    box.append(d_combo)
    box.append(add_btn)
    add_row.add_suffix(box)
    add_grp.add(add_row)

    refresh()
    loading["v"] = False
    return page

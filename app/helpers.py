"""Shared helpers: run omarchy/shell commands, parse outputs, toast feedback."""

from __future__ import annotations

import json
import re
import subprocess
import threading
from typing import Callable

from gi.repository import GLib


def run(*args: str, timeout: int = 15) -> str:
    """Run a command, return stdout stripped. Raises on failure."""
    proc = subprocess.run(
        list(args), capture_output=True, text=True, timeout=timeout
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(err or f"{' '.join(args)} failed")
    return (proc.stdout or "").strip()


def run_ok(*args: str, timeout: int = 15) -> bool:
    """Run a command, return True on success (swallows output)."""
    try:
        subprocess.run(list(args), capture_output=True, timeout=timeout,
                       check=True)
        return True
    except Exception:
        return False


def launch(*args: str) -> bool:
    """Fire-and-forget a GUI app (no waiting, no output)."""
    try:
        subprocess.Popen(list(args), stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return True
    except Exception:
        return False


def run_async(args: list[str], done: Callable[[bool, str], None],
              timeout: int = 120) -> None:
    """Run a long command off the UI thread; done(ok, msg) on main loop."""
    def worker() -> None:
        try:
            out = run(*args, timeout=timeout)
            GLib.idle_add(done, True, out)
        except Exception as exc:  # noqa: BLE001
            GLib.idle_add(done, False, str(exc))
    threading.Thread(target=worker, daemon=True).start()


def run_async_raw(args: list[str], done: Callable[[int, str], None],
                  timeout: int = 120) -> None:
    """Like run_async but delivers (returncode, output); some commands
    report valid answers (e.g. 'up to date') with nonzero exit codes."""
    def worker() -> None:
        try:
            proc = subprocess.run(list(args), capture_output=True,
                                  text=True, timeout=timeout)
            out = (proc.stdout or proc.stderr or "").strip()
            GLib.idle_add(done, proc.returncode, out)
        except Exception as exc:  # noqa: BLE001
            GLib.idle_add(done, 127, str(exc))
    threading.Thread(target=worker, daemon=True).start()


def toast(overlay, message: str) -> None:
    """Show a toast on an Adw.ToastOverlay (import kept local)."""
    from gi.repository import Adw  # deferred: needs Gtk init order
    overlay.add_toast(Adw.Toast.new(message))


def parse_volume_percent(pactl_out: str) -> int:
    m = re.search(r"(\d+)%", pactl_out)
    return int(m.group(1)) if m else -1


def parse_json_flag(out: str, key: str, default: bool = False) -> bool:
    try:
        return bool(json.loads(out).get(key, default))
    except Exception:
        return default

"""Shared helpers: run omarchy/shell commands, parse outputs, toast feedback."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import threading
from pathlib import Path
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


def refuse_if_symlink(path: Path, label: str) -> None:
    """Refuse to overwrite a symlink target implicitly.

    `os.replace(tmp, dst)` replaces a destination symlink itself rather
    than following it, which would silently break dotfile-managed
    symlinks. Refusing is explicit and safe: the user edits the real
    file manually instead.
    """
    if path.is_symlink():
        raise RuntimeError(
            f"{label} is a symlink, refusing to overwrite "
            "(edit the real file manually)")


def atomic_write_text(target: Path, data: str, mode: int | None = None) -> None:
    """Write text to target atomically without symlink-following writes.

    Uses tempfile.mkstemp (O_CREAT|O_EXCL, random name, 0600 — see
    Stack Overflow "Symlink Exploits in Python" / "How to make file
    creation an atomic operation" and CPython tempfile.mkstemp using
    O_EXCL|O_NOFOLLOW) in the same directory, then fsync + os.replace.
    mkstemp's random name + O_EXCL closes the predictable-tmp symlink
    race (CWE-59/CWE-377); os.replace never follows a destination
    symlink, it replaces the link itself.
    """
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(parent), prefix=target.name + ".tmp.", suffix=".settings-app")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        if mode is not None:
            os.chmod(tmp_name, mode)
        os.replace(tmp_name, target)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def secure_backup(src: Path, backup: Path) -> bool:
    """Back up src to backup without following a backup symlink.

    Returns False when src does not exist (nothing to back up).
    Refuses when src itself is a symlink. If backup currently lexists
    as a symlink it is unlinked first (never followed); the copy itself
    goes through atomic_write_text, whose os.replace replaces rather
    than follows the destination.
    """
    if not src.exists() or src.is_symlink():
        if src.is_symlink():
            raise RuntimeError(
                f"{src} is a symlink, refusing to back up "
                "(edit the real file manually)")
        return False
    try:
        if backup.is_symlink() or backup.exists():
            # Unlink a pre-planted symlink instead of following it.
            # atomic_write_text would already replace-not-follow, but
            # explicit unlink keeps the intent obvious and auditable.
            if backup.is_symlink():
                backup.unlink()
    except OSError:
        pass
    data = src.read_text()
    try:
        mode = src.stat().st_mode & 0o777
    except OSError:
        mode = 0o644
    atomic_write_text(backup, data, mode=mode)
    return True


def secure_restore(backup: Path, target: Path) -> None:
    """Restore target from backup without following symlinks on write."""
    if backup.is_symlink():
        raise RuntimeError(f"{backup} is a symlink, refusing to restore")
    data = backup.read_text()
    atomic_write_text(target, data)


def parse_volume_percent(pactl_out: str) -> int:
    m = re.search(r"(\d+)%", pactl_out)
    return int(m.group(1)) if m else -1


def parse_json_flag(out: str, key: str, default: bool = False) -> bool:
    try:
        return bool(json.loads(out).get(key, default))
    except Exception:
        return default

#!/usr/bin/env python3
"""Omarchy Settings — a Windows-style settings app for Omarchy Linux.

v1 pages: Sound+Display, Input Devices, Network+Bluetooth, Personalization.
Every control runs a real omarchy/system command; nothing is decorative.
"""

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk  # noqa: E402

from pages import (apps, gestures, input_devices, keybindings, network,
                 notifications, personalization, power, sound_display,
                 system, updates)  # noqa: E402

SECTIONS = [
    ("sound", "Sound + Display", "audio-volume-high-symbolic",
     sound_display.build,
     "volume mute speaker brightness night light monitor scaling text"),
    ("power", "Power & Battery", "battery-good-symbolic",
     power.build,
     "battery power profile suspend sleep idle hibernate"),
    ("notifications", "Notifications", "notifications-symbolic",
     notifications.build,
     "notifications disturb dnd history alert ping"),
    ("input", "Input Devices", "input-keyboard-symbolic",
     input_devices.build,
     "keyboard mouse touchpad scroll capslock layout repeat sensitivity "
     "tap click touchscreen"),
    ("gestures", "Touchpad Gestures", "input-touchpad-symbolic",
     gestures.build,
     "gesture swipe fingers touchpad media play track workspace"),
    ("keys", "Keybindings", "input-keyboard-symbolic",
     keybindings.build,
     "keybindings shortcuts keys hotkeys"),
    ("network", "Network + Bluetooth", "network-wireless-symbolic",
     network.build,
     "wifi bluetooth network dns band speed tailscale wireless"),
    ("personal", "Personalization",
     "preferences-desktop-wallpaper-symbolic", personalization.build,
     "theme wallpaper background bar appearance font"),
    ("system", "System & Security", "emblem-system-symbolic",
     system.build,
     "system time timezone weather security fingerprint sudo about "
     "accessibility password ssh disk snapshot storage"),
    ("updates", "System Updates", "software-update-available-symbolic",
     updates.build,
     "update upgrade firmware packages"),
    ("apps", "Apps & Recovery", "application-x-executable-symbolic",
     apps.build,
     "apps defaults browser editor terminal webapp startup recovery "
     "reset factory restart"),
]


class SettingsWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title="Settings",
                         default_width=940, default_height=640)
        self.set_icon_name("preferences-system-symbolic")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(vbox)

        header = Adw.HeaderBar()
        title = Adw.WindowTitle(title="Settings",
                                subtitle="Omarchy system settings")
        header.set_title_widget(title)
        vbox.append(header)

        self.toast = Adw.ToastOverlay()
        vbox.append(self.toast)

        main = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True,
                       vexpand=True)
        self.toast.set_child(main)

        # Sidebar
        side_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.search = Gtk.SearchEntry(placeholder_text="Search settings…",
                                      margin_start=8, margin_end=8,
                                      margin_top=8, margin_bottom=4)
        side_box.append(self.search)
        side_scroll = Gtk.ScrolledWindow(hscrollbar_policy="never",
                                         width_request=220, vexpand=True)
        side_scroll.add_css_class("sidebar")
        self.sidebar = Gtk.ListBox(selection_mode="single",
                                   css_classes=["navigation-sidebar"])
        side_scroll.set_child(self.sidebar)
        side_box.append(side_scroll)
        main.append(side_box)

        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        main.append(sep)

        # Pages
        self.stack = Gtk.Stack(transition_type="crossfade", hexpand=True,
                               vexpand=True, margin_start=12, margin_end=12,
                               margin_top=12, margin_bottom=12)
        main.append(self.stack)

        self._rows: list = []
        self._builders: dict = {}
        for name, label, icon, builder, keywords in SECTIONS:
            try:
                page = builder(self.toast)
            except Exception as exc:  # noqa: BLE001 — one bad page
                print(f"settings: page {name} failed: {exc}")  # must not kill app
                continue
            self.stack.add_named(page, name)
            self._builders[name] = builder
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                          margin_start=12, margin_end=12, margin_top=10,
                          margin_bottom=10)
            box.append(Gtk.Image.new_from_icon_name(icon))
            box.append(Gtk.Label(label=label, xalign=0))
            row.set_child(box)
            row.set_name(name)
            self.sidebar.append(row)
            self._rows.append((row, f"{label} {keywords}".lower()))

        self.sidebar.connect("row-selected", self._on_select)
        self.search.connect("search-changed", self._on_search)
        first = self.sidebar.get_row_at_index(0)
        if first is not None:
            self.sidebar.select_row(first)

    def _on_search(self, _entry) -> None:
        q = self.search.get_text().strip().lower()
        first_visible = None
        for row, hay in self._rows:
            vis = not q or q in hay
            row.set_visible(vis)
            if vis and first_visible is None:
                first_visible = row
        if q and first_visible is not None:
            self.sidebar.select_row(first_visible)

    def _on_select(self, _box: Gtk.ListBox, row) -> None:
        if row is None:
            return
        name = row.get_name()
        # Rebuild the page on every open so switches always show live
        # state, even if something changed outside the app.
        builder = self._builders.get(name)
        if builder is not None:
            try:
                new_page = builder(self.toast)
            except Exception as exc:  # noqa: BLE001 — keep old page
                print(f"settings: rebuild {name} failed: {exc}")
                self.stack.set_visible_child_name(name)
                return
            old = self.stack.get_child_by_name(name)
            if old is not None:
                self.stack.remove(old)
            self.stack.add_named(new_page, name)
        self.stack.set_visible_child_name(name)


class SettingsApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id="org.omarchy.Settings",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self) -> None:
        win = self.props.active_window or SettingsWindow(self)
        win.present()


def main() -> None:
    app = SettingsApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()

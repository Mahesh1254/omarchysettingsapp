# Settings — a Windows-style settings app for Omarchy

Plugin ID: `io.github.mahesh1254.settings`

A searchable settings app with sidebar sections: Sound + Display, Power &
Battery, Notifications, Input Devices, Touchpad Gestures, Keybindings,
Network + Bluetooth, Personalization, System & Security, System Updates,
and Apps & Recovery. Every control runs a real `omarchy`/system command —
nothing is decorative.

The shell plugin itself is a thin overlay (`SettingsOverlay.qml`) that
launches the bundled Python/GTK app, so it behaves like a native
"open Settings" action.

## Dependencies

- Omarchy Linux (provides the `omarchy`, `omarchy-shell`, `hyprctl` commands)
- `python3` with PyGObject
- GTK4 + libadwaita (`gtk4`, `libadwaita`, `python-gobject` on Arch)
- Standard tools: `pactl`, `nmcli`, `bluetoothctl`, `timedatectl`

No downloads, no sudo, and no background services are used by the installer.
Some in-app actions (updates, firmware, snapshots, splash screen) open a
terminal because they legitimately need your password.

## Installation

```bash
git clone https://github.com/Mahesh1254/omarchysettingsapp.git
cd omarchysettingsapp
./install.sh
omarchy plugin add https://github.com/Mahesh1254/omarchysettingsapp.git
```

Then open Settings from your app launcher, with `omarchy-settings`,
or via the overlay:

```bash
omarchy-shell shell toggle io.github.mahesh1254.settings
```

## Removal

```bash
omarchy plugin remove io.github.mahesh1254.settings
rm -rf ~/.local/share/omarchy-settings
rm -f ~/.local/bin/omarchy-settings
rm -f ~/.local/share/applications/omarchy-settings.desktop
```

Your Hyprland configs are never touched by install/remove. Controls inside
the app that edit `~/.config/hypr/input.lua` (scroll, CapsLock, gestures)
work on your live files with backup + validation.

## Development

- App source lives in `app/` (`app.py` + `pages/`).
- After editing, re-run `./install.sh` and relaunch the app.
- Validate the manifest any time with:
  `omarchy plugin validate /path/to/omarchysettingsapp`

## License

MIT — see [LICENSE](LICENSE).

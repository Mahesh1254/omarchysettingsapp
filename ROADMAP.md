# Omarchy Settings — Windows-Parity Roadmap

App: `omarchy-settings` (`~/.local/share/omarchy-settings/`, launcher `~/.local/bin/omarchy-settings`).
Every control must run a real command — nothing decorative.
This file has a twin: `~/Desktop/Omarchy-Settings-Roadmap.md`.
**Rule: both copies are updated in the same turn as any feature lands or completes.**

Progress: 81 / 83 items complete. Only 2 remain, both externally blocked (see below).

---

## Phase 0 — Foundations (DONE, v1)

- [x] Sound: volume slider (exact %) — `pactl set-sink-volume`
- [x] Sound: mute switch — `omarchy-audio-output-volume mute-toggle`
- [x] Sound: output switcher — `omarchy-audio-output-switch`
- [x] Display: brightness slider — `omarchy-brightness-display N%`
- [x] Display: night light toggle — `omarchy toggle nightlight`
- [x] Input: touchpad on/off — `omarchy toggle touchpad`
- [x] Input: natural scroll switch — `~/.config/hypr/input.lua` + `hyprctl reload`
- [x] Input: CapsLock mode (Standard / Compose) — `kb_options` + `hyprctl reload`
- [x] Input: gesture readout (3/4-finger map) — static, from `input.lua`
- [x] Network: WiFi switch — `nmcli radio wifi`
- [x] Network: network picker button — `nm-connection-editor`
- [x] Bluetooth: power switch — `omarchy bluetooth power`
- [x] Network: DNS provider (DHCP/Cloudflare/Google) — `omarchy dns`
- [x] Personalization: theme picker — `omarchy theme list/set`
- [x] Personalization: wallpaper cycler — `omarchy theme bg next`
- [x] Personalization: bar position (top/bottom) — `omarchy bar position`

## Phase 1 — System essentials

### Display Pro
- [x] Monitor scaling (up/down/set) — `omarchy hyprland monitor scaling`
- [x] Text size (global scaling) — `omarchy display text size`
- [x] Internal laptop display on/off — `omarchy hyprland monitor internal`
- [x] Display mirroring toggle — `omarchy hyprland monitor internal mirror`
- [ ] External/DDC brightness (where supported) — `omarchy brightness display ddc`

### Sound Pro
- [x] Output device picker — `omarchy audio output set default`
- [x] Input device picker + mic mute — `omarchy audio input set default/mute`
- [x] Speaker tuning status — `omarchy audio tuning status` (info row; nothing ships for this laptop)

### Power & Battery
- [x] Power profile (saver/balanced/performance) — `omarchy powerprofiles set/list`
- [x] Suspend availability toggle — `omarchy toggle suspend`
- [x] Idle behavior (stay-awake/allow-idle) — `omarchy toggle idle`
- [x] Battery status readout — `omarchy battery status`
- [x] Hibernation setup — `omarchy hibernation setup` (terminal wizard)

### Notifications
- [x] Do-not-disturb toggle — `omarchy toggle notification-silencing` (state via `isDnd`)
- [x] Notification history viewer — `omarchy-shell notifications showHistory`
- [x] Send test notification — `omarchy notification send`

## Phase 2 — Input & Connectivity Pro

### Keyboard & Mouse
- [x] Keyboard layout/variant editor — `input.lua kb_layout/kb_variant` + reload
- [x] Key repeat rate/delay sliders — `input.lua repeat_rate/repeat_delay` + reload
- [x] Mouse sensitivity + accel profile — `input.lua sensitivity/accel_profile` + reload
- [x] Touchpad scroll-speed stepper — `input.lua scroll_factor` + reload
- [x] Tap-to-click toggle — `input.lua tap_to_click` + reload
- [x] Touchscreen toggle — `omarchy toggle touchscreen`

### Gesture editor (visual 3/4-finger mapper → `input.lua`)
- [x] List current 3/4-finger mappings (parsed from `hl.gesture` blocks)
- [x] Reassign actions from a fixed palette (volume/media/launcher/workspaces/notifications)
- [x] Add/remove a gesture row, validate with `hyprctl configerrors`

### Keybindings viewer
- [x] Searchable list — `omarchy menu keybindings --print`

### Bluetooth devices
- [x] Paired-device list + pair/connect/disconnect/forget — `omarchy bluetooth device` (+ `bluetoothctl` state)

### Network Pro
- [x] Connection status readout — `omarchy network status`
- [x] WiFi band select (auto/2.4/5/6) — `omarchy network band`
- [x] Speed test — `omarchy network speedtest` (async, result in row)
- [x] Share WiFi via QR — `omarchy network qr` (terminal display)
- [x] Tailscale status row (not installed → installer button)

### App-level: search
- [x] Settings search bar filtering sidebar sections (Windows signature feature)

## Phase 3 — Personalize, Locale, Access, Security

### Personalization Pro
- [x] Font picker — `omarchy font list/set`
- [x] Boot splash theme — `omarchy plymouth list/set/switcher`
- [x] Bar visibility toggle — `omarchy toggle bar`
- [x] Screensaver toggle + launch — `omarchy toggle screensaver`
- [x] Keyboard backlight — `omarchy brightness keyboard`

### Time & Language
- [x] Timezone picker — `omarchy menu timezone`
- [x] Weather location — `omarchy weather location`
- [x] Time sync repair — `omarchy update time`

### Accessibility
- [x] Global text size (shared with Display Pro) — `omarchy display text size`
- [ ] High-contrast/legibility theme shortcut — theme apply path
- [x] Honest gap list where Hyprland has no equivalent (document, don't fake)

### Security & About
- [x] Fingerprint setup wizard — `omarchy setup security fingerprint`
- [x] FIDO2 key setup — `omarchy setup security fido2`
- [x] SSH server setup — `omarchy setup security sshd`
- [x] Passwordless sudo toggle — `omarchy sudo passwordless`
- [x] About this PC — `omarchy launch about` (fastfetch) + `omarchy version`

## Phase 4 — System, Updates, Apps, Recovery

### System
- [x] Disk usage + speed test — `df` usage row, `omarchy disk speedtest`
- [x] Snapshots create/restore — `omarchy snapshot` (confirm dialog, terminal for sudo)
- [x] Crash-diagnosis entry — PID entry + terminal diagnosis (`omarchy agent crash <pid>`)

### Updates
- [x] Check for updates — `omarchy update available` (async)
- [x] Apply updates (with confirm) — `omarchy update -y` (terminal)
- [x] Firmware update — `omarchy update firmware` (terminal)
- [x] Post-update reboot prompt — `omarchy update restart` (terminal)

### Apps
- [x] Default browser/editor/terminal — `omarchy default browser/editor/terminal`
- [x] Web apps install/remove — terminal-guided (`omarchy webapp install/remove`)
- [x] Terminal apps install/remove — terminal-guided (`omarchy tui install/remove`)
- [x] Startup apps editor — opens `autostart.lua` in your editor

### Recovery (confirmations + auto-backup before everything)
- [x] Per-area config reset — hyprland/shell/tmux/hyprsunset (confirm, backed up first)
- [x] Shell/Hyprland restart buttons — `omarchy restart shell/hyprctl`
- [x] Factory reset — double-confirm dialogs, then terminal

## App-level (ongoing)
- [x] Re-read live state every time a page opens (pages rebuild on sidebar select)
- [x] Consistent error toasts on every failed command
- [x] Safe sudo/password flow — privileged ops run in a terminal (DNS applies inline with error toast)
- [x] Desktop entry + launcher kept working (`omarchy-settings`)

---

*Last updated: 2026-09-27 — Closed re-read gap (rebuild-on-select) and crash entry (PID row). Added native panel links (audio/BT/power). 81/83 — effectively complete.*

## Accepted gaps (not bugs)

- DDC brightness: no DDC monitor on this machine to build/test against.
- High-contrast shortcut: no Hyprland backend — documented in-app instead of faked.

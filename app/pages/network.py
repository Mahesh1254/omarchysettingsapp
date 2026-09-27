"""Network + Bluetooth page: WiFi, Bluetooth power, DNS provider."""

from gi.repository import Adw, Gtk

from helpers import launch, run, run_async, run_ok, toast

DNS_CHOICES = ["DHCP", "Cloudflare", "Google"]
BANDS = ["auto", "2.4", "5", "6"]


def _bt_devices() -> list[dict]:
    """Known bluetooth devices with paired/connected state."""
    out = []
    try:
        addrs = []
        for ln in run("bluetoothctl", "devices").splitlines():
            parts = ln.split(None, 2)
            if len(parts) >= 2 and parts[0] == "Device":
                addrs.append((parts[1], parts[2] if len(parts) > 2
                              else parts[1]))
    except Exception:
        return []
    for addr, name in addrs:
        paired = connected = False
        try:
            info = run("bluetoothctl", "info", addr)
            paired = "Paired: yes" in info
            connected = "Connected: yes" in info
        except Exception:
            pass
        out.append({"addr": addr, "name": name, "paired": paired,
                    "connected": connected})
    return out


def _net_status() -> str:
    try:
        return run("omarchy", "network", "status") or "Unknown"
    except Exception:
        return "Unknown"


def _band() -> int:
    try:
        for ln in run("omarchy", "network", "band").splitlines():
            if ln.startswith("selected"):
                sel = ln.split()[-1]
                return BANDS.index(sel) if sel in BANDS else 0
    except Exception:
        pass
    return 0


def _tailscale() -> str:
    try:
        out = run("tailscale", "status")
        return out.splitlines()[0] if out else "Connected"
    except Exception:
        return "Not installed"


def _bt_act(overlay, action: str, addr: str, refresh) -> None:
    try:
        run("omarchy", "bluetooth", "device", action, addr)
        toast(overlay, f"{action.title()} {addr}")
    except Exception as exc:  # noqa: BLE001
        toast(overlay, f"{action.title()} failed: {exc}")
    refresh()


def _wifi() -> bool:
    try:
        return run("nmcli", "radio", "wifi").lower() == "enabled"
    except Exception:
        return False


def _bt() -> bool:
    try:
        out = run("omarchy", "bluetooth", "power", "is-on")
        return out.lower() in ("on", "yes", "true", "enabled", "1")
    except Exception:
        return False


def _dns() -> int:
    try:
        cur = run("omarchy", "dns").strip()
        for i, name in enumerate(DNS_CHOICES):
            if name.lower() in cur.lower():
                return i
    except Exception:
        pass
    return 0


def build(overlay: Adw.ToastOverlay) -> Adw.PreferencesPage:
    page = Adw.PreferencesPage(title="Network + Bluetooth",
                               icon_name="network-wireless-symbolic")
    loading = {"v": True}

    net = Adw.PreferencesGroup(title="WiFi")
    page.add(net)

    wifi_row = Adw.SwitchRow(title="WiFi")
    wifi_row.set_active(_wifi())

    def on_wifi(_r, _p) -> None:
        if loading["v"]:
            return
        state = "on" if wifi_row.get_active() else "off"
        if run_ok("nmcli", "radio", "wifi", state):
            toast(overlay, f"WiFi {state}")
        else:
            loading["v"] = True
            wifi_row.set_active(not wifi_row.get_active())
            loading["v"] = False
            toast(overlay, "WiFi switch failed")
    wifi_row.connect("notify::active", on_wifi)
    net.add(wifi_row)

    conns = Adw.ActionRow(title="Networks",
                          subtitle="Pick a network to join")
    nc_btn = Gtk.Button(label="Choose", valign="center")

    def on_nc(_b) -> None:
        if launch("uwsm-app", "--", "nm-connection-editor"):
            toast(overlay, "Opening network editor…")
        else:
            toast(overlay, "Could not open network editor")
    nc_btn.connect("clicked", on_nc)
    conns.add_suffix(nc_btn)
    net.add(conns)

    bt = Adw.PreferencesGroup(title="Bluetooth")
    page.add(bt)

    bt_row = Adw.SwitchRow(title="Bluetooth")
    bt_row.set_active(_bt())

    def on_bt(_r, _p) -> None:
        if loading["v"]:
            return
        state = "on" if bt_row.get_active() else "off"
        if run_ok("omarchy", "bluetooth", "power", state):
            toast(overlay, f"Bluetooth {state}")
        else:
            loading["v"] = True
            bt_row.set_active(not bt_row.get_active())
            loading["v"] = False
            toast(overlay, "Bluetooth switch failed")
    bt_row.connect("notify::active", on_bt)
    bt.add(bt_row)

    bt_panel = Adw.ActionRow(title="Bluetooth panel",
                             subtitle="Native quick-settings popup")
    bt_panel_btn = Gtk.Button(label="Open", valign="center")
    bt_panel_btn.connect("clicked", lambda _b: toast(
        overlay, "Panel failed to open")
        if not run_ok("omarchy-shell", "shell", "toggle",
                      "omarchy.bluetooth") else None)
    bt_panel.add_suffix(bt_panel_btn)
    bt.add(bt_panel)

    dev_rows: list = []

    def refresh_bt() -> None:
        for r in dev_rows:
            bt.remove(r)
        dev_rows.clear()
        for d in _bt_devices():
            state = ("Connected" if d["connected"]
                     else "Paired" if d["paired"] else "Known")
            row = Adw.ActionRow(title=d["name"],
                                subtitle=f'{d["addr"]} · {state}')
            box = Gtk.Box(spacing=6, valign="center")
            if d["connected"]:
                b = Gtk.Button(label="Disconnect")
                b.connect("clicked", lambda _x, a=d["addr"]: _bt_act(
                    overlay, "disconnect", a, refresh_bt))
            else:
                b = Gtk.Button(label="Connect")
                b.connect("clicked", lambda _x, a=d["addr"]: _bt_act(
                    overlay, "connect", a, refresh_bt))
            f = Gtk.Button(label="Forget")
            f.connect("clicked", lambda _x, a=d["addr"]: _bt_act(
                overlay, "forget", a, refresh_bt))
            box.append(b)
            box.append(f)
            row.add_suffix(box)
            bt.add(row)
            dev_rows.append(row)
        if not dev_rows:
            row = Adw.ActionRow(title="No devices",
                                subtitle="Pair one to see it here")
            bt.add(row)
            dev_rows.append(row)

    ref_row = Adw.ActionRow(title="Known devices")
    ref_btn = Gtk.Button(label="Refresh", valign="center")
    ref_btn.connect("clicked", lambda _b: refresh_bt())
    ref_row.add_suffix(ref_btn)
    bt.add(ref_row)
    pair_row = Adw.ActionRow(title="Pair a new device",
                             subtitle="Opens bluetooth controls in a terminal")
    pair_btn = Gtk.Button(label="Pair", valign="center")
    pair_btn.connect("clicked", lambda _b: toast(
        overlay, "Opening bluetooth controls…"
        if launch("omarchy-launch-terminal", "bluetoothctl")
        else "Could not open bluetooth controls"))
    pair_row.add_suffix(pair_btn)
    bt.add(pair_row)
    refresh_bt()

    pro = Adw.PreferencesGroup(title="Connection")
    page.add(pro)

    st_row = Adw.ActionRow(title="Status", subtitle=_net_status())
    st_btn = Gtk.Button(label="Refresh", valign="center")
    st_btn.connect("clicked",
                   lambda _b: st_row.set_subtitle(_net_status()))
    st_row.add_suffix(st_btn)
    pro.add(st_row)

    band_row = Adw.ComboRow(title="WiFi band",
                            model=Gtk.StringList.new(BANDS))
    band_row.set_selected(_band())

    def on_band(_r, _p) -> None:
        if loading["v"]:
            return
        band = BANDS[band_row.get_selected()]
        try:
            run("omarchy", "network", "band", band)
            toast(overlay, f"WiFi band → {band}")
        except Exception as exc:  # noqa: BLE001
            toast(overlay, f"Band change failed: {exc}")
    band_row.connect("notify::selected", on_band)
    pro.add(band_row)

    sp_row = Adw.ActionRow(title="Speed test",
                           subtitle="Measure download or upload")
    sp_box = Gtk.Box(spacing=6, valign="center")
    sp_down = Gtk.Button(label="Down")
    sp_up = Gtk.Button(label="Up")

    def on_speed(_b, direction: str) -> None:
        sp_row.set_subtitle(f"Testing {direction}…")

        def done(ok: bool, msg: str) -> None:
            sp_row.set_subtitle(
                msg.strip().splitlines()[0] if ok and msg.strip()
                else "Speed test failed")
        run_async(["omarchy", "network", "speedtest", direction], done)
    sp_down.connect("clicked", on_speed, "down")
    sp_up.connect("clicked", on_speed, "up")
    sp_box.append(sp_down)
    sp_box.append(sp_up)
    sp_row.add_suffix(sp_box)
    pro.add(sp_row)

    qr_row = Adw.ActionRow(title="WiFi QR code",
                           subtitle="Show a scannable code for this network")
    qr_btn = Gtk.Button(label="Show", valign="center")
    qr_btn.connect("clicked", lambda _b: toast(
        overlay, "Opening QR code…"
        if launch("omarchy-launch-terminal", "omarchy", "network", "qr")
        else "Could not open QR code"))
    qr_row.add_suffix(qr_btn)
    pro.add(qr_row)

    ts_state = _tailscale()
    ts_row = Adw.ActionRow(title="Tailscale", subtitle=ts_state)
    if ts_state == "Not installed":
        ts_btn = Gtk.Button(label="Install", valign="center")
        ts_btn.connect("clicked", lambda _b: toast(
            overlay, "Opening installer…"
            if launch("omarchy-launch-terminal", "omarchy", "install",
                      "service", "tailscale")
            else "Could not open installer"))
        ts_row.add_suffix(ts_btn)
    pro.add(ts_row)

    dns = Adw.PreferencesGroup(title="DNS")
    page.add(dns)

    dns_row = Adw.ComboRow(title="DNS provider",
                           subtitle="May ask for your password",
                           model=Gtk.StringList.new(DNS_CHOICES))
    dns_row.set_selected(_dns())

    def on_dns(_r, _p) -> None:
        if loading["v"]:
            return
        choice = DNS_CHOICES[dns_row.get_selected()]
        try:
            run("omarchy", "dns", choice)
            toast(overlay, f"DNS → {choice}")
        except Exception as exc:  # noqa: BLE001
            toast(overlay, f"DNS change failed: {exc}")
    dns_row.connect("notify::selected", on_dns)
    dns.add(dns_row)

    loading["v"] = False
    return page

"""Keybindings viewer page: searchable stock + custom Hyprland binds."""

from gi.repository import Adw, Gtk

from helpers import run, toast


def _binds() -> list[tuple[str, str]]:
    try:
        rows = []
        for ln in run("omarchy", "menu", "keybindings",
                      "--print").splitlines():
            if "→" in ln:
                keys, desc = ln.split("→", 1)
                rows.append((keys.strip(), desc.strip()))
            elif ln.strip():
                rows.append(("", ln.strip()))
        return rows
    except Exception:
        return []


def build(overlay: Adw.ToastOverlay) -> Adw.PreferencesPage:
    page = Adw.PreferencesPage(title="Keybindings",
                               icon_name="input-keyboard-symbolic")
    loading = {"v": True}

    grp = Adw.PreferencesGroup(title="All keybindings")
    page.add(grp)

    search = Gtk.SearchEntry(placeholder_text="Search keybindings…",
                             hexpand=True)
    search_row = Adw.ActionRow()
    search_row.add_suffix(search)
    search_row.set_activatable_widget(search)
    grp.add(search_row)

    listbox = Gtk.ListBox(selection_mode="none")
    scroll = Gtk.ScrolledWindow(min_content_height=380, vexpand=True)
    scroll.set_child(listbox)
    wrap = Adw.ActionRow()
    wrap.add_suffix(scroll)
    grp.add(wrap)

    binds = _binds()
    if not binds:
        toast(overlay, "Could not load keybindings")

    def refill(query: str) -> None:
        while True:
            row = listbox.get_first_child()
            if row is None:
                break
            listbox.remove(row)
        q = query.lower()
        shown = 0
        for keys, desc in binds:
            if q and q not in keys.lower() and q not in desc.lower():
                continue
            r = Adw.ActionRow(title=desc or keys,
                              subtitle=keys if desc else None)
            listbox.append(r)
            shown += 1
            if shown >= 150:
                break

    search.connect("search-changed",
                   lambda _s: refill(search.get_text()))
    refill("")

    loading["v"] = False
    return page

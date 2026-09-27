import Quickshell
import Quickshell.Io
import QtQuick

// Launcher overlay for the Settings app.
//
// The Settings UI itself is a Python/GTK program bundled in app/ and
// installed on PATH by install.sh. This overlay is intentionally thin:
// opening it launches the app and dismisses itself, so the plugin
// behaves like a native "open Settings" action. Open it with:
//
//   omarchy-shell shell toggle io.github.mahesh1254.settings
//
// If the app is not installed, the overlay shows a hint instead.

Item {
  id: root

  property var shell: null
  property var manifest: null
  property string pluginId: (root.manifest && root.manifest.id)
                             || "io.github.mahesh1254.settings"

  function open(payloadJson) {
    Quickshell.execDetached(["omarchy-settings"]);
    dismiss();
  }

  function close() {
    dismiss();
  }

  function dismiss() {
    if (root.shell && typeof root.shell.hide === "function")
      root.shell.hide(root.pluginId);
  }

  function toggle() {
    root.open("{}");
  }
}

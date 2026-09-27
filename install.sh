#!/bin/bash
# Install the Settings app files (local copies only — no downloads, no sudo).
#
# The shell plugin itself is installed separately with:
#   omarchy plugin add https://github.com/Mahesh1254/omarchysettingsapp.git
#
# Run this from the repository root:  ./install.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$HOME/.local/share/omarchy-settings"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR"

cp "$REPO_DIR/app/app.py" "$REPO_DIR/app/helpers.py" "$APP_DIR/"
mkdir -p "$APP_DIR/pages"
cp "$REPO_DIR/app/pages/"*.py "$APP_DIR/pages/"
chmod +x "$APP_DIR/app.py"

cat >"$BIN_DIR/omarchy-settings" <<'EOF'
#!/bin/bash
# Launcher for Omarchy Settings.
exec python3 "$HOME/.local/share/omarchy-settings/app.py" "$@"
EOF
chmod +x "$BIN_DIR/omarchy-settings"

cat >"$DESKTOP_DIR/omarchy-settings.desktop" <<'EOF'
[Desktop Entry]
Name=Settings
Comment=Omarchy system settings
Exec=omarchy-settings
Icon=preferences-system-symbolic
Terminal=false
Type=Application
Categories=Settings;System;
Keywords=settings;preferences;system;
StartupNotify=true
EOF

echo "Installed. Launch with: omarchy-settings"
echo "Or open the plugin overlay: omarchy-shell shell toggle io.github.mahesh1254.settings"
echo "Make sure ~/.local/bin is on your PATH."

#!/usr/bin/env bash

set -euo pipefail

cat "$CONTAINER_WORKSPACE_FOLDER/.devcontainer/bin/set_shortcuts.sh" >> /home/$REMOTE_USER/.bashrc


BIN_DIR="/usr/local/sbin"
cp  "$CONTAINER_WORKSPACE_FOLDER/.devcontainer/bin/as_non_admin.sh" "$BIN_DIR"
cp  "$CONTAINER_WORKSPACE_FOLDER/.devcontainer/bin/shortcut_as_non_admin.sh" "$BIN_DIR"
cp  "$CONTAINER_WORKSPACE_FOLDER/.devcontainer/bin/claude_ide.sh" "$BIN_DIR"

chown root:root "$BIN_DIR/as_non_admin.sh"
chown root:root "$BIN_DIR/shortcut_as_non_admin.sh"
chown root:root "$BIN_DIR/claude_ide.sh"
chmod 0555 "$BIN_DIR/as_non_admin.sh"
chmod 0555 "$BIN_DIR/shortcut_as_non_admin.sh"
chmod 0555 "$BIN_DIR/claude_ide.sh"

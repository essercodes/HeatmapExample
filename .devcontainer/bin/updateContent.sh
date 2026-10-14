#!/usr/bin/env bash

set -euo pipefail

find "$CONTAINER_WORKSPACE_FOLDER" \
    -path "$CONTAINER_WORKSPACE_FOLDER/.git" -prune \
    -o -path "$CONTAINER_WORKSPACE_FOLDER/.devcontainer" -prune \
    -o -exec chown -h "$REMOTE_USER:project" {} +

chown -R root:root "$CONTAINER_WORKSPACE_FOLDER/.devcontainer"
chmod -R 0700 "$CONTAINER_WORKSPACE_FOLDER/.devcontainer"

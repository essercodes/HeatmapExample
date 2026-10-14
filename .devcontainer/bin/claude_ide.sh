#!/usr/bin/env bash

# Launch claude as the non-admin user from claudecode.nvim (terminal_cmd).
# The plugin writes its lock file 0600 under the nvim user's ~/.claude/ide,
# so copy this port's lock into the non-admin user's ~/.claude/ide and pass
# the IDE env vars through sudo. The copy is removed when claude exits.

set -euo pipefail

TARGET_USER=${AS_NON_ADMIN_USER:-nonAdmin}
ENV_FILE="/home/${REMOTE_USER}/claude.env"
SECRET_FILE="/home/${REMOTE_USER}/op_secret"
CLAUDE_BIN="/home/${TARGET_USER}/.local/bin/claude"
SRC_LOCK="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/ide/${CLAUDE_CODE_SSE_PORT:-}.lock"
DST_DIR="/home/${TARGET_USER}/.claude/ide"

dst=""
if [[ -n ${CLAUDE_CODE_SSE_PORT:-} && -r $SRC_LOCK ]]; then
    dst="${DST_DIR}/${CLAUDE_CODE_SSE_PORT}.lock"
    sudo -u "$TARGET_USER" -- bash -c 'umask 077; mkdir -p "$1"; cat > "$2"' \
        _ "$DST_DIR" "$dst" < "$SRC_LOCK"
    trap 'sudo -u "$TARGET_USER" -- rm -f "$dst"' EXIT
else
    printf 'claude_ide: no IDE lock copied (CLAUDE_CODE_SSE_PORT=%s, lock=%s)\n' \
        "${CLAUDE_CODE_SSE_PORT:-<unset>}" "$SRC_LOCK" >&2
fi

# The lock's pid is nvim's, owned by another user, so claude can't signal it
# to check liveness. Point it at the claude process itself: the bash below
# rewrites pid to its own $$ and then execs claude, keeping that pid.
# shellcheck disable=SC2016
launch='
    [[ -n $1 && -f $1 ]] && sed -i -E "s/(\"pid\"[[:space:]]*:[[:space:]]*)[0-9]+/\1$$/" "$1"
    shift
    exec "$@"
'

# Not exec'd so the EXIT trap still cleans up the copied lock file.
OP_SERVICE_ACCOUNT_TOKEN="$(<"$SECRET_FILE")" \
    op --account my.1password.com run --env-file="$ENV_FILE" --no-masking -- \
    as_non_admin.sh -e "$ENV_FILE" \
        -p CLAUDE_CODE_SSE_PORT,ENABLE_IDE_INTEGRATION,FORCE_CODE_TERMINAL,no_proxy,NO_PROXY \
        bash -c "$launch" _ "$dst" "$CLAUDE_BIN" "$@"

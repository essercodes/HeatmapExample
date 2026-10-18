AWS_ENV_FILE="/home/${REMOTE_USER}/aws.env"
cat <<EOF > "$AWS_ENV_FILE"
AWS_ACCESS_KEY_ID = "op://Devcontainer/AWS Access Key/access key id"
AWS_SECRET_ACCESS_KEY = "op://Devcontainer/AWS Access Key/secret access key"
AWS_REGION = "op://Devcontainer/AWS Access Key/region"
EOF

CLAUDE_ENV_FILE="/home/${REMOTE_USER}/claude.env"
cat <<EOF > "$CLAUDE_ENV_FILE"
CLAUDE_CODE_OAUTH_TOKEN = op://Devcontainer/CLAUDE_CODE_OAUTH_TOKEN/credential
EOF

OPENCODE_ENV_FILE="/home/${REMOTE_USER}/opencode.env"
cat <<EOF > "$OPENCODE_ENV_FILE"
OPENROUTER_API_KEY = op://Devcontainer/OPENROUTER_API_KEY/credential
EOF

shortcut_as_non_admin() { eval "$(command shortcut_as_non_admin.sh "$@")"; }

shortcut_as_non_admin -m -c claude -e "$CLAUDE_ENV_FILE" \
    -b "/home/nonAdmin/.local/bin/claude"
# nvim generates OPENCODE_SERVER_PASSWORD per session; keep it across sudo
shortcut_as_non_admin -m -c opencode -e "$OPENCODE_ENV_FILE" -p OPENCODE_SERVER_PASSWORD \
    -b "/home/nonAdmin/.opencode/bin/opencode"

shortcut_as_non_admin -m -c aws -e "$AWS_ENV_FILE"
shortcut_as_non_admin -m -c terraform -e "$AWS_ENV_FILE"

shortcut_as_non_admin -c pnpm
shortcut_as_non_admin -c npm
shortcut_as_non_admin -c python
shortcut_as_non_admin -c python3
shortcut_as_non_admin -c pip 
shortcut_as_non_admin -c pip3
shortcut_as_non_admin -c cargo


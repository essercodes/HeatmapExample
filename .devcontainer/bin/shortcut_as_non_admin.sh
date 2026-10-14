#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: op_env_run -c <cmd> [-b <bin>] [-e <env_file>] [-p <VAR,VAR,...>] [-m] [-- <args>...]

  -c <cmd>       name of the shell function to define
  -b <bin>       binary to run; defaults to <cmd>
  -e <env_file>  op env file to inject, and whose keys survive sudo
  -p <vars>      comma-separated variable names to also preserve across sudo
  -m             pass --no-masking to op run
  -h             show this help

  Anything after -- is baked into the generated function as fixed
  arguments, placed before the caller's own "$@".
EOF
}

end() {
    printf 'shortcut_as_non_admin: %s\n' "$1" >&2
}

main() {
    local cmd="" env_file="" no_mask="" bin="" preserve="" flag
    local OPTIND=1 OPTARG

    while getopts ':mc:b:e:p:h' flag; do
        case $flag in
            m) no_mask=1 ;;
            c) cmd="${OPTARG}" ;;
            b) bin="${OPTARG}" ;;
            e) env_file="${OPTARG}" ;;
            p) preserve="${OPTARG}" ;;
            h) usage >&2; return 0 ;;
            :) end "missing argument for -$OPTARG"; usage >&2; return 1 ;;
            *) end "unknown option -$OPTARG"; usage >&2; return 1 ;;
        esac
    done
    # getopts consumes a lone -- and stops; OPTIND now points at the
    # first passthrough arg.
    shift $((OPTIND - 1))

    if [[ -z $cmd ]]; then
        end 'no command name given (-c)'
        usage >&2
        return 1
    fi

    [[ -n $bin ]] || bin=$cmd

    local masking=""
    if [[ -n "$no_mask" ]]; then 
        masking="--no-masking"
    fi

    local secret_file="/home/${REMOTE_USER}/op_secret"

    local envs=""
    local op_prefix=""
    if [[ -n ${env_file} ]]; then
        op_prefix="OP_SERVICE_ACCOUNT_TOKEN=\$(cat ${secret_file@Q}) \
            op --account my.1password.com run --env-file=${env_file@Q} ${masking} --"

        envs="-e ${env_file}"
    fi

    if [[ -n ${preserve} ]]; then
        envs="${envs:+${envs} }-p ${preserve@Q}"
    fi

    # Fixed args from after --, frozen into the definition at generation
    # time. The guard keeps ${*@Q} from tripping set -u when $# is 0.
    local extra=""
    (($#)) && extra=" ${*@Q}"

    printf '%s\n' "
    ${cmd}() {
        ${op_prefix} as_non_admin.sh ${envs} ${bin@Q}${extra} \"\$@\"
    }
    "
}

main "$@"

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

load_credentials_file() {
    local file="$1"
    local key
    local value

    while IFS="=" read -r key value; do
        case "$key" in
            PORKBUN_SANDBOX_API_KEY | PORKBUN_SANDBOX_SECRET_KEY | API_KEY | SECRET_KEY)
                printf -v "$key" "%s" "$value"
                export "$key"
                ;;
        esac
    done <"$file"
}

credentials_file="${PORKBUN_SANDBOX_ENV_FILE:-.pbsb}"
if [[ -f "$credentials_file" ]]; then
    load_credentials_file "$credentials_file"
elif [[ -f "$HOME/.pbsb" ]]; then
    load_credentials_file "$HOME/.pbsb"
else
    echo "No sandbox credentials found. Copy .pbsb.example to .pbsb and add sandbox keys." >&2
    exit 1
fi

if [[ -z "${PORKBUN_SANDBOX_API_KEY:-}" && -n "${API_KEY:-}" ]]; then
    PORKBUN_SANDBOX_API_KEY="$API_KEY"
    export PORKBUN_SANDBOX_API_KEY
fi
if [[ -z "${PORKBUN_SANDBOX_SECRET_KEY:-}" && -n "${SECRET_KEY:-}" ]]; then
    PORKBUN_SANDBOX_SECRET_KEY="$SECRET_KEY"
    export PORKBUN_SANDBOX_SECRET_KEY
fi

case "${PORKBUN_SANDBOX_API_KEY:-}" in
    pk1_sb_*) ;;
    *)
        echo "Refusing to run without a pk1_sb_ Porkbun sandbox API key." >&2
        exit 1
        ;;
esac

case "${PORKBUN_SANDBOX_SECRET_KEY:-}" in
    sk1_sb_*) ;;
    *)
        echo "Refusing to run without an sk1_sb_ Porkbun sandbox secret key." >&2
        exit 1
        ;;
esac

uv sync --locked
PORKBUN_RUN_CONTRACT=1 PORKBUN_RUN_SANDBOX=1 \
    uv run --no-sync pytest tests/test_api_contract.py tests/test_api_sandbox.py -v --tb=short

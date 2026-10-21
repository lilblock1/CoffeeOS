#!/usr/bin/env bash
set -Eeuo pipefail
: "${COFFEEOS_GPG_PRIVATE_KEY:?COFFEEOS_GPG_PRIVATE_KEY is required}"
KEY_FILE="$(mktemp)"
trap 'rm -f "$KEY_FILE"' EXIT
printf '%s\n' "$COFFEEOS_GPG_PRIVATE_KEY" > "$KEY_FILE"
chmod 600 "$KEY_FILE"

if [[ -n ${COFFEEOS_GPG_PASSPHRASE:-} ]]; then
  gpg --batch --yes --pinentry-mode loopback     --passphrase "$COFFEEOS_GPG_PASSPHRASE" --import "$KEY_FILE"
else
  gpg --batch --yes --import "$KEY_FILE"
fi

KEY_ID="$(gpg --batch --with-colons --list-secret-keys | awk -F: '$1=="sec"{print $5; exit}')"
[[ -n "$KEY_ID" ]] || { echo 'No secret key imported.' >&2; exit 1; }
printf '%s\n' "$KEY_ID" > "$RUNNER_TEMP/coffeeos-signing-key-id"

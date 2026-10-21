#!/usr/bin/env bash
set -Eeuo pipefail
EXPECTED="${1:-}"
case "$EXPECTED" in ''|coffee) ;; *) echo 'Usage: kernel-smoke.sh [coffee]' >&2; exit 2;; esac
printf 'Running kernel: %s\n' "$(uname -r)"
[[ -r /proc/version && -r /proc/meminfo ]] || { echo 'Basic procfs missing' >&2; exit 3; }
if [[ -n $EXPECTED ]]; then
  [[ $(uname -r) == *-coffee ]] || { echo 'Booted kernel does not match CoffeeKernel' >&2; exit 4; }
fi
if command -v systemctl >/dev/null && [[ -d /run/systemd/system ]]; then
  systemctl is-system-running || true
fi
printf '\nKernel command line:\n'
cat /proc/cmdline
printf '\nInstalled package candidates:\n'
dpkg-query -W 'linux-image-*' 'linux-headers-*' 2>/dev/null | grep -E 'coffee|amd64' || true
printf '\nBasic OS smoke checks complete. This does NOT prove game performance, stability or GPU support.\n'

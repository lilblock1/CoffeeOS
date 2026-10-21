#!/usr/bin/env bash
# Check dependencies available in the host Debian environment.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
printf 'Coffee Desktop preflight on %s\n' "$(uname -sr)"
for app in labwc waybar fuzzel foot mako swaybg gtkgreet cage python3; do
  if command -v "$app" >/dev/null 2>&1; then
    printf '[present] %s\n' "$app"
  else
    printf '[missing] %s\n' "$app"
  fi
done
bash scripts/validate.sh
printf '\nNOTE: This validates source and installed command availability, not live graphics.\n'

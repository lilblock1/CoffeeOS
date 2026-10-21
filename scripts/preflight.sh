#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo 'CoffeeOS builder preflight'
if [[ -r /etc/os-release ]]; then . /etc/os-release; echo "Host: ${PRETTY_NAME:-unknown} (${VERSION_CODENAME:-unknown})"; fi
echo "Architecture: $(uname -m)"
[[ $(uname -m) == x86_64 ]] || echo 'WARNING: expected an amd64/x86_64 builder.'
[[ ${VERSION_CODENAME:-} == trixie ]] || echo 'WARNING: recommended native Debian 13 Trixie builder.'
for c in lb debootstrap mksquashfs xorriso rsync sha256sum qemu-system-x86_64; do
  if command -v "$c" >/dev/null 2>&1; then echo "OK: $c"; else echo "MISSING: $c"; fi
done
if command -v getent >/dev/null && getent ahostsv4 deb.debian.org >/dev/null 2>&1; then
  echo 'DNS: deb.debian.org resolves (downloads not yet tested)'
else echo 'DNS: deb.debian.org does not resolve; online builds will fail'; fi
echo 'Required disk headroom: approximately 25 GB free (more for builds/caches)'
df -h "$ROOT" | tail -n 1

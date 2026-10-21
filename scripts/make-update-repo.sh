#!/usr/bin/env bash
# Publish the currently staged CoffeeOS .deb files as a standard APT repository.
# Remote repositories MUST be signed. Use --unsigned only for disposable local testing.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/dist/update-repo"
SUITE=stable
KEY=''
UNSIGNED=0
usage(){ echo 'Usage: make-update-repo.sh [--output DIR] [--suite stable] [--key GPG_KEY_ID] [--unsigned]' >&2; }
while (( $# )); do
 case "$1" in
   --output) OUT=${2:?}; shift 2;;
   --suite) SUITE=${2:?}; shift 2;;
   --key) KEY=${2:?}; shift 2;;
   --unsigned) UNSIGNED=1; shift;;
   -h|--help) usage; exit 0;;
   *) usage; exit 2;;
 esac
done
[[ $SUITE =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { echo 'Invalid suite.' >&2; exit 2; }
for x in dpkg-scanpackages apt-ftparchive gzip; do command -v "$x" >/dev/null || { echo "Missing $x (install dpkg-dev/apt-utils)." >&2; exit 3; }; done
if (( ! UNSIGNED )); then
 command -v gpg >/dev/null || { echo 'Missing gpg.' >&2; exit 3; }
 [[ -n $KEY ]] || { echo 'Signed update repositories require --key GPG_KEY_ID.' >&2; exit 4; }
fi
bash "$ROOT/scripts/build-coffeeos-system-package.sh"
rm -rf "$OUT"; mkdir -p "$OUT/pool/main" "$OUT/dists/$SUITE/main/binary-amd64"
shopt -s nullglob
pkgs=("$ROOT/live-build/config/packages.chroot"/*.deb)
(( ${#pkgs[@]} )) || { echo 'No staged CoffeeOS packages. Build CoffeeKernel/optimized packages first.' >&2; exit 5; }
cp -f "${pkgs[@]}" "$OUT/pool/main/"
# Include CoffeeKernel headers as an optional developer package if they were built.
headers=("$ROOT/dist/kernels/coffee"/linux-headers-*-coffee_*.deb)
(( ${#headers[@]} == 0 )) || cp -f "${headers[@]}" "$OUT/pool/main/"
shopt -u nullglob
(
 cd "$OUT"
 dpkg-scanpackages --multiversion pool /dev/null > "dists/$SUITE/main/binary-amd64/Packages"
 gzip -9c "dists/$SUITE/main/binary-amd64/Packages" > "dists/$SUITE/main/binary-amd64/Packages.gz"
 apt-ftparchive -o APT::FTPArchive::Release::Origin=CoffeeOS \
   -o APT::FTPArchive::Release::Label=CoffeeOS \
   -o APT::FTPArchive::Release::Suite="$SUITE" \
   -o APT::FTPArchive::Release::Codename="$SUITE" \
   -o APT::FTPArchive::Release::Architectures='amd64 all' \
   -o APT::FTPArchive::Release::Components=main \
   release "dists/$SUITE" > "dists/$SUITE/Release"
 if (( UNSIGNED )); then
   echo 'WARNING: repository is UNSIGNED and is only suitable for isolated local testing.' >&2
 else
   gpg --batch --yes --default-key "$KEY" --clearsign -o "dists/$SUITE/InRelease" "dists/$SUITE/Release"
   gpg --batch --yes --default-key "$KEY" -abs -o "dists/$SUITE/Release.gpg" "dists/$SUITE/Release"
 fi
)
printf 'CoffeeOS update repository ready: %s\n' "$OUT"
printf 'Host this directory over HTTPS, export the PUBLIC key, then configure clients with:\n'
printf '  sudo coffee-update set-feed https://YOUR-HOST/coffeeos %s /path/to/public-key.gpg\n' "$SUITE"

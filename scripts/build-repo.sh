#!/usr/bin/env bash
set -Eeuo pipefail

CHANNEL="${1:?channel required}"
INPUT="${2:?input directory required}"
OUTPUT="${3:?output directory required}"

case "$CHANNEL" in
  dev|beta|stable) ;;
  *) echo "Invalid channel" >&2; exit 2 ;;
esac

command -v dpkg-scanpackages >/dev/null
command -v apt-ftparchive >/dev/null
command -v gpg >/dev/null
command -v sha256sum >/dev/null

shopt -s nullglob
debs=("$INPUT"/*.deb)
(("${#debs[@]}" > 0)) || { echo "No .deb packages" >&2; exit 1; }

mkdir -p "$OUTPUT/pool/$CHANNEL" "$OUTPUT/dists/$CHANNEL/main/binary-amd64"

for f in "${debs[@]}"; do
  dpkg-deb --info "$f" >/dev/null
  cp "$f" "$OUTPUT/pool/$CHANNEL/"
done

gpg_common=(
  --batch
  --yes
  --pinentry-mode loopback
  --passphrase-fd 3
)

if [[ -n "${COFFEEOS_GPG_KEY_ID:-}" ]]; then
  gpg_common+=(--local-user "$COFFEEOS_GPG_KEY_ID")
fi

passphrase="${COFFEEOS_GPG_PASSPHRASE:-}"

(
  cd "$OUTPUT"

  # Sign every update package individually for manual/offline verification.
  for pkg in "pool/$CHANNEL"/*.deb; do
    gpg "${gpg_common[@]}" --armor --detach-sign \
      -o "$pkg.asc" "$pkg" 3<<<"$passphrase"
  done

  # Publish and sign a deterministic checksum list for all channel packages.
  (
    cd "pool/$CHANNEL"
    sha256sum -- *.deb | LC_ALL=C sort -k2 > SHA256SUMS
    gpg "${gpg_common[@]}" --armor --detach-sign \
      -o SHA256SUMS.asc SHA256SUMS 3<<<"$passphrase"
  )

  # Build the standard APT package index.
  dpkg-scanpackages --multiversion "pool/$CHANNEL" /dev/null \
    > "dists/$CHANNEL/main/binary-amd64/Packages"
  gzip -n -9 -c "dists/$CHANNEL/main/binary-amd64/Packages" \
    > "dists/$CHANNEL/main/binary-amd64/Packages.gz"

  cat > "dists/$CHANNEL/apt.conf" <<CONF
APT::FTPArchive::Release {
  Origin "CoffeeOS";
  Label "CoffeeOS";
  Suite "$CHANNEL";
  Codename "$CHANNEL";
  Architectures "amd64 all";
  Components "main";
  Description "CoffeeOS $CHANNEL update channel";
};
CONF

  apt-ftparchive -c "dists/$CHANNEL/apt.conf" release "dists/$CHANNEL" \
    > "dists/$CHANNEL/Release"
  rm "dists/$CHANNEL/apt.conf"

  # These are the signatures APT itself trusts.
  gpg "${gpg_common[@]}" --armor --detach-sign \
    -o "dists/$CHANNEL/Release.gpg" "dists/$CHANNEL/Release" 3<<<"$passphrase"

  gpg "${gpg_common[@]}" --clearsign \
    -o "dists/$CHANNEL/InRelease" "dists/$CHANNEL/Release" 3<<<"$passphrase"
)

echo "Signed $CHANNEL repository generated"

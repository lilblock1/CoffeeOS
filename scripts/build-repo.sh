#!/usr/bin/env bash
set -Eeuo pipefail
CHANNEL="${1:?channel required}"
INPUT="${2:?input directory required}"
OUTPUT="${3:?output directory required}"
case "$CHANNEL" in dev|beta|stable) ;; *) echo "Invalid channel" >&2; exit 2;; esac
command -v dpkg-scanpackages >/dev/null
command -v apt-ftparchive >/dev/null
command -v gpg >/dev/null
shopt -s nullglob
debs=("$INPUT"/*.deb)
(("${#debs[@]}" > 0)) || { echo "No .deb packages" >&2; exit 1; }
mkdir -p "$OUTPUT/pool/$CHANNEL" "$OUTPUT/dists/$CHANNEL/main/binary-amd64"
for f in "${debs[@]}"; do
  dpkg-deb --info "$f" >/dev/null
  cp "$f" "$OUTPUT/pool/$CHANNEL/"
done
(
  cd "$OUTPUT"
  dpkg-scanpackages --multiversion "pool/$CHANNEL" /dev/null > "dists/$CHANNEL/main/binary-amd64/Packages"
  gzip -n -9 -c "dists/$CHANNEL/main/binary-amd64/Packages" > "dists/$CHANNEL/main/binary-amd64/Packages.gz"
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
  apt-ftparchive -c "dists/$CHANNEL/apt.conf" release "dists/$CHANNEL" > "dists/$CHANNEL/Release"
  rm "dists/$CHANNEL/apt.conf"
  gpg --batch --yes --pinentry-mode loopback \
    --passphrase-fd 3 -abs -o "dists/$CHANNEL/Release.gpg" "dists/$CHANNEL/Release" 3<<<"${COFFEEOS_GPG_PASSPHRASE:-}"
  gpg --batch --yes --pinentry-mode loopback \
    --passphrase-fd 3 --clearsign -o "dists/$CHANNEL/InRelease" "dists/$CHANNEL/Release" 3<<<"${COFFEEOS_GPG_PASSPHRASE:-}"
)
echo "Signed $CHANNEL repository generated"

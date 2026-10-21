# CoffeeOS optimized package pipeline

CoffeeOS keeps Debian binary compatibility and broad x86-64 CPU support. It does **not** use `-march=native` or an x86-64-v3 baseline in the general ISO, because those would make one image fail on older 64-bit CPUs.

`bash scripts/build-optimized-packages.sh --mode core` rebuilds a curated set of latency-sensitive desktop/gaming packages from the exact Debian 13 source packages with Debian hardening retained and LTO enabled. Leaf applications additionally get `-O3`. The Debian version is suffixed with `+coffee1`, so the rebuilt package is selected over the same Debian base version while a later Debian security revision can still supersede it.

`--mode deep` also attempts larger graphics/audio/input components such as Mesa, PipeWire and libinput. Deep builds are intentionally optional: they consume much more time and can fail when an upstream package is incompatible with LTO. A failed optimized rebuild is recorded and CoffeeOS falls back to the official Debian binary package instead of producing a broken ISO.

The script writes its audit report to `dist/optimized/STATUS.tsv` and copies only approved runtime `.deb` packages into `live-build/config/packages.chroot/`. No debug or development packages are injected into the live image.

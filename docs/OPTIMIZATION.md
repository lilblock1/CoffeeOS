# CoffeeOS 0.6 optimization architecture

CoffeeOS uses one generic x86-64 CoffeeKernel and runtime profiles. It deliberately does **not** use `-march=native`, CPU-vendor-only binaries, disabled security mitigations, or blanket O3 on the whole Debian archive. Those approaches would make a distributable OS fragile or incompatible.

## Build modes

- **Stock**: official Debian kernel/packages only.
- **Core**: builds CoffeeKernel and rebuilds a curated set of compositor/UI/gaming components with Debian hardening plus LTO; O3 is limited to selected leaf applications.
- **Deep**: Core plus graphics/audio/input packages such as Mesa, PipeWire, libinput, libdrm and Xwayland. This is the mandatory Windows-builder mode and can take hours; the Windows GUI no longer exposes Stock/Core choices. A package source/build failure falls back to Debian's signed Stable binary; CoffeeKernel failure is fatal in optimized modes.

Ultra Fast Deep also uses a persistent live-build package-download cache, zstd level 1 for the live SquashFS, RAM-aware parallelism up to 24 jobs, cold-cache overlap of CoffeeKernel with optimized package builds, and a second bounded worker pool that compiles independent Debian source packages concurrently. Repeated source validation is content-hash cached, and ISO payload verification reuses one SquashFS extraction across parallel checks. Debian repository indices are not cached persistently, so update discovery remains fresh.

The source rebuild script creates `+coffee1` Debian package versions, filters produced `.deb` files through an approved runtime-package allowlist, and stages only those runtime packages into live-build. An audit report is installed at `/usr/share/coffeeos/optimized-packages.tsv`.

## Kernel

CoffeeKernel enables full preemption with dynamic-preemption support, 1000 Hz timers, high-resolution timers, scheduler autogrouping, AMD/Intel P-state, BFQ/mq-deadline, zram compression backends and THP madvise defaults while removing scheduler debug instrumentation. Debian's regular `linux-image-amd64` stays installed as a recovery fallback. There are not two CoffeeKernel variants.

## Runtime/resource policy

The image uses systemd-zram-generator (half RAM, capped at 4 GiB), conservative desktop sysctls, per-device I/O-scheduler selection, bounded compressed journald storage, and existing CoffeeOS performance profiles. Security services, networking and hardware support are not disabled just to improve benchmark-looking idle numbers.

## Installer choices

There is one CoffeeOS ISO. Calamares offers optional Steam/Proton libraries, Wine/DXVK, Lutris/Winetricks and Gamescope. The chooser is intentionally separated from Debian's normal live-media package-removal job: CoffeeOS installs selected optional software with its own Calamares Python job after `sources-final`, when the installed target has normal Debian/CoffeeOS network repositories again. These packages are fetched only when selected and Internet is available. Lutris is never preinstalled merely because the ISO supports it.

## Verification status

Static/unit tests validate the recipes and safety invariants. Actual source compilation, final ISO construction, QEMU boot, hardware compatibility and gaming benchmarks must run in the native Debian builder and on representative physical hardware. CoffeeOS must not claim a performance gain until A/B measurements support it.

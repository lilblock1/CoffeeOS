# CoffeeOS Adaptive Performance Engine — 0.10.0-dev

CoffeeOS 0.10.0 adds a hardware-aware, reversible performance layer. The goal is
consistent responsiveness and gaming frametimes without unsafe overclocking,
realtime scheduling, core-parking hacks, or disabled CPU security mitigations.

## Components

- `coffee-hardware-info`: reports CPU topology, x86-64 feature level, RAM, GPU,
  storage scheduler, power state and sched_ext availability.
- `coffee-performance-daemon`: watches the explicit Coffee Gaming Mode marker and
  Steam/Proton processes. While a game is active it requests the CoffeeKernel
  Performance profile and the gaming memory policy, then restores the previous
  profile when gaming ends.
- `coffee-memory-tune`: RAM-size-aware conservative VM settings. Low-memory
  systems get a different policy from 16/32+ GiB systems.
- `coffee-scheduler`: safe controller for optional sched_ext schedulers. The
  kernel exposes sched_ext but CoffeeOS does not force an experimental scheduler.
- `coffee-benchmark`: small local CPU/memory/disk comparison benchmark. It is not
  an FPS benchmark and does not claim gaming gains.
- `coffee-autotune`: recommends a CoffeeKernel profile from power/RAM/workload.
- `Coffee Gaming Session`: a second Wayland login session that prefers
  Gamescope+Steam and otherwise uses a reduced Coffee Desktop autostart.

## Per-game controls

Steam's `SteamAppId`/`SteamGameId` is detected automatically by
`coffee-gaming-mode`. Example:

```bash
coffee-gaming-preferences game-set 1091500 hud on
coffee-gaming-preferences game-set 1091500 gamescope on
```

When launched through Coffee Gaming Mode, the game is also placed in a transient
systemd user scope with high CPU and I/O weights. This is normal cgroup weighting,
not realtime scheduling.

## sched_ext

CoffeeKernel enables the kernel sched_ext/BPF prerequisites. `coffee-scheduler`
can start a supported scheduler only if that scheduler binary is separately
installed. No sched_ext scheduler is auto-loaded by default because the sched_ext
userspace ABI can change between kernel versions.

## Architecture-aware binaries

`coffee-hardware-info` reports x86-64-v1/v2/v3/v4 capability. CoffeeOS still
ships a broadly compatible baseline. The feature level is intended for the signed
CoffeeOS package repository to select optional prebuilt optimized variants later;
CoffeeOS does not use `-march=native` for the universal ISO.

# Phase 5 — Coffee Control Center

**Version:** 0.10.0-dev. **Base:** Debian 13 Trixie amd64.

## Implemented in source

- GTK3 Coffee Control Center with Overview, Performance, Gaming, Appearance,
  Software & Drivers, and Updates pages.
- Polkit-backed CoffeeKernel profile apply/restore; no fake unprivileged toggle.
- Per-user JSON gaming defaults for MangoHud/Gamescope, plus CLI overrides.
- Optional-software management remains on the same ISO: Calamares checkboxes at
  install time and explicit post-install actions in Control Center.
- Explicit Debian NVIDIA driver installation with live-session blocking.
- Allow-listed stable-update backend pinned to the existing Debian Trixie setup.
- Waybar gear, desktop launcher and Super+C integration.
- Phase-5 SquashFS verification so an ISO cannot pass verification if the Control
  Center/backend payload is missing.

## Verified in this development environment

- Python AST / shell syntax validation.
- Unit tests for Control Center wiring and security properties.
- Behavioral tests for gaming preference JSON creation, reset and permissions.
- Existing kernel, gaming, desktop, optimization and builder tests.

## Not claimed/tested here

- Successful polkit authentication inside the freshly built live/installed image.
- Real apt upgrade or package installation through the graphical frontend.
- Real CPU frequency changes on physical hardware.
- NVIDIA driver DKMS build or reboot on a physical NVIDIA system.
- Visual appearance on every display scale / compositor / VM GPU.

Those remain runtime tests for the ISO/installed system. Source tests are not a
substitute for booting the final image.

# Phase 3 — Coffee Desktop build and test results

**Version:** 0.3.1-dev (source-only, not an ISO release)

## Implemented

- Maintained Phase 1 live-build recipe and Phase 2 single-kernel project.
- Built Wayland session launcher, labwc root menu/keybindings, and window theme.
- Configured Waybar status panel, Fuzzel, Foot, Mako, desktop background.
- Replaced text login configuration with GTK-based greetd/cage login configuration.
- Built original per-user `coffee-appearance` configuration tool with Espresso
  and Latte palettes and optional reduced visual effects.
- Built GTK3 quick-settings/power-menu utility source and desktop entries.
- Added screenshot helper and developer test coverage.

## Tested in this environment

- Python import-independent syntax compilation for GUI files.
- Valid XML for labwc (config and menu) and valid JSON for Waybar.
- greetd TOML config, related package manifests and launcher references.
- Real isolated filesystem tests of theme switching, effects on/off,
  preservation of existing user keybinds, invalid-option rejection and reset.
- Previous Phase 1/Phase 2 unit and simulated-kernel tests repeated.

No ISO or real compositor was booted here; Debian mirror network, live-build,
QEMU and graphical seat/session services are not available in the build runtime.
No real idle RAM, CPU, login speed, gaming performance or GPU compatibility
measurements are available. No screenshot is represented as proof of a running
system.

## Additional integration work still needed

1. Install and boot the live ISO on a networked Debian 13 VM builder.
2. Confirm the greetd user has seat access and gtkgreet accepts logins.
3. Verify every GTK3 component on actual Wayland and all config syntaxes
   against the exact Debian Trixie binary package versions.
4. Test audio, Bluetooth, Wi-Fi, NVIDIA/AMD/Intel and multiple monitor modes.
5. Compare cold login/idle memory to a plain Debian installation.
6. Ensure the installed Calamares-based system enables `greetd` and carries
   over the live desktop config without overwriting existing user data.
7. Implement true automatic gaming-specific visual toggles during Phase 4.

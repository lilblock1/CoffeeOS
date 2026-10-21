# Coffee Desktop — Phase 3

Coffee Desktop is a modular labwc/Wayland desktop on Debian 13 Trixie. It is a
real configuration and utility implementation; it has **not yet been boot-tested**
on the release ISO or profiled on real GPUs.

## Components

| Component | Debian package / utility | Role |
|---|---|---|
| Window compositor | `labwc` | Stacking Wayland compositor, corner radius, optional shadows |
| Bar | `waybar` | Taskbar, resources, network, clock, power controls |
| Launcher | `fuzzel` | Native lightweight app launcher |
| Terminal | `foot` | Wayland terminal |
| Notifications | `mako-notifier` | Notification stack |
| Wallpaper | `swaybg` | Static wallpaper, exits only when session closes |
| Graphical login | `greetd` + `gtkgreet` + `cage` | PAM-backed password greeter on Wayland |
| GUI utility | `coffee-quick-settings` + GTK3 | Theme, effects, sound, network and saved profile preference |
| Power GUI | `coffee-power-menu` + GTK3 | Confirm logout, restart, shutdown |
| Screenshot | `grim` + `slurp` | Full-screen and optional selection capture |

Waybar is a **themed upstream panel** and Fuzzel is a **themed upstream launcher**,
not separately compiled CoffeeOS panel/launcher applications. This approach
reduces software to maintain.

## Keyboard shortcuts

- `Super + Space` / `Super + D`: launcher
- `Super + Return`: terminal
- `Super + E`: file manager
- `Super + S`: quick settings
- `Super + P`: power menu
- `Super + Q`: close focused window
- `Super + Shift + E`: exit current desktop (logout)
- `Print`: full-screen screenshot under `~/Pictures/`
- `Alt + Tab`: window switcher (labwc defaults)
- Multimedia volume/brightness keys where supported by the keyboard and hardware

Right-click the wallpaper for the Coffee Desktop menu.

## Appearance

```bash
coffee-appearance show
coffee-appearance theme espresso-noir
coffee-appearance theme latte-cream
coffee-appearance theme caramel-sunrise
coffee-appearance theme mocha-night
coffee-appearance theme hazelnut-mist
coffee-appearance theme macchiato-glow
coffee-appearance effects off
coffee-appearance effects on
coffee-appearance reset
```

Changes create files in `~/.config/` (Waybar/Fuzzel/Mako colors, GTK3 preferences,
labwc window style and optional shadow setting), and request compositor reload.
The `coffee-appearance` tool **does not** overwrite an existing user's entire
`~/.config/labwc/rc.xml`; it only adds/updates `<theme><dropShadows>`.

Effects 'off' disables compositor **shadows** and GTK's toolkit animation
preference, and removes the bar's CSS transitions. labwc does not provide the
flashy window opening/closing animations of large desktop compositors; this
option makes no claim to toggle nonexistent compositor features.

The feature currently writes Coffee-managed `~/.config/{waybar,fuzzel,mako}`
files; manually customized settings in those files may be overwritten by an
explicit appearance change. A per-user reset restores CoffeeOS defaults; it
does not restore an earlier third-party theme backup. Keep backups before
modifying heavily customized profiles.

The GTK quick settings **profile selector saves a preference only**, in line
with Phase 2 separation of unprivileged preferences and root-level CPUFreq.
To activate actual supported CPU controls, use
`sudo coffee-profile apply performance` or a different mode.

## Wallpaper

The default is `/usr/share/backgrounds/coffeeos/espresso-noir.svg`. Each built-in CoffeeOS theme has a matching branded wallpaper in the same directory.
To set a personal wallpaper, write its absolute path to:

`~/.config/coffeeos/wallpaper`

Then log out and in (or restart `coffee-wallpaper`). Images are read locally,
never uploaded. The default wallpaper is included in the source tree.

## Login & security

The login manager uses `greetd`/PAM and launches `cage` with `gtkgreet`.
The `coffee-session` launcher starts `labwc` via a session D-Bus if needed.
The **live ISO auto-signs in once** as the `coffeeos` live user and launches Coffee Desktop. The auto-login configuration is generated under `/run` only for `boot=live`; installed systems retain the normal greetd/PAM password greeter. Logging out of the live session returns to that greeter. Seat permissions and physical GPU behavior still require hardware verification. A fallback TTY login and Debian recovery kernel remain available.

## Run validation

On a Debian builder with deps and display support:

```bash
bash scripts/validate.sh
bash scripts/desktop-preflight.sh
sudo bash scripts/build-iso.sh
bash scripts/test-qemu.sh --bios
```

For manual VM inspection: verify a graphical login on VT7, login user, Waybar
and Fuzzel working, no missing window decoration, theming on both presets,
network menu, screenshots, logout/login and multi-monitor hotplug.
**A passing static test does not replace runtime verification.**


### Complete CoffeeOS themes

The six presets are Espresso Noir, Latte Cream, Caramel Sunrise, Mocha Night, Hazelnut Mist and Macchiato Glow. `coffee-appearance theme NAME` applies the full preset: labwc, GTK3/GTK4, Waybar, Fuzzel, Mako, Foot, Coffee Control Center, Coffee Quick Settings and that theme's wallpaper. Legacy `espresso` and `latte` command names remain aliases for installed systems upgraded from older CoffeeOS releases.

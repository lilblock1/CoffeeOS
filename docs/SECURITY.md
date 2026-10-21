# Security and release policy

- Debian's official signed package archives are the source of system packages. Preserve `apt-secure` and archive signatures.
- Trixie security/updates must be configured by live-build; inspect `/etc/apt/sources.list*` in the built image.
- `non-free-firmware` and `non-free` areas are opted in for hardware support; no third-party unsigned repositories.
- No root autologin, disabled password, hardcoded secret, firewall bypass or privileged performance daemon is included.
- The live-only `coffeeos` account uses Debian live-config's default `live` password (never intended as a persistent secure account); installed accounts must have installer-created passwords. The lightweight TUI greeter is not a custom auth mechanism. Greetd uses PAM.
- UEFI **Secure Boot is explicitly disabled for the image**. Do not claim support until signed chain and external validation exist.
- CoffeeOS's custom logo is original, but underlying Debian packages retain their own licenses/trademarks.
- `calamares-settings-debian` is used for early installer integration; don't presume it safely handles every custom partition scheme without testing.

- OS identity is a provisional, unowned `/etc/os-release` override in the prototype; package maintenance must be addressed before public release.

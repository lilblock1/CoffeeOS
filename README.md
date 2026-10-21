# CoffeeOS

CoffeeOS is a Debian 13 (Trixie) based gaming Linux distribution focused on low overhead, adaptive performance tuning, a lightweight Wayland desktop, and an updateable CoffeeOS package layer.

> Status: active development. The current development line is 0.10.x. CoffeeOS is not yet a production release.

## Goals

- Debian Stable foundation with APT/dpkg compatibility
- One custom CoffeeKernel with runtime Lite, Balanced, Performance, and Portable profiles
- Lightweight labwc / Wayland Coffee Desktop
- Adaptive gaming performance engine
- Deep-optimized curated packages while preserving Debian fallbacks
- One installer ISO with optional software choices such as Steam, Wine/DXVK, Gamescope, Lutris, and Heroic
- Signed in-place CoffeeOS updates in addition to Debian security updates
- Stable, Beta, and Developer release channels
- Prebuilt optimized packages so end-user builds do not need to compile Mesa and CoffeeKernel every time

## Repository infrastructure

GitHub Actions in `.github/workflows/` is designed to provide:

- source validation and tests
- ISO builds and QEMU smoke tests
- package/repository publication
- Stable / Beta / Developer channels
- signed APT metadata
- release artifacts and SHA-256 checksums

See [GitHub infrastructure](docs/GITHUB-INFRASTRUCTURE.md), [signing setup](docs/SIGNING.md), and [release process](docs/RELEASING.md).

## Security

Do not commit private signing keys, passwords, tokens, or GitHub credentials. Release signing material belongs in GitHub Actions secrets or an offline signing environment.

## License

Apache-2.0. See [LICENSE](LICENSE).

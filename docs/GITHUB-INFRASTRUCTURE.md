# CoffeeOS GitHub infrastructure

The repository is being prepared to become the canonical CoffeeOS source and release location.

## Intended layout

```text
CoffeeOS/
├── .github/workflows/
├── docs/
├── kernel/
├── live-build/
├── optimization/
├── optional/
├── scripts/
├── tests/
└── README.md
```

Large generated artifacts such as ISO images, compiled .deb files, object files, and Windows executables should not be committed to git. They belong in GitHub Actions artifacts or GitHub Releases.

## Release channels

- `dev`: fastest-moving development packages.
- `beta`: release candidates and wider testing.
- `stable`: tested public packages.

Installed CoffeeOS systems use the selected channel as the APT suite.

## GitHub Pages

The `Publish CoffeeOS Channel` workflow is designed for GitHub Pages deployment. Repository settings must use **GitHub Actions** as the Pages source.

## Build strategy

The long-term CI path is:

1. Validate source and tests.
2. Build only changed CoffeeOS packages.
3. Reuse compiler and binary caches.
4. Build CoffeeKernel and curated optimized packages.
5. Assemble the ISO.
6. Verify the ISO contents.
7. Boot-test it in QEMU.
8. Publish signed packages only after validation.

Physical GPU/game-performance testing remains separate from VM boot validation.

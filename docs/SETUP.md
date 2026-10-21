# Set up the CoffeeOS web updater

1. Generate a dedicated OpenPGP key on a trusted Linux computer: `gpg --full-generate-key`. Keep a backup securely.
2. In GitHub **Settings → Secrets and variables → Actions**, add `COFFEEOS_GPG_PRIVATE_KEY` containing the ASCII-armored export of the dedicated signing key. Add `COFFEEOS_GPG_PASSPHRASE` if encrypted. Never commit either.
3. Under **Settings → Pages**, select **GitHub Actions** as the build/deployment source.
4. Build your changed CoffeeOS packages locally, test them, and attach them to a GitHub Release. The Release must contain one or more `.deb` files.
5. In **Actions → Publish CoffeeOS Updates**, select the target channel and release tag.
6. The workflow signs every `.deb`, creates and signs `SHA256SUMS`, generates the standard signed APT metadata (`InRelease` and `Release.gpg`), verifies every signature/checksum, and only then deploys GitHub Pages.
7. The workflow also publishes the **public** signing key as:
   - `coffeeos-update-key.asc`
   - `coffeeos-update-key.gpg`
8. Install the trusted public key on CoffeeOS systems at `/usr/share/keyrings/coffeeos-update.gpg`. The key must be distributed or fingerprint-verified through a trusted bootstrap channel.
9. Configure a CoffeeOS client source such as:

```
Types: deb
URIs: https://lilblock1.github.io/CoffeeOS/
Suites: dev
Components: main
Signed-By: /usr/share/keyrings/coffeeos-update.gpg
Architectures: amd64
```

For Stable users, replace `dev` with `stable`.

**Do not** disable APT signature verification or use `trusted=yes`.

## What is signed

For each published channel, CoffeeOS now produces:

- Every `.deb` package plus a matching `.deb.asc` detached OpenPGP signature.
- `pool/<channel>/SHA256SUMS` plus `SHA256SUMS.asc`.
- `dists/<channel>/Release.gpg`.
- `dists/<channel>/InRelease`.

APT normally verifies `InRelease`/`Release.gpg`; those signed metadata files contain authenticated hashes for the package indexes, and the package indexes contain hashes for the `.deb` files. The extra per-package signatures and signed checksum file provide an additional manual verification path.

## Manual package verification

After importing the CoffeeOS public key:

```bash
gpg --verify coffeeos-system_0.10.1_amd64.deb.asc coffeeos-system_0.10.1_amd64.deb
```

To verify the channel checksum list:

```bash
gpg --verify SHA256SUMS.asc SHA256SUMS
sha256sum -c SHA256SUMS
```

## Limitations

- GitHub Pages must be enabled manually.
- GitHub Release asset downloads need to succeed before publishing; package files are copied into Pages to provide ordinary APT pool URLs.
- Pages storage/bandwidth limits may make it unsuitable for large kernel/Mesa update repositories; move to a proper static host if limits are reached.
- CI-hosted signing keys can be exposed if privileged workflows are compromised. Restrict who can modify workflows and who can run release jobs. For stronger security, sign offline.
- This workflow packages supplied binaries; it does not build or test CoffeeOS itself.

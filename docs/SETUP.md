# Set up the CoffeeOS web updater

1. Generate a dedicated OpenPGP key on a trusted Linux computer: `gpg --full-generate-key`. Keep a backup securely.
2. In GitHub **Settings → Secrets and variables → Actions**, add `COFFEEOS_GPG_PRIVATE_KEY` containing the ASCII-armored export of the dedicated signing key. Add `COFFEEOS_GPG_PASSPHRASE` if encrypted. Never commit either.
3. Under **Settings → Pages**, select **GitHub Actions** as the build/deployment source.
4. Build your changed CoffeeOS packages locally, test them, and attach them to a GitHub Release. The Release must contain one or more `.deb` files.
5. In **Actions → Publish CoffeeOS Updates**, select the target channel and release tag. The workflow checks the assets, generates signed APT metadata, and deploys Pages.
6. Export the **public** signing key (`gpg --armor --export KEYID`) and install it on CoffeeOS systems. The public key must be distributed through a trusted channel. APT clients must use `Signed-By` to bind this key to the CoffeeOS feed.
7. Configure a CoffeeOS client source such as:

```
Types: deb
URIs: https://lilblock1.github.io/CoffeeOS/
Suites: dev
Components: main
Signed-By: /usr/share/keyrings/coffeeos-update.gpg
Architectures: amd64
```

For Stable users, replace `dev` with `stable`. Import the trusted public key into `/usr/share/keyrings/coffeeos-update.gpg` using `gpg --dearmor`.

**Do not** disable APT signature verification or use `trusted=yes`.

## Limitations

- GitHub Pages must be enabled manually.
- GitHub Release asset downloads need to succeed before publishing; package files are copied into Pages to provide ordinary APT pool URLs.
- Pages storage/bandwidth limits may make it unsuitable for large kernel/Mesa update repositories; move to a proper static host if limits are reached.
- CI-hosted signing keys can be exposed if privileged workflows are compromised. Restrict who can modify workflows and who can run release jobs. For stronger security, sign offline.
- This workflow packages supplied binaries; it does not build or test CoffeeOS itself.

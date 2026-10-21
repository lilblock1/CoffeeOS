# CoffeeOS release signing

CoffeeOS update repositories must be signed. Never commit the private key.

## Create a dedicated signing key

On an offline or trusted Linux machine:

```bash
gpg --full-generate-key
gpg --list-secret-keys --keyid-format LONG
```

Export the private key for GitHub Actions only if you accept CI-held signing credentials:

```bash
gpg --armor --export-secret-keys YOUR_KEY_ID > coffeeos-release-private.asc
gpg --armor --export YOUR_KEY_ID > coffeeos-release-public.asc
```

## Required GitHub Actions secrets

Create these repository secrets:

- `COFFEEOS_GPG_PRIVATE_KEY` — complete ASCII-armored private key.
- `COFFEEOS_GPG_PASSPHRASE` — key passphrase, if the key has one.

Do not paste either secret into an issue, commit, pull request, chat message, or workflow file.

The public key is safe to publish and should eventually ship in CoffeeOS under `/usr/share/keyrings/`.

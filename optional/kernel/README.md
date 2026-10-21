# CoffeeKernel — ONE kernel, runtime modes

`../../kernel/configs/coffee.conf` is the **only** CoffeeKernel config.
`../../scripts/build-kernel.sh` builds ONE kernel image and headers pair.
Switch CPU governor/energy profiles live using
`sudo coffee-profile apply lite|balanced|performance|portable`.
The Debian kernel remains installed for emergency boot fallback only.
No compiled CoffeeKernel exists yet. See `../../docs/KERNEL-BUILD.md`.

Profiles: Lite, Balanced, Performance, Portable. `coffee-profile set NAME`
records a user preference only. `sudo coffee-profile apply NAME` calls the
real runtime CPUFreq profile controller; `sudo coffee-profile restore` restores
the pre-CoffeeOS CPU governor/EPP settings when still supported. Supported-only
settings, no overclocking, no mandatory services or telemetry. Requires CPUFreq
sysfs hardware support; test on physical systems. See docs/KERNEL-BUILD.md.

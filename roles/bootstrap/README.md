# bootstrap

Initial host setup: SSH keys, packages, timezone, hostname, and related baseline configuration.

On modern Ubuntu images without `/etc/timezone` (for example 26.04), timezone is set via `community.general.timezone` only; legacy `/etc/timezone` and `/etc/localtime` tasks run only when that file already exists.

Part of the `steveyminecraft.pihole` collection.

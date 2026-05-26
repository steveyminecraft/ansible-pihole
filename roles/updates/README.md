# updates

Apply OS package updates on Pi-hole hosts.

When `vagrant_env: true`, the role skips rebooting after package updates so
Molecule/Vagrant runs do not stall while guest networking re-initializes.

Part of the `steveyminecraft.pihole` collection.

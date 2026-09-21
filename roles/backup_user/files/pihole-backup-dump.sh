#!/usr/bin/env bash
# Dump Pi-hole config + gravity DB to stdout as gzip tar.
# Forced-command target for the dump-only backup SSH user.
# Does not include pihole-FTL.db (query history) or other volume files.
# PIHOLE_BACKUP_ROOT is for tests only (ignored when running as root).
set -euo pipefail

root="/opt/pihole"
if [[ "$(id -u)" -ne 0 && -n "${PIHOLE_BACKUP_ROOT:-}" ]]; then
  root="$PIHOLE_BACKUP_ROOT"
fi
exec tar -C "$root" -czf - \
  etc/dnsmasq.d \
  etc/pihole/pihole.toml \
  etc/pihole/gravity.db

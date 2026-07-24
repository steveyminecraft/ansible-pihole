#!/usr/bin/env bash
# Ensure vagrant-56 has static DHCP host entries matching inventory/vagrant_libvirt.yml
# (192.168.121.4 / .5). Without these, NM DHCP hands out .100+ and Molecule prepare
# cannot reach ansible_host addresses.
set -euo pipefail

export LIBVIRT_DEFAULT_URI="${LIBVIRT_DEFAULT_URI:-qemu:///system}"

ensure_host() {
  local mac="$1" ip="$2" name="$3" xml current
  xml="$(virsh net-dumpxml vagrant-56)"
  if echo "$xml" | grep -Fq "mac='${mac}'"; then
    current="$(echo "$xml" | tr '\n' ' ' | sed -n "s/.*mac='${mac}'[^>]*ip='\([^']*\)'.*/\1/p")"
    if [[ "${current}" == "${ip}" ]]; then
      echo "OK: ${mac} -> ${ip}"
      return 0
    fi
    virsh net-update vagrant-56 delete ip-dhcp-host "<host mac='${mac}'/>" --live --config || true
  fi
  virsh net-update vagrant-56 add-last ip-dhcp-host \
    "<host mac='${mac}' name='${name}' ip='${ip}'/>" --live --config
  echo "SET: ${mac} -> ${ip}"
}

ensure_host '52:54:00:56:00:04' '192.168.121.4' 'vagrant-pihole-01'
ensure_host '52:54:00:56:00:05' '192.168.121.5' 'vagrant-pihole-02'

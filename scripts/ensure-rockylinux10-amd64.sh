#!/usr/bin/env bash
# Ensure rockylinux/10 libvirt box is official x86_64, has correct virtual_size
# metadata, and NetworkManager DHCP profiles.
#
# CDN box ships empty system-connections (no cloud-init) and metadata.json with
# virtual_size=5 while the qcow2 is 10GiB — vagrant-libvirt then creates a 5G
# disk, root XFS cannot mount (dracut emergency), and Vagrant waits forever for SSH.
set -euo pipefail

BOX_NAME=rockylinux/10
URL=${ROCKY10_LIBVIRT_AMD64_BOX_URL:-https://dl.rockylinux.org/pub/rocky/10/images/x86_64/Rocky-10-Vagrant-Libvirt.latest.x86_64.vagrant.libvirt.box}
OUT=${TMPDIR:-/tmp}/rockylinux-10-libvirt-amd64.box
BOX_DIR="${HOME}/.vagrant.d/boxes/rockylinux-VAGRANTSLASH-10/0/libvirt"
BOX_IMG="${BOX_DIR}/box.img"
BOX_META="${BOX_DIR}/metadata.json"
NM_CONN=${TMPDIR:-/tmp}/vagrant-dhcp.nmconnection

ensure_box_present() {
  if [[ -f "${BOX_IMG}" ]]; then
    echo "OK: ${BOX_NAME} box image present"
    return 0
  fi
  echo "Downloading amd64 ${BOX_NAME} from ${URL}"
  curl -fL --retry 3 --retry-delay 5 -o "${OUT}" "${URL}"
  vagrant box add "${OUT}" --name "${BOX_NAME}" --provider libvirt --force
}

# Official CDN box is 10GiB, but metadata.json ships virtual_size=5. vagrant-libvirt
# trusts that and creates a 5G volume → GPT/root XFS past EOF → dracut emergency
# (no NM/DHCP). Align metadata with qemu-img virtual size (GiB, rounded up).
fix_box_virtual_size_metadata() {
  [[ -f "${BOX_IMG}" && -f "${BOX_META}" ]] || return 0
  local bytes gib
  bytes=$(qemu-img info --output=json "${BOX_IMG}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["virtual-size"])')
  gib=$(( (bytes + 1024*1024*1024 - 1) / (1024*1024*1024) ))
  python3 - "${BOX_META}" "${gib}" <<'PY'
import json, sys
path, gib = sys.argv[1], int(sys.argv[2])
with open(path, encoding="utf-8") as f:
    meta = json.load(f)
if meta.get("virtual_size") == gib:
    print(f"OK: metadata virtual_size already {gib}")
else:
    print(f"Fixing metadata virtual_size {meta.get('virtual_size')!r} -> {gib}")
    meta["virtual_size"] = gib
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")
PY
}

write_nm_conn() {
  # multi-connect=3: Rocky has ens5 (vagrant-libvirt mgmt) + ens6 (vagrant-56).
  # Without it NM binds the profile to one NIC → no mgmt DHCP → vagrant hangs.
  cat > "${NM_CONN}" <<'EOF'
[connection]
id=vagrant-dhcp
uuid=a1b2c3d4-e5f6-7890-abcd-ef1234567890
type=ethernet
autoconnect=true
autoconnect-priority=100
multi-connect=3

[ethernet]

[ipv4]
method=auto

[ipv6]
method=auto
EOF
  chmod 600 "${NM_CONN}"
}

inject_nm_into_image() {
  local img="$1"
  [[ -f "${img}" ]] || return 0
  echo "Injecting NetworkManager DHCP profile into ${img}"
  # Root FS is the last xfs partition on Rocky 10 Vagrant libvirt images (sda4).
  guestfish --rw -a "${img}" <<'EOF'
run
mount /dev/sda4 /
mkdir-p /etc/NetworkManager/system-connections
upload /tmp/vagrant-dhcp.nmconnection /etc/NetworkManager/system-connections/vagrant-dhcp.nmconnection
chmod 0600 /etc/NetworkManager/system-connections/vagrant-dhcp.nmconnection
# Ensure NM is enabled even if a future box drops the symlink.
ln-sf /usr/lib/systemd/system/NetworkManager.service /etc/systemd/system/multi-user.target.wants/NetworkManager.service
EOF
}

ensure_box_present
fix_box_virtual_size_metadata
write_nm_conn
# Always re-inject (idempotent upload) so retries after partial fixes work.
inject_nm_into_image "${BOX_IMG}"

# Also patch any libvirt pool copies so reused volumes get the fix.
for img in /var/lib/libvirt/images/rockylinux*_box.img; do
  [[ -e "${img}" ]] || continue
  # Pool images may be root-owned; try via sg libvirt / writable by user.
  if [[ -w "${img}" ]]; then
    inject_nm_into_image "${img}"
  else
    echo "Skipping non-writable pool image ${img} (will be recreated from patched box)"
  fi
done

echo "Installed/patched ${BOX_NAME} with NM DHCP autoconnect"

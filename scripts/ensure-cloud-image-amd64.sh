#!/usr/bin/env bash
# Ensure cloud-image/ubuntu-26.04 libvirt box is amd64 (x86_64 hosts).
# This Vagrant lacks vm.box_architecture; Vagrant Cloud can hand out arm64.
set -euo pipefail
BOX_NAME=cloud-image/ubuntu-26.04
META=$(find "${HOME}/.vagrant.d/boxes/cloud-image-VAGRANTSLASH-ubuntu-26.04" -name metadata.json 2>/dev/null | head -1 || true)
if [[ -n "${META}" ]] && grep -q '"architecture": "amd64"' "${META}"; then
  echo "OK: ${BOX_NAME} is amd64 ($(dirname "${META}"))"
  exit 0
fi
if [[ -n "${META}" ]] && grep -q '"architecture": "arm64"' "${META}"; then
  echo "Removing arm64 ${BOX_NAME} box..."
  vagrant box remove "${BOX_NAME}" --provider libvirt --all -f || true
  rm -rf "${HOME}/.vagrant.d/boxes/cloud-image-VAGRANTSLASH-ubuntu-26.04"
  virsh -c "${LIBVIRT_DEFAULT_URI:-qemu:///system}" vol-delete --pool default \
    cloud-image-VAGRANTSLASH-ubuntu-26.04_vagrant_box_image_20260720.0.0_box.img 2>/dev/null || true
fi
BOX_URL=${CLOUD_IMAGE_UBUNTU_2604_AMD64_URL:-https://vagrantcloud.com/cloud-image/boxes/ubuntu-26.04/versions/20260720.0.0/providers/libvirt/amd64/vagrant.box}
OUT=${TMPDIR:-/tmp}/ubuntu-26.04-libvirt-amd64.box
echo "Downloading amd64 ${BOX_NAME}..."
curl -fL --retry 3 --retry-delay 5 -o "${OUT}" "${BOX_URL}"
vagrant box add "${OUT}" --name "${BOX_NAME}" --provider libvirt --force
META=$(find "${HOME}/.vagrant.d/boxes/cloud-image-VAGRANTSLASH-ubuntu-26.04" -name metadata.json | head -1)
grep -q '"architecture": "amd64"' "${META}"
echo "Installed amd64 ${BOX_NAME}"

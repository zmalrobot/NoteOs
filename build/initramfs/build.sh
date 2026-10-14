#!/usr/bin/env bash
# ==============================================================================
# NoteOS — build/initramfs/build.sh
# Deterministic generation of NoteOS initramfs images (release and debug).
# ==============================================================================
set -euo pipefail

DEVICE="${DEVICE:-n8000}"
BUILD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${BUILD_DIR}/.." && pwd)"
DEVICE_CONF="${BUILD_DIR}/devices/${DEVICE}/device.conf"

if [ ! -f "${DEVICE_CONF}" ]; then
    echo "ERROR: Device configuration not found: ${DEVICE_CONF}" >&2
    exit 1
fi

# shellcheck source=/dev/null
source "${DEVICE_CONF}"

export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1700000000}"
OUT_DIR="${REPO_ROOT}/out/${DEVICE}"

build_cpio_variant() {
    local variant="$1"
    local build_dir="${OUT_DIR}/initramfs_root_${variant}"
    local cpio_out="${OUT_DIR}/initramfs${variant:+-${variant}}.cpio"

    rm -rf "${build_dir}"
    mkdir -p "${OUT_DIR}"
    mkdir -p "${build_dir}"/{bin,sbin,dev,proc,sys,sysroot,etc,run}

    if [ -x /usr/bin/busybox ]; then
        cp /usr/bin/busybox "${build_dir}/bin/busybox"
    else
        echo "ERROR: /usr/bin/busybox not found in build environment!" >&2
        exit 1
    fi
    chmod 0755 "${build_dir}/bin/busybox"

    (
        cd "${build_dir}/bin"
        for app in $(./busybox --list); do
            [ "$app" = "busybox" ] && continue
            ln -sf busybox "$app"
        done
    )

    rm -rf "${build_dir}/sbin"
    ln -s bin "${build_dir}/sbin"

    mknod -m 600 "${build_dir}/dev/console" c 5 1 2>/dev/null || true
    mknod -m 666 "${build_dir}/dev/null" c 1 3 2>/dev/null || true
    mknod -m 666 "${build_dir}/dev/tty" c 5 0 2>/dev/null || true
    mknod -m 666 "${build_dir}/dev/tty0" c 4 0 2>/dev/null || true

    if [ -z "${variant}" ]; then
        # Production release variant: zero console noise, zero debug code
        cat << 'EOF' > "${build_dir}/init"
#!/bin/sh
export PATH=/bin:/sbin

mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev

printf '\033[?25l' > /dev/tty0 2>/dev/null || true

ROOT_DEV=""
for i in $(seq 1 10); do
    CAND=$(findfs LABEL=debian_root 2>/dev/null || true)
    if [ -n "$CAND" ] && [ -b "$CAND" ]; then
        ROOT_DEV="$CAND"
        break
    fi
    for dev in /dev/mmcblk0p8 /dev/block/mmcblk0p8 /dev/block/platform/dw_mmc/by-name/USERDATA; do
        if [ -b "$dev" ]; then
            ROOT_DEV="$dev"
            break 2
        fi
    done
    sleep 1
done

if [ -n "$ROOT_DEV" ] && mount -t ext4 -o rw,noatime "$ROOT_DEV" /sysroot 2>/dev/null; then
    if [ -x /sysroot/sbin/init ] || [ -L /sysroot/sbin/init ]; then
        mkdir -p /sysroot/dev
        mount --move /dev /sysroot/dev 2>/dev/null || true
        umount /proc 2>/dev/null || true
        umount /sys 2>/dev/null || true
        exec switch_root /sysroot /sbin/init
    fi
fi

sleep 5
reboot -f
EOF
    else
        # Diagnostic debug variant (used only in boot-debug.img)
        cat << 'EOF' > "${build_dir}/init"
#!/bin/sh
export PATH=/bin:/sbin

mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev

echo "=== NoteOS Diagnostic Initramfs ==="

for i in 1 2 3; do
    if ip link show usb0 >/dev/null 2>&1; then
        ip link set usb0 up 2>/dev/null || true
        ip addr add 192.168.3.2/24 dev usb0 2>/dev/null || true
        break
    fi
    sleep 1
done

ROOT_DEV=""
for i in $(seq 1 10); do
    CAND=$(findfs LABEL=debian_root 2>/dev/null || true)
    if [ -n "$CAND" ] && [ -b "$CAND" ]; then
        ROOT_DEV="$CAND"
        break
    fi
    for dev in /dev/mmcblk0p8 /dev/block/mmcblk0p8 /dev/block/platform/dw_mmc/by-name/USERDATA; do
        if [ -b "$dev" ]; then
            ROOT_DEV="$dev"
            break 2
        fi
    done
    sleep 1
done

if [ -n "$ROOT_DEV" ] && mount -t ext4 -o rw,noatime "$ROOT_DEV" /sysroot 2>/dev/null; then
    if [ -x /sysroot/sbin/init ] || [ -L /sysroot/sbin/init ]; then
        mkdir -p /sysroot/dev /sysroot/run
        mount -t tmpfs -o mode=0755,nosuid,nodev tmpfs /sysroot/run 2>/dev/null || true
        mkdir -p /sysroot/run/systemd/system/multi-user.target.wants /sysroot/run/sshd
        chmod 0755 /sysroot/run/sshd
        cat << 'UNIT_EOF' > /sysroot/run/systemd/system/noteos-debug.service
[Unit]
Description=NoteOS Transient USB RNDIS & SSH Diagnostics (RAM-only)
After=network-pre.target
Before=network.target NetworkManager.service

[Service]
Type=oneshot
RemainAfterExit=yes
TimeoutStartSec=30
ExecStart=/bin/sh -c 'mkdir -p /run/NetworkManager/conf.d /run/sshd; chmod 0755 /run/sshd; printf "[keyfile]\nunmanaged-devices=interface-name:usb0\n" > /run/NetworkManager/conf.d/99-unmanaged-usb0.conf; ip link set usb0 up 2>/dev/null || true; ip addr replace 192.168.3.2/24 dev usb0 2>/dev/null || true; ip route replace default via 192.168.3.100 dev usb0 2>/dev/null || true; cp /etc/shadow /run/debug-shadow && sed -i "s|^root:[^:]*:|root::|" /run/debug-shadow && mount --bind /run/debug-shadow /etc/shadow; ssh-keygen -A 2>/dev/null || true; /usr/sbin/sshd -o PermitRootLogin=yes -o PasswordAuthentication=yes -o PermitEmptyPasswords=yes -o UsePAM=no 2>/dev/null || true'
UNIT_EOF
        ln -sf ../noteos-debug.service /sysroot/run/systemd/system/multi-user.target.wants/noteos-debug.service
        mount --move /dev /sysroot/dev 2>/dev/null || true
        umount /proc 2>/dev/null || true
        umount /sys 2>/dev/null || true
        exec switch_root /sysroot /sbin/init
    fi
fi

while true; do
    setsid cttyhack sh 2>/dev/console < /dev/console > /dev/console || sh < /dev/console > /dev/console 2>&1
    sleep 1
done
EOF
    fi

    chmod 0755 "${build_dir}/init"
    find "${build_dir}" -exec touch -h -d "@${SOURCE_DATE_EPOCH}" {} +

    (
        cd "${build_dir}"
        find . -print0 | LC_ALL=C sort -z | cpio --null --reproducible -H newc -o > "${cpio_out}"
        gzip -n -9 -c "${cpio_out}" > "${cpio_out}.gz"
    )
}

echo "=== [initramfs] Generating Release and Debug Initramfs for NoteOS (${DEVICE}) ==="
build_cpio_variant ""
build_cpio_variant "debug"

rm -rf "${OUT_DIR}/initramfs_root"
cp -a "${OUT_DIR}/initramfs_root_" "${OUT_DIR}/initramfs_root" 2>/dev/null || true
rm -rf "${OUT_DIR}/initramfs_root_" 2>/dev/null || true

echo "=== [initramfs] Completed: Release=$(stat -c%s "${OUT_DIR}/initramfs.cpio.gz") B | Debug=$(stat -c%s "${OUT_DIR}/initramfs-debug.cpio.gz") B ==="

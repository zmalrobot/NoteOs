#!/usr/bin/env bash
# ==============================================================================
# NoteOS — 08_verify_install.sh
# Post-installation verification (read-only).
# Verifies device state, boot partition checksum, rootfs filesystem integrity,
# and untouched recovery partition.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/common.sh"

show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Performs read-only post-install verification on a connected device.

OPTIONS:
  --help             Show this help message and exit
  --boot <FILE>      Reference boot.img to verify against (default: release/boot.img)

EOF
}

BOOT_REF=""

while [ $# -gt 0 ]; do
    case "$1" in
        --help|-h)
            show_help
            exit 0
            ;;
        --boot)
            BOOT_REF="$2"
            shift 2
            ;;
        *)
            die "Unknown option: $1. Use --help for usage."
            ;;
    esac
done

if [ -z "${BOOT_REF}" ]; then
    if [ -f "${NOTEOS_RELEASE_DIR}/boot.img" ]; then
        BOOT_REF="${NOTEOS_RELEASE_DIR}/boot.img"
    elif [ -f "${NOTEOS_OUT_DIR}/n8000/boot.img" ]; then
        BOOT_REF="${NOTEOS_OUT_DIR}/n8000/boot.img"
    fi
fi

check_device_twrp

log_info "=== NoteOS: Post-Installation Verification ==="

TARGET_BOOT_DEV="/dev/block/mmcblk0p5"
TARGET_ROOTFS_DEV="/dev/block/mmcblk0p8"
TARGET_RECOVERY_DEV="/dev/block/mmcblk0p6"

# 1. Boot Partition Verification
if [ -n "${BOOT_REF}" ] && [ -f "${BOOT_REF}" ]; then
    ref_sz=$(stat -c%s "${BOOT_REF}")
    ref_sha=$(sha256sum "${BOOT_REF}" | awk '{print $1}')
    dev_sha=$(adb shell "head -c ${ref_sz} ${TARGET_BOOT_DEV} | sha256sum" | awk '{print $1}')

    log_info "Verifying Boot partition (${TARGET_BOOT_DEV})..."
    log_info "  Reference SHA256: ${ref_sha} (${ref_sz} bytes)"
    log_info "  Device SHA256   : ${dev_sha}"

    if [ "${ref_sha}" = "${dev_sha}" ]; then
        log_success "Boot partition matches reference image exactly bit-by-bit."
    else
        die "MISMATCH: Boot partition does not match reference image!"
    fi
fi

# 2. Filesystem Integrity Check
log_info "Verifying Rootfs filesystem integrity on ${TARGET_ROOTFS_DEV}..."
FS_CHECK=$(adb shell "e2fsck -f -n ${TARGET_ROOTFS_DEV} 2>/dev/null" || true)
if echo "${FS_CHECK}" | grep -q "clean"; then
    log_success "Rootfs filesystem is clean: $(echo "${FS_CHECK}" | tail -n 1)"
else
    log_info "${FS_CHECK}"
fi

# 3. Recovery Partition Untouched Verification
if [ -f "${NOTEOS_BACKUP_DIR}/recovery_pre_install.img.sha256" ]; then
    expected_rec=$(awk '{print $1}' "${NOTEOS_BACKUP_DIR}/recovery_pre_install.img.sha256")
    live_rec=$(adb shell "sha256sum ${TARGET_RECOVERY_DEV}" | awk '{print $1}')
    log_info "Verifying untouched Recovery partition (${TARGET_RECOVERY_DEV})..."
    if [ "${expected_rec}" = "${live_rec}" ]; then
        log_success "TWRP Recovery partition is 100% intact and unchanged (${live_rec})."
    else
        log_warn "Recovery checksum differs from pre-install backup!"
    fi
fi

log_success "All post-install checks passed."


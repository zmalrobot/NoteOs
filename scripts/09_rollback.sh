#!/usr/bin/env bash
# ==============================================================================
# NoteOS — 09_rollback.sh
# Safely restores stock or pre-install BOOT partition (and optionally RECOVERY)
# from user's backup directory.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/common.sh"

show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Restores BOOT (mmcblk0p5) and/or RECOVERY (mmcblk0p6) from backup files.

OPTIONS:
  --help             Show this help message and exit
  --dry-run          Simulate restoration without writing (SAFE)
  --backup-dir <DIR> Backup directory (default: ${NOTEOS_BACKUP_DIR})
  --recovery         Also restore RECOVERY partition from backup
  --stock            Restore stock Android boot.img instead of pre-install backup

EOF
}

DRY_RUN=0
RESTORE_RECOVERY=0
USE_STOCK=0
BACKUP_DIR="${NOTEOS_BACKUP_DIR}"

while [ $# -gt 0 ]; do
    case "$1" in
        --help|-h)
            show_help
            exit 0
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --recovery)
            RESTORE_RECOVERY=1
            shift
            ;;
        --stock)
            USE_STOCK=1
            shift
            ;;
        --backup-dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        *)
            die "Unknown option: $1. Use --help for usage."
            ;;
    esac
done

check_device_twrp

log_info "=== NoteOS: Partition Rollback & Recovery ==="
log_info "Backup directory: ${BACKUP_DIR}"

TARGET_BOOT_DEV="/dev/block/mmcblk0p5"
TARGET_RECOVERY_DEV="/dev/block/mmcblk0p6"

# Determine source boot image
if [ "${USE_STOCK}" -eq 1 ]; then
    BOOT_SRC="${BACKUP_DIR}/boot.img"
else
    if [ -f "${BACKUP_DIR}/boot_pre_install.img" ]; then
        BOOT_SRC="${BACKUP_DIR}/boot_pre_install.img"
    else
        BOOT_SRC="${BACKUP_DIR}/boot.img"
    fi
fi

if [ ! -f "${BOOT_SRC}" ]; then
    die "Boot backup image not found at ${BOOT_SRC}."
fi

RECOVERY_SRC="${BACKUP_DIR}/recovery.img"
if [ ! -f "${RECOVERY_SRC}" ] && [ -f "${BACKUP_DIR}/recovery_pre_install.img" ]; then
    RECOVERY_SRC="${BACKUP_DIR}/recovery_pre_install.img"
fi

echo ""
echo "Partitions selected for rollback:"
echo "  BOOT     : ${BOOT_SRC} -> ${TARGET_BOOT_DEV}"
if [ "${RESTORE_RECOVERY}" -eq 1 ]; then
    echo "  RECOVERY : ${RECOVERY_SRC} -> ${TARGET_RECOVERY_DEV}"
fi
echo ""

if [ "${DRY_RUN}" -eq 1 ]; then
    log_info "[DRY-RUN] Rollback simulation complete. No data written."
    exit 0
fi

read -r -p "Type exactly 'CONFIRM ROLLBACK' to proceed: " CONFIRM_ROLLBACK
if [ "${CONFIRM_ROLLBACK}" != "CONFIRM ROLLBACK" ]; then
    die "Confirmation phrase did not match. Aborting rollback."
fi

# Flash and verify BOOT
log_info "Restoring BOOT partition..."
boot_sz=$(stat -c%s "${BOOT_SRC}")
boot_sha=$(sha256sum "${BOOT_SRC}" | awk '{print $1}')

adb push "${BOOT_SRC}" /tmp/rollback_boot.img
adb shell "dd if=/tmp/rollback_boot.img of=${TARGET_BOOT_DEV} bs=4096 conv=fsync 2>/dev/null"
adb shell "rm -f /tmp/rollback_boot.img"

readback_boot_sha=$(adb shell "head -c ${boot_sz} ${TARGET_BOOT_DEV} | sha256sum" | awk '{print $1}')
if [ "${boot_sha}" != "${readback_boot_sha}" ]; then
    die "CRITICAL FAILURE: Restored boot partition checksum does not match backup image!"
fi
log_success "BOOT partition restored and verified bit-by-bit."

# Optionally restore RECOVERY
if [ "${RESTORE_RECOVERY}" -eq 1 ]; then
    if [ ! -f "${RECOVERY_SRC}" ]; then
        die "Recovery backup image not found at ${RECOVERY_SRC}."
    fi
    log_info "Restoring RECOVERY partition..."
    rec_sz=$(stat -c%s "${RECOVERY_SRC}")
    rec_sha=$(sha256sum "${RECOVERY_SRC}" | awk '{print $1}')

    adb push "${RECOVERY_SRC}" /tmp/rollback_recovery.img
    adb shell "dd if=/tmp/rollback_recovery.img of=${TARGET_RECOVERY_DEV} bs=4096 conv=fsync 2>/dev/null"
    adb shell "rm -f /tmp/rollback_recovery.img"

    readback_rec_sha=$(adb shell "head -c ${rec_sz} ${TARGET_RECOVERY_DEV} | sha256sum" | awk '{print $1}')
    if [ "${rec_sha}" != "${readback_rec_sha}" ]; then
        die "CRITICAL FAILURE: Restored recovery partition checksum does not match backup image!"
    fi
    log_success "RECOVERY partition restored and verified bit-by-bit."
fi

log_success "Rollback completed successfully."


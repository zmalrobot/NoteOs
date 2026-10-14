#!/usr/bin/env bash
# ==============================================================================
# NoteOS — 01_backup_device.sh
# Safely dumps critical device partitions (BOOT, RECOVERY, EFS, GPT layout)
# to an external private backup directory before performing any write operations.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/common.sh"

show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Dumps partition images and MBR/GPT table from connected GT-N8000 device via TWRP ADB.

OPTIONS:
  --help             Show this help message and exit
  --dry-run          Simulate actions without reading or writing files
  --out <DIR>        Destination directory (default: ${NOTEOS_BACKUP_DIR})
  --full             Also dump SYSTEM partition (/dev/block/mmcblk0p9, ~3.5 GiB)

EOF
}

DRY_RUN=0
DUMP_FULL=0
OUT_BACKUP_DIR="${NOTEOS_BACKUP_DIR}"

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
        --full)
            DUMP_FULL=1
            shift
            ;;
        --out)
            OUT_BACKUP_DIR="$2"
            shift 2
            ;;
        *)
            die "Unknown option: $1. Use --help for usage."
            ;;
    esac
done

if [ "${DRY_RUN}" -eq 1 ]; then
    log_info "DRY-RUN mode enabled. No files will be transferred or written."
fi

check_device_twrp

log_info "=== NoteOS Device Backup ==="
log_info "Destination: ${OUT_BACKUP_DIR}"

if [ "${DRY_RUN}" -eq 0 ]; then
    mkdir -p "${OUT_BACKUP_DIR}"
fi

# Partition block mapping on Samsung Galaxy Note 10.1 (GT-N8000)
declare -A PARTITIONS=(
    ["boot.img"]="/dev/block/mmcblk0p5"
    ["recovery.img"]="/dev/block/mmcblk0p6"
    ["efs.img"]="/dev/block/mmcblk0p3"
    ["param.img"]="/dev/block/mmcblk0p4"
    ["radio.img"]="/dev/block/mmcblk0p7"
)

if [ "${DUMP_FULL}" -eq 1 ]; then
    PARTITIONS["system.img"]="/dev/block/mmcblk0p9"
fi

for img_name in "${!PARTITIONS[@]}"; do
    dev_path="${PARTITIONS[${img_name}]}"
    dest_file="${OUT_BACKUP_DIR}/${img_name}"
    log_info "Backing up ${img_name} from ${dev_path}..."

    if [ "${DRY_RUN}" -eq 1 ]; then
        log_info "  [DRY-RUN] Would dump ${dev_path} -> ${dest_file}"
        continue
    fi

    adb shell "dd if=${dev_path} bs=4096 2>/dev/null" > "${dest_file}"
    sz=$(stat -c%s "${dest_file}")
    sha=$(sha256sum "${dest_file}" | awk '{print $1}')
    printf "  [OK] %-15s %10d bytes  SHA256: %s\n" "${img_name}" "${sz}" "${sha}"
done

# Dump MBR/GPT partition table
log_info "Dumping partition table and first 16 MiB of mmcblk0..."
if [ "${DRY_RUN}" -eq 1 ]; then
    log_info "  [DRY-RUN] Would dump sfdisk -d and first 16M of /dev/block/mmcblk0"
else
    adb shell "sfdisk -d /dev/block/mmcblk0 2>/dev/null" > "${OUT_BACKUP_DIR}/mmcblk0_sfdisk_original.dump"
    adb shell "dd if=/dev/block/mmcblk0 bs=1M count=16 2>/dev/null" > "${OUT_BACKUP_DIR}/mmcblk0_first16M.img"
    (
        cd "${OUT_BACKUP_DIR}"
        find . -type f -not -name "*.sha256" -not -name "BACKUP_VERIFIED_SHA256.txt" -exec sha256sum {} + > "BACKUP_VERIFIED_SHA256.txt"
    )
    log_success "Device backup completed successfully and checksummed."
fi


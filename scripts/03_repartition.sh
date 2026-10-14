#!/usr/bin/env bash
# ==============================================================================
# NoteOS — 03_repartition.sh (EXPERIMENTAL)
# Merges partitions 8-12 into a single unified root partition on Samsung Galaxy Note 10.1.
#
# SAFETY RULES:
# - DRY-RUN by default.
# - Requires typed confirmation phrase and --apply to write.
# - Strictly preserves protected partitions: BOTA0/1, EFS, PARAM, BOOT, RECOVERY, RADIO.
# - Rejects if current partition table does not match stock layout.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/common.sh"

show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

EXPERIMENTAL: Repartitions GT-N8000 eMMC to allocate ~14.5 GiB for NoteOS rootfs.

OPTIONS:
  --help             Show this help message and exit
  --dry-run          Simulate checks and partition commands without writing (DEFAULT)
  --apply            Actually apply the partition changes (requires typed confirmation)
  --backup-dir <DIR> Path to backup directory containing mmcblk0_sfdisk_original.dump

WARNING:
  This script is EXPERIMENTAL. Repartitioning eMMC carries inherent risk of bricking.
  You MUST have completed scripts/01_backup_device.sh before attempting this.
EOF
}

APPLY=0
DRY_RUN=1
BACKUP_DIR="${NOTEOS_BACKUP_DIR}"

while [ $# -gt 0 ]; do
    case "$1" in
        --help|-h)
            show_help
            exit 0
            ;;
        --dry-run)
            DRY_RUN=1
            APPLY=0
            shift
            ;;
        --apply)
            APPLY=1
            DRY_RUN=0
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

log_info "=== NoteOS: Device Repartitioning Check ==="

ORIGINAL_LAYOUT="${REPO_ROOT}/build/devices/n8000/partition-layout-original.sfdisk"
TARGET_LAYOUT="${REPO_ROOT}/build/devices/n8000/partition-layout-current.sfdisk"

if [ ! -f "${ORIGINAL_LAYOUT}" ]; then
    die "Original partition layout reference not found: ${ORIGINAL_LAYOUT}"
fi

if [ ! -f "${TARGET_LAYOUT}" ]; then
    die "Target partition layout reference not found: ${TARGET_LAYOUT}"
fi

# Verification 1: Require backup files from 01_backup_device.sh
log_info "Verifying required safety backup files in ${BACKUP_DIR}..."
if [ ! -f "${BACKUP_DIR}/mmcblk0_sfdisk_original.dump" ] || [ ! -f "${BACKUP_DIR}/mmcblk0_first16M.img" ]; then
    die "Required backup files missing in ${BACKUP_DIR}!\nYou must run scripts/01_backup_device.sh before repartitioning."
fi
log_success "Backup verification passed."

# Verification 2: Check whether device is already repartitioned
log_info "Inspecting live partition table on device..."
LIVE_PARTITIONS=$(adb shell "cat /proc/partitions" 2>/dev/null || true)
if echo "${LIVE_PARTITIONS}" | grep -q "mmcblk0p8" && ! echo "${LIVE_PARTITIONS}" | grep -q "mmcblk0p9"; then
    log_warn "Device is ALREADY repartitioned with the NoteOS layout (mmcblk0p8 has ~14.5 GiB, p9-p12 absent)."
    log_info "No repartitioning needed. Aborting."
    exit 0
fi

# Verification 3: Locate sfdisk on device
SFDISK_BIN=""
if adb shell "which sfdisk >/dev/null 2>&1"; then
    SFDISK_BIN="sfdisk"
elif adb shell "[ -x /tmp/sfdisk ]"; then
    SFDISK_BIN="/tmp/sfdisk"
else
    die "sfdisk not found in TWRP. Please copy an armhf static sfdisk binary to /tmp/sfdisk on the device (see docs/REPARTITION.md)."
fi

# Verification 4: Read live partition table via sfdisk -d
log_info "Reading live partition table from /dev/block/mmcblk0 via ${SFDISK_BIN}..."
TEMP_CURRENT=$(mktemp)
adb shell "${SFDISK_BIN} -d /dev/block/mmcblk0 2>/dev/null" > "${TEMP_CURRENT}"

if grep -q "mmcblk0p8.*size=.*30588928" "${TEMP_CURRENT}"; then
    rm -f "${TEMP_CURRENT}"
    log_warn "Device is ALREADY repartitioned with the NoteOS layout (mmcblk0p8 has ~14.5 GiB)."
    log_info "No repartitioning needed. Aborting."
    exit 0
fi

# Verification 5: Current layout must match stock original layout exactly
log_info "Comparing live partition table with stock original reference..."
# Compare partition lines (p1 to p12)
TEMP_STOCK_FILTERED=$(mktemp)
TEMP_LIVE_FILTERED=$(mktemp)
grep -E "/dev/block/mmcblk0p[0-9]+" "${ORIGINAL_LAYOUT}" | awk '{print $1,$3,$4,$5,$6}' > "${TEMP_STOCK_FILTERED}"
grep -E "/dev/block/mmcblk0p[0-9]+" "${TEMP_CURRENT}" | awk '{print $1,$3,$4,$5,$6}' > "${TEMP_LIVE_FILTERED}"

if ! cmp -s "${TEMP_STOCK_FILTERED}" "${TEMP_LIVE_FILTERED}"; then
    rm -f "${TEMP_CURRENT}" "${TEMP_STOCK_FILTERED}" "${TEMP_LIVE_FILTERED}"
    die "Live partition table does NOT match expected stock GT-N8000 layout!\nRefusing to repartition non-standard partition table to prevent data loss."
fi
rm -f "${TEMP_CURRENT}" "${TEMP_STOCK_FILTERED}" "${TEMP_LIVE_FILTERED}"
log_success "Live partition layout matches stock GT-N8000 layout."

if [ "${APPLY}" -eq 0 ]; then
    log_info "[DRY-RUN] Repartitioning simulated. Device layout is eligible for repartitioning."
    log_info "To actually apply, run with: $(basename "$0") --apply"
    exit 0
fi

# Interactive confirmation requirement
echo ""
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
echo "                             DANGER / CRITICAL WARNING                        "
echo " You are about to write a new GPT partition table to /dev/block/mmcblk0.     "
echo " Any interruption or mistake can cause permanent, unrecoverable bricking.     "
echo " Protected partitions (BOOT, RECOVERY, EFS, PARAM, RADIO) will be preserved,  "
echo " but partitions 8-12 (CACHE, SYSTEM, HIDDEN, OTA, USERDATA) will be deleted! "
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
echo ""
read -r -p "Type exactly 'YES I HAVE A BACKUP AND WANT TO REPARTITION' to proceed: " CONFIRM_PHRASE
if [ "${CONFIRM_PHRASE}" != "YES I HAVE A BACKUP AND WANT TO REPARTITION" ]; then
    die "Confirmation phrase did not match. Aborting."
fi

log_info "Pushing target partition table to device..."
adb push "${TARGET_LAYOUT}" /tmp/new_partitions.sfdisk

log_info "Writing partition table with sfdisk..."
adb shell "${SFDISK_BIN} --force /dev/block/mmcblk0 < /tmp/new_partitions.sfdisk"

log_info "Informing kernel of partition changes (partx/blockdev)..."
adb shell "blockdev --rereadpt /dev/block/mmcblk0 2>/dev/null || partx -u /dev/block/mmcblk0 2>/dev/null || true"

# Verify protected partitions
log_info "Verifying integrity of protected partitions 1-7..."
TEMP_NEW=$(mktemp)
adb shell "${SFDISK_BIN} -d /dev/block/mmcblk0 2>/dev/null" > "${TEMP_NEW}"

for part_num in 1 2 3 4 5 6 7; do
    orig_line=$(grep "mmcblk0p${part_num} " "${ORIGINAL_LAYOUT}" | awk '{print $3,$4,$5,$6}')
    new_line=$(grep "mmcblk0p${part_num} " "${TEMP_NEW}" | awk '{print $3,$4,$5,$6}')
    if [ "${orig_line}" != "${new_line}" ]; then
        rm -f "${TEMP_NEW}"
        die "CRITICAL INTEGRITY FAILURE: Partition ${part_num} changed during repartitioning!"
    fi
done
rm -f "${TEMP_NEW}"

log_success "Repartitioning completed successfully! Protected partitions 1-7 remain 100% intact."
log_info "New rootfs partition is /dev/block/mmcblk0p8 (~14.5 GiB)."


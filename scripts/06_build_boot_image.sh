#!/usr/bin/env bash
# ==============================================================================
# NoteOS — 06_build_boot_image.sh
# Packages Android boot.img from compiled zImage, DTB, and initramfs ramdisk.
# Strictly enforces the 7.5 MiB (7,864,320 bytes) hardware partition limit.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/common.sh"

show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Packages boot.img and boot-debug.img using mkbootimg with device-specific offsets.
Rejects any output image exceeding the 7.5 MiB hardware limit.

OPTIONS:
  --help             Show this help message and exit
  --dry-run          Verify input paths and parameters without writing images
  --device <DEVICE>  Target device name (default: ${TARGET_DEVICE})

EOF
}

DRY_RUN=0
DEVICE="${TARGET_DEVICE}"

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
        --device)
            DEVICE="$2"
            shift 2
            ;;
        *)
            die "Unknown option: $1. Use --help for usage."
            ;;
    esac
done

DEVICE_CONF="${REPO_ROOT}/build/devices/${DEVICE}/device.conf"
if [ ! -f "${DEVICE_CONF}" ]; then
    die "Device configuration not found: ${DEVICE_CONF}"
fi

# shellcheck source=/dev/null
source "${DEVICE_CONF}"

OUT_DIR="${REPO_ROOT}/out/${DEVICE}"
ZIMAGE="${OUT_DIR}/zImage-dtb"
RAMDISK_RELEASE="${OUT_DIR}/initramfs.cpio.gz"
RAMDISK_DEBUG="${OUT_DIR}/initramfs-debug.cpio.gz"
BOOT_OUT="${OUT_DIR}/boot.img"
BOOT_DEBUG_OUT="${OUT_DIR}/boot-debug.img"

log_info "=== NoteOS: Boot Image Packaging (${DEVICE_NAME}) ==="
log_info "Partition BOOT limit: ${BOOT_MAX_BYTES} bytes (7.5 MiB)"

if [ "${DRY_RUN}" -eq 1 ]; then
    log_info "[DRY-RUN] Verified packaging parameters for ${DEVICE}."
    log_info "[DRY-RUN] Base offset: ${MKBOOTIMG_BASE}"
    log_info "[DRY-RUN] Pagesize   : ${MKBOOTIMG_PAGESIZE}"
    exit 0
fi

if [ ! -f "${ZIMAGE}" ]; then
    die "Kernel zImage-dtb not found at ${ZIMAGE}. Run scripts/04_build_kernel.sh first."
fi

if [ ! -f "${RAMDISK_RELEASE}" ]; then
    die "Release ramdisk not found at ${RAMDISK_RELEASE}. Run initramfs build first."
fi

package_and_verify() {
    local kernel_bin="$1"
    local ramdisk_bin="$2"
    local cmdline_str="$3"
    local out_img="$4"
    local desc="$5"

    log_info "Packaging ${desc}: $(basename "${out_img}")..."
    "${SCRIPT_DIR}/lib/mkbootimg.py" \
        --kernel "${kernel_bin}" \
        --ramdisk "${ramdisk_bin}" \
        --base "${MKBOOTIMG_BASE}" \
        --pagesize "${MKBOOTIMG_PAGESIZE}" \
        --kernel_offset "${MKBOOTIMG_KERNEL_OFFSET}" \
        --ramdisk_offset "${MKBOOTIMG_RAMDISK_OFFSET}" \
        --second_offset "${MKBOOTIMG_SECOND_OFFSET}" \
        --tags_offset "${MKBOOTIMG_TAGS_OFFSET}" \
        --header_version "${MKBOOTIMG_HEADER_VERSION}" \
        --cmdline "${cmdline_str}" \
        --output "${out_img}"

    local actual_size
    actual_size=$(stat -c%s "${out_img}")
    local margin=$((BOOT_MAX_BYTES - actual_size))

    if [ "${actual_size}" -gt "${BOOT_MAX_BYTES}" ]; then
        rm -f "${out_img}"
        die "CRITICAL: ${desc} size (${actual_size} bytes) EXCEEDS 7.5 MiB limit (${BOOT_MAX_BYTES} bytes) by $((actual_size - BOOT_MAX_BYTES)) bytes!"
    fi

    local sha
    sha=$(sha256sum "${out_img}" | awk '{print $1}')
    log_success "${desc} verified: ${actual_size} bytes (Margin: ${margin} bytes / $((margin / 1024)) KiB) | SHA256: ${sha}"
}

package_and_verify "${ZIMAGE}" "${RAMDISK_RELEASE}" "${CMDLINE_RELEASE}" "${BOOT_OUT}" "boot.img (Release)"

if [ -f "${RAMDISK_DEBUG}" ]; then
    package_and_verify "${ZIMAGE}" "${RAMDISK_DEBUG}" "${CMDLINE_DEBUG}" "${BOOT_DEBUG_OUT}" "boot-debug.img (Debug)"
fi

log_success "All boot images successfully packaged within 7.5 MiB budget."


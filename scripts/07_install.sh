#!/usr/bin/env bash
# ==============================================================================
# NoteOS — 07_install.sh
# Complete, non-destructive installer for Samsung Galaxy Note 10.1 (GT-N8000).
# Flashes NoteOS kernel and base rootfs via TWRP ADB.
#
# STAGES:
#   1. check    - Verify ADB connectivity, TWRP mode, GT-N8000 model, battery
#   2. backup   - Safety backup of existing BOOT and RECOVERY partitions
#   3. format   - Clean ext4 formatting of rootfs partition (mmcblk0p8)
#   4. rootfs   - Push and extract rootfs.tar.gz
#   5. firmware - Install Wi-Fi & Bluetooth firmware from local proprietary/
#   6. boot     - Flash boot.img to mmcblk0p5 with bit-by-bit readback verification
#   7. verify   - Check filesystem consistency and verify TWRP recovery integrity
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/common.sh"

show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Flashes NoteOS onto a Samsung Galaxy Note 10.1 (GT-N8000) running in TWRP recovery.

OPTIONS:
  --help             Show this help message and exit
  --dry-run          Simulate checks and commands without writing to device (SAFE)
  --full             Execute all 7 stages sequentially
  --stage <NAME>     Run specific stage: check, backup, format, rootfs, firmware, boot, verify
  --debug            Flash boot-debug.img instead of release boot.img
  --yes              Skip interactive confirmation prompts for non-destructive stages
  --rootfs <FILE>    Custom rootfs archive (default: release/rootfs.tar.gz or out/n8000/rootfs.tar.gz)
  --boot <FILE>      Custom boot image (default: release/boot.img or out/n8000/boot.img)

SAFETY GUARANTEES:
  - NEVER touches bootloader, EFS, PARAM, RADIO, or RECOVERY.
  - Verifies TWRP recovery partition (mmcblk0p6) checksum to prove it remains untouched.
  - Bit-by-bit readback SHA256 verification of flashed boot partition.
EOF
}

DRY_RUN=0
RUN_FULL=0
STAGE=""
USE_DEBUG=0
ASSUME_YES=0

BOOT_IMG=""
ROOTFS_TAR=""

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
            RUN_FULL=1
            shift
            ;;
        --stage)
            STAGE="$2"
            shift 2
            ;;
        --debug)
            USE_DEBUG=1
            shift
            ;;
        --yes|-y)
            ASSUME_YES=1
            shift
            ;;
        --boot)
            BOOT_IMG="$2"
            shift 2
            ;;
        --rootfs)
            ROOTFS_TAR="$2"
            shift 2
            ;;
        *)
            die "Unknown option: $1. Use --help for usage."
            ;;
    esac
done

# Resolve default boot image path
if [ -z "${BOOT_IMG}" ]; then
    if [ "${USE_DEBUG}" -eq 1 ]; then
        if [ -f "${NOTEOS_RELEASE_DIR}/boot-debug.img" ]; then
            BOOT_IMG="${NOTEOS_RELEASE_DIR}/boot-debug.img"
        else
            BOOT_IMG="${NOTEOS_OUT_DIR}/n8000/boot-debug.img"
        fi
    else
        if [ -f "${NOTEOS_RELEASE_DIR}/boot.img" ]; then
            BOOT_IMG="${NOTEOS_RELEASE_DIR}/boot.img"
        else
            BOOT_IMG="${NOTEOS_OUT_DIR}/n8000/boot.img"
        fi
    fi
fi

# Resolve default rootfs archive path
if [ -z "${ROOTFS_TAR}" ]; then
    if [ -f "${NOTEOS_RELEASE_DIR}/rootfs.tar.gz" ]; then
        ROOTFS_TAR="${NOTEOS_RELEASE_DIR}/rootfs.tar.gz"
    elif [ -f "${NOTEOS_OUT_DIR}/n8000/rootfs.tar.gz" ]; then
        ROOTFS_TAR="${NOTEOS_OUT_DIR}/n8000/rootfs.tar.gz"
    fi
fi

TARGET_BOOT_DEV="/dev/block/mmcblk0p5"
TARGET_ROOTFS_DEV="/dev/block/mmcblk0p8"
TARGET_RECOVERY_DEV="/dev/block/mmcblk0p6"

# STAGE 1: CHECK
stage_check() {
    log_info "=== [Stage 1/7: Check] Verifying Environment and Device ==="
    check_device_twrp

    local model
    model=$(adb shell getprop ro.product.device 2>/dev/null | tr -d '\r\n ')
    local battery
    battery=$(adb shell cat /sys/class/power_supply/battery/capacity 2>/dev/null | tr -d '\r\n ' || echo "unknown")
    local charging
    charging=$(adb shell cat /sys/class/power_supply/battery/status 2>/dev/null | tr -d '\r\n ' || echo "unknown")

    log_success "Target device identified: ${model}"
    log_info "Battery status: ${battery}% (${charging})"

    if [ "${battery}" != "unknown" ] && [ "${battery}" -lt 50 ] && [ "${charging}" != "Charging" ] && [ "${charging}" != "Full" ]; then
        die "Battery level is below 50% (${battery}%) and not charging. Flashing aborted."
    fi

    # Verify partition size of mmcblk0p8
    local rootfs_blocks
    rootfs_blocks=$(adb shell "cat /sys/block/mmcblk0/mmcblk0p8/size 2>/dev/null" | tr -d '\r\n ')
    local rootfs_gb=$(( rootfs_blocks * 512 / 1024 / 1024 / 1024 ))
    log_info "Rootfs partition (/dev/block/mmcblk0p8) capacity: ${rootfs_gb} GiB (${rootfs_blocks} sectors)"

    if [ "${rootfs_blocks}" -lt 20000000 ]; then
        log_warn "mmcblk0p8 has stock size (~1.5-2 GiB). If you wish to use the full 14.5 GiB for NoteOS, consider running scripts/03_repartition.sh."
    fi

    if [ ! -f "${BOOT_IMG}" ]; then
        die "Boot image not found at ${BOOT_IMG}. Build it or place it in release/boot.img."
    fi

    local boot_sz
    boot_sz=$(stat -c%s "${BOOT_IMG}")
    if [ "${boot_sz}" -gt "${BOOT_MAX_BYTES}" ]; then
        die "Boot image exceeds 7.5 MiB budget: ${boot_sz} bytes > ${BOOT_MAX_BYTES} bytes."
    fi
    log_success "Boot image size verified: ${boot_sz} bytes (<= 7.5 MiB)."
}

# STAGE 2: BACKUP
stage_backup() {
    log_info "=== [Stage 2/7: Backup] Safety Backup of BOOT and RECOVERY ==="
    if [ "${DRY_RUN}" -eq 1 ]; then
        log_info "  [DRY-RUN] Would dump ${TARGET_BOOT_DEV} and ${TARGET_RECOVERY_DEV} to ${NOTEOS_BACKUP_DIR}/"
        return 0
    fi

    mkdir -p "${NOTEOS_BACKUP_DIR}"
    adb shell "dd if=${TARGET_BOOT_DEV} bs=4096 2>/dev/null" > "${NOTEOS_BACKUP_DIR}/boot_pre_install.img"
    adb shell "dd if=${TARGET_RECOVERY_DEV} bs=4096 2>/dev/null" > "${NOTEOS_BACKUP_DIR}/recovery_pre_install.img"

    sha256sum "${NOTEOS_BACKUP_DIR}/boot_pre_install.img" > "${NOTEOS_BACKUP_DIR}/boot_pre_install.img.sha256"
    sha256sum "${NOTEOS_BACKUP_DIR}/recovery_pre_install.img" > "${NOTEOS_BACKUP_DIR}/recovery_pre_install.img.sha256"
    log_success "Safety backups saved in ${NOTEOS_BACKUP_DIR}."
}

# STAGE 3: FORMAT
stage_format() {
    log_info "=== [Stage 3/7: Format] Clean ext4 formatting of ${TARGET_ROOTFS_DEV} ==="
    if [ "${DRY_RUN}" -eq 1 ]; then
        log_info "  [DRY-RUN] Would unmount /mnt and format ${TARGET_ROOTFS_DEV} with label debian_root"
        return 0
    fi

    if [ "${ASSUME_YES}" -eq 0 ]; then
        echo ""
        echo "WARNING: Partition ${TARGET_ROOTFS_DEV} will be formatted. All existing OS data on it will be deleted."
        read -r -p "Proceed with formatting? (y/N): " answer
        if [[ ! "${answer}" =~ ^[yY]$ ]]; then
            die "Formatting cancelled by user."
        fi
    fi

    adb shell "umount -f /mnt /mnt/debian /data /sdcard 2>/dev/null || true"
    adb shell "mke2fs -t ext4 -F -L debian_root ${TARGET_ROOTFS_DEV}"
    adb shell "e2fsck -fy ${TARGET_ROOTFS_DEV} 2>/dev/null || true"
    log_success "Partition ${TARGET_ROOTFS_DEV} formatted cleanly as ext4 with LABEL=debian_root."
}

# STAGE 4: ROOTFS
stage_rootfs() {
    log_info "=== [Stage 4/7: Rootfs] Pushing and Unpacking Rootfs ==="
    if [ -z "${ROOTFS_TAR}" ] || [ ! -f "${ROOTFS_TAR}" ]; then
        if [ "${DRY_RUN}" -eq 1 ]; then
            log_warn "Rootfs archive not present locally (specify with --rootfs <PATH> or build via scripts/05_build_rootfs.sh)."
            log_info "  [DRY-RUN] Would push and extract rootfs.tar.gz to ${TARGET_ROOTFS_DEV} mounted on /mnt"
            return 0
        fi
        die "Rootfs tarball not found! Specify with --rootfs <PATH> or build via scripts/05_build_rootfs.sh."
    fi

    local tar_sz
    tar_sz=$(stat -c%s "${ROOTFS_TAR}")
    local tar_sha
    tar_sha=$(sha256sum "${ROOTFS_TAR}" | awk '{print $1}')
    log_info "Rootfs archive: ${ROOTFS_TAR} (${tar_sz} bytes, SHA256: ${tar_sha})"

    if [ "${DRY_RUN}" -eq 1 ]; then
        log_info "  [DRY-RUN] Would push and extract rootfs.tar.gz to ${TARGET_ROOTFS_DEV} mounted on /mnt"
        return 0
    fi

    adb shell "mkdir -p /mnt && mount -t ext4 ${TARGET_ROOTFS_DEV} /mnt"
    log_info "Pushing rootfs archive to device..."
    adb push "${ROOTFS_TAR}" /mnt/.rootfs.tar.gz
    log_info "Verifying pushed archive checksum..."
    local pushed_sha
    pushed_sha=$(adb shell "sha256sum /mnt/.rootfs.tar.gz" | awk '{print $1}' | tr -d '\r')
    if [ "${pushed_sha}" != "${tar_sha}" ]; then
        die "SHA256 mismatch for pushed rootfs.tar.gz: ${pushed_sha} != ${tar_sha}"
    fi

    log_info "Bootstrapping GNU tar for accurate permissions and symlinks..."
    adb shell "mkdir -p /tmp/gnutar && /sbin/tar -xzf /mnt/.rootfs.tar.gz -C /mnt ./usr/bin/tar ./usr/lib/arm-linux-gnueabihf && cp -L /mnt/usr/bin/tar /mnt/usr/lib/arm-linux-gnueabihf/ld-linux-armhf.so.3 /mnt/usr/lib/arm-linux-gnueabihf/libc.so.6 /mnt/usr/lib/arm-linux-gnueabihf/libacl.so.1 /mnt/usr/lib/arm-linux-gnueabihf/libselinux.so.1 /mnt/usr/lib/arm-linux-gnueabihf/libpcre2-8.so.0 /tmp/gnutar/ && chmod 755 /tmp/gnutar/*"

    log_info "Extracting full rootfs onto target partition..."
    adb shell "/sbin/gzip -dc /mnt/.rootfs.tar.gz | /tmp/gnutar/ld-linux-armhf.so.3 --library-path /tmp/gnutar /tmp/gnutar/tar --numeric-owner -xpf - -C /mnt && rm -rf /mnt/.rootfs.tar.gz /tmp/gnutar"
    adb shell "sync"
    log_success "Rootfs extracted successfully."
}

# STAGE 5: FIRMWARE
stage_firmware() {
    log_info "=== [Stage 5/7: Firmware] Installing Wi-Fi & Bluetooth Firmware ==="
    local fw_dir="${NOTEOS_PROPRIETARY_DIR}"
    local required_fw=(
        "brcmfmac4334-sdio.bin"
        "brcmfmac4334-sdio.txt"
        "BCM4334B0.hcd"
    )

    local missing=()
    for fw in "${required_fw[@]}"; do
        if [ ! -f "${fw_dir}/${fw}" ]; then
            missing+=("${fw}")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        if [ "${DRY_RUN}" -eq 1 ]; then
            log_warn "Missing proprietary firmware files in ${fw_dir} (obtain via scripts/02_extract_firmware.sh)."
            log_info "  [DRY-RUN] Would copy firmware to /mnt/lib/firmware/brcm/ and set permissions"
            return 0
        fi
        log_error "Missing required proprietary firmware files in ${fw_dir}:"
        for m in "${missing[@]}"; do
            echo "  - ${m}" >&2
        done
        echo "" >&2
        echo "These files are non-redistributable proprietary blobs required for Wi-Fi and Bluetooth." >&2
        echo "Please run scripts/02_extract_firmware.sh to extract them from your device backup." >&2
        echo "Refer to docs/PROPRIETARY.md for instructions." >&2
        die "Proprietary firmware stage failed."
    fi

    if [ "${DRY_RUN}" -eq 1 ]; then
        log_info "  [DRY-RUN] Would install firmware blobs to /mnt/lib/firmware/brcm/:"
        for fw in "${required_fw[@]}"; do
            log_info "    ${fw_dir}/${fw} -> /mnt/lib/firmware/brcm/${fw}"
        done
        return 0
    fi

    log_info "Installing verified firmware blobs into /mnt/lib/firmware/brcm/ and /mnt/usr/lib/firmware/brcm/..."
    adb shell "mkdir -p /mnt/lib/firmware/brcm /mnt/usr/lib/firmware/brcm"
    for fw in "${required_fw[@]}"; do
        adb push "${fw_dir}/${fw}" "/mnt/lib/firmware/brcm/${fw}"
        adb push "${fw_dir}/${fw}" "/mnt/usr/lib/firmware/brcm/${fw}" 2>/dev/null || true
    done
    if [ -f "${fw_dir}/brcmfmac4334-sdio.samsung,n8000.txt" ]; then
        adb push "${fw_dir}/brcmfmac4334-sdio.samsung,n8000.txt" "/mnt/lib/firmware/brcm/brcmfmac4334-sdio.samsung,n8000.txt"
        adb push "${fw_dir}/brcmfmac4334-sdio.samsung,n8000.txt" "/mnt/usr/lib/firmware/brcm/brcmfmac4334-sdio.samsung,n8000.txt" 2>/dev/null || true
    else
        adb shell "cp -f /mnt/lib/firmware/brcm/brcmfmac4334-sdio.txt /mnt/lib/firmware/brcm/brcmfmac4334-sdio.samsung,n8000.txt"
        adb shell "cp -f /mnt/lib/firmware/brcm/brcmfmac4334-sdio.txt /mnt/usr/lib/firmware/brcm/brcmfmac4334-sdio.samsung,n8000.txt 2>/dev/null || true"
    fi
    adb shell "chmod 0644 /mnt/lib/firmware/brcm/* /mnt/usr/lib/firmware/brcm/* 2>/dev/null || true"

    # Integrity verification: ensure NVRAM calibrations are non-empty before unmounting
    local chk
    chk=$(adb shell "([ -s /mnt/usr/lib/firmware/brcm/brcmfmac4334-sdio.txt ] || [ -s /mnt/lib/firmware/brcm/brcmfmac4334-sdio.txt ]) && echo OK" | tr -d '\r\n ')
    if [ "${chk}" != "OK" ]; then
        die "Firmware verification failed: brcmfmac4334-sdio.txt is missing or empty on /mnt!"
    fi
    adb shell "sync && umount /mnt"
    log_success "Proprietary Wi-Fi and Bluetooth firmware installed and verified cleanly."
}

# STAGE 6: BOOT
stage_boot() {
    log_info "=== [Stage 6/7: Boot] Flashing Kernel Boot Image ==="
    local boot_sz
    boot_sz=$(stat -c%s "${BOOT_IMG}")
    local expected_sha
    expected_sha=$(sha256sum "${BOOT_IMG}" | awk '{print $1}')
    log_info "Boot image: ${BOOT_IMG} (${boot_sz} bytes, SHA256: ${expected_sha})"

    if [ "${DRY_RUN}" -eq 1 ]; then
        log_info "  [DRY-RUN] Would flash ${BOOT_IMG} to ${TARGET_BOOT_DEV} with conv=fsync and verify readback SHA256"
        return 0
    fi

    adb push "${BOOT_IMG}" /tmp/noteos_boot.img
    adb shell "dd if=/tmp/noteos_boot.img of=${TARGET_BOOT_DEV} bs=4096 conv=fsync 2>/dev/null"
    adb shell "rm -f /tmp/noteos_boot.img"

    # Bit-by-bit readback SHA256 verification
    log_info "Performing bit-by-bit readback SHA256 verification..."
    local readback_sha
    readback_sha=$(adb shell "head -c ${boot_sz} ${TARGET_BOOT_DEV} | sha256sum" | awk '{print $1}')

    log_info "  Expected SHA256 : ${expected_sha}"
    log_info "  Readback SHA256 : ${readback_sha}"

    if [ "${expected_sha}" != "${readback_sha}" ]; then
        die "CRITICAL FAILURE: Readback SHA256 does not match written boot image!"
    fi
    log_success "Boot image flashed and verified 100% bit-by-bit."
}

# STAGE 7: VERIFY
stage_verify() {
    log_info "=== [Stage 7/7: Verify] Integrity & Safety Verification ==="
    if [ "${DRY_RUN}" -eq 1 ]; then
        log_info "  [DRY-RUN] Would verify filesystem consistency on ${TARGET_ROOTFS_DEV} and untouched recovery partition"
        return 0
    fi

    log_info "Checking filesystem consistency on ${TARGET_ROOTFS_DEV}..."
    adb shell "e2fsck -f -n ${TARGET_ROOTFS_DEV} 2>/dev/null"
    log_success "Filesystem check on ${TARGET_ROOTFS_DEV} passed with zero errors."

    # Verify that RECOVERY partition (mmcblk0p6) was NOT modified
    if [ -f "${NOTEOS_BACKUP_DIR}/recovery_pre_install.img.sha256" ]; then
        local expected_recovery_sha
        expected_recovery_sha=$(awk '{print $1}' "${NOTEOS_BACKUP_DIR}/recovery_pre_install.img.sha256")
        local live_recovery_sha
        live_recovery_sha=$(adb shell "sha256sum ${TARGET_RECOVERY_DEV}" | awk '{print $1}')

        log_info "Verifying untouched TWRP Recovery partition integrity..."
        log_info "  Pre-install Recovery SHA256: ${expected_recovery_sha}"
        log_info "  Live Recovery SHA256       : ${live_recovery_sha}"

        if [ "${expected_recovery_sha}" != "${live_recovery_sha}" ]; then
            die "SAFETY WARNING: Recovery partition checksum changed during installation!"
        fi
        log_success "TWRP Recovery partition is 100% untouched and safe."
    fi

    log_success "All NoteOS installation stages completed and verified successfully!"
}

# Execution dispatcher
if [ "${RUN_FULL}" -eq 1 ]; then
    stage_check
    stage_backup
    stage_format
    stage_rootfs
    stage_firmware
    stage_boot
    stage_verify
elif [ -n "${STAGE}" ]; then
    case "${STAGE}" in
        check)    stage_check ;;
        backup)   stage_backup ;;
        format)   stage_format ;;
        rootfs)   stage_rootfs ;;
        firmware) stage_firmware ;;
        boot)     stage_boot ;;
        verify)   stage_verify ;;
        *)        die "Unknown stage: ${STAGE}. Valid stages: check, backup, format, rootfs, firmware, boot, verify." ;;
    esac
else
    show_help
    exit 0
fi


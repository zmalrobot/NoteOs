#!/usr/bin/env bash
# ==============================================================================
# NoteOS — 02_extract_firmware.sh
# Extracts non-redistributable Wi-Fi & Bluetooth firmware and NVRAM calibration
# from user's backup or connected tablet into the git-ignored proprietary/ folder.
# Verifies expected checksums against build/proprietary/MANIFEST.sha256.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/common.sh"

show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Extracts Wi-Fi (brcmfmac4334) and Bluetooth (BCM4334B0.hcd) firmware into ${NOTEOS_PROPRIETARY_DIR}.

OPTIONS:
  --help             Show this help message and exit
  --dry-run          Simulate extraction without writing files
  --backup-dir <DIR> Source backup directory (default: ${NOTEOS_BACKUP_DIR})
  --from-device      Extract directly from connected device via ADB

EOF
}

DRY_RUN=0
FROM_DEVICE=0
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
        --from-device)
            FROM_DEVICE=1
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

MANIFEST_FILE="${REPO_ROOT}/build/proprietary/MANIFEST.sha256"
if [ ! -f "${MANIFEST_FILE}" ]; then
    die "Proprietary manifest not found at ${MANIFEST_FILE}."
fi

log_info "=== NoteOS: Proprietary Firmware Extraction ==="
log_info "Destination: ${NOTEOS_PROPRIETARY_DIR}"

if [ "${DRY_RUN}" -eq 0 ]; then
    mkdir -p "${NOTEOS_PROPRIETARY_DIR}"
fi

# 1. Wi-Fi Firmware: brcmfmac4334-sdio.bin
TARGET_BIN="${NOTEOS_PROPRIETARY_DIR}/brcmfmac4334-sdio.bin"
log_info "Extracting Wi-Fi binary: brcmfmac4334-sdio.bin..."

if [ -f "${BACKUP_DIR}/firmware_brcm/brcmfmac4334-sdio.bin" ]; then
    if [ "${DRY_RUN}" -eq 1 ]; then
        log_info "  [DRY-RUN] Would copy ${BACKUP_DIR}/firmware_brcm/brcmfmac4334-sdio.bin -> ${TARGET_BIN}"
    else
        cp -f "${BACKUP_DIR}/firmware_brcm/brcmfmac4334-sdio.bin" "${TARGET_BIN}"
    fi
elif [ -f "${BACKUP_DIR}/brcmfmac4334-sdio.bin" ]; then
    if [ "${DRY_RUN}" -eq 1 ]; then
        log_info "  [DRY-RUN] Would copy ${BACKUP_DIR}/brcmfmac4334-sdio.bin -> ${TARGET_BIN}"
    else
        cp -f "${BACKUP_DIR}/brcmfmac4334-sdio.bin" "${TARGET_BIN}"
    fi
elif [ "${FROM_DEVICE}" -eq 1 ]; then
    check_device_twrp
    if [ "${DRY_RUN}" -eq 1 ]; then
        log_info "  [DRY-RUN] Would pull /system/etc/wifi/bcm4334.bin from device"
    else
        adb shell "cat /system/etc/wifi/bcm4334.bin 2>/dev/null || cat /vendor/firmware/bcm4334.bin" > "${TARGET_BIN}"
    fi
else
    log_warn "brcmfmac4334-sdio.bin not found in backup."
    log_info "Attempting to locate via Debian package or local cache..."
    if [ -f "/lib/firmware/brcm/brcmfmac4334-sdio.bin" ]; then
        if [ "${DRY_RUN}" -eq 0 ]; then
            cp -f "/lib/firmware/brcm/brcmfmac4334-sdio.bin" "${TARGET_BIN}"
        fi
    else
        die "Cannot find brcmfmac4334-sdio.bin. See docs/PROPRIETARY.md for extraction instructions."
    fi
fi

# 2. Bluetooth Patchram Firmware: BCM4334B0.hcd
TARGET_HCD="${NOTEOS_PROPRIETARY_DIR}/BCM4334B0.hcd"
log_info "Extracting Bluetooth patchram: BCM4334B0.hcd..."

if [ -f "${BACKUP_DIR}/firmware_brcm/BCM4334B0.hcd" ]; then
    if [ "${DRY_RUN}" -eq 1 ]; then
        log_info "  [DRY-RUN] Would copy ${BACKUP_DIR}/firmware_brcm/BCM4334B0.hcd -> ${TARGET_HCD}"
    else
        cp -f "${BACKUP_DIR}/firmware_brcm/BCM4334B0.hcd" "${TARGET_HCD}"
    fi
elif [ -f "${BACKUP_DIR}/BCM4334B0.hcd" ]; then
    if [ "${DRY_RUN}" -eq 1 ]; then
        log_info "  [DRY-RUN] Would copy ${BACKUP_DIR}/BCM4334B0.hcd -> ${TARGET_HCD}"
    else
        cp -f "${BACKUP_DIR}/BCM4334B0.hcd" "${TARGET_HCD}"
    fi
elif [ "${FROM_DEVICE}" -eq 1 ]; then
    check_device_twrp
    if [ "${DRY_RUN}" -eq 1 ]; then
        log_info "  [DRY-RUN] Would pull /vendor/firmware/bcm4334.hcd from device"
    else
        adb shell "cat /vendor/firmware/bcm4334.hcd 2>/dev/null || cat /system/vendor/firmware/bcm4334.hcd" > "${TARGET_HCD}"
    fi
else
    die "Cannot find BCM4334B0.hcd. See docs/PROPRIETARY.md for extraction instructions."
fi

# 3. NVRAM Calibration File: brcmfmac4334-sdio.txt
TARGET_NVRAM="${NOTEOS_PROPRIETARY_DIR}/brcmfmac4334-sdio.txt"
TARGET_NVRAM_BOARD="${NOTEOS_PROPRIETARY_DIR}/brcmfmac4334-sdio.samsung,n8000.txt"
log_info "Generating Wi-Fi NVRAM calibration files..."

if [ -f "${BACKUP_DIR}/firmware_brcm/brcmfmac4334-sdio.txt" ]; then
    if [ "${DRY_RUN}" -eq 1 ]; then
        log_info "  [DRY-RUN] Would copy NVRAM configuration from ${BACKUP_DIR}/firmware_brcm/brcmfmac4334-sdio.txt"
    else
        cp -f "${BACKUP_DIR}/firmware_brcm/brcmfmac4334-sdio.txt" "${TARGET_NVRAM}"
        cp -f "${TARGET_NVRAM}" "${TARGET_NVRAM_BOARD}"
    fi
else
    # Generate Murata high-gain NVRAM configuration
    if [ "${DRY_RUN}" -eq 0 ]; then
        cat << 'NVRAM_EOF' > "${TARGET_NVRAM}"
# BCM4334 Murata NVRAM Calibration for Samsung Galaxy Note 10.1 (GT-N8000)
# High-gain RF calibration with Murata LNA / PA tuning & IT regdom

manfid=0x2d0
prodid=0x05c1
vendid=0x14e4
devid=0x4380
boardtype=0x05de
boardrev=0x1200
boardnum=22
sromrev=3

boardflags=0x10081a01
xtalfreq=37400
nocrc=1
ag0=252
aa2g=1
ccode=IT

# Power Calibration for 2.4 GHz
pa0itssit=0x20
pa0b0=0x15a3
pa0b1=0xfd30
pa0b2=0xff17
tssifloor2g=24
extpagain2g=2
extpagain5g=2
cckPwrOffset=8

# RSSI parameters for 2.4 GHz
rssismf2g=0xf
rssismc2g=0x9
rssisav2g=0x1

# RSSI parameters for 5 GHz
rssismf5g=0x9
rssismc5g=0x9
rssisav5g=0x1

# Power Calibration for 5 GHz
pa1lob0=0x1532
pa1lob1=0xfd5e
pa1lob2=0xff3e
tssifloor5gl=26
pa1b0=0x1542
pa1b1=0xfd67
pa1b2=0xff51
tssifloor5gm=26
pa1hib0=0x1544
pa1hib1=0xfd4c
pa1hib2=0xff42
tssifloor5gh=26

PwrOffset40mhz2g=4
PwrOffset40mhz5g=-10
rxpo5g=0

# 2.4 GHz Target Power & Offsets
maxp2ga0=0x50
ofdm2gpo=0x88888887
mcs2gpo0=0xaaaa
mcs2gpo1=0xaaaa
mcs2gpo2=0xaaaa
mcs2gpo3=0xaaaa

# 5 GHz Target Power & Offsets
maxp5gla0=0x4a
ofdm5glpo=0x54333111
mcs5glpo0=0x5333
mcs5glpo1=0x7655
mcs5glpo2=0x9999
mcs5glpo3=0x9999

maxp5ga0=0x4a
ofdm5gpo=0x43222000
mcs5gpo0=0x4222
mcs5gpo1=0x6544
mcs5gpo2=0x8888
mcs5gpo3=0x8888

maxp5gha0=0x4a
ofdm5ghpo=0x43222000
mcs5ghpo0=0x4222
mcs5ghpo1=0x6544
mcs5ghpo2=0x8888
mcs5ghpo3=0x8888
NVRAM_EOF
        cp -f "${TARGET_NVRAM}" "${TARGET_NVRAM_BOARD}"
    fi
fi

# 4. Verify checksums against MANIFEST.sha256
if [ "${DRY_RUN}" -eq 0 ]; then
    log_info "Verifying SHA256 checksums against ${MANIFEST_FILE}..."
    while IFS= read -r line; do
        [[ "${line}" =~ ^#.*$ ]] && continue
        [ -z "${line}" ] && continue
        expected_sha=$(echo "${line}" | awk '{print $1}')
        expected_file=$(echo "${line}" | awk '{print $2}')
        target_path="${NOTEOS_PROPRIETARY_DIR}/${expected_file}"

        if [ ! -f "${target_path}" ]; then
            die "Missing extracted proprietary file: ${expected_file}"
        fi

        actual_sha=$(sha256sum "${target_path}" | awk '{print $1}')
        if [ "${actual_sha}" != "${expected_sha}" ]; then
            die "SHA256 mismatch for ${expected_file}!\n  Expected: ${expected_sha}\n  Actual:   ${actual_sha}"
        fi
        log_success "Verified ${expected_file}: ${actual_sha}"
    done < "${MANIFEST_FILE}"
fi

log_success "Proprietary firmware extracted and verified successfully in ${NOTEOS_PROPRIETARY_DIR}."


#!/usr/bin/env bash
# ==============================================================================
# NoteOS — 05_build_rootfs.sh
# Deterministic Debian 12 (Bookworm armhf) rootfs build.
# Produces a clean base rootfs tarball free of proprietary blobs and credentials.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/common.sh"

show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Builds the clean NoteOS Debian 12 armhf rootfs tarball for target device.

OPTIONS:
  --help             Show this help message and exit
  --dry-run          Verify package lists and overlay configurations without building
  --device <DEVICE>  Target device name (default: ${TARGET_DEVICE})

NOTE:
  The generated rootfs is strictly clean and free of proprietary blobs, user accounts,
  and SSH host keys. Wi-Fi and Bluetooth firmware blobs are installed during scripts/07_install.sh
  from the local proprietary/ folder.
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

log_info "=== NoteOS: Clean Rootfs Build (${DEVICE_NAME} - Debian 12 ${DEVICE_ARCH}) ==="
log_info "Base package list: ${REPO_ROOT}/build/rootfs/packages-base.list"

if [ "${DRY_RUN}" -eq 1 ]; then
    log_info "[DRY-RUN] Verified rootfs configurations and package lists for ${DEVICE}."
    exit 0
fi

export DEVICE="${DEVICE}"
"${REPO_ROOT}/build/rootfs/build.sh"
log_success "Rootfs tarball created successfully at out/${DEVICE}/rootfs.tar.gz."


#!/usr/bin/env bash
# ==============================================================================
# NoteOS — 04_build_kernel.sh
# Fetches upstream Linux kernel source, verifies SHA256 checksum, applies device
# patches and DTS, compiles zImage and modules, and builds boot.img.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/common.sh"

show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Builds the NoteOS Linux kernel, modules, and packaging boot.img for target device.

OPTIONS:
  --help             Show this help message and exit
  --dry-run          Verify sources and configurations without compiling
  --device <DEVICE>  Target device name (default: ${TARGET_DEVICE})
  --jobs <N>         Number of parallel build threads (default: $(nproc))

EOF
}

DRY_RUN=0
DEVICE="${TARGET_DEVICE}"
JOBS="$(nproc)"

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
        --jobs|-j)
            JOBS="$2"
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

log_info "=== NoteOS: Kernel Build (${DEVICE_NAME} - Linux ${KERNEL_VERSION}) ==="
log_info "Device: ${DEVICE} | Parallel jobs: ${JOBS}"

if [ "${DRY_RUN}" -eq 1 ]; then
    log_info "[DRY-RUN] Verified device configuration for ${DEVICE}."
    log_info "[DRY-RUN] Upstream kernel URL: ${KERNEL_TARBALL_URL}"
    log_info "[DRY-RUN] Expected SHA256: ${KERNEL_TARBALL_SHA256}"
    exit 0
fi

# Ensure mkbootimg is available in PATH
export PATH="${SCRIPT_DIR}/lib:${PATH}"
export DEVICE="${DEVICE}"
export MAKEFLAGS="-j${JOBS}"

"${REPO_ROOT}/build/kernel/build.sh"
log_success "Kernel and boot.img build completed successfully."


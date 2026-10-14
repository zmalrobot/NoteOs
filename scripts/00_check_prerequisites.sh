#!/usr/bin/env bash
# ==============================================================================
# NoteOS — 00_check_prerequisites.sh
# Verifies host tools, disk space, and target device TWRP readiness.
# Optional: Installs pre-commit cleanliness hook.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/common.sh"

show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Checks host development tools, available disk space, and tablet connectivity in TWRP.

OPTIONS:
  --help             Show this help message and exit
  --install-hooks    Install git pre-commit hook (runs check_repo_clean.sh)
  --skip-device      Check only host tools and disk space without probing device

EOF
}

INSTALL_HOOKS=0
SKIP_DEVICE=0

for arg in "$@"; do
    case "${arg}" in
        --help|-h)
            show_help
            exit 0
            ;;
        --install-hooks)
            INSTALL_HOOKS=1
            ;;
        --skip-device)
            SKIP_DEVICE=1
            ;;
        *)
            die "Unknown option: ${arg}. Use --help for usage."
            ;;
    esac
done

if [ "${INSTALL_HOOKS}" -eq 1 ]; then
    log_info "Installing git pre-commit hook..."
    HOOK_PATH="${REPO_ROOT}/.git/hooks/pre-commit"
    mkdir -p "${REPO_ROOT}/.git/hooks"
    cat << 'HOOK_EOF' > "${HOOK_PATH}"
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
"${REPO_ROOT}/scripts/lib/check_repo_clean.sh"
HOOK_EOF
    chmod +x "${HOOK_PATH}"
    log_success "Pre-commit hook installed at ${HOOK_PATH}."
    exit 0
fi

log_info "=== NoteOS: Checking Host Prerequisites ==="

# Check essential host tools
REQUIRED_TOOLS=(
    "bash"
    "git"
    "tar"
    "gzip"
    "sha256sum"
    "awk"
    "grep"
    "sed"
    "make"
    "patch"
    "python3"
    "adb"
)

MISSING_TOOLS=()
for tool in "${REQUIRED_TOOLS[@]}"; do
    if command -v "${tool}" >/dev/null 2>&1; then
        printf "  [OK] %-15s found (%s)\n" "${tool}" "$(command -v "${tool}")"
    else
        printf "  [MISSING] %-15s NOT FOUND\n" "${tool}"
        MISSING_TOOLS+=("${tool}")
    fi
done

# Check container engine (podman or docker)
if command -v podman >/dev/null 2>&1; then
    printf "  [OK] %-15s found (%s)\n" "container engine" "podman"
elif command -v docker >/dev/null 2>&1; then
    printf "  [OK] %-15s found (%s)\n" "container engine" "docker"
else
    log_warn "Neither podman nor docker found. Building rootfs/kernel will require native arm cross-toolchain and debootstrap."
fi

if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
    die "Missing required host tools: ${MISSING_TOOLS[*]}. Please install them before proceeding."
fi

# Check free disk space (require at least 8 GB)
FREE_KB=$(df -P "${REPO_ROOT}" | awk 'NR==2 {print $4}')
FREE_GB=$((FREE_KB / 1024 / 1024))
if [ "${FREE_GB}" -lt 8 ]; then
    die "Insufficient free disk space: ${FREE_GB} GB available. NoteOS build requires at least 8 GB free."
fi
log_success "Disk space check passed: ${FREE_GB} GB available."

# Check device connectivity
if [ "${SKIP_DEVICE}" -eq 0 ]; then
    log_info "=== Checking Device Status via ADB ==="
    if ! command -v adb >/dev/null 2>&1; then
        log_warn "adb not found; skipping device check."
    else
        DEV_STATE=$(adb get-state 2>/dev/null || echo "disconnected")
        if [ "${DEV_STATE}" != "recovery" ]; then
            log_warn "Device is not connected in TWRP recovery mode (state: ${DEV_STATE})."
            log_warn "Connect GT-N8000 via USB and boot into TWRP to perform backup or installation."
        else
            DEV_MODEL=$(adb shell getprop ro.product.device 2>/dev/null | tr -d '\r\n ' || true)
            BATTERY_CAP=$(adb shell cat /sys/class/power_supply/battery/capacity 2>/dev/null | tr -d '\r\n ' || echo "unknown")
            log_success "Device connected in TWRP recovery."
            log_info "  Reported model: ${DEV_MODEL}"
            log_info "  Battery level : ${BATTERY_CAP}%"
            if [ "${BATTERY_CAP}" != "unknown" ] && [ "${BATTERY_CAP}" -lt 50 ]; then
                log_warn "Battery level is below 50% (${BATTERY_CAP}%). Please charge device before flashing."
            fi
        fi
    fi
fi

log_success "All prerequisites verified successfully."


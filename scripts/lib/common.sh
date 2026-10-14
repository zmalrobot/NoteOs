#!/usr/bin/env bash
# ==============================================================================
# NoteOS — Common Functions and Definitions (scripts/lib/common.sh)
# ==============================================================================
set -euo pipefail

# Determine repository root relative to this script
SCRIPT_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_LIB_DIR}/../.." && pwd)"

# Configurable paths with environment overrides
NOTEOS_WORKDIR="${NOTEOS_WORKDIR:-${REPO_ROOT}/.work}"
NOTEOS_BACKUP_DIR="${NOTEOS_BACKUP_DIR:-${REPO_ROOT}/../NoteOs-private/backup}"
NOTEOS_PROPRIETARY_DIR="${NOTEOS_PROPRIETARY_DIR:-${REPO_ROOT}/proprietary}"
NOTEOS_RELEASE_DIR="${NOTEOS_RELEASE_DIR:-${REPO_ROOT}/release}"
NOTEOS_OUT_DIR="${NOTEOS_OUT_DIR:-${REPO_ROOT}/out}"

# Device constants
TARGET_DEVICE="${DEVICE:-n8000}"
EXPECTED_DEVICE_MODEL="p4noterf"
EXPECTED_PRODUCT_DEVICE="GT-N8000"
BOOT_MAX_BYTES=7864320 # 7.5 MiB = 7,864,320 bytes

# Terminal Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    printf "${BLUE}[INFO]${NC} %s\n" "$*"
}

log_success() {
    printf "${GREEN}[OK]${NC} %s\n" "$*"
}

log_warn() {
    printf "${YELLOW}[WARN]${NC} %s\n" "$*"
}

log_error() {
    printf "${RED}[ERROR]${NC} %s\n" "$*" >&2
}

die() {
    log_error "$*"
    exit 1
}

# Pre-flight device check via ADB in TWRP recovery
check_device_twrp() {
    if ! command -v adb >/dev/null 2>&1; then
        die "adb tool is not installed or not in PATH."
    fi

    local dev_state
    dev_state=$(adb get-state 2>/dev/null || echo "disconnected")
    if [ "${dev_state}" != "recovery" ]; then
        die "Target device is not connected in TWRP recovery mode (Current state: ${dev_state}). Please boot into TWRP."
    fi

    local dev_model
    dev_model=$(adb shell getprop ro.product.device 2>/dev/null | tr -d '\r\n ' || true)
    if [ "${dev_model}" != "${EXPECTED_DEVICE_MODEL}" ] && [ "${dev_model}" != "${EXPECTED_PRODUCT_DEVICE}" ]; then
        die "Unsupported device connected: '${dev_model}'. Expected '${EXPECTED_DEVICE_MODEL}' / '${EXPECTED_PRODUCT_DEVICE}'."
    fi
}


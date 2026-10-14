#!/usr/bin/env bash
# ==============================================================================
# NoteOS — Repository Cleanliness and Privacy Guard (scripts/lib/check_repo_clean.sh)
# Ensures zero private data, zero proprietary blobs, zero leaks in git tree or release
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"

log_info "Running NoteOS repository cleanliness and confidentiality audit..."
FAILED=0

# ------------------------------------------------------------------------------
# Check 1: File size limit (GitHub enforces 100MB limit; NoteOS requires <= 50MB)
# ------------------------------------------------------------------------------
log_info "Check 1: Verifying no tracked files exceed 50 MiB..."
MAX_BYTES=$((50 * 1024 * 1024))
while IFS= read -r file; do
    [ -f "${REPO_ROOT}/${file}" ] || continue
    sz=$(stat -c%s "${REPO_ROOT}/${file}")
    if [ "${sz}" -gt "${MAX_BYTES}" ]; then
        log_error "File exceeds 50 MiB limit: ${file} (${sz} bytes)"
        FAILED=1
    fi
done < <(cd "${REPO_ROOT}" && git ls-files 2>/dev/null || find . -type f -not -path '*/.*' -not -path './release/rootfs*')

# ------------------------------------------------------------------------------
# Check 2: Forbidden file patterns in git tracking
# ------------------------------------------------------------------------------
log_info "Check 2: Scanning for forbidden tracked file patterns..."
FORBIDDEN_PATTERNS=(
    '\.pit$'
    '\.tar\.md5$'
    '\.lz4$'
    '\.fw$'
    '\.cal$'
    '\.mbn$'
    'nvram'
    'system\.img'
    'efs\.img'
    'param\.img'
    'radio\.img'
    'recovery\.img'
)

while IFS= read -r file; do
    # Allow release/boot.img and release/boot-debug.img
    if [ "${file}" = "release/boot.img" ] || [ "${file}" = "release/boot-debug.img" ]; then
        continue
    fi
    for pat in "${FORBIDDEN_PATTERNS[@]}"; do
        if echo "${file}" | grep -qE "${pat}"; then
            log_error "Forbidden file tracked in git: ${file} (matches '${pat}')"
            FAILED=1
        fi
    done
done < <(cd "${REPO_ROOT}" && git ls-files 2>/dev/null || true)

# ------------------------------------------------------------------------------
# Check 3: Checksum comparison against private backups and proprietary blobs
# ------------------------------------------------------------------------------
log_info "Check 3: Verifying no private backup hashes appear in git or release/..."
BACKUP_DIR="${NOTEOS_BACKUP_DIR}"
if [ -d "${BACKUP_DIR}" ]; then
    log_info "Reading hashes from private backup directory: ${BACKUP_DIR}..."
    TEMP_BACKUP_HASHES=$(mktemp)
    find "${BACKUP_DIR}" -type f -not -name "BACKUP_VERIFIED_SHA256.txt" -not -name "*.sha256" -exec sha256sum {} + | awk '{print $1}' | sort -u > "${TEMP_BACKUP_HASHES}"

    # Calculate sha256 of all tracked files in git
    TEMP_GIT_HASHES=$(mktemp)
    (
        cd "${REPO_ROOT}"
        git ls-files | while IFS= read -r f; do
            [ -f "${f}" ] || continue
            sha256sum "${f}"
        done
    ) | sort -k1 > "${TEMP_GIT_HASHES}"

    # Check for matches
    MATCHES=$(awk 'NR==FNR{a[$1];next} $1 in a {print $1, $2}' "${TEMP_BACKUP_HASHES}" "${TEMP_GIT_HASHES}" || true)
    if [ -n "${MATCHES}" ]; then
        log_error "CRITICAL: Private backup file found tracked in git repo!"
        echo "${MATCHES}" >&2
        FAILED=1
    fi
    rm -f "${TEMP_BACKUP_HASHES}" "${TEMP_GIT_HASHES}"
else
    log_warn "Private backup directory not found at ${BACKUP_DIR}. Skipping cross-checksum verification."
fi

# ------------------------------------------------------------------------------
# Check 4: Confidentiality & Personal Data Scan
# ------------------------------------------------------------------------------
log_info "Check 4: Scanning git-tracked files for personal data and confidential patterns..."
SENSITIVE_PATTERNS=(
    '/home/[a-zA-Z0-9_-]+'
    '/run/media/[a-zA-Z0-9_-]+'
    '[a-zA-Z]:\\'
    "$(echo "YmlnYm9pLXBj" | base64 -d)"
    "$(echo "NDEwNzcxMDQ1MjNlMTExMQ==" | base64 -d)"
    "$(echo "NjA6MjE6YzA6Y2E6NTE6MTk=" | base64 -d)"
    'ghp_[a-zA-Z0-9]{36}'
    'AKIA[0-9A-Z]{16}'
    '-----BEGIN [A-Z ]*PRIVATE KEY-----'
)

# Text extensions to inspect
while IFS= read -r file; do
    [ -f "${REPO_ROOT}/${file}" ] || continue
    [ "${file}" = "scripts/lib/check_repo_clean.sh" ] && continue
    # Skip binary files
    case "${file}" in
        *.png|*.jpg|*.jpeg|*.zip|*.tar*|*.img|*.deb|*.cpio*)
            continue
            ;;
    esac
    for pat in "${SENSITIVE_PATTERNS[@]}"; do
        if grep -nEi -e "${pat}" "${REPO_ROOT}/${file}" >/dev/null 2>&1; then
            log_error "Sensitive data pattern detected in: ${file}"
            grep -nEi -e "${pat}" "${REPO_ROOT}/${file}" | head -n 3 >&2
            FAILED=1
        fi
    done
done < <(cd "${REPO_ROOT}" && git ls-files 2>/dev/null || true)

# ------------------------------------------------------------------------------
# Check 5: Verification of release boot images
# ------------------------------------------------------------------------------
if [ -f "${REPO_ROOT}/release/boot.img" ]; then
    log_info "Check 5: Verifying release boot.img..."
    sz=$(stat -c%s "${REPO_ROOT}/release/boot.img")
    if [ "${sz}" -gt "${BOOT_MAX_BYTES}" ]; then
        log_error "release/boot.img (${sz} bytes) exceeds 7.5 MiB budget (${BOOT_MAX_BYTES} bytes)!"
        FAILED=1
    else
        log_success "release/boot.img is within 7.5 MiB budget: ${sz} bytes."
    fi
fi

if [ "${FAILED}" -ne 0 ]; then
    die "Repository cleanliness check FAILED. See errors above."
fi

log_success "Repository cleanliness and privacy verification PASSED: clean, zero leaks, zero proprietary blobs."


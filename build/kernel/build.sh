#!/usr/bin/env bash
# ==============================================================================
# NoteOS — build/kernel/build.sh
# Fetch, patch, and deterministic compilation of Linux kernel + boot.img
# ==============================================================================
set -euo pipefail

DEVICE="${DEVICE:-n8000}"
BUILD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${BUILD_DIR}/.." && pwd)"
DEVICE_DIR="${BUILD_DIR}/devices/${DEVICE}"
DEVICE_CONF="${DEVICE_DIR}/device.conf"

if [ ! -f "${DEVICE_CONF}" ]; then
    echo "ERROR: Device configuration not found: ${DEVICE_CONF}" >&2
    exit 1
fi

# shellcheck source=/dev/null
source "${DEVICE_CONF}"

export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1700000000}"
export KBUILD_BUILD_TIMESTAMP="$(LC_ALL=C date -u -d "@${SOURCE_DATE_EPOCH}" '+%Y-%m-%d %H:%M:%S UTC')"
export KBUILD_BUILD_USER="noteos"
export KBUILD_BUILD_HOST="reproducible-builder"
export KBUILD_BUILD_VERSION="1"

SRC_ROOT="${NOTEOS_WORKDIR:-${REPO_ROOT}/.work}/src"
TARBALL="${SRC_ROOT}/linux-${KERNEL_VERSION}.tar.xz"
KERNEL_SRC="${SRC_ROOT}/linux-${KERNEL_VERSION}"
OUT_DIR="${REPO_ROOT}/out/${DEVICE}"

mkdir -p "${SRC_ROOT}" "${OUT_DIR}" "${OUT_DIR}/modules"

echo "=== [kernel] Verifying Linux ${KERNEL_VERSION} Sources for ${DEVICE_NAME} ==="

if [ ! -f "${TARBALL}" ]; then
    echo "--> Downloading ${KERNEL_TARBALL_URL}..."
    wget -O "${TARBALL}" "${KERNEL_TARBALL_URL}"
fi

echo "--> Verifying Linux tarball SHA256 (${KERNEL_TARBALL_SHA256})..."
ACTUAL_TAR_SHA=$(sha256sum "${TARBALL}" | awk '{print $1}')
if [ "${ACTUAL_TAR_SHA}" != "${KERNEL_TARBALL_SHA256}" ]; then
    echo "CRITICAL ERROR: Kernel tarball SHA256 checksum mismatch!" >&2
    echo "  Expected: ${KERNEL_TARBALL_SHA256}" >&2
    echo "  Actual:   ${ACTUAL_TAR_SHA}" >&2
    exit 1
fi

if [ ! -d "${KERNEL_SRC}" ]; then
    echo "--> Extracting ${TARBALL} to ${SRC_ROOT}..."
    tar -xf "${TARBALL}" -C "${SRC_ROOT}"
fi

echo "--> Applying DTS and device patches for ${DEVICE}..."
if [ -d "${DEVICE_DIR}/dts" ]; then
    cp -f "${DEVICE_DIR}/dts/"*.dts "${KERNEL_SRC}/arch/arm/boot/dts/samsung/"
fi

if [ -d "${DEVICE_DIR}/patches" ]; then
    for patch_file in "${DEVICE_DIR}/patches/"*.patch; do
        [ -f "${patch_file}" ] || continue
        if patch -d "${KERNEL_SRC}" -p1 -N --dry-run -s < "${patch_file}" >/dev/null 2>&1; then
            echo "    Applying patch: $(basename "${patch_file}")"
            patch -d "${KERNEL_SRC}" -p1 -N < "${patch_file}"
        else
            echo "    Patch already applied: $(basename "${patch_file}")"
        fi
    done
fi

# Ensure initramfs images exist before compiling kernel
if [ ! -f "${OUT_DIR}/initramfs.cpio" ] || [ ! -f "${OUT_DIR}/initramfs-debug.cpio" ]; then
    echo "--> initramfs images not found, invoking build/initramfs/build.sh..."
    DEVICE="${DEVICE}" "${BUILD_DIR}/initramfs/build.sh"
fi

cd "${KERNEL_SRC}"
export ARCH=arm
export CROSS_COMPILE=arm-linux-gnueabihf-

echo "--> Configuring kernel: ${KERNEL_DEFCONFIG} + devices/${DEVICE}/kernel.config"
make "${KERNEL_DEFCONFIG}"
./scripts/kconfig/merge_config.sh -m -O . .config "${DEVICE_DIR}/kernel.config"
./scripts/config --set-str CONFIG_INITRAMFS_SOURCE "${OUT_DIR}/initramfs.cpio"
make olddefconfig
cp -f .config "${OUT_DIR}/kernel.config.resolved"

package_boot_img() {
    local zimage_path="$1"
    local ramdisk_path="$2"
    local cmdline_str="$3"
    local output_img="$4"
    local label_desc="$5"

    echo "--> Packaging ${label_desc}: $(basename "${output_img}")"
    "${REPO_ROOT}/scripts/lib/mkbootimg.py" \
        --kernel "${zimage_path}" \
        --ramdisk "${ramdisk_path}" \
        --base "${MKBOOTIMG_BASE}" \
        --pagesize "${MKBOOTIMG_PAGESIZE}" \
        --kernel_offset "${MKBOOTIMG_KERNEL_OFFSET}" \
        --ramdisk_offset "${MKBOOTIMG_RAMDISK_OFFSET}" \
        --second_offset "${MKBOOTIMG_SECOND_OFFSET}" \
        --tags_offset "${MKBOOTIMG_TAGS_OFFSET}" \
        --header_version "${MKBOOTIMG_HEADER_VERSION}" \
        --cmdline "${cmdline_str}" \
        --output "${output_img}"

    local img_size
    img_size=$(stat -c%s "${output_img}")
    echo "    Size $(basename "${output_img}"): ${img_size} bytes (Limit: ${BOOT_IMAGE_MAX_BYTES} bytes / 7.5 MiB)"
    if [ "${img_size}" -gt "${BOOT_IMAGE_MAX_BYTES}" ]; then
        echo "CRITICAL ERROR: $(basename "${output_img}") exceeds 7.5 MiB budget!" >&2
        rm -f "${output_img}"
        exit 1
    fi
}

echo "--> Compiling zImage (Release), modules, and DTB (-j$(nproc))..."
./scripts/config --set-str CONFIG_INITRAMFS_SOURCE "${OUT_DIR}/initramfs.cpio"
./scripts/config --set-str CONFIG_CMDLINE "${CMDLINE_RELEASE}"
make olddefconfig
make -j"$(nproc)" zImage modules "${KERNEL_DTB}"

cat arch/arm/boot/zImage "arch/arm/boot/dts/${KERNEL_DTB}" > "${OUT_DIR}/zImage-dtb"
package_boot_img "${OUT_DIR}/zImage-dtb" "${OUT_DIR}/initramfs.cpio.gz" "${CMDLINE_RELEASE}" "${OUT_DIR}/boot.img" "boot.img (Release)"

echo "--> Compiling zImage (Debug with debug=1) and boot-debug.img..."
./scripts/config --set-str CONFIG_INITRAMFS_SOURCE "${OUT_DIR}/initramfs-debug.cpio"
./scripts/config --set-str CONFIG_CMDLINE "${CMDLINE_DEBUG}"
make olddefconfig
make -j"$(nproc)" zImage
cat arch/arm/boot/zImage "arch/arm/boot/dts/${KERNEL_DTB}" > "${OUT_DIR}/zImage-dtb-debug"
package_boot_img "${OUT_DIR}/zImage-dtb-debug" "${OUT_DIR}/initramfs-debug.cpio.gz" "${CMDLINE_DEBUG}" "${OUT_DIR}/boot-debug.img" "boot-debug.img (Debug)"

echo "--> Installing kernel modules into ${OUT_DIR}/modules..."
rm -rf "${OUT_DIR}/modules"/*
make INSTALL_MOD_PATH="${OUT_DIR}/modules" modules_install

echo "=== [kernel] Kernel build completed successfully! ==="
ls -lh "${OUT_DIR}/boot.img" "${OUT_DIR}/boot-debug.img"

#!/usr/bin/env bash
# ==============================================================================
# NoteOS — build/rootfs/build.sh
# Deterministic Debian 12 Bookworm armhf rootfs build for NoteOS.
# Produces a clean base rootfs tarball free of proprietary firmware and credentials.
# ==============================================================================
set -euo pipefail

DEVICE="${DEVICE:-n8000}"
ROOTFS_MODE="${ROOTFS_MODE:-base}"
BUILD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${BUILD_DIR}/.." && pwd)"
DEVICE_CONF="${BUILD_DIR}/devices/${DEVICE}/device.conf"

if [ ! -f "${DEVICE_CONF}" ]; then
    echo "ERROR: Device configuration not found: ${DEVICE_CONF}" >&2
    exit 1
fi

# shellcheck source=/dev/null
source "${DEVICE_CONF}"

export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1700000000}"
OUT_DIR="${REPO_ROOT}/out/${DEVICE}"
ROOTFS_WORK="${OUT_DIR}/rootfs_work"
ROOTFS_CACHE="${OUT_DIR}/rootfs_base_cache"
ROOTFS_TAR_GZ="${OUT_DIR}/rootfs.tar.gz"
PACKAGES_FILE="${BUILD_DIR}/rootfs/packages-base.list"

mkdir -p "${OUT_DIR}"

echo "=== [rootfs] Building NoteOS Rootfs for ${DEVICE_NAME} (${DEVICE_ARCH}) ==="

PKG_CSV=$(grep -vE '^\s*#|^\s*$' "${PACKAGES_FILE}" | tr '\n' ',' | sed 's/,$//')
PKG_LIST_SHA=$(sha256sum "${PACKAGES_FILE}" | awk '{print $1}')

if [ "${ROOTFS_MODE}" = "current" ] && [ -d "${BUILD_DIR}/rootfs/etc" ]; then
    echo "--> Reusing existing rootfs directory from ${BUILD_DIR}/rootfs..."
    rm -rf "${ROOTFS_WORK}"
    mkdir -p "${ROOTFS_WORK}"
    cp -a "${BUILD_DIR}/rootfs/." "${ROOTFS_WORK}/"
elif [ -d "${ROOTFS_CACHE}/etc" ] && [ -f "${ROOTFS_CACHE}/.pkg_sha256" ] && [ "$(cat "${ROOTFS_CACHE}/.pkg_sha256")" = "${PKG_LIST_SHA}" ]; then
    echo "--> Reusing verified mmdebstrap cache (${ROOTFS_CACHE})..."
    rm -rf "${ROOTFS_WORK}"
    mkdir -p "${ROOTFS_WORK}"
    cp -a "${ROOTFS_CACHE}/." "${ROOTFS_WORK}/"
    rm -f "${ROOTFS_WORK}/.pkg_sha256"
else
    echo "--> Clean bootstrap Debian 12 Bookworm (${DEVICE_ARCH}) via mmdebstrap..."
    rm -rf "${ROOTFS_WORK}" "${ROOTFS_CACHE}"
    mkdir -p "${ROOTFS_WORK}"
    mmdebstrap \
        --skip=check/qemu \
        --architectures="${DEVICE_ARCH}" \
        --components="main,contrib,non-free,non-free-firmware" \
        --include="${PKG_CSV}" \
        bookworm \
        "${ROOTFS_WORK}" \
        http://deb.debian.org/debian

    mkdir -p "${ROOTFS_CACHE}"
    cp -a "${ROOTFS_WORK}/." "${ROOTFS_CACHE}/"
    echo "${PKG_LIST_SHA}" > "${ROOTFS_CACHE}/.pkg_sha256"
fi

cleanup_mounts() {
    umount -lf "${ROOTFS_WORK}/sys" 2>/dev/null || true
    umount -lf "${ROOTFS_WORK}/proc" 2>/dev/null || true
    umount -lf "${ROOTFS_WORK}/dev" 2>/dev/null || true
}
trap cleanup_mounts EXIT
mkdir -p "${ROOTFS_WORK}/dev" "${ROOTFS_WORK}/proc" "${ROOTFS_WORK}/sys"
mount --rbind /dev "${ROOTFS_WORK}/dev"
mount --make-rslave "${ROOTFS_WORK}/dev"
mount -t proc proc "${ROOTFS_WORK}/proc"
mount -t sysfs sys "${ROOTFS_WORK}/sys"

# 1. Build and install noteos-branding package
echo "--> Building and installing noteos-branding debian package..."
DEVICE="${DEVICE}" "${BUILD_DIR}/branding/build-deb.sh"
DEB_FILE="${OUT_DIR}/noteos-branding_1.0.0_all.deb"
cp -f "${DEB_FILE}" "${ROOTFS_WORK}/tmp/noteos-branding.deb"
chroot "${ROOTFS_WORK}" dpkg -i /tmp/noteos-branding.deb
rm -f "${ROOTFS_WORK}/tmp/noteos-branding.deb"

# 2. Apply system overlays
echo "--> Applying system configurations from build/rootfs/overlay/..."
rm -rf "${ROOTFS_WORK}/etc/systemd/system/n8000-"*.service \
       "${ROOTFS_WORK}/etc/systemd/system/multi-user.target.wants/n8000-"*.service \
       "${ROOTFS_WORK}/etc/systemd/system/graphical.target.wants/n8000-"*.service \
       "${ROOTFS_WORK}/usr/share/n8000-setup" \
       "${ROOTFS_WORK}/usr/sbin/n8000-setup" 2>/dev/null || true
cp -a "${BUILD_DIR}/rootfs/overlay/." "${ROOTFS_WORK}/"

# 2b. Ensure Wi-Fi & Bluetooth firmware and Murata high-gain NVRAM calibration are present
echo "--> Verifying and staging Wi-Fi & Bluetooth firmware in ${ROOTFS_WORK}/usr/lib/firmware/brcm/..."
mkdir -p "${ROOTFS_WORK}/usr/lib/firmware/brcm"

# Import any proprietary firmware files if present (e.g., BCM4334B0.hcd, brcmfmac4334-sdio.bin)
if [ -d "${REPO_ROOT}/proprietary" ]; then
    for fw in "${REPO_ROOT}/proprietary"/brcmfmac4334* "${REPO_ROOT}/proprietary"/BCM4334*; do
        if [ -f "$fw" ]; then
            cp -f "$fw" "${ROOTFS_WORK}/usr/lib/firmware/brcm/"
        fi
    done
fi

# Ensure Murata high-gain NVRAM calibration is present for both generic and device-tree board names
if [ ! -s "${ROOTFS_WORK}/usr/lib/firmware/brcm/brcmfmac4334-sdio.txt" ]; then
    echo "    Generating Murata high-gain NVRAM calibration..."
    cat << 'NVRAM_EOF' > "${ROOTFS_WORK}/usr/lib/firmware/brcm/brcmfmac4334-sdio.txt"
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
fi

cp -f "${ROOTFS_WORK}/usr/lib/firmware/brcm/brcmfmac4334-sdio.txt" "${ROOTFS_WORK}/usr/lib/firmware/brcm/brcmfmac4334-sdio.samsung,n8000.txt"
chmod 0644 "${ROOTFS_WORK}/usr/lib/firmware/brcm/brcmfmac4334-sdio"*

# Compatibility fallback if /lib is not a symlink to usr/lib
if [ ! -L "${ROOTFS_WORK}/lib" ] && [ -d "${ROOTFS_WORK}/lib" ]; then
    mkdir -p "${ROOTFS_WORK}/lib/firmware/brcm"
    cp -af "${ROOTFS_WORK}/usr/lib/firmware/brcm/." "${ROOTFS_WORK}/lib/firmware/brcm/"
fi

# 3. Install compiled kernel modules
echo "--> Installing kernel modules in ${ROOTFS_WORK}/lib/modules/..."
mkdir -p "${ROOTFS_WORK}/lib/modules"
if [ ! -d "${OUT_DIR}/modules/lib/modules" ] && [ -d "${REPO_ROOT}/../NoteN8000Linux/out/n8000/modules/lib/modules" ]; then
    echo "    Importing kernel modules from NoteN8000Linux..."
    mkdir -p "${OUT_DIR}/modules"
    cp -a "${REPO_ROOT}/../NoteN8000Linux/out/n8000/modules/lib" "${OUT_DIR}/modules/"
fi

if [ -d "${OUT_DIR}/modules/lib/modules" ]; then
    cp -a "${OUT_DIR}/modules/lib/modules/." "${ROOTFS_WORK}/lib/modules/"
    for d in "${ROOTFS_WORK}/lib/modules"/*; do
        if [ -d "$d" ]; then
            kver=$(basename "$d")
            rm -f "$d/build" "$d/source"
            chroot "${ROOTFS_WORK}" depmod -a "${kver}" || true
        fi
    done
fi

# Verify critical kernel modules were installed (fail build if Wi-Fi driver is missing)
MODULE_COUNT=$(find "${ROOTFS_WORK}/lib/modules" -name "*.ko" 2>/dev/null | wc -l)
if [ "${MODULE_COUNT}" -eq 0 ]; then
    echo "CRITICAL ERROR: No kernel modules installed in ${ROOTFS_WORK}/lib/modules!" >&2
    exit 1
fi
if ! find "${ROOTFS_WORK}/lib/modules" -name "brcmfmac.ko" | grep -q brcmfmac; then
    echo "CRITICAL ERROR: Wi-Fi driver brcmfmac.ko not found in rootfs modules!" >&2
    exit 1
fi
echo "    Verified ${MODULE_COUNT} kernel modules installed (including brcmfmac.ko)."

# 4. Install setup wizard and desktop catalogs
echo "--> Installing setup wizard and desktop catalogs..."
mkdir -p "${ROOTFS_WORK}/usr/share/noteos-setup/desktops"
cp -f "${BUILD_DIR}/rootfs/desktops/"*.list "${ROOTFS_WORK}/usr/share/noteos-setup/desktops/"
if [ -d "${BUILD_DIR}/wizard" ]; then
    cp -a "${BUILD_DIR}/wizard/." "${ROOTFS_WORK}/usr/share/noteos-setup/"
    chmod 0755 "${ROOTFS_WORK}/usr/share/noteos-setup/start-kiosk.sh" \
               "${ROOTFS_WORK}/usr/share/noteos-setup/wizard_app.py" \
               "${ROOTFS_WORK}/usr/share/noteos-setup/noteos-setup" 2>/dev/null || true
    if [ -f "${BUILD_DIR}/wizard/noteos-setup" ]; then
        install -m 0755 "${BUILD_DIR}/wizard/noteos-setup" "${ROOTFS_WORK}/usr/sbin/noteos-setup"
    fi
fi

# 5. Configure locale, timezone, security hardening, and services
echo "--> Configuring base system services and security hardening..."
chroot "${ROOTFS_WORK}" /bin/sh -c '
    export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
    mkdir -p /etc/default
    echo "noteos" > /etc/hostname
    cat << "HOSTS_EOF" > /etc/hosts
127.0.0.1   localhost
127.0.1.1   noteos
::1         localhost ip6-localhost ip6-loopback
HOSTS_EOF

    if ! grep -q "^en_US.UTF-8" /etc/locale.gen 2>/dev/null; then
        echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
    fi
    if ! grep -q "^it_IT.UTF-8" /etc/locale.gen 2>/dev/null; then
        echo "it_IT.UTF-8 UTF-8" >> /etc/locale.gen
    fi
    mkdir -p /usr/lib/locale
    locale-gen
    echo "LANG=en_US.UTF-8" > /etc/default/locale
    ln -sf /usr/share/zoneinfo/UTC /etc/localtime
    echo "UTC" > /etc/timezone

    # Security hardening: lock root password and disable remote ssh by default
    userdel -r debian 2>/dev/null || true
    rm -f /etc/sudoers.d/010_debian-nopasswd
    rm -f /etc/ssh/sshd_config.d/01-permitroot.conf
    rm -f /etc/ssh/sshd_config.d/99-n8000-debug.conf
    rm -f /etc/network/interfaces.d/usb0
    rm -f /etc/NetworkManager/system-connections/usb0.nmconnection
    mkdir -p /etc/NetworkManager/system-connections
    chmod 0700 /etc/NetworkManager/system-connections
    passwd -l root
    systemctl disable ssh.service 2>/dev/null || true
    systemctl disable ssh.socket 2>/dev/null || true
    systemctl disable ModemManager.service 2>/dev/null || true
    systemctl disable cups.service 2>/dev/null || true
    systemctl disable avahi-daemon.service 2>/dev/null || true
    systemctl mask fstrim.timer fstrim.service 2>/dev/null || true
    rm -f /etc/systemd/system/timers.target.wants/fstrim.timer
    rm -f /var/lib/systemd/deb-systemd-helper-enabled/timers.target.wants/fstrim.timer

    systemctl enable NetworkManager.service 2>/dev/null || true
    systemctl enable systemd-timesyncd.service 2>/dev/null || true
    systemctl enable bluetooth.service 2>/dev/null || true
    systemctl enable zramswap.service 2>/dev/null || true
    systemctl enable earlyoom.service 2>/dev/null || true
    systemctl enable noteos-resize-rootfs.service 2>/dev/null || true
    systemctl enable wifi-regdom.service 2>/dev/null || true
    systemctl set-default multi-user.target 2>/dev/null || true
    if [ -f /etc/systemd/system/noteos-firstboot.service ]; then
        systemctl enable noteos-firstboot.service 2>/dev/null || true
    fi
    dconf update 2>/dev/null || true
'

# Patch zramswap stop to prevent failure when zram is built-in kernel driver
if [ -f "${ROOTFS_WORK}/usr/sbin/zramswap" ]; then
    sed -i 's/modprobe -r zram || elog/modprobe -r zram 2>\/dev\/null || true #/g' "${ROOTFS_WORK}/usr/sbin/zramswap" || true
fi

# 6. Generate package manifest with exact versions
chroot "${ROOTFS_WORK}" dpkg-query -W -f='${Package}=${Version}\n' | LC_ALL=C sort > "${OUT_DIR}/packages.manifest"

# 7. Privacy scrub: remove SSH host keys, empty machine-id, clean apt archive cache (preserve package lists)
echo "--> Performing privacy scrub: removing SSH host keys, clearing machine-id and caches..."
rm -rf "${ROOTFS_WORK}/var/cache/apt/archives/"*.deb "${ROOTFS_WORK}/var/lib/apt/lists/partial" "${ROOTFS_WORK}/var/lib/apt/lists/lock" 2>/dev/null || true
rm -f "${ROOTFS_WORK}/etc/ssh/ssh_host_"*
: > "${ROOTFS_WORK}/etc/machine-id"
rm -f "${ROOTFS_WORK}/var/lib/dbus/machine-id"
rm -rf "${ROOTFS_WORK}/etc/NetworkManager/system-connections/"*
mkdir -p "${ROOTFS_WORK}/etc/NetworkManager/system-connections"
chmod 0700 "${ROOTFS_WORK}/etc/NetworkManager/system-connections"
rm -rf "${ROOTFS_WORK}/root/.bash_history"
rm -rf "${ROOTFS_WORK}/home/"*

cleanup_mounts

# Verify essential Wi-Fi & BT firmware before packaging
if [ ! -s "${ROOTFS_WORK}/usr/lib/firmware/brcm/brcmfmac4334-sdio.txt" ] || [ ! -s "${ROOTFS_WORK}/usr/lib/firmware/brcm/brcmfmac4334-sdio.samsung,n8000.txt" ]; then
    echo "CRITICAL ERROR: Murata Wi-Fi NVRAM calibration missing in ${ROOTFS_WORK}/usr/lib/firmware/brcm/!" >&2
    exit 1
fi
echo "    Verified Murata Wi-Fi NVRAM calibration present in rootfs."

# 8. Deterministic rootfs.tar.gz packaging
echo "--> Deterministic packaging of ${ROOTFS_TAR_GZ}..."
NPROC=$(nproc 2>/dev/null || echo 4)
if command -v pigz >/dev/null 2>&1; then
    COMPRESS_CMD="pigz -n -6 -p ${NPROC}"
else
    COMPRESS_CMD="gzip -n -6"
fi

tar --one-file-system \
    --format=gnu \
    --sort=name \
    --mtime="@${SOURCE_DATE_EPOCH}" \
    --numeric-owner \
    -C "${ROOTFS_WORK}" \
    -cf - . | ${COMPRESS_CMD} > "${ROOTFS_TAR_GZ}"

ROOTFS_SIZE=$(stat -c%s "${ROOTFS_TAR_GZ}")
echo "=== [rootfs] Completed: ${ROOTFS_TAR_GZ} (${ROOTFS_SIZE} bytes / $(( ROOTFS_SIZE / 1024 / 1024 )) MiB) ==="

# NoteOS — Empirical Development and Verification Log

This document records the empirical chronology, technical hypotheses, verification tests, and hardware results throughout the NoteOS project for the Samsung Galaxy Note 10.1 (`GT-N8000`).

---

## Phase Summary & Hardware Verification Chronology

### 1. Pre-Flight Hardware Inspection & Partition Analysis — [VERIFIED]
- **Hardware Architecture**: Samsung Galaxy Note 10.1 (`GT-N8000` / `p4noterf`), Exynos 4412 Quad-Core Cortex-A9 @ 1.4 GHz, 2 GiB RAM (`1994 MiB` detected by Linux kernel).
- **Physical eMMC Storage**: 16 GB eMMC (`15,758,000,128` bytes, `30,777,344` 512-byte sectors).
- **Bootloader Constraints**: Samsung proprietary S-BOOT bootloader parses standard Android `boot.img` headers. S-BOOT enforces an 8 MiB limit on the `BOOT` partition (`mmcblk0p5`); kernel decompressor fails if `boot.img` exceeds 7.5 MiB (`7,864,320` bytes).
- **Recovery Preservation**: TWRP 3.7.0 recovery partition (`mmcblk0p6`, SHA256: `894508b9f5cae24e047c7fdb1fb6d7f011f13ce9b36e5c844e9efd2b91cc6099`) kept completely untouched across all operations.

### 2. Mainline Kernel 6.6 LTS & Hardware Subsystems — [VERIFIED]
- **Upstream Kernel**: Linux 6.6.158 LTS compiled with ARM gnueabihf toolchain.
- **Bootloader Cache State Resolution**: Samsung S-BOOT leaves L1/L2 caches enabled with inconsistent MMU mapping at `0x40004000`. Patch `0003-ARM-compressed-head-bypass-cache_on-sboot.patch` bypasses decompressor `cache_on`, enabling clean execution with MMU off.
- **GPU Acceleration**: ARM Mali-400 MP4 running on upstream Mesa Lima driver (`lima_drm`) with modesetting, achieving 60 fps at native 1280x800 resolution.
- **Input & Touch**: Melfas MMS134S multi-touch digitizer operational out-of-the-box via `libinput`.
- **Wi-Fi & Bluetooth**: Broadcom BCM4334 SDIO/UART initialized via `brcmfmac` and `hci_bcm`. Firmware loaded from `/lib/firmware/brcm/`.

### 3. Unified Partition Layout & eMMC Optimization — [VERIFIED]
- **Original Stock Layout**: 12 partitions with small Android system allocations.
- **NoteOS Layout**: Partitions 1-7 (BOTA0/1, EFS, PARAM, BOOT, RECOVERY, RADIO) kept 100% bit-for-bit identical to preserve bootloader safety. Partitions 8-12 merged into a single unified rootfs partition `mmcblk0p8` (~14.5 GiB, `LABEL=debian_root`).
- **Filesystem**: Formatted as ext4 with journaling. Tested clean with `e2fsck`.

### 4. Deterministic Rootfs & Setup Wizard — [VERIFIED]
- **Base OS**: Clean Debian 12 Bookworm `armhf`.
- **Kiosk First-Boot Setup**: Python 3 / PyQt5 touch setup wizard (`noteos-setup`) launches in a frameless full-screen Openbox kiosk at native 1280x800 resolution.
- **KDE Breeze Dark Theme**: Complete dark theme styling matching KDE Plasma Breeze Dark across UI controls, radio buttons, combo boxes, text inputs, and on-screen keyboard (`Onboard` with Nightshade theme).
- **Curated Applications Catalog**: 20 verified ARMv7 compatible applications with dynamic substitution of 32-bit incompatible packages.

### 5. Silent Boot & Plymouth Graphic Animation — [VERIFIED]
- **Release Boot Configuration**: Kernel cmdline configured with `quiet splash loglevel=0 vt.global_cursor_default=0 systemd.show_status=false`.
- **Plymouth Theme**: Custom NoteOS boot animation (30 PNG frames at native 1280x800) plays smoothly from rootfs startup until the kiosk wizard or desktop displays.
- **Diagnostic Variant**: `boot-debug.img` provides verbose serial console (`ttySAC2,115200`), earlyprintk, USB RNDIS gadget networking (`192.168.3.2`), and RAM-backed transient SSH.

### 6. Clean Flash Verification on Device — [VERIFIED]
- Full clean installation executed via `scripts/07_install.sh --full` from TWRP recovery.
- `boot.img` flashed to `mmcblk0p5` (`7,350,272` bytes <= 7.5 MiB). Bit-by-bit readback SHA256 verified exact match (`6de03d4f2a2ba5bfe96bea21fe30d34f1f30972597195485293fed583c2d6863`).
- TWRP Recovery partition (`mmcblk0p6`) verified completely untouched (`894508b9f5cae24e047c7fdb1fb6d7f011f13ce9b36e5c844e9efd2b91cc6099`).
- Rootfs filesystem verified with `e2fsck -f -n /dev/block/mmcblk0p8`: 52,451 files, 0 errors.


# NoteOS — Mainline Linux & Debian for Samsung Galaxy Note 10.1 (GT-N8000)

[![License](https://img.shields.io/badge/License-GPL--2.0%20%2F%20MIT-blue.svg)](LICENSE)
[![Debian](https://img.shields.io/badge/Debian-12%20(Bookworm%20armhf)-crimson.svg)](https://www.debian.org/)
[![Kernel](https://img.shields.io/badge/Linux%20Kernel-6.6%20LTS-green.svg)](https://www.kernel.org/)
[![Target](https://img.shields.io/badge/Device-Samsung%20GT--N8000%20(p4note)-orange.svg)](docs/NEW_DEVICE.md)

**NoteOS** transforms the classic **Samsung Galaxy Note 10.1** (GT-N8000, 2012) into a modern, usable, and open Linux tablet powered by mainline Linux 6.6 LTS, pure Debian 12 (Bookworm `armhf`), GPU acceleration via Mesa Lima, and a touch-optimized setup wizard.

---

## 1. Project Status & Legal Disclaimer

> [!WARNING]
> **EXPERIMENTAL SOFTWARE — PROCEED AT YOUR OWN RISK**:
> NoteOS is an independent community project and is provided "AS IS", WITHOUT WARRANTY OF ANY KIND. Flashing custom operating systems or repartitioning eMMC storage carries an inherent risk of device bricking or data loss.
>
> NoteOS is **NOT affiliated with, sponsored by, or endorsed by** Samsung Electronics Co., Ltd., The Debian Project, The KDE Community, LXQt, or any third-party software provider. All trademarks, service marks, and trade names belong to their respective owners.

---

## 2. Hardware Specifications (`GT-N8000`)

- **Model**: Samsung Galaxy Note 10.1 3G (`GT-N8000`, codename `p4note` / `p4noterf`)
- **SoC**: Samsung Exynos 4412 Quad-Core ARM Cortex-A9 @ 1.4 GHz (ARMv7-A, `armhf`, VFPv3-D16 + NEON)
- **RAM**: 2 GiB LPDDR2 (`1994 MiB` accessible to kernel + `997 MiB` ZRAM swap)
- **Display**: 10.1" WXGA (1280x800, 16:10 aspect ratio) SEC panel
- **GPU**: ARM Mali-400 MP4 (OpenGL ES 2.0 accelerated via upstream Mesa `lima` driver)
- **Touch Digitizer**: Melfas MMS134S / MMS136 Multi-touch I2C
- **Storage**: 16 GB eMMC (eMMC 4.41 high speed mode via `dw_mmc`)
- **BOOT Partition Limit**: Physical limit is 8 MiB (8,388,608 bytes). NoteOS enforces a strict build budget of **<= 7.5 MiB** (`7,864,320` bytes) to guarantee bootloader decompression.

### Supported Devices
- **GT-N8000 (3G)**: Fully tested and verified on physical hardware.
- **GT-N8010 / GT-N8013 (Wi-Fi only)**: Untested on physical hardware. The build scripts will refuse to flash non-N8000 models to prevent damage. Porting instructions are available in [`docs/NEW_DEVICE.md`](docs/NEW_DEVICE.md).

---

## 3. Hardware Support Matrix

| Subsystem / Feature | Status | Notes |
| :--- | :---: | :--- |
| **Kernel & Boot** | ✅ Working | Mainline Linux 6.6 LTS, silent boot, Plymouth graphic animation |
| **GPU / 3D Acceleration** | ✅ Working | ARM Mali-400 MP4 via Mesa Lima (`lima_drm`), 60 fps |
| **Multi-touch Screen** | ✅ Working | Multi-touch operational out-of-the-box (`melfas_mms114`) |
| **Wi-Fi (802.11 a/b/g/n)** | ✅ Working | Broadcom BCM4334 SDIO (`brcmfmac`); requires extracted firmware |
| **Bluetooth (4.0 LE)** | ✅ Working | Broadcom BCM4334 UART (`hci_bcm`); requires extracted patchram |
| **Audio (Speakers & Jack)** | ✅ Working | Wolfson WM1811 I2S via ALSA and PipeWire |
| **Battery & Charging** | ✅ Working | Maxim MAX77686 PMIC and SMB347 charger telemetry |
| **ZRAM Compressed Swap** | ✅ Working | 50% RAM (`997 MiB`) compressed with `lz4` |
| **Full Disk Encryption** | ⚠️ Experimental | Supported via cryptsetup / LUKS on `mmcblk0p8` |
| **Wacom S-Pen EMR** | ❌ Not Working | Wacom digitizer is not powered or enabled in upstream DTS |
| **Camera (Front/Rear)** | ❌ Not Working | Exynos FIMC/MIPI camera drivers missing in mainline |
| **Modem (3G / Voice / SMS)** | ❌ Not Working | Samsung XMM6262 modem interface unmaintained in mainline |

---

## 4. What This Repository Does NOT Contain

In strict compliance with open-source licensing and privacy standards, **this repository contains NO proprietary Samsung firmware, NO stock Android images, and NO binary blobs**:

| Component | Status | How to Obtain Legally |
| :--- | :--- | :--- |
| **Wi-Fi Firmware (`brcmfmac4334-sdio.bin`)** | Excluded | Extracted from your tablet or via Debian package `firmware-brcm80211` |
| **Bluetooth Firmware (`BCM4334B0.hcd`)** | Excluded | Extracted from your tablet backup (`/vendor/firmware/bcm4334.hcd`) |
| **Wi-Fi NVRAM Calibration** | Excluded | Extracted from your tablet and personalized with factory MAC |
| **Modem Radio & EFS** | Excluded | Stored strictly in private local backup (`../NoteOs-private/backup/`) |

See [`docs/PROPRIETARY.md`](docs/PROPRIETARY.md) for full extraction instructions and cryptographic verification hashes.

---

## 5. Prerequisites

### Host PC Requirements
- **Linux Distribution**: Debian, Ubuntu, Fedora, Nobara, Arch, or compatible.
- **Required Tools**: `bash`, `adb`, `tar`, `gzip` (or `pigz`), `sha256sum`, `make`, `python3`.
- **Optional**: `podman` or `docker` (recommended for reproducible containerized builds).
- **Disk Space**: At least **10 GB** free space on host.
- **USB Cable**: Reliable 30-pin Samsung data cable.

### Tablet Requirements
- **Model**: Samsung Galaxy Note 10.1 (`GT-N8000`).
- **Recovery**: Working **TWRP Recovery (>= 3.7.0)** installed on the `RECOVERY` partition (`mmcblk0p6`).
- **Battery**: Charged to at least **50%**.
- **Mandatory Backup**: You **MUST** back up and keep private your device's `EFS` partition before any write operation.

---

## 6. Step-by-Step Installation

### Step 0: Check Host Prerequisites & Pre-Commit Guard
```bash
./scripts/00_check_prerequisites.sh
```

### Step 1: Back Up Connected Device (TWRP ADB)
Connect your tablet running in TWRP recovery mode:
```bash
./scripts/01_backup_device.sh
```
*Dumps BOOT, RECOVERY, EFS, and partition tables to `../NoteOs-private/backup/`.*

### Step 2: Extract Proprietary Wi-Fi/Bluetooth Firmware
```bash
./scripts/02_extract_firmware.sh
```
*Populates the local `proprietary/` directory and verifies SHA256 against `build/proprietary/MANIFEST.sha256`.*

### Step 3: (Optional) Unified Partition Layout
If your tablet still has the stock Android 12-partition layout and you wish to allocate the full 14.5 GiB for NoteOS:
```bash
# Verify eligibility in dry-run mode:
./scripts/03_repartition.sh --dry-run

# Apply partition changes (requires typed confirmation):
./scripts/03_repartition.sh --apply
```
*See [`docs/REPARTITION.md`](docs/REPARTITION.md) for architecture details.*

### Step 4: Obtain Release Artifacts
You can either download pre-built release artifacts from [GitHub Releases](https://github.com/zmalrobot/NoteOs/releases) into `release/`, or build from source (see Section 7).

### Step 5: Flash NoteOS to Tablet
```bash
# Simulate all checks and operations in dry-run mode:
./scripts/07_install.sh --dry-run

# Execute full installation:
./scripts/07_install.sh --full
```

### Step 6: Verify Installation & Reboot
```bash
# Verify partition integrity:
./scripts/08_verify_install.sh

# Reboot into NoteOS:
adb reboot
```

---

## 7. Building from Source

To build everything from source using Docker/Podman:

```bash
# 1. Fetch, patch, and build the Linux kernel + boot.img:
./scripts/04_build_kernel.sh

# 2. Build the clean Debian 12 armhf rootfs:
./scripts/05_build_rootfs.sh

# 3. Package and verify boot images (enforcing <= 7.5 MiB budget):
./scripts/06_build_boot_image.sh
```

---

## 8. First-Boot Touch Setup Wizard (`noteos-setup`)

On initial boot, NoteOS launches a full-screen, frameless kiosk wizard styled with **KDE Breeze Dark**:

1. **Language & Keyboard**: Select UI language (English / Italiano) and keyboard layout.
2. **Wi-Fi Network**: Scan and connect to wireless networks via NetworkManager.
3. **Date, Time & Timezone**: Configure NTP synchronization and timezones.
4. **Desktop Environment Selection**:
   - **LXQt (Recommended)**: Extremely lightweight (~295 MiB idle RAM).
   - **KDE Plasma 5.27**: Full-featured Qt5 desktop (~433 MiB idle RAM).
5. **Applications Selection**: Choose from 20 verified ARMv7 packages (Chromium, LibreOffice, VLC, VS Code, GIMP, btop++, etc.).
6. **User Account Creation**: Set full name, username, and password.
7. **Login Behavior**: Enable or disable automatic login.
8. **Installation**: Displays live APT installation progress and reboots into your chosen desktop.

See [`docs/DESKTOP.md`](docs/DESKTOP.md) and [`docs/APPS.md`](docs/APPS.md) for details.

---

## 9. Rollback & Emergency Recovery

- **Restore Boot from Backup**:
  ```bash
  ./scripts/09_rollback.sh
  ```
- **Hardware Key Combinations**:
  - **TWRP Recovery**: Hold **Power + Volume Up** until Samsung logo appears.
  - **Download Mode**: Hold **Power + Volume Down** until yellow warning triangle appears.
  - **Hard Reset**: Hold **Power** for 10–12 seconds.

See [`docs/RECOVERY.md`](docs/RECOVERY.md) and [`notes/ROLLBACK.md`](notes/ROLLBACK.md).

---

## 10. Repository Structure

```text
NoteOs/
├── Makefile                          # Thin wrapper calling scripts/
├── Dockerfile                        # Multi-core reproducible Debian builder
├── LICENSE                           # GPL-2.0-only / MIT split license
├── NOTICE                            # Third-party notices and attributions
├── README.md                         # Main documentation
├── scripts/
│   ├── 00_check_prerequisites.sh     # Host tools & pre-commit hook installer
│   ├── 01_backup_device.sh           # Safe device partition backup
│   ├── 02_extract_firmware.sh        # Proprietary firmware extractor
│   ├── 03_repartition.sh             # (Experimental) Unified eMMC repartitioner
│   ├── 04_build_kernel.sh            # Kernel fetch & compile entrypoint
│   ├── 05_build_rootfs.sh            # Clean rootfs build entrypoint
│   ├── 06_build_boot_image.sh        # Boot image packaging (<= 7.5 MiB check)
│   ├── 07_install.sh                 # 7-stage ADB/TWRP device installer
│   ├── 08_verify_install.sh          # Post-installation verifier
│   ├── 09_rollback.sh                # Backup restoration tool
│   └── lib/
│       ├── check_repo_clean.sh       # Cleanliness, leak & privacy guard
│       ├── common.sh                 # Common shell functions & constants
│       └── mkbootimg.py              # AOSP mkbootimg tool
├── build/
│   ├── devices/                      # Device definitions (n8000 & _template)
│   ├── kernel/                       # Kernel build scripts
│   ├── initramfs/                    # Deterministic initramfs generator
│   ├── rootfs/                       # Debian base package lists & overlay
│   ├── wizard/                       # NoteOS Setup Wizard source code
│   ├── branding/                     # Wallpapers and deb builder
│   └── proprietary/                  # Checksum manifest for proprietary blobs
├── proprietary/                      # Local git-ignored firmware store
├── release/                          # Verified release boot images & manifests
├── docs/                             # Architecture, hardware, and desktop guides
└── notes/                            # Technical notes, verified logs, and research
```

---

## 11. Empirical Validation Status

| Milestone / Component | Validation Status | Hardware Test Date | Evidence |
| :--- | :---: | :---: | :--- |
| **Kernel Decompressor (Cache bypass)** | **Validated on Hardware** | 2026-10-12 | Clean boot past S-BOOT without cache freeze |
| **Mesa Lima GPU (Mali-400 MP4)** | **Validated on Hardware** | 2026-10-12 | 60 fps rendering on Xorg modesetting |
| **Touchscreen Digitizer** | **Validated on Hardware** | 2026-10-12 | Full multi-touch input functional via libinput |
| **Wi-Fi (Broadcom BCM4334)** | **Validated on Hardware** | 2026-10-12 | Association and DHCP operational via NetworkManager |
| **Unified Partitioning (14.5 GiB)** | **Validated on Hardware** | 2026-10-12 | `mmcblk0p8` formatted ext4, 0 errors |
| **TWRP Recovery Partition Safety** | **Validated on Hardware** | 2026-10-14 | Exact readback SHA256 match; untouched |
| **Boot Image 7.5 MiB Budget** | **Validated on Hardware** | 2026-10-14 | `7,350,272` bytes (Margin: `502 KiB`) |
| **KDE Breeze Dark Kiosk Wizard** | **Validated on Hardware** | 2026-10-14 | Frameless 1280x800 full-screen touch wizard |
| **Clean Flash via `install.sh`** | **Validated on Hardware** | 2026-10-14 | Bit-by-bit readback SHA256 exact match |

---

## 12. Contributing & Guidelines

Contributions are welcome! Please follow these rules:
1. **Never commit binary blobs, proprietary firmware, or partition dumps.**
2. **Never commit personal credentials, MAC addresses, or device serials.**
3. Run the repository cleanliness guard before submitting pull requests:
   ```bash
   ./scripts/lib/check_repo_clean.sh
   ```

---

## 13. License & Credits

- **Kernel Patches & Device Trees**: Licensed under **GPL-2.0-only**.
- **Scripts, Setup Wizard & Documentation**: Licensed under **MIT License**.
- **Third-Party Attributions**: See [`NOTICE`](NOTICE) and [`docs/THIRD_PARTY.md`](docs/THIRD_PARTY.md).


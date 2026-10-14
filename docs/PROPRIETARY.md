# NoteOS — Proprietary Components & Extraction Guide

This document provides a comprehensive inventory of non-redistributable proprietary components required for NoteOS hardware functionality on the Samsung Galaxy Note 10.1 (GT-N8000), along with legitimate methods for obtaining them.

---

## 1. Proprietary Components Inventory

| Component | Why NoteOS Needs It | License / Legal Status | Why It Is Excluded | How to Obtain Legally | Expected SHA256 Checksum | Local Destination |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`brcmfmac4334-sdio.bin`** | Broadcom BCM4334 Wi-Fi baseband firmware | Proprietary (Broadcom / Cypress) | Redistribution prohibited without explicit commercial agreement | Extracted from your own device backup via `scripts/02_extract_firmware.sh`, or obtained from Debian package `firmware-brcm80211` ([Debian Package](https://packages.debian.org/bookworm/firmware-brcm80211)) *(Verified: 2026-10-14, HTTP 200)* | `7b4eebe4d3bbc9a8bf3c2d55d9404cf0ed9cce3388b3d5708d2352d0af89eeb3` | `proprietary/brcmfmac4334-sdio.bin` |
| **`BCM4334B0.hcd`** | Broadcom BCM4334 Bluetooth Patchram firmware | Proprietary (Broadcom / Samsung) | Redistribution prohibited | Extracted from your own tablet or stock Samsung `system.img` (`/vendor/firmware/bcm4334.hcd`) via `scripts/02_extract_firmware.sh` | `613651c0506c0ddec78788d13a8a4a3d3077468cd8445df58773c76b98b10963` | `proprietary/BCM4334B0.hcd` |
| **`brcmfmac4334-sdio.txt`** | Broadcom BCM4334 NVRAM RF calibration parameters | Proprietary / Device-specific calibration data | Contains device-specific calibration and hardware MAC address | Extracted from your own tablet or stock `system.img` (`/etc/wifi/nvram_net.txt`) and personalized with factory MAC from `/efs/wifi/.mac.info` via `scripts/02_extract_firmware.sh` | Generated per-device | `proprietary/brcmfmac4334-sdio.txt` |
| **`brcmfmac4334-sdio.samsung,n8000.txt`** | Board-compatible symlink/copy of NVRAM calibration | Proprietary / Device-specific calibration data | Required by Linux kernel brcmfmac driver for device tree matching (`samsung,n8000`) | Created automatically as a duplicate of `brcmfmac4334-sdio.txt` by `scripts/02_extract_firmware.sh` | Generated per-device | `proprietary/brcmfmac4334-sdio.samsung,n8000.txt` |
| **Samsung Stock Partitions** (`system.img`, `param.img`, `radio.img`, `boot.img`, `recovery.img`) | Stock Android firmware and modem radio code | Proprietary (Samsung Electronics) | Commercial copyrighted firmware; redistribution strictly prohibited | Backed up from your own device before flashing via `scripts/01_backup_device.sh`. Sources for stock open-source kernel components: [Samsung Open Source](https://opensource.samsung.com/) *(Status: UNVERIFIED - HTTP 403 Cloudflare WAF on automated check 2026-10-14)* | Device-dependent | Stored locally in `../NoteOs-private/backup/` (never in Git) |
| **Samsung EFS Partition** (`efs.img`) | Non-volatile device calibration, IMEI, RF tuning, factory MAC | Strictly Private / Confidential | Contains device IMEI and sensitive factory cryptographic data | Dumped from your device using `scripts/01_backup_device.sh`. **NEVER share, upload, or publish this file anywhere.** | Unique per physical unit | `../NoteOs-private/backup/efs.img` (never in Git) |

---

## 2. Automated Extraction from Device Backup

NoteOS provides an automated extraction tool that populates the `proprietary/` directory directly from your device backup:

```bash
# 1. Back up your connected device (tablet in TWRP mode)
./scripts/01_backup_device.sh

# 2. Extract Wi-Fi and Bluetooth firmware into proprietary/
./scripts/02_extract_firmware.sh
```

The script automatically verifies checksums against `build/proprietary/MANIFEST.sha256` and prepares the files for installation.

---

## 3. Alternative: Manual Extraction via ADB from TWRP

If you have a working GT-N8000 connected in TWRP recovery mode:

```bash
# Extract Wi-Fi firmware
adb shell "mount /system 2>/dev/null || true"
adb shell "cat /system/etc/wifi/bcm4334.bin" > proprietary/brcmfmac4334-sdio.bin

# Extract Bluetooth patchram
adb shell "cat /system/vendor/firmware/bcm4334.hcd" > proprietary/BCM4334B0.hcd

# Extract NVRAM calibration
adb shell "cat /system/etc/wifi/nvram_net.txt" > proprietary/brcmfmac4334-sdio.txt
cp proprietary/brcmfmac4334-sdio.txt proprietary/brcmfmac4334-sdio.samsung,n8000.txt
```


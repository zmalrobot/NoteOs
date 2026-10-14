# NoteOS — Proprietary Files Directory

This directory (`proprietary/`) is intended solely for local storage of non-redistributable proprietary binary files required by NoteOS for hardware operation (such as Wi-Fi and Bluetooth firmware blobs).

## Privacy & Legal Notice
- **Files in this directory are strictly excluded from version control (`.gitignore`).**
- **NEVER commit any file from this directory to Git.**
- **NEVER distribute proprietary firmware files across public channels.**

## Required Files for GT-N8000
When preparing to install NoteOS on a Samsung Galaxy Note 10.1 (GT-N8000), the following files must be populated in this directory:

1. **`brcmfmac4334-sdio.bin`**: Broadcom BCM4334 Wi-Fi firmware
   - *Expected SHA256*: `7b4eebe4d3bbc9a8bf3c2d55d9404cf0ed9cce3388b3d5708d2352d0af89eeb3`
   - *How to obtain*: Available via Debian package `firmware-brcm80211` or extracted from your device backup using `scripts/02_extract_firmware.sh`.
2. **`BCM4334B0.hcd`**: Broadcom BCM4334 Bluetooth patchram firmware
   - *Expected SHA256*: `613651c0506c0ddec78788d13a8a4a3d3077468cd8445df58773c76b98b10963`
   - *How to obtain*: Extracted from your device backup (`/vendor/firmware/bcm4334.hcd`) using `scripts/02_extract_firmware.sh`.
3. **`brcmfmac4334-sdio.txt` & `brcmfmac4334-sdio.samsung,n8000.txt`**: NVRAM Wi-Fi calibration file
   - *How to obtain*: Generated from your device backup or live tablet by `scripts/02_extract_firmware.sh` with your tablet's factory MAC address read from `/efs/wifi/.mac.info`.

For step-by-step instructions and full legal documentation, see [`docs/PROPRIETARY.md`](../docs/PROPRIETARY.md).


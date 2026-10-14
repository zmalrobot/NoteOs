# NoteOS — Troubleshooting & Diagnostic Guide

This guide addresses common diagnostic scenarios, recovery steps, and debugging procedures for NoteOS on Samsung Galaxy Note 10.1 (GT-N8000).

---

## CRITICAL PRIVACY WARNING
> [!CAUTION]
> **NEVER upload, paste, or attach the following data in public GitHub issues, forum threads, or pull requests:**
> - Partition dumps of `EFS` (`efs.img`), `PARAM` (`param.img`), or `RADIO` (`radio.img`)
> - Device **IMEI** (15 digits) or device **serial number** (from `adb devices` or `/efs/`)
> - Hardware **MAC address** (Wi-Fi or Bluetooth)
> - Wi-Fi passwords, SSIDs, or private network configuration files (`/etc/NetworkManager/system-connections/*`)
>
> Doing so may permanently compromise your device identity and expose sensitive private network credentials.

---

## Common Issues and Solutions

### 1. Tablet stays stuck on Samsung logo (Boot Loop)
- **Cause A: Boot image exceeded partition limit**
  - The `BOOT` partition (`mmcblk0p5`) on GT-N8000 is strictly 8 MiB (8,388,608 bytes). If `boot.img` exceeds 7.5 MiB (7,864,320 bytes), S-BOOT bootloader fails to decompress the kernel.
  - *Fix*: Check `stat -c%s release/boot.img`. Ensure it is <= 7,864,320 bytes.
- **Cause B: S-BOOT MMU Cache incompatibility**
  - S-BOOT leaves the L1/L2 caches in an inconsistent state when executing the kernel decompressor.
  - *Fix*: Ensure patch `0003-ARM-compressed-head-bypass-cache_on-sboot.patch` is applied to your kernel build.
- **Recovery Action**:
  - Hold **Power + Volume Up** until the tablet reboots into TWRP recovery.
  - Run `./scripts/09_rollback.sh` from your PC to restore your working boot backup.

### 2. Wi-Fi or Bluetooth fails to turn on
- **Cause: Missing proprietary firmware or NVRAM**
  - The Linux kernel driver `brcmfmac` requires `brcmfmac4334-sdio.bin` and the board-specific NVRAM calibration file `brcmfmac4334-sdio.samsung,n8000.txt`.
- **Diagnosis**:
  - Run `dmesg | grep brcm` in a terminal.
  - If you see `brcmfmac: Direct firmware load for ... failed with error -2`, the firmware blobs were not installed.
- **Fix**:
  - Boot tablet into TWRP recovery.
  - Run `./scripts/02_extract_firmware.sh` to populate `proprietary/`.
  - Run `./scripts/07_install.sh --stage firmware` to install the blobs.

### 3. Setup Wizard (`noteos-setup`) does not appear
- **Diagnosis**:
  - Check the kiosk service status:
    ```bash
    systemctl status noteos-firstboot.service
    ```
  - Verify that the marker `/var/lib/noteos/setup.done` does NOT exist:
    ```bash
    ls -l /var/lib/noteos/setup.done
    ```
- **Fix**:
  - If the setup wizard exited prematurely, remove the completion marker and restart the service:
    ```bash
    sudo rm -f /var/lib/noteos/setup.done
    sudo systemctl restart noteos-firstboot.service
    ```

### 4. Hardware Key Combinations Reference
- **TWRP Recovery Mode**: Hold **Power + Volume Up** until the Samsung logo appears, then release Power while continuing to hold Volume Up.
- **Odin / Download Mode**: Hold **Power + Volume Down** until the warning screen appears, then press **Volume Up** to confirm.
- **Forced Hard Reset**: Hold **Power** continuously for 10–12 seconds until the screen turns black and power cycles.


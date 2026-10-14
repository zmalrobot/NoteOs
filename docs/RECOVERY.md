# NoteOS — TWRP Recovery, Key Combinations, and Restoration Guide

**Target Device**: Samsung Galaxy Note 10.1 3G (`GT-N8000` / `p4noterf`)  
**Recovery Partition (`mmcblk0p6`)**: **TWRP 3.7.0_9-0** (`8,388,608` bytes, SHA256: `894508b9f5cae24e047c7fdb1fb6d7f011f13ce9b36e5c844e9efd2b91cc6099`)

> [!IMPORTANT]
> **RECOVERY INTEGRITY RULE**:
> 1. The `RECOVERY` partition (`/dev/block/mmcblk0p6`) **must never be overwritten, modified, or wiped**. It serves as the permanent hardware safety net for device access and recovery.
> 2. **Never use the graphical Wipe / Format / Mount menus inside TWRP**: Because Android partitions `p8..p12` are merged into a single `mmcblk0p8` partition for NoteOS, TWRP's built-in `recovery.fstab` expects the legacy layout (where `p8` was `/cache` and `p12` was `/data`). It is expected that the TWRP GUI may show warnings for `/cache` or `/data`. Operate exclusively via `adb shell` using block devices or `/dev/block/platform/dw_mmc/by-name/`.

---

## 1. Physical Hardware Keys & Verified Button Combinations

Holding the tablet horizontally with the front camera at the top:
- **Power Button**: On the far left of the top edge.
- **Volume Rocker**: Immediately to the right of Power:
  - **Volume Down**: The side of the rocker **closest** to the Power button.
  - **Volume Up**: The side of the rocker **farthest** from the Power button.
- *There is no physical front Home button.*

### 1.1 Entering TWRP Recovery
1. Power off the device completely (if frozen, hold **Power for 10–15 seconds**).
2. Press and hold **Power + Volume Up** simultaneously.
3. As soon as the white *"Samsung Galaxy Note 10.1"* logo appears, **release Power**, but **continue holding Volume Up** for 3–5 seconds until TWRP launches.

### 1.2 Entering Download Mode (Odin / Heimdall)
1. Power off the device completely.
2. Press and hold **Power + Volume Down** simultaneously.
3. When the yellow warning triangle appears (*"Warning!! A custom OS can cause critical problems..."*), release both buttons.
4. Press **Volume Up** once to confirm (*Continue*).
5. The device displays the green robot: *"Downloading... Do not turn off target!!"*.

### 1.3 Recovering from a Bootloop or Kernel Panic
Because `BOOT` (`mmcblk0p5`) and `RECOVERY` (`mmcblk0p6`) are physically distinct partitions and `boot.img` is strictly bounded to `<= 7.5 MiB`:
1. Hold **Power + Volume Up** continuously for **10–12 seconds** until the hardware PMIC resets (the screen turns black and the logo reappears).
2. Release Power immediately while keeping Volume Up depressed.
3. S-BOOT boots directly into **TWRP Recovery**, providing immediate `adb` shell access.

---

## 2. Reinstalling NoteOS from TWRP

Connect the tablet via USB in TWRP recovery mode:

```bash
# 1. Dry-run simulation (verifies all checks without writing)
./scripts/07_install.sh --dry-run

# 2. Complete guided installation
./scripts/07_install.sh --full
```

---

## 3. Restoring Boot from Backup (Rollback)

### 3.1 Via Automated Script
```bash
# Restore previous boot partition from local backup:
./scripts/09_rollback.sh
```

### 3.2 Via Low-Level ADB Shell
```bash
# Push backup image to /tmp and flash with fsync
adb push backup/boot_pre_install.img /tmp/boot.img
adb shell "dd if=/tmp/boot.img of=/dev/block/platform/dw_mmc/by-name/BOOT bs=4096 conv=fsync"
adb shell "sync"
```

### 3.3 Via Download Mode (Heimdall)
If ADB is unavailable:
```bash
heimdall detect
heimdall flash --BOOT backup/boot_pre_install.img
```

To revert the entire eMMC disk to stock 12-partition layout and restore Android, see [`docs/REPARTITION.md`](REPARTITION.md).


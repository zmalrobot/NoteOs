# NoteOS — eMMC Repartitioning Architecture & Manual Guide

**Target Device**: Samsung Galaxy Note 10.1 3G (`GT-N8000` / `p4noterf`)  
**Status**: One-time manual or script-assisted procedure (Verified on hardware: 2026-10-12).

> [!CAUTION]
> **REPARTITIONING CARRIES INHERENT RISK OF BRICKING AND DATA LOSS**:
> Repartitioning modifies the hardware eMMC partition table. The installer (`scripts/07_install.sh`) **refuses** to flash if it detects an invalid partition table. You MUST have created a complete backup using `scripts/01_backup_device.sh` before modifying any partitions.

---

## 1. eMMC Disk Architecture (`/dev/block/mmcblk0`) on GT-N8000

Inspection of the physical 16 GB eMMC disk (`15,758,000,128` bytes, `30,777,344` sectors of 512 bytes = `14.68 GiB`) demonstrates that the Samsung GT-N8000 combines **two partitioning structures**:

1. **Standard GPT Table (`label: gpt`)**:
   - Occupies sectors **LBA `0..33`** (Protective MBR at `LBA 0`, Primary GPT Header at `LBA 1`, 128 GPT partition entries at `LBA 2..33`, with `first-lba: 34`) and the trailing 33 sectors (**LBA `30777311..30777343`**, `last-lba: 30777310`).
   - Disk `label-id`: `52444E41-494F-2044-4D4D-43204449534B` (ASCII encoding of `"ANDROID MMC DISK"`).
2. **Samsung Proprietary `PIT` Table (`note10.pit`, magic `0x12349876`) and `MD5HDR`**:
   - Physical location: **LBA `34..49`** (16 sectors = 8 KiB), situated *outside* the GPT entries but *before* the first partition (`p1 BOTA0` at `LBA 8192`).
   - `MD5HDR` header (`md5.img`): **LBA `50..2097`** (2048 sectors = 1 MiB).
   - Bootloaders (`sboot.bin`) and TrustZone firmware (`tz.img`) reside in the separate hardware boot partition **`/dev/block/mmcblk0boot0`** (2 MiB, read-only).

### Golden Rule for Bootloader Safety (S-BOOT)
S-BOOT boots **Download Mode (Odin)**, **TWRP Recovery** (`p6`), and **BOOT** (`p5`) reliably if and only if:
- `/dev/block/mmcblk0boot0`, `/dev/block/mmcblk0boot1`, and sectors **LBA `34..8191`** (`PIT` + `MD5HDR`) are **NEVER modified**.
- The first 7 GPT partitions (**`p1 BOTA0`**, **`p2 BOTA1`**, **`p3 EFS`**, **`p4 PARAM`**, **`p5 BOOT`**, **`p6 RECOVERY`**, **`p7 RADIO`**, sectors `8192..180223`) remain **100% identical** in number, start sector, size, type GUID, name, and Samsung ASCII PARTUUID.

---

## 2. Stock Android Layout (12 Partitions) vs NoteOS Unified Layout (8 Partitions)

All 7 protected partitions (`p1..p7`) reside at the beginning of the disk (`8192..180223`). The 5 Android partitions (`p8 CACHE`, `p9 SYSTEM`, `p10 HIDDEN`, `p11 OTA`, `p12 USERDATA`) were contiguous from sector **`180224`** to **`30769151`** without any protected partition in between. NoteOS merges them into a **single unified partition `mmcblk0p8`** of **`14.59 GiB`** (`30,588,928` sectors):

| Partition | Label (`PARTLABEL`) | Sectors in Stock Layout (12 Partitions) | Sectors in NoteOS Layout (8 Partitions) | Current Size | Status in NoteOS |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `mmcblk0p1` | `BOTA0` | `8192 .. 16383` (`8192`) | `8192 .. 16383` (`8192`) | 4.00 MiB | **UNCHANGED** |
| `mmcblk0p2` | `BOTA1` | `16384 .. 24575` (`8192`) | `16384 .. 24575` (`8192`) | 4.00 MiB | **UNCHANGED** |
| `mmcblk0p3` | `EFS` | `24576 .. 65535` (`40960`) | `24576 .. 65535` (`40960`) | 20.00 MiB | **UNCHANGED** |
| `mmcblk0p4` | `PARAM` | `65536 .. 81919` (`16384`) | `65536 .. 81919` (`16384`) | 8.00 MiB | **UNCHANGED** |
| `mmcblk0p5` | `BOOT` | `81920 .. 98303` (`16384`) | `81920 .. 98303` (`16384`) | 8.00 MiB | **UNCHANGED** (NoteOS Kernel) |
| `mmcblk0p6` | `RECOVERY` | `98304 .. 114687` (`16384`) | `98304 .. 114687` (`16384`) | 8.00 MiB | **UNCHANGED** (TWRP Recovery) |
| `mmcblk0p7` | `RADIO` | `114688 .. 180223` (`65536`) | `114688 .. 180223` (`65536`) | 32.00 MiB | **UNCHANGED** |
| `mmcblk0p8` | `USERDATA` | `180224 .. 385023` (100 MiB) | **`180224 .. 30769151` (`30588928`)** | **`14.59 GiB`** | **UNIFIED (`LABEL=debian_root`)** |
| *(ex `p9`)* | *(ex `SYSTEM`)* | `385024 .. 7553023` (3500 MiB) | *(Merged into `mmcblk0p8`)* | — | Deleted |
| *(ex `p10`)* | *(ex `HIDDEN`)* | `7553024 .. 8577023` (500 MiB) | *(Merged into `mmcblk0p8`)* | — | Deleted |
| *(ex `p11`)* | *(ex `OTA`)* | `8577024 .. 8593407` (8 MiB) | *(Merged into `mmcblk0p8`)* | — | Deleted |
| *(ex `p12`)* | *(ex `USERDATA`)* | `8593408 .. 30769151` (10828 MiB) | *(Merged into `mmcblk0p8`)* | — | Deleted |

---

## 3. Repartitioning Workflow

1. Boot device into TWRP recovery.
2. Back up existing layout:
   ```bash
   ./scripts/01_backup_device.sh
   ```
3. Test layout eligibility in dry-run mode:
   ```bash
   ./scripts/03_repartition.sh --dry-run
   ```
4. If eligible, apply with explicit confirmation:
   ```bash
   ./scripts/03_repartition.sh --apply
   ```
5. Format the new unified root partition:
   ```bash
   adb shell "mke2fs -t ext4 -L debian_root -F /dev/block/mmcblk0p8"
   adb shell "e2fsck -fy /dev/block/mmcblk0p8"
   ```

---

## 4. Restoring Stock 12-Partition Layout (Rollback)

To return the tablet to the stock 12-partition layout:
```bash
# Push original sfdisk table from backup
adb push backup/mmcblk0_sfdisk_original.dump /tmp/orig.sfdisk
adb shell "sfdisk --wipe=never /dev/block/mmcblk0 < /tmp/orig.sfdisk"
adb shell "blockdev --rereadpt /dev/block/mmcblk0"
```
See [`docs/RECOVERY.md`](RECOVERY.md) for full Android system restoration steps.


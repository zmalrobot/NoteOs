# NoteOS — Emergency Rollback & Restoration Guide

**Target Device**: Samsung Galaxy Note 10.1 3G (`GT-N8000` / `p4noterf`)  
**Status**: Verified on Hardware

---

## 1. Restoring Android Boot from TWRP Recovery

If you have flashed NoteOS or a custom kernel to the `BOOT` partition (`mmcblk0p5`) and wish to restore your original stock boot image, your backup is preserved in your private backup directory (`backup/boot.img` or `backup/boot_pre_install.img`).

### Method A: Automated Rollback via Script (Recommended)
```bash
./scripts/09_rollback.sh
```

### Method B: Low-Level ADB Shell
```bash
# Push backup image to device RAM (tmpfs)
adb push backup/boot_pre_install.img /tmp/boot.img

# Flash to BOOT partition by name with sync
adb shell "dd if=/tmp/boot.img of=/dev/block/platform/dw_mmc/by-name/BOOT bs=4096 conv=fsync"
adb shell "sync"

# Reboot device
adb reboot
```

---

## 2. Restoring from Download Mode (Heimdall)

If the device cannot reach TWRP recovery:
1. Hold **Power + Volume Down** until the warning screen appears, then press **Volume Up** to enter Download Mode.
2. Connect USB cable to PC.
3. Flash the stock boot partition:
   ```bash
   heimdall detect
   heimdall flash --BOOT backup/boot_pre_install.img
   ```

---

## 3. Full Android System & GPT Restoration

To revert the partition table back to the stock 12-partition layout and restore Android:

```bash
# 1. Boot into TWRP Recovery and unmount partitions
adb shell "umount /cache /data /system /efs /sdcard /mnt 2>/dev/null || true"

# 2. Restore stock partition table
adb push backup/mmcblk0_sfdisk_original.dump /tmp/orig.sfdisk
adb shell "sfdisk --wipe=never /dev/block/mmcblk0 < /tmp/orig.sfdisk"
adb shell "sync && blockdev --rereadpt /dev/block/mmcblk0"

# 3. Format restored Android partitions
adb shell "mke2fs -t ext4 -F /dev/block/mmcblk0p8"   # CACHE (100 MiB)
adb shell "mke2fs -t ext4 -F /dev/block/mmcblk0p10"  # HIDDEN (500 MiB)
adb shell "mke2fs -t ext4 -F /dev/block/mmcblk0p12"  # USERDATA (~10.8 GiB)

# 4. Restore stock SYSTEM and BOOT
adb push backup/boot.img /tmp/boot.img
adb shell "dd if=/tmp/boot.img of=/dev/block/mmcblk0p5 bs=4096 conv=fsync"
adb shell -T "dd of=/dev/block/mmcblk0p9 bs=1M conv=fsync" < backup/system.img
adb shell "sync"
```


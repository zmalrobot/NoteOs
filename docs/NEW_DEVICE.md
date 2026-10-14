# NoteOS — Porting Guide: Adding a New Device

The architecture of **NoteOS** separates generic build recipes (`build/kernel/`, `build/initramfs/`, `build/rootfs/`, `build/wizard/`, `scripts/`) from device-specific hardware definitions, stored exclusively under `build/devices/<codename>/`.

---

## 1. Directory Structure

To start a new port, duplicate the base template:
```bash
cp -r build/devices/_template build/devices/<codename>
```

A complete device directory contains:
```text
build/devices/<codename>/
├── device.conf                        # Partition layout, mkbootimg parameters, kernel cmdline, arch
├── kernel.config                      # Kconfig fragment merged into the SoC defconfig
├── dts/
│   └── <soc>-<board>.dts              # Device Tree Source (if not already upstream in mainline)
├── patches/
│   └── 0001-*.patch                   # Kernel patches applied sequentially
├── partition-layout-original.sfdisk   # Stock partition layout dump
├── partition-layout-current.sfdisk    # Unified partition layout dump for NoteOS
└── partitions.conf                    # Mappings of protected and writable partitions
```

---

## 2. Configuring `device.conf`

1. **Partition Identification via TWRP**:
   Boot the target device into TWRP and inspect:
   ```bash
   adb shell "ls -la /dev/block/platform/*/by-name/"
   adb shell "cat /proc/partitions"
   ```
2. **Stock `boot.img` Parameters**:
   Extract the stock `BOOT` partition (`dd if=... of=boot_stock.img`) and identify `base`, `pagesize`, `kernel_offset`, `ramdisk_offset`, `tags_offset`, and default `cmdline`.
3. **Partition Size Limit**:
   Set `BOOT_IMAGE_MAX_BYTES` leaving at least **512 KiB** safety margin below the physical `BOOT` partition size (e.g., `7864320` bytes / 7.5 MiB for an 8 MiB physical partition).
4. **Proprietary Firmware**:
   Document all proprietary firmware blobs required in `docs/PROPRIETARY.md` and record expected checksums in `build/proprietary/MANIFEST.sha256`. Never commit binary blobs to the Git repository.

---

## 3. Building and Verification

```bash
make kernel DEVICE=<codename>
make rootfs DEVICE=<codename>
make boot DEVICE=<codename>
```

Build outputs are placed in `out/<codename>/`:
- `boot.img` (release, silent) and `boot-debug.img` (diagnostic `debug=1`)
- `rootfs.tar.gz`
- `manifest.txt`


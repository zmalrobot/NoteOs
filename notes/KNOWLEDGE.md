# NoteOS — Technical Knowledge & Hardware Architecture (GT-N8000 / "p4note")

> **NOTICE**: This document records verified technical knowledge, hardware specifications, and upstream findings for running mainline Linux and Debian on the Samsung Galaxy Note 10.1 (`GT-N8000`). All findings are derived from verified upstream repositories, kernel documentation, Replicant/postmarketOS sources, and empirical tests.

---

## 1. Boot Chain Architecture on Exynos 4412

### 1.1 Hardware Bootloader Stages
1. **iROM (Boot ROM)**: `[VERIFIED]`
   - Internal ROM hardcoded into the Exynos 4412 SoC.
   - Initializes basic clocks and loads Stage 1 (`BL1`) from the hardware boot partition `mmcblk0boot0`.
2. **BL1 (Primary Bootloader)**: `[VERIFIED]`
   - Executes in internal iRAM; verifies and loads Stage 2 (`BL2` / `SPL`).
3. **BL2 / SPL (Secondary Program Loader)**: `[VERIFIED]`
   - Configures LPDDR2 DRAM memory controllers and loads `S-BOOT`.
4. **S-BOOT (Samsung Proprietary Bootloader / sboot.bin)**: `[VERIFIED]`
   - Initializes the display with the stock Samsung logo.
   - Reads the PIT (Partition Information Table) and GPT partition table.
   - On normal boot: loads the `BOOT` partition (`mmcblk0p5`) into RAM at `0x40008000`.
   - On Recovery button combo: loads `RECOVERY` (`mmcblk0p6`).
   - On Download combo: enters Odin / Download mode.

### 1.2 Android `boot.img` Structure & Offsets
S-BOOT parses standard Android `boot.img` header format version 0:
- **Base Address**: `0x40000000` `[VERIFIED]`
- **Page Size**: `2048` bytes `[VERIFIED]`
- **Kernel Offset**: `0x00008000` (Loaded at `0x40008000`) `[VERIFIED]`
- **Ramdisk Offset**: `0x01000000` (Loaded at `0x41000000`) `[VERIFIED]`
- **Tags Offset**: `0x00000100` (Loaded at `0x40000100`) `[VERIFIED]`
- **Header Version**: `0` `[VERIFIED]`
- **Physical Partition Limit**: `8,388,608` bytes (8 MiB). Any image >= 8 MiB causes decompressor failure in S-BOOT. NoteOS enforces a strict limit of `7,864,320` bytes (7.5 MiB).

### 1.3 Mainline Kernel Decompressor Cache State Quirk
- **Finding**: On Exynos 4412 with Samsung S-BOOT, calling `cache_on` in the ARM zImage decompressor (`arch/arm/boot/compressed/head.S`) causes execution freeze due to pre-existing MMU state set by S-BOOT at `0x40004000`.
- **Resolution**: Patch `0003-ARM-compressed-head-bypass-cache_on-sboot.patch` bypasses decompressor `cache_on`. The kernel decompresses cleanly in ~1 second with MMU off. `[VERIFIED]`

---

## 2. Hardware Subsystems & Driver Mapping

| Subsystem | Hardware Component | Linux Kernel Driver | Status in NoteOS | Technical Details |
| :--- | :--- | :--- | :--- | :--- |
| **CPU** | Samsung Exynos 4412 Quad Cortex-A9 (1.4 GHz) | `arch/arm/mach-exynos/` | **WORKING** `[VERIFIED]` | All 4 cores active with cpufreq support. |
| **GPU** | ARM Mali-400 MP4 (4 fragment cores, 1 vertex core) | `drivers/gpu/drm/lima/` | **WORKING** `[VERIFIED]` | Full OpenGL ES 2.0 acceleration via Mesa Lima. Modesetting on DRM. |
| **Display Panel** | Samsung SEC 10.1" WXGA (1280x800, 16:10) | `drivers/gpu/drm/panel/` | **WORKING** `[VERIFIED]` | Native 1280x800 resolution at 60 Hz. |
| **Touchscreen** | Melfas MMS134S / MMS136 Multi-touch I2C | `drivers/input/touchscreen/melfas_mms114.c` | **WORKING** `[VERIFIED]` | Multi-touch functional out-of-the-box via libinput. |
| **Wi-Fi** | Broadcom BCM4334 SDIO | `drivers/net/wireless/broadcom/brcm80211/brcmfmac/` | **WORKING** `[VERIFIED]` | Requires `brcmfmac4334-sdio.bin` and board NVRAM. |
| **Bluetooth** | Broadcom BCM4334 UART | `drivers/bluetooth/hci_bcm.c` | **WORKING** `[VERIFIED]` | Requires `BCM4334B0.hcd` patchram uploaded at 3 Mbps. |
| **Power & Battery** | Maxim MAX77686 PMIC + SMB347 Charger | `drivers/mfd/max77686.c`, `drivers/power/supply/` | **WORKING** `[VERIFIED]` | Battery percentage, charging status, and PMIC regulators functional. |
| **Audio** | Wolfson Microelectronics WM1811 (I2S) | `sound/soc/samsung/`, `sound/soc/codecs/wm8994.c` | **WORKING** `[VERIFIED]` | ALSA and PipeWire operational for stereo output. |
| **Storage** | Samsung eMMC 4.41 (dw_mmc) | `drivers/mmc/host/dw_mmc-exynos.c` | **WORKING** `[VERIFIED]` | High-speed eMMC mode active. Partition mmcblk0p8 formatted ext4. |
| **USB Gadget** | Synopsys DesignWare HSOTG / DWC2 | `drivers/usb/gadget/udc/dwc2/` | **WORKING** `[VERIFIED]` | USB RNDIS networking operational in diagnostic mode. |


# NoteOS — Third-Party Notices & Credits

This document attributes third-party open-source components, device tree authors, community projects, and upstream software utilized in the NoteOS project.

---

## 1. Upstream Projects and Licenses

### Linux Kernel
- **Upstream Project**: Linux Kernel Organization ([kernel.org](https://www.kernel.org/)) *(Verified: 2026-10-14, HTTP 200)*
- **Kernel Version**: 6.6.158 LTS
- **License**: GNU General Public License version 2.0 only (`GPL-2.0-only`)
- **Notice**: Kernel source code is not bundled within this repository; tarballs are retrieved directly from `https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.6.158.tar.xz` *(Verified: 2026-10-14, HTTP 200)* and verified with SHA256 checksums.

### Samsung Exynos & p4note Device Tree Authors
- **Files**: `arch/arm/boot/dts/samsung/exynos4412-p4note.dtsi`, `exynos4412-p4note-n8010.dts`, `exynos4412-p4note-n8000.dts`
- **Copyright**: Copyright (c) 2013 Samsung Electronics Co., Ltd.
- **License**: `GPL-2.0-only`
- **Upstream References**:
  - `exynos4412-p4note.dtsi`: [kernel.org cgit](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm/boot/dts/samsung/exynos4412-p4note.dtsi) *(Verified: 2026-10-14, HTTP 200)*
  - `exynos4412-p4note-n8010.dts`: [kernel.org cgit](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm/boot/dts/samsung/exynos4412-p4note-n8010.dts) *(Verified: 2026-10-14, HTTP 200)*
- **Community Authors & Maintainers**:
  - PostmarketOS p4note port maintainers (Simon Shields, Henrik Grimler). Reference: [PostmarketOS p4note Wiki](https://wiki.postmarketos.org/wiki/Samsung_Galaxy_Note_10.1_(samsung-p4note)) *(Verified: 2026-10-14, HTTP 200)*
  - Replicant Project Exynos 4412 research contributors. Reference: [Replicant Wiki](https://redmine.replicant.us/projects/replicant/wiki/Exynos4412Devices) *(Verified: 2026-10-14, HTTP 200)*

### Android Open Source Project (AOSP) — mkbootimg
- **File**: `scripts/lib/mkbootimg.py`
- **Copyright**: Copyright (C) 2015, The Android Open Source Project
- **License**: Apache License, Version 2.0 ([Apache 2.0](http://www.apache.org/licenses/LICENSE-2.0)) *(Verified: 2026-10-14, HTTP 200)*

### Debian GNU/Linux
- **Distribution**: Debian 12 (Bookworm) `armhf`
- **Project**: The Debian Project ([debian.org](https://www.debian.org/)) *(Verified: 2026-10-14, HTTP 200)*
- **License**: Debian Free Software Guidelines (DFSG) compliant software packages.

### Desktop Environments
- **KDE Plasma**: Copyright (C) KDE Community ([invent.kde.org](https://invent.kde.org/)) *(Verified: 2026-10-14, HTTP 200)* — LGPL-2.1+ / GPL-2.0+
- **LXQt**: Copyright (C) LXQt Team ([lxqt-project.org](https://lxqt-project.org/)) *(Verified: 2026-10-14, HTTP 200)* — LGPL-2.1+ / GPL-2.0+

### Plymouth Boot Splash
- **Project**: Plymouth ([freedesktop.org](https://www.freedesktop.org/wiki/Software/Plymouth/)) *(Verified: 2026-10-14, HTTP 200)*
- **License**: GPL-2.0+

### TWRP Recovery
- **Project**: TeamWin Recovery Project ([twrp.me](https://dl.twrp.me/n8000/)) *(Verified: 2026-10-14, HTTP 200)*
- **Notice**: TWRP is used as the recovery environment and installation facilitator. NoteOS modifies neither the TWRP partition nor its binary code.

---

## 2. Disclaimer Regarding Proprietary Samsung Firmware
This repository contains NO Samsung proprietary firmware, NO stock Android images, and NO Broadcom binary blobs. All proprietary components required for hardware operation must be extracted independently by the user from their own legally owned device using `scripts/02_extract_firmware.sh`, as documented in [`docs/PROPRIETARY.md`](PROPRIETARY.md).


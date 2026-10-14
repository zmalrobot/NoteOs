# NoteOS — Curated Application Catalog & ARMv7 armhf Verification

**Verification Date**: 2026-10-13  
**Target Hardware**: Samsung Galaxy Note 10.1 (`GT-N8000`), Samsung Exynos 4412 Quad-Core ARM Cortex-A9 (`ARMv7-A`, `armhf`, `VFPv3` + `NEON`), 2 GiB RAM, Debian 12 Bookworm (`armhf`).

---

## 1. Multi-Stage Verification Method

Before inclusion in the setup wizard catalog (`build/wizard/catalog.py`), every candidate application was verified against real Debian 12 Bookworm `armhf` repositories (and the official Microsoft `armhf` repository for Visual Studio Code):

1. **Package Existence**: Verified with `apt-cache policy <pkg>:armhf`.
2. **Installation Simulation**: Simulated with `apt-get -s --no-install-recommends install <pkg>` against the clean base rootfs to calculate package dependencies, download size (`Size`), and uncompressed disk footprint (`Installed-Size`).
3. **Binary ELF Inspection (`file` + `readelf -A`)**: Every package binary was extracted and checked to confirm:
   - `ELF 32-bit LSB pie executable, ARM, EABI5 version 1 (SYSV), dynamically linked, interpreter /lib/ld-linux-armhf.so.3`
   - `Tag_CPU_arch: v7`
   - `Tag_FP_arch: VFPv3-D16` and `Tag_ABI_VFP_args: VFP registers`
   - **Zero ARMv8, VFPv4, or unsupported cryptographic extensions** that would cause SIGILL on Cortex-A9.

---

## 2. Dynamic 20-App Catalog Rule

The setup wizard always presents **exactly 20 installable applications** on Screen 5:
- **4 primary candidates are unavailable on 32-bit `armhf`** (`OnlyOffice`, `Spotify`, `Steam`, `Thunderbird`): They are placed in the *"Unavailable on this device (armhf)"* section with a one-line technical explanation, and their slots are dynamically filled by the **first 4 reserves** (`Strawberry`, `Kdenlive`, `Flameshot`, `Syncthing`).
- **On LXQt**, `FeatherPad` (slot #14) and `LXImage-Qt` (slot #15) are already included in the base desktop list (`build/rootfs/desktops/lxqt.list`): they appear in *"Already included in chosen desktop base"* and their slots are filled by **reserves #5 and #6** (`Remmina`, `Geany`).

---

## 3. Primary Candidates Verification Table

| Slot | Application | Package (`armhf`) | Verified Version | Repository Source | Download Size | Installed Size | Status in Wizard |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| **1** | **btop++** | `btop` | `1.2.13-1` | Debian Bookworm `main` | `0.4 MiB` | `0.9 MiB` | Available (Recommended) |
| **2** | **OnlyOffice Desktop** | — | — | Upstream OnlyOffice | — | — | Unavailable (`amd64`/`arm64` only) -> Replaced by Reserve #1 (`Strawberry`) |
| **3** | **VLC Media Player** | `vlc` | `3.0.23-0+deb12u1` | Debian Bookworm `main`/`security` | `31.7 MiB` | `73.9 MiB` | Available (Recommended) |
| **4** | **Chromium Browser** | `chromium` | `150.0.7871.100-1~deb12u1` | Debian Bookworm `security/main` | `98.4 MiB` | `257.3 MiB` | Available (Open-source alternative to Chrome) |
| **5** | **Visual Studio Code** | `code` | `1.106.3-1764110884` | Microsoft Official Repo (`armhf`) | `100.0 MiB` | `357.6 MiB` | Available (Official Microsoft ARMv7 build) |
| **6** | **Spotify** | — | — | `repository.spotify.com` | — | — | Unavailable (`amd64` only, no Widevine on armhf) -> Replaced by Reserve #2 (`Kdenlive`) |
| **7** | **Steam** | — | — | Debian `non-free` (`i386`) | — | — | Unavailable (x86 proprietary client only) -> Replaced by Reserve #3 (`Flameshot`) |
| **8** | **Firefox ESR** | `firefox-esr` | `140.12.0esr-1~deb12u1` | Debian Bookworm `security/main` | `69.1 MiB` | `221.6 MiB` | Available (Lightweight recommended browser) |
| **9** | **LibreOffice** | `libreoffice-writer`, `libreoffice-calc`, `libreoffice-impress`, `libreoffice-qt5` | `4:7.4.7-1+deb12u14` | Debian Bookworm `security/main` | `108.8 MiB` | `402.8 MiB` | Available |
| **10** | **Thunderbird** | `thunderbird` | `Candidate: (none)` | Debian Bookworm `main` | — | — | Unavailable (32-bit armhf dropped in Bookworm due to Rust address space exhaustion) -> Replaced by Reserve #4 (`Syncthing`) |
| **11** | **GIMP** | `gimp` | `2.10.34-1+deb12u10` | Debian Bookworm `security/main` | `55.9 MiB` | `216.6 MiB` | Available |
| **12** | **Audacity** | `audacity` | `3.2.4+dfsg-1` | Debian Bookworm `main` | `12.8 MiB` | `45.0 MiB` | Available |
| **13a** | **PDF Viewer (LXQt): qpdfview** | `qpdfview` | `0.5.0+ds-2` | Debian Bookworm `main` | `3.4 MiB` | `7.8 MiB` | Available (Qt native) |
| **13b** | **PDF Viewer (KDE): Okular** | `okular` | `4:22.12.3-1+deb12u1` | Debian Bookworm `security/main` | `65.5 MiB` | `204.6 MiB` | Available (KDE native) |
| **14a** | **Editor (LXQt): FeatherPad** | `featherpad` | `1.3.5-1` | Debian Bookworm `main` | `0.5 MiB` | `1.4 MiB` | Already in LXQt base -> Replaced on LXQt by Reserve #5 (`Remmina`) |
| **14b** | **Editor (KDE): Kate** | `kate` | `4:22.12.3-1` | Debian Bookworm `main` | `39.7 MiB` | `157.1 MiB` | Available (KDE native) |
| **15a** | **Images (LXQt): LXImage-Qt** | `lximage-qt` | `1.2.0-2` | Debian Bookworm `main` | `2.2 MiB` | `13.5 MiB` | Already in LXQt base -> Replaced on LXQt by Reserve #6 (`Geany`) |
| **15b** | **Images (KDE): Gwenview** | `gwenview` | `4:22.12.3-1` | Debian Bookworm `main` | `63.7 MiB` | `196.5 MiB` | Available (KDE native) |
| **16** | **qBittorrent** | `qbittorrent` | `4.5.2-3+deb12u1` | Debian Bookworm `security/main` | `8.3 MiB` | `13.6 MiB` | Available |
| **17** | **KeePassXC** | `keepassxc` | `2.7.4+dfsg.1-2` | Debian Bookworm `main` | `8.7 MiB` | `29.5 MiB` | Available |
| **18** | **Telegram Desktop** | `telegram-desktop` | `4.6.5+ds-2+b1` | Debian Bookworm `main` | `49.4 MiB` | `110.5 MiB` | Available |
| **19** | **Inkscape** | `inkscape` | `1.2.2-2+b1` | Debian Bookworm `main` | `29.9 MiB` | `120.5 MiB` | Available |
| **20** | **Calibre** | `calibre` | `6.13.0+repack-2+deb12u9` | Debian Bookworm `security/main` | `112.2 MiB` | `291.3 MiB` | Available |

---

## 4. Reserve Applications Verification Table

| Reserve Slot | Application | Package (`armhf`) | Verified Version | Repository Source | Download Size | Installed Size | Trigger Condition |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| **Reserve #1** | **Strawberry Music Player** | `strawberry` | `1.0.14-1` | Debian Bookworm `main` | `30.9 MiB` | `74.0 MiB` | Activated in place of `OnlyOffice` |
| **Reserve #2** | **Kdenlive** | `kdenlive` | `22.12.3-2+deb12u2` | Debian Bookworm `security/main` | `211.9 MiB` | `517.2 MiB` | Activated in place of `Spotify` |
| **Reserve #3** | **Flameshot** | `flameshot` | `12.1.0-2` | Debian Bookworm `main` | `0.6 MiB` | `2.7 MiB` | Activated in place of `Steam` |
| **Reserve #4** | **Syncthing** | `syncthing` | `1.19.2~ds1-1+b4` | Debian Bookworm `main` | `6.6 MiB` | `19.9 MiB` | Activated in place of `Thunderbird` |
| **Reserve #5** | **Remmina** | `remmina` | `1.4.29+dfsg-1` | Debian Bookworm `main` | `2.7 MiB` | `8.2 MiB` | Activated on LXQt (replaces FeatherPad) |
| **Reserve #6** | **Geany** | `geany` | `1.38-1+b1` | Debian Bookworm `main` | `4.0 MiB` | `11.9 MiB` | Activated on LXQt (replaces LXImage-Qt) |


# NoteOS — Supported Desktop Environments (KDE Plasma & LXQt)

This document details the architectural choices, package curation (`--no-install-recommends`), measured idle memory consumption, service optimizations, and known behaviors for the two supported desktop environments in NoteOS:

1. **LXQt Desktop (`build/rootfs/desktops/lxqt.list`)** — **Default & Recommended** for the 2 GiB RAM budget of GT-N8000 (`1994 MiB` accessible to kernel + `997 MiB` ZRAM swap).
2. **KDE Plasma 5.27 (`build/rootfs/desktops/kde.list`)** — Full-featured Qt5/KDE Frameworks 5 desktop, accompanied in the setup wizard by an explicit memory usage notice.

---

## 1. Package Curation: Debian Metapackages vs Curated Lists

All measurements were taken on the clean NoteOS Debian 12 (Bookworm `armhf`) base rootfs (Xorg, Mesa Lima, PipeWire, NetworkManager, BlueZ, Openbox, PyQt5, Onboard).

| Desktop Configuration | APT Mode | Additional Packages (`armhf`) | Download Size | Installed Disk Space | Rationale & Selection Notes |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `lxqt` (Standard Metapackage) | With `Recommends` | `755` | `411.5 MiB` | `1323.8 MiB` | Automatically pulls `firefox-esr`, `smplayer`, `audacious`, `preload`, and `xscreensaver` regardless of user choices in the wizard. |
| `lxqt` (Standard Metapackage) | `--no-install-recommends` | `92` | `20.9 MiB` | `82.0 MiB` | Too minimal: omits `sddm`, `nm-tray`, `blueman`, `gvfs-backends`, `lxqt-archiver`, `screengrab`, `qps`, and `galculator`. |
| **Curated `build/rootfs/desktops/lxqt.list`** | **`--no-install-recommends` (Final Choice)** | **`185`** | **`62.5 MiB`** | **`162.7 MiB`** | **Complete & Lightweight**: Includes `lxqt-core`, `lxqt`, `sddm`, `nm-tray`, `blueman`, `gvfs-backends`, `udisks2`, `upower`, `lxqt-archiver`, `screengrab`, `qps`, `galculator`, `featherpad`, `lximage-qt`, `onboard`, avoiding heavy indexers or unwanted browsers. |
| `kde-plasma-desktop` (Standard Metapackage) | With `Recommends` | `914` | `712.0 MiB` | `2064.1 MiB` | Pulls `discover`, Akonadi/PIM suites, games, and background daemons that overwhelm 2 GiB of RAM. |
| `kde-plasma-desktop` (Standard Metapackage) | `--no-install-recommends` | `440` | `264.1 MiB` | `701.3 MiB` | Omits essential applets: `plasma-nm` (Wi-Fi), `plasma-pa` (audio), `bluedevil` (Bluetooth), `powerdevil` (brightness/battery), `ark`, `spectacle`, `kcalc`. |
| **Curated `build/rootfs/desktops/kde.list`** | **`--no-install-recommends` (Final Choice)** | **`530`** | **`287.6 MiB`** | **`787.2 MiB`** | **Complete & Controlled**: Includes `kde-plasma-desktop` plus all necessary system applets (`systemsettings`, `kscreen`, `dolphin`, `konsole`, `ark`, `spectacle`, `plasma-pa`, `plasma-nm`, `bluedevil`, `powerdevil`, `plasma-systemmonitor`, `kinfocenter`, `kcalc`, `sddm-theme-breeze`) without Akonadi/PIM. |

---

## 2. Core Desktop Components Included by Default

The base components for the chosen desktop are **always installed** by the setup wizard to ensure immediate touch usability:

| System Function | LXQt Base Components | KDE Plasma Base Components |
| :--- | :--- | :--- |
| **Session & Window Manager** | `lxqt-core`, `lxqt-session`, `lxqt-panel`, `lxqt-runner`, `openbox` | `kde-plasma-desktop`, `plasma-workspace`, `kwin-x11`, `breeze` |
| **System Settings & Display** | `lxqt-config`, `lxqt-admin`, `obconf-qt` | `systemsettings`, `kscreen`, `kinfocenter` |
| **Display Manager & Login** | `sddm`, `sddm-theme-debian-maui`, `qtvirtualkeyboard-plugin` | `sddm`, `sddm-theme-breeze`, `qtvirtualkeyboard-plugin` |
| **File Manager & Storage** | `pcmanfm-qt`, `gvfs`, `gvfs-backends`, `udisks2` | `dolphin`, `kio-extras`, `udisks2` |
| **Terminal Emulator** | `qterminal` | `konsole` |
| **Archive Manager** | `lxqt-archiver`, `unzip`, `p7zip-full` | `ark`, `unzip`, `p7zip-full` |
| **Screenshot Utility** | `screengrab` | `spectacle` |
| **Audio Volume (PipeWire)** | `pavucontrol-qt` | `plasma-pa` |
| **Network & Bluetooth** | `nm-tray`, `network-manager-gnome`, `blueman` | `plasma-nm`, `bluedevil` |
| **Power & Battery** | `lxqt-powermanagement`, `upower` | `powerdevil`, `upower` |
| **Process Monitor & Calculator** | `qps`, `galculator` | `plasma-systemmonitor`, `kcalc` |
| **On-Screen Touch Keyboard** | `onboard` | `onboard` + `qtvirtualkeyboard-plugin` |

---

## 3. Measured Idle RAM Consumption on Hardware (GT-N8000)

Measurements performed on physical hardware Samsung Galaxy Note 10.1 (`GT-N8000`, `1994 MiB` total RAM, Linux kernel `6.6.158`, Mali-400 MP4 GPU with Mesa `lima` driver, `1280x800@60Hz`, ZRAM swap `997 MiB` `lz4`):

| State / Environment | RAM `used` (`free -m`) | RAM `available` (`free -m`) | ZRAM Swap Used | Primary Active Processes |
| :--- | :---: | :---: | :---: | :--- |
| **Base Kiosk Setup Wizard (`noteos-setup` on Openbox)** | **`188 MiB`** | **`1715 MiB`** | `0 MiB` | `Xorg` (~42 MiB), `openbox` (~9 MiB), `python3 wizard_app.py` (~38 MiB), `NetworkManager`, `pipewire` |
| **LXQt Desktop Idle (After SDDM login)** | **`295 MiB`** | **`1580 MiB`** | `0 MiB` | `Xorg`, `sddm`, `openbox`, `lxqt-session`, `lxqt-panel`, `pcmanfm-qt --desktop`, `onboard`, `pipewire` |
| **KDE Plasma 5.27 Idle (Baloo disabled)** | **`433 MiB`** | **`1410 MiB`** | `0 MiB` | `Xorg`, `sddm`, `kwin_x11`, `plasmashell`, `kded5`, `powerdevil`, `onboard`, `pipewire` |

---

## 4. Performance Optimizations for 2 GiB RAM & eMMC

1. **KDE Baloo File Indexer Disabled by Default**:
   - On the GT-N8000 eMMC and 2 GiB RAM, `baloo_file` causes heavy I/O saturation and consumes `150–250 MiB` RAM.
   - Disabled globally in `/etc/xdg/baloofilerc` and user home config:
     ```ini
     [Basic Settings]
     Indexing-Enabled=false
     ```
2. **Akonadi / KDE PIM Excluded**:
   - Eliminating Akonadi and MySQL saves `~220 MiB` idle RAM.
3. **ZRAM `lz4` Compression (50% of RAM, `997 MiB`)**:
   - Configured in `/etc/default/zramswap`, preventing OOM locks when launching heavy apps (Chromium, Firefox ESR, LibreOffice, VS Code).


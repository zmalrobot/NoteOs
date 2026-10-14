# NoteOS — Branding, Wallpapers, and Plymouth Boot Animation

This document records the specifications, dimensions, cryptographic `SHA-256` checksums, and integration details for all official **NoteOS** visual assets on the Samsung Galaxy Note 10.1 (`GT-N8000`).

---

## 1. Wallpapers (`build/branding/wallpapers/`)

The official NoteOS wallpapers are provided in high resolution and optimized formats:

| Asset | Local Repository Path | File Size (Bytes) | Format & Resolution | SHA-256 Checksum |
| :--- | :--- | ---: | :--- | :--- |
| `NoteOs_00.jpeg` (Default) | `build/branding/wallpapers/NoteOs_00.jpeg` | `1,545,592` | JPEG RGB 8-bit, `2752×1536` (`1.7917:1`) | `8ed16e864aede9c532859cd322fe82160ed86f9bf8cb03f161f7c256fd579a03` |
| `NoteOs_01.jpeg` (Wave) | `build/branding/wallpapers/NoteOs_01.jpeg` | `2,067,984` | JPEG RGB 8-bit, `2752×1536` (`1.7917:1`) | `1b857d6600fb57e82d39a34c4dd791e535389a97059fa00a32f03d4febfa6ad5` |

### Pre-scaled 16:10 (`1280×800`) Variants
For instantaneous desktop rendering in KDE Plasma KPackage (`NoteOS_Default` and `NoteOS_Wave`), SDDM, and setup wizard, two center-cropped `1280×800` renders (`1.6000:1`, zero deformation) are generated:

| File | File Size (Bytes) | Resolution | SHA-256 Checksum |
| :--- | ---: | :--- | :--- |
| `NoteOs_00_1280x800.jpg` | `181,783` | `1280×800` (16:10) | `55275ae23e3a991df60288d5281f42520cae36b76c19cff7d27b26962311edce` |
| `NoteOs_01_1280x800.jpg` | `206,746` | `1280×800` (16:10) | `eb91fb14e02cd6cfabeae12bb52b8646fac6093c600faae0ccb4f011c821daf1` |

---

## 2. Plymouth Boot Animation (`build/devices/n8000/branding/bootanimation/`)

The Plymouth boot animation provides smooth visual feedback during startup and shutdown on the native `1280×800` panel.

### Animation Files
- **`desc.txt`** (`24` bytes, SHA256: `46c007be2cf39ee6a06d5dc7a9e57f9b728d8f67222e203d94cf872652e80da3`): `1280 800 24 \n p 0 0 part0`
- **`noteos.plymouth`** (`247` bytes, SHA256: `836da28199633aee31b49ea3f1e845d3c0e7e6398dabeb5f3e7582fd108ee3d3`)
- **`noteos.script`** (`705` bytes, SHA256: `f828056ed3ad4ef99e531c784447d22ae449937040e0c2efdcc5396bb069503d`)

### Frames: `part0/0000.png` to `part0/0029.png` (`1280×800`, PNG RGB 8-bit)
- Total on disk: 30 PNG frames (`22,998,394` bytes / `21.93 MiB`).
- Uncompressed RGBA32 memory footprint (`30 × 1280 × 800 × 4` bytes): `122,880,000` bytes (`117.19 MiB`).

---

## 3. Debian Package `noteos-branding`

The `noteos-branding` package (`build/branding/build-deb.sh`) encapsulates all visual branding and system configuration:

### Diversions (`dpkg-divert`)
Guarantees custom branding persists across Debian `base-files` updates:
- `/usr/lib/os-release` (diverted to `/usr/lib/os-release.debian`)
- `/etc/issue` (diverted to `/etc/issue.debian`)
- `/etc/issue.net` (diverted to `/etc/issue.net.debian`)
- `/etc/motd` (diverted to `/etc/motd.debian`)

### Components Installed
1. **OS Identity**: `/usr/lib/os-release`, `/etc/issue`, `/etc/issue.net`, `/etc/motd`.
2. **Plymouth Theme**: `/usr/share/plymouth/themes/noteos/` and `/etc/plymouth/plymouthd.conf`.
3. **Wallpapers**: Installed to `/usr/share/backgrounds/noteos/` and KDE Plasma packages `/usr/share/wallpapers/NoteOS_Default/` and `NoteOS_Wave/`.
4. **Global Dark Theme**:
   - KDE Plasma: `BreezeDark` in `/etc/xdg/kdeglobals`, `/etc/xdg/plasmarc`, and autostart script for wallpaper scaling (`FillMode=2`).
   - LXQt: Dark theme, `breeze-dark` icons, and `WallpaperMode=zoom`.
   - GTK: `gtk-application-prefer-dark-theme=1` and `color-scheme='prefer-dark'` via `dconf`.
   - SDDM: Breeze Dark login theme.


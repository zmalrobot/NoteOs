#!/bin/bash
set -euo pipefail

# ==============================================================================
# branding/build-deb.sh — Costruzione deterministica di noteos-branding.deb
# Include:
# - /usr/lib/os-release, /etc/issue, /etc/issue.net, /etc/motd (con dpkg-divert)
# - Tema Plymouth /usr/share/plymouth/themes/noteos/ + /etc/plymouth/plymouthd.conf
# - Sfondi NoteOs_00.jpeg (default) e NoteOs_01.jpeg (aggiuntivo) per KDE/LXQt/SDDM
# - Tema scuro predefinito per KDE Plasma (Breeze Dark), LXQt, GTK3/4, dconf,
#   Firefox ESR, Chromium, Onboard e terminali.
# ==============================================================================

DEVICE="${DEVICE:-n8000}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${OUT_DIR:-$(cd "${PROJECT_DIR}/.." && pwd)/out/${DEVICE}}"
PKG_VERSION="${NOTEOS_VERSION:-1.0.0}"
PKG_DIR="${OUT_DIR}/noteos-branding_pkg"
DEB_OUT="${OUT_DIR}/noteos-branding_${PKG_VERSION}_all.deb"
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1700000000}"

echo "=== [branding] Costruzione pacchetto Debian noteos-branding (${PKG_VERSION}) ==="

rm -rf "${PKG_DIR}"
mkdir -p "${PKG_DIR}/DEBIAN"

# ------------------------------------------------------------------------------
# 1. Control file e maintainer scripts (dpkg-divert per base-files)
# ------------------------------------------------------------------------------
cat << EOF > "${PKG_DIR}/DEBIAN/control"
Package: noteos-branding
Version: ${PKG_VERSION}
Section: misc
Priority: optional
Architecture: all
Maintainer: NoteOS Project <maintainers@noteos.local>
Provides: lxqt-branding
Replaces: lxqt-branding-debian
Conflicts: lxqt-branding-debian
Description: Identita di sistema, tema scuro, sfondi e boot animation per NoteOS
 Pacchetto ufficiale di branding per NoteOS (basato su Debian 12 bookworm).
 Configura /etc/os-release tramite dpkg-divert, il tema Plymouth NoteOS,
 gli sfondi predefiniti NoteOs_00.jpeg e NoteOs_01.jpeg e il tema scuro
 globale per KDE Plasma, LXQt, SDDM, GTK3/4, Qt e browser.
EOF

cat << 'EOF' > "${PKG_DIR}/DEBIAN/preinst"
#!/bin/sh
set -e
if [ "$1" = "install" ] || [ "$1" = "upgrade" ]; then
    for f in /usr/lib/os-release /etc/issue /etc/issue.net /etc/motd /etc/plymouth/plymouthd.conf; do
        if ! dpkg-divert --list "$f" | grep -q "noteos-branding"; then
            dpkg-divert --package noteos-branding --divert "${f}.debian" --rename "$f"
        fi
    done
fi
exit 0
EOF

cat << 'EOF' > "${PKG_DIR}/DEBIAN/postinst"
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    ln -sf ../usr/lib/os-release /etc/os-release
    if [ -d /usr/share/plymouth/themes/noteos ]; then
        if command -v plymouth-set-default-theme >/dev/null 2>&1; then
            plymouth-set-default-theme noteos 2>/dev/null || true
        else
            ln -sf /usr/share/plymouth/themes/noteos/noteos.plymouth /usr/share/plymouth/themes/default.plymouth 2>/dev/null || true
        fi
    fi
    if command -v dconf >/dev/null 2>&1; then
        dconf update 2>/dev/null || true
    fi
fi
exit 0
EOF

cat << 'EOF' > "${PKG_DIR}/DEBIAN/postrm"
#!/bin/sh
set -e
if [ "$1" = "remove" ] || [ "$1" = "abort-install" ] || [ "$1" = "disappear" ]; then
    for f in /usr/lib/os-release /etc/issue /etc/issue.net /etc/motd /etc/plymouth/plymouthd.conf; do
        if dpkg-divert --list "$f" | grep -q "noteos-branding"; then
            dpkg-divert --package noteos-branding --remove --rename "$f"
        fi
    done
fi
exit 0
EOF

chmod 0755 "${PKG_DIR}/DEBIAN/preinst" "${PKG_DIR}/DEBIAN/postinst" "${PKG_DIR}/DEBIAN/postrm"

# ------------------------------------------------------------------------------
# 2. Identità OS (/usr/lib/os-release, /etc/issue, /etc/motd)
# ------------------------------------------------------------------------------
mkdir -p "${PKG_DIR}/usr/lib" "${PKG_DIR}/etc"
cat << 'EOF' > "${PKG_DIR}/usr/lib/os-release"
PRETTY_NAME="NoteOS 1.0 (basato su Debian 12 bookworm)"
NAME="NoteOS"
VERSION_ID="1.0"
VERSION="1.0 (bookworm)"
VERSION_CODENAME=bookworm
DEBIAN_CODENAME=bookworm
ID=noteos
ID_LIKE=debian
HOME_URL="https://www.debian.org/"
SUPPORT_URL="https://www.debian.org/support"
BUG_REPORT_URL="https://bugs.debian.org/"
EOF

cat << 'EOF' > "${PKG_DIR}/etc/issue"
NoteOS 1.0 (basato su Debian 12 bookworm) \n \l

EOF

cat << 'EOF' > "${PKG_DIR}/etc/issue.net"
NoteOS 1.0 (basato su Debian 12 bookworm)
EOF

cat << 'EOF' > "${PKG_DIR}/etc/motd"
Benvenuto in NoteOS 1.0 (basato su Debian GNU/Linux 12 bookworm) — Samsung Galaxy Note 10.1 (GT-N8000)
EOF

# ------------------------------------------------------------------------------
# 3. Animazione di avvio Plymouth (/usr/share/plymouth/themes/noteos)
# ------------------------------------------------------------------------------
BOOTANIM_SRC="${PROJECT_DIR}/devices/${DEVICE}/branding/bootanimation"
PLYMOUTH_DST="${PKG_DIR}/usr/share/plymouth/themes/noteos"
mkdir -p "${PLYMOUTH_DST}/part0" "${PKG_DIR}/etc/plymouth"

cp -p "${BOOTANIM_SRC}/desc.txt" "${PLYMOUTH_DST}/desc.txt"
cp -p "${BOOTANIM_SRC}/noteos.plymouth" "${PLYMOUTH_DST}/noteos.plymouth"
cp -p "${BOOTANIM_SRC}/noteos.script" "${PLYMOUTH_DST}/noteos.script"
cp -p "${BOOTANIM_SRC}/part0/"*.png "${PLYMOUTH_DST}/part0/"

# Symlink relativi per risolvere Image("0000.png") con ImageDir=/usr/share/plymouth/themes/noteos
for png in "${PLYMOUTH_DST}/part0/"*.png; do
    base="$(basename "${png}")"
    ln -sf "part0/${base}" "${PLYMOUTH_DST}/${base}"
done

cat << 'EOF' > "${PKG_DIR}/etc/plymouth/plymouthd.conf"
# Configurazione Plymouth per NoteOS
[Daemon]
Theme=noteos
ShowDelay=0
DeviceTimeout=5
EOF

# ------------------------------------------------------------------------------
# 4. Sfondi NoteOs_00.jpeg (default) e NoteOs_01.jpeg (aggiuntivo)
# ------------------------------------------------------------------------------
BG_DST="${PKG_DIR}/usr/share/backgrounds/noteos"
mkdir -p "${BG_DST}"
cp -p "${PROJECT_DIR}/branding/wallpapers/NoteOs_00.jpeg" "${BG_DST}/NoteOs_00.jpeg"
cp -p "${PROJECT_DIR}/branding/wallpapers/NoteOs_01.jpeg" "${BG_DST}/NoteOs_01.jpeg"
cp -p "${PROJECT_DIR}/branding/wallpapers/optimized/NoteOs_00_1280x800.jpg" "${BG_DST}/NoteOs_00_1280x800.jpg"
cp -p "${PROJECT_DIR}/branding/wallpapers/optimized/NoteOs_01_1280x800.jpg" "${BG_DST}/NoteOs_01_1280x800.jpg"

# KPackage Wallpapers per KDE Plasma (/usr/share/wallpapers/)
WP1="${PKG_DIR}/usr/share/wallpapers/NoteOS_Default"
WP2="${PKG_DIR}/usr/share/wallpapers/NoteOS_Wave"
mkdir -p "${WP1}/contents/images" "${WP2}/contents/images"

cat << 'EOF' > "${WP1}/metadata.json"
{
    "KPlugin": {
        "Authors": [
            {
                "Name": "NoteOS"
            }
        ],
        "Id": "NoteOS_Default",
        "License": "CC-BY-SA-4.0",
        "Name": "NoteOS Default"
    }
}
EOF
cat << 'EOF' > "${WP1}/metadata.desktop"
[Desktop Entry]
Name=NoteOS Default
X-KDE-PluginInfo-Name=NoteOS_Default
X-KDE-PluginInfo-Author=NoteOS
X-KDE-PluginInfo-License=CC-BY-SA-4.0
EOF
ln -sf "../../../../backgrounds/noteos/NoteOs_00.jpeg" "${WP1}/contents/images/2752x1536.jpg"
ln -sf "../../../../backgrounds/noteos/NoteOs_00_1280x800.jpg" "${WP1}/contents/images/1280x800.jpg"

cat << 'EOF' > "${WP2}/metadata.json"
{
    "KPlugin": {
        "Authors": [
            {
                "Name": "NoteOS"
            }
        ],
        "Id": "NoteOS_Wave",
        "License": "CC-BY-SA-4.0",
        "Name": "NoteOS Wave"
    }
}
EOF
cat << 'EOF' > "${WP2}/metadata.desktop"
[Desktop Entry]
Name=NoteOS Wave
X-KDE-PluginInfo-Name=NoteOS_Wave
X-KDE-PluginInfo-Author=NoteOS
X-KDE-PluginInfo-License=CC-BY-SA-4.0
EOF
ln -sf "../../../../backgrounds/noteos/NoteOs_01.jpeg" "${WP2}/contents/images/2752x1536.jpg"
ln -sf "../../../../backgrounds/noteos/NoteOs_01_1280x800.jpg" "${WP2}/contents/images/1280x800.jpg"

# ------------------------------------------------------------------------------
# 5. Tema Scuro Globale e Sfondi di Default (KDE, LXQt, SDDM, GTK3/4, dconf)
# ------------------------------------------------------------------------------
mkdir -p \
    "${PKG_DIR}/etc/xdg/lxqt" \
    "${PKG_DIR}/etc/xdg/pcmanfm-qt/lxqt" \
    "${PKG_DIR}/etc/xdg/qterminal.org" \
    "${PKG_DIR}/etc/xdg/autostart" \
    "${PKG_DIR}/etc/skel/.config/lxqt" \
    "${PKG_DIR}/etc/skel/.config/pcmanfm-qt/lxqt" \
    "${PKG_DIR}/etc/skel/.config/qterminal.org" \
    "${PKG_DIR}/etc/skel/.config/gtk-3.0" \
    "${PKG_DIR}/etc/skel/.config/gtk-4.0" \
    "${PKG_DIR}/etc/skel/.local/share/konsole" \
    "${PKG_DIR}/etc/gtk-3.0" \
    "${PKG_DIR}/etc/dconf/profile" \
    "${PKG_DIR}/etc/dconf/db/local.d" \
    "${PKG_DIR}/etc/sddm.conf.d" \
    "${PKG_DIR}/usr/share/sddm/themes/debian-maui" \
    "${PKG_DIR}/usr/share/sddm/themes/breeze" \
    "${PKG_DIR}/etc/firefox-esr" \
    "${PKG_DIR}/etc/chromium.d" \
    "${PKG_DIR}/usr/local/bin"

# 5a. KDE Plasma: Breeze Dark + palette completa in kdeglobals e plasmarc
cat << 'EOF' > "${PKG_DIR}/etc/xdg/kdeglobals"
[ColorEffects:Disabled]
Color=56,56,56
ColorAmount=0
ColorEffect=0
ContrastAmount=0.65
ContrastEffect=1
IntensityAmount=0.1
IntensityEffect=2

[ColorEffects:Inactive]
ChangeSelectionColor=true
Color=112,111,110
ColorAmount=0.025
ColorEffect=2
ContrastAmount=0.1
ContrastEffect=2
Enable=false
IntensityAmount=0
IntensityEffect=0

[Colors:Button]
BackgroundAlternate=30,87,116
BackgroundNormal=49,54,59
DecorationFocus=61,174,233
DecorationHover=61,174,233
ForegroundActive=61,174,233
ForegroundInactive=161,169,177
ForegroundLink=29,153,243
ForegroundNegative=218,68,83
ForegroundNeutral=246,116,0
ForegroundNormal=252,252,252
ForegroundPositive=39,174,96
ForegroundVisited=155,89,182

[Colors:Complementary]
BackgroundAlternate=30,87,116
BackgroundNormal=42,46,50
DecorationFocus=61,174,233
DecorationHover=61,174,233
ForegroundActive=61,174,233
ForegroundInactive=161,169,177
ForegroundLink=29,153,243
ForegroundNegative=218,68,83
ForegroundNeutral=246,116,0
ForegroundNormal=252,252,252
ForegroundPositive=39,174,96
ForegroundVisited=155,89,182

[Colors:Header]
BackgroundAlternate=42,46,50
BackgroundNormal=49,54,59
DecorationFocus=61,174,233
DecorationHover=61,174,233
ForegroundActive=61,174,233
ForegroundInactive=161,169,177
ForegroundLink=29,153,243
ForegroundNegative=218,68,83
ForegroundNeutral=246,116,0
ForegroundNormal=252,252,252
ForegroundPositive=39,174,96
ForegroundVisited=155,89,182

[Colors:Selection]
BackgroundAlternate=30,87,116
BackgroundNormal=61,174,233
DecorationFocus=61,174,233
DecorationHover=61,174,233
ForegroundActive=252,252,252
ForegroundInactive=161,169,177
ForegroundLink=253,188,75
ForegroundNegative=176,55,69
ForegroundNeutral=198,92,0
ForegroundNormal=252,252,252
ForegroundPositive=23,104,57
ForegroundVisited=155,89,182

[Colors:Tooltip]
BackgroundAlternate=42,46,50
BackgroundNormal=49,54,59
DecorationFocus=61,174,233
DecorationHover=61,174,233
ForegroundActive=61,174,233
ForegroundInactive=161,169,177
ForegroundLink=29,153,243
ForegroundNegative=218,68,83
ForegroundNeutral=246,116,0
ForegroundNormal=252,252,252
ForegroundPositive=39,174,96
ForegroundVisited=155,89,182

[Colors:View]
BackgroundAlternate=35,38,41
BackgroundNormal=27,30,32
DecorationFocus=61,174,233
DecorationHover=61,174,233
ForegroundActive=61,174,233
ForegroundInactive=161,169,177
ForegroundLink=29,153,243
ForegroundNegative=218,68,83
ForegroundNeutral=246,116,0
ForegroundNormal=252,252,252
ForegroundPositive=39,174,96
ForegroundVisited=155,89,182

[Colors:Window]
BackgroundAlternate=49,54,59
BackgroundNormal=42,46,50
DecorationFocus=61,174,233
DecorationHover=61,174,233
ForegroundActive=61,174,233
ForegroundInactive=161,169,177
ForegroundLink=29,153,243
ForegroundNegative=218,68,83
ForegroundNeutral=246,116,0
ForegroundNormal=252,252,252
ForegroundPositive=39,174,96
ForegroundVisited=155,89,182

[General]
ColorScheme=BreezeDark
Name=Breeze Dark
shadeSortColumn=true
widgetStyle=Breeze

[Icons]
Theme=breeze-dark

[KDE]
LookAndFeelPackage=org.kde.breezedark.desktop
SingleClick=false
widgetStyle=Breeze

[WM]
activeBackground=49,54,59
activeBlend=252,252,252
activeForeground=252,252,252
inactiveBackground=42,46,50
inactiveBlend=161,169,177
inactiveForeground=161,169,177
EOF
cp -p "${PKG_DIR}/etc/xdg/kdeglobals" "${PKG_DIR}/etc/skel/.config/kdeglobals"

cat << 'EOF' > "${PKG_DIR}/etc/xdg/plasmarc"
[Theme]
name=breeze-dark

[Wallpapers]
usersWallpapers=/usr/share/backgrounds/noteos/NoteOs_00.jpeg,/usr/share/backgrounds/noteos/NoteOs_01.jpeg
EOF
cp -p "${PKG_DIR}/etc/xdg/plasmarc" "${PKG_DIR}/etc/skel/.config/plasmarc"

# Script primo login KDE Plasma per applicare NoteOs_00.jpeg con FillMode=2 (Scaled and Cropped)
cat << 'EOF' > "${PKG_DIR}/usr/local/bin/noteos-apply-defaults"
#!/bin/sh
MARKER="${HOME}/.config/noteos-defaults-applied"
if [ -f "${MARKER}" ]; then
    exit 0
fi
mkdir -p "${HOME}/.config"
if [ "${XDG_CURRENT_DESKTOP:-}" = "KDE" ] || pgrep -x plasmashell >/dev/null 2>&1; then
    if command -v lookandfeeltool >/dev/null 2>&1; then
        lookandfeeltool -a org.kde.breezedark.desktop 2>/dev/null || true
    fi
    if command -v plasma-apply-colorscheme >/dev/null 2>&1; then
        plasma-apply-colorscheme BreezeDark 2>/dev/null || true
    fi
    if command -v qdbus >/dev/null 2>&1; then
        for i in 1 2 3 4 5; do
            if qdbus org.kde.plasmashell /PlasmaShell >/dev/null 2>&1; then
                qdbus org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript '
                    var allDesktops = desktops();
                    for (var i = 0; i < allDesktops.length; i++) {
                        var d = allDesktops[i];
                        d.wallpaperPlugin = "org.kde.image";
                        d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");
                        d.writeConfig("Image", "file:///usr/share/wallpapers/NoteOS_Default/");
                        d.writeConfig("FillMode", "2");
                        d.writeConfig("SlidePaths", "/usr/share/wallpapers,/usr/share/backgrounds/noteos");
                    }
                ' 2>/dev/null && break
            fi
            sleep 1
        done
    fi
fi
touch "${MARKER}"
exit 0
EOF
chmod 0755 "${PKG_DIR}/usr/local/bin/noteos-apply-defaults"

cat << 'EOF' > "${PKG_DIR}/etc/xdg/autostart/noteos-apply-defaults.desktop"
[Desktop Entry]
Type=Application
Name=NoteOS First Login Defaults
Exec=/usr/local/bin/noteos-apply-defaults
X-GNOME-Autostart-enabled=true
NoDisplay=true
EOF

# 5b. LXQt: tema scuro + icone breeze-dark + sfondo NoteOs_00.jpeg con zoom
cat << 'EOF' > "${PKG_DIR}/etc/xdg/lxqt/lxqt.conf"
[General]
theme=dark
icon_theme=breeze-dark
single_click_activate=false
 tool_button_style=ToolButtonTextBesideIcon

[Qt]
style=Fusion
font="DejaVu Sans,11,-1,5,50,0,0,0,0,0"

[Palette]
base_color=#1b1e20
background_color=#2a2e32
text_color=#fcfcfc
link_color=#1d99f3
link_visited_color=#9b59b6
highlight_color=#3daee9
highlighted_text_color=#fcfcfc
disabled_text_color=#7f8c8d
EOF
cp -p "${PKG_DIR}/etc/xdg/lxqt/lxqt.conf" "${PKG_DIR}/etc/skel/.config/lxqt/lxqt.conf"

cat << 'EOF' > "${PKG_DIR}/etc/xdg/pcmanfm-qt/lxqt/settings.conf"
[System]
IconThemeName=breeze-dark

[Desktop]
WallpaperMode=zoom
Wallpaper=/usr/share/backgrounds/noteos/NoteOs_00.jpeg
BgColor=#0b0f17
FgColor=#fcfcfc
ShadowColor=#000000
Font="DejaVu Sans,11,-1,5,50,0,0,0,0,0"
EOF
cp -p "${PKG_DIR}/etc/xdg/pcmanfm-qt/lxqt/settings.conf" "${PKG_DIR}/etc/skel/.config/pcmanfm-qt/lxqt/settings.conf"

# 5c. Terminali (QTerminal e Konsole) in tema scuro
cat << 'EOF' > "${PKG_DIR}/etc/xdg/qterminal.org/qterminal.ini"
[General]
colorScheme=Linux
fontFamily=DejaVu Sans Mono
fontSize=11
TerminalTransparency=0
EOF
cp -p "${PKG_DIR}/etc/xdg/qterminal.org/qterminal.ini" "${PKG_DIR}/etc/skel/.config/qterminal.org/qterminal.ini"

cat << 'EOF' > "${PKG_DIR}/etc/skel/.local/share/konsole/NoteOS-Dark.profile"
[Appearance]
ColorScheme=Breeze
Font=DejaVu Sans Mono,11,-1,5,50,0,0,0,0,0

[General]
Name=NoteOS-Dark
Parent=FALLBACK/
EOF

cat << 'EOF' > "${PKG_DIR}/etc/xdg/konsolerc"
[Desktop Entry]
DefaultProfile=NoteOS-Dark.profile
EOF
cp -p "${PKG_DIR}/etc/xdg/konsolerc" "${PKG_DIR}/etc/skel/.config/konsolerc"

# 5d. GTK 3, GTK 4 e dconf (color-scheme='prefer-dark' + Onboard scuro)
cat << 'EOF' > "${PKG_DIR}/etc/gtk-3.0/settings.ini"
[Settings]
gtk-application-prefer-dark-theme=1
gtk-theme-name=Adwaita-dark
gtk-icon-theme-name=breeze-dark
gtk-font-name=DejaVu Sans 11
EOF
cp -p "${PKG_DIR}/etc/gtk-3.0/settings.ini" "${PKG_DIR}/etc/skel/.config/gtk-3.0/settings.ini"
cp -p "${PKG_DIR}/etc/gtk-3.0/settings.ini" "${PKG_DIR}/etc/skel/.config/gtk-4.0/settings.ini"

cat << 'EOF' > "${PKG_DIR}/etc/dconf/profile/user"
user-db:user
system-db:local
EOF

cat << 'EOF' > "${PKG_DIR}/etc/dconf/db/local.d/00-noteos-dark"
[org/gnome/desktop/interface]
color-scheme='prefer-dark'
gtk-theme='Adwaita-dark'
icon-theme='breeze-dark'
font-name='DejaVu Sans 11'

[org/onboard]
theme='Nightshade'
key-label-font='DejaVu Sans bold'
EOF

# 5e. Browser (Firefox ESR e Chromium) in modalità scura di default
cat << 'EOF' > "${PKG_DIR}/etc/firefox-esr/noteos-prefs.js"
// NoteOS Default Dark Theme Preferences for Firefox ESR
pref("ui.systemUsesDarkTheme", 1);
pref("layout.css.prefers-color-scheme.content-override", 0);
pref("browser.theme.content-theme", 0);
pref("browser.theme.toolbar-theme", 0);
EOF

cat << 'EOF' > "${PKG_DIR}/etc/chromium.d/noteos-dark"
# NoteOS Dark Mode defaults for Chromium
export CHROMIUM_FLAGS="${CHROMIUM_FLAGS:-} --enable-features=WebUIDarkMode --force-dark-mode"
EOF

# 5f. SDDM Login Screen (sfondo NoteOs_00_1280x800.jpg + tema scuro)
cat << 'EOF' > "${PKG_DIR}/etc/sddm.conf.d/10-noteos-theme.conf"
[Theme]
Current=debian-maui

[General]
InputMethod=qtvirtualkeyboard
EOF

cat << 'EOF' > "${PKG_DIR}/usr/share/sddm/themes/debian-maui/theme.conf.user"
[General]
background=/usr/share/backgrounds/noteos/NoteOs_00_1280x800.jpg
EOF

cat << 'EOF' > "${PKG_DIR}/usr/share/sddm/themes/breeze/theme.conf.user"
[General]
background=/usr/share/backgrounds/noteos/NoteOs_00_1280x800.jpg
type=image
EOF

# Normalizzazione timestamp con SOURCE_DATE_EPOCH
find "${PKG_DIR}" -exec touch -h -d "@${SOURCE_DATE_EPOCH}" {} +

if command -v dpkg-deb >/dev/null 2>&1; then
    dpkg-deb --root-owner-group -Zxz -b "${PKG_DIR}" "${DEB_OUT}"
else
    podman run --rm --security-opt label=disable -v "${PROJECT_DIR}":/work -w /work localhost/n8000-builder:latest \
        dpkg-deb --root-owner-group -Zxz -b "/work/out/${DEVICE}/noteos-branding_pkg" "/work/out/${DEVICE}/noteos-branding_${PKG_VERSION}_all.deb"
fi
rm -rf "${PKG_DIR}"

echo "=== [branding] Pacchetto generato: ${DEB_OUT} ($(stat -c%s "${DEB_OUT}") byte) ==="
sha256sum "${DEB_OUT}"

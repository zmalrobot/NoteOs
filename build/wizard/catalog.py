#!/usr/bin/env python3
"""
wizard/catalog.py — Catalogo verificato dei Desktop (LXQt / KDE Plasma),
dei 20 programmi + 6 riserve per Debian 12 Bookworm (armhf) su GT-N8000,
e dizionario bilingue (Italiano / English) per noteos-setup.
"""

# ==============================================================================
# 1. DEFINIZIONE AMBIENTI DESKTOP E BASE INCLUSA DI SERIE
# ==============================================================================
DESKTOPS = {
    "lxqt": {
        "id": "lxqt",
        "name_it": "LXQt Desktop (Consigliato — Predefinito)",
        "name_en": "LXQt Desktop (Recommended — Default)",
        "session_name": "lxqt",
        "ram_idle_mb": 295,
        "download_mb": 62.5,
        "installed_mb": 162.7,
        "list_file": "/usr/share/noteos-setup/desktops/lxqt.list",
        "fallback_list_file": "rootfs/desktops/lxqt.list",
        "base_included_ids": {"featherpad", "lximage-qt"},
        "base_summary_it": (
            "Inclusa di serie (non deselezionabile): Impostazioni (lxqt-config, obconf-qt), "
            "File Manager (PCManFM-Qt + GVFS/udisks2), Terminale (QTerminal), Gestore Archivi (lxqt-archiver), "
            "Screenshot (ScreenGrab), Audio (pavucontrol-qt), Rete (nm-tray), Bluetooth (Blueman), "
            "Energia (lxqt-powermanagement), Processi (qps), Calcolatrice (Galculator), Appunti (Qlipper), "
            "Editor (FeatherPad), Immagini (LXImage-Qt), Tastiera Touch (Onboard) e Display Manager (SDDM)."
        ),
        "base_summary_en": (
            "Included by default (always installed): Settings (lxqt-config, obconf-qt), "
            "File Manager (PCManFM-Qt + GVFS/udisks2), Terminal (QTerminal), Archive Manager (lxqt-archiver), "
            "Screenshot (ScreenGrab), Audio (pavucontrol-qt), Network (nm-tray), Bluetooth (Blueman), "
            "Power (lxqt-powermanagement), Process Manager (qps), Calculator (Galculator), Clipboard (Qlipper), "
            "Text Editor (FeatherPad), Image Viewer (LXImage-Qt), Touch Keyboard (Onboard), and Display Manager (SDDM)."
        ),
        "warning_it": "Leggero, reattivo e ottimale per i 2 GB di RAM del Galaxy Note 10.1 (~295 MiB RAM a riposo).",
        "warning_en": "Lightweight, responsive, and optimal for the Galaxy Note 10.1's 2 GB RAM (~295 MiB idle RAM).",
    },
    "kde": {
        "id": "kde",
        "name_it": "KDE Plasma 5.27 Desktop",
        "name_en": "KDE Plasma 5.27 Desktop",
        "session_name": "plasma",
        "ram_idle_mb": 433,
        "download_mb": 287.6,
        "installed_mb": 787.2,
        "list_file": "/usr/share/noteos-setup/desktops/kde.list",
        "fallback_list_file": "rootfs/desktops/kde.list",
        "base_included_ids": set(),
        "base_summary_it": (
            "Inclusa di serie (non deselezionabile): Impostazioni di Sistema (systemsettings + kscreen), "
            "File Manager (Dolphin + kio-extras/udisks2), Terminale (Konsole), Gestore Archivi (Ark), "
            "Screenshot (Spectacle), Audio (plasma-pa), Rete (plasma-nm), Bluetooth (Bluedevil), "
            "Energia (PowerDevil), Monitor di Sistema (plasma-systemmonitor), Info Sistema (KInfoCenter), "
            "Calcolatrice (KCalc), Tastiera Touch (QtVirtualKeyboard + Onboard) e Display Manager (SDDM). "
            "L'indicizzatore Baloo viene disattivato automaticamente di default."
        ),
        "base_summary_en": (
            "Included by default (always installed): System Settings (systemsettings + kscreen), "
            "File Manager (Dolphin + kio-extras/udisks2), Terminal (Konsole), Archive Manager (Ark), "
            "Screenshot (Spectacle), Audio (plasma-pa), Network (plasma-nm), Bluetooth (Bluedevil), "
            "Power (PowerDevil), System Monitor (plasma-systemmonitor), Info Center (KInfoCenter), "
            "Calculator (KCalc), Touch Keyboard (QtVirtualKeyboard + Onboard), and Display Manager (SDDM). "
            "Baloo file indexer is automatically disabled by default."
        ),
        "warning_it": (
            "ATTENZIONE: KDE Plasma è significativamente più pesante su 2 GB di RAM (~433 MiB a riposo "
            "con Baloo disattivato, contro ~295 MiB di LXQt). Aprendo browser pesanti rimane meno margine."
        ),
        "warning_en": (
            "WARNING: KDE Plasma is significantly heavier on 2 GB RAM (~433 MiB at idle "
            "with Baloo disabled, vs ~295 MiB on LXQt). Less headroom remains when running heavy browsers."
        ),
    },
}


# ==============================================================================
# 2. CATALOGO DEI PROGRAMMI VERIFICATI SU ARMHF (20 PRIMARI + 6 RISERVE)
# ==============================================================================
# Nota sulle regole:
# - I programmi dipendenti dal desktop (lettore PDF, editor di testo, visualizzatore immagini)
#   usano la variante nativa del toolkit scelto (Qt leggero su LXQt, KDE/Qt su KDE).
# - Se un programma primario è già incluso nella base del desktop scelto (es. FeatherPad e
#   LXImage-Qt su LXQt) oppure non è disponibile su armhf (OnlyOffice, Spotify, Steam, Thunderbird),
#   non conta tra i 20 installabili e il suo posto viene preso in ordine dalla lista RISERVE,
#   così la schermata 5 presenta SEMPRE 20 programmi aggiuntivi installabili verificati.

PRIMARY_CANDIDATES = [
    {
        "slot": 1,
        "id": "btop",
        "name_it": "btop++ (Monitor risorse)",
        "name_en": "btop++ (Resource Monitor)",
        "cat_it": "Sistema e Utilità",
        "cat_en": "System & Utilities",
        "pkgs": ["btop"],
        "version": "1.2.13-1",
        "source": "Debian main (armhf)",
        "dl_mb": 0.4,
        "inst_mb": 0.9,
        "ram_mb": 12,
        "recommended": True,
        "available": True,
    },
    {
        "slot": 2,
        "id": "onlyoffice",
        "name_it": "OnlyOffice Desktop Editors",
        "name_en": "OnlyOffice Desktop Editors",
        "cat_it": "Ufficio e Documenti",
        "cat_en": "Office & Documents",
        "pkgs": [],
        "version": "N/A",
        "source": "Upstream OnlyOffice",
        "dl_mb": 0.0,
        "inst_mb": 0.0,
        "ram_mb": 0,
        "recommended": False,
        "available": False,
        "reason_it": "Compilato solo per x86_64 (amd64) e ARM64; nessun pacchetto armhf 32-bit disponibile (usa LibreOffice).",
        "reason_en": "Built only for x86_64 (amd64) and ARM64; no 32-bit armhf package exists (use LibreOffice).",
    },
    {
        "slot": 3,
        "id": "vlc",
        "name_it": "VLC Media Player",
        "name_en": "VLC Media Player",
        "cat_it": "Multimedia e Grafica",
        "cat_en": "Multimedia & Graphics",
        "pkgs": ["vlc"],
        "version": "3.0.23-0+deb12u1",
        "source": "Debian main (armhf)",
        "dl_mb": 31.7,
        "inst_mb": 73.9,
        "ram_mb": 65,
        "recommended": True,
        "available": True,
    },
    {
        "slot": 4,
        "id": "chromium",
        "name_it": "Chromium Web Browser (sostituisce Google Chrome, assente su armhf)",
        "name_en": "Chromium Web Browser (replaces Google Chrome, unavailable on armhf)",
        "cat_it": "Internet e Comunicazione",
        "cat_en": "Internet & Communication",
        "pkgs": ["chromium"],
        "version": "150.0.7871.100-1~deb12u1",
        "source": "Debian security/main (armhf)",
        "dl_mb": 98.4,
        "inst_mb": 257.3,
        "ram_mb": 260,
        "recommended": False,
        "available": True,
    },
    {
        "slot": 5,
        "id": "code",
        "name_it": "Visual Studio Code (Build ufficiale Microsoft ARMv7 armhf)",
        "name_en": "Visual Studio Code (Official Microsoft ARMv7 armhf build)",
        "cat_it": "Sviluppo e Testo",
        "cat_en": "Development & Text",
        "pkgs": ["code"],
        "version": "1.106.3-1764110884",
        "source": "Microsoft Official Repo (armhf, signed-by)",
        "dl_mb": 100.0,
        "inst_mb": 357.6,
        "ram_mb": 310,
        "recommended": False,
        "available": True,
    },
    {
        "slot": 6,
        "id": "spotify",
        "name_it": "Spotify Client",
        "name_en": "Spotify Client",
        "cat_it": "Multimedia e Grafica",
        "cat_en": "Multimedia & Graphics",
        "pkgs": [],
        "version": "N/A",
        "source": "repository.spotify.com",
        "dl_mb": 0.0,
        "inst_mb": 0.0,
        "ram_mb": 0,
        "recommended": False,
        "available": False,
        "reason_it": "Il repository ufficiale Spotify fornisce solo binari amd64 e Widevine DRM non è supportato su Linux armhf standard.",
        "reason_en": "Official Spotify repo only provides amd64 binaries and Widevine DRM is unavailable on standard Linux armhf.",
    },
    {
        "slot": 7,
        "id": "steam",
        "name_it": "Steam",
        "name_en": "Steam",
        "cat_it": "Multimedia e Grafica",
        "cat_en": "Multimedia & Graphics",
        "pkgs": [],
        "version": "N/A",
        "source": "Debian non-free",
        "dl_mb": 0.0,
        "inst_mb": 0.0,
        "ram_mb": 0,
        "recommended": False,
        "available": False,
        "reason_it": "Client proprietario solo x86 (i386/amd64); non esiste versione nativa ARMv7 armhf.",
        "reason_en": "Proprietary x86-only client (i386/amd64); no native ARMv7 armhf version exists.",
    },
    {
        "slot": 8,
        "id": "firefox-esr",
        "name_it": "Firefox ESR (Browser Web leggero consigliato)",
        "name_en": "Firefox ESR (Recommended lightweight Web Browser)",
        "cat_it": "Internet e Comunicazione",
        "cat_en": "Internet & Communication",
        "pkgs": ["firefox-esr"],
        "version": "140.12.0esr-1~deb12u1",
        "source": "Debian security/main (armhf)",
        "dl_mb": 69.1,
        "inst_mb": 221.6,
        "ram_mb": 220,
        "recommended": True,
        "available": True,
    },
    {
        "slot": 9,
        "id": "libreoffice",
        "name_it": "LibreOffice (Writer, Calc, Impress)",
        "name_en": "LibreOffice (Writer, Calc, Impress)",
        "cat_it": "Ufficio e Documenti",
        "cat_en": "Office & Documents",
        "pkgs": ["libreoffice-writer", "libreoffice-calc", "libreoffice-impress", "libreoffice-qt5"],
        "version": "4:7.4.7-1+deb12u14",
        "source": "Debian main (armhf)",
        "dl_mb": 108.8,
        "inst_mb": 402.8,
        "ram_mb": 165,
        "recommended": False,
        "available": True,
    },
    {
        "slot": 10,
        "id": "thunderbird",
        "name_it": "Thunderbird (Client Email e Calendario)",
        "name_en": "Thunderbird (Email & Calendar Client)",
        "cat_it": "Internet e Comunicazione",
        "cat_en": "Internet & Communication",
        "pkgs": [],
        "version": "N/A (Candidate: none)",
        "source": "Debian main (assente su armhf)",
        "dl_mb": 0.0,
        "inst_mb": 0.0,
        "ram_mb": 0,
        "recommended": False,
        "available": False,
        "reason_it": "Assente nei repository Debian 12 Bookworm armhf (Candidate: none; build 32-bit rimossa per limiti spazio indirizzi linker Rust/LLVM).",
        "reason_en": "Absent from Debian 12 Bookworm armhf repositories (Candidate: none; 32-bit build dropped due to Rust/LLVM linker address space limits).",
    },
    {
        "slot": 11,
        "id": "gimp",
        "name_it": "GIMP (Fotoritocco ed Elaborazione Immagini)",
        "name_en": "GIMP (Image Manipulation Program)",
        "cat_it": "Multimedia e Grafica",
        "cat_en": "Multimedia & Graphics",
        "pkgs": ["gimp"],
        "version": "2.10.34-1+deb12u10",
        "source": "Debian main (armhf)",
        "dl_mb": 55.9,
        "inst_mb": 216.6,
        "ram_mb": 145,
        "recommended": False,
        "available": True,
    },
    {
        "slot": 12,
        "id": "audacity",
        "name_it": "Audacity (Editor e Registratore Audio)",
        "name_en": "Audacity (Audio Editor & Recorder)",
        "cat_it": "Multimedia e Grafica",
        "cat_en": "Multimedia & Graphics",
        "pkgs": ["audacity"],
        "version": "3.2.4+dfsg-1",
        "source": "Debian main (armhf)",
        "dl_mb": 12.8,
        "inst_mb": 45.0,
        "ram_mb": 95,
        "recommended": False,
        "available": True,
    },
    {
        "slot": 13,
        "id": "pdf-reader",
        "desktop_variants": {
            "lxqt": {
                "id": "qpdfview",
                "name_it": "qpdfview (Lettore PDF rapido Qt)",
                "name_en": "qpdfview (Fast Qt PDF Viewer)",
                "pkgs": ["qpdfview"],
                "version": "0.5.0+ds-2",
                "dl_mb": 3.4,
                "inst_mb": 7.8,
                "ram_mb": 32,
            },
            "kde": {
                "id": "okular",
                "name_it": "Okular (Lettore PDF e Documenti KDE)",
                "name_en": "Okular (KDE PDF & Document Viewer)",
                "pkgs": ["okular"],
                "version": "4:22.12.3-1+deb12u1",
                "dl_mb": 65.5,
                "inst_mb": 204.6,
                "ram_mb": 58,
            },
        },
        "cat_it": "Ufficio e Documenti",
        "cat_en": "Office & Documents",
        "source": "Debian main (armhf)",
        "recommended": False,
        "available": True,
    },
    {
        "slot": 14,
        "id": "text-editor",
        "desktop_variants": {
            "lxqt": {
                "id": "featherpad",
                "name_it": "FeatherPad (Editor di testo leggero Qt)",
                "name_en": "FeatherPad (Lightweight Qt Text Editor)",
                "pkgs": ["featherpad"],
                "version": "1.3.5-1",
                "dl_mb": 0.5,
                "inst_mb": 1.4,
                "ram_mb": 24,
            },
            "kde": {
                "id": "kate",
                "name_it": "Kate (Editor di testo avanzato KDE)",
                "name_en": "Kate (KDE Advanced Text Editor)",
                "pkgs": ["kate"],
                "version": "4:22.12.3-1",
                "dl_mb": 39.7,
                "inst_mb": 157.1,
                "ram_mb": 55,
            },
        },
        "cat_it": "Sviluppo e Testo",
        "cat_en": "Development & Text",
        "source": "Debian main (armhf)",
        "recommended": False,
        "available": True,
    },
    {
        "slot": 15,
        "id": "image-viewer",
        "desktop_variants": {
            "lxqt": {
                "id": "lximage-qt",
                "name_it": "LXImage-Qt (Visualizzatore immagini LXQt)",
                "name_en": "LXImage-Qt (LXQt Image Viewer)",
                "pkgs": ["lximage-qt"],
                "version": "1.2.0-2",
                "dl_mb": 2.2,
                "inst_mb": 13.5,
                "ram_mb": 26,
            },
            "kde": {
                "id": "gwenview",
                "name_it": "Gwenview (Visualizzatore immagini KDE)",
                "name_en": "Gwenview (KDE Image Viewer)",
                "pkgs": ["gwenview"],
                "version": "4:22.12.3-1",
                "dl_mb": 63.7,
                "inst_mb": 196.5,
                "ram_mb": 54,
            },
        },
        "cat_it": "Multimedia e Grafica",
        "cat_en": "Multimedia & Graphics",
        "source": "Debian main (armhf)",
        "recommended": False,
        "available": True,
    },
    {
        "slot": 16,
        "id": "qbittorrent",
        "name_it": "qBittorrent (Client BitTorrent Qt)",
        "name_en": "qBittorrent (Qt BitTorrent Client)",
        "cat_it": "Internet e Comunicazione",
        "cat_en": "Internet & Communication",
        "pkgs": ["qbittorrent"],
        "version": "4.5.2-3+deb12u1",
        "source": "Debian main (armhf)",
        "dl_mb": 8.3,
        "inst_mb": 13.6,
        "ram_mb": 45,
        "recommended": False,
        "available": True,
    },
    {
        "slot": 17,
        "id": "keepassxc",
        "name_it": "KeePassXC (Gestore Password Cifrato)",
        "name_en": "KeePassXC (Encrypted Password Manager)",
        "cat_it": "Sistema e Utilità",
        "cat_en": "System & Utilities",
        "pkgs": ["keepassxc"],
        "version": "2.7.4+dfsg.1-2",
        "source": "Debian main (armhf)",
        "dl_mb": 8.7,
        "inst_mb": 29.5,
        "ram_mb": 42,
        "recommended": False,
        "available": True,
    },
    {
        "slot": 18,
        "id": "telegram-desktop",
        "name_it": "Telegram Desktop (Messaggistica)",
        "name_en": "Telegram Desktop (Messaging)",
        "cat_it": "Internet e Comunicazione",
        "cat_en": "Internet & Communication",
        "pkgs": ["telegram-desktop"],
        "version": "4.6.5+ds-2+b1",
        "source": "Debian main (armhf)",
        "dl_mb": 49.4,
        "inst_mb": 110.5,
        "ram_mb": 125,
        "recommended": False,
        "available": True,
    },
    {
        "slot": 19,
        "id": "inkscape",
        "name_it": "Inkscape (Grafica Vettoriale SVG)",
        "name_en": "Inkscape (SVG Vector Graphics Editor)",
        "cat_it": "Multimedia e Grafica",
        "cat_en": "Multimedia & Graphics",
        "pkgs": ["inkscape"],
        "version": "1.2.2-2+b1",
        "source": "Debian main (armhf)",
        "dl_mb": 29.9,
        "inst_mb": 120.5,
        "ram_mb": 150,
        "recommended": False,
        "available": True,
    },
    {
        "slot": 20,
        "id": "calibre",
        "name_it": "Calibre (Gestione e Lettura E-Book)",
        "name_en": "Calibre (E-Book Manager & Reader)",
        "cat_it": "Ufficio e Documenti",
        "cat_en": "Office & Documents",
        "pkgs": ["calibre"],
        "version": "6.13.0+repack-2+deb12u9",
        "source": "Debian main (armhf)",
        "dl_mb": 112.2,
        "inst_mb": 291.3,
        "ram_mb": 135,
        "recommended": False,
        "available": True,
    },
]

# Le 6 Riserve verificate nell'ordine richiesto:
# Strawberry, Kdenlive, Flameshot, Syncthing, Remmina, Geany
RESERVE_CANDIDATES = [
    {
        "id": "strawberry",
        "name_it": "Strawberry Music Player (Lettore e Collezione Musicale Qt)",
        "name_en": "Strawberry Music Player (Qt Music Player & Organizer)",
        "cat_it": "Multimedia e Grafica",
        "cat_en": "Multimedia & Graphics",
        "pkgs": ["strawberry"],
        "version": "1.0.14-1",
        "source": "Debian main (armhf)",
        "dl_mb": 30.9,
        "inst_mb": 74.0,
        "ram_mb": 52,
        "recommended": False,
        "available": True,
    },
    {
        "id": "kdenlive",
        "name_it": "Kdenlive (Editor Video Non-Lineare Qt/MLT)",
        "name_en": "Kdenlive (Non-Linear Video Editor Qt/MLT)",
        "cat_it": "Multimedia e Grafica",
        "cat_en": "Multimedia & Graphics",
        "pkgs": ["kdenlive"],
        "version": "22.12.3-2+deb12u2",
        "source": "Debian main (armhf)",
        "dl_mb": 211.9,
        "inst_mb": 517.2,
        "ram_mb": 140,
        "recommended": False,
        "available": True,
    },
    {
        "id": "flameshot",
        "name_it": "Flameshot (Cattura e Annotazione Schermate Qt)",
        "name_en": "Flameshot (Qt Screenshot & Annotation Tool)",
        "cat_it": "Sistema e Utilità",
        "cat_en": "System & Utilities",
        "pkgs": ["flameshot"],
        "version": "12.1.0-2",
        "source": "Debian main (armhf)",
        "dl_mb": 0.6,
        "inst_mb": 2.7,
        "ram_mb": 28,
        "recommended": False,
        "available": True,
    },
    {
        "id": "syncthing",
        "name_it": "Syncthing (Sincronizzazione File P2P Continua)",
        "name_en": "Syncthing (Continuous P2P File Synchronization)",
        "cat_it": "Internet e Comunicazione",
        "cat_en": "Internet & Communication",
        "pkgs": ["syncthing"],
        "version": "1.19.2~ds1-1+b4",
        "source": "Debian main (armhf)",
        "dl_mb": 6.6,
        "inst_mb": 19.9,
        "ram_mb": 38,
        "recommended": False,
        "available": True,
    },
    {
        "id": "remmina",
        "name_it": "Remmina (Client Desktop Remoto RDP/VNC/SSH)",
        "name_en": "Remmina (Remote Desktop Client RDP/VNC/SSH)",
        "cat_it": "Internet e Comunicazione",
        "cat_en": "Internet & Communication",
        "pkgs": ["remmina"],
        "version": "1.4.29+dfsg-1",
        "source": "Debian main (armhf)",
        "dl_mb": 2.7,
        "inst_mb": 8.2,
        "ram_mb": 46,
        "recommended": False,
        "available": True,
    },
    {
        "id": "geany",
        "name_it": "Geany (IDE Leggero e Veloce)",
        "name_en": "Geany (Fast and Lightweight IDE)",
        "cat_it": "Sviluppo e Testo",
        "cat_en": "Development & Text",
        "pkgs": ["geany"],
        "version": "1.38-1+b1",
        "source": "Debian main (armhf)",
        "dl_mb": 4.0,
        "inst_mb": 11.9,
        "ram_mb": 34,
        "recommended": False,
        "available": True,
    },
]


def resolve_apps_for_desktop(desktop_id: str):
    """
    Restituisce:
      - installable_20: lista di esattamente 20 programmi installabili aggiuntivi
      - already_in_base: lista dei programmi già inclusi nella base del desktop scelto
      - unavailable: lista dei programmi non disponibili su armhf con motivo in una riga
    """
    desk = DESKTOPS.get(desktop_id, DESKTOPS["lxqt"])
    base_ids = desk["base_included_ids"]

    installable = []
    already_in_base = []
    unavailable = []

    for item in PRIMARY_CANDIDATES:
        if not item.get("available", True):
            unavailable.append(item)
            continue

        entry = dict(item)
        if "desktop_variants" in item:
            var = item["desktop_variants"][desktop_id]
            entry.update(var)

        if entry["id"] in base_ids:
            already_in_base.append(entry)
        else:
            installable.append(entry)

    # Aggiungi le riserve nell'ordine fissato fino a raggiungere esattamente 20 installabili
    for res in RESERVE_CANDIDATES:
        if len(installable) >= 20:
            break
        if res["id"] not in base_ids and all(x["id"] != res["id"] for x in installable):
            installable.append(dict(res))

    return installable[:20], already_in_base, unavailable

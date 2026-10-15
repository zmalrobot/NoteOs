#!/usr/bin/env python3
"""
wizard/wizard_app.py — Wizard Grafico Touch di Primo Avvio (noteos-setup)
Progettato per Samsung Galaxy Note 10.1 (GT-N8000, 1280x800, 2 GB RAM, ARMv7 armhf).

Caratteristiche:
- 8 schermate nell'ordine esatto richiesto (Lingua/Tastiera, Rete Wi-Fi, Data/Ora/Fuso,
  Desktop LXQt/KDE con base sempre inclusa, 20 Programmi verificati + sezione non disponibili
  + sezione già inclusi, Utente/Hostname, Login automatico, Riepilogo e Installazione).
- Tutti i pulsanti, checkbox e controlli interattivi >= 52 px per usabilità solo touch.
- Tastiera virtuale touch integrata automatica al focus di qualsiasi campo di testo (QLineEdit)
  + supporto Onboard di sistema.
- Traduzione istantanea Italiano / English.
- Salvataggio stato ad ogni passo in state.json (escluse le password, mai scritte su disco o nei log)
  per riprendere dopo uno spegnimento imprevisto.
- Supporto --rerun, --dry-run e --test-screenshots <dir>.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request

def _global_exception_handler(exctype, value, tb):
    err_str = "".join(traceback.format_exception(exctype, value, tb))
    sys.stderr.write(f"UNHANDLED EXCEPTION in noteos-setup - {err_str}\n")
    try:
        with open("/var/log/noteos-setup-crash.log", "a") as f:
            f.write(f"\n--- Crash at {time.ctime()} ---\n{err_str}\n")
    except Exception:
        pass
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = _global_exception_handler

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal, QObject, QEvent, QPointF
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QPainterPath, QPalette
from PyQt5.QtWidgets import (
    QAbstractButton,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from catalog import DESKTOPS, resolve_apps_for_desktop

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHECK_PNG = os.path.join(SCRIPT_DIR, "assets", "check.png")
DOWN_ARROW_PNG = os.path.join(SCRIPT_DIR, "assets", "down_arrow.png")


# ==============================================================================
# WIDGET INDICATORI A PUNTI (PAGINATION DOTS — 8 PASSI STILE KDE BREEZE)
# ==============================================================================
class PaginationDotsWidget(QWidget):
    def __init__(self, count=8, parent=None):
        super().__init__(parent)
        self.count = count
        self.current_step = 0
        self.setFixedHeight(14)
        self.setMinimumWidth(160)

    def set_step(self, step):
        self.current_step = step
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        spacing = 9.0
        active_r = 4.5
        inactive_r = 3.0

        total_width = (self.count - 1) * (2 * inactive_r) + (2 * active_r) + (self.count - 1) * spacing
        start_x = (self.width() - total_width) / 2.0
        center_y = self.height() / 2.0

        cur_x = start_x
        for i in range(self.count):
            if i == self.current_step:
                painter.setBrush(QColor("#3daee9"))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QPointF(cur_x + active_r, center_y), active_r, active_r)
                cur_x += 2 * active_r + spacing
            else:
                painter.setBrush(QColor("#4b5660"))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QPointF(cur_x + inactive_r, center_y), inactive_r, inactive_r)
                cur_x += 2 * inactive_r + spacing
        painter.end()

# ==============================================================================
# DIZIONARIO TRADUZIONI (ITALIANO / ENGLISH)
# ==============================================================================
TR = {
    "it": {
        "app_title": "NoteOS — Configurazione di Primo Avvio (GT-N8000)",
        "btn_back": "◀  Indietro",
        "btn_next": "Avanti  ▶",
        "btn_kbd": "⌨  Tastiera Touch",
        "step_of": "Passo {cur} di 8",
        # Screen 1
        "s1_title": "Passo 1: Lingua di Sistema e Tastiera",
        "s1_desc": "Seleziona la lingua per il sistema NoteOS e configura il layout della tastiera.",
        "s1_lang_hdr": "Seleziona la lingua",
        "s1_kb_hdr": "Layout della tastiera",
        "s1_vkbd_chk": "Attiva tastiera virtuale touch su schermo",
        # Screen 2
        "s2_title": "2. Connessione di Rete Wi-Fi",
        "s2_desc": "Seleziona una rete Wi-Fi e verifica l'accesso a Internet (obbligatorio per scaricare il desktop e i programmi).",
        "s2_scan_btn": "🔄  Scansiona Reti Wi-Fi",
        "s2_hidden_chk": "Connetti a una rete Wi-Fi nascosta (inserisci SSID)",
        "s2_ssid_ph": "Nome rete Wi-Fi (SSID)...",
        "s2_pass_ph": "Password Wi-Fi (WPA2/WPA3)...",
        "s2_show_pass": "Mostra password",
        "s2_connect_btn": "📶  Connetti e Verifica Internet",
        "s2_status_ok": "✅ Connesso a Internet ({net}). Puoi procedere al passo successivo.",
        "s2_status_wait": "⚠️ Non connesso a Internet. Connettiti a una rete Wi-Fi per abilitare 'Avanti'.",
        "s2_status_err": "❌ Errore di connessione o Internet assente: {err}",
        # Screen 3
        "s3_title": "3. Data, Ora e Fuso Orario",
        "s3_ntp_chk": "Sincronizza automaticamente data e ora via Internet (NTP)",
        "s3_tz_lbl": "Fuso orario (Timezone):",
        "s3_man_lbl": "Impostazione manuale data e ora (usata se NTP non è disponibile):",
        "s3_apply_btn": "🕒  Applica Data, Ora e Fuso Orario",
        # Screen 4
        "s4_title": "4. Scelta dell'Ambiente Desktop",
        "s4_desc": "La base del desktop scelto (impostazioni, file manager, terminale, archivi, rete, audio, tastiera touch) viene SEMPRE installata di serie.",
        "s4_base_hdr": "📦 Componenti della Base del Desktop (Sempre Inclusi):",
        "s4_stats": "RAM a riposo misurata: ~{ram} MiB   |   Download base: {dl:.1f} MiB   |   Spazio installato: {inst:.1f} MiB",
        # Screen 5
        "s5_title": "5. Scelta dei Programmi (20 Verificati per ARMv7 armhf)",
        "s5_rec_btn": "⭐  Selezione consigliata (btop, VLC + Firefox ESR)",
        "s5_clear_btn": "Deseleziona tutti",
        "s5_summary": "Selezionati: {cnt}/20 programmi  |  Download: +{dl:.1f} MiB  |  Spazio richiesto (Desktop+App): {tot:.1f} MiB su {free:.0f} MiB liberi  |  RAM stimata: ~{ram} MiB",
        "s5_ram_warn": "⚠️ ATTENZIONE: La selezione attuale + desktop supera la soglia consigliata per 2 GB di RAM. Evita di aprire molte app pesanti contemporaneamente.",
        "s5_in_base_hdr": "✔ Già incluso nella base del desktop scelto (non conta tra i 20; slot assegnato alle riserve):",
        "s5_unavail_hdr": "✖ Non disponibile su questo dispositivo (ARM 32-bit armhf — sostituito dalle riserve):",
        # Screen 6
        "s6_title": "6. Creazione Utente e Nome Dispositivo",
        "s6_fn_lbl": "Nome completo:",
        "s6_un_lbl": "Nome utente (username, solo minuscole/numeri):",
        "s6_pw1_lbl": "Password utente (anche per sudo):",
        "s6_pw2_lbl": "Conferma password:",
        "s6_hn_lbl": "Nome dispositivo (hostname):",
        "s6_err_empty": "❌ Compila nome utente e password (minimo 4 caratteri).",
        "s6_err_user": "❌ Nome utente non valido (usa solo lettere minuscole, numeri, '-' o '_').",
        "s6_err_match": "❌ Le due password non coincidono!",
        # Screen 7
        "s7_title": "7. Accesso Automatico all'Avvio (Autologin)",
        "s7_yes": "Sì — Accedi automaticamente al desktop all'accensione (Consigliato per uso tablet)",
        "s7_no": "No — Chiedi la password nella schermata di login SDDM (con tastiera virtuale touch)",
        # Screen 8
        "s8_title": "8. Riepilogo e Installazione",
        "s8_bat_warn": "⚠️ Batteria rilevata al {cap}% ({st}). Assicurati che il cavo di alimentazione resti collegato durante l'installazione.",
        "s8_bat_ok": "🔋 Stato alimentazione: {cap}% ({st}) — Schermo mantenuto sempre acceso.",
        "s8_start_btn": "🚀  Avvia Installazione Completa",
        "s8_retry_btn": "🔁  Riprova Installazione (riprende dal punto interrotto)",
        "s8_reboot_btn": "✅  Installazione Completata — Riavvia in NoteOS",
        "s8_sum_lang": "• Lingua / Tastiera : {lang} / layout '{kb}' (Tastiera Touch: {vkbd})",
        "s8_sum_wifi": "• Rete Wi-Fi / Fuso : {net}   |   Fuso: {tz} (NTP: {ntp})",
        "s8_sum_desk": "• Ambiente Desktop  : {desk} + {base} ({mb:.1f} MiB)",
        "s8_sum_apps": "• Programmi ({cnt:02d}/20) : {apps}",
        "s8_sum_user": "• Utente / Hostname : {user} ({name}) @ {host}   |   Autologin: {auto}",
        "s8_yes": "Sì",
        "s8_no": "No",
        "s8_none": "Nessuno",
        "s8_base_inc": "Base completa di serie",
        "s8_active": "Attiva",
        "inst_step_init": "Configurazione lingua, tastiera, fuso orario e hostname...",
        "inst_log_init": "Impostazione locale={locale}, tastiera={kb}, fuso={tz}, hostname={host}",
        "inst_step_apt": "Aggiornamento indici dei pacchetti Debian (apt-get update)...",
        "inst_log_vscode": "Configurazione repository ufficiale Microsoft VS Code (armhf, signed-by)...",
        "inst_log_vscode_err": "Avviso: Impossibile scaricare la chiave Microsoft ({err}); VS Code verrà saltato",
        "inst_step_desk": "Installazione base desktop ({desk}: {cnt} pacchetti)...",
        "inst_step_apps": "Installazione programmi selezionati ({cnt} pacchetti)...",
        "inst_step_user": "Creazione utente, configurazione sudo, Baloo e SDDM...",
        "inst_log_user": "Creazione/aggiornamento utente '{user}' ({name})...",
        "inst_step_clean": "Pulizia cache apt e scrittura setup.done...",
        "inst_step_done": "Installazione completata con successo!",
        "inst_log_done": "Setup di NoteOS completato con successo. Pronto per il riavvio.",
        "inst_err_prefix": "Errore installazione",
        "inst_sim_err": "ERRORE SIMULATO: Connessione interrotta durante apt-get update!",
        "inst_cmd_fail": "Comando fallito (exit {rc}): {cmd}",
        "inst_repo_unavail": "Repository non raggiungibili o indice pacchetti non disponibile. Verifica la connessione Internet e riprova.",
        "inst_dns_unavail": "Risoluzione DNS fallita per deb.debian.org. Verifica che la rete Wi-Fi abbia accesso a Internet.",
    },
    "en": {
        "app_title": "NoteOS — First-Boot Setup Wizard (GT-N8000)",
        "btn_back": "◀  Back",
        "btn_next": "Next  ▶",
        "btn_kbd": "⌨  Touch Keyboard",
        "step_of": "Step {cur} of 8",
        # Screen 1
        "s1_title": "Step 1: System Language & Keyboard",
        "s1_desc": "Select the system language for NoteOS and configure the keyboard layout.",
        "s1_lang_hdr": "Select language",
        "s1_kb_hdr": "Keyboard layout",
        "s1_vkbd_chk": "Enable on-screen touch virtual keyboard",
        # Screen 2
        "s2_title": "2. Wi-Fi Network Connection",
        "s2_desc": "Select a Wi-Fi network and verify Internet access (mandatory to download desktop and applications).",
        "s2_scan_btn": "🔄  Scan Wi-Fi Networks",
        "s2_hidden_chk": "Connect to a hidden Wi-Fi network (enter SSID)",
        "s2_ssid_ph": "Wi-Fi Network Name (SSID)...",
        "s2_pass_ph": "Wi-Fi Password (WPA2/WPA3)...",
        "s2_show_pass": "Show password",
        "s2_connect_btn": "📶  Connect & Verify Internet",
        "s2_status_ok": "✅ Connected to Internet ({net}). You may proceed to the next step.",
        "s2_status_wait": "⚠️ Not connected to Internet. Connect to Wi-Fi to enable 'Next'.",
        "s2_status_err": "❌ Connection error or no Internet access: {err}",
        # Screen 3
        "s3_title": "3. Date, Time & Timezone",
        "s3_ntp_chk": "Automatically synchronize date and time via Internet (NTP)",
        "s3_tz_lbl": "Timezone:",
        "s3_man_lbl": "Manual date and time setting (fallback if NTP is unavailable):",
        "s3_apply_btn": "🕒  Apply Date, Time & Timezone",
        # Screen 4
        "s4_title": "4. Desktop Environment Selection",
        "s4_desc": "The chosen desktop's base (settings, file manager, terminal, archives, network, audio, touch keyboard) is ALWAYS installed by default.",
        "s4_base_hdr": "📦 Desktop Base Components (Always Included):",
        "s4_stats": "Measured idle RAM: ~{ram} MiB   |   Base download: {dl:.1f} MiB   |   Installed size: {inst:.1f} MiB",
        # Screen 5
        "s5_title": "5. Application Selection (20 Verified for ARMv7 armhf)",
        "s5_rec_btn": "⭐  Recommended selection (btop, VLC + Firefox ESR)",
        "s5_clear_btn": "Clear all",
        "s5_summary": "Selected: {cnt}/20 apps  |  Download: +{dl:.1f} MiB  |  Required space (Desktop+Apps): {tot:.1f} MiB of {free:.0f} MiB free  |  Est. RAM: ~{ram} MiB",
        "s5_ram_warn": "⚠️ WARNING: Current selection + desktop exceeds recommended threshold for 2 GB RAM. Avoid running multiple heavy apps simultaneously.",
        "s5_in_base_hdr": "✔ Already included in chosen desktop base (does not count toward 20; slot filled from reserves):",
        "s5_unavail_hdr": "✖ Unavailable on this device (32-bit ARM armhf — replaced from reserves):",
        # Screen 6
        "s6_title": "6. User Account & Device Hostname",
        "s6_fn_lbl": "Full Name:",
        "s6_un_lbl": "Username (lowercase letters/numbers only):",
        "s6_pw1_lbl": "User Password (also used for sudo):",
        "s6_pw2_lbl": "Confirm Password:",
        "s6_hn_lbl": "Device Hostname:",
        "s6_err_empty": "❌ Please fill in username and password (minimum 4 characters).",
        "s6_err_user": "❌ Invalid username (use lowercase letters, numbers, '-' or '_' only).",
        "s6_err_match": "❌ Passwords do not match!",
        # Screen 7
        "s7_title": "7. Automatic Login at Boot (Autologin)",
        "s7_yes": "Yes — Log in automatically to the desktop at boot (Recommended for tablet use)",
        "s7_no": "No — Require password at the SDDM login screen (with touch virtual keyboard)",
        # Screen 8
        "s8_title": "8. Summary & Installation",
        "s8_bat_warn": "⚠️ Battery level is {cap}% ({st}). Keep the power cable plugged in during installation.",
        "s8_bat_ok": "🔋 Power status: {cap}% ({st}) — Screen blanking disabled.",
        "s8_start_btn": "🚀  Start Full Installation",
        "s8_retry_btn": "🔁  Retry Installation (resumes from interrupted step)",
        "s8_reboot_btn": "✅  Installation Complete — Reboot into Desktop",
        "s8_sum_lang": "• Language / Keyboard : {lang} / layout '{kb}' (Touch Keyboard: {vkbd})",
        "s8_sum_wifi": "• Wi-Fi Network / Timezone : {net}   |   Timezone: {tz} (NTP: {ntp})",
        "s8_sum_desk": "• Desktop Environment : {desk} + {base} ({mb:.1f} MiB)",
        "s8_sum_apps": "• Applications ({cnt:02d}/20) : {apps}",
        "s8_sum_user": "• User / Hostname : {user} ({name}) @ {host}   |   Autologin: {auto}",
        "s8_yes": "Yes",
        "s8_no": "No",
        "s8_none": "None",
        "s8_base_inc": "Full base included",
        "s8_active": "Active",
        "inst_step_init": "Configuring language, keyboard, timezone and hostname...",
        "inst_log_init": "Setting locale={locale}, keyboard={kb}, timezone={tz}, hostname={host}",
        "inst_step_apt": "Updating Debian package lists (apt-get update)...",
        "inst_log_vscode": "Configuring official Microsoft VS Code repository (armhf, signed-by)...",
        "inst_log_vscode_err": "Warning: Could not fetch Microsoft key ({err}); skipping VS Code repo",
        "inst_step_desk": "Installing desktop base ({desk}: {cnt} packages)...",
        "inst_step_apps": "Installing selected applications ({cnt} packages)...",
        "inst_step_user": "Creating user account, configuring sudo, Baloo and SDDM...",
        "inst_log_user": "Creating/updating user '{user}' ({name})...",
        "inst_step_clean": "Cleaning apt cache and writing setup.done...",
        "inst_step_done": "Installation completed successfully!",
        "inst_log_done": "NoteOS setup completed successfully. Ready to reboot.",
        "inst_err_prefix": "Installation error",
        "inst_sim_err": "SIMULATED ERROR: Connection lost during apt-get update!",
        "inst_cmd_fail": "Command failed (exit {rc}): {cmd}",
        "inst_repo_unavail": "Repositories unreachable or package index unavailable. Please verify Internet connection and retry.",
        "inst_dns_unavail": "DNS resolution failed for deb.debian.org. Please verify your Wi-Fi network has Internet access.",
    },
}


# ==============================================================================
# TASTIERA TOUCH VIRTUALE INTEGRATA (QWERTY >= 48px PER TASTO)
# ==============================================================================
class TouchKeyboardWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.target_input = None
        self.shift_active = False
        self.setObjectName("TouchKeyboard")
        self.setStyleSheet("""
            QFrame#TouchKeyboard {
                background-color: #161c21;
                border-top: 1px solid #283138;
                padding: 4px;
            }
            QPushButton.kbdKey {
                background-color: #20272d;
                color: #eff0f1;
                border: 1px solid #48535d;
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
                min-height: 48px;
                min-width: 48px;
            }
            QPushButton.kbdKey:pressed {
                background-color: #1d99f3;
                color: #ffffff;
            }
        """)
        self.rows_lower = [
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "_"],
            ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "@", "."],
            ["a", "s", "d", "f", "g", "h", "j", "k", "l", "!", "?", "/"],
            ["SHIFT", "z", "x", "c", "v", "b", "n", "m", "SPACE", "⌫", "⬇ CHIUDI"],
        ]
        self.rows_upper = [
            ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "+", "="],
            ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", ":", ";"],
            ["A", "S", "D", "F", "G", "H", "J", "K", "L", ",", ".", "/"],
            ["SHIFT", "Z", "X", "C", "V", "B", "N", "M", "SPACE", "⌫", "⬇ CHIUDI"],
        ]
        self.key_buttons = []
        self._build_ui()

    def _build_ui(self):
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(6, 4, 6, 4)
        vbox.setSpacing(4)
        for r_idx, row in enumerate(self.rows_lower):
            hbox = QHBoxLayout()
            hbox.setSpacing(4)
            row_btns = []
            for key in row:
                btn = QPushButton(key)
                btn.setProperty("class", "kbdKey")
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setMinimumHeight(48)
                if key == "SPACE":
                    btn.setMinimumWidth(180)
                elif key in ("SHIFT", "⌫", "⬇ CHIUDI"):
                    btn.setMinimumWidth(95)
                btn.clicked.connect(lambda checked=False, r=r_idx, c=len(row_btns): self._on_key(r, c))
                hbox.addWidget(btn)
                row_btns.append(btn)
            self.key_buttons.append(row_btns)
            vbox.addLayout(hbox)

    def _on_key(self, r, c):
        rows = self.rows_upper if self.shift_active else self.rows_lower
        label = rows[r][c]
        if label == "⬇ CHIUDI":
            self.hide()
            return
        if label == "SHIFT":
            self.shift_active = not self.shift_active
            new_rows = self.rows_upper if self.shift_active else self.rows_lower
            for ri, r_btns in enumerate(self.key_buttons):
                for ci, b in enumerate(r_btns):
                    b.setText(new_rows[ri][ci])
            return
        if not self.target_input:
            return
        if label == "⌫":
            self.target_input.backspace()
        elif label == "SPACE":
            self.target_input.insert(" ")
        else:
            self.target_input.insert(label)


# ==============================================================================
# WORKER THREAD SCANSIONE RETI WI-FI (ASINCRONO, NON BLOCCANTE)
# ==============================================================================
class WifiScanWorker(QThread):
    finished_sig = pyqtSignal(list)

    def __init__(self, dry_run=False, state_dir="/var/lib/noteos"):
        super().__init__()
        self.dry_run = dry_run
        self.state_dir = state_dir

    def _log(self, msg):
        try:
            with open(os.path.join(self.state_dir, "wifi.log"), "a", encoding="utf-8") as f:
                f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} [scan] {msg}\n")
        except Exception:
            pass

    def run(self):
        nets = []
        if self.dry_run:
            nets = [
                ("TIM-33744972 (5 GHz)", 88, "WPA2", False),
                ("TIM-33744972 (2.4 GHz)", 92, "WPA2", False),
                ("Vodafone-30546686", 64, "WPA2", False),
                ("Hotspot-Mobile-N8000", 75, "WPA2/WPA3", False),
            ]
            self.finished_sig.emit(nets)
            return

        # 1. Pre-scan: Ensure kernel driver module is loaded, radio is enabled, and interface is UP
        try:
            subprocess.run(["modprobe", "brcmfmac"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            subprocess.run(["rfkill", "unblock", "wifi"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
            subprocess.run(["nmcli", "radio", "wifi", "on"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
            subprocess.run(["ip", "link", "set", "wlan0", "up"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
        except Exception as e:
            self._log(f"Pre-scan interface setup error: {e}")

        # 2. Stage A: Read cached network list first (instant response)
        out = ""
        try:
            res_cached = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,IN-USE", "dev", "wifi", "list"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5
            )
            out = res_cached.stdout
            if res_cached.returncode != 0 and res_cached.stderr:
                self._log(f"Cached scan stderr: {res_cached.stderr.strip()}")
        except Exception as e:
            self._log(f"Cached scan exception: {e}")

        # 3. Stage B: If cached list is empty or sparse, trigger active rescan with 25s timeout
        lines = [l for l in out.splitlines() if l.strip()]
        if len(lines) < 2:
            self._log("Cached list empty or sparse, triggering active scan...")
            try:
                res_active = subprocess.run(
                    ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,IN-USE", "dev", "wifi", "list", "--rescan", "auto"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=25
                )
                if res_active.stdout.strip():
                    out = res_active.stdout
                if res_active.returncode != 0 and res_active.stderr:
                    self._log(f"Active scan (--rescan auto) stderr: {res_active.stderr.strip()}")
                    # Fallback to --rescan yes if auto failed
                    res_yes = subprocess.run(
                        ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,IN-USE", "dev", "wifi", "list", "--rescan", "yes"],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=25
                    )
                    if res_yes.stdout.strip():
                        out = res_yes.stdout
                    elif res_yes.stderr:
                        self._log(f"Active scan (--rescan yes) stderr: {res_yes.stderr.strip()}")
            except Exception as e:
                self._log(f"Active scan exception: {e}")

        # 4. Parse networks safely handling escaped colons
        seen = set()
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            safe_line = line.replace(r"\:", "__COLON__")
            parts = safe_line.split(":")
            if len(parts) >= 4:
                ssid = parts[0].replace("__COLON__", ":").strip()
                sig_str = parts[1].strip()
                sec = parts[2].replace("__COLON__", ":").strip() or "OPEN"
                in_use = parts[3].strip() == "*"
                if ssid and ssid not in seen:
                    seen.add(ssid)
                    try:
                        sig = int(sig_str)
                    except ValueError:
                        sig = 50
                    nets.append((ssid, sig, sec, in_use))

        self._log(f"Scan finished: found {len(nets)} networks (seen={list(seen)[:5]})")
        self.finished_sig.emit(nets)


# ==============================================================================
# WORKER GENERICO: esegue una funzione bloccante fuori dal thread GUI
# ==============================================================================
class CallableWorker(QThread):
    done_sig = pyqtSignal(object)

    def __init__(self, fn):
        super().__init__()
        self._fn = fn

    def run(self):
        try:
            res = self._fn()
        except Exception as exc:  # delivered to the GUI thread, never swallowed silently
            res = exc
        self.done_sig.emit(res)


def ensure_dns_servers():
    """Garantisce che /etc/resolv.conf contenga sempre nameserver validi prima delle operazioni di rete."""
    try:
        has_ns = False
        if os.path.exists("/etc/resolv.conf"):
            with open("/etc/resolv.conf", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.strip().startswith("nameserver") and len(line.strip().split()) >= 2:
                        has_ns = True
                        break
        if not has_ns:
            os.makedirs("/etc", exist_ok=True)
            with open("/etc/resolv.conf", "a", encoding="utf-8") as f:
                f.write("\n# NoteOS Fallback DNS\nnameserver 1.1.1.1\nnameserver 8.8.8.8\nnameserver 1.0.0.1\n")
            return True
    except Exception:
        pass
    return False


# ==============================================================================
# WORKER THREAD DI INSTALLAZIONE (IDEMPOTENTE E CON RIPROVA)
# ==============================================================================
class InstallWorker(QThread):
    progress_sig = pyqtSignal(int, str)
    log_sig = pyqtSignal(str)
    finished_sig = pyqtSignal(bool, str)

    def __init__(self, state_dict, user_password, dry_run=False, simulate_apt_fail=False, log_path="/var/lib/noteos/install.log"):
        super().__init__()
        self.state = dict(state_dict)
        self.user_password = user_password
        self.dry_run = dry_run
        self.simulate_apt_fail = simulate_apt_fail
        self.log_path = log_path

    def _tr(self, key, **kwargs):
        lang = self.state.get("lang", "en")
        txt = TR.get(lang, TR["en"]).get(key, TR["en"].get(key, key))
        if kwargs:
            try:
                return txt.format(**kwargs)
            except Exception:
                return txt
        return txt

    def _log(self, msg):
        # Sicurezza: mai scrivere la password nei log
        if self.user_password and len(self.user_password) >= 2:
            msg = msg.replace(self.user_password, "********")
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self.log_sig.emit(line)
        try:
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def _run_cmd(self, cmd, check=True):
        self._log(f"$ {' '.join(cmd)}")
        if self.dry_run:
            time.sleep(0.15)
            return 0
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={
                **os.environ,
                "DEBIAN_FRONTEND": "noninteractive",
                "DEBCONF_NONINTERACTIVE_SEEN": "true",
            },
        )
        for line in proc.stdout:
            self._log("  " + line.rstrip("\n"))
        rc = proc.wait()
        if check and rc != 0:
            raise RuntimeError(self._tr("inst_cmd_fail", rc=rc, cmd=' '.join(cmd)))
        return rc

    def run(self):
        try:
            self.progress_sig.emit(5, self._tr("inst_step_init"))
            lang = self.state.get("lang", "it")
            locale_str = "it_IT.UTF-8" if lang == "it" else "en_US.UTF-8"
            kb_layout = self.state.get("kb_layout", "it")
            tz = self.state.get("timezone", "Europe/Rome")
            hostname = self.state.get("hostname", "noteos").strip() or "noteos"

            self._log(self._tr("inst_log_init", locale=locale_str, kb=kb_layout, tz=tz, host=hostname))
            if not self.dry_run:
                with open("/etc/default/locale", "w") as f:
                    f.write(f"LANG={locale_str}\n")
                with open("/etc/default/keyboard", "w") as f:
                    f.write(f'XKBMODEL="pc105"\nXKBLAYOUT="{kb_layout}"\nXKBVARIANT=""\nXKBOPTIONS=""\nBACKSPACE="guess"\n')
                if os.path.exists(f"/usr/share/zoneinfo/{tz}"):
                    if os.path.lexists("/etc/localtime"):
                        os.unlink("/etc/localtime")
                    os.symlink(f"/usr/share/zoneinfo/{tz}", "/etc/localtime")
                with open("/etc/timezone", "w") as f:
                    f.write(f"{tz}\n")
                with open("/etc/hostname", "w") as f:
                    f.write(f"{hostname}\n")
                with open("/etc/hosts", "w") as f:
                    f.write(f"127.0.0.1\tlocalhost\n127.0.1.1\t{hostname}\n::1\t\tlocalhost ip6-localhost ip6-loopback\n")

            self.progress_sig.emit(15, self._tr("inst_step_apt"))
            if self.simulate_apt_fail:
                self._log(self._tr("inst_sim_err"))
                raise RuntimeError("apt update simulated failure")

            # Assicura nameserver DNS prima di qualsiasi operazione di rete
            if not self.dry_run:
                ensure_dns_servers()

            # Se è stato selezionato VS Code, configura il repository ufficiale Microsoft armhf con signed-by
            selected_ids = set(self.state.get("selected_apps", []))
            if "code" in selected_ids:
                self._log(self._tr("inst_log_vscode"))
                if not self.dry_run:
                    key_file = "/etc/apt/keyrings/microsoft-archive-keyring.gpg"
                    if not os.path.exists(key_file):
                        try:
                            import base64
                            os.makedirs("/etc/apt/keyrings", exist_ok=True)
                            req = urllib.request.Request(
                                "https://packages.microsoft.com/keys/microsoft.asc",
                                headers={"User-Agent": "NoteOS-Setup/1.0 (GT-N8000)"}
                            )
                            with urllib.request.urlopen(req, timeout=15) as resp:
                                asc = resp.read().decode("ascii", errors="ignore")
                            b64_lines = [l.strip() for l in asc.splitlines() if l.strip() and not l.startswith("-----") and not l.startswith("=") and ":" not in l]
                            with open(key_file, "wb") as kf:
                                kf.write(base64.b64decode("".join(b64_lines)))
                            os.chmod(key_file, 0o644)
                        except Exception as key_err:
                            self._log(self._tr("inst_log_vscode_err", err=str(key_err)))
                    os.makedirs("/etc/apt/sources.list.d", exist_ok=True)
                    with open("/etc/apt/sources.list.d/vscode.list", "w") as f:
                        f.write(f"deb [arch=armhf signed-by={key_file}] https://packages.microsoft.com/repos/code stable main\n")

            self._run_cmd(["apt-get", "update"])

            desk_id = self.state.get("desktop", "lxqt")
            desk = DESKTOPS.get(desk_id, DESKTOPS["lxqt"])
            list_path = desk["list_file"] if os.path.exists(desk["list_file"]) else desk["fallback_list_file"]
            desk_pkgs = []
            if os.path.exists(list_path):
                with open(list_path) as f:
                    desk_pkgs = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]

            # Verifica che il catalogo pacchetti sia disponibile e interrogabile
            if not self.dry_run and desk_pkgs:
                chk_pkg = desk_pkgs[0]
                chk_proc = subprocess.run(
                    ["apt-cache", "policy", chk_pkg],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                if "Candidate: (none)" in chk_proc.stdout or "Unable to locate" in chk_proc.stderr:
                    raise RuntimeError(self._tr("inst_repo_unavail"))

            installable_20, _, _ = resolve_apps_for_desktop(desk_id)
            app_pkgs = []
            for app in installable_20:
                if app["id"] in selected_ids:
                    app_pkgs.extend(app["pkgs"])

            apt_install_cmd = [
                "apt-get", "install", "-y", "--no-install-recommends",
                "-o", "Dpkg::Options::=--force-confdef",
                "-o", "Dpkg::Options::=--force-confold",
            ]

            self.progress_sig.emit(35, self._tr("inst_step_desk", desk=desk_id.upper(), cnt=len(desk_pkgs)))
            if desk_pkgs:
                self._run_cmd(apt_install_cmd + desk_pkgs)

            self.progress_sig.emit(65, self._tr("inst_step_apps", cnt=len(app_pkgs)))
            if app_pkgs:
                self._run_cmd(apt_install_cmd + app_pkgs)

            self.progress_sig.emit(80, self._tr("inst_step_user"))
            username = self.state.get("username", "utente").strip()
            fullname = self.state.get("fullname", username).strip() or username
            autologin = bool(self.state.get("autologin", True))

            self._log(self._tr("inst_log_user", user=username, name=fullname))
            if not self.dry_run:
                rc = subprocess.run(["id", "-u", username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
                if rc != 0:
                    self._run_cmd(["useradd", "-m", "-s", "/bin/bash", "-c", fullname, "-G", "sudo,audio,video,render,input,netdev,bluetooth", username])
                else:
                    self._run_cmd(["usermod", "-aG", "sudo,audio,video,render,input,netdev,bluetooth", username])

                # Imposta password via stdin senza mai passarla sulla riga di comando o nei log
                p = subprocess.Popen(["chpasswd"], stdin=subprocess.PIPE, text=True)
                p.communicate(f"{username}:{self.user_password}\n")
                if p.returncode != 0:
                    raise RuntimeError("Impostazione password utente con chpasswd fallita.")

                # Disabilita Baloo su KDE sia a livello globale sia nella home dell'utente
                os.makedirs("/etc/xdg", exist_ok=True)
                with open("/etc/xdg/baloofilerc", "w") as f:
                    f.write("[Basic Settings]\nIndexing-Enabled=false\n")
                user_cfg = f"/home/{username}/.config"
                os.makedirs(user_cfg, exist_ok=True)
                with open(f"{user_cfg}/baloofilerc", "w") as f:
                    f.write("[Basic Settings]\nIndexing-Enabled=false\n")

                # Autostart tastiera virtuale Onboard se abilitata
                if self.state.get("vkbd_enabled", True):
                    autostart_dir = f"{user_cfg}/autostart"
                    os.makedirs(autostart_dir, exist_ok=True)
                    with open(f"{autostart_dir}/onboard-noteos.desktop", "w") as f:
                        f.write("[Desktop Entry]\nType=Application\nName=Onboard Touch Keyboard\nExec=onboard\nX-GNOME-Autostart-enabled=true\n")
                subprocess.run(["chown", "-R", f"{username}:{username}", f"/home/{username}"], check=False)

                # Configurazione SDDM (sessione + tastiera virtuale al login + autologin opzionale)
                os.makedirs("/etc/sddm.conf.d", exist_ok=True)
                session_name = desk["session_name"]
                sddm_theme = "breeze" if desk_id == "kde" else "debian-maui"
                sddm_lines = [
                    "[General]",
                    "InputMethod=qtvirtualkeyboard",
                    "",
                    "[Theme]",
                    f"Current={sddm_theme}",
                    "",
                ]
                if autologin:
                    sddm_lines.extend([
                        "[Autologin]",
                        f"User={username}",
                        f"Session={session_name}.desktop",
                        "Relogin=false",
                        "",
                    ])
                with open("/etc/sddm.conf.d/noteos.conf", "w") as f:
                    f.write("\n".join(sddm_lines))

                self._run_cmd(["systemctl", "enable", "sddm.service"], check=False)
                self._run_cmd(["systemctl", "set-default", "graphical.target"], check=False)

            self.progress_sig.emit(95, self._tr("inst_step_clean"))
            self._run_cmd(["apt-get", "clean"], check=False)
            done_file = os.path.join(os.path.dirname(self.log_path), "setup.done")
            os.makedirs(os.path.dirname(done_file), exist_ok=True)
            with open(done_file, "w") as f:
                f.write(json.dumps({
                    "completed_at": datetime.datetime.now().isoformat(),
                    "desktop": desk_id,
                    "username": username,
                    "hostname": hostname,
                    "autologin": autologin,
                    "selected_apps": list(selected_ids),
                }, indent=2) + "\n")

            self.progress_sig.emit(100, self._tr("inst_step_done"))
            self._log(self._tr("inst_log_done"))
            self.finished_sig.emit(True, self._tr("inst_step_done"))
        except Exception as e:
            self._log(f"{self._tr('inst_err_prefix')}: {e}")
            self.finished_sig.emit(False, str(e))


# ==============================================================================
# FINESTRA PRINCIPALE DEL WIZARD (1280x800 TOUCH-FIRST)
# ==============================================================================
class N8000SetupWizard(QMainWindow):
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.state_dir = args.state_dir
        self.state_file = os.path.join(self.state_dir, "state.json")
        self.done_file = os.path.join(self.state_dir, "setup.done")
        self.log_file = os.path.join(self.state_dir, "install.log")

        # State persistence (never store user passwords)
        self.state = {
            "step": 0,
            "lang": "en",
            "kb_layout": "us",
            "vkbd_enabled": True,
            "wifi_ssid": "",
            "net_connected": False,
            "net_name": "",
            "ntp_enabled": True,
            "timezone": "UTC",
            "desktop": "lxqt",
            "selected_apps": ["btop", "vlc", "firefox-esr"],
            "fullname": "NoteOS User",
            "username": "noteos",
            "hostname": "noteos",
            "autologin": True,
        }
        self._load_state()
        self.user_password = ""
        self.app_checkboxes = {}

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setGeometry(0, 0, 1280, 800)
        self.setFixedSize(1280, 800)

        self._apply_stylesheet()
        self._build_ui()
        self._retranslate_ui()
        self._go_to_step(self.state.get("step", 0), save=False)

        if not getattr(self.args, "test_screenshots", False):
            self.showFullScreen()
        else:
            self.show()

        QApplication.instance().installEventFilter(self)

        # Anti-standby timer: prevents display powerdown, blanking, or standby during setup
        self.anti_sleep_timer = QTimer(self)
        self.anti_sleep_timer.timeout.connect(self._prevent_screen_sleep)
        self.anti_sleep_timer.start(30000)  # Every 30 seconds
        self._prevent_screen_sleep()

        # Single-shot timer to guarantee display wake-up and repaint after the event loop starts
        QTimer.singleShot(10, self._force_initial_display)

    def _force_initial_display(self):
        self.repaint()
        QApplication.flush()
        if not getattr(self.args, "dry_run", False) and not getattr(self.args, "test_screenshots", False):
            try:
                import glob
                for fb in glob.glob("/sys/class/graphics/fb*/blank"):
                    try:
                        with open(fb, "w") as f:
                            f.write("0\n")
                    except Exception:
                        pass
                for b in glob.glob("/sys/class/backlight/*/max_brightness"):
                    try:
                        with open(b) as f_max:
                            max_b = int(f_max.read().strip())
                        b_dir = os.path.dirname(b)
                        # NOTE: max level = 100% PWM duty, which blacks out the N8000 panel
                        with open(os.path.join(b_dir, "brightness"), "w") as f_br:
                            f_br.write(str(max(1, max_b // 2)) + "\n")
                    except Exception:
                        pass
                subprocess.run(["xset", "dpms", "force", "on"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["xset", "s", "reset"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["xset", "s", "off", "-dpms"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["plymouth", "quit", "--retain-splash"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    def _prevent_screen_sleep(self):
        if not getattr(self.args, "dry_run", False):
            try:
                subprocess.run(["xset", "dpms", "force", "on"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["xset", "s", "reset"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["xset", "s", "off", "-dpms"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    def t(self, key, **kwargs):
        lang = self.state.get("lang", "en")
        txt = TR.get(lang, TR["en"]).get(key, key)
        return txt.format(**kwargs) if kwargs else txt

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                if isinstance(saved, dict):
                    for k in self.state:
                        if k in saved and k not in ("password", "wifi_password"):
                            self.state[k] = saved[k]
            except Exception:
                pass

    def _save_state(self):
        try:
            os.makedirs(self.state_dir, exist_ok=True)
            safe_copy = {k: v for k, v in self.state.items() if "pass" not in k.lower()}
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(safe_copy, f, indent=2)
        except Exception:
            pass

    def _apply_stylesheet(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget#CentralWidget {{
                background-color: #1b2228;
                color: #eff0f1;
                font-family: "DejaVu Sans", "Noto Sans", sans-serif;
                font-size: 15px;
            }}
            QWidget {{
                color: #eff0f1;
            }}
            QLabel {{
                color: #eff0f1;
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
                color: #eff0f1;
            }}
            QFrame#HeaderBar {{
                background-color: #161c21;
                border-bottom: 1px solid #283138;
            }}
            QLabel#LogoBadge {{
                background-color: #1d99f3;
                color: #ffffff;
                font-size: 20px;
                font-weight: bold;
                border-radius: 6px;
                min-width: 36px;
                max-width: 36px;
                min-height: 36px;
                max-height: 36px;
            }}
            QLabel#HeaderTitle {{
                font-size: 16px;
                font-weight: 600;
                color: #eff0f1;
            }}
            QLabel#HeaderStep {{
                font-size: 13px;
                color: #bdc3c7;
                margin-top: 1px;
            }}
            QPushButton#HeaderKbdBtn {{
                background-color: #20272d;
                color: #eff0f1;
                border: 1px solid #48535d;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 14px;
                font-weight: 500;
                min-height: 36px;
            }}
            QPushButton#HeaderKbdBtn:hover, QPushButton#HeaderKbdBtn:pressed {{
                background-color: #2c353e;
                border-color: #3daee9;
            }}
            QLabel#ScreenTitle, QLabel#SectionTitle {{
                font-size: 24px;
                font-weight: bold;
                color: #eff0f1;
                margin-bottom: 2px;
            }}
            QLabel#ScreenSubtitle, QLabel#SectionSubtitle {{
                font-size: 15px;
                color: #a0aab4;
                margin-bottom: 12px;
            }}
            QLabel#ColumnHeader {{
                font-size: 17px;
                font-weight: bold;
                color: #eff0f1;
                margin-bottom: 8px;
            }}
            QFrame.Card {{
                background-color: #20272d;
                border: 1px solid #343d46;
                border-radius: 6px;
                padding: 12px;
            }}
            QRadioButton {{
                font-size: 15px;
                color: #eff0f1;
                spacing: 12px;
                min-height: 38px;
                padding: 2px 4px;
                background: transparent;
            }}
            QRadioButton::indicator {{
                width: 22px;
                height: 22px;
                border-radius: 11px;
                border: 2px solid #56606a;
                background-color: #20272d;
            }}
            QRadioButton::indicator:hover {{
                border-color: #3daee9;
            }}
            QRadioButton::indicator:checked {{
                border: 2px solid #3daee9;
                background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 #3daee9, stop:0.48 #3daee9, stop:0.52 #20272d, stop:1 #20272d);
            }}
            QCheckBox {{
                font-size: 15px;
                color: #eff0f1;
                spacing: 12px;
                min-height: 38px;
                padding: 2px 4px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 3px;
                border: 2px solid #56606a;
                background-color: #20272d;
            }}
            QCheckBox::indicator:hover {{
                border-color: #3daee9;
            }}
            QCheckBox::indicator:checked {{
                border: 2px solid #3daee9;
                background-color: #3daee9;
                image: url({CHECK_PNG});
            }}
            QComboBox {{
                background-color: #20272d;
                color: #eff0f1;
                border: 1px solid #48535d;
                border-radius: 4px;
                padding: 8px 14px;
                font-size: 15px;
                min-height: 42px;
            }}
            QComboBox:focus, QComboBox:hover {{
                border-color: #3daee9;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 32px;
                border-left: none;
            }}
            QComboBox::down-arrow {{
                image: url({DOWN_ARROW_PNG});
                width: 14px;
                height: 14px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #20272d;
                color: #eff0f1;
                selection-background-color: #1d99f3;
                selection-color: #ffffff;
                border: 1px solid #48535d;
            }}
            QLineEdit {{
                background-color: #20272d;
                color: #eff0f1;
                border: 1px solid #48535d;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 16px;
                min-height: 44px;
            }}
            QLineEdit:focus {{
                border-color: #3daee9;
            }}
            QListWidget {{
                background-color: #20272d;
                color: #eff0f1;
                border: 1px solid #343d46;
                border-radius: 6px;
                font-size: 15px;
            }}
            QListWidget::item {{
                min-height: 44px;
                padding: 8px;
                border-bottom: 1px solid #283138;
            }}
            QListWidget::item:selected {{
                background-color: #1d99f3;
                color: #ffffff;
            }}
            QFrame#BottomBar {{
                background-color: #161c21;
                border-top: 1px solid #283138;
            }}
            QPushButton {{
                background-color: #20272d;
                color: #eff0f1;
                border: 1px solid #48535d;
                border-radius: 4px;
                padding: 8px 18px;
                font-size: 15px;
                font-weight: bold;
                min-height: 42px;
            }}
            QPushButton:hover, QPushButton:pressed {{
                background-color: #2c353e;
                border-color: #3daee9;
            }}
            QPushButton:disabled {{
                background-color: #182025;
                border: 1px solid #2a323a;
                color: #4e5862;
            }}
            QPushButton#PrimaryBtn {{
                background-color: #1b7e64;
                border: 1px solid #1b7e64;
                color: #ffffff;
            }}
            QPushButton#PrimaryBtn:hover {{
                background-color: #239474;
                border-color: #239474;
            }}
            QPushButton#PrimaryBtn:pressed {{
                background-color: #156550;
                border-color: #156550;
            }}
            QPushButton#PrimaryBtn:disabled {{
                background-color: #182025;
                border: 1px solid #2a323a;
                color: #4e5862;
            }}
            QProgressBar {{
                background-color: #20272d;
                border: 1px solid #343d46;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
            }}
            QProgressBar::chunk {{
                background-color: #1b7e64;
                border-radius: 3px;
            }}
            QScrollBar:vertical {{
                background: #1b2228;
                width: 22px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: #3a444e;
                min-height: 36px;
                border-radius: 4px;
            }}
        """)

    def eventFilter(self, obj, event):
        if isinstance(obj, QLineEdit) and event.type() == QEvent.FocusIn:
            self.touch_kbd.target_input = obj
            if self.state.get("vkbd_enabled", True):
                self.touch_kbd.show()
        elif event.type() == QEvent.MouseButtonPress:
            if isinstance(obj, (QAbstractButton, QListWidget, QComboBox)) or \
                    isinstance(getattr(obj, 'parent', lambda: None)(), (QListWidget, QComboBox)):
                if not self.touch_kbd.isAncestorOf(obj) and obj != self.btn_toggle_kbd:
                    self.touch_kbd.hide()
        return super().eventFilter(obj, event)

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)
        main_vbox = QVBoxLayout(central)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(0)

        # Top Header Bar Frame
        header_frame = QFrame()
        header_frame.setObjectName("HeaderBar")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(24, 10, 24, 10)
        header_layout.setSpacing(0)

        # Left block (Logo badge 'N')
        left_box = QWidget()
        left_box.setFixedWidth(200)
        left_layout = QHBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        self.lbl_logo = QLabel("N")
        self.lbl_logo.setObjectName("LogoBadge")
        self.lbl_logo.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.lbl_logo, 0, Qt.AlignVCenter | Qt.AlignLeft)
        left_layout.addStretch(1)
        header_layout.addWidget(left_box)

        # Center block (Title, Step, Pagination dots)
        center_box = QWidget()
        center_layout = QVBoxLayout(center_box)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(2)
        center_layout.setAlignment(Qt.AlignCenter)

        self.lbl_app_title = QLabel()
        self.lbl_app_title.setObjectName("HeaderTitle")
        self.lbl_app_title.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(self.lbl_app_title)

        self.lbl_step_indicator = QLabel()
        self.lbl_step_indicator.setObjectName("HeaderStep")
        self.lbl_step_indicator.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(self.lbl_step_indicator)

        self.dots_widget = PaginationDotsWidget(8)
        center_layout.addWidget(self.dots_widget, 0, Qt.AlignCenter)

        header_layout.addWidget(center_box, 1)

        # Right block (Keyboard button)
        right_box = QWidget()
        right_box.setFixedWidth(200)
        right_layout = QHBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addStretch(1)
        self.btn_toggle_kbd = QPushButton()
        self.btn_toggle_kbd.setObjectName("HeaderKbdBtn")
        self.btn_toggle_kbd.setFocusPolicy(Qt.NoFocus)
        self.btn_toggle_kbd.clicked.connect(self._toggle_touch_kbd)
        right_layout.addWidget(self.btn_toggle_kbd, 0, Qt.AlignVCenter | Qt.AlignRight)
        header_layout.addWidget(right_box)

        main_vbox.addWidget(header_frame)

        # Stacked 8 Screens
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_screen1_lang())
        self.stack.addWidget(self._build_screen2_wifi())
        self.stack.addWidget(self._build_screen3_datetime())
        self.stack.addWidget(self._build_screen4_desktop())
        self.stack.addWidget(self._build_screen5_apps())
        self.stack.addWidget(self._build_screen6_user())
        self.stack.addWidget(self._build_screen7_autologin())
        self.stack.addWidget(self._build_screen8_install())
        main_vbox.addWidget(self.stack, 1)

        # Integrated Touch Keyboard
        self.touch_kbd = TouchKeyboardWidget(self)
        self.touch_kbd.hide()
        main_vbox.addWidget(self.touch_kbd)

        # Bottom Navigation Bar
        bottom_frame = QFrame()
        bottom_frame.setObjectName("BottomBar")
        nav_bar = QHBoxLayout(bottom_frame)
        nav_bar.setContentsMargins(24, 12, 24, 12)
        nav_bar.setSpacing(14)

        self.btn_back = QPushButton()
        self.btn_back.setFixedSize(130, 42)
        self.btn_back.clicked.connect(self._on_back)

        self.lbl_nav_error = QLabel("")
        self.lbl_nav_error.setStyleSheet("color: #da4453; font-weight: bold; font-size: 15px;")
        self.lbl_nav_error.setWordWrap(True)

        self.btn_next = QPushButton()
        self.btn_next.setObjectName("PrimaryBtn")
        self.btn_next.setFixedSize(130, 42)
        self.btn_next.clicked.connect(self._on_next)

        nav_bar.addWidget(self.btn_back)
        nav_bar.addSpacing(10)
        nav_bar.addWidget(self.lbl_nav_error, 1)
        nav_bar.addSpacing(10)
        nav_bar.addWidget(self.btn_next)
        main_vbox.addWidget(bottom_frame)

    def _toggle_touch_kbd(self):
        if self.touch_kbd.isVisible():
            self.touch_kbd.hide()
        else:
            self.touch_kbd.show()

    # --------------------------------------------------------------------------
    # SCHERMATA 1: LINGUA E TASTIERA
    # --------------------------------------------------------------------------
    def _build_screen1_lang(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(50, 30, 50, 10)
        v.setSpacing(8)

        self.s1_title = QLabel()
        self.s1_title.setObjectName("ScreenTitle")
        v.addWidget(self.s1_title)

        self.s1_desc = QLabel()
        self.s1_desc.setObjectName("ScreenSubtitle")
        v.addWidget(self.s1_desc)

        cols = QHBoxLayout()
        cols.setSpacing(60)

        # Colonna Sinistra: Selezione Lingua
        col_left = QVBoxLayout()
        col_left.setSpacing(10)
        col_left.setAlignment(Qt.AlignTop)

        self.s1_lang_hdr = QLabel()
        self.s1_lang_hdr.setObjectName("ColumnHeader")
        col_left.addWidget(self.s1_lang_hdr)

        self.lang_group = QButtonGroup(self)
        self.rb_lang_it = QRadioButton("🇮🇹  Italiano (it_IT.UTF-8)")
        self.rb_lang_en = QRadioButton("English (US)")
        self.rb_lang_fr = QRadioButton("Français (France)")
        self.rb_lang_de = QRadioButton("Deutsch (Deutschland)")
        self.rb_lang_es = QRadioButton("Español (España)")

        for idx, rb in enumerate([self.rb_lang_it, self.rb_lang_en, self.rb_lang_fr, self.rb_lang_de, self.rb_lang_es]):
            self.lang_group.addButton(rb, idx)
            col_left.addWidget(rb)

        cur_lang = self.state.get("lang", "en")
        if cur_lang == "it":
            self.rb_lang_it.setChecked(True)
        elif cur_lang == "fr":
            self.rb_lang_fr.setChecked(True)
        elif cur_lang == "de":
            self.rb_lang_de.setChecked(True)
        elif cur_lang == "es":
            self.rb_lang_es.setChecked(True)
        else:
            self.rb_lang_en.setChecked(True)

        self.rb_lang_it.toggled.connect(self._on_lang_changed)
        self.rb_lang_en.toggled.connect(self._on_lang_changed)
        self.rb_lang_fr.toggled.connect(self._on_lang_changed)
        self.rb_lang_de.toggled.connect(self._on_lang_changed)
        self.rb_lang_es.toggled.connect(self._on_lang_changed)

        col_left.addStretch(1)
        cols.addLayout(col_left, 1)

        # Colonna Destra: Layout Tastiera e Tastiera Virtuale
        col_right = QVBoxLayout()
        col_right.setSpacing(16)
        col_right.setAlignment(Qt.AlignTop)

        self.s1_kb_hdr = QLabel()
        self.s1_kb_hdr.setObjectName("ColumnHeader")
        col_right.addWidget(self.s1_kb_hdr)

        self.cmb_kb = QComboBox()
        self.kb_items = [
            ("it", "⌨  Italiano (IT)"),
            ("us", "⌨  English (US)"),
            ("de", "⌨  Deutsch (DE)"),
            ("fr", "⌨  Français (FR)"),
            ("es", "⌨  Español (ES)"),
        ]
        for code, label in self.kb_items:
            self.cmb_kb.addItem(label, code)
        idx = next((i for i, (c, _) in enumerate(self.kb_items) if c == self.state.get("kb_layout", "it")), 0)
        self.cmb_kb.setCurrentIndex(idx)
        self.cmb_kb.currentIndexChanged.connect(self._on_kb_changed)
        col_right.addWidget(self.cmb_kb)

        self.chk_vkbd = QCheckBox()
        self.chk_vkbd.setChecked(self.state.get("vkbd_enabled", True))
        self.chk_vkbd.toggled.connect(lambda c: self.state.update({"vkbd_enabled": c}))
        col_right.addWidget(self.chk_vkbd)

        col_right.addStretch(1)
        cols.addLayout(col_right, 1)

        v.addLayout(cols, 1)
        return w

    def _on_lang_changed(self):
        if self.rb_lang_it.isChecked():
            self.state["lang"] = "it"
            self.state["locale"] = "it_IT.UTF-8"
        elif self.rb_lang_en.isChecked():
            self.state["lang"] = "en"
            self.state["locale"] = "en_US.UTF-8"
        elif self.rb_lang_fr.isChecked():
            self.state["lang"] = "en"
            self.state["locale"] = "fr_FR.UTF-8"
        elif self.rb_lang_de.isChecked():
            self.state["lang"] = "en"
            self.state["locale"] = "de_DE.UTF-8"
        elif self.rb_lang_es.isChecked():
            self.state["lang"] = "it"
            self.state["locale"] = "es_ES.UTF-8"
        self._retranslate_ui()
        self._save_state()

    def _on_kb_changed(self):
        code = self.cmb_kb.currentData()
        if code:
            self.state["kb_layout"] = code
            if not self.args.dry_run:
                subprocess.run(["setxkbmap", code], check=False)
            self._save_state()

    # --------------------------------------------------------------------------
    # SCHERMATA 2: RETE WI-FI
    # --------------------------------------------------------------------------
    def _build_screen2_wifi(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(10)

        self.s2_title = QLabel()
        self.s2_title.setObjectName("SectionTitle")
        self.s2_desc = QLabel()
        self.s2_desc.setWordWrap(True)
        v.addWidget(self.s2_title)
        v.addWidget(self.s2_desc)

        top_row = QHBoxLayout()
        self.btn_scan_wifi = QPushButton()
        self.btn_scan_wifi.clicked.connect(self._scan_wifi)
        self.chk_hidden_wifi = QCheckBox()
        self.chk_hidden_wifi.toggled.connect(lambda c: self.inp_hidden_ssid.setVisible(c))
        top_row.addWidget(self.btn_scan_wifi)
        top_row.addWidget(self.chk_hidden_wifi)
        top_row.addStretch(1)
        v.addLayout(top_row)

        self.wifi_list = QListWidget()
        self.wifi_list.setMaximumHeight(180)
        self.wifi_list.itemClicked.connect(self._on_wifi_selected)
        self.wifi_list.currentItemChanged.connect(lambda cur, prev: self._on_wifi_selected(cur) if cur else None)
        v.addWidget(self.wifi_list)

        self.inp_hidden_ssid = QLineEdit()
        self.inp_hidden_ssid.setVisible(False)
        v.addWidget(self.inp_hidden_ssid)

        pw_row = QHBoxLayout()
        self.inp_wifi_pass = QLineEdit()
        self.inp_wifi_pass.setEchoMode(QLineEdit.Password)
        self.chk_wifi_show_pw = QCheckBox()
        self.chk_wifi_show_pw.toggled.connect(
            lambda c: self.inp_wifi_pass.setEchoMode(QLineEdit.Normal if c else QLineEdit.Password)
        )
        self.btn_connect_wifi = QPushButton()
        self.btn_connect_wifi.setObjectName("PrimaryBtn")
        self.btn_connect_wifi.clicked.connect(self._connect_wifi_and_check)
        pw_row.addWidget(self.inp_wifi_pass, 1)
        pw_row.addWidget(self.chk_wifi_show_pw)
        pw_row.addWidget(self.btn_connect_wifi)
        v.addLayout(pw_row)

        self.lbl_wifi_status = QLabel()
        self.lbl_wifi_status.setWordWrap(True)
        self.lbl_wifi_status.setStyleSheet("font-size: 17px; font-weight: bold; padding: 8px; background: #161b22; color: #eff0f1; border-radius: 8px;")
        v.addWidget(self.lbl_wifi_status)
        v.addStretch(1)
        return w

    def _scan_wifi(self):
        if hasattr(self, "scan_worker") and self.scan_worker and self.scan_worker.isRunning():
            return
        self.btn_scan_wifi.setEnabled(False)
        self.btn_scan_wifi.setText("⏳ " + self.t("s2_scan_btn"))
        if self.wifi_list.count() == 0:
            self.wifi_list.clear()
            item = QListWidgetItem("⏳ Scansione reti Wi-Fi in corso...")
            item.setFlags(Qt.NoItemFlags)
            self.wifi_list.addItem(item)
        self.scan_worker = WifiScanWorker(dry_run=self.args.dry_run, state_dir=self.state_dir)
        self.scan_worker.finished_sig.connect(self._on_wifi_scan_finished)
        self.scan_worker.start()

    def _on_wifi_scan_finished(self, nets):
        self.btn_scan_wifi.setEnabled(True)
        self.btn_scan_wifi.setText(self.t("s2_scan_btn"))
        self.wifi_list.clear()
        if not nets:
            item = QListWidgetItem("⚠️ Nessuna rete Wi-Fi trovata. Clicca Scansiona per riprovare.")
            item.setFlags(Qt.NoItemFlags)
            self.wifi_list.addItem(item)
            return
        selected_idx = 0
        current_ssid = self.state.get("wifi_ssid")
        for i, (ssid, sig, sec, in_use) in enumerate(nets):
            mark = "✅ [CONNESSA] " if in_use else ""
            item = QListWidgetItem(f"📶  {mark}{ssid}   —   {sig}%   [{sec}]")
            item.setData(Qt.UserRole, ssid)
            self.wifi_list.addItem(item)
            if current_ssid and ssid == current_ssid:
                selected_idx = i
            elif in_use:
                selected_idx = i
        self.wifi_list.setCurrentRow(selected_idx)
        self.state["wifi_ssid"] = self.wifi_list.item(selected_idx).data(Qt.UserRole)

    def _on_wifi_selected(self, item):
        data = item.data(Qt.UserRole)
        if data:
            self.state["wifi_ssid"] = data

    def _check_internet(self, wait_dhcp=False):
        """
        Verifica la connettività Internet in modo rapido e resiliente:
        1. Se wait_dhcp=True, attende l'assegnazione IP via DHCP da parte del router (fino a 8s).
           Altrimenti esegue solo un controllo immediato senza bloccare.
        2. Esegue test HTTP via IPv4 (-4) su deb.debian.org e fallback su endpoint leggeri.
        3. Verifica ping verso DNS pubblico (1.1.1.1) in caso di latenza DNS.
        Ritorna: (ok: bool, info: str, is_local_only: bool)
        """
        if getattr(self.args, "simulate_no_net", False):
            return False, "Nessuna risposta da deb.debian.org (rete assente simulata)", False
        if self.args.dry_run:
            return True, self.state.get("wifi_ssid") or "TIM-33744972", False

        # Verifica preliminare rapida dello stato di wlan0 per evitare attese se disconnesso
        try:
            dev_status = subprocess.run(["nmcli", "-t", "-f", "DEVICE,STATE", "dev"],
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=2).stdout
            wlan_connected = False
            for line in dev_status.splitlines():
                if line.startswith("wlan0:connected"):
                    wlan_connected = True
                    break
            if not wlan_connected and not wait_dhcp:
                return False, "Non connesso alla rete Wi-Fi", False
        except Exception:
            pass

        # 1. Attesa assegnazione IP / route default via DHCP
        ip_assigned = None
        attempts = 8 if wait_dhcp else 1
        for _ in range(attempts):
            try:
                addr_out = subprocess.run(["ip", "-4", "addr", "show", "wlan0"],
                                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=2).stdout
                for line in addr_out.splitlines():
                    if "inet " in line:
                        ip_assigned = line.strip().split()[1].split("/")[0]
                        break
                route_out = subprocess.run(["ip", "route", "show", "default"],
                                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=2).stdout
                if "default via" in route_out and ip_assigned:
                    break
            except Exception:
                pass
            if wait_dhcp:
                time.sleep(1)

        # Assicura la presenza di server DNS validi prima dei test
        ensure_dns_servers()

        # 2. Test HTTP su repository Debian ed endpoint di fallback
        endpoints = [
            "http://deb.debian.org/debian/dists/bookworm/Release",
            "http://connectivity-check.ubuntu.com",
            "http://www.google.com/generate_204",
        ]
        for ep in endpoints:
            try:
                rc = subprocess.run(
                    ["curl", "-4", "-fsSI", "--connect-timeout", "3", "--max-time", "5", ep],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=6
                ).returncode
                if rc == 0:
                    net_label = self.state.get("wifi_ssid") or "Wi-Fi"
                    if ip_assigned:
                        net_label += f" ({ip_assigned})"
                    return True, net_label, False
            except Exception:
                continue

        # Se il primo tentativo curl fallisce, rinforza /etc/resolv.conf e riprova
        ensure_dns_servers()
        for ep in endpoints:
            try:
                rc = subprocess.run(
                    ["curl", "-4", "-fsSI", "--connect-timeout", "4", "--max-time", "6", ep],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=7
                ).returncode
                if rc == 0:
                    net_label = self.state.get("wifi_ssid") or "Wi-Fi"
                    if ip_assigned:
                        net_label += f" ({ip_assigned})"
                    return True, net_label, False
            except Exception:
                continue

        # 3. Test ping IP pubblico per diagnosticare se la rete è attiva ma il DNS è bloccato
        ping_ok = False
        try:
            ping_rc = subprocess.run(["ping", "-4", "-c", "1", "-W", "2", "1.1.1.1"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3).returncode
            ping_ok = (ping_rc == 0)
        except Exception:
            pass

        if ping_ok:
            # IP raggiungibile ma risoluzione DNS fallita: non permettere di proseguire al wizard
            return False, "Wi-Fi connesso ma impossibile risolvere i domini (DNS non raggiungibile)", False

        if ip_assigned:
            return False, f"Wi-Fi connesso con IP {ip_assigned}, ma accesso web a deb.debian.org non pronto", True

        return False, "Nessun indirizzo IP ricevuto dal router (timeout DHCP o associazione non riuscita)", False

    def _wifi_log(self, msg):
        """Append a diagnostic line (never a password) to /var/lib/noteos/wifi.log."""
        try:
            with open(os.path.join(self.state_dir, "wifi.log"), "a", encoding="utf-8") as f:
                f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} {msg}\n")
        except Exception:
            pass

    def _start_net_check(self):
        """Run _check_internet off the GUI thread (inline in --dry-run, where it is instant)."""
        if self.args.dry_run:
            self._on_net_check_done(self._check_internet(wait_dhcp=False))
            return
        if getattr(self, "net_worker", None) and self.net_worker.isRunning():
            return
        self.net_worker = CallableWorker(lambda: self._check_internet(wait_dhcp=False))
        self.net_worker.done_sig.connect(self._on_net_check_done)
        self.net_worker.start()

    def _on_net_check_done(self, res):
        # Ignore stale results: user left the Wi-Fi screen or a connection attempt is running
        if self.stack.currentIndex() != 1:
            return
        if getattr(self, "wifi_worker", None) and self.wifi_worker.isRunning():
            return
        if isinstance(res, Exception):
            return
        ok, info, is_local_only = res
        if ok and not self.args.dry_run:
            self.state["net_connected"] = True
            self.state["net_name"] = info
            self._update_wifi_banner()
        elif is_local_only:
            self.lbl_wifi_status.setText(f"⚠️ {info}.\nPuoi proseguire al passo successivo se la connessione è attiva.")
            self.lbl_wifi_status.setStyleSheet("color: #d29922; font-size: 15px; font-weight: bold; padding: 10px; background: #161b22; border-radius: 8px;")
            self.state["net_connected"] = True
            self.state["net_name"] = self.state.get("wifi_ssid") or "Wi-Fi"
            self.btn_next.setEnabled(True)
        else:
            self._update_wifi_banner(err_msg=None)

    def _connect_wifi_and_check(self):
        ssid = self.inp_hidden_ssid.text().strip() if self.chk_hidden_wifi.isChecked() else self.state.get("wifi_ssid", "")
        pw = self.inp_wifi_pass.text()
        hidden = self.chk_hidden_wifi.isChecked()

        if not ssid:
            self._update_wifi_banner(err_msg="Seleziona una rete Wi-Fi dall'elenco prima di connetterti")
            return
        if getattr(self, "wifi_worker", None) and self.wifi_worker.isRunning():
            return

        self.touch_kbd.hide()
        self.lbl_wifi_status.setText(f"⏳ Connessione a '{ssid}' in corso...")
        self.lbl_wifi_status.setStyleSheet("color: #58a6ff; font-size: 17px; font-weight: bold; padding: 10px; background: #161b22; border-radius: 8px;")
        self.btn_connect_wifi.setEnabled(False)

        if self.args.dry_run:
            # Instant in simulation: keep it synchronous (used by --test-screenshots)
            self._on_wifi_connect_done(ssid, self._wifi_connect_job(ssid, pw, hidden))
            return

        # nmcli/DHCP/curl can take up to ~60 s: never run them on the GUI thread
        self.wifi_worker = CallableWorker(lambda: self._wifi_connect_job(ssid, pw, hidden))
        self.wifi_worker.done_sig.connect(lambda res: self._on_wifi_connect_done(ssid, res))
        self.wifi_worker.start()

    def _wifi_connect_job(self, ssid, pw, hidden):
        """Worker-thread body. Must not touch any widget. Returns (ok, info, is_local_only, err_detail)."""
        err_detail = None

        if not self.args.dry_run:
            # Unlock European Wi-Fi channels (1-13)
            subprocess.run(["iw", "reg", "set", "IT"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Remove prior profiles with the same SSID to avoid conflicts or secret-agent errors
            subprocess.run(["nmcli", "connection", "delete", "id", ssid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["nmcli", "connection", "delete", ssid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Stage 1: Create persistent connection profile with PMF disabled (wifi-sec.pmf 1)
            # This prevents status_code=16 rejection from Broadcom BCM4334 chip on modern routers
            add_cmd = [
                "nmcli", "connection", "add", "type", "wifi",
                "con-name", ssid, "ssid", ssid,
                "ifname", "wlan0",
                "connection.autoconnect", "yes",
                "ipv4.dns", "1.1.1.1 8.8.8.8",
                "ipv4.ignore-auto-dns", "no",
            ]
            if pw:
                add_cmd += [
                    "wifi-sec.key-mgmt", "wpa-psk",
                    "wifi-sec.psk", pw,
                    "wifi-sec.pmf", "1",  # 1 = disabled
                ]
            if hidden:
                add_cmd += ["802-11-wireless.hidden", "yes"]

            add_res = subprocess.run(add_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if add_res.returncode == 0:
                ensure_dns_servers()
                up_res = subprocess.run(["nmcli", "--wait", "20", "connection", "up", ssid],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if up_res.returncode != 0:
                    err_detail = up_res.stderr.strip() or up_res.stdout.strip()
                    self._wifi_log(f"up failed (stage 1): {err_detail}")
                    # Stage 2: Fallback to pure 2.4 GHz band (bg) for routers with dual-band steering issues
                    if pw:
                        subprocess.run(["nmcli", "connection", "modify", ssid, "802-11-wireless.band", "bg"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        up_res2 = subprocess.run(["nmcli", "--wait", "20", "connection", "up", ssid],
                                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        if up_res2.returncode == 0:
                            err_detail = None
                        else:
                            err_detail = up_res2.stderr.strip() or err_detail
                            self._wifi_log(f"up failed (stage 2, 2.4 GHz): {err_detail}")
            else:
                err_detail = add_res.stderr.strip() or "Failed to create connection profile"
                self._wifi_log(f"add failed: {err_detail}")

        ok, info, is_local_only = self._check_internet(wait_dhcp=True)
        return ok, info, is_local_only, err_detail

    def _on_wifi_connect_done(self, ssid, res):
        self.btn_connect_wifi.setEnabled(True)
        if isinstance(res, Exception):
            res = (False, str(res), False, str(res))
        ok, info, is_local_only, err_detail = res

        self.state["net_connected"] = ok
        self.state["net_name"] = info if ok else ""

        if ok:
            self._update_wifi_banner(err_msg=None)
        elif is_local_only:
            # Wi-Fi connesso con IP locale: avvisa ma abilita il proseguimento per non bloccare l'utente
            self.lbl_wifi_status.setText(f"⚠️ {info}.\nPuoi proseguire al passo successivo se la connessione è attiva.")
            self.lbl_wifi_status.setStyleSheet("color: #d29922; font-size: 15px; font-weight: bold; padding: 10px; background: #161b22; border-radius: 8px;")
            self.state["net_connected"] = True
            self.state["net_name"] = ssid
            self.btn_next.setEnabled(True)
        else:
            final_err = err_detail if err_detail else info
            self._update_wifi_banner(err_msg=final_err)

        self._save_state()

    def _update_wifi_banner(self, err_msg=None):
        if self.state.get("net_connected"):
            self.lbl_wifi_status.setText(self.t("s2_status_ok", net=self.state.get("net_name", "Wi-Fi")))
            self.lbl_wifi_status.setStyleSheet("color: #3fb950; font-size: 17px; font-weight: bold; padding: 10px; background: #161b22; border-radius: 8px;")
            if self.stack.currentIndex() == 1:
                self.btn_next.setEnabled(True)
        elif err_msg:
            self.lbl_wifi_status.setText(self.t("s2_status_err", err=err_msg))
            self.lbl_wifi_status.setStyleSheet("color: #ff7b72; font-size: 17px; font-weight: bold; padding: 10px; background: #161b22; border-radius: 8px;")
            if self.stack.currentIndex() == 1:
                self.btn_next.setEnabled(False)
        else:
            self.lbl_wifi_status.setText(self.t("s2_status_wait"))
            self.lbl_wifi_status.setStyleSheet("color: #d29922; font-size: 17px; font-weight: bold; padding: 10px; background: #161b22; border-radius: 8px;")
            if self.stack.currentIndex() == 1:
                self.btn_next.setEnabled(False)

    # --------------------------------------------------------------------------
    # SCHERMATA 3: DATA, ORA E FUSO ORARIO
    # --------------------------------------------------------------------------
    def _build_screen3_datetime(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(14)

        self.s3_title = QLabel()
        self.s3_title.setObjectName("SectionTitle")
        v.addWidget(self.s3_title)

        card = QFrame()
        card.setProperty("class", "Card")
        vc = QVBoxLayout(card)
        vc.setSpacing(12)

        self.chk_ntp = QCheckBox()
        self.chk_ntp.setChecked(self.state.get("ntp_enabled", True))
        self.chk_ntp.toggled.connect(lambda c: self.state.update({"ntp_enabled": c}))
        vc.addWidget(self.chk_ntp)

        self.s3_tz_lbl = QLabel()
        self.cmb_tz = QComboBox()
        tz_list = [
            "Europe/Rome", "UTC", "Europe/London", "Europe/Berlin",
            "Europe/Paris", "Europe/Madrid", "Europe/Zurich",
            "America/New_York", "America/Chicago", "America/Los_Angeles",
            "Asia/Tokyo", "Asia/Shanghai", "Australia/Sydney",
        ]
        for tz in tz_list:
            self.cmb_tz.addItem(tz)
        if self.state["timezone"] in tz_list:
            self.cmb_tz.setCurrentText(self.state["timezone"])
        self.cmb_tz.currentTextChanged.connect(lambda t: self.state.update({"timezone": t}))
        vc.addWidget(self.s3_tz_lbl)
        vc.addWidget(self.cmb_tz)

        self.s3_man_lbl = QLabel()
        vc.addWidget(self.s3_man_lbl)

        now = datetime.datetime.now()
        dt_row = QHBoxLayout()
        self.inp_date = QLineEdit(now.strftime("%Y-%m-%d"))
        self.inp_time = QLineEdit(now.strftime("%H:%M"))
        self.btn_apply_dt = QPushButton()
        self.btn_apply_dt.clicked.connect(self._apply_datetime)
        dt_row.addWidget(QLabel("Data (YYYY-MM-DD):"))
        dt_row.addWidget(self.inp_date)
        dt_row.addWidget(QLabel("Ora (HH:MM):"))
        dt_row.addWidget(self.inp_time)
        dt_row.addWidget(self.btn_apply_dt)
        vc.addLayout(dt_row)

        v.addWidget(card)
        v.addStretch(1)
        return w

    def _apply_datetime(self):
        if not self.args.dry_run:
            tz = self.cmb_tz.currentText()
            subprocess.run(["timedatectl", "set-timezone", tz], check=False)
            if self.chk_ntp.isChecked():
                subprocess.run(["timedatectl", "set-ntp", "true"], check=False)
            else:
                subprocess.run(["timedatectl", "set-ntp", "false"], check=False)
                dt_str = f"{self.inp_date.text().strip()} {self.inp_time.text().strip()}:00"
                subprocess.run(["date", "-s", dt_str], check=False)
        self._save_state()

    # --------------------------------------------------------------------------
    # SCHERMATA 4: SCELTA DEL DESKTOP (LXQT vs KDE PLASMA)
    # --------------------------------------------------------------------------
    def _build_screen4_desktop(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)

        self.s4_title = QLabel()
        self.s4_title.setObjectName("SectionTitle")
        self.s4_desc = QLabel()
        self.s4_desc.setWordWrap(True)
        v.addWidget(self.s4_title)
        v.addWidget(self.s4_desc)

        self.desk_group = QButtonGroup(self)
        self.rb_lxqt = QRadioButton()
        self.rb_kde = QRadioButton()
        self.desk_group.addButton(self.rb_lxqt)
        self.desk_group.addButton(self.rb_kde)

        if self.state.get("desktop") == "kde":
            self.rb_kde.setChecked(True)
        else:
            self.rb_lxqt.setChecked(True)

        self.rb_lxqt.toggled.connect(self._on_desktop_changed)

        card_sel = QFrame()
        card_sel.setProperty("class", "Card")
        vs = QVBoxLayout(card_sel)
        vs.addWidget(self.rb_lxqt)
        vs.addWidget(self.rb_kde)
        v.addWidget(card_sel)

        self.card_desk_info = QFrame()
        self.card_desk_info.setProperty("class", "Card")
        vi = QVBoxLayout(self.card_desk_info)
        self.lbl_desk_stats = QLabel()
        self.lbl_desk_stats.setStyleSheet("font-size: 18px; font-weight: bold; color: #58a6ff;")
        self.lbl_desk_warn = QLabel()
        self.lbl_desk_warn.setWordWrap(True)
        self.s4_base_hdr = QLabel()
        self.s4_base_hdr.setStyleSheet("font-weight: bold; color: #3fb950; margin-top: 6px;")
        self.lbl_desk_base = QLabel()
        self.lbl_desk_base.setWordWrap(True)
        vi.addWidget(self.lbl_desk_stats)
        vi.addWidget(self.lbl_desk_warn)
        vi.addWidget(self.s4_base_hdr)
        vi.addWidget(self.lbl_desk_base)
        v.addWidget(self.card_desk_info)
        v.addStretch(1)
        return w

    def _on_desktop_changed(self):
        self.state["desktop"] = "lxqt" if self.rb_lxqt.isChecked() else "kde"
        self._update_desktop_card()
        self._rebuild_apps_screen()
        self._save_state()

    def _update_desktop_card(self):
        desk = DESKTOPS[self.state.get("desktop", "lxqt")]
        lang = self.state.get("lang", "it")
        self.rb_lxqt.setText(DESKTOPS["lxqt"][f"name_{lang}"])
        self.rb_kde.setText(DESKTOPS["kde"][f"name_{lang}"])
        self.lbl_desk_stats.setText(self.t("s4_stats", ram=desk["ram_idle_mb"], dl=desk["download_mb"], inst=desk["installed_mb"]))
        self.lbl_desk_warn.setText(desk[f"warning_{lang}"])
        if desk["id"] == "kde":
            self.lbl_desk_warn.setStyleSheet("color: #f0883e; font-weight: bold; font-size: 16px;")
        else:
            self.lbl_desk_warn.setStyleSheet("color: #3fb950; font-weight: bold; font-size: 16px;")
        self.lbl_desk_base.setText(desk[f"base_summary_{lang}"])

    # --------------------------------------------------------------------------
    # SCHERMATA 5: SCELTA DEI 20 PROGRAMMI VERIFICATI
    # --------------------------------------------------------------------------
    def _build_screen5_apps(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(8)

        top = QHBoxLayout()
        self.s5_title = QLabel()
        self.s5_title.setObjectName("SectionTitle")
        self.btn_rec_apps = QPushButton()
        self.btn_rec_apps.clicked.connect(self._select_recommended_apps)
        self.btn_clear_apps = QPushButton()
        self.btn_clear_apps.clicked.connect(self._clear_all_apps)
        top.addWidget(self.s5_title)
        top.addStretch(1)
        top.addWidget(self.btn_rec_apps)
        top.addWidget(self.btn_clear_apps)
        v.addLayout(top)

        self.lbl_apps_summary = QLabel()
        self.lbl_apps_summary.setWordWrap(True)
        self.lbl_apps_summary.setStyleSheet("font-size: 15px; font-weight: bold; color: #3daee9; background: #20272d; border: 1px solid #343d46; padding: 6px 10px; border-radius: 6px;")
        v.addWidget(self.lbl_apps_summary)

        self.lbl_apps_ram_warn = QLabel()
        self.lbl_apps_ram_warn.setWordWrap(True)
        self.lbl_apps_ram_warn.setStyleSheet("color: #ff7b72; font-weight: bold; background: #2d1619; padding: 6px 10px; border-radius: 6px;")
        self.lbl_apps_ram_warn.hide()
        v.addWidget(self.lbl_apps_ram_warn)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.apps_scroll = scroll
        self.apps_scroll_content = QWidget()
        self.apps_vbox = QVBoxLayout(self.apps_scroll_content)
        self.apps_vbox.setSpacing(6)
        scroll.setWidget(self.apps_scroll_content)
        v.addWidget(scroll, 1)
        return w

    def _rebuild_apps_screen(self):
        while self.apps_vbox.count():
            item = self.apps_vbox.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        self.app_checkboxes.clear()

        desk_id = self.state.get("desktop", "lxqt")
        lang = self.state.get("lang", "it")
        installable_20, already_in_base, unavailable = resolve_apps_for_desktop(desk_id)

        # Raggruppa i 20 programmi per categoria
        categories = {}
        for idx, app in enumerate(installable_20, 1):
            cat = app[f"cat_{lang}"]
            categories.setdefault(cat, []).append((idx, app))

        selected_set = set(self.state.get("selected_apps", []))

        for cat_name, items in categories.items():
            cat_lbl = QLabel(f"📂  {cat_name}")
            cat_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #79c0ff; margin-top: 6px;")
            self.apps_vbox.addWidget(cat_lbl)

            grid_frame = QFrame()
            grid_frame.setProperty("class", "Card")
            grid = QVBoxLayout(grid_frame)
            grid.setSpacing(4)
            for pos, (num, app) in enumerate(items):
                title = app[f"name_{lang}"]
                chk = QCheckBox(f"[{num:02d}/20] {title}   (↓ {app['dl_mb']:.1f} MiB | 💾 {app['inst_mb']:.1f} MiB)")
                chk.setChecked(app["id"] in selected_set)
                chk.toggled.connect(self._on_app_Selection_changed)
                self.app_checkboxes[app["id"]] = (chk, app)
                grid.addWidget(chk)
            self.apps_vbox.addWidget(grid_frame)

        # Sezione: Già inclusi nella base del desktop scelto
        if already_in_base:
            in_base_lbl = QLabel(self.t("s5_in_base_hdr"))
            in_base_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #3fb950; margin-top: 8px;")
            self.apps_vbox.addWidget(in_base_lbl)
            for b_app in already_in_base:
                lbl = QLabel(f"  ✔  {b_app[f'name_{lang}']} — Già incluso nella base di {desk_id.upper()}")
                lbl.setStyleSheet("color: #8b949e; font-size: 15px;")
                self.apps_vbox.addWidget(lbl)

        # Sezione: Non disponibili su armhf (con motivo in una riga)
        unavail_lbl = QLabel(self.t("s5_unavail_hdr"))
        unavail_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #f0883e; margin-top: 8px;")
        self.apps_vbox.addWidget(unavail_lbl)
        for u_app in unavailable:
            reason = u_app[f"reason_{lang}"]
            lbl = QLabel(f"  ✖  {u_app[f'name_{lang}']}: {reason}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #8b949e; font-size: 15px;")
            self.apps_vbox.addWidget(lbl)

        self._update_apps_totals()

    def _on_app_Selection_changed(self):
        sel = [app_id for app_id, (chk, _) in self.app_checkboxes.items() if chk.isChecked()]
        self.state["selected_apps"] = sel
        self._update_apps_totals()
        self._save_state()

    def _select_recommended_apps(self):
        # Solo btop, VLC e il browser più leggero (firefox-esr)
        rec_ids = {"btop", "vlc", "firefox-esr"}
        for app_id, (chk, _) in self.app_checkboxes.items():
            chk.blockSignals(True)
            chk.setChecked(app_id in rec_ids)
            chk.blockSignals(False)
        self._on_app_Selection_changed()

    def _clear_all_apps(self):
        for _, (chk, _) in self.app_checkboxes.items():
            chk.blockSignals(True)
            chk.setChecked(False)
            chk.blockSignals(False)
        self._on_app_Selection_changed()

    def _update_apps_totals(self):
        desk = DESKTOPS[self.state.get("desktop", "lxqt")]
        sel_apps = [app for _, (chk, app) in self.app_checkboxes.items() if chk.isChecked()]
        dl_mb = sum(a["dl_mb"] for a in sel_apps)
        inst_mb = desk["installed_mb"] + sum(a["inst_mb"] for a in sel_apps)
        est_ram = desk["ram_idle_mb"] + max((a["ram_mb"] for a in sel_apps), default=0)

        try:
            st = os.statvfs("/")
            free_mb = (st.f_bavail * st.f_frsize) / (1024 * 1024)
        except Exception:
            free_mb = 12288.0

        self.lbl_apps_summary.setText(
            self.t("s5_summary", cnt=len(sel_apps), dl=dl_mb, tot=inst_mb, free=free_mb, ram=est_ram)
        )
        # Avviso se la selezione è eccessiva per 2 GB di RAM o >8 app pesanti
        heavy_cnt = sum(1 for a in sel_apps if a["ram_mb"] >= 140)
        if est_ram > 700 or heavy_cnt >= 4 or len(sel_apps) >= 10:
            self.lbl_apps_ram_warn.setText(self.t("s5_ram_warn"))
            self.lbl_apps_ram_warn.show()
        else:
            self.lbl_apps_ram_warn.hide()

    # --------------------------------------------------------------------------
    # SCHERMATA 6: UTENTE E HOSTNAME
    # --------------------------------------------------------------------------
    def _build_screen6_user(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(10)

        self.s6_title = QLabel()
        self.s6_title.setObjectName("SectionTitle")
        v.addWidget(self.s6_title)

        card = QFrame()
        card.setProperty("class", "Card")
        grid = QGridLayout(card)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)

        self.s6_fn_lbl = QLabel()
        self.inp_fullname = QLineEdit(self.state.get("fullname", ""))
        self.inp_fullname.textChanged.connect(lambda t: self.state.update({"fullname": t}))

        self.s6_un_lbl = QLabel()
        self.inp_username = QLineEdit(self.state.get("username", "note"))
        self.inp_username.textChanged.connect(lambda t: self.state.update({"username": t}))

        self.s6_pw1_lbl = QLabel()
        self.inp_pw1 = QLineEdit()
        self.inp_pw1.setEchoMode(QLineEdit.Password)

        self.s6_pw2_lbl = QLabel()
        self.inp_pw2 = QLineEdit()
        self.inp_pw2.setEchoMode(QLineEdit.Password)

        self.chk_user_show_pw = QCheckBox()
        self.chk_user_show_pw.toggled.connect(
            lambda c: (
                self.inp_pw1.setEchoMode(QLineEdit.Normal if c else QLineEdit.Password),
                self.inp_pw2.setEchoMode(QLineEdit.Normal if c else QLineEdit.Password),
            )
        )

        self.s6_hn_lbl = QLabel()
        self.inp_hostname = QLineEdit(self.state.get("hostname", "noteos"))
        self.inp_hostname.textChanged.connect(lambda t: self.state.update({"hostname": t}))

        grid.addWidget(self.s6_fn_lbl, 0, 0)
        grid.addWidget(self.inp_fullname, 0, 1)
        grid.addWidget(self.s6_un_lbl, 0, 2)
        grid.addWidget(self.inp_username, 0, 3)

        grid.addWidget(self.s6_pw1_lbl, 1, 0)
        grid.addWidget(self.inp_pw1, 1, 1)
        grid.addWidget(self.s6_pw2_lbl, 1, 2)
        grid.addWidget(self.inp_pw2, 1, 3)

        grid.addWidget(self.s6_hn_lbl, 2, 0)
        grid.addWidget(self.inp_hostname, 2, 1)
        grid.addWidget(self.chk_user_show_pw, 2, 2, 1, 2)

        v.addWidget(card)
        v.addStretch(1)
        return w

    def _validate_user_screen(self):
        un = self.inp_username.text().strip()
        pw1 = self.inp_pw1.text()
        pw2 = self.inp_pw2.text()
        if not un or len(pw1) < 4:
            self.lbl_nav_error.setText(self.t("s6_err_empty"))
            return False
        if not re.match(r"^[a-z_][a-z0-9_-]*$", un):
            self.lbl_nav_error.setText(self.t("s6_err_user"))
            return False
        if pw1 != pw2:
            self.lbl_nav_error.setText(self.t("s6_err_match"))
            return False
        self.user_password = pw1
        self.lbl_nav_error.setText("")
        return True

    # --------------------------------------------------------------------------
    # SCHERMATA 7: LOGIN AUTOMATICO
    # --------------------------------------------------------------------------
    def _build_screen7_autologin(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(14)

        self.s7_title = QLabel()
        self.s7_title.setObjectName("SectionTitle")
        v.addWidget(self.s7_title)

        card = QFrame()
        card.setProperty("class", "Card")
        vc = QVBoxLayout(card)
        self.rb_autologin_yes = QRadioButton()
        self.rb_autologin_no = QRadioButton()
        if self.state.get("autologin", True):
            self.rb_autologin_yes.setChecked(True)
        else:
            self.rb_autologin_no.setChecked(True)
        self.rb_autologin_yes.toggled.connect(lambda c: self.state.update({"autologin": c}))
        vc.addWidget(self.rb_autologin_yes)
        vc.addWidget(self.rb_autologin_no)
        v.addWidget(card)
        v.addStretch(1)
        return w

    # --------------------------------------------------------------------------
    # SCHERMATA 8: RIEPILOGO E INSTALLAZIONE
    # --------------------------------------------------------------------------
    def _build_screen8_install(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(10)

        self.s8_title = QLabel()
        self.s8_title.setObjectName("SectionTitle")
        v.addWidget(self.s8_title)

        self.lbl_bat_status = QLabel()
        self.lbl_bat_status.setWordWrap(True)
        v.addWidget(self.lbl_bat_status)

        self.lbl_summary_box = QLabel()
        self.lbl_summary_box.setWordWrap(True)
        self.lbl_summary_box.setStyleSheet("background: #161b22; color: #eff0f1; border: 1px solid #30363d; border-radius: 8px; padding: 10px; font-size: 16px;")
        v.addWidget(self.lbl_summary_box)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(36)
        self.progress_bar.setValue(0)
        v.addWidget(self.progress_bar)

        self.txt_install_log = QPlainTextEdit()
        self.txt_install_log.setReadOnly(True)
        self.txt_install_log.setStyleSheet("background: #090d11; color: #7ee787; font-family: monospace; font-size: 14px;")
        v.addWidget(self.txt_install_log, 1)

        act_row = QHBoxLayout()
        self.btn_start_install = QPushButton()
        self.btn_start_install.setObjectName("PrimaryBtn")
        self.btn_start_install.clicked.connect(lambda: self._start_installation(simulate_fail=False))

        self.btn_retry_install = QPushButton()
        self.btn_retry_install.setStyleSheet("background-color: #9e6a03; color: #ffffff;")
        self.btn_retry_install.hide()
        self.btn_retry_install.clicked.connect(lambda: self._start_installation(simulate_fail=False))

        self.btn_reboot_now = QPushButton()
        self.btn_reboot_now.setObjectName("PrimaryBtn")
        self.btn_reboot_now.hide()
        self.btn_reboot_now.clicked.connect(self._reboot_to_desktop)

        act_row.addWidget(self.btn_start_install)
        act_row.addWidget(self.btn_retry_install)
        act_row.addWidget(self.btn_reboot_now)
        v.addLayout(act_row)
        return w

    def _refresh_summary_screen(self):
        # Controllo batteria
        cap, st = 85, "Charging"
        try:
            if os.path.exists("/sys/class/power_supply/battery/capacity"):
                with open("/sys/class/power_supply/battery/capacity") as f:
                    cap = int(f.read().strip())
            if os.path.exists("/sys/class/power_supply/battery/status"):
                with open("/sys/class/power_supply/battery/status") as f:
                    st = f.read().strip()
        except Exception:
            pass

        if cap < 30:
            self.lbl_bat_status.setText(self.t("s8_bat_warn", cap=cap, st=st))
            self.lbl_bat_status.setStyleSheet("color: #f0883e; font-weight: bold; background: #2d2115; padding: 8px; border-radius: 6px;")
        else:
            self.lbl_bat_status.setText(self.t("s8_bat_ok", cap=cap, st=st))
            self.lbl_bat_status.setStyleSheet("color: #3fb950; font-weight: bold; background: #161b22; padding: 8px; border-radius: 6px;")

        desk = DESKTOPS[self.state.get("desktop", "lxqt")]
        apps = self.state.get("selected_apps", [])
        lang = self.state.get("lang", "en")
        desk_name = desk.get(f"name_{lang}", desk.get("name_en", desk.get("name_it")))
        yes_str = self.t("s8_yes")
        no_str = self.t("s8_no")
        none_str = self.t("s8_none")
        base_str = self.t("s8_base_inc")
        act_str = self.t("s8_active")
        vkbd_str = yes_str if self.state.get("vkbd_enabled", True) else no_str
        ntp_str = yes_str if self.state.get("ntp_enabled", True) else no_str
        auto_str = yes_str if self.state.get("autologin", True) else no_str
        net_str = self.state.get("net_name") or self.state.get("wifi_ssid") or act_str
        apps_str = ", ".join(apps) if apps else none_str

        summary_lines = [
            self.t("s8_sum_lang", lang=lang.upper(), kb=self.state["kb_layout"], vkbd=vkbd_str),
            self.t("s8_sum_wifi", net=net_str, tz=self.state["timezone"], ntp=ntp_str),
            self.t("s8_sum_desk", desk=desk_name, base=base_str, mb=desk["installed_mb"]),
            self.t("s8_sum_apps", cnt=len(apps), apps=apps_str),
            self.t("s8_sum_user", user=self.state.get("username"), name=self.state.get("fullname"), host=self.state.get("hostname"), auto=auto_str),
        ]
        self.lbl_summary_box.setText("\n".join(summary_lines))

    def _start_installation(self, simulate_fail=False):
        self.btn_start_install.setEnabled(False)
        self.btn_retry_install.hide()
        self.btn_back.setEnabled(False)
        self.worker = InstallWorker(
            self.state,
            self.user_password or "debian",
            dry_run=self.args.dry_run,
            simulate_apt_fail=simulate_fail,
            log_path=self.log_file,
        )
        self.worker.progress_sig.connect(self._on_install_progress)
        self.worker.log_sig.connect(self.txt_install_log.appendPlainText)
        self.worker.finished_sig.connect(self._on_install_finished)
        self.worker.start()

    def _on_install_progress(self, pct, msg):
        self.progress_bar.setValue(pct)
        self.lbl_nav_error.setStyleSheet("color: #58a6ff; font-weight: bold;")
        self.lbl_nav_error.setText(msg)

    def _on_install_finished(self, ok, msg):
        if ok:
            self.lbl_nav_error.setStyleSheet("color: #3fb950; font-weight: bold;")
            self.lbl_nav_error.setText(msg)
            self.btn_start_install.hide()
            self.btn_retry_install.hide()
            self.btn_reboot_now.show()
        else:
            self.lbl_nav_error.setStyleSheet("color: #ff7b72; font-weight: bold;")
            err_prefix = self.t("inst_err_prefix")
            self.lbl_nav_error.setText(f"❌ {err_prefix}: {msg}")
            self.btn_retry_install.show()
            self.btn_back.setEnabled(True)

    def _reboot_to_desktop(self):
        if self.args.dry_run:
            QApplication.quit()
        else:
            subprocess.run(["systemctl", "reboot"], check=False)

    # --------------------------------------------------------------------------
    # NAVIGAZIONE E TRADUZIONE
    # --------------------------------------------------------------------------
    def _retranslate_ui(self):
        self.setWindowTitle(self.t("app_title"))
        self.lbl_app_title.setText(self.t("app_title"))
        self.btn_back.setText(self.t("btn_back"))
        self.btn_next.setText(self.t("btn_next"))
        self.btn_toggle_kbd.setText(self.t("btn_kbd"))

        self.s1_title.setText(self.t("s1_title"))
        self.s1_desc.setText(self.t("s1_desc"))
        self.s1_lang_hdr.setText(self.t("s1_lang_hdr"))
        self.s1_kb_hdr.setText(self.t("s1_kb_hdr"))
        self.chk_vkbd.setText(self.t("s1_vkbd_chk"))

        self.s2_title.setText(self.t("s2_title"))
        self.s2_desc.setText(self.t("s2_desc"))
        self.btn_scan_wifi.setText(self.t("s2_scan_btn"))
        self.chk_hidden_wifi.setText(self.t("s2_hidden_chk"))
        self.inp_hidden_ssid.setPlaceholderText(self.t("s2_ssid_ph"))
        self.inp_wifi_pass.setPlaceholderText(self.t("s2_pass_ph"))
        self.chk_wifi_show_pw.setText(self.t("s2_show_pass"))
        self.btn_connect_wifi.setText(self.t("s2_connect_btn"))

        self.s3_title.setText(self.t("s3_title"))
        self.chk_ntp.setText(self.t("s3_ntp_chk"))
        self.s3_tz_lbl.setText(self.t("s3_tz_lbl"))
        self.s3_man_lbl.setText(self.t("s3_man_lbl"))
        self.btn_apply_dt.setText(self.t("s3_apply_btn"))

        self.s4_title.setText(self.t("s4_title"))
        self.s4_desc.setText(self.t("s4_desc"))
        self.s4_base_hdr.setText(self.t("s4_base_hdr"))
        self._update_desktop_card()

        self.s5_title.setText(self.t("s5_title"))
        self.btn_rec_apps.setText(self.t("s5_rec_btn"))
        self.btn_clear_apps.setText(self.t("s5_clear_btn"))
        self._rebuild_apps_screen()

        self.s6_title.setText(self.t("s6_title"))
        self.s6_fn_lbl.setText(self.t("s6_fn_lbl"))
        self.s6_un_lbl.setText(self.t("s6_un_lbl"))
        self.s6_pw1_lbl.setText(self.t("s6_pw1_lbl"))
        self.s6_pw2_lbl.setText(self.t("s6_pw2_lbl"))
        self.chk_user_show_pw.setText(self.t("s2_show_pass"))
        self.s6_hn_lbl.setText(self.t("s6_hn_lbl"))

        self.s7_title.setText(self.t("s7_title"))
        self.rb_autologin_yes.setText(self.t("s7_yes"))
        self.rb_autologin_no.setText(self.t("s7_no"))

        self.s8_title.setText(self.t("s8_title"))
        self.btn_start_install.setText(self.t("s8_start_btn"))
        self.btn_retry_install.setText(self.t("s8_retry_btn"))
        self.btn_reboot_now.setText(self.t("s8_reboot_btn"))

    def _go_to_step(self, idx, save=True):
        idx = max(0, min(7, idx))
        self.stack.setCurrentIndex(idx)
        self.state["step"] = idx
        self.lbl_step_indicator.setText(self.t("step_of", cur=idx + 1))
        self.dots_widget.set_step(idx)
        self.lbl_nav_error.setText("")
        self.touch_kbd.hide()

        self.btn_back.setEnabled(idx > 0)
        self.btn_next.setVisible(idx < 7)

        if idx == 1:
            if self.wifi_list.count() == 0:
                self._scan_wifi()
            # Never block the GUI thread here: the check may run several curl/ping commands
            self._update_wifi_banner(err_msg=None)
            self._start_net_check()
        else:
            self.btn_next.setEnabled(True)

        if idx == 7:
            self._refresh_summary_screen()

        if save:
            self._save_state()

    def _on_back(self):
        cur = self.stack.currentIndex()
        if cur > 0:
            self._go_to_step(cur - 1)

    def _on_next(self):
        cur = self.stack.currentIndex()
        if cur == 1 and not self.state.get("net_connected"):
            self._update_wifi_banner(err_msg="Connettiti al Wi-Fi prima di procedere.")
            return
        if cur == 2:
            self._apply_datetime()
        if cur == 5:
            if not self._validate_user_screen():
                return
        if cur < 7:
            self._go_to_step(cur + 1)


# ==============================================================================
# AUTOMAZIONE SCREENSHOT E TEST ERRORI PER XEPHYR / XVFB (--test-screenshots)
# ==============================================================================
def run_automated_screenshots(win: N8000SetupWizard, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)

    def snap(name):
        QApplication.processEvents()
        time.sleep(0.15)
        QApplication.processEvents()
        pix = win.grab()
        pix.save(os.path.join(out_dir, name), "PNG")
        print(f"Screenshot salvato: {os.path.join(out_dir, name)}")

    # 1. Schermata 1: Lingua e Tastiera
    win._go_to_step(0)
    snap("screen1_language_keyboard.png")

    # 2. Schermata 2: Wi-Fi (prima mostra errore rete assente, poi connesso)
    win._go_to_step(1)
    win.args.simulate_no_net = True
    win._connect_wifi_and_check()
    snap("screen2_wifi_error_no_net.png")
    win.args.simulate_no_net = False
    win.inp_wifi_pass.setText("PasswordSegreta123")
    win._connect_wifi_and_check()
    snap("screen2_wifi_connected.png")

    # 3. Schermata 3: Data, Ora e Fuso
    win._go_to_step(2)
    snap("screen3_datetime_timezone.png")

    # 4. Schermata 4: Desktop (LXQt default + KDE Plasma con avviso)
    win._go_to_step(3)
    win.rb_lxqt.setChecked(True)
    snap("screen4_desktop_lxqt.png")
    win.rb_kde.setChecked(True)
    snap("screen4_desktop_kde_warning.png")
    win.rb_lxqt.setChecked(True)

    # 5. Schermata 5: 20 Programmi (LXQt + sezione finale con già inclusi / non disponibili)
    win._go_to_step(4)
    snap("screen5_apps_20_lxqt.png")
    win.apps_scroll.verticalScrollBar().setValue(win.apps_scroll.verticalScrollBar().maximum())
    snap("screen5_apps_bottom_sections.png")
    win.apps_scroll.verticalScrollBar().setValue(0)

    # 6. Schermata 6: Utente (errore password diverse + valido con tastiera touch)
    win._go_to_step(5)
    win.inp_fullname.setText("Note User")
    win.inp_username.setText("noteos")
    win.inp_pw1.setText("linux123")
    win.inp_pw2.setText("diversa999")
    win._validate_user_screen()
    win.touch_kbd.show()
    snap("screen6_user_password_mismatch.png")
    win.inp_pw2.setText("linux123")
    win._validate_user_screen()
    snap("screen6_user_valid.png")

    # 7. Schermata 7: Login Automatico
    win._go_to_step(6)
    snap("screen7_autologin.png")

    # 8. Schermata 8: Riepilogo, Errore apt simulato con Riprova, e Completamento
    win._go_to_step(7)
    win._start_installation(simulate_fail=True)
    while win.worker.isRunning():
        QApplication.processEvents()
        time.sleep(0.05)
    snap("screen8_install_apt_error_retry.png")

    win._start_installation(simulate_fail=False)
    while win.worker.isRunning():
        QApplication.processEvents()
        time.sleep(0.05)
    snap("screen8_install_completed.png")
    QApplication.quit()


def parse_args():
    p = argparse.ArgumentParser(description="noteos-setup First-Boot Touch Wizard")
    p.add_argument("--rerun", action="store_true", help="Rilancia il wizard anche se setup.done esiste già")
    p.add_argument("--dry-run", action="store_true", help="Modalità simulazione (non modifica il sistema)")
    p.add_argument("--state-dir", default="/var/lib/noteos", help="Directory di stato (default: /var/lib/noteos)")
    p.add_argument("--test-screenshots", default="", help="Cattura automaticamente gli screenshot delle 8 schermate nella cartella indicata")
    p.add_argument("--simulate-no-net", action="store_true", help="Simula assenza di connessione internet")
    return p.parse_args()


def main():
    args = parse_args()
    done_file = os.path.join(args.state_dir, "setup.done")
    if os.path.exists(done_file) and not args.rerun and not args.test_screenshots:
        print(f"Setup già completato ({done_file}). Usa 'noteos-setup --rerun' per rieseguire il wizard.")
        return 0
    if args.rerun and os.path.exists(done_file):
        try:
            os.remove(done_file)
        except Exception:
            pass

    app = QApplication(sys.argv)
    dark_pal = QPalette()
    dark_pal.setColor(QPalette.Window, QColor("#1b2228"))
    dark_pal.setColor(QPalette.WindowText, QColor("#eff0f1"))
    dark_pal.setColor(QPalette.Base, QColor("#20272d"))
    dark_pal.setColor(QPalette.AlternateBase, QColor("#1b2228"))
    dark_pal.setColor(QPalette.ToolTipBase, QColor("#eff0f1"))
    dark_pal.setColor(QPalette.ToolTipText, QColor("#eff0f1"))
    dark_pal.setColor(QPalette.Text, QColor("#eff0f1"))
    dark_pal.setColor(QPalette.Button, QColor("#20272d"))
    dark_pal.setColor(QPalette.ButtonText, QColor("#eff0f1"))
    dark_pal.setColor(QPalette.BrightText, Qt.red)
    dark_pal.setColor(QPalette.Link, QColor("#3daee9"))
    dark_pal.setColor(QPalette.Highlight, QColor("#1d99f3"))
    dark_pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(dark_pal)

    win = N8000SetupWizard(args)
    if not args.test_screenshots:
        win.showFullScreen()
        win.raise_()
        win.activateWindow()
    else:
        win.show()

    # Flush initial draw calls and wake up display immediately
    win.repaint()
    QApplication.flush()
    QApplication.processEvents()
    if not args.dry_run and not args.test_screenshots:
        import glob
        for fb in glob.glob("/sys/class/graphics/fb*/blank"):
            try:
                with open(fb, "w") as f:
                    f.write("0\n")
            except Exception:
                pass
        for b in glob.glob("/sys/class/backlight/*/max_brightness"):
            try:
                with open(b) as f_max:
                    max_b = int(f_max.read().strip())
                b_dir = os.path.dirname(b)
                # NOTE: max level = 100% PWM duty, which blacks out the N8000 panel
                with open(os.path.join(b_dir, "brightness"), "w") as f_br:
                    f_br.write(str(max(1, max_b // 2)) + "\n")
            except Exception:
                pass
        subprocess.run(["xset", "dpms", "force", "on"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        subprocess.run(["plymouth", "quit", "--retain-splash"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

    if args.test_screenshots:
        QTimer.singleShot(200, lambda: run_automated_screenshots(win, args.test_screenshots))

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())

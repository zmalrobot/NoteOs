# NoteOS 1.0.0 — Samsung Galaxy Note 10.1 (GT-N8000)

**NoteOS 1.0.0** è la prima release ufficiale per **Samsung Galaxy Note 10.1 3G (GT-N8000 / p4noterf)**, progettata per trasformare il tablet del 2012 in un sistema operativo Linux desktop moderno, stabile, scattante e touch-friendly basato su **Debian 12 (Bookworm armhf)** e **Linux Mainline 6.6 LTS**.

---

## 1. Matrice di Supporto Hardware

### Cosa Funziona al 100%
- **Kernel Linux 6.6 LTS**: kernel mainline moderno con silent boot e splash grafico Plymouth a 1280x800.
- **Accelerazione Grafica 3D (GPU)**: ARM Mali-400 MP4 gestita nativamente tramite driver open-source Mesa Lima (`lima_drm`), con rendering OpenGL ES 2.0 a 60 fps fluidi.
- **Schermo e Multi-touch**: digitalizzatore touch Melfas MMS134S/MMS136 pienamente funzionante con gesture multi-dito e tastiera virtuale integrata.
- **Luminosità Schermo**: gestione PWM controllata al 50% all'avvio per evitare lo spegnimento del pannello LCD SEC 1280x800.
- **Wi-Fi (802.11 a/b/g/n)**: Broadcom BCM4334 SDIO (`brcmfmac`) completamente stabilizzato:
  - Risparmio energetico 802.11 disattivato per eliminare packet loss e timeout TCP.
  - Roaming autonomo del firmware disattivato (`roamoff=1`) per evitare interruzioni di rete.
  - Gestione credenziali `nmcli` con `psk-flags 0` e iniezione `passwd-file` per associazioni istantanee senza Secret Agent D-Bus.
- **Bluetooth 4.0 LE**: Broadcom BCM4334 UART (`hci_bcm`) con caricamento firmware patchram `BCM4334B0.hcd`.
- **Audio Completo**: chip Wolfson WM1811 I2S integrato tramite ALSA e PipeWire (altoparlanti stereo e jack cuffie).
- **Batteria & Telemetria di Ricarica**: monitoraggio percentuale e stato di ricarica tramite PMIC Maxim MAX77686 e controller SMB347.
- **ZRAM Compressed Swap**: partizione di swap compressa in RAM da 1 GB (algoritmo LZ4) per garantire eccellente multitasking sui 2 GB di RAM LPDDR2.
- **Rete Resiliente & APT**: stack di rete IPv4 forzato, TCP MTU probing abilitato per hotspot mobili/DSL, e retry automatici in APT per download sicuri.

### Cosa NON Funziona (Limitazioni Note)
- **Wacom S-Pen (Digitalizzatore EMR)**: il controller magnetico Wacom non è alimentato/mappato nel Device Tree mainline 6.6. Il tocco delle dita funziona perfettamente su tutto lo schermo.
- **Fotocamere (Fronte e Retro)**: i driver per il controller Samsung FIMC e i sensori MIPI Exynos4412 non sono stati portati nel kernel Linux mainline.
- **Modem 3G Cellulare (Chiamate vocali e SMS)**: l'interfaccia proprietaria IPC del modem baseband Intel XMM6262 non è supportata in Linux moderno. La connettività internet avviene via Wi-Fi.

---

## 2. Il Ripartizionamento eMMC: Architettura, Vantaggi e Svantaggi

### Come Funziona l'Architettura del Disco
La memoria interna eMMC del GT-N8000 da 16 GB (~14.68 GiB effettivi) adotta una tabella partizioni GPT standard con bootloader proprietario Samsung S-BOOT.
- Nel layout originale Android a 12 partizioni, lo spazio era frammentato tra partizioni ridotte: `p8 CACHE` (100 MB), `p9 SYSTEM` (3.5 GB), `p10 HIDDEN` (500 MB), `p11 OTA` (8 MB) e `p12 USERDATA` (~10.8 GB).
- Il ripartizionamento di NoteOS fonde le 5 vecchie partizioni Android contigue (`p8..p12`) in **un'unica grande partizione `mmcblk0p8` da 14.59 GiB** formattata in ext4 (`LABEL=debian_root`).
- **Le prime 7 partizioni (`p1 BOTA0` .. `p7 RADIO`) rimangono IDENTICHE al 100% per LBA di inizio, dimensione e PARTUUID**. La Recovery TWRP (`mmcblk0p6`) e il bootloader S-BOOT restano completamente intatti e protetti.

### Vantaggi del Ripartizionamento
1. **Spazio Disco Pieno per Linux**: l'utente dispone di **14.6 GiB effettivi** per il sistema operativo, i desktop completi, gli ambienti di programmazione e i propri documenti, senza saturare la vecchia partizione di sistema Android.
2. **Semplicità e Affidabilità**: un unico filesystem `ext4` lineare senza partizioni frammentate, loop device o overlay complessi.
3. **Sicurezza Bootloader Garantita**: S-BOOT e TWRP risiedono nelle partizioni inviolate `p1..p7`. È sempre possibile avviare TWRP o la Download Mode in qualsiasi circostanza.
4. **Completamente Reversibile**: grazie al backup salvato `partition-layout-original.sfdisk`, è possibile ripristinare il layout stock a 12 partizioni in qualsiasi momento.

### Svantaggi e Rischi da Considerare
1. **Incompatibilità con ROM Android Tradizionali**: il nuovo layout impedisce l'avvio delle vecchie ROM Android basate sullo schema a 12 partizioni senza prima eseguire la procedura di rollback.
2. **Brickbug Hardware eMMC (`VTU00M 0xF1`)**: il chip eMMC montato su GT-N8000 soffre del noto difetto hardware Samsung sul comando TRIM/CMD38. **È vietato eseguire comandi `fstrim` o montare con opzione `discard`**. NoteOS include già di serie il mascheramento preventivo di `fstrim.timer` e `fstrim.service` per proteggere l'hardware a vita.

---

## 3. Guida all'Installazione da PC

### Prerequisiti
- **Tablet Samsung Galaxy Note 10.1 (GT-N8000)** con batteria carica ad almeno il 50%.
- **TWRP Recovery (versione 3.7.0 o successiva)** installata sulla partizione recovery (`mmcblk0p6`).
- **Cavo dati USB 30 pin Samsung** collegato a un computer con sistema operativo Linux.
- Backup di sicurezza della partizione `/efs` salvato preventivamente sul computer.

### Procedura di Installazione Automatica
1. Avviare il tablet in modalità TWRP Recovery (tenere premuti contemporaneamente i tasti `Power` + `Volume Su` fino alla comparsa della schermata TeamWin).
2. Collegare il cavo USB al PC e verificare la connessione:
   ```bash
   adb devices
   # Deve comparire: <serial_device> recovery
   ```
3. Clonare o scaricare il repository NoteOS sul computer host:
   ```bash
   git clone https://github.com/zmalrobot/NoteOs.git
   cd NoteOs
   ```
4. Se il rootfs non è presente localmente in `out/n8000/rootfs.tar.gz`, compilarlo con Docker/Podman:
   ```bash
   ./scripts/05_build_rootfs.sh
   ```
5. Avviare l'installatore automatico completo:
   ```bash
   ./scripts/07_install.sh --full --yes
   ```
   L'installer eseguirà in modo trasparente e sicuro:
   - Controllo del dispositivo target (`p4noterf`), batteria e budget boot image (<= 7.5 MiB).
   - Backup di sicurezza di `BOOT` e `RECOVERY`.
   - Formattazione pulita in `ext4` della partizione unificata `mmcblk0p8` (`LABEL=debian_root`).
   - Invio ad alta velocità ed estrazione completa del rootfs Debian 12 con GNU tar.
   - Installazione dei firmware ufficiali Wi-Fi e Bluetooth.
   - Flashing del kernel `boot.img` con verifica bit-a-bit tramite rilettura crittografica SHA256.
   - Controllo di integrità del filesystem `e2fsck` e verifica dell'integrità della recovery.
6. Riavviare il tablet in NoteOS:
   ```bash
   adb reboot
   ```

---

## 4. Guida all'Uso del Wizard di Primo Avvio (`noteos-setup`)

All'accensione, il tablet mostrerà l'animazione grafica di boot NoteOS a schermo intero (1280x800), avviando direttamente il wizard touch guidato a 8 schermate:

1. **Schermata 1 — Benvenuto, Lingua e Tastiera**:
   - Scegli la lingua del sistema e del wizard (Italiano, English, Français, Deutsch, Español).
   - Seleziona il layout della tastiera hardware/USB (es. `it`, `us`, `de`, `fr`, `es`).
   - Abilita o disabilita la tastiera virtuale touch su schermo.
2. **Schermata 2 — Connessione Wi-Fi**:
   - Premi "Cerca Reti" per scansionare gli access point wireless disponibili.
   - Seleziona la tua rete (o seleziona "Rete Nascosta" e digita l'SSID).
   - Inserisci la password Wi-Fi e premi "Connetti".
   - Il wizard applica automaticamente il salvataggio persistente della chiave, inietta i DNS pubblici (`1.1.1.1`, `8.8.8.8`) e verifica la connettività web con i server Debian.
3. **Schermata 3 — Data, Ora e Fuso Orario**:
   - Seleziona il tuo fuso orario dalla lista a scorrimento (es. `Europe/Rome`).
   - Mantieni abilitata la sincronizzazione automatica dell'orologio tramite protocollo NTP via rete.
4. **Schermata 4 — Scelta dell'Ambiente Desktop**:
   - **LXQt (Consigliato)**: Desktop leggerissimo basato su Qt, estremamente reattivo, a basso consumo di memoria RAM, ideale per l'hardware del tablet.
   - **KDE Plasma**: Desktop completo, elegante e moderno, ricco di effetti e personalizzazioni grafiche.
5. **Schermata 5 — Selezione delle Applicazioni**:
   - Scegli i pacchetti desiderati dalla suite verificata per architettura ARMv7 (`armhf`):
     - *Produttività*: LibreOffice (Suite da ufficio completa), Visual Studio Code (Editor di codice).
     - *Navigazione & Media*: Firefox ESR (Browser web moderno), VLC Player (Media player con supporto hardware), Thunderbird.
     - *Utilità & Grafica*: GIMP (Editor immagini), Btop (Monitor risorse touch), Calibre, e altri tool.
6. **Schermata 6 — Creazione Account Utente**:
   - Digita il tuo nome completo, il nome utente di login (tutto minuscolo) e l'hostname del dispositivo.
   - Imposta la password dell'account (inviata in modo sicuro direttamente a `chpasswd` via stdin).
7. **Schermata 7 — Opzioni di Accesso**:
   - Scegli se abilitare l'**Accesso Automatico (Autologin)** per entrare direttamente nel Desktop all'accensione del tablet senza dover digitare la password.
8. **Schermata 8 — Installazione e Completamento**:
   - Esamina il riassunto della configurazione e premi "Avvia Installazione".
   - Il worker configurerà l'utente, installerà i pacchetti del desktop scelto e delle applicazioni selezionate, con log dettagliati e barra di avanzamento in tempo reale.
   - Al termine, comparirà il pulsante "Riavvia in NoteOS": premilo per accedere al tuo nuovo ambiente Linux touch!

---

## 5. Checksum Crittografici degli Asset (SHA256)

Tutti gli asset di release possono essere verificati tramite `sha256sum`:

```
3812472f92f3b8ec5e2e07470efbe169f587a5042e06957982f85bc3202d0c9b  boot.img
42b24cc9a623e8313efa37650ef1d57de6af5ca7591bbb67b1b1fad105e4fbfa  boot-debug.img
a1f616b6e523b62c21f5e95cc4bcc7363a21c774c22ea1afc29a1efdeb3f6001  rootfs.tar.gz
5a06623bb936269b262c83add22aa2671b003ab62b45484712e5dfc3a01dec2c  noteos-branding_1.0.0_all.deb
```

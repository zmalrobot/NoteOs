#!/bin/bash
set -euo pipefail

# ==============================================================================
# wizard/start-kiosk.sh
# Avvia una sessione X11 minimale a schermo intero (1280x800) con Openbox,
# la tastiera virtuale touch Onboard e il wizard PyQt5 noteos-setup.
# ==============================================================================

export DISPLAY=:0
export QT_QPA_PLATFORM=xcb
export QT_AUTO_SCREEN_SCALE_FACTOR=0
export QT_SCALE_FACTOR=1

mkdir -p /var/lib/noteos

# Termina Plymouth rilasciando il DRM master ma mantenendo lo splash screen attivo fino a Xorg
if command -v plymouth >/dev/null 2>&1; then
    plymouth quit --retain-splash 2>/dev/null || true
fi

# Disattiva console blanking sul kernel virtual terminal (VT1)
TERM=linux setterm --blank 0 --powerdown 0 </dev/tty1 >/dev/tty1 2>/dev/null || true

cat << 'XINIT_EOF' > /tmp/noteos-kiosk-xinitrc
#!/bin/sh
xset s off
xset -dpms
xset s noblank

# Configura Openbox per non mostrare decorazioni né cornici (modalità kiosk a tutto schermo)
mkdir -p ~/.config/openbox
cat << 'OB_EOF' > ~/.config/openbox/rc.xml
<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
  <theme>
    <titleLayout></titleLayout>
  </theme>
  <applications>
    <application class="*">
      <decor>no</decor>
      <position force="yes">
        <x>0</x>
        <y>0</y>
      </position>
      <maximized>yes</maximized>
      <fullscreen>yes</fullscreen>
    </application>
  </applications>
</openbox_config>
OB_EOF

# Avvia window manager leggero senza decorazioni
openbox --config-file ~/.config/openbox/rc.xml &
sleep 0.3

# Avvia il wizard grafico di NoteOS a schermo intero (1280x800)
python3 /usr/share/noteos-setup/wizard_app.py "$@"
XINIT_EOF
chmod +x /tmp/noteos-kiosk-xinitrc

exec xinit /tmp/noteos-kiosk-xinitrc -- :0 vt1 -nolisten tcp -s 0 -dpms -quiet


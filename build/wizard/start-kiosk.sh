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

# Assicura che Plymouth venga chiuso se lo script termina inaspettatamente
trap 'plymouth quit 2>/dev/null || true' EXIT

# Disattiva console blanking sul kernel virtual terminal (VT1)
TERM=linux setterm --blank 0 --powerdown 0 </dev/tty1 >/dev/tty1 2>/dev/null || true

cat << 'XINIT_EOF' > /tmp/noteos-kiosk-xinitrc
# Force display power on immediately and disable blanking/standby
xset dpms force on 2>/dev/null || true
xset s off 2>/dev/null || true
xset -dpms 2>/dev/null || true
xset s noblank 2>/dev/null || true

# Ensure display panel backlight is turned on at full brightness
for b in /sys/class/backlight/*; do
    if [ -d "$b" ] && [ -f "$b/max_brightness" ]; then
        cat "$b/max_brightness" > "$b/brightness" 2>/dev/null || true
    fi
done

# Same colour as the Plymouth background: no black gap before the first Qt frame
xsetroot -solid '#161b22' 2>/dev/null || true

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

# Watchdog: the boot splash must never stay on screen forever, whatever happens.
( sleep 90; plymouth quit 2>/dev/null || true ) &
WATCHDOG_PID=$!

wait_plymouthd_gone() {
    # plymouthd exits asynchronously after "plymouth quit": wait until it released the DRM device
    for _ in $(seq 1 25); do
        pidof plymouthd >/dev/null 2>&1 || return 0
        sleep 0.2
    done
    return 0
}

# Release the DRM master held by Plymouth but keep the splash pixels on screen.
# Without this Xorg/modesetting fails with "drmSetMaster failed: Device or resource busy".
plymouth deactivate 2>/dev/null || true
sleep 0.5

# NOTE: no "exec" here, otherwise the EXIT trap above would never run.
rc=1
for attempt in 1 2 3; do
    started=$(date +%s)
    xinit /tmp/noteos-kiosk-xinitrc -- :0 vt1 -nolisten tcp -s 0 -dpms -quiet && rc=0 || rc=$?
    [ "${rc}" -eq 0 ] && break
    # X died quickly (e.g. DRM still busy): drop the splash completely and retry
    if [ $(( $(date +%s) - started )) -lt 20 ]; then
        echo "noteos-kiosk: X exited with ${rc} after <20s (attempt ${attempt}), retrying" >&2
        plymouth quit 2>/dev/null || true
        wait_plymouthd_gone
        sleep 1
    else
        break
    fi
done

kill "${WATCHDOG_PID}" 2>/dev/null || true
exit "${rc}"


"""Headless regression tests for the NoteOS setup wizard.

Run (needs PyQt5; no display required):

    QT_QPA_PLATFORM=offscreen python3 -m unittest build/wizard/tests/test_wizard_regressions.py -v

They guard the three fixes the tablet needs: no GUI-thread freeze when entering the
Wi-Fi screen, the touch keyboard closing on taps, and the Wi-Fi flow (PMF disabled,
no secret-agent dependency, GUI stays responsive while connecting).
"""
import os
import subprocess
import sys
import tempfile
import time
import types
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from PyQt5.QtCore import QEvent, QPoint, QTimer, Qt  # noqa: E402
from PyQt5.QtGui import QFocusEvent, QMouseEvent  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

import wizard_app as wa  # noqa: E402

APP = QApplication.instance() or QApplication(sys.argv)

SLOW_SECONDS = 0.5


class FakeRun:
    """Replacement for subprocess.run: records calls and makes network tools slow."""

    def __init__(self, connected=True, slow=True):
        self.calls = []
        self.connected = connected
        self.slow = slow

    def __call__(self, cmd, *args, **kwargs):
        self.calls.append(list(cmd))
        tool = cmd[0]
        if self.slow and tool in ("curl", "ping", "nmcli"):
            time.sleep(SLOW_SECONDS)
        out, rc = "", 0
        if tool == "nmcli" and "dev" in cmd and "-t" in cmd:
            out = "wlan0:connected\n" if self.connected else "wlan0:disconnected\n"
        elif tool == "ip" and "addr" in cmd:
            out = "    inet 192.168.1.5/24 brd 192.168.1.255 scope global wlan0\n"
        elif tool == "ip" and "route" in cmd:
            out = "default via 192.168.1.1 dev wlan0\n"
        elif tool == "curl":
            rc = 0 if self.connected else 1
        elif tool == "ping":
            rc = 0 if self.connected else 1
        return subprocess.CompletedProcess(cmd, rc, stdout=out, stderr="")


def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        APP.processEvents()
        time.sleep(0.01)


class WizardRegression(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.args = types.SimpleNamespace(
            rerun=False, dry_run=False, state_dir=self.tmp.name,
            test_screenshots="", simulate_no_net=False,
        )
        self.fake = FakeRun(connected=False, slow=True)
        self.patcher = unittest_mock_patch(wa.subprocess, "run", self.fake)
        self.patcher.start()
        self.win = wa.N8000SetupWizard(self.args)
        self.win.show()
        pump(0.1)

    def tearDown(self):
        for name in ("scan_worker", "net_worker", "wifi_worker"):
            w = getattr(self.win, name, None)
            if w is not None:
                w.wait(10000)
        self.win.close()
        self.patcher.stop()
        self.tmp.cleanup()

    # 1. Freeze when advancing from the language screen
    def test_entering_wifi_screen_does_not_block_gui(self):
        self.fake.connected = True  # connected but offline-ish: curl/ping are slow
        t0 = time.time()
        self.win._go_to_step(1)
        elapsed = time.time() - t0
        self.assertLess(elapsed, 0.15, f"_go_to_step(1) blocked the GUI thread for {elapsed:.2f}s")

    # 2. Touch keyboard closes on taps
    def _press(self, widget):
        ev = QMouseEvent(QEvent.MouseButtonPress, QPoint(5, 5), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        APP.sendEvent(widget, ev)

    def test_keyboard_closes_on_button_press(self):
        self.win.touch_kbd.show()
        self.assertFalse(self.win.touch_kbd.isHidden())
        self._press(self.win.btn_next)
        self.assertTrue(self.win.touch_kbd.isHidden())

    def test_keyboard_closes_on_list_tap(self):
        self.win.touch_kbd.show()
        self._press(self.win.wifi_list.viewport())
        self.assertTrue(self.win.touch_kbd.isHidden())

    def test_keyboard_opens_on_text_focus(self):
        self.win.state["vkbd_enabled"] = True
        self.win.touch_kbd.hide()
        APP.sendEvent(self.win.inp_wifi_pass, QFocusEvent(QEvent.FocusIn))
        self.assertFalse(self.win.touch_kbd.isHidden())

    # 3. Wi-Fi connection flow
    def test_wifi_flow_disables_pmf_and_keeps_gui_responsive(self):
        self.fake.connected = True
        self.win.state["wifi_ssid"] = "TestNet"
        self.win.inp_wifi_pass.setText("secret123")

        ticks = []
        timer = QTimer()
        timer.timeout.connect(lambda: ticks.append(1))
        timer.start(10)

        t0 = time.time()
        self.win._connect_wifi_and_check()
        self.assertLess(time.time() - t0, 0.15, "connect click blocked the GUI thread")

        deadline = time.time() + 20
        while self.win.wifi_worker.isRunning() and time.time() < deadline:
            APP.processEvents()
            time.sleep(0.01)
        pump(0.2)
        timer.stop()

        self.assertGreater(len(ticks), 20, "GUI event loop starved while connecting")
        flat = [" ".join(c) for c in self.fake.calls]
        add = [c for c in flat if "connection add" in c]
        self.assertTrue(add, "no 'nmcli connection add' call")
        self.assertIn("wifi-sec.pmf 1", add[0])
        self.assertFalse([c for c in flat if "dev wifi connect" in c],
                         "must not rely on 'nmcli dev wifi connect' (needs a SecretAgent)")
        self.assertTrue(self.win.state["net_connected"])


def unittest_mock_patch(target, attr, value):
    from unittest import mock
    return mock.patch.object(target, attr, value)


if __name__ == "__main__":
    unittest.main()


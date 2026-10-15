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
        out, rc, err = "", 0, ""
        if tool == "nmcli" and "connection" in cmd and "up" in cmd and getattr(self, "nmcli_up_err", None):
            rc = 1
            err = self.nmcli_up_err
        elif tool == "nmcli" and "dev" in cmd and "wifi" in cmd and "list" in cmd:
            out = "TestNet:90:WPA2:*\nGuestNet:60:WPA2:\n"
        elif tool == "nmcli" and "dev" in cmd and "-t" in cmd:
            out = "wlan0:connected\n" if self.connected else "wlan0:disconnected\n"
        elif tool == "nmcli" and "connection" in cmd and "show" in cmd:
            out = getattr(self, "conn_show_out", "")
        elif tool == "ip" and "addr" in cmd:
            out = "    inet 192.168.1.5/24 brd 192.168.1.255 scope global wlan0\n"
        elif tool == "ip" and "route" in cmd:
            out = "default via 192.168.1.1 dev wlan0\n"
        elif tool == "curl":
            rc = 0 if self.connected else 1
        elif tool == "ping":
            rc = 0 if self.connected else 1
        return subprocess.CompletedProcess(cmd, rc, stdout=out, stderr=err)


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
        self.assertIn("wifi-sec.psk-flags 0", add[0])
        self.assertFalse([c for c in flat if "dev wifi connect" in c],
                         "must not rely on 'nmcli dev wifi connect' (needs a SecretAgent)")
        up = [c for c in flat if "connection up" in c]
        self.assertTrue(up, "no 'nmcli connection up' call")
        self.assertIn("passwd-file", up[0], "nmcli connection up must supply passwd-file to avoid secret-agent errors")
        self.assertTrue(self.win.state["net_connected"])

    def test_wifi_flow_open_network(self):
        """Edge case: Open network without password connects cleanly without wifi-sec or passwd-file."""
        self.fake.connected = True
        self.fake.calls.clear()
        self.win.state["wifi_ssid"] = "FreePublicWiFi"
        self.win.inp_wifi_pass.setText("")
        self.win.chk_hidden_wifi.setChecked(False)

        self.win._connect_wifi_and_check()
        deadline = time.time() + 20
        while self.win.wifi_worker.isRunning() and time.time() < deadline:
            APP.processEvents()
            time.sleep(0.01)
        pump(0.1)

        flat = [" ".join(c) for c in self.fake.calls]
        add = [c for c in flat if "connection add" in c]
        self.assertTrue(add, "no 'nmcli connection add' call for open network")
        self.assertNotIn("wifi-sec.key-mgmt", add[0])
        self.assertNotIn("wifi-sec.psk", add[0])
        up = [c for c in flat if "connection up" in c]
        self.assertTrue(up, "no 'nmcli connection up' call for open network")
        self.assertNotIn("passwd-file", up[0])
        self.assertTrue(self.win.state["net_connected"])

    def test_wifi_flow_hidden_network(self):
        """Edge case: Hidden network sets 802-11-wireless.hidden yes and triggers directed probe."""
        self.fake.connected = True
        self.fake.calls.clear()
        self.win.chk_hidden_wifi.setChecked(True)
        self.win.inp_hidden_ssid.setText("SecretRouter")
        self.win.inp_wifi_pass.setText("supersecret99")

        self.win._connect_wifi_and_check()
        deadline = time.time() + 20
        while self.win.wifi_worker.isRunning() and time.time() < deadline:
            APP.processEvents()
            time.sleep(0.01)
        pump(0.1)

        flat = [" ".join(c) for c in self.fake.calls]
        add = [c for c in flat if "connection add" in c]
        self.assertTrue(add, "no 'nmcli connection add' call for hidden network")
        self.assertIn("802-11-wireless.hidden yes", add[0])
        self.assertIn("wifi-sec.psk-flags 0", add[0])
        rescan = [c for c in flat if "rescan" in c and "SecretRouter" in c]
        self.assertTrue(rescan, "hidden network should trigger directed probe rescan")
        self.assertTrue(self.win.state["net_connected"])

    def test_wifi_flow_short_password_validation(self):
        """Edge case: WPA password with fewer than 8 chars is rejected before invalid NM command."""
        self.fake.calls.clear()
        self.win.state["lang"] = "it"
        self.win.state["wifi_ssid"] = "SecuredNet"
        self.win.inp_wifi_pass.setText("short")
        self.win._connect_wifi_and_check()
        pump(0.1)
        flat = [" ".join(c) for c in self.fake.calls]
        add = [c for c in flat if "connection add" in c]
        self.assertEqual(len(add), 0, "must not invoke nmcli connection add with invalid short password")
        self.assertIn("almeno 8 caratteri", self.win.lbl_wifi_status.text())

    def test_wifi_error_formatting(self):
        """Edge case: Cryptic nmcli/NM errors are translated into human-friendly messages."""
        self.win.state["lang"] = "it"
        msg1 = self.win._format_wifi_error("Warning: password for '802-11-wireless-security.psk' not given in 'password-file' and nmcli cannot ask without '--ask' option", "TestNet")
        self.assertIn("non valida o autenticazione WPA fallita", msg1)

        msg2 = self.win._format_wifi_error("Error: Connection activation failed: Secrets were required, but not provided.", "TestNet")
        self.assertIn("non valida o autenticazione WPA fallita", msg2)

        msg3 = self.win._format_wifi_error("Error: The Wi-Fi network could not be found", "TestNet")
        self.assertIn("non trovata o fuori portata", msg3)

        # Also verify English translations
        self.win.state["lang"] = "en"
        msg_en = self.win._format_wifi_error("Warning: password for '802-11-wireless-security.psk' not given in 'passwd-file' and nmcli cannot ask without '--ask' option", "TestNet")
        self.assertIn("Invalid Wi-Fi password", msg_en)

    def test_wifi_flow_cleans_up_stale_profiles_by_uuid(self):
        """Edge case: Re-connection deletes prior matching profiles by UUID before creating new one."""
        self.fake.connected = True
        self.fake.calls.clear()
        self.fake.conn_show_out = "aaaa-bbbb-cccc-dddd:802-11-wireless:StaleNet\n"
        self.win.state["wifi_ssid"] = "StaleNet"
        self.win.inp_wifi_pass.setText("password123")

        self.win._connect_wifi_and_check()
        deadline = time.time() + 20
        while self.win.wifi_worker.isRunning() and time.time() < deadline:
            APP.processEvents()
            time.sleep(0.01)
        pump(0.1)

        flat = [" ".join(c) for c in self.fake.calls]
        del_uuid = [c for c in flat if "connection delete uuid aaaa-bbbb-cccc-dddd" in c]
        self.assertTrue(del_uuid, "must delete stale profile by UUID to avoid duplicate/ambiguous connection up")
        self.fake.conn_show_out = ""

    # 4. Wi-Fi scanning parses networks and updates QListWidget
    def test_wifi_scan_parses_networks_and_updates_list(self):
        self.win._scan_wifi()
        deadline = time.time() + 10
        while getattr(self.win, "scan_worker", None) and self.win.scan_worker.isRunning() and time.time() < deadline:
            APP.processEvents()
            time.sleep(0.01)
        pump(0.1)
        self.assertGreater(self.win.wifi_list.count(), 0)
        first_item = self.win.wifi_list.item(0).data(Qt.UserRole)
        self.assertEqual(first_item, "TestNet")

    # 5. Wi-Fi authentication failure handling (no wasteful retries, Next button remains disabled)
    def test_wifi_flow_auth_failure_skips_retry_and_disables_next(self):
        """Edge case: When WPA secrets are rejected, skip slow retry and ensure Next is disabled."""
        self.fake.calls.clear()
        self.fake.connected = False
        self.fake.nmcli_up_err = (
            "Warning: password for '802-11-wireless-security.psk' not given in 'passwd-file' "
            "and nmcli cannot ask without '--ask' option.\n"
            "Error: Connection activation failed: Secrets were required, but not provided."
        )
        self.win.state["lang"] = "it"
        self.win.state["wifi_ssid"] = "SecuredNet"
        self.win.inp_wifi_pass.setText("wrongpassword123")
        self.win.btn_next.setEnabled(True)  # Pretend it was enabled previously

        self.win._connect_wifi_and_check()
        self.assertFalse(self.win.btn_next.isEnabled(), "Next button must be disabled immediately when connection begins")

        deadline = time.time() + 20
        while self.win.wifi_worker.isRunning() and time.time() < deadline:
            APP.processEvents()
            time.sleep(0.01)
        pump(0.1)

        flat = [" ".join(c) for c in self.fake.calls]
        up_calls = [c for c in flat if "connection up" in c]
        self.assertEqual(len(up_calls), 1, "must not perform a second slow retry when credentials are confirmed invalid")
        self.assertFalse(self.win.state["net_connected"], "net_connected must remain False on auth failure")
        self.assertFalse(self.win.btn_next.isEnabled(), "Next button must remain disabled on auth failure")
        self.assertIn("non valida o autenticazione WPA fallita", self.win.lbl_wifi_status.text())
        curl_calls = [c for c in flat if "curl" in c]
        self.assertEqual(len(curl_calls), 0, "must skip DHCP/curl internet check when connection activation failed")

    # 6. Empty SSID validation in both hidden and standard modes
    def test_wifi_flow_empty_ssid_validation_hidden_and_standard(self):
        """Edge case: Empty SSID prompts appropriate localized warning for both standard list and hidden networks."""
        self.fake.calls.clear()
        # Case A: Standard mode without selection
        self.win.state["lang"] = "it"
        self.win.state["wifi_ssid"] = ""
        self.win.chk_hidden_wifi.setChecked(False)
        self.win._connect_wifi_and_check()
        pump(0.05)
        self.assertIn("Seleziona una rete Wi-Fi dall'elenco", self.win.lbl_wifi_status.text())

        # English translation
        self.win.state["lang"] = "en"
        self.win._connect_wifi_and_check()
        pump(0.05)
        self.assertIn("Select a Wi-Fi network from the list", self.win.lbl_wifi_status.text())

        # Case B: Hidden network mode without entering SSID
        self.win.chk_hidden_wifi.setChecked(True)
        self.win.inp_hidden_ssid.setText("")
        self.win._connect_wifi_and_check()
        pump(0.05)
        self.assertIn("Please enter the hidden Wi-Fi network name", self.win.lbl_wifi_status.text())

        self.win.state["lang"] = "it"
        self.win._connect_wifi_and_check()
        pump(0.05)
        self.assertIn("Inserisci il nome (SSID) della rete Wi-Fi nascosta", self.win.lbl_wifi_status.text())

    # 7. Password-file generation sanitization and cleanup
    def test_passwd_file_content_and_cleanup(self):
        """Edge case: Temporary passwd-file contains canonical setting name and is cleaned up."""
        self.fake.connected = True
        self.fake.calls.clear()
        self.win.state["wifi_ssid"] = "TestNet"
        self.win.inp_wifi_pass.setText("p@ss:word\r\n")

        created_files = []
        orig_ntf = tempfile.NamedTemporaryFile

        def tracking_ntf(*args, **kwargs):
            tf = orig_ntf(*args, **kwargs)
            created_files.append(tf.name)
            return tf

        with unittest.mock.patch.object(wa.tempfile, "NamedTemporaryFile", side_effect=tracking_ntf):
            self.win._connect_wifi_and_check()
            deadline = time.time() + 20
            while self.win.wifi_worker.isRunning() and time.time() < deadline:
                APP.processEvents()
                time.sleep(0.01)
            pump(0.1)

        self.assertTrue(created_files, "NamedTemporaryFile must be created for WPA connection")
        for f in created_files:
            self.assertFalse(os.path.exists(f), f"passwd-file '{f}' must be unlinked in finally block")


def unittest_mock_patch(target, attr, value):
    from unittest import mock
    return mock.patch.object(target, attr, value)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WizardRegression)
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    # Use os._exit to cleanly exit without C++ global destructor races under armhf QEMU
    os._exit(0 if res.wasSuccessful() else 1)


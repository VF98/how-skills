import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PortableLauncherTests(unittest.TestCase):
    def invoke(self, folder):
        return subprocess.run([sys.executable, str(ROOT / "scripts/run.py"), "doctor"],
                              env={**os.environ, "XHS_LOCAL_DATA": folder},
                              text=True, capture_output=True, timeout=10)

    def test_fresh_install_uses_isolated_private_state_without_historical_account_proof(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.invoke(folder)
            self.assertEqual(result.returncode, 0, result.stderr)
            doctor = json.loads(result.stdout)
            self.assertEqual(doctor["browser_mode"], "isolated_headless")
            self.assertFalse(doctor["desktop_browser_operations_enabled"])
            self.assertFalse(doctor["native_drafts"]["live_verified"])
            self.assertNotIn("recorded_verification", doctor["native_drafts"])
            self.assertEqual({p.name for p in Path(folder).iterdir()}, {"browser-backend.json"})
            self.assertEqual((Path(folder) / "browser-backend.json").stat().st_mode & 0o777, 0o600)

    def test_existing_legacy_config_is_preserved_and_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "browser-backend.json"
            config.write_text('{"mode":"legacy_native"}')
            config.chmod(0o600)
            result = self.invoke(folder)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(config.read_text())["mode"], "legacy_native")
            self.assertEqual(json.loads(result.stdout)["error"], "backend_conflict")

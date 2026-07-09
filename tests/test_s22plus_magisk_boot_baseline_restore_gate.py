import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_magisk_boot_baseline_restore_gate.py")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_magisk_boot_baseline_restore_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_tar(path: Path, members: dict[str, bytes]) -> None:
    with tarfile.open(path, "w") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))


class S22PlusMagiskBootBaselineRestoreGateTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def configure_temp_magisk_ap(self, path: Path, payload: bytes = b"boot-lz4") -> None:
        write_tar(path, {self.module.EXPECTED_MAGISK_MEMBER: payload})
        self.module.EXPECTED_MAGISK_AP_SHA256 = sha256_file(path)
        self.module.EXPECTED_MAGISK_LZ4_SHA256 = hashlib.sha256(payload).hexdigest()

    def test_active_exception_template_contains_required_markers(self):
        template = self.module.active_exception_template()

        for marker in self.module.policy_required_markers():
            self.assertIn(marker, template)
        self.assertIn("boot partition only", template)
        self.assertIn("does not authorize recovery", template)

    def test_verify_agents_exception_accepts_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            agents = tmp_path / "AGENTS.md"
            agents.write_text(self.module.active_exception_template(), encoding="utf-8")
            log_path = tmp_path / "log.txt"

            self.module.verify_agents_exception(agents, log_path)

            self.assertIn("agents_exception=ok", log_path.read_text(encoding="utf-8"))

    def test_verify_agents_exception_rejects_missing_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            agents = tmp_path / "AGENTS.md"
            agents.write_text("S22+ Magisk boot-baseline restore boot-only gate\n", encoding="utf-8")

            with self.assertRaises(SystemExit):
                self.module.verify_agents_exception(agents, tmp_path / "log.txt")

    def test_verify_magisk_ap_accepts_single_matching_member(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ap = tmp_path / "AP.tar.md5"
            self.configure_temp_magisk_ap(ap)

            self.module.verify_magisk_ap(ap, tmp_path / "log.txt")

            log_text = (tmp_path / "log.txt").read_text(encoding="utf-8")
            self.assertIn("magisk_ap_sha256=", log_text)
            self.assertIn("magisk_member_sha256=", log_text)

    def test_verify_magisk_ap_rejects_extra_member(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ap = tmp_path / "AP.tar.md5"
            write_tar(ap, {self.module.EXPECTED_MAGISK_MEMBER: b"boot-lz4", "recovery.img.lz4": b"bad"})
            self.module.EXPECTED_MAGISK_AP_SHA256 = sha256_file(ap)

            with self.assertRaises(SystemExit):
                self.module.verify_magisk_ap(ap, tmp_path / "log.txt")

    def test_android_identity_errors_accepts_current_stock_state(self):
        errors = self.module.android_identity_errors(
            {
                "boot_completed": "1",
                "model": "SM-S906N",
                "device": "g0q",
                "incremental": "S906NKSS7FYG8",
                "vbstate": "orange",
            }
        )

        self.assertEqual(errors, [])

    def test_android_identity_errors_rejects_wrong_build_before_reboot(self):
        errors = self.module.android_identity_errors(
            {
                "boot_completed": "1",
                "model": "SM-S906N",
                "device": "g0q",
                "incremental": "S906NKSS7NOTFYG8",
                "vbstate": "orange",
            }
        )

        self.assertIn("incremental='S906NKSS7NOTFYG8' != 'S906NKSS7FYG8'", errors)

    def test_write_result_summary_redacts_android_serial(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            android = self.module.AndroidProof(
                serial="S22_TEST_SERIAL_123",
                root_path="/debug_ramdisk/su",
                boot_sha256=self.module.EXPECTED_MAGISK_BOOT_SHA256,
            )

            self.module.write_result_summary(
                tmp_path,
                tmp_path / "log.txt",
                result="magisk-baseline-restored",
                rc=0,
                android=android,
                rollback_device="/dev/bus/usb/001/002",
            )

            result = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
            result_text = json.dumps(result)
            self.assertEqual(result["android_serial"], self.module.DISPLAY_SERIAL_REDACTED)
            self.assertNotIn("S22_TEST_SERIAL_123", result_text)

    def test_main_offline_check_verifies_artifact_without_device(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ap = tmp_path / "AP.tar.md5"
            run_dir = tmp_path / "run"
            self.configure_temp_magisk_ap(ap)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                rc = self.module.main(["--magisk-ap", str(ap), "--run-dir", str(run_dir), "--offline-check"])

            self.assertEqual(rc, 0)
            self.assertIn("offline-check ok", stdout.getvalue())
            self.assertTrue((run_dir / "s22plus_magisk_boot_baseline_restore_gate.txt").is_file())


if __name__ == "__main__":
    unittest.main()

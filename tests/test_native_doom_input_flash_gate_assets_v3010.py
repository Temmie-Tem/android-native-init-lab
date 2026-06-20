"""Static checks for V3010 DOOM input flash-gate asset audit."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from _loader import load_script


runner = load_script("workspace/public/src/scripts/revalidation/native_doom_input_flash_gate_assets_v3010.py")


def complete_texts() -> dict[str, str]:
    return {
        "v3004": "\n".join([
            "v3004-doominput-keyboard-dry-run",
            "Candidate SHA256: `30e37c64196e7ff2649291c1398c67e96efea9313b25c51dade39d1c62c9ccc2`",
            "Preflight ok: `1`",
            "Live execution: `0`",
            "USB keyboard/OTG attached and DOOM keys pressed during the doominput window",
        ]),
        "v3007": "\n".join([
            "v3007-doom-keyboard-gate-hardware-stimulus-required",
            "A90 OTG keyboard evdev evidence: `0`",
            "V3004 live actionable now: `0`",
        ]),
        "v3008": "\n".join([
            "v3008-doom-input-frontier-keyboard-gate-still-external-stimulus",
            "USB keyboard live gate staged: `1`",
            "Active tier saturated without external stimulus: `1`",
            "native_doominput_keyboard_live_gate_v3004.py --live --count 32 --timeout-ms 60000",
        ]),
        "v3009": "\n".join([
            "frontier-selector-no-automatic-safe-unit",
            "VIDEO` / `doom-input",
            "external-hardware-stimulus-required",
            "native_doominput_keyboard_live_gate_v3004.py --live --count 32 --timeout-ms 60000",
        ]),
    }


class NativeDoomInputFlashGateAssetsV3010Tests(unittest.TestCase):
    def test_script_is_host_only_asset_audit(self) -> None:
        script = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn('RUN_ID = "V3010"', script)
        self.assertIn("host-only flash-gate asset audit", script)
        self.assertIn("native_init_flash.py", script)
        self.assertNotIn("subprocess.run", script)
        self.assertNotIn("a90ctl.py", script)
        self.assertNotIn("EVIOCGRAB", script)
        self.assertNotIn("O_WRONLY", script)
        self.assertNotIn("sendevent", script)

    def test_sha256_and_asset_audit_accept_matching_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root / "artifact.bin"
            payload.write_bytes(b"abc")
            spec = runner.AssetSpec("artifact", "artifact.bin", "test", runner.hashlib.sha256(b"abc").hexdigest())

            audited = runner.audit_asset(spec, root)

        self.assertTrue(audited["ok"])
        self.assertTrue(audited["sha256_ok"])
        self.assertEqual(audited["size_bytes"], 3)

    def test_asset_audit_rejects_missing_and_sha_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "artifact.bin").write_bytes(b"abc")
            mismatch = runner.AssetSpec("artifact", "artifact.bin", "test", "0" * 64)
            missing = runner.AssetSpec("missing", "missing.bin", "test")

            audited = runner.audit_assets(root, (mismatch, missing))

        self.assertFalse(audited["artifact"]["ok"])
        self.assertFalse(audited["artifact"]["sha256_ok"])
        self.assertFalse(audited["missing"]["ok"])
        self.assertFalse(audited["missing"]["exists"])

    def test_analyze_report_markers_classifies_current_hardware_wait(self) -> None:
        markers = runner.analyze_report_markers(complete_texts())

        self.assertTrue(markers["all_reports_ok"])
        self.assertTrue(markers["external_hardware_wait"])
        self.assertTrue(markers["per_report"]["v3004"]["ok"])

    def test_analyze_report_markers_rejects_live_ready_report(self) -> None:
        texts = complete_texts()
        texts["v3007"] = "v3007-doom-keyboard-gate-live-ready\nV3004 live actionable now: `1`"

        markers = runner.analyze_report_markers(texts)

        self.assertFalse(markers["all_reports_ok"])
        self.assertFalse(markers["external_hardware_wait"])
        self.assertFalse(markers["per_report"]["v3007"]["ok"])

    def test_classify_requires_assets_reports_and_external_wait(self) -> None:
        assets = {
            "candidate": {"required": True, "exists": True, "is_file": True, "expected_sha256": "a", "sha256_ok": True, "ok": True},
            "helper": {"required": True, "exists": True, "is_file": True, "expected_sha256": None, "sha256_ok": None, "ok": True},
        }
        markers = runner.analyze_report_markers(complete_texts())

        flags = runner.classify(assets, markers)

        self.assertEqual(flags["decision"], runner.DECISION_READY)
        self.assertTrue(flags["all_required_assets_ok"])
        self.assertTrue(flags["reports_ok"])
        self.assertFalse(flags["v3004_live_actionable_now"])
        self.assertIn("native_doominput_keyboard_live_gate_v3004.py --live", flags["next_live_command"])

    def test_classify_rejects_sha_mismatch(self) -> None:
        assets = {
            "candidate": {"required": True, "exists": True, "is_file": True, "expected_sha256": "a", "sha256_ok": False, "ok": False},
        }
        markers = runner.analyze_report_markers(complete_texts())

        flags = runner.classify(assets, markers)

        self.assertEqual(flags["decision"], runner.DECISION_INCOMPLETE)
        self.assertFalse(flags["all_expected_sha256_ok"])

    def test_render_report_records_command_and_safety(self) -> None:
        payload = {
            "assets": {
                "candidate": {
                    "kind": "boot-image-candidate",
                    "ok": True,
                    "sha256_ok": True,
                    "path": "workspace/private/inputs/boot_images/candidate.img",
                }
            },
            "reports": runner.analyze_report_markers(complete_texts()),
            "flags": runner.classify(
                {
                    "candidate": {
                        "required": True,
                        "exists": True,
                        "is_file": True,
                        "expected_sha256": "a",
                        "sha256_ok": True,
                        "ok": True,
                    }
                },
                runner.analyze_report_markers(complete_texts()),
            ),
        }

        report = runner.render_report(payload)

        self.assertIn("Native Init V3010 DOOM Input Flash Gate Assets", report)
        self.assertIn(runner.DECISION_READY, report)
        self.assertIn("Command when the external prerequisite is true", report)
        self.assertIn("no flash", report)
        self.assertIn("checked flash helper is only treated as an audited file path", report)


if __name__ == "__main__":
    unittest.main()

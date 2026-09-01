import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_p0_twrp_boot_owner_h0.py"
)
PRIVATE_TMP = ROOT / "workspace/private/tmp"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s20plus_g986n_p0_twrp_boot_owner_h0_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S20PlusP0TwrpBootOwnerH0Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.plan = cls.module.render_plan()

    def test_plan_is_dormant_exact_target_and_commandless(self):
        self.assertFalse(self.plan["active"])
        self.assertFalse(self.plan["live_authority"])
        self.assertEqual(
            self.plan["status"], "H0_DESIGN_PASS_GO_NOT_ACTIVE"
        )
        self.assertEqual(
            self.plan["binding"]["target"],
            {
                "model": "SM-G986N",
                "device": "y2q",
                "product": "y2qksx",
                "build": "G986NKSS8IYC2",
            },
        )
        self.assertEqual(self.plan["device_commands"], [])
        self.assertEqual(self.plan["device_writes"], [])
        self.assertEqual(self.plan["partition_transfers"], [])

    def test_binding_is_deterministic_and_pins_complete_h0_closure(self):
        first = self.module.binding_value()
        second = self.module.binding_value()
        self.assertEqual(first, second)
        self.assertEqual(self.module.digest(first), self.plan["binding_sha256"])
        closure = first["closure"]
        self.assertEqual(
            set(closure),
            set(self.module.PUBLIC_CLOSURE)
            | {
                "candidate_manifest",
                "candidate_boot",
                "resident_rollback_boot",
                "resident_rollback_ap",
                "t2_retained_terminal",
            },
        )
        for name, expected in self.module.PUBLIC_CLOSURE.items():
            self.assertEqual(closure[name]["size"], expected["size"])
            self.assertEqual(closure[name]["sha256"], expected["sha256"])

    def test_candidate_and_rollback_are_distinct_exact_raw_boots(self):
        binding = self.plan["binding"]
        candidate = binding["candidate"]
        rollback = binding["rollback"]
        self.assertEqual(candidate["boot_size"], 67_108_864)
        self.assertEqual(rollback["boot_size"], 67_108_864)
        self.assertEqual(
            candidate["boot_sha256"], self.module.CANDIDATE_BOOT_SHA256
        )
        self.assertEqual(
            rollback["boot_sha256"], self.module.ROLLBACK_BOOT_SHA256
        )
        self.assertNotEqual(candidate["boot_sha256"], rollback["boot_sha256"])
        self.assertEqual(candidate["first_runtime_syscall"], "getpid")
        self.assertEqual(candidate["accepted_pid"], 1)
        self.assertFalse(candidate["replay_permitted"])
        self.assertTrue(rollback["mandatory_after_candidate_intent"])
        self.assertFalse(rollback["replay_permitted"])

    def test_retained_t2_is_prerequisite_not_replay_or_ui_authority(self):
        recovery = self.plan["binding"]["starting_recovery"]
        receipt = self.plan["binding"]["closure"]["t2_retained_terminal"]
        self.assertEqual(recovery["proof"], "PROVED_T2_RECOVERY_RETAINED")
        self.assertTrue(recovery["candidate_consumed"])
        self.assertFalse(recovery["new_t2_transfer_permitted"])
        self.assertFalse(
            recovery["ui_mount_format_install_backup_restore_terminal_authority"]
        )
        self.assertEqual(receipt["sha256"], self.module.T2_TERMINAL_SHA256)
        self.assertEqual(receipt["twrp_version"], self.module.T2_VERSION)
        self.assertEqual(receipt["usb_config"], "mtp,adb")

    def test_effect_budget_is_boot_only_one_shot_and_physical(self):
        budget = self.plan["effect_budget"]
        self.assertEqual(budget["candidate_boot_partition_writes"], 1)
        self.assertEqual(budget["candidate_readbacks"], 1)
        self.assertEqual(budget["rollback_boot_partition_writes"], 1)
        self.assertEqual(budget["rollback_readbacks"], 1)
        self.assertFalse(budget["candidate_replay"])
        self.assertFalse(budget["rollback_replay"])
        for key in (
            "recovery_partition_writes",
            "misc_writes",
            "userdata_formats",
            "other_partition_writes",
        ):
            self.assertEqual(budget[key], 0, key)
        machine = self.plan["state_machine"]
        self.assertIn(
            "future-attended-physical-system-boot-without-twrp-system-hook",
            machine,
        )
        self.assertIn(
            "future-attended-physical-return-to-t2-recovery", machine
        )

    def test_all_missing_live_components_are_explicit_blockers(self):
        blockers = self.plan["activation_blockers"]
        self.assertEqual(len(blockers), 7)
        for blocker in blockers:
            self.assertEqual(
                set(blocker),
                {"id", "hazard", "scope", "retire_when", "review_trigger"},
            )
            self.assertTrue(all(blocker.values()))
        rendered_blockers = json.dumps(blockers, sort_keys=True)
        for token in (
            "exact-boot-identity",
            "fixed-twrp-backend",
            "durable-journal",
            "contract-activation",
            "independent-review",
            "fresh-run-binding",
        ):
            self.assertIn(token, rendered_blockers)
        qualification = self.plan["binding"]["prior_transfer_qualification"]
        self.assertTrue(qualification["required"])
        self.assertFalse(qualification["proved"])
        self.assertFalse(qualification["part_of_p0_candidate_attempt"])
        self.assertTrue(
            qualification["physical_no_hook_system_and_direct_recovery_required"]
        )
        forbidden = self.plan["forbidden_even_after_future_activation"]
        for value in (
            "twrp-rebootsystem-hook",
            "misc-bcb-write",
            "recovery-partition-write",
            "candidate-replay",
            "rollback-replay",
            "other-device-command",
        ):
            self.assertIn(value, forbidden)

    def test_typed_or_semantically_mutated_t2_terminal_rejects(self):
        original = json.loads(self.module.T2_TERMINAL.read_text(encoding="utf-8"))
        mutations = (
            {**original, "candidate_retained": 1},
            {**original, "candidate_attempts": True},
            {**original, "candidate_replay_permitted": True},
            {**original, "verdict": "PROVED_T2_RECOVERY_RETAINED_FORGED"},
        )
        with tempfile.TemporaryDirectory(
            prefix="s20plus-p0-owner-terminal-", dir=PRIVATE_TMP
        ) as temporary:
            for index, value in enumerate(mutations):
                path = Path(temporary) / f"terminal-{index}.json"
                payload = json.dumps(value, separators=(",", ":")).encode()
                path.write_bytes(payload)
                with (
                    mock.patch.object(self.module, "T2_TERMINAL", path),
                    mock.patch.object(
                        self.module, "T2_TERMINAL_SIZE", len(payload)
                    ),
                    mock.patch.object(
                        self.module,
                        "T2_TERMINAL_SHA256",
                        hashlib.sha256(payload).hexdigest(),
                    ),
                ):
                    with self.assertRaises(self.module.OwnerDesignError):
                        self.module.validate_t2_terminal()

    def test_duplicate_key_and_semantically_mutated_manifest_reject(self):
        with self.assertRaisesRegex(self.module.OwnerDesignError, "duplicate"):
            self.module.strict_json(b'{"x":1,"x":1}', "duplicate")
        original = json.loads(
            self.module.CANDIDATE_MANIFEST.read_text(encoding="utf-8")
        )
        original["review_state"] = "PASS_GO"
        payload = json.dumps(original, separators=(",", ":")).encode()
        with tempfile.TemporaryDirectory(
            prefix="s20plus-p0-owner-manifest-", dir=PRIVATE_TMP
        ) as temporary:
            path = Path(temporary) / "manifest.json"
            path.write_bytes(payload)
            with (
                mock.patch.object(self.module, "CANDIDATE_MANIFEST", path),
                mock.patch.object(
                    self.module, "CANDIDATE_MANIFEST_SIZE", len(payload)
                ),
                mock.patch.object(
                    self.module,
                    "CANDIDATE_MANIFEST_SHA256",
                    hashlib.sha256(payload).hexdigest(),
                ),
            ):
                with self.assertRaisesRegex(
                    self.module.OwnerDesignError, "review_state"
                ):
                    self.module.validate_candidate_manifest()

    def test_indirect_hardlinked_or_hash_drift_artifact_rejects(self):
        with tempfile.TemporaryDirectory(
            prefix="s20plus-p0-owner-artifact-", dir=PRIVATE_TMP
        ) as temporary:
            root = Path(temporary)
            first = root / "first"
            second = root / "second"
            link = root / "link"
            first.write_bytes(b"x")
            os.link(first, second)
            link.symlink_to(first)
            common = {
                "expected_size": 1,
                "expected_sha256": hashlib.sha256(b"x").hexdigest(),
                "maximum": 1,
                "label": "hostile artifact",
            }
            for path in (first, link):
                with self.assertRaises(self.module.OwnerDesignError):
                    self.module.read_exact_regular(path, **common)
            second.unlink()
            with self.assertRaisesRegex(self.module.OwnerDesignError, "hash"):
                self.module.read_exact_regular(
                    first,
                    **{**common, "expected_sha256": "0" * 64},
                )

    def test_cli_only_renders_plan_and_has_no_execution_surface(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--render-plan"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=10,
            text=True,
        )
        rendered = json.loads(completed.stdout)
        self.assertEqual(rendered["binding_sha256"], self.plan["binding_sha256"])
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "import subprocess",
            "os.system",
            "Popen(",
            "--prepare",
            "--execute",
            "--approval",
            "OWNER_ACTIVE = True",
            "adb shell",
            "su -c",
            "dd if=",
        ):
            self.assertNotIn(forbidden, source)
        with mock.patch.object(
            self.module,
            "validate_closure",
            side_effect=AssertionError("invalid CLI must stop before closure"),
        ):
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                with mock.patch.object(sys, "argv", [str(SCRIPT)]):
                    self.module.main()


if __name__ == "__main__":
    unittest.main()

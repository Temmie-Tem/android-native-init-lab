from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_twrp_identical_resident_q0_owner_h0.py"
)
SCRIPT_DIR = SCRIPT.parent
PRIVATE_TMP = ROOT / "workspace/private/tmp"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s20plus_g986n_twrp_identical_resident_q0_owner_h0_tested",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S20PlusTwrpIdenticalResidentQ0OwnerH0Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.plan = cls.module.render_plan()

    def test_owner_is_dormant_render_only_and_exact_target(self):
        self.assertFalse(self.plan["active"])
        self.assertFalse(self.plan["live_authority"])
        self.assertEqual(
            self.plan["status"], "H0_PASS_GO_NOT_ACTIVE"
        )
        self.assertEqual(self.plan["binding"]["target"], self.module.TARGET)
        self.assertEqual(self.plan["device_commands"], [])
        self.assertEqual(self.plan["device_writes"], [])
        self.assertEqual(self.plan["partition_transfers"], [])

    def test_binding_is_deterministic_and_private_identifiers_are_not_exposed(self):
        first = self.module.binding_value()
        second = self.module.binding_value()
        self.assertEqual(first, second)
        self.assertEqual(self.module.digest(first), self.plan["binding_sha256"])
        rendered = json.dumps(self.plan, sort_keys=True)
        for forbidden in (
            "serial_sha256",
            "topology_sha256",
            "current_boot_id_sha256",
            "predecessor_boot_id_sha256",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_d0_proof_is_metadata_only_and_never_inherited_as_write_authority(self):
        result = self.plan["binding"]["closure"]["metadata_d0_result"]
        self.assertEqual(
            result["verdict"],
            "PROVED_S20PLUS_G986N_TWRP_BOOT_IDENTITY_METADATA",
        )
        self.assertEqual(result["direct_path"], "/dev/block/sda23")
        self.assertEqual(result["rdev"], "259:7")
        self.assertEqual(result["partname"], "boot")
        self.assertEqual(result["partition_number"], 23)
        self.assertEqual(result["size_bytes"], 67_108_864)
        self.assertTrue(result["same_retained_recovery_boot"])
        self.assertFalse(result["f1_authorized"])
        self.assertFalse(result["direct_block_write_authorized"])

    def test_backend_resident_and_download_fallback_are_exact(self):
        closure = self.plan["binding"]["closure"]
        self.assertEqual(closure["backend"]["size"], self.module.BACKEND_SIZE)
        self.assertEqual(closure["backend"]["sha256"], self.module.BACKEND_SHA256)
        self.assertEqual(
            closure["backend_manifest"]["sha256"],
            self.module.BACKEND_MANIFEST_SHA256,
        )
        self.assertFalse(closure["backend_manifest"]["live_authority"])
        self.assertEqual(
            closure["resident_boot"]["sha256"], self.module.RESIDENT_BOOT_SHA256
        )
        fallback = closure["download_odin_fallback"]
        self.assertEqual(fallback["sha256"], self.module.p0.ROLLBACK_AP_SHA256)
        self.assertEqual(fallback["member"]["name"], "boot.img.lz4")

    def test_retained_t2_is_consumed_prerequisite_not_new_transfer_authority(self):
        retained = self.plan["binding"]["closure"]["retained_t2"]
        self.assertEqual(retained["journal_node_count"], 43)
        self.assertTrue(retained["candidate_consumed"])
        self.assertFalse(retained["candidate_replay_permitted"])
        self.assertFalse(retained["new_t2_transfer_authority"])
        self.assertEqual(
            retained["terminal_sha256"], self.module.T2_TERMINAL_SHA256
        )

    def test_h0_evidence_model_is_bound_but_not_integrated_or_live(self):
        evidence = self.plan["binding"]["closure"]["q0_evidence_model_plan"]
        self.assertTrue(evidence["strict_backend_parser"])
        self.assertTrue(evidence["canonical_journal_prefix_validator"])
        self.assertTrue(evidence["write_intent_consumes_attempt_without_result"])
        self.assertFalse(evidence["backend_replay_permitted"])
        self.assertFalse(evidence["system_boot_authorized"])
        self.assertFalse(evidence["durable_publisher_implemented"])
        self.assertFalse(evidence["connected_owner_implemented"])
        closure = self.plan["binding"]["closure"]
        self.assertEqual(
            closure["q0_evidence_model"]["sha256"],
            self.module.PUBLIC_CLOSURE["q0_evidence_model"]["sha256"],
        )
        self.assertEqual(
            closure["q0_evidence_test"]["sha256"],
            self.module.PUBLIC_CLOSURE["q0_evidence_test"]["sha256"],
        )

    def test_proposed_effect_budget_is_one_boot_write_and_no_other_partition(self):
        budget = self.plan["binding"]["proposed_effect_budget"]
        self.assertEqual(budget["boot_partition_content_reads"], 2)
        self.assertEqual(budget["boot_partition_write_attempts"], 1)
        self.assertEqual(budget["boot_partition_write_bytes"], 67_108_864)
        self.assertEqual(budget["fsync_attempts"], 1)
        self.assertEqual(budget["physical_system_boots"], 1)
        self.assertEqual(budget["physical_direct_recovery_returns"], 1)
        self.assertFalse(budget["replay"])
        for key in ("recovery_partition_writes", "misc_writes", "other_partition_writes"):
            self.assertEqual(budget[key], 0, key)

    def test_interruption_and_health_failures_never_authorize_replay(self):
        rules = self.plan["binding"]["failure_rules"]
        self.assertIn("attempt consumed", rules["after_write_intent_without_proved_result"])
        self.assertIn("never invoke backend again", rules["after_write_intent_without_proved_result"])
        self.assertIn("no backend replay", rules["proved_readback_but_android_health_absent"])
        qualification = self.plan["binding"]["qualification"]
        self.assertFalse(qualification["torn_identical_write_safe"])
        self.assertFalse(qualification["candidate_is_p0"])
        self.assertFalse(qualification["retires_p0_candidate_attempt"])

    def test_every_missing_live_component_remains_an_explicit_blocker(self):
        blockers = self.plan["binding"]["activation_blockers"]
        self.assertEqual(len(blockers), 8)
        rendered = "\n".join(blockers)
        for token in (
            "stdout/failure parser",
            "intent-before-effect journal",
            "staging",
            "physical no-hook",
            "Download/Odin",
            "not active",
            "independent PASS_GO",
            "fresh attended",
        ):
            self.assertIn(token, rendered)

    def test_d0_typed_geometry_authority_and_count_mutations_reject(self):
        original = json.loads(self.module.D0_RESULT.read_text(encoding="utf-8"))
        variants = []
        value = json.loads(json.dumps(original))
        value["boot_partition"]["rdev_minor"] = 8
        variants.append(value)
        value = json.loads(json.dumps(original))
        value["direct_block_write_authorized"] = True
        variants.append(value)
        value = json.loads(json.dumps(original))
        value["host_command_count"] = True
        variants.append(value)
        value = json.loads(json.dumps(original))
        value["recovery"]["serial_sha256"] = 1
        variants.append(value)
        with tempfile.TemporaryDirectory(
            prefix="s20plus-q0-d0-mutation-", dir=PRIVATE_TMP
        ) as temporary:
            for index, value in enumerate(variants):
                path = Path(temporary) / f"result-{index}.json"
                payload = json.dumps(value, separators=(",", ":")).encode()
                path.write_bytes(payload)
                with (
                    mock.patch.object(self.module, "D0_RESULT", path),
                    mock.patch.object(self.module, "D0_RESULT_SIZE", len(payload)),
                    mock.patch.object(
                        self.module,
                        "D0_RESULT_SHA256",
                        hashlib.sha256(payload).hexdigest(),
                    ),
                ):
                    with self.assertRaises(self.module.OwnerError):
                        self.module.validate_d0_result()

    def test_backend_manifest_activation_path_and_safety_mutations_reject(self):
        original = json.loads(
            self.module.BACKEND_MANIFEST.read_text(encoding="utf-8")
        )
        variants = []
        value = json.loads(json.dumps(original))
        value["live_authority"] = True
        variants.append(value)
        value = json.loads(json.dumps(original))
        value["runtime_binding"]["target_path"] = "/dev/block/sda24"
        variants.append(value)
        value = json.loads(json.dumps(original))
        value["safety"]["interrupted_write_recoverable_only_not_safe"] = False
        variants.append(value)
        with tempfile.TemporaryDirectory(
            prefix="s20plus-q0-manifest-mutation-", dir=PRIVATE_TMP
        ) as temporary:
            for index, value in enumerate(variants):
                path = Path(temporary) / f"manifest-{index}.json"
                payload = json.dumps(value, separators=(",", ":")).encode()
                path.write_bytes(payload)
                with (
                    mock.patch.object(self.module, "BACKEND_MANIFEST", path),
                    mock.patch.object(
                        self.module, "BACKEND_MANIFEST_SIZE", len(payload)
                    ),
                    mock.patch.object(
                        self.module,
                        "BACKEND_MANIFEST_SHA256",
                        hashlib.sha256(payload).hexdigest(),
                    ),
                ):
                    with self.assertRaises(self.module.OwnerError):
                        self.module.validate_backend_manifest()

    def test_target_contract_activation_or_indirect_file_rejects(self):
        original = self.module.TARGET_CONTRACT.read_text(encoding="utf-8")
        activated = original.replace(
            "Status: **DEFINED - H0 ONLY - NOT ACTIVE**",
            "Status: **BINDING - ACTIVE**",
            1,
        )
        with tempfile.TemporaryDirectory(
            prefix="s20plus-q0-contract-mutation-", dir=PRIVATE_TMP
        ) as temporary:
            root = Path(temporary)
            direct = root / "contract.md"
            direct.write_text(activated, encoding="utf-8")
            link = root / "contract-link.md"
            link.symlink_to(direct)
            with mock.patch.object(self.module, "TARGET_CONTRACT", direct):
                with self.assertRaises(self.module.OwnerError):
                    self.module.validate_target_contract()
            with mock.patch.object(self.module, "TARGET_CONTRACT", link):
                with self.assertRaises(self.module.OwnerError):
                    self.module.validate_target_contract()

    def test_duplicate_json_and_indirect_hardlinked_artifact_reject(self):
        with self.assertRaisesRegex(self.module.OwnerError, "duplicate"):
            self.module.strict_json(b'{"x":1,"x":1}', "duplicate")
        with tempfile.TemporaryDirectory(
            prefix="s20plus-q0-indirect-", dir=PRIVATE_TMP
        ) as temporary:
            root = Path(temporary)
            first = root / "first"
            second = root / "second"
            first.write_bytes(b"x")
            os.link(first, second)
            with self.assertRaises(self.module.OwnerError):
                self.module.read_exact_regular(
                    first,
                    expected_size=1,
                    expected_sha256=hashlib.sha256(b"x").hexdigest(),
                    maximum=1,
                    label="hardlink",
                )

    def test_cli_only_renders_and_has_no_connected_surface(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--render-plan"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=15,
            text=True,
        )
        rendered = json.loads(completed.stdout)
        self.assertEqual(rendered["binding_sha256"], self.plan["binding_sha256"])
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "import subprocess",
            "Popen(",
            "os.system",
            "--connected",
            "--prepare",
            "--execute",
            "--approval",
            "Q0_ACTIVE = True",
            "adb shell",
            "odin4",
        ):
            self.assertNotIn(forbidden, source)
        with mock.patch.object(
            self.module,
            "validate_closure",
            side_effect=AssertionError("invalid CLI must not validate closure"),
        ):
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                with mock.patch.object(sys, "argv", [str(SCRIPT)]):
                    self.module.main()


if __name__ == "__main__":
    unittest.main()

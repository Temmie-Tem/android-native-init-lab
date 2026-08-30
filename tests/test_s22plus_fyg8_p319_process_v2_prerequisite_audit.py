from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_process_v2_prerequisite_audit.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_p319_process_v2_prerequisite_audit_tested", SCRIPT
    )
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load P3.19 prerequisite auditor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P319ProcessV2PrerequisiteAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.receipt = cls.module.build_receipt()

    def test_registry_capability_and_runner_consumption_are_separate_from_readiness(self):
        self.assertEqual(self.receipt["verdict"], self.module.VERDICT)
        self.assertEqual(self.receipt["status"], self.module.VERDICT)
        admission = self.receipt["no_replay"]
        self.assertTrue(
            admission["new_live_run_id_absent_from_consumed_population"]
        )
        self.assertTrue(
            admission["candidate_pair_absent_from_consumed_population"]
        )
        self.assertTrue(admission["ready_manifest_is_nonconsuming_declaration"])
        self.assertTrue(admission["observation_and_consumption_namespaces_distinct"])
        self.assertEqual(
            admission["carrier_observation_run_id"],
            self.module.CARRIER_OBSERVATION_RUN_ID,
        )
        self.assertEqual(
            admission["process_live_run_id"], self.module.NEW_LIVE_RUN_ID
        )
        self.assertEqual(admission["candidate_ap"]["sha256"], self.module.CANDIDATE_AP_SHA256)
        self.assertEqual(admission["candidate_ap"]["single_member"], "boot.img.lz4")
        registry = admission["global_consumed_run_registry"]
        self.assertTrue(registry["capability_authoritative"])
        self.assertTrue(registry["runner_registry_consumption_proved"])
        self.assertFalse(registry["runner_recovery_closed"])
        self.assertFalse(registry["runner_ready"])
        self.assertIsNone(self.receipt["global_registry_blocker"])

    def test_ready_manifest_is_classified_as_declaration_not_consumption(self):
        self.module._validate_nonconsuming_ready_manifest()  # noqa: SLF001
        with tempfile.TemporaryDirectory(prefix="p319-ready-declaration-") as name:
            path = Path(name) / "ready.json"
            value = json.loads(self.module.P319_READY_MANIFEST.read_bytes())
            path.write_text(
                json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="ascii",
            )
            path.chmod(0o644)
            self.module._validate_nonconsuming_ready_manifest(path)  # noqa: SLF001
            path.chmod(0o664)
            self.module._validate_nonconsuming_ready_manifest(path)  # noqa: SLF001
            path.chmod(0o666)
            with self.assertRaisesRegex(
                self.module.AuditError, "public checkout mode differs"
            ):
                self.module._validate_nonconsuming_ready_manifest(path)  # noqa: SLF001
            value["status"] = "approved"
            path.write_text(
                json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="ascii",
            )
            path.chmod(0o644)
            with self.assertRaisesRegex(
                self.module.AuditError, "ready declaration identity differs"
            ):
                self.module._validate_nonconsuming_ready_manifest(path)  # noqa: SLF001

    def test_ready_declaration_rejects_acceptance_and_artifact_drift(self):
        original = json.loads(self.module.P319_READY_MANIFEST.read_bytes())
        mutations = {
            "decoder": lambda value: value["observation"]["acceptance"].__setitem__(
                "decoder", "foreign"
            ),
            "policy": lambda value: value["observation"]["acceptance"].__setitem__(
                "policy_id", "0" * 32
            ),
            "family": lambda value: value["observation"]["acceptance"].__setitem__(
                "long_family_hex", "00"
            ),
            "terminal": lambda value: value["observation"]["acceptance"].__setitem__(
                "terminal_stage", 146
            ),
            "terminal_float": lambda value: value["observation"]["acceptance"].__setitem__(
                "terminal_stage", 147.0
            ),
            "minimum": lambda value: value["observation"]["acceptance"].__setitem__(
                "minimum_success_count", 2
            ),
            "minimum_bool": lambda value: value["observation"]["acceptance"].__setitem__(
                "minimum_success_count", True
            ),
            "minimum_float": lambda value: value["observation"]["acceptance"].__setitem__(
                "minimum_success_count", 1.0
            ),
            "baseline": lambda value: value["observation"]["acceptance"].__setitem__(
                "clean_baseline_required", False
            ),
            "timeout": lambda value: value["observation"].__setitem__(
                "timeout_sec", 601
            ),
            "timeout_float": lambda value: value["observation"].__setitem__(
                "timeout_sec", 300.0
            ),
            "candidate_size_float": lambda value: value["candidate_ap"].__setitem__(
                "size", 27_279_401.0
            ),
            "rollback_size_float": lambda value: value["rollback_ap"].__setitem__(
                "size", 23_367_721.0
            ),
            "digest": lambda value: value["observation"]["acceptance"]["contract"][
                "candidate_static"
            ].__setitem__("sha256", "0" * 64),
        }
        with tempfile.TemporaryDirectory(prefix="p319-ready-hostile-") as name:
            for label, mutate in mutations.items():
                with self.subTest(label=label):
                    value = json.loads(json.dumps(original))
                    mutate(value)
                    path = Path(name) / f"{label}.json"
                    path.write_text(
                        json.dumps(value, sort_keys=True, separators=(",", ":"))
                        + "\n",
                        encoding="ascii",
                    )
                    path.chmod(0o644)
                    with self.assertRaises(self.module.AuditError):
                        self.module._validate_nonconsuming_ready_manifest(path)  # noqa: SLF001

    def test_exact_pre_effect_prepared_record_is_nonconsuming_only(self):
        with tempfile.TemporaryDirectory(prefix="p319-prepared-nonconsuming-") as name:
            private_runs = Path(name) / "workspace/private/runs"
            run_dir = private_runs / "device-action-f1-live-v2/fixture-run"
            preflight = run_dir / "preflight"
            preflight.mkdir(parents=True)

            def write_private(path, payload):
                path.write_bytes(payload)
                path.chmod(0o400)
                return {
                    "path": str(path.absolute()),
                    "size": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }

            d0_receipt = write_private(preflight / "result.json", b"{}\n")
            target_receipt = write_private(run_dir / "target-private.json", b"{}\n")
            trace_receipt = write_private(
                run_dir / "p300-usb-trace-binding.json", b"{}\n"
            )
            base = {
                "schema": "device_action_f1_approval_binding_v2",
                "bundle_sha256": "1" * 64,
                "candidate_ap_sha256": self.module.CANDIDATE_AP_SHA256,
                "manifest_id": "s22plus-fyg8-p319-process-v2-ready-1",
                "observation": {},
                "profile_id": "s22plus-fyg8",
                "rollback_ap_sha256": (
                    "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56"
                ),
                "rollback_preapproved": True,
                "runner_version": "device-action-f1-v2-host-core-3",
                "target_evidence_sha256": "2" * 64,
            }
            closure = {
                "repo_root": str(self.module.ROOT),
                "schema": "device_action_f1_execution_closure_v2",
                "sha256": "3" * 64,
                "sources": {},
            }
            binding = {
                "schema": "device_action_f1_live_approval_binding_v2",
                "adapter_version": "device-action-f1-live-v2-8",
                "base_binding": base,
                "base_binding_sha256": self.module._canonical_digest(base),  # noqa: SLF001
                "d0_result": d0_receipt,
                "private_target": target_receipt,
                "execution_closure_sha256": closure["sha256"],
                "mandatory_rollback_preapproved": True,
                "recovery_requires_second_approval": False,
            }
            binding_sha256 = self.module._canonical_digest(binding)  # noqa: SLF001
            prepared = {
                "schema": "device_action_f1_prepared_v2",
                "adapter_version": "device-action-f1-live-v2-8",
                "manifest_id": "s22plus-fyg8-p319-process-v2-ready-1",
                "bundle_sha256": "1" * 64,
                "manifest_status": "ready-for-f1-approval",
                "d0_result": d0_receipt,
                "private_target": target_receipt,
                "execution_closure": closure,
                "approval_binding": binding,
                "approval_binding_sha256": binding_sha256,
                "approval_token": "DEVICE-ACTION-F1-V2-APPROVE:" + binding_sha256,
                "p300_usb_trace_binding": trace_receipt,
                "device_contact": True,
                "device_writes": False,
                "reboot_requested": False,
                "odin_invoked": False,
                "partition_transfer": False,
                "f1_authorized": False,
                "live_authorized": False,
            }
            path = run_dir / "prepared.json"
            path.write_text(json.dumps(prepared), encoding="utf-8")
            path.chmod(0o400)
            ready = {"observation": base["observation"]}
            schema = (
                "device_action_f1_prepared_v2",
                "device-action-f1-live-v2-8",
                self.module.PREPARED_KEYS,
            )
            with (
                mock.patch.object(self.module, "PRIVATE_RUNS", private_runs),
                mock.patch.object(
                    self.module,
                    "_current_live_prepared_schema",
                    return_value=schema,
                ),
                mock.patch.object(
                    self.module,
                    "_current_execution_closure",
                    return_value=closure,
                ),
                mock.patch.object(
                    self.module,
                    "_validate_nonconsuming_ready_manifest",
                    return_value=ready,
                ),
            ):
                parsed, parsed_receipt = self.module._strict_json(  # noqa: SLF001
                    path, "prepared fixture", mode=0o400
                )
                self.module._validate_nonconsuming_prepared_record(  # noqa: SLF001
                    path, parsed, parsed_receipt
                )
                forged = dict(prepared)
                forged["f1_authorized"] = True
                with self.assertRaisesRegex(
                    self.module.AuditError, "prepared record identity differs"
                ):
                    self.module._validate_nonconsuming_prepared_record(  # noqa: SLF001
                        path, forged
                    )
                missing_trace = dict(prepared)
                missing_trace["p300_usb_trace_binding"] = None
                with self.assertRaisesRegex(
                    self.module.AuditError, "USB trace binding receipt is absent"
                ):
                    self.module._validate_nonconsuming_prepared_record(  # noqa: SLF001
                        path, missing_trace
                    )
                for unexpected in (
                    "transaction",
                    "f1-session",
                    "odin-endpoints",
                    "p300-candidate-observation-durable.json",
                    "weird.json",
                ):
                    extra = run_dir / unexpected
                    if "." in unexpected:
                        extra.write_text("{}\n", encoding="utf-8")
                    else:
                        extra.mkdir()
                    with self.assertRaisesRegex(
                        self.module.AuditError, "unexpected run children"
                    ):
                        self.module._validate_nonconsuming_prepared_record(  # noqa: SLF001
                            path, prepared
                        )
                    if extra.is_dir():
                        extra.rmdir()
                    else:
                        extra.unlink()

                wrong_version = dict(prepared)
                wrong_version["adapter_version"] = "device-action-f1-live-v2-9"
                with self.assertRaisesRegex(
                    self.module.AuditError, "prepared record identity differs"
                ):
                    self.module._validate_nonconsuming_prepared_record(  # noqa: SLF001
                        path, wrong_version
                    )

                wrong_observation = json.loads(json.dumps(prepared))
                wrong_observation["approval_binding"]["base_binding"][
                    "observation"
                ] = {"forged": True}
                wrong_observation["approval_binding"]["base_binding_sha256"] = (
                    self.module._canonical_digest(  # noqa: SLF001
                        wrong_observation["approval_binding"]["base_binding"]
                    )
                )
                wrong_observation["approval_binding_sha256"] = (
                    self.module._canonical_digest(  # noqa: SLF001
                        wrong_observation["approval_binding"]
                    )
                )
                wrong_observation["approval_token"] = (
                    "DEVICE-ACTION-F1-V2-APPROVE:"
                    + wrong_observation["approval_binding_sha256"]
                )
                with self.assertRaisesRegex(
                    self.module.AuditError, "prepared record identity differs"
                ):
                    self.module._validate_nonconsuming_prepared_record(  # noqa: SLF001
                        path, wrong_observation
                    )

                wrong_closure = json.loads(json.dumps(prepared))
                wrong_closure["execution_closure"]["sources"] = {
                    "forged": {"path": "/tmp/forged", "size": 1, "sha256": "0" * 64}
                }
                wrong_closure["execution_closure"]["sha256"] = (
                    self.module._canonical_digest(  # noqa: SLF001
                        wrong_closure["execution_closure"]["sources"]
                    )
                )
                wrong_closure["approval_binding"]["execution_closure_sha256"] = (
                    wrong_closure["execution_closure"]["sha256"]
                )
                wrong_closure["approval_binding_sha256"] = (
                    self.module._canonical_digest(  # noqa: SLF001
                        wrong_closure["approval_binding"]
                    )
                )
                wrong_closure["approval_token"] = (
                    "DEVICE-ACTION-F1-V2-APPROVE:"
                    + wrong_closure["approval_binding_sha256"]
                )
                with self.assertRaisesRegex(
                    self.module.AuditError, "prepared record identity differs"
                ):
                    self.module._validate_nonconsuming_prepared_record(  # noqa: SLF001
                        path, wrong_closure
                    )

                replacement = dict(prepared)
                replacement["bundle_sha256"] = "9" * 64
                path.unlink()
                path.write_text(json.dumps(replacement), encoding="utf-8")
                path.chmod(0o400)
                with self.assertRaisesRegex(
                    self.module.AuditError, "prepared record identity differs"
                ):
                    self.module._validate_nonconsuming_prepared_record(  # noqa: SLF001
                        path, parsed, parsed_receipt
                    )

    def test_recovery_provenance_is_distinct_from_reopening_ap(self):
        recovery = self.receipt["recovery_usability_provenance"]
        self.assertTrue(recovery["demonstrated_download_path"])
        self.assertTrue(recovery["rollback_bound_exact"])
        self.assertTrue(recovery["final_healthy_closed"])
        self.assertEqual(recovery["classification"], "odin_transfer_completed")
        self.assertEqual(recovery["transport"]["attempts"], 1)
        self.assertTrue(recovery["transport"]["attempt_2_absent"])
        self.assertEqual(
            recovery["artifact"]["sha256"],
            "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
        )
        self.assertEqual(recovery["artifact"]["single_member"], "boot.img.lz4")
        self.assertEqual(recovery["journal"]["record_count"], 19)
        self.assertEqual(recovery["journal"]["state"], "CLOSED")
        self.assertEqual(len(recovery["journal"]["records_0010_0018"]), 9)
        self.assertEqual(recovery["topology"]["authority_state"], "rollback_bound_exact")

    def test_active_global_registry_claim_is_not_reported_absent(self):
        class ClaimedRegistry:
            @staticmethod
            def history(_root):
                return [
                    {
                        "event": "claim",
                        "candidate_key": "1" * 64,
                        "candidate_ap_sha256": self.module.CANDIDATE_AP_SHA256,
                    }
                ]

        with self.assertRaisesRegex(
            self.module.AuditError, "active global registry claim"
        ):
            self.module._assert_candidate_absent_from_registry(  # noqa: SLF001
                ClaimedRegistry
            )
    def test_restart_probe_uses_two_durable_attempts_then_rejects(self):
        restart = self.receipt["restart_durability"]
        self.assertEqual(restart["helper"]["size"], 2974)
        self.assertEqual(
            restart["helper"]["sha256"],
            "e24090b43d9a0b59f675f7a4c2bab8ee6343183dd34e3bdee9ff86f116dc1e7f",
        )
        self.assertTrue(restart["helper"]["fresh_python_command_only"])
        self.assertEqual(restart["attempts_after_reopen"], 2)
        self.assertTrue(restart["third_attempt_rejected"])
        self.assertEqual(restart["retained_checkpoint_count"], 2)
        self.assertEqual(restart["backend_transfer_calls"], 0)
        self.assertEqual(restart["device_function_calls"], 0)
        self.assertEqual(
            [item.get("attempt") for item in restart["process_restarts"][:2]],
            [1, 2],
        )
        self.assertTrue(restart["process_restarts"][2]["rejected"])

    def test_raw_first_projection_is_disk_population_probe(self):
        raw = self.receipt["raw_first_execution_closure"]
        self.assertEqual(raw["auditor"]["size"], 76345)
        self.assertEqual(
            raw["auditor"]["sha256"],
            "122c4bd497c4d54c76f4fce572f3c8dc84b6d2ea7647087692a976dc590ce4b6",
        )
        self.assertEqual(
            raw["receipt"]["sha256"],
            "54db40b2fc63f98bc235cdc52bf87e02b9b875346859eea3b2eb257e61aa0958",
        )
        self.assertEqual(raw["receipt"]["size"], 15075)
        self.assertEqual(raw["predecessor"], self.module.RAW_FIRST_PREDECESSOR)
        self.assertEqual(raw["receipt"]["mode"], "0400")
        self.assertEqual(raw["receipt"]["nlink"], 1)
        self.assertEqual(
            raw["baseline"],
            {
                "projection_sha256": "79d3088c218d64b3f6a660fd249af7164ad100cdb0ccf8a27c3c753013ebff0e",
            },
        )
        self.assertTrue(raw["census_values_retained_only_in_raw_receipt"])
        self.assertEqual(
            raw["semantic_projection_omits_only"],
            [
                "all_revalidation_python_files_scanned",
                "subprocess_modules_scanned",
            ],
        )
        self.assertTrue(raw["inert_addition"]["full_census_changed"])
        self.assertTrue(raw["inert_addition"]["projection_unchanged"])
        self.assertTrue(raw["inert_addition"]["restored_exactly_after_deletion"])
        self.assertTrue(raw["neutral_host_process_addition"]["projection_unchanged"])
        self.assertTrue(raw["relevant_s22_mutation"]["failed_closed"])
        self.assertEqual(
            raw["override_vs_disk_population_mismatch"],
            "test-surface-only; this probe uses actual copied on-disk files and no overrides",
        )

    def test_all_authority_and_causal_fields_are_false(self):
        authority = self.receipt["authority"]
        for key in (
            "device_contact",
            "approval_created",
            "live_authorized",
            "candidate_success",
            "causal_result_allowed",
            "mux_result_claimable",
            "host_silent_claimable",
            "candidate_replay_authorized",
            "recovery_authorized",
            "transfer",
        ):
            with self.subTest(key=key):
                self.assertFalse(authority[key])
        self.assertEqual(authority["odin_invocations"], 0)
        self.assertEqual(authority["adb_commands"], 0)
        self.assertEqual(self.receipt["scope"]["tier"], "H0")
        self.assertTrue(self.receipt["scope"]["host_only"])
        self.assertFalse(self.receipt["scope"]["device_contact"])

    def test_raw_receipt_publication_is_complete_mode0400_and_no_clobber(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "prerequisite.json"
            identity = self.module.write_receipt(destination, self.receipt)
            self.assertEqual(destination.stat().st_mode & 0o777, 0o400)
            self.assertEqual(destination.stat().st_nlink, 1)
            self.assertEqual(identity["size"], destination.stat().st_size)
            self.assertEqual(
                json.loads(destination.read_text(encoding="utf-8"))["verdict"],
                self.module.VERDICT,
            )
            with self.assertRaises(self.module.AuditError):
                self.module.write_receipt(destination, self.receipt)
            sibling = Path(directory) / "prerequisite-copy.json"
            self.module.write_receipt(sibling, self.receipt)
            self.assertEqual(destination.read_bytes(), sibling.read_bytes())

    def test_strict_json_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_bytes(b'{"a":1,"a":2}\n')
            path.chmod(0o400)
            with self.assertRaises(self.module.AuditError):
                self.module._strict_json(path, "duplicate", mode=0o400)

    def test_new_auditor_has_no_device_command_import_or_live_authority(self):
        source = SCRIPT.read_text(encoding="utf-8")
        helper_path = (
            ROOT
            / "workspace/public/src/scripts/h0/"
            / "s22plus_fyg8_p319_restart_probe.py"
        )
        helper = helper_path.read_text(encoding="utf-8")
        for forbidden in (
            "import subprocess",
            "os.system(",
            "Popen(",
            "check_output(",
            "--adb",
            "--approval",
            "--finalize",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)
        self.assertNotIn("DEVICE-ACTION-F1-V2-APPROVE:", source)
        self.assertIn("subprocess.run", helper)
        self.assertNotIn("adb shell", helper)
        self.assertNotIn("odin4", helper)

    def test_restart_probe_byte_mutation_is_rejected(self):
        helper = (
            ROOT
            / "workspace/public/src/scripts/h0/"
            / "s22plus_fyg8_p319_restart_probe.py"
        )
        with tempfile.TemporaryDirectory() as directory:
            mutated = Path(directory) / helper.name
            mutated.write_bytes(helper.read_bytes() + b"\n# mutation\n")
            mutated.chmod(0o400)
            with self.assertRaises(self.module.AuditError):
                self.module._validate_restart_probe_source(mutated)


if __name__ == "__main__":
    unittest.main()

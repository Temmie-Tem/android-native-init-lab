import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_pref1_normal_reboot_live_v1.py"
)
PRIVATE = ROOT / "workspace/private"


def load_source():
    spec = importlib.util.spec_from_file_location("p319_pref1_live_test", SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P319PreF1NormalRebootLiveV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_source()

    def sandbox(self, *, pass_go=True):
        temporary = tempfile.TemporaryDirectory(
            prefix="p319-pref1-live-", dir=PRIVATE
        )
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve()
        session = root / "session"
        paths = {
            "SESSION_ROOT": session,
            "SESSION_LOCK": session / "coordinator.lock",
            "PREPARE_ADB": session / "prepare-adb",
            "PREPARE_RAW": session / "prepare-raw",
            "PROPOSAL_PATH": session / "activation-proposal.json",
            "PREPARE_STOP": session / "prepare-stop.json",
            "ACTIVATE_ADB": session / "activate-adb",
            "ACTIVATE_RAW": session / "activate-raw",
            "ACTIVATION_PATH": session / "activation.json",
            "JOURNAL_ROOT": session / "journal-owner",
            "RUN_STOP": session / "run-stop.json",
            "BINDING_PATH": root / "binding.json",
        }
        patcher = mock.patch.multiple(self.module, **paths)
        patcher.start()
        self.addCleanup(patcher.stop)
        payloads = self.module._input_payloads()
        review = (
            {"status": "pass-go", "verdict": self.module.REVIEW_VERDICT}
            if pass_go
            else {"status": "review-pending", "verdict": None}
        )
        paths["BINDING_PATH"].write_bytes(
            self.module.canonical(self.module._expected_binding(payloads, review))
        )
        result_validator = mock.patch.object(
            self.module,
            "_validated_v3_result",
            side_effect=lambda _v3: self.result(),
        )
        result_validator.start()
        self.addCleanup(result_validator.stop)
        preflight = mock.patch.object(self.module, "_preflight_executor")
        preflight.start()
        self.addCleanup(preflight.stop)
        return root

    def observation(
        self,
        *,
        boot="1" * 64,
        topology="2" * 64,
        serial="5" * 64,
        calls=None,
    ):
        def observe(_v3, **kwargs):
            if calls is not None:
                calls.append(dict(kwargs))
            return {
                "target": dict(self.module.TARGET),
                "topology_sha256": topology,
                "boot_id_sha256": boot,
                "healthy_android": True,
                "selection": {
                    "inventory_count": 1,
                    "inventory_models": ["SM-S906N"],
                    "inventory_sha256": "6" * 64,
                    "selected_serial_sha256": serial,
                    "selected_topology_sha256": topology,
                    "other_targets_commanded": False,
                },
                "fixture": "no-device",
            }

        return observe

    def prepare_and_activate(self, *, now=100):
        first = self.observation()
        prepared = self.module.prepare_activation(
            observer=first,
            now=now,
            campaign_id="3" * 32,
        )
        activated = self.module.activate_session(
            prepared["session_approval"],
            observer=self.observation(),
            now=now + 1,
        )
        return prepared, activated

    def result(self, *, before="1" * 64, after="4" * 64, topology="2" * 64):
        def health(boot):
            return {
                "android_boot_completed": True,
                "boot_animation_stopped": True,
                "boot_id_sha256": boot,
                "boot_sha256": "7" * 64,
                "kernel_release": "5.10.226-fixture",
                "odin_endpoint_absent": True,
                "root_verified": True,
                "supporting_partition_sha256": {
                    "dtbo": "8" * 64,
                    "recovery": "9" * 64,
                    "vendor_boot": "a" * 64,
                },
                "verified_boot_state": "orange",
            }

        def child(name, size, digest):
            return {
                "name": name,
                "node_type": "regular",
                "mode": "0400",
                "nlink": 1,
                "size": size,
                "sha256": digest,
            }

        name = "0000-adb-inventory"
        receipt = child(f"{name}.capture.json", 128, "b" * 64)
        stdout = child(f"{name}.stdout.bin", 16, "c" * 64)
        stderr = child(f"{name}.stderr.bin", 0, "d" * 64)
        raw_evidence = {
            "schema": "s22plus_fyg8_p319_d1_fresh_baseline_v3_raw_inventory",
            "root": (
                "workspace/private/runs/device-action-d1-p319-fresh-baseline-v3/"
                "p319-fresh-baseline-3-raw"
            ),
            "directory": (
                "workspace/private/runs/device-action-d1-p319-fresh-baseline-v3/"
                "p319-fresh-baseline-3-raw/raw-adb"
            ),
            "root_present": True,
            "directory_present": True,
            "complete": True,
            "children": [receipt, stderr, stdout],
            "handles": [
                {
                    "name": name,
                    "receipt": receipt,
                    "stdout": stdout,
                    "stderr": stderr,
                    "returncode": 0,
                    "timed_out": False,
                    "output_exceeded": False,
                    "producer_error_type": None,
                }
            ],
            "invalid_receipts": [],
            "unclaimed_children": [],
        }
        raw_evidence["aggregate_sha256"] = hashlib.sha256(
            self.module.canonical(raw_evidence)
        ).hexdigest()
        return {
            "schema": "s22plus_fyg8_p319_d1_fresh_baseline_v3_result",
            "verdict": "PASS_P319_D1_FRESH_BASELINE_V3_EXACT_NORMAL_REBOOT_RETURN_HEALTH",
            "ordinal": "d1-fresh-baseline-3",
            "reboot_count": 1,
            "other_targets_commanded": False,
            "before": health(before),
            "after": health(after),
            "selection": {
                "inventory_count": 1,
                "inventory_models": ["SM-S906N"],
                "inventory_sha256": "6" * 64,
                "selected_serial_sha256": "5" * 64,
                "selected_topology_sha256": topology,
                "other_targets_commanded": False,
            },
            "raw_evidence": raw_evidence,
            "candidate_transfer": False,
            "partition_payload": False,
            "odin": False,
            "download_transition": False,
            "f1_authorized": False,
            "replay_authorized": False,
            "device_writes": False,
            "live_authorized": False,
        }

    def journal_kinds(self):
        static = self.module._static()
        journal, _v3 = self.module._modules(static)
        with journal.Journal(self.module.JOURNAL_ROOT) as store:
            return [entry["record"]["kind"] for entry in store.history()]

    def record_bare_intent(self, *, now=102):
        static = self.module._static()
        journal, _v3 = self.module._modules(static)
        with journal.Journal(self.module.JOURNAL_ROOT) as store:
            state, intent = store._tail()
            self.assertEqual(state["phase"], "OPEN_HEALTHY")
            self.assertIsNone(intent)
            store.record_intent(
                {
                    "target": dict(self.module.TARGET),
                    "topology_sha256": state["topology_sha256"],
                    "boot_id_sha256": state["boot_id_sha256"],
                    "healthy_android": True,
                },
                now=now,
            )

    def test_default_binding_is_reviewed_but_self_test_has_no_authority(self):
        value = self.module.self_test()
        self.assertEqual(value["review_status"], "pass-go")
        self.assertFalse(value["connected_entries_blocked_until_review"])
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["activation_created"])
        self.assertFalse(value["live_authority"])

    def test_result_is_reopened_through_bound_v3_post_validation(self):
        retained = self.result()

        class FakeV3:
            @staticmethod
            def _validated_static_inputs():
                return {"fixture": True}

            @staticmethod
            def _validated_execution_inputs(_static):
                return {"raw": object()}

            @staticmethod
            def _post_validate(_inputs):
                return retained

        self.assertEqual(self.module._validated_v3_result(FakeV3), retained)

    def test_pending_review_blocks_before_observer_or_namespace(self):
        self.sandbox(pass_go=False)
        calls = []
        with self.assertRaisesRegex(self.module.LiveRunnerError, "review is absent"):
            self.module.prepare_activation(
                observer=self.observation(calls=calls),
                now=100,
                campaign_id="3" * 32,
            )
        self.assertEqual(calls, [])
        self.assertFalse(self.module.SESSION_ROOT.exists())

    def test_prepare_only_observes_and_emits_short_lived_exact_approval(self):
        self.sandbox()
        calls = []
        value = self.module.prepare_activation(
            observer=self.observation(calls=calls),
            now=100,
            campaign_id="3" * 32,
        )
        self.assertEqual(len(calls), 1)
        self.assertFalse(value["device_effect"])
        self.assertFalse(value["d1_consumed"])
        raw = self.module.PROPOSAL_PATH.read_bytes()
        proposal = json.loads(raw)
        self.assertEqual(proposal["created_at_epoch"], 100)
        self.assertEqual(proposal["expires_at_epoch"], 700)
        self.assertEqual(
            value["session_approval"],
            self.module.AUTHORITY_PREFIX + self.module._sha(raw),
        )
        self.assertFalse(self.module.ACTIVATION_PATH.exists())
        self.assertFalse(self.module.JOURNAL_ROOT.exists())

    def test_wrong_or_expired_approval_blocks_before_activation_observer(self):
        self.sandbox()
        prepared = self.module.prepare_activation(
            observer=self.observation(), now=100, campaign_id="3" * 32
        )
        calls = []
        with self.assertRaisesRegex(self.module.LiveRunnerError, "approval is absent"):
            self.module.activate_session(
                self.module.AUTHORITY_PREFIX + "0" * 64,
                observer=self.observation(calls=calls),
                now=101,
            )
        self.assertEqual(calls, [])
        with self.assertRaisesRegex(self.module.LiveRunnerError, "proposal expired"):
            self.module.activate_session(
                prepared["session_approval"],
                observer=self.observation(calls=calls),
                now=700,
            )
        self.assertEqual(calls, [])

    def test_activation_rechecks_same_target_topology_boot_and_health(self):
        self.sandbox()
        prepared = self.module.prepare_activation(
            observer=self.observation(), now=100, campaign_id="3" * 32
        )
        with self.assertRaisesRegex(self.module.LiveRunnerError, "topology, boot"):
            self.module.activate_session(
                prepared["session_approval"],
                observer=self.observation(boot="9" * 64),
                now=101,
            )
        self.assertFalse(self.module.ACTIVATION_PATH.exists())
        self.assertFalse(self.module.JOURNAL_ROOT.exists())

    def test_activation_rechecks_same_selected_serial(self):
        self.sandbox()
        prepared = self.module.prepare_activation(
            observer=self.observation(), now=100, campaign_id="3" * 32
        )
        with self.assertRaisesRegex(self.module.LiveRunnerError, "activation target"):
            self.module.activate_session(
                prepared["session_approval"],
                observer=self.observation(serial="b" * 64),
                now=101,
            )
        self.assertFalse(self.module.ACTIVATION_PATH.exists())
        self.assertFalse(self.module.JOURNAL_ROOT.exists())

    def test_activation_publication_cut_resumes_without_second_observation(self):
        self.sandbox()
        prepared = self.module.prepare_activation(
            observer=self.observation(), now=100, campaign_id="3" * 32
        )
        static = self.module._static()
        journal, v3 = self.module._modules(static)
        calls = []
        with mock.patch.object(self.module, "_modules", return_value=(journal, v3)):
            with mock.patch.object(
                journal.Journal,
                "create",
                side_effect=journal.JournalError("fixture activation cut"),
            ):
                with self.assertRaises(journal.JournalError):
                    self.module.activate_session(
                        prepared["session_approval"],
                        observer=self.observation(calls=calls),
                        now=101,
                    )
            self.assertTrue(self.module.ACTIVATION_PATH.is_file())
            recovered = self.module.activate_session(
                prepared["session_approval"],
                observer=self.observation(calls=calls),
                now=800,
            )
        self.assertEqual(recovered["status"], "ACTIVATED_NO_EFFECT")
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.journal_kinds(), ["CAMPAIGN_OPEN"])

    def test_activation_boot_or_topology_cannot_diverge_from_proposal(self):
        self.sandbox()
        prepared, _activated = self.prepare_and_activate()
        value = json.loads(self.module.ACTIVATION_PATH.read_bytes())
        value["activation"]["topology_sha256"] = "9" * 64
        value["activation"]["boot_id_sha256"] = "8" * 64
        self.module.ACTIVATION_PATH.chmod(0o600)
        self.module.ACTIVATION_PATH.write_bytes(self.module.canonical(value))
        self.module.ACTIVATION_PATH.chmod(0o400)
        calls = []
        with self.assertRaisesRegex(self.module.LiveRunnerError, "binding differs"):
            self.module.activate_session(
                prepared["session_approval"],
                observer=self.observation(calls=calls),
                now=102,
            )
        self.assertEqual(calls, [])

    def test_happy_path_consumes_one_d1_and_cannot_repeat(self):
        self.sandbox()
        _prepared, activated = self.prepare_and_activate()
        self.assertEqual(activated["status"], "ACTIVATED_NO_EFFECT")
        calls = []

        def execute(_v3):
            calls.append("effect")
            return self.result()

        value = self.module.run_normal_reboot(
            observer=self.observation(), executor=execute, now=701
        )
        self.assertEqual(value["status"], "HEALTHY_RETURN_CLOSED")
        self.assertEqual(calls, ["effect"])
        self.assertEqual(
            self.journal_kinds(),
            ["CAMPAIGN_OPEN", "EFFECT_INTENT", "EFFECT_HEALTHY_RETURN", "CAMPAIGN_CLOSE"],
        )
        with self.assertRaisesRegex(self.module.LiveRunnerError, "not eligible"):
            self.module.run_normal_reboot(
                observer=self.observation(), executor=execute, now=702
            )
        self.assertEqual(calls, ["effect"])

    def test_expired_session_blocks_before_observer_or_effect(self):
        self.sandbox()
        self.prepare_and_activate()
        calls = []
        with self.assertRaisesRegex(self.module.LiveRunnerError, "expired"):
            self.module.run_normal_reboot(
                observer=self.observation(calls=calls),
                executor=lambda _v3: calls.append("effect"),
                now=43_301,
            )
        self.assertEqual(calls, [])
        self.assertEqual(self.journal_kinds(), ["CAMPAIGN_OPEN"])

    def test_fresh_pre_intent_mismatch_consumes_nothing(self):
        self.sandbox()
        self.prepare_and_activate()
        calls = []
        with self.assertRaisesRegex(self.module.LiveRunnerError, "pre-intent"):
            self.module.run_normal_reboot(
                observer=self.observation(boot="8" * 64),
                executor=lambda _v3: calls.append("effect"),
                now=102,
            )
        self.assertEqual(calls, [])
        self.assertEqual(self.journal_kinds(), ["CAMPAIGN_OPEN"])

    def test_fresh_pre_intent_serial_mismatch_consumes_nothing(self):
        self.sandbox()
        self.prepare_and_activate()
        calls = []
        with self.assertRaisesRegex(self.module.LiveRunnerError, "selected serial"):
            self.module.run_normal_reboot(
                observer=self.observation(serial="b" * 64),
                executor=lambda _v3: calls.append("effect"),
                now=102,
            )
        self.assertEqual(calls, [])
        self.assertEqual(self.journal_kinds(), ["CAMPAIGN_OPEN"])

    def test_failed_pre_intent_observation_is_preserved_and_next_slot_runs(self):
        self.sandbox()
        self.prepare_and_activate()
        seen = []

        def partial(_v3, **kwargs):
            seen.append(kwargs["raw_root"])
            kwargs["raw_root"].mkdir()
            raise RuntimeError("fixture partial observation")

        with self.assertRaisesRegex(RuntimeError, "partial observation"):
            self.module.run_normal_reboot(observer=partial, now=102)
        value = self.module.run_normal_reboot(
            observer=self.observation(calls=seen),
            executor=lambda _v3: self.result(),
            now=103,
        )
        self.assertEqual(value["status"], "HEALTHY_RETURN_CLOSED")
        self.assertEqual(len(seen), 2)
        self.assertNotEqual(seen[0], seen[1]["raw_root"])

    def test_existing_v3_namespace_blocks_before_outer_intent(self):
        self.sandbox()
        self.prepare_and_activate()
        calls = []
        self.module._preflight_executor.side_effect = self.module.LiveRunnerError(
            "fixture V3 namespace is not fresh"
        )
        with self.assertRaisesRegex(self.module.LiveRunnerError, "not fresh"):
            self.module.run_normal_reboot(
                observer=self.observation(),
                executor=lambda _v3: calls.append("effect"),
                now=102,
            )
        self.assertEqual(calls, [])
        self.assertEqual(self.journal_kinds(), ["CAMPAIGN_OPEN"])

    def test_close_cut_cannot_dispatch_second_reboot(self):
        self.sandbox()
        self.prepare_and_activate()
        static = self.module._static()
        journal, v3 = self.module._modules(static)
        original_close = journal.Journal.record_close
        close_calls = []
        effects = []

        def fail_once(store, *, now):
            close_calls.append(now)
            if len(close_calls) == 1:
                raise journal.JournalError("fixture close cut")
            return original_close(store, now=now)

        def execute(_v3):
            effects.append("effect")
            return self.result()

        with mock.patch.object(self.module, "_modules", return_value=(journal, v3)):
            with mock.patch.object(journal.Journal, "record_close", new=fail_once):
                with self.assertRaisesRegex(self.module.LiveRunnerError, "close remains pending"):
                    self.module.run_normal_reboot(
                        observer=self.observation(), executor=execute, now=102
                    )
                value = self.module.run_normal_reboot(
                    observer=self.observation(), executor=execute, now=103
                )
        self.assertEqual(value["status"], "FINALIZED_EXISTING_HEALTHY_RETURN")
        self.assertEqual(effects, ["effect"])
        self.assertEqual(close_calls, [102, 103])
        self.assertEqual(
            self.journal_kinds(),
            ["CAMPAIGN_OPEN", "EFFECT_INTENT", "EFFECT_HEALTHY_RETURN", "CAMPAIGN_CLOSE"],
        )

    def test_post_intent_failure_parks_and_never_replays(self):
        self.sandbox()
        self.prepare_and_activate()
        calls = []

        def fail(_v3):
            calls.append("effect")
            raise RuntimeError("fixture-cut")

        with self.assertRaisesRegex(self.module.LiveRunnerError, "uncertain-consumed"):
            self.module.run_normal_reboot(
                observer=self.observation(), executor=fail, now=102
            )
        self.assertEqual(calls, ["effect"])
        self.assertEqual(
            self.journal_kinds(),
            ["CAMPAIGN_OPEN", "EFFECT_INTENT", "EFFECT_UNCERTAIN_PARK"],
        )
        value = self.module.reconcile(
            now=103,
            result_loader=lambda _v3: calls.append("forbidden-reload"),
        )
        self.assertEqual(value["status"], "PARKED_UNCERTAIN_CONSUMED_NO_REPLAY")
        self.assertEqual(calls, ["effect"])

    def test_reporting_cut_reconciles_existing_result_without_effect_replay(self):
        self.sandbox()
        self.prepare_and_activate()
        self.record_bare_intent()
        loads = []

        def load(_v3):
            loads.append("result")
            return self.result()

        value = self.module.reconcile(now=103, result_loader=load)
        self.assertEqual(value["status"], "RECONCILED_HEALTHY_RETURN")
        self.assertEqual(loads, ["result"])
        self.assertEqual(
            self.journal_kinds(),
            ["CAMPAIGN_OPEN", "EFFECT_INTENT", "EFFECT_HEALTHY_RETURN", "CAMPAIGN_CLOSE"],
        )

    def test_expired_session_still_reconciles_durable_intent(self):
        self.sandbox()
        self.prepare_and_activate()
        self.record_bare_intent()
        value = self.module.reconcile(
            now=50_000,
            result_loader=lambda _v3: self.result(),
        )
        self.assertEqual(value["status"], "RECONCILED_HEALTHY_RETURN")
        self.assertEqual(self.journal_kinds()[-1], "CAMPAIGN_CLOSE")

    def test_malformed_success_result_parks_instead_of_closing(self):
        self.sandbox()
        self.prepare_and_activate()
        malformed = self.result()
        malformed["after"]["root_verified"] = False
        with self.assertRaisesRegex(self.module.LiveRunnerError, "uncertain-consumed"):
            self.module.run_normal_reboot(
                observer=self.observation(),
                executor=lambda _v3: malformed,
                now=102,
            )
        self.assertEqual(self.journal_kinds()[-1], "EFFECT_UNCERTAIN_PARK")

    def test_forged_or_incomplete_raw_inventory_cannot_close(self):
        self.sandbox()
        self.prepare_and_activate()
        malformed = self.result()
        malformed["raw_evidence"]["forged"] = "accepted"
        with self.assertRaisesRegex(self.module.LiveRunnerError, "uncertain-consumed"):
            self.module.run_normal_reboot(
                observer=self.observation(),
                executor=lambda _v3: malformed,
                now=102,
            )
        self.assertEqual(self.journal_kinds()[-1], "EFFECT_UNCERTAIN_PARK")

    def test_empty_raw_child_and_handle_schemas_cannot_close(self):
        self.sandbox()
        self.prepare_and_activate()
        malformed = self.result()
        raw = malformed["raw_evidence"]
        raw["children"] = [{}]
        raw["handles"] = [{}]
        base = {key: value for key, value in raw.items() if key != "aggregate_sha256"}
        raw["aggregate_sha256"] = hashlib.sha256(
            self.module.canonical(base)
        ).hexdigest()
        with self.assertRaisesRegex(self.module.LiveRunnerError, "uncertain-consumed"):
            self.module.run_normal_reboot(
                observer=self.observation(),
                executor=lambda _v3: malformed,
                now=102,
            )
        self.assertEqual(self.journal_kinds()[-1], "EFFECT_UNCERTAIN_PARK")

    def test_missing_result_after_bare_intent_parks_once(self):
        self.sandbox()
        self.prepare_and_activate()
        self.record_bare_intent()
        loads = []

        def missing(_v3):
            loads.append("missing")
            raise FileNotFoundError("fixture-result")

        value = self.module.reconcile(now=103, result_loader=missing)
        self.assertEqual(value["status"], "PARKED_UNCERTAIN_CONSUMED_NO_REPLAY")
        self.assertEqual(loads, ["missing"])
        value = self.module.reconcile(now=104, result_loader=missing)
        self.assertEqual(value["status"], "PARKED_UNCERTAIN_CONSUMED_NO_REPLAY")
        self.assertEqual(loads, ["missing"])

    def test_namespace_symlink_is_rejected_before_observation(self):
        root = self.sandbox()
        target = root / "target"
        target.mkdir()
        self.module.SESSION_ROOT.symlink_to(target, target_is_directory=True)
        calls = []
        with self.assertRaisesRegex(self.module.LiveRunnerError, "already exists"):
            self.module.prepare_activation(
                observer=self.observation(calls=calls),
                now=100,
                campaign_id="3" * 32,
            )
        self.assertEqual(calls, [])

    def test_cli_exposes_no_caller_selected_path_or_action(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("--path", source)
        self.assertNotIn("--command", source)
        self.assertNotIn("--class", source)
        self.assertIn('group.add_argument("--run-normal-reboot"', source)
        self.assertIn("MAX_JSON = 512 * 1024", source)


if __name__ == "__main__":
    unittest.main()

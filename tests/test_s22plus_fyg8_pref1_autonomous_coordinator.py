"""Hostile host-only tests for the dormant S22+ pre-F1 coordinator core."""

from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import importlib.util
import io
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/device-action/coordinators/"
    "s22plus_fyg8_pref1_autonomous_coordinator_h0.py"
)
REPORT = (
    ROOT
    / "docs/reports/"
    "S22PLUS_FYG8_PREF1_AUTONOMOUS_COORDINATOR_H0_2026-08-29.md"
)


def load_module():
    spec = importlib.util.spec_from_file_location("s22plus_pref1_coordinator_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S22PlusPreF1AutonomousCoordinatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def activation(self, *, now: int = 100, **updates):
        binding = self.module.current_binding()
        value = {
            "schema": self.module.ACTIVATION_SCHEMA,
            "campaign_id": "1" * 32,
            "target": deepcopy(self.module.TARGET),
            "policy_sha256": binding["policy"]["sha256"],
            "coordinator_sha256": binding["coordinator"]["sha256"],
            "catalog_sha256": binding["catalog_sha256"],
            "effect_core_sha256": "2" * 64,
            "topology_sha256": "3" * 64,
            "boot_id_sha256": "4" * 64,
            "opened_at_epoch": now,
            "expires_at_epoch": now + self.module.CAMPAIGN_DURATION_SECONDS,
            "d1_effect_max": self.module.D1_EFFECT_MAX,
            "d0_command_group_max": self.module.D0_COMMAND_GROUP_MAX,
            "independent_pass_go_sha256": "5" * 64,
            "live_session_approval_sha256": "6" * 64,
            "operator_attended_opening": True,
        }
        value.update(updates)
        return value

    def state(self, *, now: int = 100):
        raw = self.module.canonical_bytes(self.activation(now=now))
        return self.module.model_campaign_open(raw, now=now)

    def observed(self, state, *, boot: str | None = None, **updates):
        value = {
            "target": deepcopy(self.module.TARGET),
            "topology_sha256": state["topology_sha256"],
            "boot_id_sha256": boot or state["boot_id_sha256"],
            "healthy_android": True,
        }
        value.update(updates)
        return value

    @staticmethod
    def distinct_boot(index: int) -> str:
        return hashlib.sha256(f"boot-{index}".encode()).hexdigest()

    def roundtrip(self, state, class_id, *, now=101, boot=None, proof_mode=None):
        selected_mode = proof_mode or self.module.DEFAULT_PROOF_MODES[class_id]
        intended, intent = self.module.model_effect_intent(
            state,
            class_id=class_id,
            proof_mode=selected_mode,
            observed=self.observed(state),
            now=now,
        )
        returned, result = self.module.model_healthy_return(
            intended,
            intent=intent,
            observed=self.observed(intended, boot=boot),
            now=now,
        )
        self.assertEqual(result["status"], "HEALTHY_RETURN")
        return returned

    def test_render_plan_is_dormant_and_has_no_effect_surface(self):
        plan = self.module.render_plan()
        self.assertEqual(plan["status"], "H0_PREF1_AUTONOMOUS_COORDINATOR_NOT_ACTIVE")
        for key in (
            "active",
            "live_authority",
            "device_action_integration",
            "durable_journal_integration",
            "activation_manifest_present",
            "live_session_approval_present",
        ):
            self.assertIs(plan[key], False)
        self.assertEqual(plan["cli"], ["--render-plan"])
        self.assertEqual(plan["device_commands"], [])
        self.assertEqual(plan["device_effects"], [])
        self.assertEqual(plan["partition_transfers"], [])
        self.assertEqual(plan["policy_status"], "DEFINED_NOT_ACTIVE")

    def test_policy_is_the_versioned_catalog_authority(self):
        plan = self.module.render_plan()
        self.assertEqual(plan["action_tiers"], self.module.ACTION_TIERS)
        self.assertEqual(
            set(plan["action_tiers"]),
            {
                "bounded_raw_first_read",
                "normal_android_reboot_health",
                "payload_free_download_roundtrip",
                "fixed_privileged_usb_role_or_udc_transient",
            },
        )
        binding = plan["binding"]
        self.assertEqual(binding, self.module.current_binding())
        self.assertEqual(len(binding["catalog_sha256"]), 64)

    def test_activation_is_exact_canonical_attended_and_current(self):
        manifest = self.activation()
        raw = self.module.canonical_bytes(manifest)
        self.assertEqual(self.module.parse_activation_manifest(raw, now=100), manifest)
        state = self.module.model_campaign_open(raw, now=100)
        self.assertEqual(state["phase"], "OPEN_HEALTHY")
        self.assertEqual(state["d1_effects_used"], 0)
        self.assertEqual(state["d0_command_groups_used"], 0)
        self.assertEqual(state["activation_sha256"], hashlib.sha256(raw).hexdigest())

    def test_activation_mutations_fail_closed(self):
        base = self.activation()
        mutations = []
        for key, value in (
            ("target", {"model": "other", "device": "g0q", "build": "S906NKSS7FYG8"}),
            ("policy_sha256", "0" * 64),
            ("coordinator_sha256", "0" * 64),
            ("catalog_sha256", "0" * 64),
            ("d1_effect_max", 9),
            ("d0_command_group_max", 257),
            ("operator_attended_opening", False),
            ("opened_at_epoch", True),
            ("expires_at_epoch", 200),
        ):
            item = deepcopy(base)
            item[key] = value
            mutations.append(item)
        extra = deepcopy(base)
        extra["path"] = "/tmp/foreign"
        mutations.append(extra)
        for value in mutations:
            with self.subTest(value=value), self.assertRaises(
                self.module.CoordinatorModelError
            ):
                self.module.parse_activation_manifest(
                    self.module.canonical_bytes(value), now=100
                )
        with self.assertRaisesRegex(self.module.CoordinatorModelError, "not canonical"):
            self.module.parse_activation_manifest(
                (self.module.canonical_bytes(base).decode().replace(":", ": ", 1)).encode(),
                now=100,
            )
        with self.assertRaisesRegex(self.module.CoordinatorModelError, "duplicate"):
            self.module.strict_json_bytes(b'{"x":1,"x":2}\n')

    def test_pre_intent_failure_consumes_nothing(self):
        state = self.state()
        before = self.module.canonical_bytes(state)
        after = self.module.model_pre_intent_failure(
            state, reason="host_input_invalid"
        )
        self.assertEqual(self.module.canonical_bytes(after), before)
        for reason in ("unknown", True, ["host_input_invalid"]):
            with self.subTest(reason=reason), self.assertRaises(
                self.module.CoordinatorModelError
            ):
                self.module.model_pre_intent_failure(state, reason=reason)

    def test_d0_budget_is_one_aggregate_campaign_counter(self):
        state = self.state()
        for _ in range(self.module.D0_COMMAND_GROUP_MAX):
            state = self.roundtrip(state, "bounded_raw_first_read")
        self.assertEqual(
            state["d0_command_groups_used"], self.module.D0_COMMAND_GROUP_MAX
        )
        self.assertEqual(state["d1_effects_used"], 0)
        with self.assertRaisesRegex(self.module.CoordinatorModelError, "D0 budget"):
            self.module.model_effect_intent(
                state,
                class_id="bounded_raw_first_read",
                proof_mode="same_boot_observation",
                observed=self.observed(state),
                now=101,
            )

    def test_d1_budget_is_shared_by_all_d1_classes(self):
        state = self.state()
        classes = (
            "fixed_privileged_usb_role_or_udc_transient",
            "normal_android_reboot_health",
            "payload_free_download_roundtrip",
        )
        for index in range(self.module.D1_EFFECT_MAX):
            class_id = classes[index % len(classes)]
            proof_mode = self.module.DEFAULT_PROOF_MODES[class_id]
            boot = self.distinct_boot(index) if proof_mode in self.module.NEW_BOOT_PROOF_MODES else None
            state = self.roundtrip(state, class_id, boot=boot)
        self.assertEqual(state["d1_effects_used"], self.module.D1_EFFECT_MAX)
        with self.assertRaisesRegex(self.module.CoordinatorModelError, "D1 budget"):
            self.module.model_effect_intent(
                state,
                class_id="normal_android_reboot_health",
                proof_mode="new_boot_health",
                observed=self.observed(state),
                now=101,
            )

    def test_boot_relation_is_bound_per_class(self):
        for class_id, proof_modes in self.module.PROOF_MODES.items():
            for proof_mode in proof_modes:
                with self.subTest(class_id=class_id, proof_mode=proof_mode):
                    state = self.state()
                    intended, intent = self.module.model_effect_intent(
                        state,
                        class_id=class_id,
                        proof_mode=proof_mode,
                        observed=self.observed(state),
                        now=101,
                    )
                    wrong_boot = (
                        state["boot_id_sha256"]
                        if proof_mode in self.module.NEW_BOOT_PROOF_MODES
                        else self.distinct_boot(99)
                    )
                    with self.assertRaises(self.module.CoordinatorModelError):
                        self.module.model_healthy_return(
                            intended,
                            intent=intent,
                            observed=self.observed(intended, boot=wrong_boot),
                            now=101,
                        )
                    correct_boot = (
                        self.distinct_boot(100)
                        if proof_mode in self.module.NEW_BOOT_PROOF_MODES
                        else state["boot_id_sha256"]
                    )
                    returned, result = self.module.model_healthy_return(
                        intended,
                        intent=intent,
                        observed=self.observed(intended, boot=correct_boot),
                        now=101,
                    )
                    self.assertEqual(result["proof_mode"], proof_mode)
                    self.assertEqual(returned["phase"], "OPEN_HEALTHY")

    def test_uncertain_cut_consumes_and_parks_without_replay(self):
        state = self.state()
        intended, intent = self.module.model_effect_intent(
            state,
            class_id="normal_android_reboot_health",
            proof_mode="new_boot_health",
            observed=self.observed(state),
            now=101,
        )
        parked, result = self.module.model_uncertain_cut(
            intended, intent=intent, reason="result_uncertain"
        )
        self.assertEqual(parked["phase"], "PARKED")
        self.assertEqual(result["status"], "UNCERTAIN_CONSUMED_NO_REPLAY")
        self.assertEqual(parked["d1_effects_used"], 1)
        with self.assertRaises(self.module.CoordinatorModelError):
            self.module.model_effect_intent(
                parked,
                class_id="bounded_raw_first_read",
                proof_mode="same_boot_observation",
                observed=self.observed(parked),
                now=102,
            )
        with self.assertRaises(self.module.CoordinatorModelError):
            self.module.model_healthy_return(
                parked,
                intent=intent,
                observed=self.observed(parked, boot=self.distinct_boot(1)),
                now=102,
            )
        with self.assertRaises(self.module.CoordinatorModelError):
            self.module.model_close(parked)

    def test_unknown_or_recovery_action_and_tampered_intent_are_rejected(self):
        state = self.state()
        for class_id in ("android_recovery_entry", "shell", True, {"class_id": "bounded_raw_first_read"}):
            with self.subTest(class_id=class_id), self.assertRaises(
                self.module.CoordinatorModelError
            ):
                self.module.model_effect_intent(
                    state,
                    class_id=class_id,
                    proof_mode="same_boot_observation",
                    observed=self.observed(state),
                    now=101,
                )
        for proof_mode in ("unknown", "new_boot_health", True):
            with self.subTest(proof_mode=proof_mode), self.assertRaises(
                self.module.CoordinatorModelError
            ):
                self.module.model_effect_intent(
                    state,
                    class_id="fixed_privileged_usb_role_or_udc_transient",
                    proof_mode=proof_mode,
                    observed=self.observed(state),
                    now=101,
                )
        intended, intent = self.module.model_effect_intent(
            state,
            class_id="bounded_raw_first_read",
            proof_mode="same_boot_observation",
            observed=self.observed(state),
            now=101,
        )
        tampered = deepcopy(intent)
        tampered["d0_command_groups_used_after"] = 0
        with self.assertRaises(self.module.CoordinatorModelError):
            self.module.model_healthy_return(
                intended,
                intent=tampered,
                observed=self.observed(intended),
                now=101,
            )
        for key, replacement in (
            ("expires_at_epoch", intended["expires_at_epoch"] + 1),
            ("next_ordinal", intended["next_ordinal"] + 1),
            ("policy_sha256", "0" * 64),
            ("coordinator_sha256", "0" * 64),
        ):
            changed = deepcopy(intended)
            changed[key] = replacement
            with self.subTest(key=key), self.assertRaises(
                self.module.CoordinatorModelError
            ):
                self.module.model_uncertain_cut(
                    changed, intent=intent, reason="result_uncertain"
                )

    def test_expiry_blocks_new_effect_but_not_clean_close(self):
        state = self.state()
        with self.assertRaisesRegex(self.module.CoordinatorModelError, "expired"):
            self.module.model_effect_intent(
                state,
                class_id="bounded_raw_first_read",
                proof_mode="same_boot_observation",
                observed=self.observed(state),
                now=state["expires_at_epoch"],
            )
        closed = self.module.model_close(state)
        self.assertEqual(closed["phase"], "CLOSED")
        with self.assertRaises(self.module.CoordinatorModelError):
            self.module.model_close(closed)

    def test_source_has_no_process_or_device_execution_surface(self):
        source = SCRIPT.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertTrue(
            imports.isdisjoint({"subprocess", "ctypes", "pty", "asyncio", "multiprocessing"})
        )
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertTrue(calls.isdisjoint({"system", "popen", "execv", "posix_spawn", "write_bytes", "write_text"}))
        self.assertEqual(SCRIPT.parent.name, "coordinators")
        self.assertNotEqual(SCRIPT.parent.name, "revalidation")

    def test_cli_is_render_only(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(self.module.main(["--render-plan"]), 0)
        self.assertEqual(
            self.module.strict_json_bytes(output.getvalue().encode()),
            self.module.render_plan(),
        )
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                self.module.main([])
        self.assertEqual(caught.exception.code, 2)

    def test_report_preserves_the_non_active_integration_boundary(self):
        report = REPORT.read_text(encoding="utf-8")
        for clause in (
            "IMPLEMENTED / REVIEW PENDING / NOT ACTIVE",
            "one later integration unit",
            "not a live runner",
            "no process-spawn facility",
            "F1 remains freshly attended",
            "14/14",
            "reboot_restore_health",
            "c0d56417c070c5958a356110f4b1996f9c903af993d118e0f812cccdd8aea65e",
        ):
            self.assertIn(clause, report)


if __name__ == "__main__":
    unittest.main()

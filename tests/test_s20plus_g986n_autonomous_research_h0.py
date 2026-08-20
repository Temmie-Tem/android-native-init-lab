import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_research_h0.py"
)
REPORT = (
    ROOT
    / "docs/reports/"
    "S20PLUS_G986N_AUTONOMOUS_RESEARCH_SESSION_H0_2026-08-21.md"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s20plus_g986n_autonomous_research_h0_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S20PlusAutonomousResearchH0Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.plan = cls.module.render_plan()

    def identity(self):
        return {
            "target": self.module.TARGET,
            "serial_sha256": "1" * 64,
            "topology_sha256": "2" * 64,
            "boot_id_sha256": "3" * 64,
            "healthy_android": True,
            "foreign_guard_present": False,
        }

    def test_plan_is_dormant_and_has_no_command_surface(self):
        self.assertFalse(self.plan["active"])
        self.assertFalse(self.plan["live_authority"])
        self.assertEqual(
            self.plan["status"],
            "H0_AUTONOMOUS_RESEARCH_POLICY_PASS_GO_NOT_ACTIVE",
        )
        self.assertEqual(self.plan["cli"], ["--render-plan"])
        self.assertEqual(self.plan["device_commands"], [])
        self.assertEqual(self.plan["root_commands"], [])
        self.assertEqual(self.plan["device_effects"], [])
        self.assertEqual(self.plan["partition_transfers"], [])

    def test_binding_is_exact_target_and_source_bound(self):
        binding = self.plan["binding"]
        self.assertEqual(binding["target"], self.module.TARGET)
        self.assertEqual(
            self.module.digest(binding), self.plan["binding_sha256"]
        )
        self.assertEqual(
            set(binding["sources"]),
            {"inventory", "routine_d0", "routine_actions", "download_exit"},
        )
        for label, receipt in binding["sources"].items():
            self.assertEqual(
                receipt["sha256"], self.module.SOURCE_SPECS[label]["sha256"]
            )

    def test_only_named_no_input_actions_are_accepted(self):
        for action in self.module.ACTIONS:
            self.assertEqual(
                self.module.validate_named_request({"action": action}), action
            )
        hostile = (
            {},
            {"action": "shell"},
            {"action": "public-health", "path": "/data"},
            {"action": "public-health", "shell": "id"},
            {"action": 1},
            ["public-health"],
        )
        for value in hostile:
            with self.subTest(value=value), self.assertRaises(
                self.module.ResearchPolicyError
            ):
                self.module.validate_named_request(value)

    def test_policy_owner_has_no_dispatch_or_caller_backend(self):
        self.assertFalse(hasattr(self.module, "dispatch_named_action"))
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("Callable", source)
        self.assertNotIn("backend(", source)

    def test_identity_requires_exact_healthy_target_and_typed_hashes(self):
        self.assertEqual(
            self.module.validate_exact_identity(self.identity()), self.identity()
        )
        mutations = []
        for key, value in (
            ("target", {**self.module.TARGET, "device": "g0q"}),
            ("serial_sha256", True),
            ("topology_sha256", "A" * 64),
            ("boot_id_sha256", "3" * 63),
            ("healthy_android", 1),
            ("foreign_guard_present", 0),
        ):
            item = dict(self.identity())
            item[key] = value
            mutations.append(item)
        item = dict(self.identity())
        item["unexpected"] = True
        mutations.append(item)
        for value in mutations:
            with self.subTest(value=value), self.assertRaises(
                self.module.ResearchPolicyError
            ):
                self.module.validate_exact_identity(value)

    def test_limits_and_pre_f1_stop_are_finite_and_effect_free(self):
        limits = self.plan["binding"]["limits"]
        self.assertEqual(limits["session_duration_sec"], 14_400)
        self.assertEqual(limits["control_transactions_max"], 16)
        self.assertEqual(limits["component_effects_max"], 24)
        self.assertEqual(limits["private_evidence_bytes_max"], 32 * 1024 * 1024)
        campaign = self.plan["binding"]["campaign_limits"]
        self.assertTrue(campaign["fresh_attended_opening_required"])
        self.assertEqual(campaign["campaign_duration_sec"], 86_400)
        self.assertEqual(campaign["control_transactions_max"], 64)
        self.assertEqual(campaign["component_effects_max"], 96)
        self.assertFalse(campaign["automatic_renewal"])
        self.assertFalse(campaign["terminal_resets_counters"])
        accounting = self.plan["binding"]["campaign_accounting"]
        self.assertTrue(accounting["one_durable_allocation"])
        self.assertTrue(accounting["child_sessions_debit_monotonically"])
        self.assertTrue(accounting["expiry_or_terminal_never_resets"])
        self.assertTrue(accounting["new_campaign_requires_fresh_attended_opening"])
        self.assertTrue(
            accounting["roundtrip_debits_one_transaction_and_two_component_effects"]
        )
        self.assertTrue(
            accounting["entry_debits_entry_and_reserves_return_before_entry_intent"]
        )
        self.assertTrue(
            accounting["return_intent_converts_reservation_without_new_capacity"]
        )
        self.assertTrue(
            accounting["reserved_return_survives_expiry_for_recovery_only"]
        )
        self.assertTrue(
            accounting["expiry_never_allows_new_baseline_entry_or_transaction"]
        )
        boundary = self.plan["binding"]["pre_f1_boundary"]
        self.assertTrue(boundary["healthy_normal_android"])
        for key in (
            "f1_intent",
            "download_entry_for_f1",
            "approval_consumed",
            "partition_transfer",
        ):
            self.assertFalse(boundary[key])

    def test_root_profiles_are_deferred_until_complete_closure_exists(self):
        binding = self.plan["binding"]
        for profile in binding["deferred_root_profiles"].values():
            self.assertEqual(set(profile), {"paths", "status"})
            self.assertTrue(profile["paths"])
            self.assertEqual(profile["status"], "DEFERRED_NOT_AN_ACTION")
        self.assertEqual(
            set(binding["deferred_root_profiles"]),
            {
                "root-pid1-status",
                "root-pid1-mountinfo",
                "root-namespace-links",
                "root-selinux-enforce",
                "root-magisk-metadata",
            },
        )
        for action in binding["deferred_root_profiles"]:
            self.assertNotIn(action, self.module.ACTIONS)
        requirements = binding["root_profile_activation_requirements"]
        self.assertTrue(requirements)
        self.assertTrue(all(value is True for value in requirements.values()))

    def test_download_surface_is_atomic_roundtrip_not_attended_exit_reuse(self):
        controls = self.plan["binding"]["actions"]["control"]
        self.assertEqual(controls, ["reboot-system", "download-roundtrip"])
        self.assertNotIn("enter-download", self.module.ACTIONS)
        self.assertNotIn("exit-download", self.module.ACTIONS)
        self.assertIn("download_exit", self.plan["binding"]["sources"])

    def test_roundtrip_debits_both_intents_without_reset_or_replay(self):
        counters = {key: 0 for key in self.module.COUNTER_KEYS}
        entry = self.module.debit_before_intent(
            counters,
            "download-roundtrip",
            "entry",
            self.module.LIMITS,
        )
        self.assertEqual(entry["control_transactions"], 1)
        self.assertEqual(entry["component_effects_consumed"], 1)
        self.assertEqual(entry["component_effects_reserved"], 1)
        self.assertEqual(entry["roundtrip_entries"], 1)
        self.assertEqual(entry["roundtrip_returns"], 0)
        with self.assertRaisesRegex(
            self.module.ResearchPolicyError, "already unresolved"
        ):
            self.module.debit_before_intent(
                entry,
                "download-roundtrip",
                "entry",
                self.module.LIMITS,
            )
        returned = self.module.debit_before_intent(
            entry,
            "download-roundtrip",
            "return",
            self.module.LIMITS,
        )
        self.assertEqual(returned["control_transactions"], 1)
        self.assertEqual(returned["component_effects_consumed"], 2)
        self.assertEqual(returned["component_effects_reserved"], 0)
        self.assertEqual(returned["roundtrip_returns"], 1)
        with self.assertRaisesRegex(
            self.module.ResearchPolicyError, "no unmatched"
        ):
            self.module.debit_before_intent(
                returned,
                "download-roundtrip",
                "return",
                self.module.LIMITS,
            )
        malformed = dict(counters)
        malformed["component_effects_consumed"] = False
        with self.assertRaisesRegex(
            self.module.ResearchPolicyError, "malformed"
        ):
            self.module.debit_before_intent(
                malformed,
                "reboot-system",
                "reboot",
                self.module.LIMITS,
            )

    def test_roundtrip_reserves_return_at_child_and_campaign_budget_edges(self):
        cases = (
            (self.module.LIMITS, 8, 7, 7, 8),
            (self.module.CAMPAIGN_LIMITS, 32, 31, 31, 32),
        )
        for limits, reject_roundtrips, reject_reboots, allow_roundtrips, allow_reboots in cases:
            counters = {
                "control_transactions": reject_roundtrips + reject_reboots,
                "component_effects_consumed": reject_roundtrips * 2 + reject_reboots,
                "component_effects_reserved": 0,
                "normal_reboots": reject_reboots,
                "download_roundtrips": reject_roundtrips,
                "roundtrip_entries": reject_roundtrips,
                "roundtrip_returns": reject_roundtrips,
            }
            with self.subTest(limits=limits), self.assertRaisesRegex(
                self.module.ResearchPolicyError, "budget is exhausted"
            ):
                self.module.debit_before_intent(
                    counters, "download-roundtrip", "entry", limits
                )
            counters = {
                "control_transactions": allow_roundtrips + allow_reboots,
                "component_effects_consumed": allow_roundtrips * 2 + allow_reboots,
                "component_effects_reserved": 0,
                "normal_reboots": allow_reboots,
                "download_roundtrips": allow_roundtrips,
                "roundtrip_entries": allow_roundtrips,
                "roundtrip_returns": allow_roundtrips,
            }
            entry = self.module.debit_before_intent(
                counters, "download-roundtrip", "entry", limits
            )
            self.assertEqual(
                entry["component_effects_consumed"]
                + entry["component_effects_reserved"],
                limits["component_effects_max"],
            )
            with self.assertRaisesRegex(
                self.module.ResearchPolicyError, "roundtrip is unresolved"
            ):
                self.module.debit_before_intent(
                    entry, "reboot-system", "reboot", limits
                )
            returned = self.module.debit_before_intent(
                entry, "download-roundtrip", "return", limits
            )
            self.assertEqual(returned["component_effects_reserved"], 0)
            self.assertEqual(
                returned["component_effects_consumed"],
                limits["component_effects_max"],
            )

    def test_counter_relationships_reject_forged_history_and_orphan_reservation(self):
        valid = {key: 0 for key in self.module.COUNTER_KEYS}
        forged = dict(valid)
        forged.update(
            {
                "download_roundtrips": 8,
                "roundtrip_entries": 8,
                "roundtrip_returns": 8,
            }
        )
        orphan = dict(valid)
        orphan["component_effects_reserved"] = 1
        for counters in (forged, orphan):
            with self.subTest(counters=counters), self.assertRaisesRegex(
                self.module.ResearchPolicyError, "relationships are invalid"
            ):
                self.module.debit_before_intent(
                    counters, "reboot-system", "reboot", self.module.LIMITS
                )

    def test_live_recovery_authority_is_deferred_to_fixed_current_guard_chain(self):
        self.assertFalse(hasattr(self.module, "validate_recovery_node"))
        requirements = self.plan["binding"]["live_coordinator_requirements"]
        self.assertTrue(requirements)
        self.assertTrue(all(value is True for value in requirements.values()))
        for key in (
            "fixed_private_campaign_guard_path",
            "bounded_no_follow_canonical_duplicate_safe_reads",
            "derive_campaign_session_policy_source_and_ordinal_from_current_guard",
            "derive_endpoint_from_current_validated_arrival",
            "hash_actual_validated_predecessor_bytes",
            "validate_full_opening_entry_arrival_return_chain",
            "ordinal_equals_current_campaign_roundtrip_count",
            "exact_child_membership_in_current_campaign",
            "atomic_both_scope_counters_and_intent",
            "debit_only_or_partial_scope_has_zero_authority",
            "expiry_recovery_only_from_current_guard_chain",
            "hostile_old_foreign_duplicate_noncanonical_and_cut_fixtures",
        ):
            self.assertIn(key, requirements)

    def test_source_drift_rejects_render(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.py"
            path.write_bytes(b"changed")
            spec = {
                "path": path,
                "size": len(b"changed"),
                "sha256": "0" * 64,
            }
            with self.assertRaisesRegex(
                self.module.ResearchPolicyError, "source bytes changed"
            ):
                self.module.read_exact_source(spec, "hostile")

    def test_policy_target_goal_and_report_preserve_pending_boundary(self):
        common = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        target = (
            ROOT
            / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
        ).read_text(encoding="utf-8")
        goal = (ROOT / "GOAL_S20PLUS.md").read_text(encoding="utf-8")
        report = REPORT.read_text(encoding="utf-8")
        self.assertIn("S20+ Bounded Autonomous Research Delegation", common)
        self.assertIn("H0 POLICY PASS_GO - NOT ACTIVE", target)
        self.assertIn("autonomous research session", goal)
        self.assertIn("PASS_GO - POLICY H0 ONLY - NOT ACTIVE", report)
        for text in (target, goal, report):
            self.assertIn(str(SCRIPT.relative_to(ROOT)), text)

    def test_cli_emits_only_dormant_plan(self):
        import subprocess

        result = subprocess.run(
            ["python3", str(SCRIPT), "--render-plan"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        value = json.loads(result.stdout)
        self.assertFalse(value["active"])
        self.assertEqual(value["device_commands"], [])


if __name__ == "__main__":
    unittest.main()

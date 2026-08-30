import ast
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_coordinator_h0.py"
)
EVIDENCE_TEST_SCRIPT = (
    ROOT / "tests/test_s20plus_g986n_autonomous_public_health_evidence_h0.py"
)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


M = load_module("s20plus_g986n_autonomous_public_health_read_leaf_tested", SCRIPT)
ET = load_module("s20plus_g986n_autonomous_public_health_evidence_fixtures", EVIDENCE_TEST_SCRIPT)
E = ET.M
F = ET.Fixture


def reject(callable_, *args, **kwargs):
    with unittest.TestCase().assertRaises(M.ReadLeafH0Error):
        callable_(*args, **kwargs)


def exact_payload(size):
    if type(size) is not int or size < len(b'{"pad":""}\n'):
        raise ValueError("test payload size is too small")
    return M.canonical_bytes({"pad": "x" * (size - len(b'{"pad":""}\n'))})


def sized_structural(sizes=None):
    sizes = sizes or {name: 64 for name in M.FINAL_STRUCTURAL_NAMES}
    return {name: exact_payload(sizes[name]) for name in M.FINAL_STRUCTURAL_NAMES}


def model_pending_exact(*args):
    return M.model_ordinal_one_pending(
        *args,
        base_session_names=M.BASE_INITIAL_SESSION_NAMES,
        leaf_names=(),
    )


def pending_fixture(**allocation_kwargs):
    allocation, context, context_raw, head, head_raw = F.allocation(**allocation_kwargs)
    return model_pending_exact(
        allocation,
        context,
        context_raw,
        head,
        head_raw,
        context["current_time"],
    )


def evidence_completion(pending=None, *, result_completed_at=1_040, cut=None):
    pending = pending or pending_fixture()
    records = F.records(pending["intent"])
    receipts = E.build_command_receipts(pending["intent_raw"], records)
    result = E.model_validated_read_result(
        pending["accounting_opening"],
        pending["accounting_opening_raw"],
        pending["protocol_state"],
        pending["lease"],
        pending["lease_raw"],
        pending["observed_at"],
        pending["intent"],
        pending["intent_raw"],
        records,
        receipts,
        result_completed_at,
        cut,
    )
    result_raw = E.canonical_bytes(result)
    completion = E.model_future_completion(result, result_raw, result_completed_at)
    return {
        "pending": pending,
        "records": records,
        "receipts": receipts,
        "result": result,
        "result_raw": result_raw,
        "completion": completion,
        "completion_raw": E.canonical_bytes(completion),
    }


def finish(
    bundle,
    *,
    base_session_names=M.BASE_INITIAL_SESSION_NAMES,
    leaf_names=M.LEAF_PENDING_NAMES,
):
    return M.complete_pending_parked(
        bundle["pending"],
        bundle["result"],
        bundle["result_raw"],
        bundle["completion"],
        bundle["completion_raw"],
        bundle["records"],
        bundle["receipts"],
        base_session_names=base_session_names,
        leaf_names=leaf_names,
    )


class S20PlusAutonomousPublicHealthReadLeafH0Test(unittest.TestCase):
    def test_01_render_plan_is_permanent_h0_and_all_gates_false(self):
        plan = M.render_plan()
        self.assertEqual(
            plan["status"],
            "H0_AUTONOMOUS_PUBLIC_HEALTH_READ_LEAF_PASS_GO_NOT_ACTIVE",
        )
        self.assertTrue(plan["permanent_h0_only"])
        for key in (
            "read_leaf_active",
            "live_authority",
            "mechanically_activatable",
            "coordinator_integrated",
            "private_filesystem_writer",
            "execution_integrated",
            "trusted_clock_proven",
            "durable_publication_proven",
        ):
            self.assertIs(plan[key], False)

    def test_02_render_plan_has_no_action_backend_or_transfer(self):
        plan = M.render_plan()
        for key in (
            "device_commands",
            "device_effects",
            "control_actions",
            "terminal_actions",
            "f1_actions",
            "partition_transfers",
            "callbacks",
            "backends",
        ):
            self.assertEqual(plan[key], [])
        self.assertFalse(plan["base_coordinator_imported_or_executed"])

    def test_03_cli_is_render_plan_only(self):
        good = subprocess.run(
            [sys.executable, str(SCRIPT), "--render-plan"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(json.loads(good.stdout)["cli"], ["--render-plan"])
        for argv in ([], ["--connected"], ["--render-plan", "--connected"]):
            bad = subprocess.run(
                [sys.executable, str(SCRIPT), *argv],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(bad.returncode, 0)

    def test_04_live_stubs_reject(self):
        for name in (
            "begin_live_read",
            "publish_live_lease",
            "execute_live_return",
            "complete_live_read",
        ):
            reject(getattr(M, name))

    def test_05_source_has_no_writer_transport_or_command_import(self):
        payload = SCRIPT.read_bytes()
        tree = ast.parse(payload.decode())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue(
            imported.isdisjoint(
                {"subprocess", "socket", "requests", "urllib", "shutil", "tempfile"}
            )
        )
        for token in (
            b"O_WRONLY",
            b"O_CREAT",
            b"os.write",
            b"atomic_publish",
            b"durable_json",
            b"Popen",
            b"adb shell",
            b"odin4",
        ):
            self.assertNotIn(token, payload)

    def test_06_frozen_base_is_not_imported_as_module(self):
        self.assertFalse(
            any(
                getattr(value, "__name__", "").endswith(
                    "s20plus_g986n_autonomous_research_coordinator_h0"
                )
                for value in M.__dict__.values()
            )
        )
        source = SCRIPT.read_text()
        self.assertNotIn("import s20plus_g986n_autonomous_research_coordinator_h0", source)
        self.assertNotIn("from s20plus_g986n_autonomous_research_coordinator_h0", source)
        self.assertIsInstance(M._EVIDENCE, type(M.SOURCE_SPECS))
        for function in M._EVIDENCE.values():
            if callable(function):
                globals_ = function.__globals__
                self.assertNotIn("subprocess", globals_)
                self.assertNotIn("atomic_publish", globals_)
                self.assertNotIn("durable_json", globals_)

    def test_07_exact_source_closure_and_normalized_identity(self):
        receipts = M.source_receipts()
        self.assertEqual(
            receipts["base_coordinator"]["sha256"], M.BASE_COORDINATOR_SHA256
        )
        self.assertEqual(
            receipts["evidence_owner"]["sha256"], M.EVIDENCE_OWNER_SHA256
        )
        self.assertEqual(
            receipts["evidence_transitive"]["owner"]["normalized_sha256"],
            M.EVIDENCE_OWNER_NORMALIZED_SHA256,
        )

    def test_08_mutated_or_cross_labeled_source_bytes_reject(self):
        base = bytearray(M._BASE_SOURCE)
        base[-1] ^= 1
        reject(M._verify_source_payload, "base_coordinator", bytes(base))
        evidence = bytearray(M._EVIDENCE_SOURCE)
        evidence[0] ^= 1
        reject(M._verify_source_payload, "evidence_owner", bytes(evidence))
        reject(M._verify_source_payload, "base_coordinator", M._EVIDENCE_SOURCE)
        reject(M._verify_source_payload, "foreign", b"x")

    def test_09_strict_canonical_json_rejects_duplicates_and_alternate_bytes(self):
        reject(M.parse_canonical_json, b'{"x":1,"x":1}\n', "duplicate")
        reject(M.parse_canonical_json, b'{"x": 1}\n', "spacing")
        reject(M.parse_canonical_json, b'{"x":NaN}\n', "nan")
        reject(M.parse_canonical_json, b"", "empty")
        self.assertEqual(M.parse_canonical_json(b'{"x":1}\n', "valid"), {"x": 1})

    def test_10_exact_initial_allocation_models_ordinal_one_pending(self):
        pending = pending_fixture()
        state = M.validate_state(pending["state"])
        self.assertEqual(state["phase"], "pending")
        self.assertEqual(state["read_ordinal"], 1)
        self.assertEqual(
            state["child_counters"]["private_evidence_bytes_reserved"],
            M.READ_RESERVATION_BYTES,
        )
        self.assertEqual(
            pending["lease"]["coordinator_context"], pending["current_context"]
        )
        self.assertIn(
            "leaf/public-health-read-lease-000001.json",
            M.PENDING_STRUCTURAL_NAMES,
        )
        self.assertTrue(state["campaign_parked"])
        self.assertFalse(state["controls_authorized"])

    def test_11_pending_bundle_round_trip_is_exact(self):
        pending = pending_fixture()
        self.assertEqual(M.validate_pending_bundle(pending), pending)
        changed = copy.deepcopy(pending)
        changed["state"]["intent_sha256"] = "0" * 64
        reject(M.validate_pending_bundle, changed)

    def test_12_target_or_attended_opening_drift_rejects(self):
        allocation, context, context_raw, head, head_raw = F.allocation()
        allocation["opening"]["target"]["model"] = "SM-S906N"
        allocation["opening_raw"] = E.canonical_bytes(allocation["opening"])
        reject(
            model_pending_exact,
            allocation,
            context,
            context_raw,
            head,
            head_raw,
            context["current_time"],
        )
        allocation, context, context_raw, head, head_raw = F.allocation()
        allocation["opening"]["attended_opening"] = False
        allocation["opening_raw"] = E.canonical_bytes(allocation["opening"])
        reject(
            model_pending_exact,
            allocation,
            context,
            context_raw,
            head,
            head_raw,
            context["current_time"],
        )

    def test_13_guard_opening_session_raw_drift_rejects(self):
        for raw_name in ("guard_raw", "opening_raw", "session_raw"):
            allocation, context, context_raw, head, head_raw = F.allocation()
            allocation[raw_name] += b" "
            reject(
                model_pending_exact,
                allocation,
                context,
                context_raw,
                head,
                head_raw,
                context["current_time"],
            )

    def test_14_head_must_be_byte_identical_session_opening(self):
        allocation, context, context_raw, head, head_raw = F.allocation()
        changed = copy.deepcopy(head)
        changed["no_replay"] = False
        reject(
            model_pending_exact,
            allocation,
            context,
            context_raw,
            changed,
            E.canonical_bytes(changed),
            context["current_time"],
        )
        reject(
            model_pending_exact,
            allocation,
            context,
            context_raw,
            head,
            head_raw + b" ",
            context["current_time"],
        )

    def test_15_source_boot_or_head_hash_drift_rejects(self):
        for key in ("serial_sha256", "topology_sha256", "boot_id_sha256"):
            allocation, context, _, head, head_raw = F.allocation()
            context["source_identity"][key] = "f" * 64
            context_raw = E.canonical_bytes(context)
            reject(
                model_pending_exact,
                allocation,
                context,
                context_raw,
                head,
                head_raw,
                context["current_time"],
            )
        allocation, context, _, head, head_raw = F.allocation()
        context["predecessor_sha256"] = "f" * 64
        reject(
            model_pending_exact,
            allocation,
            context,
            E.canonical_bytes(context),
            head,
            head_raw,
            context["current_time"],
        )

    def test_16_expired_or_time_drift_context_rejects(self):
        allocation, context, _, head, head_raw = F.allocation(
            current_time=F.session_expiry
        )
        reject(
            model_pending_exact,
            allocation,
            context,
            E.canonical_bytes(context),
            head,
            head_raw,
            context["current_time"],
        )
        allocation, context, context_raw, head, head_raw = F.allocation()
        reject(
            model_pending_exact,
            allocation,
            context,
            context_raw,
            head,
            head_raw,
            context["current_time"] + 1,
        )

    def test_17_nonzero_control_state_rejects(self):
        allocation, context, _, head, head_raw = F.allocation(
            child_control=ET.control_counters(normal=1),
            campaign_control=ET.control_counters(normal=1),
        )
        reject(
            model_pending_exact,
            allocation,
            context,
            E.canonical_bytes(context),
            head,
            head_raw,
            context["current_time"],
        )

    def test_18_read_counter_carry_or_bool_integer_rejects(self):
        pending = pending_fixture()
        for scope in ("child_counters", "campaign_counters"):
            changed = copy.deepcopy(pending)
            changed["protocol_state"][scope]["read_operations"] = 1
            reject(M.validate_pending_bundle, changed)
        changed = copy.deepcopy(pending["state"])
        changed["structural_node_count"] = True
        reject(M.validate_state, changed)
        changed = copy.deepcopy(pending)
        changed["current_context"]["current_time"] = True
        changed["current_context_raw"] = E.canonical_bytes(changed["current_context"])
        reject(M.validate_pending_bundle, changed)

    def test_19_one_scope_lease_accounting_drift_rejects(self):
        pending = pending_fixture()
        changed = copy.deepcopy(pending)
        changed["lease"]["campaign_counters"]["read_operations"] = 0
        changed["lease_raw"] = E.canonical_bytes(changed["lease"])
        reject(M.validate_pending_bundle, changed)
        changed = copy.deepcopy(pending)
        changed["lease"]["reservation_bytes"] -= 1
        changed["lease_raw"] = E.canonical_bytes(changed["lease"])
        reject(M.validate_pending_bundle, changed)

    def test_20_second_lease_or_previous_result_carry_rejects(self):
        pending = pending_fixture()
        changed = copy.deepcopy(pending)
        changed["lease"]["read_ordinal"] = 2
        changed["lease_raw"] = E.canonical_bytes(changed["lease"])
        reject(M.validate_pending_bundle, changed)
        changed = copy.deepcopy(pending)
        changed["lease"]["previous_evidence_result_sha256"] = "a" * 64
        changed["lease_raw"] = E.canonical_bytes(changed["lease"])
        reject(M.validate_pending_bundle, changed)

    def test_21_separate_namespace_accepts_only_exact_phase_names(self):
        self.assertEqual(
            M.validate_separate_namespaces(
                "initial", M.BASE_INITIAL_SESSION_NAMES, ()
            )["phase"],
            "initial",
        )
        self.assertEqual(
            M.validate_separate_namespaces(
                "pending", M.BASE_INITIAL_SESSION_NAMES, M.LEAF_PENDING_NAMES
            )["phase"],
            "pending",
        )
        self.assertEqual(
            M.validate_separate_namespaces(
                "parked", M.BASE_INITIAL_SESSION_NAMES, M.LEAF_PARKED_NAMES
            )["phase"],
            "parked",
        )

    def test_22_old_coordinator_augmented_names_always_reject(self):
        for name in (
            "public-health-read-lease-000001.json",
            "public-health-read-complete-000001.json",
            "terminal.json",
            "baseline-000001.json",
        ):
            reject(
                M.validate_separate_namespaces,
                "pending",
                (*M.BASE_INITIAL_SESSION_NAMES, name),
                M.LEAF_PENDING_NAMES,
            )

    def test_23_sibling_gap_duplicate_and_second_ordinal_names_reject(self):
        variants = (
            (),
            (*M.LEAF_PENDING_NAMES, "reboot-intent-000001.json"),
            (*M.LEAF_PENDING_NAMES, "public-health-read-lease-000002.json"),
            (*M.LEAF_PENDING_NAMES, *M.LEAF_PENDING_NAMES),
        )
        for names in variants:
            reject(
                M.validate_separate_namespaces,
                "pending",
                M.BASE_INITIAL_SESSION_NAMES,
                names,
            )

    def test_24_initial_and_pending_successor_are_exact(self):
        self.assertEqual(
            M.validate_successor("initial", "public-health-read-lease"),
            "public-health-read-lease",
        )
        self.assertEqual(
            M.validate_successor("pending", "public-health-read-complete"),
            "public-health-read-complete",
        )

    def test_25_control_terminal_f1_and_sibling_successors_reject(self):
        for phase in ("initial", "pending"):
            for successor in (
                "reboot-system",
                "download-roundtrip",
                "terminal",
                "prepare-f1-readiness",
                "f1-intent",
                "public-health-read-sibling",
            ):
                reject(M.validate_successor, phase, successor)

    def test_26_full_frozen_evidence_completion_yields_parked_state(self):
        bundle = evidence_completion()
        final = finish(bundle)
        state = M.validate_state(final["state"])
        self.assertEqual(state["phase"], "parked")
        self.assertTrue(state["campaign_parked"])
        self.assertFalse(state["pending_effect"])
        self.assertEqual(state["structural_node_count"], 8)
        self.assertEqual(final["evidence_protocol_state"]["read_ordinal"], 1)

    def test_27_completion_is_always_zero_command_and_blocks_everything(self):
        final = finish(evidence_completion())
        state = final["state"]
        self.assertEqual(state["reporting_device_command_count"], 0)
        self.assertEqual(state["reporting_device_effect_count"], 0)
        for key in (
            "controls_authorized",
            "terminal_authorized",
            "f1_authorized",
            "second_lease_authorized",
        ):
            self.assertFalse(state[key])
        self.assertEqual(final["completion"]["completion_mode"], "permanent-h0-parked")

    def test_28_result_hash_or_raw_swap_rejects(self):
        bundle = evidence_completion()
        changed = copy.deepcopy(bundle)
        changed["result"]["coordinator_lease_sha256"] = "f" * 64
        changed["result_raw"] = E.canonical_bytes(changed["result"])
        reject(finish, changed)
        changed = copy.deepcopy(bundle)
        changed["result_raw"] = bundle["result_raw"] + b" "
        reject(finish, changed)

    def test_29_completion_hash_flags_or_counter_swap_rejects(self):
        bundle = evidence_completion()
        mutations = (
            ("evidence_result_sha256", "f" * 64),
            ("campaign_parked", False),
            ("controls_unblocked", True),
        )
        for key, value in mutations:
            changed = copy.deepcopy(bundle)
            changed["completion"][key] = value
            changed["completion_raw"] = E.canonical_bytes(changed["completion"])
            reject(finish, changed)
        changed = copy.deepcopy(bundle)
        changed["completion"]["campaign_counters"]["private_evidence_bytes_consumed"] += 1
        changed["completion_raw"] = E.canonical_bytes(changed["completion"])
        reject(finish, changed)

    def test_30_raw_return_or_receipt_swap_rejects_full_revalidation(self):
        bundle = evidence_completion()
        changed = copy.deepcopy(bundle)
        changed["records"][3]["stdout"] += b"x"
        reject(finish, changed)
        changed = copy.deepcopy(bundle)
        changed["receipts"] = list(changed["receipts"])
        changed["receipts"][0], changed["receipts"][1] = (
            changed["receipts"][1], changed["receipts"][0]
        )
        reject(finish, changed)

    def test_31_parked_state_admits_no_successor_or_double_settlement(self):
        final = finish(evidence_completion())
        for successor in (
            "public-health-read-lease",
            "public-health-read-complete",
            "reboot-system",
            "terminal",
            "f1-intent",
        ):
            reject(M.reject_any_successor_from_parked, final["state"], successor)
        reject(M.validate_pending_bundle, final)

    def test_32_cut_classifier_preserves_no_replay_at_every_cross_root_cut(self):
        cases = (
            (False, False, False, False, "NO_LEASE_NO_AUTHORITY"),
            (True, False, False, False, "LEASE_PRESENT_MIRROR_UNPROVED_PARKED"),
            (True, True, False, False, "PENDING_EVIDENCE_UNCERTAIN_CONSUMED_PARKED"),
            (True, True, True, False, "RESULT_PRESENT_COMPLETION_UNPROVED_PARKED"),
            (True, True, True, True, "COMPLETION_PRESENT_SETTLEMENT_UNPROVED_PARKED"),
        )
        for lease, intent, result, completion, status in cases:
            value = M.classify_cut(
                lease_present=lease,
                intent_present=intent,
                result_present=result,
                completion_present=completion,
            )
            self.assertEqual(value["status"], status)
            self.assertFalse(value["replay_authorized"])
            self.assertFalse(value["next_read_authorized"])
            self.assertFalse(value["control_authorized"])

    def test_33_unvalidated_completion_never_claims_settlement(self):
        value = M.classify_cut(
            lease_present=True,
            intent_present=True,
            result_present=True,
            completion_present=True,
        )
        self.assertFalse(value["settlement_validated"])
        self.assertEqual(value["reservation_state"], "RETAINED_OR_UNPROVED")
        full = finish(evidence_completion())["validated_settlement"]
        self.assertTrue(full["settlement_validated"])
        self.assertEqual(full["reservation_state"], "SETTLED")

    def test_34_impossible_cut_ancestry_and_bool_integer_reject(self):
        invalid = (
            (False, True, False, False),
            (True, False, True, False),
            (True, True, False, True),
        )
        for lease, intent, result, completion in invalid:
            reject(
                M.classify_cut,
                lease_present=lease,
                intent_present=intent,
                result_present=result,
                completion_present=completion,
            )
        reject(
            M.classify_cut,
            lease_present=1,
            intent_present=False,
            result_present=False,
            completion_present=False,
        )

    def test_35_real_final_structural_set_has_exact_eight_nodes(self):
        final = finish(evidence_completion())
        proof = final["structural_accounting"]
        self.assertEqual(proof["node_count"], M.STRUCTURAL_NODE_COUNT)
        self.assertEqual(set(proof["per_node"]), set(M.FINAL_STRUCTURAL_NAMES))
        self.assertEqual(
            [item["node_count"] for item in proof["progression"].values()],
            [3, 4, 5, 6, 7, 8],
        )
        self.assertEqual(proof["child_journal_bytes"], proof["campaign_journal_bytes"])
        self.assertLessEqual(proof["actual_bytes"], 49_152)
        self.assertFalse(proof["writer_enforced"])

    def test_36_individual_structural_node_caps_accept_edge_and_reject_plus_one(self):
        for name, cap in M.STRUCTURAL_NODE_CAPS.items():
            values = {item: 64 for item in M.FINAL_STRUCTURAL_NAMES}
            values[name] = cap
            proof = M.validate_structural_journal(sized_structural(values))
            self.assertEqual(proof["per_node"][name]["size"], cap)
            values[name] = cap + 1
            reject(M.validate_structural_journal, sized_structural(values))

    def test_37_aggregate_structural_cap_accepts_exact_edge(self):
        sizes = dict(M.STRUCTURAL_NODE_CAPS)
        sizes["evidence/accounting-opening.json"] = 8 * 1024
        self.assertEqual(sum(sizes.values()), 49_152)
        proof = M.validate_structural_journal(sized_structural(sizes))
        self.assertEqual(proof["actual_bytes"], 49_152)
        self.assertEqual(proof["child_journal_bytes"], 49_152)
        self.assertEqual(proof["campaign_journal_bytes"], 49_152)

    def test_38_aggregate_structural_cap_rejects_even_if_each_node_fits(self):
        sizes = dict(M.STRUCTURAL_NODE_CAPS)
        self.assertEqual(sum(sizes.values()), 57_344)
        reject(M.validate_structural_journal, sized_structural(sizes))

    def test_39_structural_names_count_order_canonical_and_type_are_strict(self):
        values = sized_structural()
        reject(M.validate_structural_journal, dict(list(values.items())[:-1]))
        reordered = dict(reversed(list(values.items())))
        reject(M.validate_structural_journal, reordered)
        changed = dict(values)
        changed[M.FINAL_STRUCTURAL_NAMES[0]] = b'{"x": 1}\n'
        reject(M.validate_structural_journal, changed)
        changed = dict(values)
        changed[M.FINAL_STRUCTURAL_NAMES[0]] = "not-bytes"
        reject(M.validate_structural_journal, changed)

    def test_40_transient_context_bound_is_strict_and_not_charged(self):
        at_cap = exact_payload(M.TRANSIENT_CURRENT_CONTEXT_MAX_BYTES)
        proof = M.validate_transient_current_context(at_cap)
        self.assertEqual(proof["size"], M.TRANSIENT_CURRENT_CONTEXT_MAX_BYTES)
        self.assertFalse(proof["standalone_node_retained"])
        self.assertFalse(proof["standalone_node_separately_charged"])
        self.assertTrue(proof["canonical_value_lease_embedding_required"])
        self.assertTrue(
            proof["embedded_bytes_must_be_charged_with_lease_structural_cap"]
        )
        reject(
            M.validate_transient_current_context,
            exact_payload(M.TRANSIENT_CURRENT_CONTEXT_MAX_BYTES + 1),
        )

    def test_41_evidence_and_structural_budgets_are_distinct(self):
        plan = M.render_plan()
        self.assertEqual(plan["evidence_accounting"]["reservation_bytes"], 524_288)
        self.assertEqual(plan["evidence_accounting"]["proof_max_bytes"], 507_904)
        self.assertEqual(plan["structural_journal"]["child_max_bytes"], 49_152)
        self.assertEqual(plan["structural_journal"]["campaign_max_bytes"], 49_152)
        self.assertTrue(
            finish(evidence_completion())["structural_accounting"]
            ["separate_from_evidence_reservation"]
        )

    def test_42_future_writer_clock_durability_and_same_uid_are_unproved(self):
        plan = M.render_plan()
        self.assertTrue(
            plan["structural_journal"]["future_writer_enforcement_required"]
        )
        self.assertEqual(plan["clock_provenance"], "unproved-numeric-model-only")
        self.assertFalse(plan["durable_order_proven"])
        self.assertEqual(
            plan["same_uid_concurrent_writer"],
            "outside-threat-model-stop-no-live-authority",
        )

    def test_43_completion_rechecks_pending_namespace_and_rejects_sibling(self):
        bundle = evidence_completion()
        reject(
            finish,
            bundle,
            leaf_names=(*M.LEAF_PENDING_NAMES, "public-health-read-lease-000002.json"),
        )
        reject(
            finish,
            bundle,
            base_session_names=(*M.BASE_INITIAL_SESSION_NAMES, "terminal.json"),
        )

    def test_44_standalone_state_validator_rejects_id_source_and_counter_forgery(self):
        state = copy.deepcopy(pending_fixture()["state"])
        state["campaign_id"] = "not-an-id"
        reject(M.validate_state, state)
        state = copy.deepcopy(pending_fixture()["state"])
        state["read_ordinal"] = True
        reject(M.validate_state, state)
        state = copy.deepcopy(pending_fixture()["state"])
        state["source_identity"]["boot_id_sha256"] = "not-a-hash"
        reject(M.validate_state, state)
        state = copy.deepcopy(pending_fixture()["state"])
        state["campaign_counters"]["private_evidence_bytes_reserved"] = 0
        reject(M.validate_state, state)
        state = copy.deepcopy(pending_fixture()["state"])
        state["current_head_sha256"] = "f" * 64
        reject(M.validate_state, state)

    def test_45_structural_layout_names_all_three_exact_roots(self):
        plan = M.render_plan()
        roots = plan["fixed_roots"]
        self.assertEqual(set(roots), {"base_coordinator", "evidence_owner", "read_leaf"})
        self.assertEqual(plan["structural_journal"]["fixed_root_count"], 3)
        actual_names = {
            value["actual_name"]
            for value in plan["structural_journal"]["node_layout"].values()
        }
        self.assertEqual(
            actual_names,
            {
                "active-campaign.json",
                "opening.json",
                "session-opening.json",
                "accounting-opening.json",
                "public-health-read-lease-000001.json",
                "read-intent-000001.json",
                "read-result-000001.json",
                "public-health-read-complete-000001.json",
            },
        )
        self.assertTrue(plan["selected_evidence_callable_globals_are_non_authoritative"])

    def test_46_phase_heads_follow_session_to_lease_to_completion(self):
        pending = pending_fixture()
        self.assertEqual(
            pending["state"]["admission_head_sha256"],
            pending["state"]["base_session_sha256"],
        )
        self.assertEqual(
            pending["state"]["current_head_sha256"],
            pending["state"]["lease_sha256"],
        )
        changed = copy.deepcopy(pending["state"])
        changed["current_head_sha256"] = changed["admission_head_sha256"]
        reject(M.validate_state, changed)

        final = finish(evidence_completion(pending))
        self.assertEqual(
            final["state"]["current_head_sha256"],
            final["state"]["completion_sha256"],
        )
        changed = copy.deepcopy(final["state"])
        changed["current_head_sha256"] = changed["lease_sha256"]
        reject(M.validate_state, changed)


if __name__ == "__main__":
    unittest.main()

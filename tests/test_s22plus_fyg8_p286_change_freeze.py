from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p286_change_freeze as freeze  # noqa: E402
import s22plus_fyg8_p286_candidate_intent as candidate_intent  # noqa: E402
import build_s22plus_fyg8_p286_candidate as candidate_builder  # noqa: E402
import s22plus_fyg8_p286_build as candidate_build  # noqa: E402
import s22plus_fyg8_p286_build_repro_check as repro  # noqa: E402
import s22plus_fyg8_p286_candidate_static_checker as static_checker  # noqa: E402
import s22plus_fyg8_p286_contract_spec as spec  # noqa: E402
import s22plus_fyg8_p282_linked_audit as p282_linked  # noqa: E402
import s22plus_fyg8_p286_linked_audit as linked_audit  # noqa: E402
import s22plus_fyg8_p286_pre_lto_qualification as qualification  # noqa: E402
import s22plus_fyg8_p286_source_contract as source_contract  # noqa: E402
import s22plus_fyg8_p286_source_contracts as selectors  # noqa: E402
import s22plus_fyg8_p286_trace_contract as trace_contract  # noqa: E402


class P286ChangeFreezeTests(unittest.TestCase):
    def test_exact_candidate_and_d1_requirements_are_frozen(self):
        self.assertEqual(
            tuple(key for key, _ in freeze.CANDIDATE_CHANGE_REQUIREMENTS),
            (
                "parent-runtime-status-gate",
                "bounded-helper-reap",
                "actual-outer-work-probes",
                "helper-dispatch-completion-split",
                "restart-failure-partition",
                "residual-outer-tail-bound",
                "identity-closure-enforcement",
            ),
        )
        self.assertEqual(
            tuple(key for key, _ in freeze.D1_CHANGE_REQUIREMENTS),
            (
                "instance-trace-spelling",
                "immediate-watchdog-disarm",
                "comm-newline-removal",
                "remove-unapproved-endpoint-count",
            ),
        )

    def test_payload_and_support_partitions_are_exact(self):
        self.assertEqual(
            set(freeze.PAYLOAD_SOURCE_PATHS),
            {
                "p286_contract_spec",
                "p286_source_contract",
                "p286_candidate_intent",
                "p286_e3_runtime_include",
                "p286_classifier_include",
                "p286_trace_contract",
                "p286_userspace_build",
                "p286_candidate_builder",
                "p286_build",
                "p286_boot_only_packager",
            },
        )
        self.assertEqual(
            set(freeze.NON_IDENTITY_SUPPORT_PATHS),
            {
                "p286_change_freeze",
                "p286_freeze_report",
                "p286_candidate_contract",
                "p286_source_contract_selector",
                "p286_build_repro_check",
                "p286_candidate_static_checker",
                "p286_e2_stock_closure",
                "p286_linked_audit",
                "p286_pre_lto_qualification",
                "p286_decoder_adapter",
            },
        )
        payload_paths = set(freeze.PAYLOAD_SOURCE_PATHS.values())
        support_paths = set(freeze.NON_IDENTITY_SUPPORT_PATHS.values())
        self.assertEqual(len(payload_paths), 10)
        self.assertEqual(len(support_paths), 10)
        self.assertTrue(payload_paths.isdisjoint(support_paths))

    def test_p284_is_inherited_without_a_mutation_path(self):
        inherited = {
            path.as_posix()
            for path in freeze.inherited_direct_source_paths().values()
        }
        payload = {
            path.as_posix() for path in freeze.PAYLOAD_SOURCE_PATHS.values()
        }
        self.assertEqual(len(freeze.p284.SOURCE_KEYS), 60)
        self.assertEqual(len(inherited), 55)
        self.assertEqual(len(freeze.GENERATED_SOURCE_KEYS), 5)
        self.assertTrue(inherited.isdisjoint(payload))

    def test_only_payload_overlays_become_source_keys(self):
        result = freeze.validate_freeze(ROOT)
        rows = {
            row["source_key"]: row["path"] for row in result["source_keys"]
        }
        self.assertEqual(result["source_key_counts"]["planned_payload"], 10)
        self.assertEqual(result["source_key_counts"]["planned_total"], 70)
        self.assertEqual(
            result["source_key_counts"]["bundle_bound_support"],
            10,
        )
        for key, path in freeze.PAYLOAD_SOURCE_PATHS.items():
            self.assertEqual(rows[key], path.as_posix())
        for key, path in freeze.NON_IDENTITY_SUPPORT_PATHS.items():
            self.assertNotIn(key, rows)
            self.assertNotIn(path.as_posix(), rows.values())

    def test_d1_mutations_are_private_and_do_not_overlap_candidate(self):
        result = freeze.validate_freeze(ROOT)
        self.assertEqual(result["candidate_d1_overlap_count"], 0)
        self.assertTrue(
            all(
                path.startswith(
                    "workspace/private/outputs/"
                    "s22plus_fyg8_p284_stock_outer_d1_v3/"
                )
                for path in result["d1_private_mutation_paths"]
            )
        )
        self.assertNotIn(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p284_stock_outer_d1_spec.py",
            result["d1_private_mutation_paths"],
        )

    def test_declared_change_set_is_bidirectional_and_fail_closed(self):
        actual = (
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p286_change_freeze.py"
        )
        result = freeze.validate_declared_change_set(
            derived_paths=(actual,),
            declared_paths=(actual,),
        )
        self.assertEqual(result["git_derived_paths"], (actual,))
        self.assertEqual(result["declared_paths"], (actual,))
        with self.assertRaisesRegex(
            freeze.FreezeError,
            "missing_declarations",
        ):
            freeze.validate_declared_change_set(
                derived_paths=(actual,),
                declared_paths=(),
            )
        with self.assertRaisesRegex(
            freeze.FreezeError,
            "overdeclared",
        ):
            freeze.validate_declared_change_set(
                derived_paths=(),
                declared_paths=(actual,),
            )
        outside = "workspace/public/src/native-init/unfrozen.c"
        with self.assertRaisesRegex(
            freeze.FreezeError,
            "outside the frozen change window",
        ):
            freeze.validate_declared_change_set(
                derived_paths=(outside,),
                declared_paths=(outside,),
            )

    def test_git_derivation_unions_committed_dirty_and_untracked_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def git(*args: str) -> str:
                completed = subprocess.run(
                    ("git", *args),
                    cwd=root,
                    check=True,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                return completed.stdout.strip()

            git("init", "-q")
            git("config", "user.name", "P286 Freeze Test")
            git("config", "user.email", "p286-freeze@example.invalid")
            (root / "tracked.txt").write_text("base\n", encoding="utf-8")
            git("add", "tracked.txt")
            git("commit", "-q", "-m", "base")
            base = git("rev-parse", "HEAD")

            (root / "committed.txt").write_text("committed\n", encoding="utf-8")
            git("add", "committed.txt")
            git("commit", "-q", "-m", "committed change")
            (root / "tracked.txt").write_text("dirty\n", encoding="utf-8")
            (root / "untracked.txt").write_text("untracked\n", encoding="utf-8")

            self.assertEqual(
                freeze.git_derived_changed_paths(root, base),
                ("committed.txt", "tracked.txt", "untracked.txt"),
            )

    def test_porcelain_rename_includes_both_paths(self):
        self.assertEqual(
            freeze._porcelain_paths(b"R  new-name\0old-name\0"),
            {"new-name", "old-name"},
        )

    def test_completed_overlay_closure_is_ready_but_still_pre_intent(self):
        result = freeze.validate_freeze(ROOT)
        self.assertTrue(result["pre_intent_ready"])
        self.assertFalse(result["intent_derived"])
        self.assertFalse(result["build_executed"])
        self.assertFalse(result["device_contact"])
        self.assertFalse(result["live_authorized"])
        self.assertEqual(result["missing_payload_source_paths"], [])
        self.assertEqual(result["missing_bundle_bound_support_paths"], [])
        self.assertEqual(result["missing_planned_paths"], [])
        self.assertEqual(
            result["inherited_receipts"]["run_id"],
            freeze.P284_FROZEN_RUN_ID,
        )
        self.assertEqual(
            result["inherited_receipts"]["receipt_count"],
            60,
        )
        self.assertTrue(result["inherited_receipts"]["verified"])

    def test_generated_source_rows_are_explicit(self):
        result = freeze.validate_freeze(ROOT)
        generated = {
            row["source_key"]: row["path"]
            for row in result["source_keys"]
            if row["path"].startswith("generated://")
        }
        self.assertEqual(set(generated), freeze.GENERATED_SOURCE_KEYS)

    def test_source_preimage_is_exactly_70_and_selector_is_support_only(self):
        self.assertEqual(len(source_contract.SOURCE_KEYS), 70)
        self.assertEqual(
            source_contract.SOURCE_KEYS,
            freeze.p284.SOURCE_KEYS
            | frozenset(freeze.PAYLOAD_SOURCE_PATHS),
        )
        self.assertNotIn(
            "p286_source_contract_selector",
            source_contract.SOURCE_KEYS,
        )
        self.assertEqual(
            source_contract.OVERLAY_SOURCE_PATHS,
            dict(freeze.PAYLOAD_SOURCE_PATHS),
        )
        self.assertEqual(
            set(source_contract.source_bytes(ROOT)),
            source_contract.SOURCE_KEYS,
        )

    def test_selector_accepts_p286_and_retires_p282_and_p284(self):
        selected = selectors.select(
            source_contract.CONTRACT_ID,
            source_contract.PROFILE,
        )
        self.assertIs(selected.module, source_contract)
        self.assertEqual(selected.contract.contract_id, source_contract.CONTRACT_ID)
        self.assertEqual(
            candidate_intent.SUPERSEDED_FOR_NEW_CANDIDATES,
            {
                candidate_intent.p282.CONTRACT_ID: source_contract.CONTRACT_ID,
                candidate_intent.p284.CONTRACT_ID: source_contract.CONTRACT_ID,
            },
        )
        for retired in candidate_intent.SUPERSEDED_FOR_NEW_CANDIDATES:
            with self.assertRaisesRegex(
                candidate_intent.IntentError,
                "superseded for new candidates",
            ):
                candidate_intent.selected_source_contract_for_candidate(
                    retired,
                    source_contract.PROFILE,
                )

    def test_attachment_names_match_actual_symbols(self):
        attachments = {event.name: event.symbol for event in spec.TRACE_EVENTS}
        self.assertEqual(
            attachments["start_peripheral_in"],
            "dwc3_otg_start_peripheral",
        )
        self.assertEqual(
            attachments["start_peripheral_out"],
            "dwc3_otg_start_peripheral",
        )
        self.assertEqual(
            attachments["outer_sm_work_in"],
            "dwc3_otg_sm_work",
        )
        self.assertEqual(
            attachments["outer_sm_work_out"],
            "dwc3_otg_sm_work",
        )
        self.assertEqual(
            len(spec.events_for_phase(spec.PHASE_CYCLE)),
            16,
        )

    def test_outer_parser_distinguishes_returned_and_open_work(self):
        record = trace_contract.TraceRecord
        returned = (
            record(10, 1, "outer_sm_work_in", {}),
            record(10, 2, "outer_sm_work_out", {"rc": 0}),
            record(11, 3, "outer_sm_work_in", {}),
        )
        self.assertEqual(
            trace_contract._outer_state(returned),
            {"entered": True, "returned": True, "open": True},
        )
        with self.assertRaisesRegex(
            trace_contract.TraceContractError,
            "lacks its exact entry",
        ):
            trace_contract._outer_state(
                (record(10, 1, "outer_sm_work_out", {"rc": 0}),)
            )

    def test_runtime_has_parent_gate_and_no_blocking_specific_wait4(self):
        runtime = (
            ROOT
            / freeze.PAYLOAD_SOURCE_PATHS["p286_e3_runtime_include"]
        ).read_text(encoding="utf-8")
        parent_wait = runtime.index(
            "p282_wait_exact_value(\n"
            "        P286_PARENT_RUNTIME_STATUS_PATH,\n"
            "        P286_PARENT_SUSPENDED_READBACK,"
        )
        restart = runtime.index("static unsigned int p282_cycle_restart(")
        self.assertLess(parent_wait, restart)
        self.assertNotIn("sys_wait4(pid, &child_status, 0)", runtime)
        timeout_classified = runtime.index(
            "observation->timed_out = !malformed;"
        )
        kill = runtime.index("(void)sys_kill(pid, SIGKILL);", timeout_classified)
        bounded_reap = runtime.index(
            "sys_wait4(\n                            pid, &child_status, WNOHANG)",
            kill,
        )
        self.assertLess(timeout_classified, kill)
        self.assertLess(kill, bounded_reap)
        self.assertIn("observation->unreaped = 1;", runtime)
        self.assertIn("p286_classify_peripheral_readback(", runtime)
        abort = runtime[
            runtime.index(
                "static __attribute__((noreturn)) void p282_cycle_abort("
            ):
            runtime.index(
                "static __attribute__((noreturn)) void "
                "p282_cycle_abort_condition("
            )
        ]
        self.assertLess(
            abort.index("s22_r4w1e_checkpoint_failure("),
            abort.index("(void)p282_trace_finish("),
        )
        self.assertNotIn("P282_CONTROL_TRACE_CLEANUP_UNVERIFIED", abort)
        self.assertNotIn("fail_at(stage, 0U, detail);", abort)

    def test_runtime_classifier_and_packager_mutations_fail_closed(self):
        source = source_contract.source_bytes(ROOT)
        runtime = source["p286_e3_runtime_include"]
        with self.assertRaisesRegex(
            source_contract.SourceContractError,
            "bounded-specific-child-reap",
        ):
            source_contract._validate_runtime_authority_source(
                runtime.replace(
                    b"sys_wait4(\n                            "
                    b"pid, &child_status, WNOHANG)",
                    b"sys_wait4(\n                            "
                    b"pid, &child_status, WNOHANG | 0)",
                    1,
                )
            )
        abort_start = runtime.index(
            b"static __attribute__((noreturn)) void p282_cycle_abort("
        )
        abort_end = runtime.index(
            b"static __attribute__((noreturn)) void "
            b"p282_cycle_abort_condition(",
            abort_start,
        )
        abort = runtime[abort_start:abort_end]
        publish_start = abort.index(b"    long publish_rc")
        cleanup_start = abort.index(b"    if (cycle->armed)")
        terminal_park = abort.rindex(b"    quiet_park();")
        reordered_abort = (
            abort[:publish_start]
            + abort[cleanup_start:terminal_park]
            + abort[publish_start:cleanup_start]
            + abort[terminal_park:]
        )
        with self.assertRaisesRegex(
            source_contract.SourceContractError,
            "terminal checkpoint does not precede trace cleanup",
        ):
            source_contract._validate_runtime_authority_source(
                runtime[:abort_start]
                + reordered_abort
                + runtime[abort_end:]
            )
        classifier = source["p286_classifier_include"]
        with self.assertRaisesRegex(
            source_contract.SourceContractError,
            "classifier detail",
        ):
            source_contract._validate_classifier_source(
                classifier.replace(
                    b"P282_DETAIL_START_PERIPHERAL_NO_RETURN",
                    b"P282_DETAIL_PERIPHERAL_FLUSH_TIMEOUT",
                    1,
                )
            )
        mutated = dict(source)
        mutated["p286_candidate_builder"] = mutated[
            "p286_candidate_builder"
        ].replace(b"packager.package(", b"packager.disabled(", 1)
        with self.assertRaisesRegex(
            source_contract.SourceContractError,
            "builder dispatch",
        ):
            source_contract._validate_packager_integration(mutated)

    def test_terminal_checkpoint_survives_permanently_blocked_trace_finish(self):
        runtime = (
            ROOT
            / freeze.PAYLOAD_SOURCE_PATHS["p286_e3_runtime_include"]
        ).read_text(encoding="utf-8")
        abort_start = runtime.index(
            "static __attribute__((noreturn)) void p282_cycle_abort("
        )
        abort_end = runtime.index(
            "static __attribute__((noreturn)) void "
            "p282_cycle_abort_condition(",
            abort_start,
        )
        production_abort = runtime[abort_start:abort_end]
        harness = r'''
#include <stdint.h>
#include <unistd.h>

struct p282_trace_control {
    unsigned int marker;
};

struct p282_cycle_context {
    struct p282_trace_control trace;
    unsigned int armed;
};

static int g_checkpoint;

static __attribute__((noreturn)) void quiet_park(void)
{
    _exit(0);
}

static long s22_r4w1e_checkpoint_failure(
    void *client, uint8_t stage, uint8_t item_index, long detail)
{
    if (client != &g_checkpoint || stage != 0x90U ||
        item_index != 0U || detail != 0xc59L)
        _exit(90);
    if (write(STDOUT_FILENO, "P", 1) != 1)
        _exit(91);
    return 0;
}

static __attribute__((noreturn)) long p282_trace_finish(
    struct p282_trace_control *trace, long *quality)
{
    (void)trace;
    (void)quality;
    if (write(STDOUT_FILENO, "C", 1) != 1)
        _exit(92);
    for (;;)
        __asm__ volatile("" ::: "memory");
}

'''
        harness += production_abort
        harness += r'''
int main(void)
{
    struct p282_cycle_context cycle = {0};
    cycle.armed = 1U;
    p282_cycle_abort(&cycle, 0x90U, 0xc59L);
}
'''
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source = temporary / "abort-fault.c"
            binary = temporary / "abort-fault"
            source.write_text(harness, encoding="ascii")
            compiled = subprocess.run(
                (
                    "aarch64-linux-gnu-gcc",
                    "-static",
                    "-Os",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    str(source),
                    "-o",
                    str(binary),
                ),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            self.assertEqual(
                compiled.returncode,
                0,
                compiled.stdout.decode("utf-8", errors="replace"),
            )
            identity = subprocess.run(
                ("file", str(binary)),
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout
            self.assertIn("ARM aarch64", identity)
            process = subprocess.Popen(
                ("qemu-aarch64", str(binary)),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            try:
                with self.assertRaises(subprocess.TimeoutExpired) as blocked:
                    process.communicate(timeout=5)
                self.assertEqual(blocked.exception.output, b"PC")
                self.assertIsNone(process.poll())
            finally:
                process.kill()
                process.communicate()

    def test_classifier_fault_partition_cross_compiles_and_runs(self):
        header = source_contract.trace_descriptor_header(ROOT)
        native = ROOT / "workspace/public/src/native-init"
        harness = r'''
#include <stdint.h>
#include "s22plus_fyg8_p286_trace_descriptor.h"
#include "s22plus_fyg8_p286_classifier.inc.c"

static int detail_for(
    unsigned int stage, struct p286_helper_observation observation)
{
    struct p282_classification result = {0};
    int classified = p286_classify_helper(stage, &observation, &result);
    return classified == 1 ? (int)result.detail : classified;
}

int main(void)
{
    struct p282_classification result = {0};
    struct p286_helper_observation observation = {0};
    if (p286_classify_parent_status(0, 0, &result) != 1 ||
        result.detail != P282_DETAIL_PARENT_STATUS_NOT_SUSPENDED)
        return 1;
    if (p286_classify_parent_status(0, -5, &result) != 1 ||
        result.detail != P282_DETAIL_PARENT_STATUS_READ_ERROR)
        return 2;
    if (detail_for(P282_STAGE_STOP, observation) !=
        P282_DETAIL_HELPER_DISPATCH_FAILED)
        return 3;
    observation.dispatched = 1;
    observation.unreaped = 1;
    observation.timed_out = 1;
    if (detail_for(P282_STAGE_RESTART, observation) !=
        P282_DETAIL_HELPER_UNREAPED)
        return 4;
    observation.unreaped = 0;
    observation.malformed = 1;
    if (detail_for(P282_STAGE_RESTART, observation) !=
        P282_DETAIL_HELPER_COMPLETION_MALFORMED)
        return 5;
    observation.malformed = 0;
    if (detail_for(P282_STAGE_STOP, observation) !=
        P282_DETAIL_NONE_WRITE_TIMEOUT)
        return 6;
    if (detail_for(P282_STAGE_RESTART, observation) !=
        P282_DETAIL_PERIPHERAL_FLUSH_TIMEOUT)
        return 7;
    observation.outer_open = 1;
    if (detail_for(P282_STAGE_RESTART, observation) !=
        P282_DETAIL_RESIDUAL_OUTER_TAIL_TIMEOUT)
        return 8;
    observation.outer_open = 0;
    observation.start_entered = 1;
    if (detail_for(P282_STAGE_RESTART, observation) !=
        P282_DETAIL_START_PERIPHERAL_NO_RETURN)
        return 9;
    observation.timed_out = 0;
    observation.result = -5;
    if (detail_for(P282_STAGE_STOP, observation) !=
        P282_DETAIL_NONE_WRITE_RETURNED_ERROR)
        return 10;
    if (detail_for(P282_STAGE_RESTART, observation) !=
        P282_DETAIL_PERIPHERAL_WRITE_RETURNED_ERROR)
        return 11;
    observation.result = 0;
    observation.record_complete = 1;
    observation.write_completed = 1;
    if (detail_for(P282_STAGE_RESTART, observation) != 0)
        return 12;
    if (p286_classify_peripheral_readback(1, 0, &result) != 1 ||
        result.detail !=
            P282_DETAIL_PERIPHERAL_WRITE_COMPLETED_READBACK_FAILED)
        return 13;
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            (temporary / "s22plus_fyg8_p286_trace_descriptor.h").write_bytes(
                header
            )
            (temporary / "harness.c").write_text(harness, encoding="ascii")
            binary = temporary / "harness"
            subprocess.run(
                (
                    "aarch64-linux-gnu-gcc",
                    "-static",
                    "-Os",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-Wno-unused-function",
                    "-I",
                    str(temporary),
                    "-I",
                    str(native),
                    str(temporary / "harness.c"),
                    "-o",
                    str(binary),
                ),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            identity = subprocess.run(
                ("file", str(binary)),
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout
            self.assertIn("ARM aarch64", identity)
            subprocess.run(
                ("qemu-aarch64", str(binary)),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

    def test_source_implementation_cross_compile_and_patch_audit(self):
        result = source_contract.implementation_result(ROOT)
        self.assertEqual(
            result["verdict"],
            source_contract.IMPLEMENTATION_VERDICT,
        )
        self.assertTrue(result["linked_userspace"]["static_aarch64"])
        self.assertTrue(result["linked_userspace"]["two_link_reproducible"])
        self.assertTrue(result["patch"]["clean_apply"])
        self.assertFalse(result["safety"]["kernel_built"])

    def test_generated_checkpoint_and_kernel_accept_all_new_details(self):
        generated = source_contract.generate(ROOT)
        linked = source_contract.linked_table_bytes()
        for value in range(0xC50, 0xC5C):
            checkpoint = f"0x{value:03x}U".encode("ascii")
            kernel = f"0x{value:03x}".encode("ascii")
            self.assertEqual(generated["checkpoint"].count(checkpoint), 1)
            self.assertEqual(generated["patch"].count(kernel), 1)
        self.assertEqual(
            len(linked["s22_fyg8_p282_details"]),
            len(spec.DIAGNOSTIC_DETAILS) * 4,
        )

    def test_boot_only_packager_is_deterministic_and_exact_one_member(self):
        lz4 = ROOT / candidate_builder.DEFAULT_LZ4
        self.assertTrue(lz4.is_file())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            boot = root / "boot.img"
            boot.write_bytes(bytes(range(256)) * 32)
            receipts = []
            payloads = []
            for suffix in ("a", "b"):
                output = root / suffix
                audit = root / f"{suffix}-audit"
                output.mkdir()
                audit.mkdir()
                result = candidate_builder.packager.package(
                    boot_path=boot,
                    lz4_path=lz4,
                    output_dir=output,
                    audit_dir=audit,
                )
                self.assertEqual(
                    result["ap_structure"]["members"],
                    ["boot.img.lz4"],
                )
                self.assertTrue(result["verified"])
                receipts.append(result["ap_tar_md5"])
                payloads.append((output / "odin4/AP.tar.md5").read_bytes())
            self.assertEqual(receipts[0], receipts[1])
            self.assertEqual(payloads[0], payloads[1])

    def test_all_execution_registries_select_exact_p286_closure(self):
        contract_id = source_contract.CONTRACT_ID
        self.assertEqual(
            candidate_build.QUALIFICATION_MODULES[contract_id],
            (
                "s22plus_fyg8_p286_pre_lto_qualification",
                "p286_pre_lto_qualification",
                "P2.86",
            ),
        )
        self.assertEqual(
            repro.LINKED_VALIDATOR_ADAPTERS[contract_id],
            "s22plus_fyg8_p286_linked_audit",
        )
        self.assertEqual(
            repro.P286_QUALIFICATION_MODULE,
            qualification.__name__,
        )
        self.assertEqual(
            repro.P286_QUALIFICATION_PROVENANCE_KEY,
            "p286_pre_lto_qualification",
        )
        self.assertEqual(
            qualification.p286.CONTRACT_ID,
            contract_id,
        )
        self.assertEqual(
            static_checker.p286_closure.source_contract.CONTRACT_ID,
            contract_id,
        )
        safety = candidate_builder.artifact_safety(
            {"profile": "E2", "source_contract_id": contract_id}
        )
        self.assertEqual(
            safety["userspace_parent_runtime_status_gate"],
            spec.RUNTIME_AUTHORITY[
                "userspace_parent_runtime_status_gate"
            ],
        )
        self.assertEqual(
            candidate_builder.packager.SCHEMA,
            "s22plus_fyg8_p286_boot_only_package_v1",
        )

    def test_linked_adapter_accepts_58_detail_layout_and_restores_base(self):
        from tests.test_s22plus_fyg8_p282_linked_audit import (
            P282LinkedAuditTests,
        )

        fixture = P282LinkedAuditTests(
            methodName="test_validator_loads_all_p282_tables_and_tuple_dispatch"
        )
        fixture.setUp()
        historical = (
            p282_linked.ADAPTER_ID,
            p282_linked.EXPECTED_SOURCE_CONTRACT_ID,
            p282_linked.p282,
        )
        result = linked_audit.audit_linked_validator(
            fixture.disassembly,
            fixture.calls,
            fixture.addresses,
        )
        self.assertTrue(result["verified"])
        self.assertEqual(result["p282_exact_c_detail_count"], 58)
        self.assertEqual(
            linked_audit.EXPECTED_SOURCE_CONTRACT_ID,
            source_contract.CONTRACT_ID,
        )
        self.assertEqual(
            (
                p282_linked.ADAPTER_ID,
                p282_linked.EXPECTED_SOURCE_CONTRACT_ID,
                p282_linked.p282,
            ),
            historical,
        )

    def test_run_id_preimage_changes_for_one_payload_receipt_byte(self):
        nonce = bytes.fromhex("00112233445566778899aabbccddeeff")
        original = {
            "p286_classifier_include": {
                "size": 1,
                "sha256": "00" * 32,
            }
        }
        changed = {
            "p286_classifier_include": {
                "size": 1,
                "sha256": "01" + "00" * 31,
            }
        }
        first = candidate_intent.identity_preimage(
            nonce,
            original,
            source_contract.PROFILE,
            source_contract.CONTRACT_ID,
        )
        second = candidate_intent.identity_preimage(
            nonce,
            changed,
            source_contract.PROFILE,
            source_contract.CONTRACT_ID,
        )
        self.assertNotEqual(
            candidate_intent.derive_run_id(first),
            candidate_intent.derive_run_id(second),
        )


if __name__ == "__main__":
    unittest.main()

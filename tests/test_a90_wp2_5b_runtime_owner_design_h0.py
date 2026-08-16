"""Pin the A90 WP2-5b.2 runtime-owner H0 design boundary."""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
KERNEL = (
    ROOT
    / "workspace/private/inputs/kernel_source/"
    "SM-A908N_KOR_12_Opensource_13272/Kernel"
)
PRINTK = KERNEL / "kernel/printk/printk.c"
DESIGN = (
    ROOT
    / "docs/reports/"
    "A90_WLAN_WP2_5B_RUNTIME_OWNER_DURABLE_EVIDENCE_DESIGN_H0_2026-08-16.md"
)
REQUIREMENT = (
    ROOT
    / "docs/reports/"
    "A90_WLAN_WP2_5B_STREAMING_KMSG_OBSERVER_H0_2026-08-16.md"
)
CORE_REPORT = (
    ROOT
    / "docs/reports/"
    "A90_WLAN_WP2_5B_KMSG_TRACE_CORE_H0_2026-08-16.md"
)
BASE = (
    ROOT
    / "docs/security/hardening/"
    "a90-wlan-vendor-property-ablation-2026-08-15"
)
CONTRACT = BASE / "schema/a90-wp2-5b-kmsg-trace-v1.json"
HEADER = ROOT / "workspace/public/src/native-init/helpers/a90_wp2_5b_kmsg_contract.h"
CORE = ROOT / "workspace/public/src/native-init/helpers/a90_wp2_5b_kmsg_stream.c"
OWNER = ROOT / "workspace/public/src/native-init/helpers/a90_wp2_5b_kmsg_owner.c"
OWNER_REPORT = (
    ROOT
    / "docs/reports/"
    "A90_WLAN_WP2_5B_OBSERVER_RUNTIME_COMPONENT_H0_2026-08-16.md"
)
GOAL = ROOT / "GOAL_A90.md"


class A90Wp25bRuntimeOwnerDesignH0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.design = DESIGN.read_text(encoding="utf-8")
        cls.requirement = REQUIREMENT.read_text(encoding="utf-8")
        cls.core_report = CORE_REPORT.read_text(encoding="utf-8")
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_selected_source_consumes_record_before_einval_or_efault(self) -> None:
        if not PRINTK.is_file():
            self.skipTest(f"operator-staged A90 kernel source is absent: {PRINTK}")
        source = PRINTK.read_text(errors="replace")
        section = source[source.index("static ssize_t devkmsg_read(") :]
        positions = [
            section.index("user->idx = log_next(user->idx);"),
            section.index("user->seq++;"),
            section.index("if (len > count)"),
            section.index("if (copy_to_user(buf, user->buf, len))"),
        ]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("return -EINVAL", self.design)
        self.assertIn("return -EFAULT", self.design)
        self.assertIn("not retryable reads", self.design)
        self.assertIn("there may be no later record", self.design)

    def test_selected_source_gives_each_devkmsg_open_a_private_cursor(self) -> None:
        if not PRINTK.is_file():
            self.skipTest(f"operator-staged A90 kernel source is absent: {PRINTK}")
        source = PRINTK.read_text(errors="replace")
        opened = source[source.index("static int devkmsg_open(") :]
        self.assertIn("user = kmalloc(sizeof(struct devkmsg_user)", opened)
        self.assertIn("file->private_data = user;", opened)
        reader = source[source.index("static ssize_t devkmsg_read(") :]
        self.assertIn("struct devkmsg_user *user = file->private_data;", reader)
        self.assertIn("one private\n  `devkmsg_user` cursor per opened reader file", self.design)

    def test_fault_vocabulary_appends_efault_without_renumbering(self) -> None:
        reasons = {
            row["name"]: row["id"]
            for row in self.contract["wireFormat"]["faultReasons"]
        }
        self.assertEqual(reasons["READ_ERROR"], 1)
        self.assertEqual(reasons["EINVAL_CURSOR_ADVANCED"], 4)
        self.assertEqual(reasons["BOUNDARY_ERROR"], 9)
        self.assertEqual(reasons["EFAULT_CURSOR_ADVANCED"], 10)
        self.assertIn("#define A90_WP2_5B_FAULT_EFAULT 10u", HEADER.read_text())
        self.assertIn(
            "reason > A90_WP2_5B_FAULT_EFAULT", CORE.read_text()
        )

    def test_contract_requires_terminal_no_retry_consumed_faults(self) -> None:
        faults = self.contract["kmsgRecordContract"]["consumedReadFaults"]
        self.assertIn("advances user->idx", faults["sourceOrdering"])
        for name in ("EINVAL", "EFAULT"):
            self.assertIn("already consumed", faults[name])
            self.assertIn("never retry or read again", faults[name])
        self.assertEqual(
            faults["postIntentResult"],
            "NO_PROOF_OBSERVER_AND_NO_EFFECT_REPLAY",
        )

    def test_owner_and_parent_responsibilities_do_not_alias(self) -> None:
        for claim in (
            "the observer owns the campaign's sole `/dev/kmsg` reader FD and raw trace",
            "but has no effect-dispatch authority",
            "The parent never reads `/dev/kmsg`",
            "The observer alone may",
            "`SCM_RIGHTS`, or pathname reopen substitutes",
            "No AF_UNIX socket, inherited directory FD",
            "closes the run-directory FD",
            "one `/dev/kmsg` FD",
            "a pre-existing independent OS reader has a\nseparate source-proved `devkmsg_user` cursor",
            "one writer and one reader",
            "an unsigned 64-bit sequence starting at zero and advancing by exactly\none",
            "A forward gap, duplicate,\nregression",
            "required next frame after `UINT64_MAX` is terminal",
            "total frame\nsize no larger than the qualified `PIPE_BUF`",
            "Each frame is\nissued by one direct `write()`",
            "ephemeral pipe state is never itself\na receipt",
            "The observer has no journal-directory or event-file FD",
        ):
            self.assertIn(claim, self.design)
        self.assertIn("the observer never publishes a final name", self.requirement)
        self.assertIn(
            "Only after exact wait/reap and zero-reader proof does the\nparent publish it",
            self.design,
        )

    def test_state_order_is_intent_before_effect_and_close_after_outcome(self) -> None:
        ordering = self.design[
            self.design.index("1. `QUALIFIED`") :
            self.design.index("## Read and poll decision table")
        ]
        states = (
            "`QUALIFIED`",
            "`RUN_DIR_CLAIMED`",
            "`OBSERVER_EXEC_READY`",
            "`TRACE_PENDING_CREATED`",
            "`KMSG_OPENED`",
            "`OBSERVER_CONFINED`",
            "`KMSG_AT_END`",
            "`ARM_PREFIX_DURABLE`",
            "`OBSERVER_ARMED`",
            "`EFFECT_INTENT`",
            "`EFFECT_DISPATCHED`",
            "`DRIVER_OUTCOME_BOUND`",
            "`CLOSE_REQUESTED`",
            "`CAPTURE_CLOSED`",
            "`TERMINAL_INPUT_BOUND`",
            "`TERMINAL`",
            "`FINAL_RESULT`",
        )
        positions = [ordering.index(state) for state in states]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("effectReplayAllowed=false", ordering)
        self.assertIn("sole success-path order", self.design)
        self.assertIn(
            "Any failure after `RUN_DIR_CLAIMED` branches immediately",
            self.design,
        )

    def test_observer_effect_authority_is_structurally_removed(self) -> None:
        for claim in (
            "one exact static clean exec",
            "FD-based `execveat(..., AT_EMPTY_PATH)`/equivalent exact-file primitive",
            "executable FD closes on successful exec",
            "Path-only `execve`, `/proc/self/fd` re-resolution",
            "an empty environment",
            "drop every effective,\npermitted, inheritable, ambient, and bounding capability",
            "PR_SET_NO_NEW_PRIVS",
            "all-ABI fail-closed syscall filter",
            "rejects every path open, socket",
            "ioctl, exec, namespace",
            "Unknown architectures and syscall numbers are fatal",
            "A missing kernel control is `NO_GO`",
        ):
            self.assertIn(claim, self.design)

    def test_direct_child_wait_and_pid_reuse_are_closed(self) -> None:
        for claim in (
            "blocks SIGCHLD",
            "neither `SIG_IGN`\nnor `SA_NOCLDWAIT`",
            "one exact waiter reservation",
            "every resident\n`waitpid(-1)`/reaper path must honor",
            "No handler, thread, helper, or second\nwaiter may reap it",
            "zombie/non-reuse invariant",
            "cannot prove this exclusion, the runtime design is infeasible (`NO_GO`)",
            "PID\nor start-time comparison after an unintended reap is not a repair",
        ):
            self.assertIn(claim, self.design)

    def test_scheduler_and_resource_state_is_normalized_before_child_runs(self) -> None:
        for claim in (
            "pre-exec barrier",
            "scheduling policy/priority",
            "affinity/cpuset",
            "I/O priority",
            "uclamp state",
            "dedicated aggregate cgroup",
            "non-RT/non-deadline policy",
            "native parent/recovery reserve",
            "`RLIMIT_RTPRIO=0`",
            "no `CAP_SYS_NICE`/`CAP_SYS_RESOURCE` survive",
            "cannot enter exec\nuntil those facts",
            "inherited FIFO/RR/DEADLINE/high-priority state are `NO_GO`",
        ):
            self.assertIn(claim, self.design)

    def test_durable_publication_has_exact_link_count_crash_states(self) -> None:
        for claim in (
            "O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC",
            "sole long-lived observer-owned mutable trace file",
            "pending leaves may exist only inside their fixed bounded",
            "atomic no-replace hard-link",
            "link count one",
            "link count exactly two",
            "directory fsync",
            "Direct final-name writes",
            "duplicate keys",
            "semantic-only equivalence",
            "read from raw canonical\nbytes",
            "fixed native, non-shared-storage location",
            "mode 0700",
            "directory link count is never evidence",
            "Unsupported or changed durability semantics are\n`NO_GO`",
            "one exact storage-reservation\nbackend",
            "A `statfs()` snapshot alone is not a reservation",
            "a separate\nnative recovery reserve",
            "`ENOSPC`/`EDQUOT` before\nintent declines with zero effect",
            "after intent it parks recovery and never\npermits replay",
            "never emitted\nto stdout, a terminal, or a tracked repository path",
            "writes only\nunder `workspace/private/`",
        ):
            self.assertIn(claim, self.design)

    def test_every_post_intent_crash_prefix_forbids_replay(self) -> None:
        table = self.design[
            self.design.index("## Crash-prefix reconciliation") :
            self.design.index("## Required negative corpus")
        ]
        self.assertIn(
            "`EFFECT_INTENT` without a validated dispatch receipt/event",
            table,
        )
        self.assertIn("never dispatch or replay", table)
        self.assertIn("`EFFECT_DISPATCHED` without driver outcome", table)
        self.assertIn("no resend", table)
        self.assertIn("driver outcome without closed trace", table)
        self.assertIn("never reopen a proof epoch", table)
        self.assertIn("final wrapper present, stdout/host return lost", table)
        self.assertNotRegex(table, re.compile(r"retry (?:the )?effect", re.I))

    def test_pre_effect_failure_has_durable_zero_ordinal_terminal(self) -> None:
        for claim in (
            "effectState=NOT_INTENDED",
            "pre-effect `TERMINAL_INPUT`",
            "`DECLINED_PRE_EFFECT` with ordinal zero",
            "outside the attempt-journal sequence",
            "No missing `OBSERVER_ARMED`/intent/dispatch/outcome event is synthesized",
            "no\ndriver/property receipt is invented",
            "terminal input precedes cleanup",
            "driver/property fields remain `NOT_RUN`",
        ):
            self.assertIn(claim, self.design)

    def test_terminal_input_and_existing_terminal_payload_do_not_alias(self) -> None:
        binding = self.contract["journalContract"]["payloadBindings"]["TERMINAL"]
        self.assertEqual(binding, "canonical WP2-4 property result SHA-256")
        for claim in (
            "`TERMINAL_INPUT_BOUND`",
            "`SHA256(canonical WP2-4 property result)`",
            "It never names the tagged union",
            "`FINAL_RESULT`",
            "terminal-input SHA-256",
            "full raw journal-chain SHA-256",
            "The host accepts none of the bound objects",
            "dispatch-receipt, terminal-input, and property-result digests or result states\nare not interchangeable",
        ):
            self.assertIn(claim, self.design)

    def test_dispatch_receipt_does_not_replace_existing_command_binding(self) -> None:
        binding = self.contract["journalContract"]["payloadBindings"][
            "EFFECT_DISPATCHED"
        ]
        self.assertEqual(binding, "qualified exact-command SHA-256")
        for claim in (
            "`dispatch-receipt-v1`",
            "`SHA256(qualified exact command)`",
            "The event never names the dispatch\n    receipt",
            "`MISSING_AFTER_INTENT`",
            "dispatch-receipt state and SHA-256 when present",
            "command/event versus dispatch-receipt digest substitution in both directions",
        ):
            self.assertIn(claim, self.design)

    def test_missing_property_result_cannot_fabricate_terminal_or_wrapper(self) -> None:
        for claim in (
            "`PROPERTY_RESULT_PRESENT_EXACT`",
            "`PROPERTY_RESULT_MISSING_OR_INVALID`",
            "accepts only `PROPERTY_RESULT_PRESENT_EXACT`",
            "accepts only\n`PROPERTY_RESULT_MISSING_OR_INVALID`",
            "`RECOVERY_PARKED_PROPERTY_RESULT_UNAVAILABLE`",
            "is neither `TERMINAL`\n    nor `FINAL_RESULT`",
            "never publish `TERMINAL` or `FINAL_RESULT`",
            "proof unavailable",
            "relabeled as experiment proof",
        ):
            self.assertIn(claim, self.design)

    def test_failure_close_does_not_require_or_fabricate_driver_outcome(self) -> None:
        for claim in (
            "one finite close-policy object",
            "`NORMAL_AFTER_DRIVER_OUTCOME`",
            "`FAULT_AFTER_TERMINAL_INPUT`",
            "`PARENT_CONTROL_EOF`",
            "performs zero later kmsg reads",
            "fsyncs that prefix when the trace writer remains\nusable",
            "`FAULTED` status binding the pending inode and durable prefix length",
            "first publishes the branch\nterminal input, then sends the same fixed close token",
            "never fabricates a durable\nfault frame",
            "never forces an observation loop or a fake\n`DRIVER_OUTCOME_BOUND`",
        ):
            self.assertIn(claim, self.design)

    def test_receipt_producers_are_separate_and_unimplemented(self) -> None:
        for claim in (
            "`driver-identity-receipt-v1`",
            "`interface-outcome-receipt-v1`",
            "`a90-wp2-5b-driver-outcome-receipt-v1`",
            "remain\nunimplemented",
            "Every receipt uses one compile-time fixed leaf",
            "The dispatch receipt must be durable before `EFFECT_DISPATCHED`",
            "neither the\nknown command digest nor an in-memory return may synthesize it",
            "No path, interface name, module string, boot\nvalue, or digest is caller supplied",
        ):
            self.assertIn(claim, self.design)

    def test_docs_bind_same_design_and_keep_gate_open(self) -> None:
        linked = (
            self.requirement,
            self.core_report,
            (BASE / "context.md").read_text(),
            (BASE / "hardening.md").read_text(),
            (BASE / "proposals/wlan-vendor-property-ablation.md").read_text(),
            GOAL.read_text(),
        )
        for text in linked:
            self.assertIn("WP2-5b.2", text)
            self.assertIn("EINVAL", text)
            self.assertIn("EFAULT", text)
        self.assertEqual(
            self.contract["scope"]["openGate"],
            "WP2_5B_STREAMING_KMSG_OBSERVER_ABSENT",
        )
        self.assertFalse(self.contract["authority"]["liveExecutionAuthorized"])

    def test_design_freeze_remains_h0_after_separate_component_implementation(self) -> None:
        self.assertTrue(OWNER.is_file())
        for claim in (
            "runtime implementation remains absent",
            "does not implement the owner, writer, receipt producers",
            "numeric budgets are not selected",
            "This is H0 design work only",
            "D0, D1, F1",
            "device authority",
        ):
            self.assertIn(claim, self.design)
        owner_report = OWNER_REPORT.read_text()
        self.assertIn("WP2-5b.3a", owner_report)
        self.assertIn("no live authority", owner_report)
        self.assertIn("durable final-name publication writer", owner_report)
        self.assertIn("WP2_5B_STREAMING_KMSG_OBSERVER_ABSENT", owner_report)


if __name__ == "__main__":
    unittest.main()

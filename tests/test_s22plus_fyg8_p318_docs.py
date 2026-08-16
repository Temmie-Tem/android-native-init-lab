from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P317_CDC_ACM_ENDPOINT_SELECTOR_CORRECTION_H0_2026-08-14.md"
)
INCIDENT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P317_HISTORICAL_ENDPOINT_REPLAY_RECOVERY_INCIDENT_2026-08-14.md"
)
POSTROLLBACK = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P318_POSTROLLBACK_FINALIZATION_INCIDENT_H0_2026-08-17.md"
)
POSTROLLBACK_SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_postrollback_finalize.py"
)
POSTROLLBACK_AUTHORITY = ROOT / (
    "workspace/public/src/device-action/recovery/"
    "s22plus_fyg8_p318_postrollback_finalize_v1.json"
)
POSTROLLBACK_CLOSE_AUDIT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_postrollback_close_audit.py"
)
POSTROLLBACK_CLOSE_AUDIT_RECEIPT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p318/"
    "postrollback-close-audit-20260817-01.json"
)
GOAL = ROOT / "GOAL.md"
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
TARGET_CONTRACT = ROOT / "docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md"
PRIVATE = ROOT / "workspace/private/outputs/s22plus_fyg8_p318_endpoint_selector"
QEMU_E2E = ROOT / "workspace/private/outputs/s22plus_fyg8_p318_cdc_acm_qemu_e2e"
PREPARED = ROOT / (
    "workspace/private/runs/device-action-f1-live-v2/"
    "f1-2026-08-12T165954582328Z-1786553994582372233/prepared.json"
)


class P318DocumentationTest(unittest.TestCase):
    def test_postrollback_finalizer_closed_healthy_and_audit_is_transfer_free(self):
        report = POSTROLLBACK.read_text(encoding="utf-8")
        normalized = " ".join(report.split())
        authority = json.loads(POSTROLLBACK_AUTHORITY.read_text())
        self.assertIn(
            "LIVE_CLOSED_HEALTHY; CLOSE_AUDIT_PASS_GO_H0; "
            "NO LIVE AUTHORITY",
            report,
        )
        self.assertIn("no Download request", normalized)
        self.assertIn("no Odin invocation", normalized)
        self.assertIn("no candidate or rollback transfer", normalized)
        self.assertIn("NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK", report)
        self.assertIn("candidate_not_proven_rollback_verified", report)
        self.assertIn("received an independent safety review", normalized)
        self.assertIn("qualifies only this H0 capability", normalized)
        self.assertIn("journal advanced from 15 records", normalized)
        self.assertIn("exact transfers remain 1/1", GOAL.read_text(encoding="utf-8"))
        self.assertIn("It has no ADB command, USB, Odin, subprocess", normalized)
        self.assertEqual(
            authority["binding"]["constraints"],
            {
                "candidate_transfer_allowed": False,
                "rollback_transfer_allowed": False,
                "download_request_allowed": False,
                "odin_invocation_allowed": False,
                "device_writes": False,
                "fresh_health_reads_only": True,
                "existing_observer_bytes_only": True,
            },
        )

    def test_postrollback_ledger_preserves_attempt_review_close_and_audit_pending(self):
        ledger = LEDGER.read_text(encoding="utf-8")
        attempt = "s22plus-fyg8-p318 | 1 | F1 | P318_POSTROLLBACK_CORRELATION_STOP"
        pending = (
            "s22plus-fyg8-p318 | h0-postrollback-finalizer-12 | H0 | "
            "P318_POSTROLLBACK_FINALIZER_IMPLEMENTED_REVIEW_PENDING"
        )
        review = (
            "s22plus-fyg8-p318 | h0-postrollback-finalizer-review-12 | H0 | "
            "PASS_GO_P318_POSTROLLBACK_FINALIZER_H0_CAPABILITY_V1"
        )
        close = (
            "s22plus-fyg8-p318 | 1-recovery-close | F1 | "
            "CAMPAIGN_CLOSED | HEALTHY | NO_PROOF_OBSERVER | 1/1"
        )
        close_audit = (
            "s22plus-fyg8-p318 | h0-postrollback-close-audit-13 | H0 | "
            "P318_POSTROLLBACK_CLOSE_AUDIT_IMPLEMENTED_REVIEW_PENDING"
        )
        close_audit_review = (
            "s22plus-fyg8-p318 | h0-postrollback-close-audit-review-13 | H0 | "
            "PASS_GO_P318_POSTROLLBACK_CLOSE_AUDIT_H0_CAPABILITY_V1"
        )
        self.assertEqual(ledger.count(attempt), 1)
        self.assertEqual(ledger.count(pending), 1)
        self.assertEqual(ledger.count(review), 1)
        self.assertEqual(ledger.count(close), 1)
        self.assertEqual(ledger.count(close_audit), 1)
        self.assertEqual(ledger.count(close_audit_review), 1)
        self.assertLess(ledger.index(attempt), ledger.index(pending))
        self.assertLess(ledger.index(pending), ledger.index(review))
        self.assertLess(ledger.index(review), ledger.index(close))
        self.assertLess(ledger.index(close), ledger.index(close_audit))
        self.assertLess(ledger.index(close_audit), ledger.index(close_audit_review))

    def test_postrollback_close_audit_private_receipt_is_exact_and_host_only(self):
        spec = importlib.util.spec_from_file_location(
            "p318_postrollback_close_audit_docs", POSTROLLBACK_CLOSE_AUDIT
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        receipt_bytes = POSTROLLBACK_CLOSE_AUDIT_RECEIPT.read_bytes()
        self.assertEqual(receipt_bytes, module.encode_receipt(module.build_receipt()))
        self.assertEqual(len(receipt_bytes), 2856)
        self.assertEqual(
            hashlib.sha256(receipt_bytes).hexdigest(),
            "890c97300832c5ff63e9aa0a9e61f48098a7a251607fe6ebc89cd3aa26fc7f65",
        )
        receipt = json.loads(receipt_bytes)
        self.assertEqual(receipt["terminal"]["journal_state"], "CLOSED")
        self.assertEqual(receipt["terminal"]["journal_record_count"], 19)
        self.assertEqual(receipt["terminal"]["candidate_transfers"], 1)
        self.assertEqual(receipt["terminal"]["rollback_transfers"], 1)
        self.assertFalse(receipt["scope"]["device_actions"])
        self.assertFalse(receipt["scope"]["device_contact"])
        self.assertFalse(receipt["scope"]["live_authority_created"])

    def test_report_binds_current_private_receipts(self):
        report = REPORT.read_text(encoding="utf-8")
        expected = {
            "endpoint-transition-20260814-01.json": (
                "PASS_P318_P317_PHYSICAL_TOPOLOGY_DRIFT_LOCALIZATION_H0"
            ),
            "cdc-acm-positive-control-20260814-01.json": (
                "PASS_P318_CDC_ACM_TWO_SEAM_POSITIVE_CONTROL_H0"
            ),
            "cdc-acm-selector-negative-control-20260815-01.json": (
                "PASS_P318_SELECTOR_NEGATIVE_CONTROL_H0"
            ),
            "banner-result-contract-20260814-01.json": (
                "CHANGES_REQUIRED_P318_HOST_EVENT_PRODUCER_NOT_IMPLEMENTED_H0"
            ),
            "p317-poll-budget-measurement-20260814-01.json": (
                "PASS_P318_P317_POLL_BUDGET_MEASURED_H0"
            ),
        }
        for name, verdict in expected.items():
            payload = (PRIVATE / name).read_bytes()
            value = json.loads(payload)
            self.assertEqual(value["verdict"], verdict)
            self.assertIn(name, report)
            self.assertIn(f"size    {len(payload)}", report)
            self.assertIn(f"sha256  {hashlib.sha256(payload).hexdigest()}", report)

        qemu_result = (QEMU_E2E / "result.json").read_bytes()
        self.assertEqual(
            json.loads(qemu_result)["verdict"],
            "PASS_P318_CDC_ACM_QEMU_REAL_OBSERVER_H0",
        )
        for name in (
            "result.json",
            "qemu-console.log",
            "qemu-proc-maps.log",
            "bwrap-proc-maps.log",
            "qemu-mountinfo.log",
            "p318-cdc-acm-qemu-e2e.cpio",
            "rootfs/init",
            "input-snapshots/guest-package/Packages.xz",
            (
                "input-snapshots/guest-package/debs/"
                "linux-image-6.12.94+deb13-arm64_6.12.94-1_arm64.deb"
            ),
        ):
            payload = (QEMU_E2E / name).read_bytes()
            self.assertIn(name, report)
            self.assertIn(f"size    {len(payload)}", report)
            self.assertIn(f"sha256  {hashlib.sha256(payload).hexdigest()}", report)

    def test_scope_and_offline_ready_do_not_grant_live_authority(self):
        combined = " ".join(
            (
                REPORT.read_text(encoding="utf-8")
                + GOAL.read_text(encoding="utf-8")
            ).split()
        )
        required = (
            "For P3.17 only",
            "does not reclassify earlier campaigns",
            "PASS_GO — S22PLUS_FYG8_P318_CUSTOM71_PROCESS_V2_OFFLINE_READY_CAPABILITY_V3; H0 OFFLINE CAPABILITY ONLY; NO LIVE AUTHORITY",
            "PASS_GO — S22PLUS_FYG8_P318_CUSTOM71_PROCESS_V2_OFFLINE_READY_CAPABILITY_V1",
            "PASS_GO — S22PLUS_FYG8_P318_CUSTOM71_PROCESS_V2_OFFLINE_READY_CAPABILITY_V2",
            "PASS_GO — S22PLUS_FYG8_P318_CUSTOM71_PROCESS_V2_OFFLINE_READY_CAPABILITY_V3",
            "PASS_GO — S22PLUS_FYG8_P318_SELECTOR_NEGATIVE_CONTROL_H0_CAPABILITY_V1",
            "PASS_GO — S22PLUS_FYG8_P318_CDC_ACM_QEMU_REAL_OBSERVER_H0_CAPABILITY_V1",
            "grants no D0, D1, F1, recovery, replay, or live authority",
            "Fresh connected prerequisites",
            "42 `SOURCE_KEYS`",
            "70 early and 71 effective",
            "79cf54d59171",
            "129ad86b934c",
            "without a shadow ready flag",
            "Python snapshots require an explicit pre-gate count",
            "source-and-canonical-path frozen",
            "dwc3-event-latch-build-followup-v3",
            "V3 does not claim path-independent rebuildability",
            "not a divergence upper bound",
            "both 11 characters",
            "observability was gained at the expense of source-only reproducibility",
            "V2 module is not retained for a byte audit",
            "reads `exposure_state` before `event_ready`",
            "qualified runtime cannot take that interleaving",
            "NO_PROOF_EXPERIMENT_PRECONDITION",
            "first actual host-caused device event",
            "lossless PackBits poll capacity falls from 76 to 47 bytes",
            "PASS_GO — S22PLUS_FYG8_P318_TOPOLOGY_TIMING_DESIGN_H0_CAPABILITY_V1",
            "is withdrawn",
            "PASS_GO — S22PLUS_FYG8_P318_TOPOLOGY_TIMING_DESIGN_H0_CAPABILITY_V2",
            "PASS_GO — S22PLUS_FYG8_P318_TOPOLOGY_TIMING_DESIGN_H0_CAPABILITY_V3",
            "DEVICE_RESULT_DWC3_HOST_EVENT_NO_ENDPOINT",
            "55,296 inputs and ten timing decisions",
            "valid terminal domain contains 344 rows",
            "`EINTR` branch loops before any clock check",
            "fixed `trace.h` callback ABI",
            "0x01ff0101",
            "0xabcd3040",
            "8 raw bytes",
            "9 bytes for each record",
            "Full dummy_hcd-to-observer successor control",
            "queues the source-derived 49-byte banner before the observer child is forked",
            "one complete LF-terminated terminal line",
            "cryptographically verified Debian trixie `InRelease`",
            "The same signed `Packages` authority now also binds the guest kernel",
            "built from those extracted package bytes rather than trusting the loose tree",
            "separately snapshotted Bubblewrap launcher",
            "Bubblewrap's info descriptor identifies the inner QEMU PID",
            "host_kernel_runtime_interfaces_byte_frozen: false",
            "root udev/ModemManager guard remains an explicitly synthetic healthy fixture",
            "do not qualify or waive Envelope-v4's unrelated 47/48-byte PackBits boundary",
        )
        for clause in required:
            self.assertIn(clause, combined)

    def test_ledger_correction_is_append_only_after_original_close(self):
        ledger = LEDGER.read_text(encoding="utf-8")
        original = (
            "2026-08-13T17:42:07Z | s22plus-fyg8-p317 | 1-recovery-close | "
            "F1 | CAMPAIGN_CLOSED | HEALTHY | NO_PROOF_OBSERVER | 1/1 |"
        )
        superseded_correction = (
            "s22plus-fyg8-p317 | h0-endpoint-selector-correction-1 | H0 | "
            "P317_CDC_ACM_ENDPOINT_SELECTOR_POSTCLOSE_CORRECTION_AND_P318_H0_DESIGN"
        )
        correction = (
            "s22plus-fyg8-p317 | h0-endpoint-topology-correction-2 | H0 | "
            "P317_PHYSICAL_TOPOLOGY_PRECONDITION_POSTCLOSE_CORRECTION | "
            "HEALTHY | NO_PROOF_EXPERIMENT_PRECONDITION | 0/0 |"
        )
        design = (
            "s22plus-fyg8-p318 | h0-topology-timing-review-3 | H0 | "
            "PASS_GO_P318_TOPOLOGY_TIMING_DESIGN_H0_CAPABILITY_V3"
        )
        implementation = (
            "s22plus-fyg8-p318 | h0-implementation-ready-1 | H0 | "
            "PASS_GO_P318_CUSTOM71_PROCESS_V2_OFFLINE_READY_CAPABILITY_V1"
        )
        followup = (
            "s22plus-fyg8-p318 | h0-pregate-evidence-followup-1 | H0 | "
            "P318_PRE_GATE_EVENT_EVIDENCE_IMPLEMENTED_REVIEW_PENDING"
        )
        final_review = (
            "s22plus-fyg8-p318 | h0-pregate-evidence-review-2 | H0 | "
            "PASS_GO_P318_CUSTOM71_PROCESS_V2_OFFLINE_READY_CAPABILITY_V2"
        )
        followup_3 = (
            "s22plus-fyg8-p318 | h0-gate-state-single-authority-followup-3 | H0 | "
            "P318_GATE_STATE_SINGLE_AUTHORITY_FOLLOWUP_REVIEW_PENDING"
        )
        final_review_3 = (
            "s22plus-fyg8-p318 | h0-gate-state-single-authority-review-3 | H0 | "
            "PASS_GO_P318_CUSTOM71_PROCESS_V2_OFFLINE_READY_CAPABILITY_V3"
        )
        path_provenance_4 = (
            "s22plus-fyg8-p318 | h0-build-path-provenance-4 | H0 | "
            "P318_LATCH_SOURCE_AND_PATH_FREEZE_PROVENANCE_RECORDED"
        )
        selector_negative_5 = (
            "s22plus-fyg8-p318 | h0-selector-negative-control-5 | H0 | "
            "P318_REAL_SELECTOR_NEGATIVE_CONTROL_IMPLEMENTED_REVIEW_PENDING"
        )
        selector_negative_review_5 = (
            "s22plus-fyg8-p318 | h0-selector-negative-control-review-5 | H0 | "
            "PASS_GO_P318_SELECTOR_NEGATIVE_CONTROL_H0_CAPABILITY_V1"
        )
        qemu_e2e_6 = (
            "s22plus-fyg8-p318 | h0-cdc-acm-qemu-e2e-6 | H0 | "
            "P318_CDC_ACM_QEMU_REAL_OBSERVER_IMPLEMENTED_REVIEW_PENDING"
        )
        qemu_e2e_review_6 = (
            "s22plus-fyg8-p318 | h0-cdc-acm-qemu-e2e-review-6 | H0 | "
            "PASS_GO_P318_CDC_ACM_QEMU_REAL_OBSERVER_H0_CAPABILITY_V1"
        )
        self.assertEqual(ledger.count(original), 1)
        self.assertEqual(ledger.count(superseded_correction), 1)
        self.assertEqual(ledger.count(correction), 1)
        self.assertEqual(ledger.count(design), 1)
        self.assertEqual(ledger.count(implementation), 1)
        self.assertEqual(ledger.count(followup), 1)
        self.assertEqual(ledger.count(final_review), 1)
        self.assertEqual(ledger.count(followup_3), 1)
        self.assertEqual(ledger.count(final_review_3), 1)
        self.assertEqual(ledger.count(path_provenance_4), 1)
        self.assertEqual(ledger.count(selector_negative_5), 1)
        self.assertEqual(ledger.count(selector_negative_review_5), 1)
        self.assertEqual(ledger.count(qemu_e2e_6), 1)
        self.assertEqual(ledger.count(qemu_e2e_review_6), 1)
        self.assertLess(ledger.index(original), ledger.index(superseded_correction))
        self.assertLess(ledger.index(superseded_correction), ledger.index(correction))
        self.assertLess(ledger.index(correction), ledger.index(design))
        self.assertLess(ledger.index(design), ledger.index(implementation))
        self.assertLess(ledger.index(implementation), ledger.index(followup))
        self.assertLess(ledger.index(followup), ledger.index(final_review))
        self.assertLess(ledger.index(final_review), ledger.index(followup_3))
        self.assertLess(ledger.index(followup_3), ledger.index(final_review_3))
        self.assertLess(ledger.index(final_review_3), ledger.index(path_provenance_4))
        self.assertLess(ledger.index(path_provenance_4), ledger.index(selector_negative_5))
        self.assertLess(
            ledger.index(selector_negative_5),
            ledger.index(selector_negative_review_5),
        )
        self.assertLess(ledger.index(selector_negative_review_5), ledger.index(qemu_e2e_6))
        self.assertLess(ledger.index(qemu_e2e_6), ledger.index(qemu_e2e_review_6))

    def test_incident_report_carries_explicit_post_close_correction(self):
        incident = INCIDENT.read_text(encoding="utf-8")
        normalized = " ".join(incident.split())
        self.assertIn("## Post-close endpoint/topology correction", incident)
        self.assertIn("selected no endpoint and never opened the TTY", normalized)
        self.assertIn("campaign-level multiplicity result", incident)
        self.assertIn("cable/dock connection was physically moved", incident)

    def test_tracked_unit_does_not_export_raw_candidate_serial(self):
        prepared = json.loads(PREPARED.read_text(encoding="utf-8"))
        serial = prepared["approval_binding"]["base_binding"]["observation"][
            "candidate_observer"
        ]["usb_serial"]
        tracked = [
            REPORT,
            INCIDENT,
            POSTROLLBACK,
            GOAL,
            LEDGER,
            POSTROLLBACK_SCRIPT,
            POSTROLLBACK_AUTHORITY,
            ROOT
            / "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p318_cdc_acm_endpoint_transition.py",
            ROOT
            / "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p318_cdc_acm_positive_control.py",
            ROOT
            / "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p318_selector_negative_control.py",
            ROOT / "tests/test_s22plus_fyg8_p318_selector_negative_control.py",
            ROOT
            / "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p318_banner_result_contract.py",
            ROOT
            / "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p318_poll_budget_measurement.py",
            ROOT
            / "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p318_cdc_acm_qemu_e2e.py",
            ROOT
            / "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p318_cdc_acm_qemu_guest.py",
            ROOT
            / "workspace/public/src/native-init/"
            "s22plus_fyg8_p318_cdc_acm_qemu_init.c",
            ROOT / "tests/test_s22plus_fyg8_p318_cdc_acm_qemu_e2e.py",
        ]
        for path in tracked:
            self.assertNotIn(serial, path.read_text(encoding="utf-8"), path)

    def test_target_contract_closes_physical_drift_and_rollback_rebinding(self):
        contract = " ".join(TARGET_CONTRACT.read_text(encoding="utf-8").split())
        required = (
            "through rollback transfer and verified final-health close",
            "The observer must never widen its selector or open an unapproved endpoint",
            "permanent `S22PLUS_F1_PHYSICAL_TOPOLOGY_CONTINUITY` boundary",
            "and has no expiry",
            "requires a new independent boundary review",
            "Process-v2 evidence must retain the exact endpoint identity, topology, host "
            "controller/device path, and immutable raw-snapshot receipt",
            "A missing, truncated, or unreadable snapshot is an observer failure",
            "Classification is phase-specific",
            "pre-session stop and has no consumed-run proof class",
            "host-silent device-result classification",
            "never changes an already retained experiment result",
            "A drifted topology does not authorize rollback against the new path",
            "A normal unchanged path is `rollback_bound_exact`",
            "a bounded, independently reviewed recovery-only path establishes "
            "`recovery_rebound_exact`",
            "`rollback_bound_exact` and `recovery_rebound_exact` are distinct authority states",
            "bit 7 proves that no qualifying host event linearized before that gate transition",
            "`latch_install <= gate_write` order remains a structural consistency check",
            "the retained gate-write timestamp is no later than the diagnostic pre sample",
            "Legacy masks `0x6f` and `0x7f` therefore have no causal authority",
            "Envelope-v4 `TIME_MASK=0xff` allocates all eight validity bits",
            "module-owned, write-once pre-UDC gate timestamp",
            "It is not gadget exposure or configfs bind time",
            "read back that exact gate marker and only then perform its sole configfs UDC bind",
            "An incomplete or unavailable host receipt is an observer failure",
            "`DEVICE_RESULT_DWC3_HOST_EVENT_NO_ENDPOINT`, not a host-silent result",
            "the predeclared exact rollback resume",
            "does not retroactively validate candidate attribution",
            "Candidate replay remains forbidden",
        )
        for clause in required:
            self.assertIn(clause, contract)


if __name__ == "__main__":
    unittest.main()

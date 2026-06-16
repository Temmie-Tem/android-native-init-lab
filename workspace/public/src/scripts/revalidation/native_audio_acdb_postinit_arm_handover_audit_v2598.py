#!/usr/bin/env python3
"""V2598 host-only audit for the post-init ACDB arm handover.

The operator handover asks for an acdb_ioctl dump that stays silent during init,
then arms after acdb_loader_init_v3() and before send_common_custom_topology().
This repo already contains that exact live attempt (V2562/V2576) plus the
working alternate arm point (V2563).  This audit makes that decision
machine-checkable before any redundant live run.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2598"
BUILD_TAG = "v2598-audio-acdb-postinit-arm-handover-audit"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2598_AUDIO_ACDB_POSTINIT_ARM_HANDOVER_AUDIT_2026-06-16.md"

REPORTS = {
    "v2562": ROOT / "docs/reports/NATIVE_INIT_V2562_AUDIO_ACDB_POSTINIT_ARMED_CAPTURE_LIVE_HANDOFF_2026-06-16.md",
    "v2563": ROOT / "docs/reports/NATIVE_INIT_V2563_AUDIO_ACDB_POSTINITIALIZE_TOPOLOGY_CAPTURE_LIVE_HANDOFF_2026-06-16.md",
    "v2576": ROOT / "docs/reports/NATIVE_INIT_V2576_AUDIO_ACDB_POSTINIT_MANUAL_ARM_TOPOLOGY_CAPTURE_LIVE_HANDOFF_2026-06-16.md",
    "v2577": ROOT / "docs/reports/NATIVE_INIT_V2577_AUDIO_ACDB_COMMON_TOPOLOGY_ENTRY_CAPTURE_LIVE_HANDOFF_2026-06-16.md",
    "v2597": ROOT / "docs/reports/NATIVE_INIT_V2597_AUDIO_ACDB_DIRECT_PREGET_LIVE_RESULT_2026-06-16.md",
}

SOURCES = {
    "v2562_build": ROOT / "workspace/public/src/scripts/revalidation/build_android_acdb_postinit_armed_capture_v2562.py",
    "v2563_build": ROOT / "workspace/public/src/scripts/revalidation/build_android_acdb_postinitialize_topology_capture_v2563.py",
    "tap": ROOT / "workspace/public/src/android/acdb_payload_capture/libacdbtap_v2475.c",
    "topology_helper": ROOT / "workspace/public/src/scripts/revalidation/build_android_acdb_armed_topology_exec_linked_v2540.py",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def marker(text: str, needle: str) -> bool:
    return needle in text


def source_contract() -> dict[str, Any]:
    v2562 = read_text(SOURCES["v2562_build"])
    v2563 = read_text(SOURCES["v2563_build"])
    tap = read_text(SOURCES["tap"])
    topology_helper = read_text(SOURCES["topology_helper"])
    return {
        "v2562_postinit_manual_arm_implemented": all(
            marker(v2562, token)
            for token in (
                "manual-arm only",
                "A90_ACDBTAP_AUTO_ARM_ON_INITIALIZE=0",
                "A90_ACDBTAP_EXIT_ON_TARGET=1",
                "helper_arms_after_init",
                "helper_calls_common_topology_after_arm",
            )
        ),
        "v2563_auto_arm_after_initialize_implemented": all(
            marker(v2563, token)
            for token in (
                "A90_ACDBTAP_AUTO_ARM_ON_INITIALIZE=1",
                "A90_ACDBTAP_CUSTOM_TOPOLOGY_ONLY=1",
                "target-only after INITIALIZE_V2",
                "exit immediately after first ret==0 non-all-zero 4916-byte buffer",
            )
        ),
        "tap_unarmed_path_no_dump_before_real": all(
            marker(tap, token)
            for token in (
                "if (!a90_armed)",
                "ret = a90_real_acdb_ioctl(cmd, in, in_len, out, out_len);",
                "return ret;",
            )
        ),
        "tap_manual_arm_exported": marker(tap, "void a90_arm_capture(void)") and marker(tap, "a90_armed = 1;"),
        "tap_zero_buffer_discriminator": marker(tap, "a90_is_all_zero") and marker(tap, "all_zero"),
        "topology_helper_calls_init_then_arm_then_common_topology": all(
            marker(topology_helper, token)
            for token in (
                "acdb_loader_init_v3",
                "a90_arm_capture",
                "acdb_loader_send_common_custom_topology",
            )
        ),
    }


def report_evidence() -> dict[str, Any]:
    texts = {key: read_text(path) for key, path in REPORTS.items()}
    return {
        "reports_present": {key: path.exists() for key, path in REPORTS.items()},
        "v2562_postinit_manual_arm_failed_before_arm": all(
            marker(texts["v2562"], token)
            for token in (
                "v2562-init-internal-topology-before-manual-arm-sigsegv",
                "helper_armed_before_common_topology: `False`",
                "acdb_log_has_common_topology: `True`",
                "acdb_log_has_topology_get: `True`",
            )
        ),
        "v2576_postinit_manual_arm_repeat_failed_before_arm": all(
            marker(texts["v2576"], token)
            for token in (
                "v2576-init-internal-topology-before-manual-arm-sigsegv",
                "helper_fallback_armed_before_common_topology: `False`",
                "acdb_log_has_common_topology: `True`",
                "acdb_log_has_topology_get: `True`",
            )
        ),
        "v2563_auto_arm_captured_topology": all(
            marker(texts["v2563"], token)
            for token in (
                "v2563-postinitialize-topology-captured",
                "topology_success_count: `1`",
                "topology seq=`0x00000001` cmd=`0x00013296` raw_size=`4916`",
                "sha256=`7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89`",
            )
        ),
        "v2577_common_topology_entry_arm_timed_out_without_acdbtap": all(
            marker(texts["v2577"], token)
            for token in (
                "v2577-common-topology-entry-armed-no-acdbtap-events",
                "common_hook_armed_before_real_common_topology: `True`",
                "topology_success_count: `0`",
                "helper-timeout",
            )
        ),
        "v2597_direct_preget_live": all(
            marker(texts["v2597"], token)
            for token in (
                "v2596-direct-preget-ret0-nonzero-rollback-pass",
                "acdb_ioctl(0x1122e, &0x11135, 4, out, 4) -> ret=0, out=0x10005000",
                "real `AUDIO_SET_CALIBRATION` pass-through: `0`",
            )
        ),
    }


def make_payload() -> dict[str, Any]:
    sources = source_contract()
    evidence = report_evidence()
    postinit_as_written_is_dead = bool(
        sources["v2562_postinit_manual_arm_implemented"]
        and evidence["v2562_postinit_manual_arm_failed_before_arm"]
        and evidence["v2576_postinit_manual_arm_repeat_failed_before_arm"]
    )
    alternate_topology_already_solved = bool(evidence["v2563_auto_arm_captured_topology"])
    common_hook_not_recommended = bool(evidence["v2577_common_topology_entry_arm_timed_out_without_acdbtap"])
    direct_preget_frontier_live = bool(evidence["v2597_direct_preget_live"])
    ok = bool(
        all(evidence["reports_present"].values())
        and sources["tap_unarmed_path_no_dump_before_real"]
        and sources["tap_zero_buffer_discriminator"]
        and postinit_as_written_is_dead
        and alternate_topology_already_solved
        and direct_preget_frontier_live
    )
    decision = (
        "v2598-postinit-arm-handover-superseded-by-existing-live-evidence"
        if ok
        else "v2598-postinit-arm-handover-audit-incomplete"
    )
    return {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "operator_spec": "docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md",
        "decision": decision,
        "ok": ok,
        "source_contract": sources,
        "evidence": evidence,
        "conclusion": {
            "postinit_after_init_return_should_not_be_rerun": postinit_as_written_is_dead,
            "topology_payload_already_captured_by_v2563": alternate_topology_already_solved,
            "common_topology_entry_hook_should_not_be_rerun_without_new_instrumentation": common_hook_not_recommended,
            "current_frontier_is_per_device_direct_get_after_v2597": direct_preget_frontier_live,
            "recommended_next_unit": (
                "Use V2597's live 0x1122e metadata result to derive the next pure-read "
                "per-device GET request geometry; do not repeat post-init topology arm."
            ),
        },
        "referenced_reports": {key: rel(path) for key, path in REPORTS.items()},
        "referenced_sources": {key: rel(path) for key, path in SOURCES.items()},
    }


def write_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# NATIVE_INIT V2598 — ACDB post-init arm handover audit",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Host-only audit of the operator handover requesting an `acdb_ioctl` dump that is",
        "silent during init, arms after `acdb_loader_init_v3()` returns, then calls",
        "`acdb_loader_send_common_custom_topology()`. No Android handoff, device action,",
        "speaker write, or raw ACDB payload publication was performed.",
        "",
        "## Decision",
        "",
        f"- decision: `{payload['decision']}`",
        f"- ok: `{payload['ok']}`",
        "- device_action: `none`",
        "- flash_action: `none`",
        "",
        "## Evidence",
        "",
        "- V2562 implemented the post-init manual-arm topology helper/preload and live result",
        "  `v2562-init-internal-topology-before-manual-arm-sigsegv` showed init entered the",
        "  topology path before the helper could arm.",
        "- V2576 repeated the same post-init manual-arm topology strategy and hit the same",
        "  `init-internal-topology-before-manual-arm-sigsegv` outcome.",
        "- V2563's alternate arm point, auto-arm immediately after `ACDB_CMD_INITIALIZE_V2`,",
        "  captured the real `4916`-byte topology payload with SHA",
        "  `7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89`.",
        "- V2577 proved the common-topology entry hook can arm before the real function, but",
        "  the real call timed out with zero `acdbtap` rows; do not rerun it unchanged.",
        "- V2597 proved the current frontier is live direct per-device metadata:",
        "  `acdb_ioctl(0x1122e, &0x11135, 4, out, 4) -> ret=0, out=0x10005000`.",
        "",
        "## Conclusion",
        "",
        "The requested post-`init_v3` manual-arm topology run is superseded by existing live",
        "evidence and should not be rerun as written. The topology payload is already captured",
        "and operator-verified; the meaningful next unit is per-device pure-read GET derivation",
        "from the V2597 `0x1122e` metadata result, not another topology arm variant.",
        "",
        "## Machine Checks",
        "",
        f"- postinit_after_init_return_should_not_be_rerun: `{payload['conclusion']['postinit_after_init_return_should_not_be_rerun']}`",
        f"- topology_payload_already_captured_by_v2563: `{payload['conclusion']['topology_payload_already_captured_by_v2563']}`",
        f"- common_topology_entry_hook_should_not_be_rerun_without_new_instrumentation: `{payload['conclusion']['common_topology_entry_hook_should_not_be_rerun_without_new_instrumentation']}`",
        f"- current_frontier_is_per_device_direct_get_after_v2597: `{payload['conclusion']['current_frontier_is_per_device_direct_get_after_v2597']}`",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_postinit_arm_handover_audit_v2598.py tests/test_native_audio_acdb_postinit_arm_handover_audit_v2598.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_postinit_arm_handover_audit_v2598`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_postinit_arm_handover_audit_v2598.py --write-report`",
        "- `git diff --check`",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON payload")
    parser.add_argument("--write-report", action="store_true", help="write the V2598 report")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = make_payload()
    if args.write_report:
        write_report(args.report_path, payload)
    if args.json or not args.write_report:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

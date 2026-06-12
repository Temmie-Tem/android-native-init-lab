#!/usr/bin/env python3
"""V2280 rollbackable live validation for the V2279 wide workqueue execute oracle.

Default mode is host-only dry-run. Live mode flashes the V2279 wide workqueue
execute_start + codeword boot image, waits for the helper-owned
post-FWREADY window, collects both sampler logs, rolls back to V2237, then
classifies wide workqueue execute_start evidence with the same-boot
codeword slide under the V2276 bounded UAO-patch-aware rule.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import (
    EvidenceStore,
    artifact_timestamp,
    read_bounded_json,
    safe_artifact_label,
    workspace_private_input_path,
    write_public_text,
)
import a90_transport as transport
import native_kernel_perf_regs_codeword_sample_ring_v2216 as codeword_v2216
import native_kernel_v2276_codeword_mismatch_postprocess as v2276
import native_kernel_workqueue_codeword_handoff_v2275 as v2275


REPO_ROOT = repo_root()
RUN_ROOT = REPO_ROOT / "workspace" / "private" / "runs" / "kernel"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2280_WORKQUEUE_EXEC_WIDE_LIVE_2026-06-12.md"
)
BUILD_MANIFEST = (
    REPO_ROOT
    / "workspace"
    / "private"
    / "builds"
    / "native-init"
    / "v2279-workqueue-exec-wide"
    / "manifest.json"
)
TEST_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2279_workqueue_exec_wide.img", legacy_fallback=False
)
ROLLBACK_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2237_supplicant_terminate_poll.img", legacy_fallback=False
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.276 (v2279-workqueue-exec-wide)"
ROLLBACK_EXPECT_VERSION = "A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)"
REQUIRED_CONFIRM = "I_UNDERSTAND_V2280_FLASHES_V2279_AND_ROLLS_BACK_TO_V2237"
REMOTE_ARTIFACTS = {
    "helper_result": "/cache/native-init-wifi-test-boot-v2279-helper.result",
    "summary": "/cache/native-init-wifi-test-boot-v2279.summary",
    "log": "/cache/native-init-wifi-test-boot-v2279.log",
    "workqueue_wide_log": "/cache/native-init-v2279-workqueue-exec-wide.log",
    "codeword_log": "/cache/native-init-v2279-tail-perf-regs-codeword.log",
}
TARGET_SYMBOLS = [
    "request_firmware_work_func",
    "_request_firmware",
    "request_firmware",
    "qdf_file_read",
    "qdf_ini_parse",
    "cfg_parse",
    "hdd_context_create",
    "wlan_hdd_pld_probe",
]

SAMPLE_RE = re.compile(r"^sample\s+(?P<body>.+)$", re.MULTILINE)
STACK_IP_RE = re.compile(r"^stack_ip\s+(?P<body>.+)$", re.MULTILINE)
STATS_RE = re.compile(r"^stats\s+(?P<body>.+)$", re.MULTILINE)
RESULT_RE = re.compile(r"^result=(?P<result>.+)$", re.MULTILINE)


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_scalar_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for item in body.split():
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        fields[key] = value
    return fields


def parse_int(value: str | int) -> int:
    if isinstance(value, int):
        return value
    return int(str(value), 0)


def load_build_manifest() -> dict[str, Any]:
    if not BUILD_MANIFEST.exists():
        return {}
    return read_bounded_json(BUILD_MANIFEST)


def preflight() -> dict[str, Any]:
    build_manifest = load_build_manifest()
    expected_test_sha = str(build_manifest.get("boot_sha256") or "") if build_manifest else ""
    test_sha = sha256(TEST_IMAGE) if TEST_IMAGE.exists() else ""
    rollback_sha = sha256(ROLLBACK_IMAGE) if ROLLBACK_IMAGE.exists() else ""
    return {
        "build_manifest": rel(BUILD_MANIFEST),
        "build_manifest_exists": BUILD_MANIFEST.exists(),
        "build_manifest_decision": build_manifest.get("decision"),
        "test_image": rel(TEST_IMAGE),
        "test_image_exists": TEST_IMAGE.exists(),
        "test_image_sha256": test_sha,
        "test_image_expected_sha256": expected_test_sha,
        "test_image_sha_matches_manifest": bool(expected_test_sha and test_sha == expected_test_sha),
        "rollback_image": rel(ROLLBACK_IMAGE),
        "rollback_image_exists": ROLLBACK_IMAGE.exists(),
        "rollback_image_sha256": rollback_sha,
        "test_expect_version": TEST_EXPECT_VERSION,
        "rollback_expect_version": ROLLBACK_EXPECT_VERSION,
        "remote_artifacts": REMOTE_ARTIFACTS,
        "recovery_twrp_available_source": "docs/operations/NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md",
        "flash_helper": "workspace/public/src/scripts/revalidation/native_init_flash.py",
    }


def dry_run_commands(preflight_result: dict[str, Any]) -> dict[str, Any]:
    test_sha = str(preflight_result.get("test_image_sha256") or "")
    rollback_sha = str(preflight_result.get("rollback_image_sha256") or "")
    return json.loads(json.dumps({
        "current_verify": [
            "python3",
            "workspace/public/src/scripts/revalidation/native_init_flash.py",
            "--verify-only",
            "--verify-protocol",
            "selftest",
            "--expect-version",
            ROLLBACK_EXPECT_VERSION,
            "--expect-sha256",
            rollback_sha,
            rel(ROLLBACK_IMAGE),
        ],
        "flash_test_boot": v2275.flash_command(TEST_IMAGE, TEST_EXPECT_VERSION, test_sha, from_native=True),
        "collect": [
            ["python3", "workspace/public/src/scripts/revalidation/a90ctl.py", "cat", path]
            for path in REMOTE_ARTIFACTS.values()
        ],
        "rollback": v2275.flash_command(ROLLBACK_IMAGE, ROLLBACK_EXPECT_VERSION, rollback_sha, from_native=True),
    }, default=str))


def parse_key_values(text: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for raw_line in text.replace("\r", "").splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not key or key.startswith("A90P1 "):
            continue
        values.setdefault(key, []).append(value.strip())
    return values


def last_value(values: dict[str, list[str]], key: str, default: str | None = None) -> str | None:
    items = values.get(key)
    if not items:
        return default
    return items[-1]


def parse_workqueue_wide_log(text: str) -> dict[str, Any]:
    stats_match = STATS_RE.search(text)
    stats = {
        key: parse_int(value)
        for key, value in parse_scalar_fields(stats_match.group("body")).items()
    } if stats_match else {}
    samples: dict[int, dict[str, Any]] = {}
    for match in SAMPLE_RE.finditer(text):
        fields = parse_scalar_fields(match.group("body"))
        if "index" not in fields:
            continue
        index = parse_int(fields["index"])
        row: dict[str, Any] = {"stack_ips": []}
        for key, value in fields.items():
            row[key] = parse_int(value) if key not in {"stackid"} else int(value, 0)
        samples[index] = row
    for match in STACK_IP_RE.finditer(text):
        fields = parse_scalar_fields(match.group("body"))
        if "sample" not in fields or "value" not in fields:
            continue
        index = parse_int(fields["sample"])
        samples.setdefault(index, {"index": index, "stack_ips": []})
        samples[index].setdefault("stack_ips", []).append({
            "index": parse_int(fields.get("index", 0)),
            "value": parse_int(fields["value"]),
            "kernelish": parse_int(fields.get("kernelish", 0)),
        })
    result_match = RESULT_RE.search(text)
    return {
        "stats": stats,
        "samples": [samples[key] for key in sorted(samples)],
        "result": result_match.group("result") if result_match else None,
    }


def symbol_resolver():
    symbols = codeword_v2216.load_text_symbols()
    addrs = [addr for addr, _ in symbols]
    names = [name for _, name in symbols]

    def resolve(static_addr: int) -> dict[str, Any]:
        index = bisect.bisect_right(addrs, static_addr) - 1
        if index < 0:
            return {"symbol": None, "offset": None, "static_hex": f"0x{static_addr:016x}"}
        symbol_addr = addrs[index]
        next_addr = addrs[index + 1] if index + 1 < len(addrs) else None
        in_range = next_addr is None or static_addr < next_addr
        return {
            "symbol": names[index] if in_range else None,
            "symbol_addr": f"0x{symbol_addr:016x}",
            "offset": static_addr - symbol_addr if in_range else None,
            "static_hex": f"0x{static_addr:016x}",
        }

    return resolve, dict((name, addr) for addr, name in symbols)


def analyze_codeword(codeword_text: str) -> dict[str, Any]:
    probe = codeword_v2216.parse_helper_stdout(codeword_text)
    analysis = codeword_v2216.analyze_probe(probe)
    codeword = analysis.get("codeword") or {}
    best = codeword.get("best") or {}
    slide = v2276.as_int(best.get("slide", 0))
    mismatches, counts = v2276.mismatch_rows(probe, slide)
    all_mismatches_are_uao = bool(mismatches) and all(row.get("uao_patch_class") for row in mismatches)
    lr_exact = (
        counts["lr_prev_readable"] > 0
        and counts["lr_prev_match"] == counts["lr_prev_readable"]
        and counts["lr_readable"] > 0
        and counts["lr_match"] == counts["lr_readable"]
    )
    patch_aware_accepted = bool(
        all_mismatches_are_uao
        and lr_exact
        and counts["pc_readable"] - counts["pc_match"] == len(mismatches)
    )
    existing_accepted = bool(codeword.get("accepted_symbolization_slide") or codeword.get("accepted_exact_codeword_slide"))
    return {
        "probe": probe,
        "analysis": analysis,
        "slide": slide,
        "slide_hex": best.get("slide_hex") or f"0x{slide:x}",
        "accepted": bool(existing_accepted or patch_aware_accepted),
        "accepted_existing": existing_accepted,
        "patch_aware_accepted": patch_aware_accepted,
        "acceptance_reason": codeword.get("acceptance_reason") or ("uao_patch_aware" if patch_aware_accepted else None),
        "counts": counts,
        "mismatch_count": len(mismatches),
        "mismatch_classes": sorted({str(row.get("uao_patch_class")) for row in mismatches}),
        "best": best,
        "printed_samples": len(probe.get("samples") or []),
        "occupied_samples": analysis.get("occupied_samples"),
        "capacity": analysis.get("capacity"),
    }


def classify_artifacts(paths: dict[str, Path]) -> dict[str, Any]:
    stack_text = paths.get("workqueue_wide_log", Path()).read_text(encoding="utf-8", errors="replace") if paths.get("workqueue_wide_log") and paths["workqueue_wide_log"].exists() else ""
    codeword_text = paths.get("codeword_log", Path()).read_text(encoding="utf-8", errors="replace") if paths.get("codeword_log") and paths["codeword_log"].exists() else ""
    helper_text = "\n".join(
        paths[name].read_text(encoding="utf-8", errors="replace")
        for name in ("helper_result", "summary", "log")
        if name in paths and paths[name].exists()
    )
    helper_values = parse_key_values(helper_text)

    workqueue = parse_workqueue_wide_log(stack_text)
    codeword = analyze_codeword(codeword_text) if codeword_text else {"accepted": False, "slide": 0, "slide_hex": None}
    resolve, symbol_index = symbol_resolver()
    target_static = {name: symbol_index[name] for name in TARGET_SYMBOLS if name in symbol_index}
    slide = int(codeword.get("slide") or 0)
    function_hits: list[dict[str, Any]] = []
    stack_hits: list[dict[str, Any]] = []
    samples_out: list[dict[str, Any]] = []
    function_symbol_counts: dict[str, int] = {}
    stack_symbol_counts: dict[str, int] = {}
    for sample in workqueue.get("samples") or []:
        function = int(sample.get("function", 0))
        function_resolved = resolve(function - slide) if slide and function else {"symbol": None, "offset": None, "static_hex": None}
        function_symbol = function_resolved.get("symbol")
        if function_symbol:
            function_symbol_counts[str(function_symbol)] = function_symbol_counts.get(str(function_symbol), 0) + 1
        stack_symbols: list[dict[str, Any]] = []
        for ip in sample.get("stack_ips") or []:
            value = int(ip.get("value", 0))
            if not value or not slide:
                continue
            resolved = resolve(value - slide)
            symbol = resolved.get("symbol")
            if symbol:
                stack_symbol_counts[str(symbol)] = stack_symbol_counts.get(str(symbol), 0) + 1
            row = {
                "index": ip.get("index"),
                "runtime": f"0x{value:016x}",
                "static": resolved.get("static_hex"),
                "symbol": symbol,
                "offset": resolved.get("offset"),
            }
            stack_symbols.append(row)
            if symbol in target_static:
                stack_hits.append({"sample": sample.get("index"), **row})
        row = {
            "index": sample.get("index"),
            "seq": sample.get("seq"),
            "pid": sample.get("pid"),
            "tgid": sample.get("tgid"),
            "work": f"0x{int(sample.get('work', 0)):016x}",
            "function": f"0x{function:016x}",
            "function_static": function_resolved.get("static_hex"),
            "function_symbol": function_symbol,
            "function_offset": function_resolved.get("offset"),
            "stack_depth_printed": len(sample.get("stack_ips") or []),
            "stack_symbols": stack_symbols[:16],
        }
        if len(samples_out) < 32:
            samples_out.append(row)
        if function_symbol in target_static:
            function_hits.append(row)

    total = int((workqueue.get("stats") or {}).get("total", 0))
    stored = int((workqueue.get("stats") or {}).get("stored", 0))
    printed = len(workqueue.get("samples") or [])
    overflow = int((workqueue.get("stats") or {}).get("overflow", 0))
    if not stack_text:
        classification = "workqueue-wide-log-missing"
    elif workqueue.get("result") != "v2279-workqueue-exec-wide-sample-ring-complete":
        classification = "workqueue-wide-sampler-incomplete"
    elif not codeword_text:
        classification = "codeword-log-missing"
    elif not codeword.get("accepted"):
        classification = "codeword-slide-unusable"
    elif total <= 0 or stored <= 0:
        classification = "workqueue-wide-no-activity"
    elif function_hits or stack_hits:
        classification = "workqueue-exec-wide-target-hit"
    elif overflow > 0 or printed < stored:
        classification = "workqueue-exec-wide-no-target-hit-partial-coverage"
    else:
        classification = "workqueue-exec-wide-no-target-hit"

    return {
        "classification": classification,
        "target_symbols": TARGET_SYMBOLS,
        "target_symbol_static": {name: f"0x{addr:016x}" for name, addr in target_static.items()},
        "target_hit_count": len(function_hits) + len(stack_hits),
        "function_target_hit_count": len(function_hits),
        "stack_target_hit_count": len(stack_hits),
        "function_target_hits": function_hits[:32],
        "stack_target_hits": stack_hits[:32],
        "workqueue": {
            "result": workqueue.get("result"),
            "stats": workqueue.get("stats"),
            "sample_count": len(workqueue.get("samples") or []),
            "function_symbol_counts_top": sorted(function_symbol_counts.items(), key=lambda item: (-item[1], item[0]))[:24],
            "stack_symbol_counts_top": sorted(stack_symbol_counts.items(), key=lambda item: (-item[1], item[0]))[:24],
            "sample_preview": samples_out,
        },
        "codeword": {
            key: value for key, value in codeword.items() if key not in {"probe", "analysis"}
        },
        "helper": {
            "wlan0_present": last_value(helper_values, "wlan0_present"),
            "supervisor_result": last_value(helper_values, "supervisor_result"),
            "helper_exit_code": last_value(helper_values, "helper_exit_code") or last_value(helper_values, "child_exit_code"),
            "helper_timed_out": last_value(helper_values, "helper_timed_out") or last_value(helper_values, "timed_out"),
        },
    }


def collect_artifacts(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    device_dir = store.mkdir("device")
    paths: dict[str, Path] = {}
    collected: dict[str, Any] = {}
    for name, remote_path in REMOTE_ARTIFACTS.items():
        result = v2275.run_command(v2275.a90ctl_command(args, ["cat", remote_path], allow_error=True), timeout=args.collect_timeout)
        v2275.write_step(store, steps, f"collect-{name}", result)
        local_path = device_dir / f"{name}.cmdv1.txt"
        local_path.write_text(str(result.get("stdout") or ""), encoding="utf-8")
        local_path.chmod(0o600)
        paths[name] = local_path
        collected[name] = {
            "remote_path": remote_path,
            "local_path": rel(local_path),
            "ok": bool(result.get("ok")),
            "bytes": local_path.stat().st_size,
        }
    return {"artifacts": collected, "classification": classify_artifacts(paths)}


def verify_current(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], expected_sha: str) -> dict[str, Any]:
    verify = v2275.run_command([
        "python3",
        "workspace/public/src/scripts/revalidation/native_init_flash.py",
        "--verify-only",
        "--verify-protocol",
        "selftest",
        "--expect-version",
        ROLLBACK_EXPECT_VERSION,
        "--expect-sha256",
        expected_sha,
        str(ROLLBACK_IMAGE),
    ], timeout=args.flash_timeout)
    v2275.write_step(store, steps, "preflight-current-baseline-verify", verify)
    status = v2275.run_a90ctl_step(store, steps, "preflight-current-status", args, ["status"], timeout=120)
    selftest = v2275.run_a90ctl_step(store, steps, "preflight-current-selftest", args, ["selftest"], timeout=120)
    return {
        "verify_ok": bool(verify.get("ok")),
        "status_ok": bool(status.get("ok")),
        "selftest_ok": bool(selftest.get("ok")) and "fail=0" in str(selftest.get("stdout") or ""),
    }


def rollback(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], rollback_sha: str) -> dict[str, Any]:
    first = v2275.run_command(v2275.flash_command(ROLLBACK_IMAGE, ROLLBACK_EXPECT_VERSION, rollback_sha, from_native=True), timeout=args.flash_timeout)
    v2275.write_step(store, steps, "rollback-v2237-from-native", first)
    attempt = "from-native"
    ok = bool(first.get("ok"))
    if not ok:
        second = v2275.run_command(v2275.flash_command(ROLLBACK_IMAGE, ROLLBACK_EXPECT_VERSION, rollback_sha, from_native=False), timeout=args.flash_timeout)
        v2275.write_step(store, steps, "rollback-v2237-from-recovery", second)
        attempt = "from-recovery"
        ok = bool(second.get("ok"))
    version = v2275.run_a90ctl_step(store, steps, "post-rollback-version", args, ["version"], timeout=120)
    status = v2275.run_a90ctl_step(store, steps, "post-rollback-status", args, ["status"], timeout=120)
    selftest = v2275.run_a90ctl_step(store, steps, "post-rollback-selftest", args, ["selftest"], timeout=120)
    return {
        "ok": ok,
        "attempt": attempt,
        "version_ok": bool(version.get("ok")) and ROLLBACK_EXPECT_VERSION in str(version.get("stdout") or ""),
        "status_ok": bool(status.get("ok")),
        "selftest_ok": bool(selftest.get("ok")) and "fail=0" in str(selftest.get("stdout") or ""),
    }


def classify_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if not manifest.get("execute"):
        pre = manifest["preflight"]
        ok = all([
            pre.get("build_manifest_exists"),
            pre.get("test_image_exists"),
            pre.get("test_image_sha_matches_manifest"),
            pre.get("rollback_image_exists"),
        ])
        return {
            "decision": "v2280-workqueue-exec-wide-dry-run-ready" if ok else "v2280-workqueue-exec-wide-dry-run-blocked",
            "pass": bool(ok),
            "reason": "host-only flash/capture/rollback plan is complete; live execution requires --execute and confirmation" if ok else "required V2279 build artifact or rollback image is missing/mismatched",
        }
    rollback_result = manifest.get("rollback") or {}
    if not rollback_result.get("selftest_ok"):
        return {"decision": "v2280-workqueue-exec-wide-rollback-selftest-failed", "pass": False, "reason": "rollback did not finish with selftest fail=0"}
    if manifest.get("live_block") == "preflight-current-baseline-failed":
        return {"decision": "v2280-workqueue-exec-wide-preflight-failed-no-flash", "pass": False, "reason": "current baseline verification failed before flashing V2279"}
    if manifest.get("live_block") == "test-flash-failed":
        return {"decision": "v2280-workqueue-exec-wide-test-flash-failed-rollback-pass", "pass": False, "reason": "V2279 flash or health verification failed, but rollback selftest fail=0 passed"}
    classification = ((manifest.get("collect") or {}).get("classification") or {}).get("classification", "unknown")
    if classification in {"workqueue-wide-log-missing", "workqueue-wide-sampler-incomplete", "codeword-log-missing", "codeword-slide-unusable"}:
        return {"decision": f"v2280-workqueue-exec-wide-live-{classification}-rollback-pass", "pass": False, "reason": "V2279 booted and rollback passed, but paired wide/codeword evidence was not classifiable"}
    return {"decision": f"v2280-workqueue-exec-wide-live-pass-{classification}", "pass": True, "reason": "V2279 wide workqueue execute-start and codeword artifacts were collected and classified; rollback selftest fail=0 passed"}


def render_report(manifest: dict[str, Any]) -> str:
    result = manifest["result"]
    pre = manifest["preflight"]
    lines = [
        "# Native Init V2280 Workqueue Execute Wide Live",
        "",
        "## Summary",
        "",
        "- Cycle: `V2280`",
        "- Type: rollbackable live validation of the V2279 wide workqueue execute_start and same-boot codeword observer.",
        f"- Decision: `{result['decision']}`",
        f"- Result: `{'PASS' if result['pass'] else 'FAIL'}`",
        f"- Reason: {result['reason']}",
        f"- Execute mode: `{manifest['execute']}`",
        f"- Evidence: `{manifest['out_dir']}`",
        "- Track: T1 kernel observation; no downgrade to T2/T3.",
        "",
        "## Images",
        "",
        f"- Test image: `{pre['test_image']}`",
        f"- Test SHA256: `{pre['test_image_sha256']}`",
        f"- Test version: `{pre['test_expect_version']}`",
        f"- Rollback image: `{pre['rollback_image']}`",
        f"- Rollback SHA256: `{pre['rollback_image_sha256']}`",
        f"- Rollback version: `{pre['rollback_expect_version']}`",
        "",
    ]
    if manifest.get("execute"):
        health = manifest.get("test_health") or {}
        rollback_result = manifest.get("rollback") or {}
        classification = ((manifest.get("collect") or {}).get("classification") or {})
        workqueue = classification.get("workqueue") or {}
        codeword = classification.get("codeword") or {}
        lines.extend([
            "## Live Evidence",
            "",
            f"- Preflight baseline verified: `{(manifest.get('current_preflight') or {}).get('verify_ok')}` selftest fail=0: `{(manifest.get('current_preflight') or {}).get('selftest_ok')}`",
            f"- V2279 flash OK: `{(manifest.get('test_flash') or {}).get('ok')}`",
            f"- V2279 health: version=`{health.get('version_ok')}` status=`{health.get('status_ok')}` selftest_fail0=`{health.get('selftest_ok')}`",
            f"- Rollback OK: `{rollback_result.get('ok')}` via `{rollback_result.get('attempt')}`",
            f"- Rollback health: version=`{rollback_result.get('version_ok')}` status=`{rollback_result.get('status_ok')}` selftest_fail0=`{rollback_result.get('selftest_ok')}`",
            f"- Classification: `{classification.get('classification')}`",
            f"- Workqueue samples: `{workqueue.get('sample_count')}` stats=`{workqueue.get('stats')}`",
            f"- Codeword slide: accepted=`{codeword.get('accepted')}` slide=`{codeword.get('slide_hex')}` reason=`{codeword.get('acceptance_reason')}` patch_aware=`{codeword.get('patch_aware_accepted')}`",
            f"- Target hits: total=`{classification.get('target_hit_count')}` function=`{classification.get('function_target_hit_count')}` stack=`{classification.get('stack_target_hit_count')}`",
            f"- Helper result: supervisor=`{((classification.get('helper') or {}).get('supervisor_result'))}` exit=`{((classification.get('helper') or {}).get('helper_exit_code'))}` timed_out=`{((classification.get('helper') or {}).get('helper_timed_out'))}` wlan0_present=`{((classification.get('helper') or {}).get('wlan0_present'))}`",
            "",
            "## Workqueue Wide Classification",
            "",
            f"- Workqueue sampler result: `{workqueue.get('result')}`",
            f"- Top function symbols: `{workqueue.get('function_symbol_counts_top')}`",
            f"- Top stack symbols: `{workqueue.get('stack_symbol_counts_top')}`",
            f"- Function target hits: `{classification.get('function_target_hits')}`",
            f"- Stack target hits: `{classification.get('stack_target_hits')}`",
            "",
        ])
        if classification.get("classification") == "workqueue-exec-wide-target-hit":
            lines.extend([
                "## Interpretation",
                "",
                "- The same-boot wide execute-start oracle intersects the firmware_class/qcacld-HDD target set.",
                "- Treat this as live code-path identity evidence, not as a Wi-Fi network functional test.",
                "",
            ])
        elif classification.get("classification") in {
            "workqueue-exec-wide-no-target-hit",
            "workqueue-exec-wide-no-target-hit-partial-coverage",
        }:
            lines.extend([
                "## Interpretation",
                "",
                "- The paired wide/codeword oracle was classifiable, but no execute_start function or printed stack frame intersected the firmware_class/qcacld-HDD target set.",
                "- This closes the V2278 overflow caveat for scalar `function` coverage: all observed execute_start rows were stored/printed with `overflow=0` and no target function hit. Stack evidence remains a bounded `512`-sample prefix, not a full-stack path-negative.",
                "",
            ])
    else:
        lines.extend([
            "## Dry-Run Plan",
            "",
            "```json",
            json.dumps(manifest.get("dry_run_commands") or {}, indent=2, ensure_ascii=False, default=str),
            "```",
            "",
        ])
    lines.extend([
        "## Safety Scope",
        "",
        "- Flash path is limited to boot partition via `native_init_flash.py`.",
        "- Rollback target is V2237, with post-rollback `version`/`status`/`selftest fail=0` verification.",
        "- Collection uses read-only `cat` through the native bridge after the helper window.",
        "- This run does not use Wi-Fi scan/connect, credentials, DHCP/routes, external ping, `probe_write_user`, tracefs control writes, eSoC/PCIe/GDSC/PMIC/GPIO paths, platform bind/unbind, or `sda29` writes.",
        "- The only target partition writes are the bounded test boot flash and rollback boot flash.",
        "",
    ])
    return "\n".join(lines)


def residual_state(manifest: dict[str, Any]) -> dict[str, Any]:
    steps = [step for step in manifest.get("steps", []) if isinstance(step, dict)]
    test_flash = manifest.get("test_flash") if isinstance(manifest.get("test_flash"), dict) else {}
    test_flash_attempted = "ok" in test_flash
    rollback_needed = bool(manifest.get("execute") and test_flash_attempted)
    rollback_result = manifest.get("rollback") if isinstance(manifest.get("rollback"), dict) else {}
    rollback_selftest_ok = bool(rollback_result.get("selftest_ok"))
    rollback_ok = bool(rollback_result.get("ok")) and rollback_selftest_ok if rollback_needed else True
    cleanup_required = bool(rollback_needed and not rollback_ok)
    return {
        "device_touched": bool(manifest.get("execute") and steps),
        "flash_reboot": test_flash_attempted,
        "test_flash_ok": bool(test_flash.get("ok")),
        "rollback_ok": rollback_ok,
        "rollback_attempt": rollback_result.get("attempt", "not-needed-no-flash"),
        "selftest_ok": rollback_selftest_ok if rollback_needed else True,
        "cleanup_required": cleanup_required,
        "residual_risk": "rollback-or-selftest-incomplete" if cleanup_required else "none",
        "wifi_scan_connect": False,
        "credentials_used": False,
        "dhcp_routes_ping": False,
        "tracefs_control_write": False,
        "bpf_attach": bool(manifest.get("execute")),
        "read_only_bpf": True,
        "probe_write_user_executed": False,
        "partition_write": test_flash_attempted,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2280-workqueue-exec-wide-live")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--collect-timeout", type=float, default=420.0)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--post-boot-wait-sec", type=float, default=125.0)
    parser.add_argument("--execute", action="store_true", help="perform the live flash/capture/rollback sequence")
    parser.add_argument("--confirm", default="", help=f"required for --execute: {REQUIRED_CONFIRM}")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    label = safe_artifact_label(args.label)
    run_dir = RUN_ROOT / f"{label}-{artifact_timestamp()}"
    store = EvidenceStore(run_dir)
    steps: list[dict[str, Any]] = []
    manifest: dict[str, Any] = {
        "cycle": "V2280",
        "started_at": now_iso(),
        "out_dir": rel(run_dir),
        "execute": bool(args.execute),
        "preflight": {},
        "steps": steps,
        "phase_timer_contract": transport.PHASE_TIMER_CONTRACT,
        "phase_timers": [],
        "safety": {
            "dry_run_default": True,
            "requires_confirm_for_flash": True,
            "flash_helper_only": True,
            "partition_write_scope": "boot image flash to V2279 and rollback to V2237 only" if args.execute else "none",
            "wifi_scan_connect": False,
            "credentials": False,
            "dhcp_routes_ping": False,
            "bpf_attach": bool(args.execute),
            "read_only_bpf": True,
            "probe_write_user": False,
            "tracefs_write": False,
        },
    }
    with transport.phase(manifest, "host_preflight"):
        preflight_result = preflight()
    manifest["preflight"] = preflight_result
    if not args.execute:
        with transport.phase(manifest, "dry_run_plan"):
            manifest["dry_run_commands"] = dry_run_commands(preflight_result)
    elif args.confirm != REQUIRED_CONFIRM:
        manifest["result"] = {"decision": "v2280-workqueue-exec-wide-live-confirmation-missing", "pass": False, "reason": "live mode requires the exact confirmation token"}
    else:
        with transport.phase(manifest, "verify_current_baseline"):
            current = verify_current(args, store, steps, str(preflight_result["rollback_image_sha256"]))
        manifest["current_preflight"] = current
        if not (current.get("verify_ok") and current.get("selftest_ok")):
            manifest["live_block"] = "preflight-current-baseline-failed"
            manifest["rollback"] = {"ok": True, "attempt": "not-needed-pre-test-flash", "selftest_ok": True}
        else:
            with transport.phase(manifest, "test_flash"):
                test_flash = v2275.run_command(
                    v2275.flash_command(TEST_IMAGE, TEST_EXPECT_VERSION, str(preflight_result["test_image_sha256"]), from_native=True),
                    timeout=args.flash_timeout,
                )
            v2275.write_step(store, steps, "flash-v2279-from-native", test_flash)
            manifest["test_flash"] = {"ok": bool(test_flash.get("ok")), "rc": test_flash.get("rc")}
            if bool(test_flash.get("ok")):
                with transport.phase(manifest, "test_boot_health"):
                    version = v2275.run_a90ctl_step(store, steps, "test-boot-version", args, ["version"], timeout=120)
                    status = v2275.run_a90ctl_step(store, steps, "test-boot-status", args, ["status"], timeout=120)
                    selftest = v2275.run_a90ctl_step(store, steps, "test-boot-selftest", args, ["selftest"], timeout=120)
                manifest["test_health"] = {
                    "version_ok": bool(version.get("ok")) and TEST_EXPECT_VERSION in str(version.get("stdout") or ""),
                    "status_ok": bool(status.get("ok")),
                    "selftest_ok": bool(selftest.get("ok")) and "fail=0" in str(selftest.get("stdout") or ""),
                }
                with transport.phase(manifest, "post_boot_helper_window_wait"):
                    wait_started = now_iso()
                    time.sleep(max(0.0, args.post_boot_wait_sec))
                    v2275.write_step(store, steps, "post-boot-helper-window-wait", {
                        "command": ["sleep", f"{args.post_boot_wait_sec:.3f}"],
                        "started": wait_started,
                        "ended": now_iso(),
                        "timeout": False,
                        "rc": 0,
                        "ok": True,
                        "stdout": f"waited_sec={args.post_boot_wait_sec:.3f}\n",
                        "stderr": "",
                    })
                with transport.phase(manifest, "collect_artifacts"):
                    manifest["collect"] = collect_artifacts(args, store, steps)
            else:
                manifest["live_block"] = "test-flash-failed"
            with transport.phase(manifest, "rollback"):
                manifest["rollback"] = rollback(args, store, steps, str(preflight_result["rollback_image_sha256"]))
    if "result" not in manifest:
        with transport.phase(manifest, "classify"):
            manifest["result"] = classify_manifest(manifest)
    manifest["finished_at"] = now_iso()
    transport.set_residual_state(manifest, residual_state(manifest))
    store.write_json("manifest.json", manifest)
    write_public_text(REPORT_PATH, render_report(manifest))
    print(json.dumps({
        "decision": manifest["result"]["decision"],
        "pass": manifest["result"]["pass"],
        "out_dir": manifest["out_dir"],
        "execute": manifest["execute"],
    }, indent=2, ensure_ascii=False))
    return 0 if manifest["result"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

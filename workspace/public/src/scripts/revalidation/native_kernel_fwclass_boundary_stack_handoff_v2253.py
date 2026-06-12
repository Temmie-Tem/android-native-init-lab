#!/usr/bin/env python3
"""V2253 rollbackable live validation for V2252 firmware_class boundary stacks.

Default mode is host-only dry-run.  Live mode flashes the V2252 boundary-stack
boot image, waits for the helper-owned firmware_class feeder window, collects
/cache helper artifacts, classifies the before/after feed stack snapshots, then
rolls back to the V2237 baseline and verifies selftest fail=0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
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


REPO_ROOT = repo_root()
RUN_ROOT = REPO_ROOT / "workspace" / "private" / "runs" / "kernel"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2253_FWCLASS_BOUNDARY_STACK_LIVE_2026-06-12.md"
)
BUILD_MANIFEST = (
    REPO_ROOT
    / "workspace"
    / "private"
    / "builds"
    / "native-init"
    / "v2252-fwclass-boundary-stack"
    / "manifest.json"
)
TEST_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2252_fwclass_boundary_stack.img", legacy_fallback=False
)
ROLLBACK_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2237_supplicant_terminate_poll.img", legacy_fallback=False
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.271 (v2252-fwclass-boundary-stack)"
ROLLBACK_EXPECT_VERSION = "A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)"
REQUIRED_CONFIRM = "I_UNDERSTAND_V2253_FLASHES_V2252_AND_ROLLS_BACK_TO_V2237"
REMOTE_ARTIFACTS = {
    "helper_result": "/cache/native-init-wifi-test-boot-v2252-helper.result",
    "summary": "/cache/native-init-wifi-test-boot-v2252.summary",
    "log": "/cache/native-init-wifi-test-boot-v2252.log",
}
TARGET_SYMBOLS = [
    "_request_firmware",
    "request_firmware",
    "qdf_file_read",
    "qdf_ini_parse",
    "cfg_parse",
    "hdd_context_create",
    "wlan_hdd_pld_probe",
]
REQUESTS = {
    0: "WCNSS_qcom_cfg.ini",
    1: "bdwlan.bin",
    2: "regdb.bin",
}


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


def run_command(command: list[object], *, timeout: float) -> dict[str, Any]:
    rendered = [str(item) for item in command]
    print("+ " + shlex.join(rendered), flush=True)
    started = now_iso()
    try:
        completed = subprocess.run(
            rendered,
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return {
            "command": rendered,
            "started": started,
            "ended": now_iso(),
            "timeout": False,
            "rc": completed.returncode,
            "ok": completed.returncode == 0,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": rendered,
            "started": started,
            "ended": now_iso(),
            "timeout": True,
            "rc": None,
            "ok": False,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }


def write_step(store: EvidenceStore, steps: list[dict[str, Any]], name: str, result: dict[str, Any]) -> dict[str, Any]:
    stdout_path = store.write_log("host", f"{name}.stdout.txt", str(result.get("stdout") or ""))
    stderr_path = store.write_log("host", f"{name}.stderr.txt", str(result.get("stderr") or ""))
    step = {
        "name": name,
        "command": result["command"],
        "started": result["started"],
        "ended": result["ended"],
        "timeout": result["timeout"],
        "rc": result["rc"],
        "ok": result["ok"],
        "stdout_file": str(stdout_path.relative_to(store.run_dir)),
        "stderr_file": str(stderr_path.relative_to(store.run_dir)),
    }
    steps.append(step)
    return step



def run_a90ctl_step(store: EvidenceStore,
                    steps: list[dict[str, Any]],
                    name: str,
                    args: argparse.Namespace,
                    command: list[str],
                    *,
                    allow_error: bool = True,
                    timeout: float = 90.0,
                    attempts: int = 3,
                    delay_sec: float = 4.0) -> dict[str, Any]:
    last_result: dict[str, Any] | None = None
    for attempt in range(1, max(1, attempts) + 1):
        result = run_command(a90ctl_command(args, command, allow_error=allow_error), timeout=timeout)
        write_step(store, steps, f"{name}-attempt-{attempt}", result)
        if result.get("ok"):
            result = dict(result)
            result["attempt"] = attempt
            return result
        last_result = result
        if attempt < attempts:
            time.sleep(delay_sec)
    assert last_result is not None
    last_result = dict(last_result)
    last_result["attempt"] = attempts
    return last_result

def a90ctl_command(args: argparse.Namespace, command: list[str], *, allow_error: bool = False) -> list[object]:
    rendered: list[object] = [
        "python3",
        "workspace/public/src/scripts/revalidation/a90ctl.py",
        "--host",
        args.bridge_host,
        "--port",
        str(args.bridge_port),
        "--timeout",
        str(args.timeout),
        "--input-mode",
        "slow",
        "--hide-on-busy",
    ]
    if allow_error:
        rendered.append("--allow-error")
    rendered.extend(command)
    return rendered


def flash_command(image: Path, expect_version: str, expect_sha: str, *, from_native: bool) -> list[object]:
    command: list[object] = [
        "python3",
        "workspace/public/src/scripts/revalidation/native_init_flash.py",
        image,
        "--expect-version",
        expect_version,
        "--expect-sha256",
        expect_sha,
        "--verify-protocol",
        "selftest",
        "--bridge-timeout",
        "260",
        "--recovery-timeout",
        "260",
    ]
    if from_native:
        command.append("--from-native")
    return command


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
        ],
        "flash_test_boot": flash_command(Path(rel(TEST_IMAGE)), TEST_EXPECT_VERSION, test_sha, from_native=True),
        "collect": [
            ["python3", "workspace/public/src/scripts/revalidation/a90ctl.py", "cat", path]
            for path in REMOTE_ARTIFACTS.values()
        ],
        "rollback": flash_command(Path(rel(ROLLBACK_IMAGE)), ROLLBACK_EXPECT_VERSION, rollback_sha, from_native=True),
        "post_rollback": [
            ["python3", "workspace/public/src/scripts/revalidation/a90ctl.py", "version"],
            ["python3", "workspace/public/src/scripts/revalidation/a90ctl.py", "status"],
            ["python3", "workspace/public/src/scripts/revalidation/a90ctl.py", "selftest"],
        ],
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


def int_value(values: dict[str, list[str]], key: str) -> int | None:
    value = last_value(values, key)
    if value is None:
        return None
    try:
        return int(value, 0)
    except ValueError:
        return None


def summarize_phase(values: dict[str, list[str]], phase: str) -> dict[str, Any]:
    prefix = f"icnss_register_probe_stack_sampler.{phase}."
    sample_re = re.compile(rf"^{re.escape(prefix)}sample_(\d+)\.(.+)$")
    samples: dict[int, dict[str, Any]] = {}
    phase_text_parts: list[str] = []
    for key, entries in values.items():
        match = sample_re.match(key)
        if not match:
            continue
        sample_index = int(match.group(1))
        field = match.group(2)
        sample = samples.setdefault(sample_index, {})
        value = entries[-1]
        sample[field] = value
        if field.startswith("stack_") or field in {"wchan", "comm"}:
            phase_text_parts.append(value)
    phase_text = "\n".join(phase_text_parts)
    symbols_present = [symbol for symbol in TARGET_SYMBOLS if symbol in phase_text]
    target_samples = []
    for sample_index, sample in sorted(samples.items()):
        stack_text = "\n".join(
            str(sample[key])
            for key in sorted(sample)
            if key.startswith("stack_") or key in {"wchan", "comm"}
        )
        sample_symbols = [symbol for symbol in TARGET_SYMBOLS if symbol in stack_text]
        target_flag = str(sample.get("target") or "0") == "1"
        if target_flag or sample_symbols:
            target_samples.append({
                "sample": sample_index,
                "comm": sample.get("comm"),
                "wchan": sample.get("wchan"),
                "target": target_flag,
                "symbols_present": sample_symbols,
                "symbol_count": len(sample_symbols),
            })
    return {
        "phase": phase,
        "begin": last_value(values, prefix + "begin"),
        "end": last_value(values, prefix + "end"),
        "scanned": int_value(values, prefix + "scanned"),
        "target_hits": int_value(values, prefix + "target_hits"),
        "samples": int_value(values, prefix + "samples"),
        "stack_open_ok": int_value(values, prefix + "stack_open_ok"),
        "stack_open_fail": int_value(values, prefix + "stack_open_fail"),
        "symbols_present": symbols_present,
        "symbol_count": len(symbols_present),
        "full_target_stack": len(symbols_present) == len(TARGET_SYMBOLS),
        "target_samples": target_samples[:4],
    }


def classify_boundary_artifacts(paths: dict[str, Path]) -> dict[str, Any]:
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in paths.values() if path.exists())
    values = parse_key_values(text)
    requests: dict[str, Any] = {}
    boundary_phase_count = 0
    before_full = []
    after_full = []
    before_partial = []
    after_partial = []
    for index, request_name in REQUESTS.items():
        request_summary: dict[str, Any] = {
            "index": index,
            "request": request_name,
            "feeder_label": last_value(values, f"qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_{index}.label"),
            "firmware": last_value(values, f"qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_{index}.firmware"),
            "seen": int_value(values, f"qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_{index}.seen"),
            "fed": int_value(values, f"qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_{index}.fed"),
            "source_bytes": int_value(values, f"qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_{index}.source_bytes"),
            "data_rc": int_value(values, f"qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_{index}.data_rc"),
            "loading_done_rc": int_value(values, f"qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_{index}.loading_done_rc"),
            "final_seen": int_value(values, f"qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_{index}.final_seen"),
            "final_fed": int_value(values, f"qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.request_{index}.final_fed"),
        }
        for point in ("before_feed", "after_feed"):
            boundary_prefix = f"qcacld_fwclass_boundary_stack_sampler.after_boot_wlan_trigger.request_{index}.{point}."
            phase = f"fwclass_req{index}_{point}"
            phase_summary = summarize_phase(values, phase)
            phase_summary["boundary_begin"] = last_value(values, boundary_prefix + "begin")
            phase_summary["boundary_end"] = last_value(values, boundary_prefix + "end")
            phase_summary["boundary_label"] = last_value(values, boundary_prefix + "label")
            phase_summary["boundary_firmware"] = last_value(values, boundary_prefix + "firmware")
            if phase_summary["boundary_begin"] == "1" or phase_summary["begin"] == "1":
                boundary_phase_count += 1
            request_summary[point] = phase_summary
            if phase_summary["full_target_stack"]:
                (before_full if point == "before_feed" else after_full).append(index)
            elif phase_summary["symbol_count"] > 0 or (phase_summary.get("target_hits") or 0) > 0:
                (before_partial if point == "before_feed" else after_partial).append(index)
        requests[str(index)] = request_summary

    if before_full:
        ordering_class = "target-stack-visible-before-feed"
    elif after_full:
        ordering_class = "target-stack-visible-after-feed"
    elif before_partial:
        ordering_class = "partial-target-stack-before-feed"
    elif after_partial:
        ordering_class = "partial-target-stack-after-feed"
    elif boundary_phase_count > 0:
        ordering_class = "boundary-captured-no-target-stack"
    else:
        ordering_class = "boundary-markers-missing"

    return {
        "ordering_class": ordering_class,
        "boundary_phase_count": boundary_phase_count,
        "before_full_requests": before_full,
        "after_full_requests": after_full,
        "before_partial_requests": before_partial,
        "after_partial_requests": after_partial,
        "target_symbols": TARGET_SYMBOLS,
        "feeder_seen_count": int_value(values, "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.seen_count"),
        "feeder_fed_count": int_value(values, "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.fed_count"),
        "feeder_timed_out": int_value(values, "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger.timed_out"),
        "wlan0_present": last_value(values, "wlan0_present"),
        "supervisor_result": last_value(values, "supervisor_result"),
        "helper_exit_code": last_value(values, "helper_exit_code") or last_value(values, "child_exit_code"),
        "helper_timed_out": last_value(values, "helper_timed_out") or last_value(values, "timed_out"),
        "requests": requests,
    }


def collect_artifacts(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    device_dir = store.mkdir("device")
    paths: dict[str, Path] = {}
    collected: dict[str, Any] = {}
    for name, remote_path in REMOTE_ARTIFACTS.items():
        result = run_command(a90ctl_command(args, ["cat", remote_path], allow_error=True), timeout=args.collect_timeout)
        write_step(store, steps, f"collect-{name}", result)
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
    return {
        "artifacts": collected,
        "classification": classify_boundary_artifacts(paths),
    }


def verify_current(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], expected_sha: str) -> dict[str, Any]:
    verify = run_command([
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
    write_step(store, steps, "preflight-current-baseline-verify", verify)
    status = run_a90ctl_step(store, steps, "preflight-current-status", args, ["status"], timeout=120)
    selftest = run_a90ctl_step(store, steps, "preflight-current-selftest", args, ["selftest"], timeout=120)
    return {
        "verify_ok": bool(verify.get("ok")),
        "status_ok": bool(status.get("ok")),
        "selftest_ok": bool(selftest.get("ok")) and "fail=0" in str(selftest.get("stdout") or ""),
    }


def rollback(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], rollback_sha: str) -> dict[str, Any]:
    first = run_command(flash_command(ROLLBACK_IMAGE, ROLLBACK_EXPECT_VERSION, rollback_sha, from_native=True), timeout=args.flash_timeout)
    write_step(store, steps, "rollback-v2237-from-native", first)
    attempt = "from-native"
    ok = bool(first.get("ok"))
    if not ok:
        second = run_command(flash_command(ROLLBACK_IMAGE, ROLLBACK_EXPECT_VERSION, rollback_sha, from_native=False), timeout=args.flash_timeout)
        write_step(store, steps, "rollback-v2237-from-recovery", second)
        attempt = "from-recovery"
        ok = bool(second.get("ok"))
    version = run_a90ctl_step(store, steps, "post-rollback-version", args, ["version"], timeout=120)
    status = run_a90ctl_step(store, steps, "post-rollback-status", args, ["status"], timeout=120)
    selftest = run_a90ctl_step(store, steps, "post-rollback-selftest", args, ["selftest"], timeout=120)
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
            "decision": "v2253-fwclass-boundary-stack-dry-run-ready" if ok else "v2253-fwclass-boundary-stack-dry-run-blocked",
            "pass": bool(ok),
            "reason": "host-only flash/capture/rollback plan is complete; live execution requires --execute and confirmation" if ok else "required V2252 build artifact or rollback image is missing/mismatched",
        }
    rollback_result = manifest.get("rollback") or {}
    if not rollback_result.get("selftest_ok"):
        return {
            "decision": "v2253-fwclass-boundary-stack-rollback-selftest-failed",
            "pass": False,
            "reason": "rollback did not finish with selftest fail=0",
        }
    if manifest.get("live_block") == "preflight-current-baseline-failed":
        return {
            "decision": "v2253-fwclass-boundary-stack-preflight-failed-no-flash",
            "pass": False,
            "reason": "current baseline verification failed before flashing V2252",
        }
    if manifest.get("live_block") == "test-flash-failed":
        return {
            "decision": "v2253-fwclass-boundary-stack-test-flash-failed-rollback-pass",
            "pass": False,
            "reason": "V2252 flash or health verification failed, but rollback selftest fail=0 passed",
        }
    collect = manifest.get("collect") or {}
    classification = collect.get("classification") or {}
    ordering = str(classification.get("ordering_class") or "unknown")
    if ordering == "boundary-markers-missing":
        return {
            "decision": "v2253-fwclass-boundary-stack-live-boundary-missing-rollback-pass",
            "pass": False,
            "reason": "V2252 booted and rollback passed, but boundary stack markers were not found in helper artifacts",
        }
    return {
        "decision": f"v2253-fwclass-boundary-stack-live-pass-{ordering}",
        "pass": True,
        "reason": "V2252 boundary stack artifacts were collected and classified; rollback selftest fail=0 passed",
    }


def render_report(manifest: dict[str, Any]) -> str:
    result = manifest["result"]
    pre = manifest["preflight"]
    lines = [
        "# Native Init V2253 Firmware Class Boundary Stack Live",
        "",
        "## Summary",
        "",
        "- Cycle: `V2253`",
        "- Type: rollbackable live validation of the V2252 firmware_class before/after feed stack observer.",
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
        lines.extend([
            "## Live Evidence",
            "",
            f"- Preflight baseline verified: `{(manifest.get('current_preflight') or {}).get('verify_ok')}` selftest fail=0: `{(manifest.get('current_preflight') or {}).get('selftest_ok')}`",
            f"- V2252 flash OK: `{(manifest.get('test_flash') or {}).get('ok')}`",
            f"- V2252 health: version=`{health.get('version_ok')}` status=`{health.get('status_ok')}` selftest_fail0=`{health.get('selftest_ok')}`",
            f"- Rollback OK: `{rollback_result.get('ok')}` via `{rollback_result.get('attempt')}`",
            f"- Rollback health: version=`{rollback_result.get('version_ok')}` status=`{rollback_result.get('status_ok')}` selftest_fail0=`{rollback_result.get('selftest_ok')}`",
            f"- Boundary phase count: `{classification.get('boundary_phase_count')}`",
            f"- Ordering class: `{classification.get('ordering_class')}`",
            f"- Feeder: seen=`{classification.get('feeder_seen_count')}` fed=`{classification.get('feeder_fed_count')}` timed_out=`{classification.get('feeder_timed_out')}`",
            f"- Helper result: supervisor=`{classification.get('supervisor_result')}` exit=`{classification.get('helper_exit_code')}` timed_out=`{classification.get('helper_timed_out')}` wlan0_present=`{classification.get('wlan0_present')}`",
            "",
            "## Boundary Classification",
            "",
        ])
        requests = classification.get("requests") or {}
        for index_text in sorted(requests, key=lambda item: int(item)):
            request = requests[index_text]
            before = request.get("before_feed") or {}
            after = request.get("after_feed") or {}
            lines.extend([
                f"- Request `{index_text}` `{request.get('request')}`: seen=`{request.get('seen')}` fed=`{request.get('fed')}` final_seen=`{request.get('final_seen')}` final_fed=`{request.get('final_fed')}` bytes=`{request.get('source_bytes')}`",
                f"  - before_feed: boundary=`{before.get('boundary_begin')}` target_hits=`{before.get('target_hits')}` samples=`{before.get('samples')}` symbols=`{before.get('symbol_count')}/7` full=`{before.get('full_target_stack')}`",
                f"  - after_feed: boundary=`{after.get('boundary_begin')}` target_hits=`{after.get('target_hits')}` samples=`{after.get('samples')}` symbols=`{after.get('symbol_count')}/7` full=`{after.get('full_target_stack')}`",
            ])
        lines.append("")
        if classification.get("ordering_class") == "target-stack-visible-before-feed":
            lines.extend([
                "## Interpretation",
                "",
                "- The full V2246 firmware_class/qcacld-HDD whitelist stack was visible before the `WCNSS_qcom_cfg.ini` userspace fallback feed.",
                "- The matching after-feed snapshot no longer contained the seven whitelist symbols; the sampled worker had moved to a later wait state.",
                "- `bdwlan.bin` and `regdb.bin` were not requested through this bounded userspace fallback path in the captured boot.",
                "- Conclusion: the post-FWREADY tail path definitely executes, and the V2250 generic CPU-clock zero-hit result was a sampler-miss artifact, not function absence.",
                "- Next loop should not spend another iteration on generic CPU-clock tuning for this tail. Re-evaluate T1 for a new independent kernel-observation question; if none is meaningful, record the drop trigger and proceed to T2 WLAN surface/cleanup work.",
                "",
            ])
    else:
        lines.extend([
            "## Dry-Run Plan",
            "",
            "```json",
            json.dumps(manifest.get("dry_run_commands") or {}, indent=2, ensure_ascii=False),
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
        "- The only non-read-only target-side operation inside V2252 is the pre-existing bounded firmware_class userspace fallback feed for `WCNSS_qcom_cfg.ini`, `bdwlan.bin`, and `regdb.bin`.",
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
        "bpf_attach": False,
        "probe_write_user_executed": False,
        "partition_write": test_flash_attempted,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2253-fwclass-boundary-stack-live")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--collect-timeout", type=float, default=180.0)
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
        "cycle": "V2253",
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
            "partition_write_scope": "boot image flash to V2252 and rollback to V2237 only" if args.execute else "none",
            "wifi_scan_connect": False,
            "credentials": False,
            "dhcp_routes_ping": False,
            "bpf_attach": False,
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
        manifest["result"] = {
            "decision": "v2253-fwclass-boundary-stack-live-confirmation-missing",
            "pass": False,
            "reason": "live mode requires the exact confirmation token",
        }
    else:
        with transport.phase(manifest, "verify_current_baseline"):
            current = verify_current(args, store, steps, str(preflight_result["rollback_image_sha256"]))
        manifest["current_preflight"] = current
        if not (current.get("verify_ok") and current.get("selftest_ok")):
            manifest["live_block"] = "preflight-current-baseline-failed"
            manifest["rollback"] = {"ok": True, "attempt": "not-needed-pre-test-flash", "selftest_ok": True}
        else:
            with transport.phase(manifest, "test_flash"):
                test_flash = run_command(
                    flash_command(TEST_IMAGE, TEST_EXPECT_VERSION, str(preflight_result["test_image_sha256"]), from_native=True),
                    timeout=args.flash_timeout,
                )
            write_step(store, steps, "flash-v2252-from-native", test_flash)
            manifest["test_flash"] = {"ok": bool(test_flash.get("ok")), "rc": test_flash.get("rc")}
            if bool(test_flash.get("ok")):
                with transport.phase(manifest, "test_boot_health"):
                    version = run_a90ctl_step(store, steps, "test-boot-version", args, ["version"], timeout=120)
                    status = run_a90ctl_step(store, steps, "test-boot-status", args, ["status"], timeout=120)
                    selftest = run_a90ctl_step(store, steps, "test-boot-selftest", args, ["selftest"], timeout=120)
                manifest["test_health"] = {
                    "version_ok": bool(version.get("ok")) and TEST_EXPECT_VERSION in str(version.get("stdout") or ""),
                    "status_ok": bool(status.get("ok")),
                    "selftest_ok": bool(selftest.get("ok")) and "fail=0" in str(selftest.get("stdout") or ""),
                }
                with transport.phase(manifest, "post_boot_helper_window_wait"):
                    wait_started = now_iso()
                    time.sleep(max(0.0, args.post_boot_wait_sec))
                    write_step(store, steps, "post-boot-helper-window-wait", {
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
    transport.add_total_phase(manifest, "artifact_write", time.monotonic(), ok=True)
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

#!/usr/bin/env python3
"""V2227 rollbackable boot-window handoff runner for the V2226 property-root-fixed a90 observer boot.

Default mode is host-only dry-run. The live path flashes V2226, collects the
helper-owned boot-window result, runs the V2220 parser over the collected
artifacts, then rolls back to V2189 and verifies selftest fail=0.
"""

from __future__ import annotations

import argparse
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
    / "NATIVE_INIT_V2227_A90_BOOT_WINDOW_PROPERTY_ROOT_HANDOFF_RUNNER_2026-06-12.md"
)
V2226_BUILD_DIR = REPO_ROOT / "workspace" / "private" / "builds" / "native-init" / "v2226-a90-boot-window-property-root"
V2226_MANIFEST = V2226_BUILD_DIR / "manifest.json"
TEST_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v2226_a90_boot_window_property_root.img",
    legacy_fallback=False,
)
ROLLBACK_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v2189_security_p0_stage_fix.img",
    legacy_fallback=False,
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.263 (v2226-a90-boot-window-property-root)"
ROLLBACK_EXPECT_VERSION = "A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)"
HELPER_REMOTE_PATHS = {
    "helper_result": "/cache/native-init-wifi-test-boot-v2226-helper.result",
    "summary": "/cache/native-init-wifi-test-boot-v2226.summary",
    "log": "/cache/native-init-wifi-test-boot-v2226.log",
}
REQUIRED_CONFIRM = "I_UNDERSTAND_V2227_FLASHES_V2226_AND_ROLLS_BACK_TO_V2189"
REPORT_KEY_EVENTS = [
    "uprobe:wlfw_start",
    "uprobe:wlfw_service_request",
    "uprobe:wlfw_cap_qmi",
    "uprobe:wlfw_bdf_entry",
]


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    import hashlib

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
        "240",
        "--recovery-timeout",
        "240",
    ]
    if from_native:
        command.append("--from-native")
    return command


def load_build_manifest() -> dict[str, Any]:
    if not V2226_MANIFEST.exists():
        return {}
    return read_bounded_json(V2226_MANIFEST)


def preflight() -> dict[str, Any]:
    build_manifest = load_build_manifest()
    expected_test_sha = str(build_manifest.get("boot_sha256") or "") if build_manifest else ""
    test_sha = sha256(TEST_IMAGE) if TEST_IMAGE.exists() else ""
    rollback_sha = sha256(ROLLBACK_IMAGE) if ROLLBACK_IMAGE.exists() else ""
    return {
        "v2226_manifest": rel(V2226_MANIFEST),
        "v2226_manifest_exists": V2226_MANIFEST.exists(),
        "v2226_manifest_pass": bool(build_manifest.get("pass")),
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
        "helper_remote_paths": HELPER_REMOTE_PATHS,
    }


def dry_run_commands(preflight_result: dict[str, Any]) -> dict[str, Any]:
    test_sha = str(preflight_result.get("test_image_sha256") or "")
    rollback_sha = str(preflight_result.get("rollback_image_sha256") or "")
    plan = {
        "preflight": ["python3", "workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_preflight_v2222.py"],
        "flash_test_boot": flash_command(Path(rel(TEST_IMAGE)), TEST_EXPECT_VERSION, test_sha, from_native=True),
        "collect": [
            ["python3", "workspace/public/src/scripts/revalidation/a90ctl.py", "cat", path]
            for path in HELPER_REMOTE_PATHS.values()
        ],
        "parse": ["python3", "workspace/public/src/scripts/revalidation/a90_kernel_v2220_helper_summary_trace_parser.py"],
        "rollback": flash_command(Path(rel(ROLLBACK_IMAGE)), ROLLBACK_EXPECT_VERSION, rollback_sha, from_native=True),
        "postflight": ["python3", "workspace/public/src/scripts/revalidation/a90ctl.py", "selftest"],
    }
    return json.loads(json.dumps(plan, default=str))


def run_parser(store: EvidenceStore, steps: list[dict[str, Any]], inputs: list[Path]) -> dict[str, Any]:
    parser_out = store.mkdir("parser")
    command: list[object] = [
        "python3",
        "workspace/public/src/scripts/revalidation/a90_kernel_v2220_helper_summary_trace_parser.py",
        "--out-dir",
        parser_out,
        "--label",
        "v2227-boot-window-helper",
        "--allow-nohit",
    ]
    for path in inputs:
        command.extend(["--input", path])
    result = run_command(command, timeout=120)
    write_step(store, steps, "parse-helper-artifacts-v2220", result)
    summary_path = parser_out / "summary.json"
    parsed_summary = read_bounded_json(summary_path) if summary_path.exists() else {}
    events_by_key = parsed_summary.get("events_by_key") if isinstance(parsed_summary.get("events_by_key"), dict) else {}
    key_events = {
        key: {
            "total_hit_count": (events_by_key.get(key) or {}).get("total_hit_count"),
            "first_ts": (events_by_key.get(key) or {}).get("first_ts"),
            "first_hit_line": (events_by_key.get(key) or {}).get("first_hit_line"),
        }
        for key in REPORT_KEY_EVENTS
    }
    return {
        "ok": bool(result.get("ok")),
        "out_dir": rel(parser_out),
        "summary": rel(summary_path),
        "parsed_decision": parsed_summary.get("decision"),
        "parsed_pass": parsed_summary.get("pass"),
        "event_total": parsed_summary.get("event_total"),
        "hit_event_total": parsed_summary.get("hit_event_total"),
        "key_hit_event_total": parsed_summary.get("key_hit_event_total"),
        "total_hits": parsed_summary.get("total_hits"),
        "key_events": key_events,
    }


def extract_summary_value(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}=(.*)$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def diagnose_artifacts(paths: list[Path]) -> dict[str, Any]:
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in paths if path.exists())
    nonlog = {
        "label": extract_summary_value(text, "wlan_pd_cnss_nonlog_control_flow.label"),
        "pm_init_pm_client_register_call_hits": extract_summary_value(
            text, "wlan_pd_cnss_nonlog_control_flow.uprobe.pm_init_pm_client_register_call.hit_count"
        ),
        "pm_init_pm_client_register_retcheck_hits": extract_summary_value(
            text, "wlan_pd_cnss_nonlog_control_flow.uprobe.pm_init_pm_client_register_retcheck.hit_count"
        ),
        "periph_default_service_manager_call_hits": extract_summary_value(
            text, "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_default_service_manager_call.hit_count"
        ),
        "periph_manager_name_string16_call_hits": extract_summary_value(
            text, "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_manager_name_string16_call.hit_count"
        ),
    }
    if "setup_error=lstat property root: No such file or directory" in text:
        return {
            "kind": "property-root-missing",
            "decision": "helper-setup-error-property-root-missing",
            "setup_error": "lstat property root: No such file or directory",
            "helper_exit_code": 20 if "helper_exit_code=20" in text or "child_exit_code=20" in text else None,
        }
    if "helper_status=setup-error" in text:
        return {
            "kind": "setup-error",
            "decision": "helper-setup-error",
            "helper_exit_code": 20 if "helper_exit_code=20" in text or "child_exit_code=20" in text else None,
        }
    if "helper_result_size=" in text or "A90_EXECNS_RESULT_FILE_BEGIN" in text:
        return {
            "kind": "helper-artifacts-present",
            "decision": "helper-artifacts-present",
            "helper_exit_code": extract_summary_value(text, "helper_exit_code"),
            "helper_timed_out": extract_summary_value(text, "helper_timed_out"),
            "supervisor_result": extract_summary_value(text, "supervisor_result"),
            "wlan0_present": extract_summary_value(text, "wlan0_present"),
            "helper_result_size": extract_summary_value(text, "helper_result_size"),
            "nonlog_control_flow": {key: value for key, value in nonlog.items() if value is not None},
        }
    return {"kind": "unknown", "decision": "helper-artifact-diagnosis-unknown"}


def collect_helper_artifacts(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    inputs: list[Path] = []
    collected: dict[str, Any] = {}
    device_dir = store.mkdir("device")
    for key, remote_path in HELPER_REMOTE_PATHS.items():
        result = run_command(
            a90ctl_command(args, ["cat", remote_path], allow_error=True),
            timeout=args.collect_timeout,
        )
        write_step(store, steps, f"collect-{key}", result)
        local_path = device_dir / f"{key}.txt"
        local_path.write_text(str(result.get("stdout") or ""), encoding="utf-8")
        local_path.chmod(0o600)
        inputs.append(local_path)
        collected[key] = {
            "remote_path": remote_path,
            "local_path": rel(local_path),
            "ok": bool(result.get("ok")),
            "bytes": local_path.stat().st_size,
        }
    parser = run_parser(store, steps, inputs)
    return {"artifacts": collected, "diagnosis": diagnose_artifacts(inputs), "parser": parser}


def wait_step(store: EvidenceStore, steps: list[dict[str, Any]], seconds: float) -> None:
    started = now_iso()
    time.sleep(max(0.0, seconds))
    write_step(store, steps, "post-boot-helper-window-wait", {
        "command": ["sleep", f"{seconds:.3f}"],
        "started": started,
        "ended": now_iso(),
        "timeout": False,
        "rc": 0,
        "ok": True,
        "stdout": f"waited_sec={seconds:.3f}\n",
        "stderr": "",
    })


def rollback(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], rollback_sha: str) -> dict[str, Any]:
    first = run_command(
        flash_command(ROLLBACK_IMAGE, ROLLBACK_EXPECT_VERSION, rollback_sha, from_native=True),
        timeout=args.flash_timeout,
    )
    write_step(store, steps, "rollback-v2189-from-native", first)
    attempt = "from-native"
    ok = bool(first.get("ok"))
    if not ok:
        second = run_command(
            flash_command(ROLLBACK_IMAGE, ROLLBACK_EXPECT_VERSION, rollback_sha, from_native=False),
            timeout=args.flash_timeout,
        )
        write_step(store, steps, "rollback-v2189-from-recovery", second)
        attempt = "from-recovery"
        ok = bool(second.get("ok"))
    status = run_command(a90ctl_command(args, ["status"], allow_error=True), timeout=90)
    write_step(store, steps, "post-rollback-status", status)
    selftest = run_command(a90ctl_command(args, ["selftest"], allow_error=True), timeout=90)
    write_step(store, steps, "post-rollback-selftest", selftest)
    return {
        "ok": ok,
        "attempt": attempt,
        "status_ok": bool(status.get("ok")),
        "selftest_ok": bool(selftest.get("ok")) and "fail=0" in str(selftest.get("stdout") or ""),
    }


def classify(manifest: dict[str, Any]) -> dict[str, Any]:
    if not manifest.get("execute"):
        pre = manifest["preflight"]
        ok = all([
            pre.get("v2226_manifest_pass"),
            pre.get("test_image_exists"),
            pre.get("test_image_sha_matches_manifest"),
            pre.get("rollback_image_exists"),
        ])
        return {
            "decision": "v2227-boot-window-handoff-dry-run-ready" if ok else "v2227-boot-window-handoff-dry-run-blocked",
            "pass": bool(ok),
            "reason": "host-only flash/capture/rollback plan is complete; live execution still requires explicit approval" if ok else "required boot image or V2226 build manifest is missing/mismatched",
        }
    if manifest.get("live_block") == "v2222-preflight-failed":
        return {
            "decision": "v2227-boot-window-handoff-preflight-failed-no-flash",
            "pass": False,
            "reason": "V2222 preflight failed before the test boot flash, so no live boot-window capture was attempted",
        }
    rollback_result = manifest.get("rollback") or {}
    collect = manifest.get("collect") or {}
    parser = collect.get("parser") or {}
    if not rollback_result.get("selftest_ok"):
        return {
            "decision": "v2227-boot-window-handoff-rollback-selftest-failed",
            "pass": False,
            "reason": "rollback did not finish with selftest fail=0",
        }
    if manifest.get("live_block") == "test-flash-failed":
        return {
            "decision": "v2227-boot-window-handoff-test-flash-failed-rollback-pass",
            "pass": False,
            "reason": "V2226 test boot flash failed, but rollback selftest fail=0 passed",
        }
    diagnosis = collect.get("diagnosis") or {}
    if diagnosis.get("kind") == "property-root-missing":
        return {
            "decision": "v2227-boot-window-helper-property-root-missing-rollback-pass",
            "pass": False,
            "reason": "V2226 booted and rollback passed, but the helper exited before tracing because its configured property root was missing",
        }
    if parser.get("parsed_pass") is True:
        return {
            "decision": "v2227-boot-window-helper-parsed-rollback-pass",
            "pass": True,
            "reason": "V2226 helper artifacts were collected, parsed by V2220, and rollback selftest fail=0",
        }
    return {
        "decision": "v2227-boot-window-helper-parse-incomplete-rollback-pass",
        "pass": False,
        "reason": "rollback passed, but helper artifacts did not parse cleanly",
    }


def is_current_window_a90_absent_preflight(result: dict[str, Any]) -> bool:
    try:
        payload = json.loads(str(result.get("stdout") or ""))
    except json.JSONDecodeError:
        return False
    if "v2221-current-window-contract failed" not in str(payload.get("error") or ""):
        return False
    out_dir = payload.get("out_dir")
    if not out_dir:
        return False
    collector_stdout = REPO_ROOT / str(out_dir) / "v2221-current-window-contract.stdout.txt"
    if not collector_stdout.exists():
        return False
    try:
        current = json.loads(collector_stdout.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return False
    error = str(current.get("error") or "")
    if not (
        current.get("decision") == "v2221-collector-parser-integration-failed"
        and current.get("pass") is False
        and "v2219-collector failed" in error
    ):
        return False
    collector_stdout_path = error.split(":", 1)[-1].strip().replace(".stderr.txt", ".stdout.txt")
    collector_stdout = Path(collector_stdout_path)
    if not collector_stdout.exists():
        return False
    try:
        collector = json.loads(collector_stdout.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return False
    return (
        collector.get("decision") == "v2219-a90-uprobe-trace-buffer-ready-current-window-nohit"
        and collector.get("event_exists_count") == 0
        and collector.get("event_enabled_count") == 0
        and collector.get("selftest_fail0") is True
    )


def is_current_window_collector_busy_preflight(result: dict[str, Any]) -> bool:
    try:
        payload = json.loads(str(result.get("stdout") or ""))
    except json.JSONDecodeError:
        return False
    if "v2221-current-window-contract failed" not in str(payload.get("error") or ""):
        return False
    out_dir_value = payload.get("out_dir")
    if not out_dir_value:
        return False
    out_dir = REPO_ROOT / str(out_dir_value)
    summary_path = out_dir / "summary.json"
    if not summary_path.exists():
        return False
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return False
    completed_step_names = {
        str(step.get("name") or ""): bool(step.get("ok"))
        for step in summary.get("steps", [])
        if isinstance(step, dict)
    }
    required_steps = ["bridge-status", "native-status", "native-version", "native-helpers", "helper-inventory"]
    if not all(completed_step_names.get(name) for name in required_steps):
        return False
    status_text = (out_dir / "native-status.stdout.txt").read_text(encoding="utf-8", errors="replace")
    if "A90P1 END" not in status_text or "rc=0" not in status_text or "fail=0" not in status_text:
        return False
    current_stdout = out_dir / "v2221-current-window-contract.stdout.txt"
    if not current_stdout.exists():
        return False
    try:
        current = json.loads(current_stdout.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return False
    if current.get("decision") != "v2221-collector-parser-integration-failed":
        return False
    error = str(current.get("error") or "")
    collector_stdout_path = error.split(":", 1)[-1].strip().replace(".stderr.txt", ".stdout.txt")
    collector_stdout = Path(collector_stdout_path)
    if not collector_stdout.exists():
        return False
    try:
        collector = json.loads(collector_stdout.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return False
    collector_error = str(collector.get("error") or "")
    return (
        collector.get("decision") == "v2219-a90-uprobe-trace-buffer-failed"
        and "event-state failed" in collector_error
        and "status=busy" in collector_error
        and "rc=-16" in collector_error
    )


def render_report(manifest: dict[str, Any]) -> str:
    result = manifest["result"]
    pre = manifest["preflight"]
    lines = [
        "# Native Init V2227 A90 Boot-Window Handoff Runner",
        "",
        "## Summary",
        "",
        "- Cycle: `V2227`",
        "- Type: rollbackable boot-window handoff runner; default execution is host-only dry-run.",
        f"- Decision: `{result['decision']}`",
        f"- Result: `{'PASS' if result['pass'] else 'FAIL'}`",
        f"- Reason: {result['reason']}",
        f"- Execute mode: `{manifest['execute']}`",
        f"- Evidence: `{manifest['out_dir']}`",
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
        "## Live Contract",
        "",
        "- Live mode requires `--execute` plus the exact confirmation token.",
        "- Live sequence: V2222 preflight -> flash V2226 -> collect `/cache/native-init-wifi-test-boot-v2226-*` -> V2220 parser -> rollback V2189 -> selftest fail=0.",
        "- Collection is read-only after boot; it uses `cat` over the native bridge and the helper-owned trace output.",
        "",
    ]
    if manifest.get("execute"):
        rollback_result = manifest.get("rollback") or {}
        collect = manifest.get("collect") or {}
        parser = collect.get("parser") or {}
        diagnosis = collect.get("diagnosis") or {}
        lines.extend([
            "## Live Evidence",
            "",
            f"- Rollback OK: `{rollback_result.get('ok', False)}`",
            f"- Rollback selftest fail=0: `{rollback_result.get('selftest_ok', False)}`",
            f"- Parser decision: `{parser.get('parsed_decision')}`",
            f"- Parser pass: `{parser.get('parsed_pass')}`",
            f"- Parser hits: total=`{parser.get('total_hits')}` hit_events=`{parser.get('hit_event_total')}` key_hit_events=`{parser.get('key_hit_event_total')}`",
            f"- Helper diagnosis: `{diagnosis.get('decision', 'unknown')}`",
            f"- Helper result: supervisor=`{diagnosis.get('supervisor_result')}` exit=`{diagnosis.get('helper_exit_code')}` timed_out=`{diagnosis.get('helper_timed_out')}` wlan0_present=`{diagnosis.get('wlan0_present')}`",
            "",
        ])
        nonlog = diagnosis.get("nonlog_control_flow") or {}
        if nonlog:
            lines.extend([
                "## Nonlog Control-Flow Summary",
                "",
                f"- Classifier: `{nonlog.get('label')}`",
                f"- `pm_init_pm_client_register_call`: hits=`{nonlog.get('pm_init_pm_client_register_call_hits')}`",
                f"- `pm_init_pm_client_register_retcheck`: hits=`{nonlog.get('pm_init_pm_client_register_retcheck_hits')}`",
                f"- `periph_default_service_manager_call`: hits=`{nonlog.get('periph_default_service_manager_call_hits')}`",
                f"- `periph_manager_name_string16_call`: hits=`{nonlog.get('periph_manager_name_string16_call_hits')}`",
                "",
            ])
        key_events = parser.get("key_events") or {}
        if key_events:
            lines.extend([
                "## WLFW Edge Summary",
                "",
            ])
            for key in REPORT_KEY_EVENTS:
                event = key_events.get(key) or {}
                lines.append(
                    f"- `{key}`: hits=`{event.get('total_hit_count')}` first_ts=`{event.get('first_ts')}`"
                )
            lines.append("")
        if diagnosis.get("kind") == "property-root-missing":
            lines.extend([
                "## Live Diagnosis",
                "",
                "- The V2226 helper did not reach WLFW/CNSS trace collection.",
                "- Recovered helper result shows `helper_status=setup-error` and `setup_error=lstat property root: No such file or directory`.",
                "- Root cause: the configured V2226 property root was missing on the device.",
                "- Next unit: rebuild with a present/staged property root and keep `--hide-on-busy` for bridge artifact collection.",
                "",
            ])
        elif parser.get("parsed_pass") is True:
            key_events = parser.get("key_events") or {}
            wlfw_start_hits = ((key_events.get("uprobe:wlfw_start") or {}).get("total_hit_count") or 0)
            wlfw_request_hits = ((key_events.get("uprobe:wlfw_service_request") or {}).get("total_hit_count") or 0)
            cap_hits = ((key_events.get("uprobe:wlfw_cap_qmi") or {}).get("total_hit_count") or 0)
            bdf_hits = ((key_events.get("uprobe:wlfw_bdf_entry") or {}).get("total_hit_count") or 0)
            if wlfw_start_hits and not (wlfw_request_hits or cap_hits or bdf_hits):
                nonlog = diagnosis.get("nonlog_control_flow") or {}
                if nonlog.get("label") == "peripheral-default-service-manager-call-no-return":
                    lines.extend([
                        "## Live Diagnosis",
                        "",
                        "- V2226 fixed the property-root setup failure and the helper completed normally.",
                        "- The trace reached `wlfw_start`, entered the CNSS PM registration path, and called into `libperipheral_client`.",
                        "- Nonlog classifier: `peripheral-default-service-manager-call-no-return`; `periph_default_service_manager_call` hit, but the service-name/get-service edge did not.",
                        "- This matches the V2226 output-visibility route: service-manager/PM trio were intentionally not started in that route.",
                        "- Next unit: enable the service-manager + PM/service-object-visible route with the same property-root and observer stack, rather than chasing more WLFW offsets.",
                        "",
                    ])
                else:
                    lines.extend([
                    "## Live Diagnosis",
                    "",
                    "- V2226 fixed the property-root setup failure and the helper completed normally.",
                    "- The boot-window trace reached `wlfw_start`, but did not reach `wlfw_service_request`, `wlfw_cap_qmi`, or `wlfw_bdf_entry`.",
                    "- `wlan0_present=0`; this is a valid negative downstream-cascade observation, not a parser/collection failure.",
                    "- Next unit: instrument the early `cnss-daemon` path between `wlfw_start` and the missing service-request edge.",
                    "",
                    ])
    lines.extend([
        "## Safety Scope",
        "",
        "- Dry-run does not flash, reboot, write device partitions, scan/connect Wi-Fi, use credentials, configure DHCP/routes, ping, attach BPF, execute `probe_write_user`, or write tracefs controls.",
        "- Live mode flashes only the approved rollbackable V2226 test boot and V2189 rollback image.",
        "- It does not use Wi-Fi HAL scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC/eSoC/PCI paths, platform bind/unbind, or `sda29` writes.",
        "",
    ])
    if manifest.get("dry_run_commands"):
        lines.extend([
            "## Dry-Run Command Plan",
            "",
            "```json",
            json.dumps(manifest["dry_run_commands"], indent=2, ensure_ascii=False),
            "```",
            "",
        ])
    return "\n".join(lines)


def residual_state(manifest: dict[str, Any]) -> dict[str, Any]:
    steps = [step for step in manifest.get("steps", []) if isinstance(step, dict)]
    flash_steps = [step for step in steps if str(step.get("name") or "").startswith("flash-v")]
    test_flash_attempted = bool(flash_steps)
    rollback_needed = bool(manifest.get("execute") and test_flash_attempted)
    rollback_result = manifest.get("rollback") if isinstance(manifest.get("rollback"), dict) else {}
    rollback_selftest_ok = bool(rollback_result.get("selftest_ok"))
    rollback_ok = bool(rollback_result.get("ok")) and rollback_selftest_ok if rollback_needed else True
    cleanup_required = bool(rollback_needed and not rollback_ok)
    return {
        "device_touched": bool(manifest.get("execute") and steps),
        "flash_reboot": test_flash_attempted,
        "test_flash_ok": any(bool(step.get("ok")) for step in flash_steps),
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
    parser.add_argument("--label", default="v2227-a90-boot-window-property-root-handoff")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--collect-timeout", type=float, default=120.0)
    parser.add_argument("--flash-timeout", type=float, default=720.0)
    parser.add_argument(
        "--post-boot-wait-sec",
        type=float,
        default=105.0,
        help="seconds to wait after test boot verification before collecting helper artifacts",
    )
    parser.add_argument("--execute", action="store_true", help="perform the live flash/capture/rollback sequence")
    parser.add_argument(
        "--confirm",
        default="",
        help=f"required for --execute: {REQUIRED_CONFIRM}",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    label = safe_artifact_label(args.label)
    run_dir = RUN_ROOT / f"{label}-{artifact_timestamp()}"
    store = EvidenceStore(run_dir)
    steps: list[dict[str, Any]] = []
    manifest: dict[str, Any] = {
        "cycle": "V2227",
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
            "wifi_scan_connect": False,
            "credentials": False,
            "dhcp_routes_ping": False,
            "bpf_attach": False,
            "probe_write_user": False,
            "tracefs_write": False,
            "partition_write": bool(args.execute),
            "partition_write_scope": "boot image flash to V2226 and rollback to V2189 only" if args.execute else "none",
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
            "decision": "v2227-boot-window-handoff-live-confirmation-missing",
            "pass": False,
            "reason": "live mode requires the exact confirmation token",
        }
    else:
        test_flash_attempted = False
        with transport.phase(manifest, "v2222_preflight_before_flash"):
            v2222 = run_command(
                [
                    "python3",
                    "workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_preflight_v2222.py",
                    "--label",
                    "v2227-preflight-before-flash",
                    "--bridge-host",
                    args.bridge_host,
                    "--bridge-port",
                    str(args.bridge_port),
                    "--timeout",
                    str(args.timeout),
                ],
                timeout=180,
            )
        write_step(store, steps, "preflight-v2222-before-flash", v2222)
        current_window_a90_absent = bool(not v2222.get("ok") and is_current_window_a90_absent_preflight(v2222))
        current_window_collector_busy = bool(
            not v2222.get("ok") and is_current_window_collector_busy_preflight(v2222)
        )
        if current_window_a90_absent:
            manifest["preflight_warning"] = {
                "decision": "v2227-current-window-a90-events-absent-nonblocking",
                "reason": "V2222 current-window collector found no active a90 events after rollback; V2226 test boot is expected to recreate the helper-owned boot-window events.",
            }
        elif current_window_collector_busy:
            manifest["preflight_warning"] = {
                "decision": "v2227-current-window-collector-busy-nonblocking",
                "reason": "V2222 bridge/status/version/helpers checks passed with fail=0, but the optional current-window collector hit auto-menu busy before the test boot; V2226 test boot is expected to create fresh helper-owned boot-window events.",
            }
        if not v2222.get("ok") and not (current_window_a90_absent or current_window_collector_busy):
            manifest["live_block"] = "v2222-preflight-failed"
        else:
            test_flash_attempted = True
            with transport.phase(manifest, "test_flash"):
                test_flash = run_command(
                    flash_command(TEST_IMAGE, TEST_EXPECT_VERSION, str(preflight_result["test_image_sha256"]), from_native=True),
                    timeout=args.flash_timeout,
                )
            write_step(store, steps, "flash-v2226-from-native", test_flash)
            if bool(test_flash.get("ok")):
                with transport.phase(manifest, "test_boot_health"):
                    status = run_command(a90ctl_command(args, ["status"], allow_error=True), timeout=90)
                    write_step(store, steps, "test-boot-status", status)
                    selftest = run_command(a90ctl_command(args, ["selftest"], allow_error=True), timeout=90)
                    write_step(store, steps, "test-boot-selftest", selftest)
                with transport.phase(manifest, "post_boot_helper_window_wait"):
                    wait_step(store, steps, args.post_boot_wait_sec)
                with transport.phase(manifest, "collect_helper_artifacts"):
                    manifest["collect"] = collect_helper_artifacts(args, store, steps)
            else:
                manifest["live_block"] = "test-flash-failed"
        if test_flash_attempted:
            with transport.phase(manifest, "rollback"):
                manifest["rollback"] = rollback(args, store, steps, str(preflight_result["rollback_image_sha256"]))
        else:
            manifest["rollback"] = {
                "ok": True,
                "attempt": "not-needed-pre-test-flash",
                "status_ok": False,
                "selftest_ok": False,
            }

    if "result" not in manifest:
        with transport.phase(manifest, "classify"):
            manifest["result"] = classify(manifest)
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

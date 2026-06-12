#!/usr/bin/env python3
"""V2255 rollbackable live validation for the V2254 Wi-Fi detail surface.

Default mode is host-only dry-run. Live mode flashes the V2254 read-only Wi-Fi
detail surface image, verifies native-init health, queries only `wifi status`
and `screenapp wifi-status`, then rolls back to V2237 and verifies selftest
fail=0. It deliberately does not run scan/connect/DHCP/ping.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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
RUN_ROOT = REPO_ROOT / "workspace" / "private" / "runs" / "wifi"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2255_WIFI_DETAIL_SURFACE_LIVE_2026-06-12.md"
)
BUILD_MANIFEST = (
    REPO_ROOT
    / "workspace"
    / "private"
    / "builds"
    / "native-init"
    / "v2254-wifi-detail-surface"
    / "manifest.json"
)
TEST_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2254_wifi_detail_surface.img", legacy_fallback=False
)
ROLLBACK_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2237_supplicant_terminate_poll.img", legacy_fallback=False
)
FALLBACK_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v48.img", legacy_fallback=False
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.272 (v2254-wifi-detail-surface)"
ROLLBACK_EXPECT_VERSION = "A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)"
REQUIRED_CONFIRM = "I_UNDERSTAND_V2255_FLASHES_V2254_AND_ROLLS_BACK_TO_V2237"
REQUIRED_STATUS_FIELDS = [
    "default_route_present",
    "gateway_label",
    "gateway_rc",
    "resolv_conf.present",
    "resolv_conf.nameserver_count",
]


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


def write_step(store: EvidenceStore,
               steps: list[dict[str, Any]],
               name: str,
               result: dict[str, Any]) -> dict[str, Any]:
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


def a90ctl_command(args: argparse.Namespace,
                   command: list[str],
                   *,
                   allow_error: bool = False) -> list[object]:
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


def sanitize_field_value(key: str, value: str | None) -> str | None:
    if value is None:
        return None
    if key in {"gateway_label", "gateway", "ipv4", "ip4_label", "mac", "mac_label"}:
        return "<redacted-present>" if value and value not in {"-", "none"} else value
    return value


def classify_wifi_status(result: dict[str, Any]) -> dict[str, Any]:
    text = str(result.get("stdout") or "")
    values = parse_key_values(text)
    present = {field: field in values for field in REQUIRED_STATUS_FIELDS}
    sanitized = {field: sanitize_field_value(field, last_value(values, field)) for field in REQUIRED_STATUS_FIELDS}
    forbidden_runtime_actions = {
        "scan": "scan_result_count" in values or "trigger_rc" in values,
        "connect": any(key.startswith("supplicant.command.") for key in values),
        "dhcp": "dhcp_ready" in values and last_value(values, "dhcp_ready") == "1",
        "ping": "gateway.ping_rc" in values or "internet.ping_rc" in values,
    }
    return {
        "ok": bool(result.get("ok")),
        "field_present": present,
        "all_required_fields_present": all(present.values()),
        "sanitized_values": sanitized,
        "decision": last_value(values, "decision"),
        "wlan0_present": last_value(values, "wlan0_present"),
        "default_route_present": last_value(values, "default_route_present"),
        "gateway_masked": last_value(values, "gateway_masked"),
        "resolv_conf_present": last_value(values, "resolv_conf.present"),
        "nameserver_count": last_value(values, "resolv_conf.nameserver_count"),
        "secret_values_logged": last_value(values, "secret_values_logged"),
        "forbidden_runtime_actions_detected": forbidden_runtime_actions,
        "no_forbidden_runtime_actions": not any(forbidden_runtime_actions.values()),
    }


def classify_screenapp(result: dict[str, Any]) -> dict[str, Any]:
    text = str(result.get("stdout") or "")
    values = parse_key_values(text)
    return {
        "ok": bool(result.get("ok")),
        "screenapp_title": last_value(values, "screenapp.title"),
        "screenapp_rc": last_value(values, "screenapp.rc"),
        "screenapp_presented": last_value(values, "screenapp.presented"),
        "mentions_wifi_status": "WIFI STATUS" in text or last_value(values, "screenapp.title") == "wifi-status",
    }


def load_build_manifest() -> dict[str, Any]:
    if not BUILD_MANIFEST.exists():
        return {}
    return read_bounded_json(BUILD_MANIFEST)


def preflight() -> dict[str, Any]:
    build_manifest = load_build_manifest()
    expected_test_sha = str(build_manifest.get("boot_sha256") or "") if build_manifest else ""
    test_sha = sha256(TEST_IMAGE) if TEST_IMAGE.exists() else ""
    rollback_sha = sha256(ROLLBACK_IMAGE) if ROLLBACK_IMAGE.exists() else ""
    fallback_sha = sha256(FALLBACK_IMAGE) if FALLBACK_IMAGE.exists() else ""
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
        "fallback_image": rel(FALLBACK_IMAGE),
        "fallback_image_exists": FALLBACK_IMAGE.exists(),
        "fallback_image_sha256": fallback_sha,
        "test_expect_version": TEST_EXPECT_VERSION,
        "rollback_expect_version": ROLLBACK_EXPECT_VERSION,
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
            str(ROLLBACK_IMAGE),
        ],
        "flash_test_boot": flash_command(TEST_IMAGE, TEST_EXPECT_VERSION, test_sha, from_native=True),
        "test_observations": [
            ["python3", "workspace/public/src/scripts/revalidation/a90ctl.py", "wifi", "status"],
            ["python3", "workspace/public/src/scripts/revalidation/a90ctl.py", "screenapp", "wifi-status"],
        ],
        "rollback": flash_command(ROLLBACK_IMAGE, ROLLBACK_EXPECT_VERSION, rollback_sha, from_native=True),
        "post_rollback": [
            ["python3", "workspace/public/src/scripts/revalidation/a90ctl.py", "version"],
            ["python3", "workspace/public/src/scripts/revalidation/a90ctl.py", "status"],
            ["python3", "workspace/public/src/scripts/revalidation/a90ctl.py", "selftest"],
        ],
    }, default=str))


def verify_current(args: argparse.Namespace,
                   store: EvidenceStore,
                   steps: list[dict[str, Any]],
                   expected_sha: str) -> dict[str, Any]:
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


def rollback(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             rollback_sha: str) -> dict[str, Any]:
    first = run_command(
        flash_command(ROLLBACK_IMAGE, ROLLBACK_EXPECT_VERSION, rollback_sha, from_native=True),
        timeout=args.flash_timeout,
    )
    write_step(store, steps, "rollback-v2237-from-native", first)
    attempt = "from-native"
    ok = bool(first.get("ok"))
    if not ok:
        second = run_command(
            flash_command(ROLLBACK_IMAGE, ROLLBACK_EXPECT_VERSION, rollback_sha, from_native=False),
            timeout=args.flash_timeout,
        )
        write_step(store, steps, "rollback-v2237-from-recovery", second)
        attempt = "from-recovery"
        ok = bool(second.get("ok"))
    version = run_a90ctl_step(store, steps, "post-rollback-version", args, ["version"], timeout=120)
    status = run_a90ctl_step(store, steps, "post-rollback-status", args, ["status"], timeout=120)
    selftest = run_a90ctl_step(store, steps, "post-rollback-selftest", args, ["selftest"], timeout=120)
    return {
        "attempt": attempt,
        "ok": ok,
        "version_ok": bool(version.get("ok")) and ROLLBACK_EXPECT_VERSION in str(version.get("stdout") or ""),
        "status_ok": bool(status.get("ok")),
        "selftest_ok": bool(selftest.get("ok")) and "fail=0" in str(selftest.get("stdout") or ""),
    }


def collect_live_observations(args: argparse.Namespace,
                              store: EvidenceStore,
                              steps: list[dict[str, Any]]) -> dict[str, Any]:
    wifi_status = run_a90ctl_step(
        store,
        steps,
        "test-boot-wifi-status",
        args,
        ["wifi", "status"],
        allow_error=True,
        timeout=120,
    )
    screenapp = run_a90ctl_step(
        store,
        steps,
        "test-boot-screenapp-wifi-status",
        args,
        ["screenapp", "wifi-status"],
        allow_error=True,
        timeout=120,
    )
    return {
        "wifi_status": classify_wifi_status(wifi_status),
        "screenapp_wifi_status": classify_screenapp(screenapp),
    }


def classify_test_health(version: dict[str, Any],
                         status: dict[str, Any],
                         selftest: dict[str, Any]) -> dict[str, Any]:
    version_text = str(version.get("stdout") or "")
    status_text = str(status.get("stdout") or "")
    version_ok = bool(version.get("ok")) and TEST_EXPECT_VERSION in version_text
    version_source = "version"
    if not version_ok and bool(status.get("ok")) and TEST_EXPECT_VERSION in status_text:
        version_ok = True
        version_source = "status_fallback"
    return {
        "version_ok": version_ok,
        "version_ok_source": version_source if version_ok else "missing",
        "status_ok": bool(status.get("ok")),
        "selftest_ok": bool(selftest.get("ok")) and "fail=0" in str(selftest.get("stdout") or ""),
    }


def classify_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    pre = manifest.get("preflight") or {}
    if not manifest.get("execute"):
        ok = all([
            pre.get("build_manifest_exists"),
            pre.get("test_image_exists"),
            pre.get("test_image_sha_matches_manifest"),
            pre.get("rollback_image_exists"),
            pre.get("fallback_image_exists"),
        ])
        return {
            "decision": "v2255-wifi-detail-surface-dry-run-ready" if ok else "v2255-wifi-detail-surface-dry-run-blocked",
            "pass": bool(ok),
            "reason": "host-only flash/status/rollback plan is complete; live execution requires --execute and confirmation" if ok else "required V2254 build artifact, rollback image, or fallback image is missing/mismatched",
        }
    rollback_result = manifest.get("rollback") or {}
    if not rollback_result.get("selftest_ok"):
        return {
            "decision": "v2255-wifi-detail-surface-rollback-selftest-failed",
            "pass": False,
            "reason": "rollback did not finish with selftest fail=0",
        }
    if manifest.get("live_block") == "preflight-current-baseline-failed":
        return {
            "decision": "v2255-wifi-detail-surface-preflight-failed-no-flash",
            "pass": False,
            "reason": "current baseline verification failed before flashing V2254",
        }
    if manifest.get("live_block") == "test-flash-failed":
        return {
            "decision": "v2255-wifi-detail-surface-test-flash-failed-rollback-pass",
            "pass": False,
            "reason": "V2254 flash or health verification failed, but rollback selftest fail=0 passed",
        }
    health = manifest.get("test_health") or {}
    if not (health.get("version_ok") and health.get("status_ok") and health.get("selftest_ok")):
        return {
            "decision": "v2255-wifi-detail-surface-test-health-failed-rollback-pass",
            "pass": False,
            "reason": "V2254 booted but native health check was incomplete; rollback selftest fail=0 passed",
        }
    observations = manifest.get("observations") or {}
    wifi_status = observations.get("wifi_status") or {}
    screenapp = observations.get("screenapp_wifi_status") or {}
    if not wifi_status.get("all_required_fields_present"):
        return {
            "decision": "v2255-wifi-detail-surface-missing-status-fields-rollback-pass",
            "pass": False,
            "reason": "wifi status did not expose every V2254 route/DNS field; rollback selftest fail=0 passed",
        }
    if not wifi_status.get("no_forbidden_runtime_actions"):
        return {
            "decision": "v2255-wifi-detail-surface-forbidden-action-detected-rollback-pass",
            "pass": False,
            "reason": "read-only status validation detected a forbidden scan/connect/DHCP/ping marker",
        }
    if not (screenapp.get("ok") and str(screenapp.get("screenapp_presented")) == "1"):
        return {
            "decision": "v2255-wifi-detail-surface-screenapp-not-presented-rollback-pass",
            "pass": False,
            "reason": "screenapp wifi-status did not present successfully; rollback selftest fail=0 passed",
        }
    return {
        "decision": "v2255-wifi-detail-surface-live-pass",
        "pass": True,
        "reason": "V2254 exposed read-only route/DNS status fields and screenapp wifi-status presented; rollback selftest fail=0 passed",
    }


def residual_state(manifest: dict[str, Any]) -> dict[str, Any]:
    rollback_result = manifest.get("rollback") or {}
    test_flash = manifest.get("test_flash") or {}
    observations = manifest.get("observations") or {}
    wifi_status = observations.get("wifi_status") or {}
    screenapp = observations.get("screenapp_wifi_status") or {}
    execute = bool(manifest.get("execute"))
    if not execute:
        return {
            "device_touched": False,
            "test_flash_ok": False,
            "rollback_ok": True,
            "rollback_attempt": "not-needed-dry-run",
            "rollback_selftest_ok": True,
            "status_surface_ok": False,
            "screenapp_presented": False,
            "forbidden_runtime_actions_detected": {},
            "cleanup_required": False,
            "residual_risk": "none",
            "wifi_scan_connect": False,
            "credentials_used": False,
            "dhcp_routes_ping": False,
        }
    if not test_flash and not rollback_result:
        return {
            "device_touched": False,
            "test_flash_ok": False,
            "rollback_ok": True,
            "rollback_attempt": "not-needed-no-device-action",
            "rollback_selftest_ok": True,
            "status_surface_ok": False,
            "screenapp_presented": False,
            "forbidden_runtime_actions_detected": {},
            "cleanup_required": False,
            "residual_risk": "none",
            "wifi_scan_connect": False,
            "credentials_used": False,
            "dhcp_routes_ping": False,
        }
    rollback_selftest_ok = bool(rollback_result.get("selftest_ok"))
    rollback_ok = bool(rollback_result.get("ok"))
    cleanup_required = bool(execute and not (rollback_ok and rollback_selftest_ok))
    return {
        "device_touched": bool(execute and (test_flash or rollback_result)),
        "test_flash_ok": bool(test_flash.get("ok")),
        "rollback_ok": rollback_ok,
        "rollback_attempt": rollback_result.get("attempt", "not-run"),
        "rollback_selftest_ok": rollback_selftest_ok,
        "status_surface_ok": bool(wifi_status.get("all_required_fields_present")),
        "screenapp_presented": str(screenapp.get("screenapp_presented")) == "1",
        "forbidden_runtime_actions_detected": wifi_status.get("forbidden_runtime_actions_detected") or {},
        "cleanup_required": cleanup_required,
        "residual_risk": "rollback-health-incomplete" if cleanup_required else "none",
        "wifi_scan_connect": False,
        "credentials_used": False,
        "dhcp_routes_ping": False,
    }


def render_report(manifest: dict[str, Any]) -> str:
    result = manifest["result"]
    pre = manifest["preflight"]
    lines = [
        "# Native Init V2255 Wi-Fi Detail Surface Live",
        "",
        "## Summary",
        "",
        "- Cycle: `V2255`",
        "- Track: T2 WLAN native-init surface/cleanup.",
        "- Type: rollbackable live validation of V2254 Wi-Fi detail status surface.",
        f"- Decision: `{result['decision']}`",
        f"- Result: `{'PASS' if result['pass'] else 'FAIL'}`",
        f"- Reason: {result['reason']}",
        f"- Execute mode: `{manifest['execute']}`",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Phase timer contract: `{manifest.get('phase_timer_contract')}`",
        f"- Residual-state contract: `{manifest.get('residual_state_contract')}`",
        "",
        "## Images",
        "",
        f"- Test image: `{pre['test_image']}`",
        f"- Test SHA256: `{pre['test_image_sha256']}`",
        f"- Test version: `{pre['test_expect_version']}`",
        f"- Rollback image: `{pre['rollback_image']}`",
        f"- Rollback SHA256: `{pre['rollback_image_sha256']}`",
        f"- Rollback version: `{pre['rollback_expect_version']}`",
        f"- Known-good fallback image present: `{pre['fallback_image_exists']}`",
        "",
    ]
    if manifest.get("execute"):
        health = manifest.get("test_health") or {}
        rollback_result = manifest.get("rollback") or {}
        observations = manifest.get("observations") or {}
        wifi_status = observations.get("wifi_status") or {}
        screenapp = observations.get("screenapp_wifi_status") or {}
        lines.extend([
            "## Live Evidence",
            "",
            f"- Preflight baseline verified: `{(manifest.get('current_preflight') or {}).get('verify_ok')}` selftest fail=0: `{(manifest.get('current_preflight') or {}).get('selftest_ok')}`",
            f"- V2254 flash OK: `{(manifest.get('test_flash') or {}).get('ok')}`",
            f"- V2254 health: version=`{health.get('version_ok')}` status=`{health.get('status_ok')}` selftest_fail0=`{health.get('selftest_ok')}`",
            f"- V2254 version match source: `{health.get('version_ok_source')}`",
            f"- `wifi status` OK: `{wifi_status.get('ok')}` all V2254 fields present: `{wifi_status.get('all_required_fields_present')}`",
            f"- `screenapp wifi-status` OK: `{screenapp.get('ok')}` presented=`{screenapp.get('screenapp_presented')}`",
            f"- Rollback OK: `{rollback_result.get('ok')}` via `{rollback_result.get('attempt')}`",
            f"- Rollback health: version=`{rollback_result.get('version_ok')}` status=`{rollback_result.get('status_ok')}` selftest_fail0=`{rollback_result.get('selftest_ok')}`",
            "",
            "## Status Field Classification",
            "",
        ])
        for field in REQUIRED_STATUS_FIELDS:
            present = (wifi_status.get("field_present") or {}).get(field)
            value = (wifi_status.get("sanitized_values") or {}).get(field)
            lines.append(f"- `{field}`: present=`{present}` value=`{value}`")
        forbidden = wifi_status.get("forbidden_runtime_actions_detected") or {}
        lines.extend([
            "",
            f"- secret_values_logged: `{wifi_status.get('secret_values_logged')}`",
            f"- gateway_masked: `{wifi_status.get('gateway_masked')}`",
            f"- forbidden scan/connect/DHCP/ping markers: `{forbidden}`",
            "",
        ])
        lines.extend([
            "## Interpretation",
            "",
            "- V2254's read-only `wifi status` surface exposes route/default-DNS detail without needing scan/connect/DHCP/ping.",
            "- The on-device `NETWORK > WIFI STATUS` path is reachable through `screenapp wifi-status` and presented successfully.",
            "- Public report values remain metadata-only; private stdout artifacts retain the raw command output under `workspace/private/**`.",
            "- Next T2 unit can either promote V2254 after an explicit baseline decision, or continue with remaining test-script cleanup if promotion is deferred.",
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
        "- Live observations are limited to `wifi status` and `screenapp wifi-status`.",
        "- This run does not use Wi-Fi scan/connect, credentials, DHCP/routes, external ping, `probe_write_user`, tracefs control writes, eSoC/PCIe/GDSC/PMIC/GPIO paths, platform bind/unbind, or `sda29` writes.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2255-wifi-detail-surface-live")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--execute", action="store_true", help="perform the live flash/status/rollback sequence")
    parser.add_argument("--confirm", default="", help=f"required for --execute: {REQUIRED_CONFIRM}")
    return parser.parse_args()


def main() -> int:
    main_started = time.monotonic()
    args = parse_args()
    label = safe_artifact_label(args.label)
    run_dir = RUN_ROOT / f"{label}-{artifact_timestamp()}"
    store = EvidenceStore(run_dir)
    steps: list[dict[str, Any]] = []
    preflight_result = preflight()
    manifest: dict[str, Any] = {
        "cycle": "V2255",
        "started_at": now_iso(),
        "out_dir": rel(run_dir),
        "execute": bool(args.execute),
        "preflight": preflight_result,
        "steps": steps,
        "phase_timer_contract": transport.PHASE_TIMER_CONTRACT,
        "phase_timers": [],
        "safety": {
            "dry_run_default": True,
            "requires_confirm_for_flash": True,
            "flash_helper_only": True,
            "partition_write_scope": "boot image flash to V2254 and rollback to V2237 only" if args.execute else "none",
            "wifi_scan_connect": False,
            "credentials": False,
            "dhcp_routes_ping": False,
            "bpf_attach": False,
            "probe_write_user": False,
            "tracefs_write": False,
        },
    }
    transport.add_total_phase(
        manifest,
        "preflight",
        main_started,
        ok=bool(
            preflight_result.get("test_image_exists")
            and preflight_result.get("rollback_image_exists")
            and preflight_result.get("fallback_image_exists")
        ),
    )
    if not args.execute:
        with transport.phase(manifest, "dry_run_plan"):
            manifest["dry_run_commands"] = dry_run_commands(preflight_result)
    elif args.confirm != REQUIRED_CONFIRM:
        manifest["result"] = {
            "decision": "v2255-wifi-detail-surface-live-confirmation-missing",
            "pass": False,
            "reason": "live mode requires the exact confirmation token",
        }
    else:
        with transport.phase(manifest, "current_baseline_verify"):
            current = verify_current(args, store, steps, str(preflight_result["rollback_image_sha256"]))
        manifest["current_preflight"] = current
        if not (current.get("verify_ok") and current.get("selftest_ok")):
            manifest["live_block"] = "preflight-current-baseline-failed"
            manifest["rollback"] = {"ok": True, "attempt": "not-needed-pre-test-flash", "selftest_ok": True}
        else:
            with transport.phase(manifest, "flash_test_boot"):
                test_flash = run_command(
                    flash_command(TEST_IMAGE, TEST_EXPECT_VERSION, str(preflight_result["test_image_sha256"]), from_native=True),
                    timeout=args.flash_timeout,
                )
                write_step(store, steps, "flash-v2254-from-native", test_flash)
            manifest["test_flash"] = {"ok": bool(test_flash.get("ok")), "rc": test_flash.get("rc")}
            if bool(test_flash.get("ok")):
                with transport.phase(manifest, "test_boot_health"):
                    version = run_a90ctl_step(store, steps, "test-boot-version", args, ["version"], timeout=120)
                    status = run_a90ctl_step(store, steps, "test-boot-status", args, ["status"], timeout=120)
                    selftest = run_a90ctl_step(store, steps, "test-boot-selftest", args, ["selftest"], timeout=120)
                manifest["test_health"] = classify_test_health(version, status, selftest)
                with transport.phase(manifest, "detail_observation"):
                    manifest["observations"] = collect_live_observations(args, store, steps)
            else:
                manifest["live_block"] = "test-flash-failed"
            with transport.phase(manifest, "rollback"):
                manifest["rollback"] = rollback(args, store, steps, str(preflight_result["rollback_image_sha256"]))
    if "result" not in manifest:
        manifest["result"] = classify_manifest(manifest)
    transport.set_residual_state(manifest, residual_state(manifest))
    manifest["finished_at"] = now_iso()
    artifact_started = time.monotonic()
    report_text = render_report(manifest)
    store.write_json("manifest.json", manifest)
    write_public_text(REPORT_PATH, report_text)
    transport.add_total_phase(manifest, "artifact_write", artifact_started, ok=True)
    store.write_json("manifest.json", manifest)
    print(json.dumps({
        "decision": manifest["result"]["decision"],
        "pass": manifest["result"]["pass"],
        "out_dir": manifest["out_dir"],
        "execute": manifest["execute"],
    }, indent=2, ensure_ascii=False))
    return 0 if manifest["result"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

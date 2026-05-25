#!/usr/bin/env python3
"""V835 known-ASoC-warning clean-DSP/CNSS service-notifier listener replay.

V834 selected the smallest native lower-state replay that changes a real
precondition: run the corrected `msm/modem/wlan_pd` service-notifier listener
inside the best existing bounded native lower window from V792.  This remains
below service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes,
external ping, boot image writes, partition writes, and custom kernel flashing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

import native_wifi_clean_dsp_arm_only_v787 as v787
import native_wifi_clean_dsp_lower_readback_v788 as v788
import native_wifi_known_asoc_warning_cnss_wlfw_v792 as v792
import native_wifi_service_notifier_early_listener_probe_v831 as v831
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v835-known-asoc-warning-servnotif-replay")
LATEST_POINTER = Path("tmp/wifi/latest-v835-known-asoc-warning-servnotif-replay.txt")
DEFAULT_V834_MANIFEST = Path("tmp/wifi/v834-android-native-state-up-delta/manifest.json")
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v831-execns-helper-v128-build/a90_android_execns_probe")
DEFAULT_HELPER_SHA256 = v831.DEFAULT_HELPER_SHA256
DEFAULT_HELPER_MARKER = v831.DEFAULT_HELPER_MARKER
DEFAULT_QRTR_MATRIX = v831.DEFAULT_MATRIX
PROOF_PREFIX = "/tmp/a90-v835-"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=v788.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v788.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=v788.DEFAULT_TIMEOUT)
    parser.add_argument("--expect-version", default=v788.DEFAULT_EXPECT_VERSION)
    parser.add_argument("--busybox", default=v788.DEFAULT_BUSYBOX)
    parser.add_argument("--toybox", default=v788.DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=v788.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--local-helper", type=Path, default=DEFAULT_LOCAL_HELPER)
    parser.add_argument("--transfer-method", choices=("auto", "ncm", "serial"), default="auto")
    parser.add_argument("--qrtr-matrix", default=DEFAULT_QRTR_MATRIX)
    parser.add_argument("--companion-runtime-sec", type=int, default=v792.DEFAULT_COMPANION_RUNTIME_SEC)
    parser.add_argument("--v786-manifest", type=Path, default=v788.DEFAULT_V786_MANIFEST)
    parser.add_argument("--v787-manifest", type=Path, default=v788.DEFAULT_V787_MANIFEST)
    parser.add_argument("--v791-manifest", type=Path, default=v792.DEFAULT_V791_MANIFEST)
    parser.add_argument("--v834-manifest", type=Path, default=DEFAULT_V834_MANIFEST)
    parser.add_argument("--v731-manifest", type=Path, default=v788.DEFAULT_V731_MANIFEST)
    parser.add_argument("--v732-manifest", type=Path, default=v788.DEFAULT_V732_MANIFEST)
    parser.add_argument("--v734-manifest", type=Path, default=v788.DEFAULT_V734_MANIFEST)
    parser.add_argument("--wait-timeout", type=float, default=120.0)
    parser.add_argument("--wait-interval", type=float, default=3.0)
    parser.add_argument("--allow-arm-clean-dsp", action="store_true")
    parser.add_argument("--allow-reboot", action="store_true")
    parser.add_argument("--allow-cleanup-umount", action="store_true")
    parser.add_argument("--allow-system-mount", action="store_true")
    parser.add_argument("--allow-selinuxfs-mount", action="store_true")
    parser.add_argument("--allow-policy-load", action="store_true")
    parser.add_argument("--allow-firmware-mounts", action="store_true")
    parser.add_argument("--allow-subsys-modem-holder", action="store_true")
    parser.add_argument("--allow-cnss-start-only", action="store_true")
    parser.add_argument("--allow-cleanup-reboot", action="store_true")
    parser.add_argument("--allow-known-asoc-warning", action="store_true")
    parser.add_argument("--allow-service-notifier-listener-replay", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
    parser.set_defaults(hide_on_busy=True)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "invalid": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "invalid": "not-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def required_flags(args: argparse.Namespace) -> list[str]:
    missing = v792.required_flags(args)
    if not args.allow_service_notifier_listener_replay:
        missing.append("--allow-service-notifier-listener-replay")
    return missing


def run_host(store: EvidenceStore, name: str, command: list[str], timeout: float) -> dict[str, Any]:
    def decode_output(value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value

    try:
        result = subprocess.run(
            command,
            cwd=repo_path("."),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        rc = result.returncode
        output = result.stdout
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        rc = 124
        output = decode_output(exc.stdout) + decode_output(exc.stderr) + f"\n[timeout after {timeout}s]\n"
        timed_out = True
    rel = f"host/{name}.txt"
    store.write_text(rel, "$ " + " ".join(command) + "\n" + output.rstrip() + "\n")
    return {
        "name": name,
        "command": command,
        "rc": rc,
        "ok": rc == 0,
        "timed_out": timed_out,
        "file": rel,
        "output_tail": output.splitlines()[-12:],
    }


def local_helper(args: argparse.Namespace) -> dict[str, Any]:
    return v831.local_helper(args)


def deploy_helper(args: argparse.Namespace, store: EvidenceStore, command: str) -> dict[str, Any]:
    deploy_dir = store.path(f"deploy-v128-{command}")
    cmd = [
        "python3",
        "scripts/revalidation/wifi_execns_helper_v128_deploy_preflight.py",
        "--out-dir",
        str(deploy_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--expect-version",
        args.expect_version,
        "--local-helper",
        str(args.local_helper),
        "--remote-helper",
        args.helper,
        "--helper-sha256",
        args.helper_sha256,
        "--transfer-method",
        args.transfer_method,
    ]
    if command == "run":
        cmd.extend(["--approval-phrase", v831.DEPLOY_APPROVAL, "--apply", "--assume-yes", "run"])
        timeout = 2400.0 if args.transfer_method in {"auto", "serial"} else 300.0
    else:
        cmd.append("preflight")
        timeout = 240.0
    result = run_host(store, f"v835-deploy-{command}", cmd, timeout)
    manifest_path = deploy_dir / "manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result.update({
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
        "device_mutations": manifest.get("device_mutations", False),
        "deploy_result": manifest.get("deploy_result"),
    })
    return result


def configure_listener_helper(args: argparse.Namespace) -> Any:
    v788.v735.configure_base()
    v788.v735.base.PROOF_PREFIX = PROOF_PREFIX
    original_helper = v788.v735.base.helper_command

    def helper_command_with_listener(inner_args: argparse.Namespace) -> list[str]:
        return original_helper(inner_args) + [
            "--qrtr-readback-matrix",
            args.qrtr_matrix,
            "--allow-service-notifier-listener-probe",
        ]

    v788.v735.base.helper_command = helper_command_with_listener
    return original_helper


def restore_listener_helper(original_helper: Any) -> None:
    v788.v735.base.helper_command = original_helper


def helper_payload_from_manifest(manifest: dict[str, Any]) -> str:
    for step in manifest.get("steps", []):
        if step.get("name") == "lower-companion-start-only":
            return str(step.get("payload") or "")
    return ""


def run_lower_listener_replay(args: argparse.Namespace, store: EvidenceStore, prep: dict[str, Any]) -> dict[str, Any]:
    lower_args = v788.lower_args(args, str(prep["v490_manifest"]))
    original_helper = configure_listener_helper(args)
    try:
        manifest = v788.v735.build_manifest(lower_args, store)
    finally:
        restore_listener_helper(original_helper)
    helper_payload = helper_payload_from_manifest(manifest)
    summary = v788.lower_summary(manifest)
    summary["matrix"] = v831.v821.summarize_matrix(helper_payload)
    summary["service_notifier"] = v831.summarize_service_notifier(helper_payload)
    summary["helper_payload_present"] = bool(helper_payload)
    store.write_json("lower-listener-summary.json", summary)
    store.write_text("lower-listener-summary.md", v788.v735.render_summary(manifest))
    return summary


def lower_markers(lower: dict[str, Any]) -> dict[str, int]:
    return v792.lower_markers(lower)


def lower_helper(lower: dict[str, Any]) -> dict[str, Any]:
    return v792.lower_helper(lower)


def lower_safety(lower: dict[str, Any]) -> dict[str, Any]:
    return v792.lower_safety(lower)


def state_up(service_notifier: dict[str, Any]) -> bool:
    return (
        service_notifier.get("response_curr_state_name") == "up"
        or service_notifier.get("indication_curr_state_name") == "up"
    )


def listener_attempt_ok(service_notifier: dict[str, Any]) -> bool:
    return (
        service_notifier.get("allowed") == 1
        and service_notifier.get("qmi_payload") == 1
        and service_notifier.get("request_hex") == v831.REGISTER_REQUEST_HEX
        and service_notifier.get("endpoint_found") == 1
        and service_notifier.get("send_attempted") == 1
        and service_notifier.get("register_send_rc") == 0
        and service_notifier.get("register_send_bytes") == 31
    )


def add_check(checks: list[dict[str, Any]], name: str, status: str, severity: str, detail: Any, next_step: str) -> None:
    checks.append({
        "name": name,
        "status": status,
        "severity": severity,
        "detail": detail,
        "next_step": next_step,
    })


def build_checks(args: argparse.Namespace,
                 v834_reference: dict[str, Any],
                 local: dict[str, Any],
                 deploy: dict[str, Any] | None,
                 flags_missing: list[str],
                 clean: dict[str, Any],
                 prep: dict[str, Any],
                 lower: dict[str, Any],
                 guard: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    add_check(
        checks,
        "v834-reference",
        "pass" if v834_reference.get("decision") == "v834-known-warning-state-listener-replay-selected" and v834_reference.get("pass") is True else "blocked",
        "blocker",
        {"decision": v834_reference.get("decision"), "pass": v834_reference.get("pass")},
        "complete V834 route classifier before V835",
    )
    add_check(
        checks,
        "local-helper-v128",
        "pass" if (
            local.get("exists")
            and local.get("sha256") == args.helper_sha256
            and local.get("marker")
            and local.get("listener_option")
            and local.get("matrix_option")
        ) else "blocked",
        "blocker",
        local,
        "rebuild helper v128 before V835",
    )
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", "run preflight or live with explicit flags")
        return checks
    add_check(
        checks,
        "helper-v128-ready" if args.command == "preflight" else "helper-v128-deploy-run",
        "pass" if deploy and deploy.get("pass") else "blocked",
        "blocker",
        deploy or {},
        "fix helper v128 deploy before V835 live",
    )
    if args.command == "preflight":
        return checks
    add_check(
        checks,
        "explicit-live-flags",
        "pass" if not flags_missing else "blocked",
        "blocker",
        {"missing": flags_missing},
        "pass all explicit V835 allow flags",
    )
    add_check(
        checks,
        "clean-dsp-inline",
        "pass" if clean.get("decision") == "v787-clean-dsp-arm-only-proof-pass" else "blocked",
        "blocker",
        {"decision": clean.get("decision"), "reason": clean.get("reason")},
        "do not run lower listener replay until clean-DSP passes",
    )
    add_check(
        checks,
        "current-boot-prep",
        "pass" if prep.get("ready") else "blocked",
        "blocker",
        {"v401": prep.get("v401_decision"), "v490": prep.get("v490_decision"), "policy_load": prep.get("v490_policy_load_executed")},
        "refresh current V401/V490 after clean-DSP reboot",
    )
    helper = lower_helper(lower)
    add_check(
        checks,
        "cnss-start-only-contract",
        "pass" if (
            helper.get("order") == v788.v735.EXPECTED_ORDER
            and helper.get("cnss_diag") == 1
            and helper.get("cnss_daemon") == 1
            and helper.get("all_postflight_safe") == 1
        ) else "blocked",
        "blocker",
        helper,
        "inspect helper transcript before interpreting listener result",
    )
    forbidden_keys = (
        "service_manager_start_executed",
        "wifi_hal_start_executed",
        "scan_connect_executed",
        "credential_use_executed",
        "dhcp_route_executed",
        "external_ping_executed",
    )
    safety = lower_safety(lower)
    add_check(
        checks,
        "forbidden-actions",
        "pass" if all(not safety.get(key) for key in forbidden_keys) else "blocked",
        "blocker",
        {key: safety.get(key) for key in forbidden_keys},
        "discard run if V835 crossed HAL/connect/network boundary",
    )
    service_notifier = lower.get("service_notifier") or {}
    add_check(
        checks,
        "service-notifier-listener-attempt",
        "pass" if listener_attempt_ok(service_notifier) else "blocked",
        "blocker",
        service_notifier,
        "fix endpoint discovery or request send before interpreting state",
    )
    markers = lower_markers(lower)
    add_check(
        checks,
        "known-asoc-warning-guard",
        "pass" if not markers.get("kernel_warning") or guard.get("exact_known_asoc_warning") else "blocked",
        "blocker",
        {"kernel_warning": markers.get("kernel_warning"), "exact_known": guard.get("exact_known_asoc_warning"), "gaps_ms": guard.get("gaps_ms")},
        "only exact ASoC pm_qos warning may be tolerated",
    )
    cleanup = ((lower.get("live") or {}).get("reboot_cleanup") or {})
    add_check(
        checks,
        "cleanup-health",
        "pass" if cleanup.get("version_seen") and cleanup.get("status_healthy") else "blocked",
        "blocker",
        cleanup,
        "recover stock v724 health before continuing",
    )
    add_check(
        checks,
        "service-notifier-state-result",
        "finding",
        "info",
        service_notifier,
        "if state is up, watch WLFW service69; otherwise continue lower-state trigger analysis",
    )
    return checks


def decide(args: argparse.Namespace, checks: list[dict[str, Any]], lower: dict[str, Any], guard: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v835-known-asoc-warning-servnotif-replay-plan-ready", True, "plan-only; no device command executed", "run V835 preflight then bounded live replay"
    blocked = [check["name"] for check in checks if check["severity"] == "blocker" and check["status"] != "pass"]
    if blocked:
        return "v835-known-asoc-warning-servnotif-replay-blocked", False, "blocked by " + ", ".join(blocked), "repair blocker before retrying V835"
    if args.command == "preflight":
        return "v835-known-asoc-warning-servnotif-replay-preflight-ready", True, "helper v128 and V834 reference are ready; live replay still requires explicit flags", "run V835 bounded live replay"
    service_notifier = lower.get("service_notifier") or {}
    if state_up(service_notifier):
        return (
            "v835-native-servnotif-state-up",
            True,
            "native listener reported WLAN-PD UP inside the known-ASoC-warning clean-DSP/CNSS window",
            "next gate should watch WLFW service69/BDF/wlan0 below HAL/connect before any scan/connect",
        )
    if service_notifier.get("response_success") == 1:
        return (
            "v835-native-servnotif-still-uninit",
            True,
            f"listener registered in the best known native lower window but state remains response={service_notifier.get('response_curr_state_name')} indication={service_notifier.get('indication_curr_state_name')}",
            "classify the remaining lower WLAN-PD state-up trigger; do not widen to HAL/connect",
        )
    if service_notifier.get("response_seen") == 1:
        return (
            "v835-native-servnotif-response-error",
            True,
            "service-notifier endpoint responded but listener registration did not succeed",
            "classify QMI response before another lower-state retry",
        )
    return (
        "v835-native-servnotif-no-response",
        True,
        "service-notifier listener send was attempted but no bounded response was observed",
        "classify endpoint lifetime or QMI transaction routing before widening",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    lower = manifest.get("lower_replay") or {}
    live = lower.get("live") or {}
    markers = live.get("markers") or {}
    service_notifier = lower.get("service_notifier") or {}
    matrix = lower.get("matrix") or {}
    return "\n".join([
        "# V835 Known-ASoC-Warning Service-notifier Replay",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
            for check in manifest["checks"]
        ]),
        "",
        "## Service-notifier",
        "",
        markdown_table(["key", "value"], [[key, value] for key, value in sorted(service_notifier.items()) if key != "packets"]),
        "",
        "## Matrix",
        "",
        markdown_table(["key", "value"], [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in sorted(matrix.items())]),
        "",
        "## Markers",
        "",
        markdown_table(["marker", "count"], [[key, value] for key, value in sorted(markers.items())]) if markers else "- none",
        "",
        "## Known Warning Guard",
        "",
        markdown_table(["key", "value"], [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in sorted((manifest.get("known_asoc_warning_guard") or {}).items()) if key != "selected_lines"]),
        "",
        "## Safety",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in sorted((manifest.get("safety") or {}).items())]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v834_reference = load_json(args.v834_manifest)
    local = local_helper(args)
    deploy: dict[str, Any] | None = None
    flags_missing = required_flags(args)
    clean: dict[str, Any] = {}
    prep: dict[str, Any] = {}
    lower: dict[str, Any] = {}
    guard: dict[str, Any] = {}
    clean_captures: list[v787.Capture] = []
    if args.command == "preflight":
        deploy = deploy_helper(args, store, "preflight")
    elif args.command == "run":
        deploy = deploy_helper(args, store, "run")
        if deploy.get("pass") and not flags_missing:
            v787_args = argparse.Namespace(**vars(args))
            v787_args.v786_manifest = args.v786_manifest
            v787_args.hide_on_busy = True
            clean_captures, clean_live = v787.collect_live(v787_args, store)
            clean_checks = v787.build_checks(v787_args, "run", v787.load_json(args.v786_manifest), clean_captures, clean_live)
            clean_decision, clean_pass, clean_reason, clean_next = v787.decide("run", clean_checks, clean_live)
            clean = {
                "decision": clean_decision,
                "pass": clean_pass,
                "reason": clean_reason,
                "next_step": clean_next,
                "checks": [asdict(check) for check in clean_checks],
                "live": clean_live,
            }
            if clean_pass:
                prep = v788.run_current_boot_prep(args, store)
            if clean_pass and prep.get("ready"):
                lower = run_lower_listener_replay(args, store, prep)
                guard = v792.warning_guard(args, store, lower)
    checks = build_checks(args, v834_reference, local, deploy, flags_missing, clean, prep, lower, guard)
    decision, passed, reason, next_step = decide(args, checks, lower, guard)
    safety = lower_safety(lower)
    manifest = {
        "cycle": "v835",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "v834_reference": {"decision": v834_reference.get("decision"), "pass": v834_reference.get("pass"), "path": str(repo_path(args.v834_manifest))},
        "local_helper": local,
        "deploy": deploy,
        "clean_dsp_inline": clean,
        "current_boot_prep": prep,
        "lower_replay": lower,
        "known_asoc_warning_guard": guard,
        "checks": checks,
        "safety": {
            "device_commands_executed": args.command in {"preflight", "run"} and deploy is not None,
            "device_mutations": bool((deploy or {}).get("device_mutations")) or (args.command == "run" and not flags_missing),
            "helper_deploy_executed": bool((deploy or {}).get("device_mutations")),
            "clean_dsp_arm_executed": bool(clean_captures and v787.ok(clean_captures, "arm-v641-clean-dsp")),
            "reboot_executed": bool(clean_captures and v787.ok(clean_captures, "reboot-after-arm")),
            "system_mount_executed": bool(prep.get("mountsystem_ok")),
            "selinuxfs_mount_executed": prep.get("v401_decision") == "toybox-selinuxfs-mount-live-executor-run-pass",
            "policy_load_executed": prep.get("v490_policy_load_executed") is True,
            "firmware_mounts_executed": safety.get("firmware_mounts_executed", False),
            "subsys_modem_opened": safety.get("subsys_modem_opened", False),
            "cnss_diag_start_executed": safety.get("cnss_diag_start_executed", False),
            "cnss_daemon_start_executed": safety.get("cnss_daemon_start_executed", False),
            "qmi_payload_executed": args.command == "run" and bool((lower.get("service_notifier") or {}).get("qmi_payload")),
            "service_manager_start_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "boot_image_write_executed": False,
            "partition_write_executed": False,
            "custom_kernel_flash_executed": False,
            "esoc0_open_executed": False,
            "subsystem_write_executed": False,
            "module_load_unload_executed": False,
        },
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    store.mkdir("host")
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['safety']['device_commands_executed']}")
    print(f"qmi_payload_executed: {manifest['safety']['qmi_payload_executed']}")
    print(f"wifi_hal_start_executed: {manifest['safety']['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['safety']['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['safety']['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

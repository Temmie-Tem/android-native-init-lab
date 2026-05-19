#!/usr/bin/env python3
"""Route V376 service-manager start-only results to the next safe action.

This is host-only. It reads V376 manifests, emits a decision and recommended
next command, and never opens the serial bridge or mutates the device.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from wifi_service_manager_start_only_approval_packet import APPROVAL_PHRASE


DEFAULT_OUT_DIR = Path("tmp/wifi/v377-service-manager-start-only-result-router")
DEFAULT_V376_GLOB = "v376-*/manifest.json"
LIVE_LABEL = "V376"
LIVE_RUNNER_SCRIPT = "scripts/revalidation/wifi_service_manager_start_only_live_runner.py"
LIVE_RUNNER_OUT_DIR = "tmp/wifi/v376-approved-run-$(date +%Y%m%d-%H%M%S)"
SUMMARY_TITLE = "V377 Service-Manager Start-Only Result Router"


@dataclass(frozen=True)
class RouteResult:
    decision: str
    pass_value: bool
    reason: str
    next_step: str
    recommended_commands: list[str]
    remaining_blockers: list[str]


@dataclass
class RouterCaseResult:
    name: str
    status: str
    decision: str
    expected_decision: str
    pass_value: bool
    expected_pass: bool
    command_count: int
    expected_command_count: int
    missing_fragments: list[str]
    detail: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v376-manifest", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("route")
    subparsers.add_parser("regression")
    return parser.parse_args()


def shell_command(argv: list[str]) -> str:
    return " ".join(shlex.quote(item) for item in argv)


def approved_live_command() -> str:
    return shell_command([
        "python3",
        LIVE_RUNNER_SCRIPT,
        "--out-dir",
        LIVE_RUNNER_OUT_DIR,
        "--apply",
        "--assume-yes",
        "--approval-phrase",
        APPROVAL_PHRASE,
        "run",
    ])


def latest_v376_manifest() -> Path | None:
    root = repo_path(Path("tmp/wifi"))
    if not root.exists():
        return None
    matches = sorted(root.glob(DEFAULT_V376_GLOB), key=lambda path: path.stat().st_mtime)
    return matches[-1] if matches else None


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"present": False, "path": ""}
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def manifest_checks(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    checks = manifest.get("checks")
    return checks if isinstance(checks, list) else []


def blockers_from_checks(manifest: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for check in manifest_checks(manifest):
        if check.get("severity") == "blocker" and check.get("status") != "pass":
            blockers.append(str(check.get("name")))
    return blockers


def observations(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    value = manifest.get("observations")
    return value if isinstance(value, list) else []


def postflight_clean(manifest: dict[str, Any]) -> bool:
    postflight = manifest.get("postflight")
    return isinstance(postflight, dict) and bool(postflight.get("clean"))


def observation_results(manifest: dict[str, Any]) -> set[str]:
    return {str(item.get("helper_result") or "missing") for item in observations(manifest)}


def all_observations_safe(manifest: dict[str, Any]) -> bool:
    items = observations(manifest)
    return bool(items) and all(
        item.get("postflight_safe") is True
        and item.get("helper_result") not in {"missing", ""}
        and item.get("exec_attempted") is True
        for item in items
    )


def route_result(v376: dict[str, Any]) -> RouteResult:
    if not v376.get("present"):
        return RouteResult(
            "service-manager-start-only-router-awaiting-v376",
            True,
            f"{LIVE_LABEL} manifest is absent",
            f"run {LIVE_LABEL} preflight, then approved live only after exact phrase",
            [approved_live_command()],
            [f"{LIVE_LABEL.lower()}-manifest"],
        )

    decision = str(v376.get("decision") or "")
    pass_value = bool(v376.get("pass"))
    daemon_started = bool(v376.get("daemon_start_executed"))
    wifi_started = bool(v376.get("wifi_bringup_executed"))

    if wifi_started:
        return RouteResult(
            "service-manager-start-only-router-scope-violation",
            False,
            "V376 manifest reports wifi_bringup_executed=true",
            "stop and inspect evidence before continuing",
            [],
            ["wifi-bringup-executed"],
        )

    if decision in {
        "service-manager-start-only-live-preflight-ready",
        "service-manager-start-only-live-approval-required",
    }:
        return RouteResult(
            "service-manager-start-only-router-awaiting-approval",
            True,
            f"{LIVE_LABEL} is ready but live start is not approved: decision={decision}",
            f"run {LIVE_LABEL} approved live only after exact V373 phrase",
            [approved_live_command()],
            ["exact-v373-service-manager-approval-phrase"],
        )

    if decision == "service-manager-start-only-live-blocked":
        blockers = blockers_from_checks(v376) or [str(v376.get("reason") or "unknown-blocker")]
        return RouteResult(
            "service-manager-start-only-router-blocked",
            False,
            f"{LIVE_LABEL} blocked: " + ", ".join(blockers),
            f"resolve {LIVE_LABEL} blockers before any daemon start",
            [],
            blockers,
        )

    if decision in {
        "service-manager-start-only-live-failed",
        "service-manager-start-only-live-review-required",
    }:
        return RouteResult(
            "service-manager-start-only-router-review-required",
            False,
            f"{LIVE_LABEL} requires review: decision={decision} pass={pass_value}",
            f"inspect {LIVE_LABEL} observations/postflight before HAL planning",
            [],
            ["manual-review"],
        )

    if decision == "service-manager-start-only-live-pass" and pass_value:
        if not daemon_started or not all_observations_safe(v376) or not postflight_clean(v376):
            return RouteResult(
                "service-manager-start-only-router-pass-postflight-review",
                False,
                f"{LIVE_LABEL} pass decision lacks daemon/postflight safety evidence",
                f"inspect {LIVE_LABEL} manifest before HAL planning",
                [],
                ["postflight-safety-evidence"],
            )
        return RouteResult(
            "service-manager-start-only-router-hal-readiness-next-ready",
            True,
            "service-manager start-only passed and postflight is clean",
            "create separate HAL start-only readiness/approval packet; still no scan/connect",
            [],
            ["hal-start-only-approval-packet"],
        )

    if decision == "service-manager-start-only-live-runtime-gap" and pass_value:
        if not daemon_started or not all_observations_safe(v376) or not postflight_clean(v376):
            return RouteResult(
                "service-manager-start-only-router-runtime-gap-review",
                False,
                "runtime-gap result lacks daemon/postflight safety evidence",
                f"inspect {LIVE_LABEL} manifest and classify runtime gap",
                [],
                ["runtime-gap-review"],
            )
        results = sorted(observation_results(v376))
        return RouteResult(
            "service-manager-start-only-router-runtime-gap",
            True,
            "service-manager start-only executed but runtime gaps remain: " + ", ".join(results),
            "classify runtime gap before any HAL start-only approval packet",
            [],
            ["runtime-gap-classification"],
        )

    return RouteResult(
        "service-manager-start-only-router-manual-review",
        False,
        f"unexpected {LIVE_LABEL} decision={decision} pass={pass_value}",
        f"inspect {LIVE_LABEL} manifest before continuing",
        [],
        ["manual-review"],
    )


def build_manifest(args: argparse.Namespace, v376: dict[str, Any]) -> dict[str, Any]:
    routed = route_result(v376)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": routed.decision,
        "pass": routed.pass_value,
        "reason": routed.reason,
        "next_step": routed.next_step,
        "host": collect_host_metadata(),
        "v376_manifest": {
            "path": v376.get("path"),
            "present": v376.get("present"),
            "decision": v376.get("decision"),
            "pass": v376.get("pass"),
            "daemon_start_executed": v376.get("daemon_start_executed"),
            "wifi_bringup_executed": v376.get("wifi_bringup_executed"),
        },
        "recommended_commands": routed.recommended_commands,
        "remaining_blockers": routed.remaining_blockers,
        "required_approval_phrase": APPROVAL_PHRASE,
        "device_commands_executed": False,
        "device_mutations": False,
        "explicitly_not_approved": [
            "Wi-Fi HAL start",
            "CNSS/diag start",
            "wificond/supplicant/hostapd start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, driver bind/unbind, firmware mutation, Android partition write",
        ],
    }


def synthetic_manifest(decision: str, pass_value: bool, **extra: Any) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "present": True,
        "path": f"synthetic-{decision}",
        "decision": decision,
        "pass": pass_value,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "checks": [],
        "observations": [],
        "postflight": None,
    }
    manifest.update(extra)
    return manifest


def blocker_check(name: str) -> dict[str, Any]:
    return {"name": name, "status": "blocked", "severity": "blocker", "detail": "", "evidence": [], "next_step": ""}


def safe_observations(results: tuple[str, ...] = ("start-only-pass", "start-only-pass")) -> list[dict[str, Any]]:
    targets = ("system-servicemanager", "system-hwservicemanager")
    return [
        {
            "target_profile": target,
            "helper_result": result,
            "helper_reason": "",
            "exec_attempted": True,
            "child_started": True,
            "postflight_safe": True,
            "reaped": True,
            "timed_out": False,
            "file": f"native/run-{target}.txt",
        }
        for target, result in zip(targets, results, strict=True)
    ]


def synthetic_cases() -> list[tuple[str, dict[str, Any], str, bool, int, tuple[str, ...]]]:
    return [
        (
            "missing",
            {"present": False, "path": ""},
            "service-manager-start-only-router-awaiting-v376",
            True,
            1,
            (f"{LIVE_LABEL.lower()}-manifest",),
        ),
        (
            "preflight-ready",
            synthetic_manifest("service-manager-start-only-live-preflight-ready", True),
            "service-manager-start-only-router-awaiting-approval",
            True,
            1,
            ("exact-v373-service-manager-approval-phrase",),
        ),
        (
            "approval-required",
            synthetic_manifest("service-manager-start-only-live-approval-required", True),
            "service-manager-start-only-router-awaiting-approval",
            True,
            1,
            ("exact-v373-service-manager-approval-phrase",),
        ),
        (
            "blocked",
            synthetic_manifest("service-manager-start-only-live-blocked", False, checks=[blocker_check("runtime-materials")]),
            "service-manager-start-only-router-blocked",
            False,
            0,
            ("runtime-materials",),
        ),
        (
            "pass-clean",
            synthetic_manifest(
                "service-manager-start-only-live-pass",
                True,
                daemon_start_executed=True,
                observations=safe_observations(),
                postflight={"clean": True},
            ),
            "service-manager-start-only-router-hal-readiness-next-ready",
            True,
            0,
            ("hal-start-only-approval-packet",),
        ),
        (
            "runtime-gap",
            synthetic_manifest(
                "service-manager-start-only-live-runtime-gap",
                True,
                daemon_start_executed=True,
                observations=safe_observations(("start-only-pass", "start-only-runtime-gap")),
                postflight={"clean": True},
            ),
            "service-manager-start-only-router-runtime-gap",
            True,
            0,
            ("runtime-gap-classification",),
        ),
        (
            "wifi-scope-violation",
            synthetic_manifest("service-manager-start-only-live-pass", True, wifi_bringup_executed=True),
            "service-manager-start-only-router-scope-violation",
            False,
            0,
            ("wifi-bringup-executed",),
        ),
        (
            "unexpected",
            synthetic_manifest("unexpected", False),
            "service-manager-start-only-router-manual-review",
            False,
            0,
            ("manual-review",),
        ),
    ]


def run_regression(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    results: list[RouterCaseResult] = []
    for name, v376, expected_decision, expected_pass, expected_command_count, expected_blockers in synthetic_cases():
        manifest = build_manifest(args, v376)
        path = store.write_json(f"cases/{name}.json", manifest)
        blockers = tuple(str(item) for item in manifest.get("remaining_blockers", []))
        missing = [item for item in expected_blockers if item not in blockers]
        commands = manifest.get("recommended_commands") if isinstance(manifest.get("recommended_commands"), list) else []
        ok = (
            manifest.get("decision") == expected_decision
            and bool(manifest.get("pass")) is expected_pass
            and len(commands) == expected_command_count
            and not missing
            and not bool(manifest.get("device_commands_executed"))
            and not bool(manifest.get("device_mutations"))
        )
        results.append(RouterCaseResult(
            name=name,
            status="pass" if ok else "blocked",
            decision=str(manifest.get("decision")),
            expected_decision=expected_decision,
            pass_value=bool(manifest.get("pass")),
            expected_pass=expected_pass,
            command_count=len(commands),
            expected_command_count=expected_command_count,
            missing_fragments=missing,
            detail=f"case_manifest={path}",
        ))
    failed = [item.name for item in results if item.status != "pass"]
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": "service-manager-start-only-router-regression-pass" if not failed else "service-manager-start-only-router-regression-failed",
        "pass": not failed,
        "reason": "all router cases passed" if not failed else "failed cases: " + ", ".join(failed),
        "next_step": f"{LIVE_LABEL} live start remains blocked by exact approval phrase",
        "host": collect_host_metadata(),
        "results": [asdict(item) for item in results],
        "device_commands_executed": False,
        "device_mutations": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    if "results" in manifest:
        rows = [
            [
                item["name"],
                item["status"],
                item["decision"],
                str(item["pass_value"]),
                str(item["command_count"]),
                item["detail"],
            ]
            for item in manifest["results"]
        ]
        body = markdown_table(["case", "status", "decision", "pass", "commands", "detail"], rows)
    else:
        body = markdown_table(
            ["field", "value"],
            [
                ["v376", json.dumps(manifest["v376_manifest"], ensure_ascii=False, sort_keys=True)],
                ["recommended_commands", "\n".join(manifest["recommended_commands"]) or "none"],
                ["remaining_blockers", ", ".join(manifest["remaining_blockers"]) or "none"],
            ],
        )
    return "\n".join([
        f"# {SUMMARY_TITLE}",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Details",
        "",
        body,
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "regression":
        manifest = run_regression(args, store)
    else:
        v376_path = args.v376_manifest if args.v376_manifest is not None else latest_v376_manifest()
        manifest = build_manifest(args, load_json(v376_path))
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

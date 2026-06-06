#!/usr/bin/env python3
"""Route V392 backchain capture results to the next safe Wi-Fi action.

This is host-only. It reads V392 executor and framechain manifests, emits a
decision and recommended next step, and never opens the bridge or mutates the
device.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v394-v392-post-live-router")
DEPLOY_APPROVAL_PHRASE = "approve v392 deploy execns helper v21 only; no daemon start and no Wi-Fi bring-up"
LIVE_APPROVAL_PHRASE = "approve v392 service-manager backchain capture only; no Wi-Fi HAL start and no Wi-Fi bring-up"
EXECUTOR_GLOB = "v39*/manifest.json"


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
    parser.add_argument("--executor-manifest", type=Path, default=None)
    parser.add_argument("--framechain-manifest", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("route")
    subparsers.add_parser("regression")
    return parser.parse_args()


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


def latest_executor_manifest() -> Path | None:
    root = repo_path(Path("tmp/wifi"))
    if not root.exists():
        return None
    matches = [
        path
        for path in root.glob(EXECUTOR_GLOB)
        if "v392" in path.parts[-2] or "v393-v392" in path.parts[-2]
    ]
    matches = sorted(matches, key=lambda path: path.stat().st_mtime)
    return matches[-1] if matches else None


def infer_framechain_manifest(executor_manifest: dict[str, Any], explicit: Path | None) -> dict[str, Any]:
    if explicit is not None:
        return load_json(explicit)
    path = str(executor_manifest.get("path") or "")
    if not path:
        return {"present": False, "path": ""}
    inferred = Path(path).parent / "framechain/manifest.json"
    return load_json(inferred)


def shell_command(argv: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in argv)


def v392_full_command() -> str:
    return shell_command([
        "python3",
        "scripts/revalidation/wifi_v392_deploy_live_executor.py",
        "--out-dir",
        "tmp/wifi/v392-approved-full-$(date +%Y%m%d-%H%M%S)",
        "--deploy-approval-phrase",
        DEPLOY_APPROVAL_PHRASE,
        "--live-approval-phrase",
        LIVE_APPROVAL_PHRASE,
        "--apply",
        "--assume-yes",
        "full",
    ])


def framechain_command(run_log: str) -> str:
    return shell_command([
        "python3",
        "scripts/revalidation/wifi_service_manager_framechain_analyze.py",
        "--out-dir",
        "tmp/wifi/v392-manual-framechain-$(date +%Y%m%d-%H%M%S)",
        "--run-log",
        run_log,
        "analyze",
    ])


def bool_field(manifest: dict[str, Any], key: str) -> bool:
    return bool(manifest.get(key))


def list_blockers(manifest: dict[str, Any]) -> list[str]:
    blockers = manifest.get("remaining_blockers")
    return [str(item) for item in blockers] if isinstance(blockers, list) else []


def frames(framechain: dict[str, Any]) -> list[dict[str, Any]]:
    value = framechain.get("frames")
    return value if isinstance(value, list) else []


def non_abort_symbols(framechain: dict[str, Any]) -> list[str]:
    symbols: list[str] = []
    for frame in frames(framechain):
        symbol = str(frame.get("symbol") or "")
        if symbol and not symbol.startswith("abort"):
            symbols.append(symbol)
    return symbols


def first_run_log(executor_manifest: dict[str, Any], framechain: dict[str, Any]) -> str:
    run_log = str(framechain.get("run_log") or "")
    if run_log:
        return run_log
    path = str(executor_manifest.get("path") or "")
    if path:
        return str(Path(path).parent / "live/native/run-system-servicemanager.txt")
    return "tmp/wifi/v392-approved-full/live/native/run-system-servicemanager.txt"


def route_result(executor_manifest: dict[str, Any], framechain: dict[str, Any]) -> RouteResult:
    if not executor_manifest.get("present"):
        return RouteResult(
            "v392-post-live-router-awaiting-executor",
            True,
            "V392 executor manifest is absent",
            "run exact-approved V392 deploy/live executor before Wi-Fi HAL planning",
            [v392_full_command()],
            ["v392-executor-manifest"],
        )

    if bool_field(executor_manifest, "wifi_bringup_executed"):
        return RouteResult(
            "v392-post-live-router-scope-violation",
            False,
            "executor manifest reports wifi_bringup_executed=true",
            "stop and inspect evidence before continuing",
            [],
            ["wifi-bringup-executed"],
        )

    decision = str(executor_manifest.get("decision") or "")
    pass_value = bool(executor_manifest.get("pass"))

    if decision in {
        "v392-deploy-live-executor-approval-required",
        "v392-deploy-live-executor-plan-ready",
    }:
        return RouteResult(
            "v392-post-live-router-awaiting-approval",
            True,
            f"V392 executor is approval-gated: decision={decision}",
            "run exact-approved V392 helper deploy and backchain capture; still no Wi-Fi HAL/start/scan/connect",
            [v392_full_command()],
            ["exact-v392-deploy-approval-phrase", "exact-v392-backchain-capture-live-approval-phrase"],
        )

    if "live-preflight-blocked" in decision or "deploy-review" in decision:
        return RouteResult(
            "v392-post-live-router-blocked",
            False,
            f"V392 executor blocked: decision={decision} pass={pass_value}",
            "inspect V392 deploy/preflight evidence before live execution",
            [],
            list_blockers(executor_manifest) or ["v392-preflight-or-deploy"],
        )

    if "service-manager-start-only-live-pass" in decision or decision.endswith("hal-readiness-next-ready"):
        return RouteResult(
            "v392-post-live-router-hal-start-only-packet-ready",
            True,
            "service-manager start-only path is clean",
            "create separate Wi-Fi HAL start-only readiness/approval packet; still no scan/connect",
            [],
            ["wifi-hal-start-only-approval-packet"],
        )

    if not framechain.get("present"):
        if "framechain" in decision:
            return RouteResult(
                "v392-post-live-router-framechain-manifest-missing",
                False,
                f"executor references framechain route but framechain manifest is absent: decision={decision}",
                "rerun host-only framechain analyzer on the V392 live log",
                [framechain_command(first_run_log(executor_manifest, framechain))],
                ["framechain-manifest"],
            )
        return RouteResult(
            "v392-post-live-router-awaiting-backchain-live",
            True,
            f"V392 live backchain evidence not present yet: decision={decision}",
            "run exact-approved V392 backchain capture before Wi-Fi HAL planning",
            [v392_full_command()],
            ["v392-backchain-live-evidence"],
        )

    frame_decision = str(framechain.get("decision") or "")
    frame_pass = bool(framechain.get("pass"))
    if frame_decision == "service-manager-framechain-symbolization-pass" and frame_pass:
        symbols = non_abort_symbols(framechain)
        if symbols:
            return RouteResult(
                "v392-post-live-router-symbolized-caller-ready",
                True,
                "framechain symbolized non-abort caller candidates: " + ", ".join(symbols[:5]),
                "plan targeted service-manager runtime repair from symbolized caller evidence; no Wi-Fi HAL yet",
                [],
                ["targeted-runtime-repair-plan"],
            )
        return RouteResult(
            "v392-post-live-router-symbolized-abort-only",
            True,
            "framechain symbolized but only abort-family frames are present",
            "inspect frame-chain depth and consider deeper stack/abort-message capture before HAL work",
            [],
            ["deeper-caller-context"],
        )

    if frame_decision == "service-manager-framechain-maprow-ready" and frame_pass:
        return RouteResult(
            "v392-post-live-router-elf-artifact-required",
            True,
            "frame return-address map rows are present but matching ELF is unavailable",
            "pull or add matching mapped ELF roots, then rerun host-only framechain analyzer",
            [framechain_command(first_run_log(executor_manifest, framechain))],
            list_blockers(framechain) or ["frame-elf-artifact"],
        )

    if frame_decision == "service-manager-framechain-no-maprow" and frame_pass:
        return RouteResult(
            "v392-post-live-router-frame-maprow-required",
            True,
            "frame-chain return addresses exist but map rows are missing",
            "extend bounded crash capture to map frame return addresses before HAL work",
            [],
            list_blockers(framechain) or ["frame-return-maprow"],
        )

    if frame_decision == "service-manager-framechain-needs-v392-live" and frame_pass:
        return RouteResult(
            "v392-post-live-router-awaiting-backchain-live",
            True,
            "framechain analyzer found no V392 frame-chain evidence",
            "run exact-approved V392 backchain capture before Wi-Fi HAL planning",
            [v392_full_command()],
            list_blockers(framechain) or ["v392-framechain-evidence"],
        )

    return RouteResult(
        "v392-post-live-router-manual-review",
        False,
        f"unexpected executor/framechain decisions: executor={decision} framechain={frame_decision} pass={frame_pass}",
        "inspect V392 executor and framechain manifests before continuing",
        [],
        ["manual-review"],
    )


def manifest_ref(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": manifest.get("path"),
        "present": manifest.get("present"),
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
    }


def build_manifest(args: argparse.Namespace, executor_manifest: dict[str, Any], framechain: dict[str, Any]) -> dict[str, Any]:
    routed = route_result(executor_manifest, framechain)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": routed.decision,
        "pass": routed.pass_value,
        "reason": routed.reason,
        "next_step": routed.next_step,
        "host": collect_host_metadata(),
        "executor_manifest": manifest_ref(executor_manifest),
        "framechain_manifest": manifest_ref(framechain),
        "recommended_commands": routed.recommended_commands,
        "remaining_blockers": routed.remaining_blockers,
        "required_approval_phrases": {
            "deploy": DEPLOY_APPROVAL_PHRASE,
            "live": LIVE_APPROVAL_PHRASE,
        },
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "explicitly_not_approved": [
            "helper deploy",
            "service-manager start",
            "Wi-Fi HAL start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, driver bind/unbind, firmware mutation, Android partition write",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        ["executor", manifest["executor_manifest"]["present"], manifest["executor_manifest"]["decision"], manifest["executor_manifest"]["path"]],
        ["framechain", manifest["framechain_manifest"]["present"], manifest["framechain_manifest"]["decision"], manifest["framechain_manifest"]["path"]],
    ]
    lines = [
        "# V394 V392 Post-Live Router",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Inputs",
        "",
        markdown_table(["name", "present", "decision", "path"], rows),
        "",
        "## Recommended Commands",
        "",
    ]
    if manifest["recommended_commands"]:
        for command in manifest["recommended_commands"]:
            lines.extend(["```bash", command, "```", ""])
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def synthetic_executor(decision: str,
                       pass_value: bool = True,
                       wifi: bool = False,
                       blockers: list[str] | None = None) -> dict[str, Any]:
    return {
        "present": True,
        "path": "/synthetic/executor/manifest.json",
        "decision": decision,
        "pass": pass_value,
        "wifi_bringup_executed": wifi,
        "remaining_blockers": blockers or [],
    }


def synthetic_framechain(decision: str,
                         pass_value: bool = True,
                         symbols: list[str] | None = None,
                         blockers: list[str] | None = None) -> dict[str, Any]:
    return {
        "present": True,
        "path": "/synthetic/framechain/manifest.json",
        "decision": decision,
        "pass": pass_value,
        "run_log": "/synthetic/run-system-servicemanager.txt",
        "remaining_blockers": blockers or [],
        "frames": [{"symbol": symbol} for symbol in (symbols or [])],
    }


def missing_manifest() -> dict[str, Any]:
    return {"present": False, "path": ""}


def run_case(name: str,
             executor_manifest: dict[str, Any],
             framechain: dict[str, Any],
             expected_decision: str,
             expected_pass: bool,
             expected_command_count: int,
             fragments: tuple[str, ...] = ()) -> RouterCaseResult:
    result = route_result(executor_manifest, framechain)
    missing = [fragment for fragment in fragments if all(fragment not in command for command in result.recommended_commands)]
    ok = (
        result.decision == expected_decision
        and result.pass_value == expected_pass
        and len(result.recommended_commands) == expected_command_count
        and not missing
    )
    return RouterCaseResult(
        name,
        "pass" if ok else "fail",
        result.decision,
        expected_decision,
        result.pass_value,
        expected_pass,
        len(result.recommended_commands),
        expected_command_count,
        missing,
        result.reason,
    )


def regression_manifest(args: argparse.Namespace) -> dict[str, Any]:
    cases = [
        run_case("missing", missing_manifest(), missing_manifest(), "v392-post-live-router-awaiting-executor", True, 1, ("wifi_v392_deploy_live_executor.py",)),
        run_case("approval", synthetic_executor("v392-deploy-live-executor-approval-required"), missing_manifest(), "v392-post-live-router-awaiting-approval", True, 1, (DEPLOY_APPROVAL_PHRASE, LIVE_APPROVAL_PHRASE)),
        run_case("scope", synthetic_executor("x", wifi=True), missing_manifest(), "v392-post-live-router-scope-violation", False, 0),
        run_case("blocked", synthetic_executor("v392-deploy-live-executor-live-preflight-blocked", False, blockers=["helper-v21"]), missing_manifest(), "v392-post-live-router-blocked", False, 0),
        run_case("symbolized-caller", synthetic_executor("v392-deploy-live-executor-full-service-manager-framechain-symbolization-pass"), synthetic_framechain("service-manager-framechain-symbolization-pass", symbols=["android::ServiceManager::addService"]), "v392-post-live-router-symbolized-caller-ready", True, 0),
        run_case("abort-only", synthetic_executor("v392-deploy-live-executor-full-service-manager-framechain-symbolization-pass"), synthetic_framechain("service-manager-framechain-symbolization-pass", symbols=["abort"]), "v392-post-live-router-symbolized-abort-only", True, 0),
        run_case("maprow", synthetic_executor("v392-deploy-live-executor-full-service-manager-framechain-maprow-ready"), synthetic_framechain("service-manager-framechain-maprow-ready", blockers=["frame-elf-artifact"]), "v392-post-live-router-elf-artifact-required", True, 1, ("wifi_service_manager_framechain_analyze.py",)),
        run_case("no-maprow", synthetic_executor("v392-deploy-live-executor-full-service-manager-framechain-no-maprow"), synthetic_framechain("service-manager-framechain-no-maprow", blockers=["frame-return-maprow"]), "v392-post-live-router-frame-maprow-required", True, 0),
        run_case("needs-live", synthetic_executor("v392-deploy-live-executor-approval-required"), synthetic_framechain("service-manager-framechain-needs-v392-live", blockers=["v392-framechain-evidence"]), "v392-post-live-router-awaiting-approval", True, 1),
    ]
    failed = [case.name for case in cases if case.status != "pass"]
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": "v392-post-live-router-regression-pass" if not failed else "v392-post-live-router-regression-failed",
        "pass": not failed,
        "reason": "all router cases passed" if not failed else "failed cases: " + ", ".join(failed),
        "next_step": "run route against real V392 executor output after exact approval",
        "host": collect_host_metadata(),
        "cases": [asdict(case) for case in cases],
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
    }


def render_regression_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [
            case["name"],
            case["status"],
            case["decision"],
            case["expected_decision"],
            case["command_count"],
            case["expected_command_count"],
            ", ".join(case["missing_fragments"]),
        ]
        for case in manifest["cases"]
    ]
    return "\n".join([
        "# V394 V392 Post-Live Router Regression",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        markdown_table(["name", "status", "decision", "expected", "commands", "expected_commands", "missing_fragments"], rows),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "regression":
        manifest = regression_manifest(args)
        store.write_json("manifest.json", manifest)
        store.write_text("summary.md", render_regression_summary(manifest))
    else:
        executor_path = args.executor_manifest or latest_executor_manifest()
        executor_manifest = load_json(executor_path)
        framechain = infer_framechain_manifest(executor_manifest, args.framechain_manifest)
        manifest = build_manifest(args, executor_manifest, framechain)
        store.write_json("manifest.json", manifest)
        store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

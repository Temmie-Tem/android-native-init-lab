#!/usr/bin/env python3
"""Host-only regression for V366 runtime repair smoke gates.

This script does not open the bridge and does not execute device commands.  It
imports wifi_runtime_repair_smoke.py, replaces the live command functions with
synthetic fixtures, and verifies the approval/preexisting-node state machine.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v367-runtime-repair-smoke-regression")
SMOKE_SCRIPT = SCRIPT_DIR / "wifi_runtime_repair_smoke.py"


@dataclass(frozen=True)
class RegressionCase:
    name: str
    command: str
    approval_phrase: str
    apply: bool
    assume_yes: bool
    preexisting_nodes: tuple[str, ...]
    expected_decision: str
    expected_pass: bool
    expected_mutation_calls: tuple[str, ...]


@dataclass
class RegressionResult:
    name: str
    status: str
    decision: str
    expected_decision: str
    pass_value: bool
    expected_pass: bool
    mutation_calls: list[str]
    expected_mutation_calls: list[str]
    checks: list[dict[str, Any]]
    manifest_path: str
    detail: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    return parser.parse_args()


def load_smoke_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("wifi_runtime_repair_smoke_under_test", SMOKE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {SMOKE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def cases(smoke: ModuleType) -> list[RegressionCase]:
    return [
        RegressionCase(
            "run-no-approval-clean-refuses",
            "run",
            "",
            False,
            False,
            (),
            "runtime-repair-smoke-approval-required",
            True,
            (),
        ),
        RegressionCase(
            "run-wrong-phrase-full-flags-refuses",
            "run",
            "approve v366 bounded runtime repair smoke only",
            True,
            True,
            (),
            "runtime-repair-smoke-approval-required",
            True,
            (),
        ),
        RegressionCase(
            "run-approved-clean-executes-synthetic-smoke",
            "run",
            smoke.APPROVAL_PHRASE,
            True,
            True,
            (),
            "runtime-repair-smoke-pass",
            True,
            ("create_nodes", "stat_created", "property_lookup", "cleanup_nodes", "postflight"),
        ),
        RegressionCase(
            "run-approved-preexisting-vendor-blocks-before-mutation",
            "run",
            smoke.APPROVAL_PHRASE,
            True,
            True,
            ("stat-vendor-block",),
            "runtime-repair-smoke-blocked",
            False,
            (),
        ),
        RegressionCase(
            "run-approved-preexisting-binder-blocks-before-mutation",
            "run",
            smoke.APPROVAL_PHRASE,
            True,
            True,
            ("stat-dev-binder",),
            "runtime-repair-smoke-blocked",
            False,
            (),
        ),
        RegressionCase(
            "cleanup-no-approval-refuses",
            "cleanup",
            "",
            False,
            False,
            (),
            "runtime-repair-smoke-cleanup-approval-required",
            True,
            (),
        ),
        RegressionCase(
            "cleanup-approved-executes-synthetic-cleanup",
            "cleanup",
            smoke.APPROVAL_PHRASE,
            True,
            True,
            (),
            "runtime-repair-smoke-cleanup-done",
            True,
            ("cleanup_nodes", "postflight"),
        ),
    ]


def make_args(smoke: ModuleType, case: RegressionCase, v365_manifest: Path, out_dir: Path) -> argparse.Namespace:
    return argparse.Namespace(
        out_dir=out_dir,
        host="127.0.0.1",
        port=54321,
        timeout=30.0,
        expect_version=smoke.DEFAULT_EXPECT_VERSION,
        v365_manifest=v365_manifest,
        approval_phrase=case.approval_phrase,
        apply=case.apply,
        assume_yes=case.assume_yes,
        command=case.command,
    )


def write_fake_v365(store: EvidenceStore) -> Path:
    path = store.write_json(
        "v365-manifest.json",
        {"decision": "service-runtime-repair-packet-ready", "pass": True},
    )
    return path


def make_step(smoke: ModuleType,
              store: EvidenceStore,
              name: str,
              ok: bool = True,
              text: str = "",
              rc: int | None = 0) -> Any:
    rel = f"native/{name}.txt"
    store.write_text(rel, text or f"synthetic {name}\n")
    return smoke.StepResult(
        name=name,
        command=f"synthetic {name}",
        ok=ok,
        rc=rc,
        status="ok" if ok else "missing",
        duration_sec=0.0,
        file=rel,
        error="" if ok else "synthetic missing",
    )


def preflight_steps(smoke: ModuleType, store: EvidenceStore, preexisting: tuple[str, ...]) -> list[Any]:
    store.mkdir("native")
    steps = [
        make_step(smoke, store, "version", text=f"{smoke.DEFAULT_EXPECT_VERSION}\n"),
        make_step(smoke, store, "status"),
        make_step(smoke, store, "mountsystem-ro"),
        make_step(smoke, store, "stat-helper"),
        make_step(smoke, store, "stat-ld-config"),
        make_step(smoke, store, "stat-apex-libraries"),
        make_step(smoke, store, "stat-property-root"),
        make_step(smoke, store, "stat-system-root"),
        make_step(smoke, store, "stat-dev-block-dir"),
        make_step(smoke, store, "stat-vendor-block", ok="stat-vendor-block" in preexisting),
        make_step(smoke, store, "proc-partitions", text=" 259       13    1382400 sda29\n"),
        make_step(smoke, store, "stat-dev-binder", ok="stat-dev-binder" in preexisting),
        make_step(smoke, store, "stat-dev-hwbinder", ok="stat-dev-hwbinder" in preexisting),
        make_step(smoke, store, "stat-dev-vndbinder", ok="stat-dev-vndbinder" in preexisting),
        make_step(smoke, store, "ps", text="PID STAT COMMAND\n1 S init\n"),
        make_step(smoke, store, "proc-net-dev", text="Inter-| Receive | Transmit\nlo: 0 0 0\nncm0: 0 0 0\n"),
        make_step(smoke, store, "sys-class-rfkill", ok=False),
    ]
    return steps


def run_case(smoke: ModuleType, case: RegressionCase, case_dir: Path) -> RegressionResult:
    store = EvidenceStore(case_dir)
    v365_manifest = write_fake_v365(store)
    args = make_args(smoke, case, v365_manifest, case_dir / "smoke-output")
    mutation_calls: list[str] = []

    def fake_run_preflight(_args: argparse.Namespace, active_store: EvidenceStore) -> list[Any]:
        return preflight_steps(smoke, active_store, case.preexisting_nodes)

    def fake_create_nodes(_args: argparse.Namespace, active_store: EvidenceStore, _preflight: list[Any]) -> list[Any]:
        mutation_calls.append("create_nodes")
        return [make_step(smoke, active_store, "create-vendor-block")]

    def fake_stat_created(_args: argparse.Namespace, active_store: EvidenceStore) -> list[Any]:
        mutation_calls.append("stat_created")
        return [
            make_step(smoke, active_store, "created-stat-vendor-block"),
            make_step(smoke, active_store, "created-stat-binder"),
            make_step(smoke, active_store, "created-stat-hwbinder"),
            make_step(smoke, active_store, "created-stat-vndbinder"),
        ]

    def fake_property_lookup(_args: argparse.Namespace, active_store: EvidenceStore) -> Any:
        mutation_calls.append("property_lookup")
        return make_step(
            smoke,
            active_store,
            "property-lookup",
            text="helper_status=namespace-ready\nchild_exit_code=0\n",
        )

    def fake_cleanup_nodes(_args: argparse.Namespace, active_store: EvidenceStore, prefix: str = "cleanup") -> list[Any]:
        mutation_calls.append("cleanup_nodes")
        return [make_step(smoke, active_store, prefix)]

    def fake_postflight(_args: argparse.Namespace, active_store: EvidenceStore) -> list[Any]:
        mutation_calls.append("postflight")
        return [
            make_step(smoke, active_store, "post-stat-vendor-block", ok=False),
            make_step(smoke, active_store, "post-stat-binder", ok=False),
            make_step(smoke, active_store, "post-stat-hwbinder", ok=False),
            make_step(smoke, active_store, "post-stat-vndbinder", ok=False),
            make_step(smoke, active_store, "post-ps", text="PID STAT COMMAND\n1 S init\n"),
            make_step(smoke, active_store, "post-proc-net-dev", text="lo: 0 0 0\nncm0: 0 0 0\n"),
            make_step(smoke, active_store, "post-version", text=f"{smoke.DEFAULT_EXPECT_VERSION}\n"),
        ]

    originals: dict[str, Callable[..., Any]] = {
        "run_preflight": smoke.run_preflight,
        "create_nodes": smoke.create_nodes,
        "stat_created": smoke.stat_created,
        "property_lookup": smoke.property_lookup,
        "cleanup_nodes": smoke.cleanup_nodes,
        "postflight": smoke.postflight,
    }
    try:
        smoke.run_preflight = fake_run_preflight
        smoke.create_nodes = fake_create_nodes
        smoke.stat_created = fake_stat_created
        smoke.property_lookup = fake_property_lookup
        smoke.cleanup_nodes = fake_cleanup_nodes
        smoke.postflight = fake_postflight
        manifest = smoke.build_manifest(args, EvidenceStore(args.out_dir))
    finally:
        for name, value in originals.items():
            setattr(smoke, name, value)

    manifest_path = store.write_json("synthetic-manifest.json", manifest)
    checks = manifest.get("checks") if isinstance(manifest.get("checks"), list) else []
    ok = (
        manifest.get("decision") == case.expected_decision
        and bool(manifest.get("pass")) is case.expected_pass
        and tuple(mutation_calls) == case.expected_mutation_calls
    )
    detail = (
        f"decision={manifest.get('decision')} pass={manifest.get('pass')} "
        f"mutation_calls={mutation_calls} expected={list(case.expected_mutation_calls)}"
    )
    return RegressionResult(
        name=case.name,
        status="pass" if ok else "fail",
        decision=str(manifest.get("decision")),
        expected_decision=case.expected_decision,
        pass_value=bool(manifest.get("pass")),
        expected_pass=case.expected_pass,
        mutation_calls=mutation_calls,
        expected_mutation_calls=list(case.expected_mutation_calls),
        checks=checks,
        manifest_path=str(manifest_path),
        detail=detail,
    )


def decide(results: list[RegressionResult]) -> tuple[str, bool, str, str]:
    failed = [item.name for item in results if item.status != "pass"]
    if failed:
        return (
            "runtime-repair-smoke-regression-failed",
            False,
            "failed cases: " + ", ".join(failed),
            "fix V366 gate before any approved smoke run",
        )
    return (
        "runtime-repair-smoke-regression-pass",
        True,
        "approval and preexisting-node gates behave as expected without device commands",
        "V366 live smoke remains blocked by exact approval phrase",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [
            item["name"],
            item["status"],
            item["decision"],
            str(item["pass_value"]),
            ",".join(item["mutation_calls"]) or "none",
            item["detail"],
        ]
        for item in manifest["results"]
    ]
    return "\n".join([
        "# V367 Runtime Repair Smoke Regression",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Cases",
        "",
        markdown_table(["case", "status", "decision", "pass", "mutation_calls", "detail"], rows),
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    smoke = load_smoke_module()
    case_root = store.mkdir("cases")
    results = [run_case(smoke, case, case_root / case.name) for case in cases(smoke)]
    decision, pass_ok, reason, next_step = decide(results)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "results": [asdict(item) for item in results],
        "device_commands_executed": False,
        "device_mutations": False,
        "notes": [
            "Host-only synthetic regression; no bridge connection is opened.",
            "Approved clean case uses monkeypatched synthetic mutation calls only.",
            "Approved preexisting-node cases must block before synthetic mutation calls.",
        ],
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

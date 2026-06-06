#!/usr/bin/env python3
"""Build a host-only property shim design model from Android-backed seed."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v307-property-shim-design")
DEFAULT_SEED = Path("tmp/wifi/v301-property-shim-seed-android/seed.json")
DEFAULT_V297 = Path("tmp/wifi/v297-android-property-capture-android/manifest.json")
DEFAULT_V298 = Path("tmp/wifi/v298-property-baseline-compare-android/manifest.json")
DEFAULT_V306 = Path("tmp/wifi/v300-android-capture-executor-live/manifest.json")
REQUIRED_KEYS = (
    "ro.build.version.sdk",
    "ro.product.name",
    "ro.hardware",
    "ro.vendor.build.version.sdk",
)


@dataclass
class DesignCandidate:
    name: str
    status: str
    risk: str
    runtime_scope: str
    benefit: str
    blocker: str
    next_proof: str


@dataclass
class SeedCheck:
    key: str
    state: str
    source: str
    has_value: bool


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--v297-manifest", type=Path, default=DEFAULT_V297)
    parser.add_argument("--v298-manifest", type=Path, default=DEFAULT_V298)
    parser.add_argument("--v306-live-manifest", type=Path, default=DEFAULT_V306)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def seed_entries(seed: dict[str, Any]) -> list[dict[str, Any]]:
    entries = seed.get("entries", [])
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def check_seed(seed: dict[str, Any]) -> list[SeedCheck]:
    by_key = {str(entry.get("key")): entry for entry in seed_entries(seed)}
    checks: list[SeedCheck] = []
    for key in REQUIRED_KEYS:
        entry = by_key.get(key, {})
        value = str(entry.get("value") or "")
        checks.append(SeedCheck(key, str(entry.get("state") or "missing"), str(entry.get("source") or "missing"), bool(value)))
    return checks


def seed_ready(seed: dict[str, Any], checks: list[SeedCheck]) -> bool:
    return bool(seed.get("present")) and all(check.state == "ready" and check.has_value for check in checks)


def candidates(ready: bool) -> list[DesignCandidate]:
    if not ready:
        return [
            DesignCandidate(
                "analysis-only-seed",
                "waiting-for-seed",
                "low",
                "host-only",
                "safe baseline once seed exists",
                "Android-backed seed is incomplete",
                "rerun v300/v297/v298/v301 chain",
            )
        ]
    return [
        DesignCandidate(
            "analysis-only-seed",
            "ready",
            "low",
            "host-only",
            "usable immediately for planning and config comparison",
            "does not satisfy bionic property_get at runtime",
            "use as reference input for future private shim prototype",
        ),
        DesignCandidate(
            "private-readonly-property-area",
            "preferred-next-prototype",
            "medium",
            "private helper namespace only",
            "closest to bionic read path without global device mutation",
            "requires exact property area/property_info format proof for this Android build",
            "build no-device format/probe model before creating any runtime node",
        ),
        DesignCandidate(
            "ld-preload-property-get-shim",
            "defer",
            "medium-high",
            "single process if preload works",
            "can intercept selected property APIs without property area creation",
            "linker namespace, bionic ABI, and preload acceptance are unproven",
            "only reconsider after linker/preload dry-run proof",
        ),
        DesignCandidate(
            "minimal-property-service-socket",
            "blocked",
            "high",
            "property service emulation",
            "could support writes/ctl-style clients if ever needed",
            "too broad; security and protocol surface exceed current Wi-Fi start-only need",
            "do not implement before private readonly path is exhausted",
        ),
    ]


def decide(seed: dict[str, Any], checks: list[SeedCheck]) -> tuple[str, bool, str, str]:
    if not seed.get("present"):
        return "property-shim-design-waiting-for-seed", True, "seed file is missing", "run v303 postprocess after Android capture"
    if not seed_ready(seed, checks):
        blocked = [check.key for check in checks if check.state != "ready" or not check.has_value]
        return "property-shim-design-waiting-for-seed", True, "seed entries blocked: " + ", ".join(blocked), "rerun Android capture/seed chain"
    return "property-shim-design-model-ready", True, "Android-backed seed can drive a future private readonly shim prototype", "plan private-readonly-property-area proof model next"


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    seed = load_json(args.seed)
    v297 = load_json(args.v297_manifest)
    v298 = load_json(args.v298_manifest)
    v306 = load_json(args.v306_live_manifest)
    checks = check_seed(seed)
    ready = seed_ready(seed, checks)
    decision, pass_ok, reason, next_step = decide(seed, checks)
    candidate_rows = candidates(ready)
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "seed": {"path": seed.get("path"), "present": bool(seed.get("present")), "schema": seed.get("schema"), "policy": seed.get("policy")},
            "v297": {"path": v297.get("path"), "present": bool(v297.get("present")), "decision": v297.get("decision"), "pass": v297.get("pass")},
            "v298": {"path": v298.get("path"), "present": bool(v298.get("present")), "decision": v298.get("decision"), "pass": v298.get("pass")},
            "v300_live": {"path": v306.get("path"), "present": bool(v306.get("present")), "decision": v306.get("decision"), "pass": v306.get("pass")},
        },
        "seed_checks": [asdict(check) for check in checks],
        "candidates": [asdict(candidate) for candidate in candidate_rows],
        "selected_next_prototype": "private-readonly-property-area" if ready else "none",
        "proof_requirements": [
            "prove expected bionic property area/property_info file layout for Android 12 vendor userspace",
            "keep property files in a private helper namespace, not global native /dev",
            "readonly keys only; no persist/ctl/property writes",
            "no service-manager/HAL/Wi-Fi daemon execution during format proof",
            "separate explicit approval before any runtime node creation or daemon retry",
        ] if ready else [],
        "blocked_actions": [
            "create global /dev/__properties__",
            "create global /dev/socket/property_service",
            "start servicemanager or hwservicemanager",
            "start Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
        "references": [
            "https://source.android.com/docs/core/architecture/configuration/sysprops-apis",
            "https://android.googlesource.com/platform/system/core.git/+/master/init/property_service.cpp",
            "https://android.googlesource.com/platform/bionic/+/master/libc/include/sys/system_properties.h",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    seed_rows = [[item["key"], item["state"], item["source"], str(item["has_value"])] for item in manifest["seed_checks"]]
    candidate_rows = [
        [item["name"], item["status"], item["risk"], item["runtime_scope"], item["blocker"], item["next_proof"]]
        for item in manifest["candidates"]
    ]
    input_rows = [[name, str(item["present"]), str(item.get("decision", item.get("policy"))), str(item["path"])] for name, item in manifest["inputs"].items()]
    return "\n".join([
        "# v307 Property Shim Design Model",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- selected_next_prototype: `{manifest['selected_next_prototype']}`",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Inputs",
        "",
        markdown_table(["input", "present", "decision/policy", "path"], input_rows),
        "",
        "## Seed Checks",
        "",
        markdown_table(["key", "state", "source", "has_value"], seed_rows),
        "",
        "## Design Candidates",
        "",
        markdown_table(["candidate", "status", "risk", "scope", "blocker", "next proof"], candidate_rows),
        "",
        "## Proof Requirements",
        "",
        *[f"- {item}" for item in manifest["proof_requirements"]],
        "",
        "## Blocked Actions",
        "",
        *[f"- {item}" for item in manifest["blocked_actions"]],
        "",
        "## References",
        "",
        *[f"- {item}" for item in manifest["references"]],
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"out_dir: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

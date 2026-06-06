#!/usr/bin/env python3
"""Evaluate Wi-Fi exposure and credential security gate v3."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import REPO_ROOT, collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_V220_MANIFEST = Path("tmp/wifi/v220-bringup-gate-v2/manifest.json")
DEFAULT_V221_MANIFEST = Path("tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json")
DEFAULT_V222_MANIFEST = Path("tmp/wifi/v222-vendor-root-evidence-export/manifest.json")
DEFAULT_V223_MANIFEST = Path("tmp/wifi/v223-recovery-rollback-policy/manifest.json")
DEFAULT_V224_MANIFEST = Path("tmp/wifi/v224-android-env-shim-materialize/manifest.json")

DEFAULT_REFERENCE_REPORTS = (
    Path("docs/reports/NATIVE_INIT_V134_NETWORK_EXPOSURE_GUARDRAIL_2026-05-07.md"),
    Path("docs/reports/NATIVE_INIT_V153_LONGSOAK_SECURITY_2026-05-08.md"),
    Path("docs/reports/NATIVE_INIT_V193_BROKER_AUTH_HARDENING_2026-05-11.md"),
    Path("docs/reports/NATIVE_INIT_V196_SECURITY_SCAN_FOLLOWUP_2026-05-11.md"),
    Path("docs/reports/NATIVE_INIT_V220_WIFI_PREFLIGHT_GATE_V2_2026-05-13.md"),
    Path("docs/reports/NATIVE_INIT_V221_HOST_VENDOR_ELF_LIBRARY_EVIDENCE_2026-05-13.md"),
    Path("docs/reports/NATIVE_INIT_V222_VENDOR_ROOT_EVIDENCE_EXPORT_2026-05-13.md"),
    Path("docs/reports/NATIVE_INIT_V223_RECOVERY_ROLLBACK_POLICY_2026-05-13.md"),
    Path("docs/reports/NATIVE_INIT_V224_ANDROID_ENV_SHIM_MATERIALIZE_2026-05-13.md"),
)

NO_DEVICE_COMMANDS: tuple[tuple[str, list[str]], ...] = ()


def default_out_dir() -> Path:
    return REPO_ROOT / "tmp" / "wifi" / "v225-exposure-security-gate-v3"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--v220-manifest", type=Path, default=DEFAULT_V220_MANIFEST)
    parser.add_argument("--v221-manifest", type=Path, default=DEFAULT_V221_MANIFEST)
    parser.add_argument("--v222-manifest", type=Path, default=DEFAULT_V222_MANIFEST)
    parser.add_argument("--v223-manifest", type=Path, default=DEFAULT_V223_MANIFEST)
    parser.add_argument("--v224-manifest", type=Path, default=DEFAULT_V224_MANIFEST)
    parser.add_argument(
        "--reference-report",
        action="append",
        type=Path,
        default=None,
        help="Additional or replacement reference report path. Can be repeated.",
    )
    return parser.parse_args()


def validate_no_device_commands() -> None:
    if NO_DEVICE_COMMANDS:
        raise AssertionError("v225 gate must not define live device commands")


def load_json(path: Path) -> dict[str, Any]:
    full_path = repo_path(path)
    if not full_path.exists():
        return {"missing": True, "path": str(full_path)}
    data = json.loads(full_path.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full_path)
    return data


def report_inventory(paths: tuple[Path, ...]) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for path in paths:
        full_path = repo_path(path)
        exists = full_path.exists()
        inventory.append(
            {
                "path": str(full_path),
                "repo_path": str(path),
                "exists": exists,
                "size": full_path.stat().st_size if exists else None,
            }
        )
    return inventory


def status_counts(items: list[dict[str, str]]) -> dict[str, int]:
    return {
        status: sum(1 for item in items if item["status"] == status)
        for status in ("pass", "warn", "blocked", "fail")
    }


def gate_item(name: str,
              status: str,
              source: str,
              evidence: str,
              reason: str,
              next_action: str) -> dict[str, str]:
    return {
        "name": name,
        "status": status,
        "source": source,
        "evidence": evidence,
        "reason": reason,
        "next_action": next_action,
    }


def manifest_decision(manifest: dict[str, Any]) -> str:
    if manifest.get("missing"):
        return "missing"
    return str(manifest.get("decision", "unknown"))


def reports_present(inventory: list[dict[str, Any]], required_fragments: tuple[str, ...]) -> bool:
    present = [
        str(item["repo_path"])
        for item in inventory
        if item.get("exists")
    ]
    return all(any(fragment in path for path in present) for fragment in required_fragments)


def build_exposure_matrix() -> list[dict[str, str]]:
    return [
        {
            "surface": "USB ACM serial bridge",
            "boundary": "trusted local USB operator path",
            "required_policy": "host bridge remains bound to localhost",
            "future_wifi_rule": "must not be bridged to wireless client reachability",
        },
        {
            "surface": "USB NCM tcpctl",
            "boundary": "USB-local control network",
            "required_policy": "token auth and explicit opt-in service state",
            "future_wifi_rule": "must not be routed from wireless client reachability",
        },
        {
            "surface": "rshell",
            "boundary": "USB-local optional root-control path",
            "required_policy": "token auth, explicit enable, audit evidence",
            "future_wifi_rule": "must remain disabled or USB-local only",
        },
        {
            "surface": "host broker",
            "boundary": "host-local control coordination",
            "required_policy": "auth, audit, exclusive unsafe-command policy",
            "future_wifi_rule": "broker must not publish device root control to WLAN",
        },
        {
            "surface": "netservice persistence",
            "boundary": "operator-controlled USB service flag",
            "required_policy": "explicit enable and review before persistent service use",
            "future_wifi_rule": "persistent flags must not widen to WLAN listeners",
        },
        {
            "surface": "future wireless network",
            "boundary": "untrusted until proven isolated",
            "required_policy": "test AP isolation, redaction, no secret collection",
            "future_wifi_rule": "active network work requires a later reviewed plan",
        },
    ]


def build_gate(v220: dict[str, Any],
               v221: dict[str, Any],
               v222: dict[str, Any],
               v223: dict[str, Any],
               v224: dict[str, Any],
               reference_reports: list[dict[str, Any]]) -> list[dict[str, str]]:
    v221_decision = manifest_decision(v221)
    v222_decision = manifest_decision(v222)
    v223_decision = manifest_decision(v223)
    v224_decision = manifest_decision(v224)
    v220_decision = manifest_decision(v220)

    vendor_ready = v221_decision == "elf-evidence-ready" and v222_decision == "vendor-root-ready"
    recovery_ready = v223_decision == "reboot-recovery-accepted"
    shim_ready = v224_decision == "shim-dryrun-ready"
    exposure_docs_ready = reports_present(
        reference_reports,
        (
            "V134_NETWORK_EXPOSURE_GUARDRAIL",
            "V193_BROKER_AUTH_HARDENING",
            "V196_SECURITY_SCAN_FOLLOWUP",
        ),
    )
    guardrails = [str(item) for item in v224.get("guardrails", [])]
    credential_denied = any("credential" in item.lower() and "no " in item.lower() for item in guardrails)
    blocked_policy = v224.get("materialization", {}).get("blocked_policy", {})
    if isinstance(blocked_policy, dict):
        credential_denied = credential_denied or str(blocked_policy.get("wifi_credentials")) == "denied"

    return [
        gate_item(
            "vendor_evidence",
            "pass" if vendor_ready else "blocked",
            "v221/v222",
            f"v221={v221_decision} v222={v222_decision}",
            "vendor executable and library evidence is complete" if vendor_ready else "host-visible vendor root evidence is still incomplete",
            "provide source vendor root, rerun v222, then rerun v221",
        ),
        gate_item(
            "recovery_policy",
            "pass" if recovery_ready else "fail",
            "v223",
            v223_decision,
            "reboot-only recovery policy is accepted for future opt-in planning" if recovery_ready else "recovery policy is missing or not accepted",
            "keep reboot-only recovery as the only accepted primitive until a safer primitive is proven",
        ),
        gate_item(
            "shim_materialization",
            "pass" if shim_ready else "blocked",
            "v224",
            v224_decision,
            "source-backed shim dry-run is ready" if shim_ready else "shim artifacts exist but source-backed materialization is incomplete",
            "rerun v224 after source vendor root evidence is available",
        ),
        gate_item(
            "root_control_exposure",
            "pass" if exposure_docs_ready else "warn",
            "v134/v193/v196",
            f"reference_reports_present={exposure_docs_ready}",
            "USB-local and broker/root-control exposure evidence is present" if exposure_docs_ready else "one or more exposure hardening reports are missing",
            "keep all root-control paths USB-local or host-local before any wireless planning",
        ),
        gate_item(
            "credential_policy",
            "pass" if credential_denied else "warn",
            "v219/v224",
            f"credential_denied={credential_denied}",
            "credential collection remains denied in this track" if credential_denied else "credential denial evidence is incomplete",
            "use a later isolated test-AP security plan before any credential handling",
        ),
        gate_item(
            "active_wifi_operations",
            "pass" if v220_decision == "no-go" else "warn",
            "v220/v225",
            f"v220={v220_decision}",
            "active wireless operations remain blocked by current gate state" if v220_decision == "no-go" else "v220 state changed; manual review required",
            "do not start daemons, radio transitions, scan, connect, routing, or credential workflows in v225",
        ),
    ]


def decide(items: list[dict[str, str]]) -> tuple[str, str, bool, list[str]]:
    failed = [item["name"] for item in items if item["status"] == "fail"]
    blocked = [item["name"] for item in items if item["status"] == "blocked"]
    warned = [item["name"] for item in items if item["status"] == "warn"]
    if failed:
        return "manual-review-required", f"gate has failed prerequisites: {', '.join(failed)}", False, blocked
    if blocked:
        return "still-no-go", f"gate has blocked prerequisites: {', '.join(blocked)}", True, blocked
    if warned:
        return "manual-review-required", f"gate has warnings requiring review: {', '.join(warned)}", False, blocked
    return "cnss-start-plan-approved", "all prerequisite and exposure gates passed for writing a later start plan", True, blocked


def build_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [item["name"], item["status"], item["source"], item["reason"], item["next_action"]]
        for item in manifest["gate"]["items"]
    ]
    exposure_rows = [
        [row["surface"], row["boundary"], row["required_policy"], row["future_wifi_rule"]]
        for row in manifest["exposure_matrix"]
    ]
    report_rows = [
        [item["repo_path"], "yes" if item["exists"] else "no", str(item.get("size"))]
        for item in manifest["reference_reports"]
    ]
    lines = [
        "# v225 Wi-Fi Exposure / Credential Security Gate v3",
        "",
        f"- generated: `{manifest['created']}`",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: `{manifest['reason']}`",
        f"- blockers: `{', '.join(manifest['blockers']) or 'none'}`",
        "",
        "## Gate Items",
        "",
        markdown_table(["name", "status", "source", "reason", "next action"], rows),
        "",
        "## Exposure Matrix",
        "",
        markdown_table(["surface", "boundary", "required policy", "future Wi-Fi rule"], exposure_rows),
        "",
        "## Reference Reports",
        "",
        markdown_table(["report", "exists", "size"], report_rows),
        "",
        "## Guardrails",
        "",
    ]
    for guardrail in manifest["guardrails"]:
        lines.append(f"- {guardrail}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `still-no-go` is a successful v225 result when prerequisite blockers remain.",
            "- v225 is a security/exposure gate and does not approve daemon execution or active network work.",
            "- If the vendor root and shim-source blockers remain open, the next work is evidence closure, not Wi-Fi activation.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    validate_no_device_commands()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)

    reference_paths = tuple(args.reference_report) if args.reference_report else DEFAULT_REFERENCE_REPORTS
    v220 = load_json(args.v220_manifest)
    v221 = load_json(args.v221_manifest)
    v222 = load_json(args.v222_manifest)
    v223 = load_json(args.v223_manifest)
    v224 = load_json(args.v224_manifest)
    reference_reports = report_inventory(reference_paths)

    items = build_gate(v220, v221, v222, v223, v224, reference_reports)
    decision, reason, pass_ok, blockers = decide(items)
    gate = {
        "items": items,
        "status_counts": status_counts(items),
    }
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "mode": "wifi-exposure-security-gate-v3",
        "blockers": blockers,
        "inputs": {
            "v220_manifest": str(repo_path(args.v220_manifest)),
            "v221_manifest": str(repo_path(args.v221_manifest)),
            "v222_manifest": str(repo_path(args.v222_manifest)),
            "v223_manifest": str(repo_path(args.v223_manifest)),
            "v224_manifest": str(repo_path(args.v224_manifest)),
        },
        "input_decisions": {
            "v220": manifest_decision(v220),
            "v221": manifest_decision(v221),
            "v222": manifest_decision(v222),
            "v223": manifest_decision(v223),
            "v224": manifest_decision(v224),
        },
        "gate": gate,
        "exposure_matrix": build_exposure_matrix(),
        "reference_reports": reference_reports,
        "guardrails": [
            "no live device commands by default",
            "no vendor or Android daemon execution",
            "no device writes",
            "no radio state transition",
            "no active network scan or association",
            "no credential collection",
            "no token or secret printing",
            "no listener reachability broadening",
            "no firewall mutation",
            "host evidence output stays private",
        ],
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_json("gate-v3.json", gate)
    store.write_text("summary.md", build_summary(manifest))
    print(f"{'PASS' if pass_ok else 'FAIL'} out_dir={out_dir} decision={decision} reason={reason}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

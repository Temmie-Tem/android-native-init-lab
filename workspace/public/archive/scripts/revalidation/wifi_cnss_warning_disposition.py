#!/usr/bin/env python3
"""v263 CNSS warning disposition model.

This tool does not start Wi-Fi services. It consumes prior live start-only
analysis, refreshes the existing read-only warning surface probe, and records
which warnings are accepted for start-only versus still requiring an opt-in shim
or manual review before broader Wi-Fi operations.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402
import wifi_cnss_warning_surface_probe as surface_probe  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v263-cnss-warning-disposition")
REFERENCE_URLS = {
    "aosp_logwrapper": "https://android.googlesource.com/platform/system/core/+/pie-dev/logwrapper/logwrapper.c",
    "aosp_klog": "https://chromium.googlesource.com/aosp/platform/system/core/libcutils/+/refs/heads/stabilize-15964.9.B/klog.cpp",
    "aosp_init": "https://chromium.googlesource.com/aosp/platform/system/core/+/refs/heads/master/init/",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    full = repo_path(path)
    if not full.exists():
        raise FileNotFoundError(full)
    return json.loads(full.read_text(encoding="utf-8"))


def warning_codes(analysis: dict[str, Any]) -> set[str]:
    return {str(item.get("code")) for item in analysis.get("warnings", []) if item.get("code")}


def surface_finding_codes(surface: dict[str, Any]) -> set[str]:
    return {str(item.get("code")) for item in surface.get("findings", []) if item.get("code")}


def build_surface_args(args: argparse.Namespace, surface_out_dir: Path) -> argparse.Namespace:
    return argparse.Namespace(
        out_dir=surface_out_dir,
        v258_manifest=args.analysis_manifest,
        helper_source=args.helper_source,
        host=args.host,
        port=args.port,
        timeout=args.timeout,
    )


def disposition_item(code: str, status: str, severity: str, classification: str, detail: str, next_action: str) -> dict[str, str]:
    return {
        "code": code,
        "status": status,
        "severity": severity,
        "classification": classification,
        "detail": detail,
        "next_action": next_action,
    }


def build_dispositions(analysis: dict[str, Any], surface: dict[str, Any]) -> list[dict[str, str]]:
    warnings = warning_codes(analysis)
    findings = surface_finding_codes(surface)
    surface_data = surface.get("surface", {})
    dispositions: list[dict[str, str]] = []

    if "perfd-client-unavailable" in warnings:
        if "perfd-client-surface-present-socket-absent" in findings:
            dispositions.append(disposition_item(
                "perfd-client-unavailable",
                "accepted-for-start-only",
                "warning",
                "android-runtime-service-gap",
                "perfd client/library surface exists but /dev/socket/perfd is absent in native init; v257/v261 start-only still passed cleanly",
                "Do not block start-only. Before broader Wi-Fi, design an opt-in private perfd/property shim or prove cnss-daemon does not require perfd beyond a warning.",
            ))
        else:
            dispositions.append(disposition_item(
                "perfd-client-unavailable",
                "manual-review",
                "warning",
                "surface-evidence-mismatch",
                "live warning exists but read-only surface probe did not classify perfd socket absence in the expected way",
                "Review surface manifest before another live operation.",
            ))

    if "kmsg-write-denied" in warnings:
        kmsg = surface_data.get("dev_kmsg", {})
        dispositions.append(disposition_item(
            "kmsg-write-denied",
            "accepted-for-start-only",
            "warning",
            "private-namespace-logging-gap",
            f"daemon/library logging path tries to write /dev/kmsg; surface mode={kmsg.get('mode')} uid={kmsg.get('uid')} gid={kmsg.get('gid')}",
            "Do not silently create or relax /dev/kmsg. If log noise blocks broader work, add a separate opt-in kmsg-null/log-sink mode and validate it without scan/connect.",
        ))

    if "shell-quote-noise" in warnings:
        if "kmsg-write-denied" in warnings:
            dispositions.append(disposition_item(
                "shell-quote-noise",
                "coalesced",
                "info",
                "logging-path-stderr-noise",
                "quote noise co-occurs with /dev/kmsg redirection failures and is not present in helper source as a generated command",
                "Track as part of the kmsg logging-path warning unless later evidence points to helper-generated shell syntax.",
            ))
        else:
            dispositions.append(disposition_item(
                "shell-quote-noise",
                "manual-review",
                "warning",
                "unpaired-shell-stderr-noise",
                "quote noise is present without a kmsg write-denied warning",
                "Review raw stderr before another live operation.",
            ))

    for code in sorted(warnings - {item["code"] for item in dispositions}):
        dispositions.append(disposition_item(
            code,
            "manual-review",
            "warning",
            "unknown-live-warning",
            "warning code was not recognized by the v263 disposition model",
            "Add an explicit disposition rule before treating this as accepted.",
        ))

    if not dispositions:
        dispositions.append(disposition_item(
            "no-live-warnings",
            "ready",
            "info",
            "no-warning-surface",
            "input analyzer manifest contains no live warnings",
            "No warning-specific action needed.",
        ))
    return dispositions


def build_checks(analysis: dict[str, Any], surface: dict[str, Any], dispositions: list[dict[str, str]]) -> list[dict[str, Any]]:
    warnings = warning_codes(analysis)
    blocked = [item for item in dispositions if item["status"] == "manual-review" and item["severity"] != "info"]
    return [
        {
            "name": "analysis-pass",
            "pass": bool(analysis.get("pass")) and analysis.get("decision") == "cnss-start-only-evidence-classified",
            "severity": "critical",
            "detail": f"decision={analysis.get('decision')} pass={analysis.get('pass')}",
        },
        {
            "name": "surface-pass",
            "pass": bool(surface.get("pass")) and surface.get("decision") == "cnss-warning-surface-classified",
            "severity": "critical",
            "detail": f"decision={surface.get('decision')} pass={surface.get('pass')}",
        },
        {
            "name": "expected-warning-codes",
            "pass": warnings.issubset({"perfd-client-unavailable", "kmsg-write-denied", "shell-quote-noise"}),
            "severity": "critical",
            "detail": json.dumps(sorted(warnings), sort_keys=True),
        },
        {
            "name": "no-blocking-disposition",
            "pass": not blocked,
            "severity": "critical",
            "detail": json.dumps([item["code"] for item in blocked], sort_keys=True),
        },
    ]


def classify_decision(checks: list[dict[str, Any]], dispositions: list[dict[str, str]]) -> tuple[bool, str, str]:
    failed = [item["name"] for item in checks if item["severity"] == "critical" and not item["pass"]]
    if failed:
        return False, "cnss-warning-disposition-incomplete", "critical warning disposition check failed: " + ", ".join(failed)
    if any(item["status"] == "manual-review" for item in dispositions):
        return False, "cnss-warning-disposition-blocked", "one or more live warnings need manual review"
    return True, "cnss-warning-disposition-ready", "known CNSS warnings are classified for start-only without daemon execution"


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], "PASS" if item["pass"] else "FAIL", item["severity"], item["detail"]] for item in manifest["checks"]]
    disposition_rows = [
        [item["code"], item["status"], item["classification"], item["next_action"]]
        for item in manifest["dispositions"]
    ]
    return "".join([
        "# v263 CNSS Warning Disposition\n\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- pass: `{manifest['pass']}`\n",
        f"- reason: `{manifest['reason']}`\n",
        f"- analysis_manifest: `{manifest['analysis_manifest']}`\n",
        f"- surface_out_dir: `{manifest['surface_out_dir']}`\n\n",
        "## Checks\n\n",
        markdown_table(["check", "result", "severity", "detail"], check_rows),
        "\n\n## Dispositions\n\n",
        markdown_table(["warning", "status", "classification", "next action"], disposition_rows),
        "\n\n## Guardrails\n\n",
        "- No daemon or Wi-Fi service is started by this tool.\n",
        "- No `/dev/kmsg`, property, perfd, QRTR/QMI, rfkill, ICNSS, or partition state is mutated.\n",
        "- Any future perfd/kmsg shim remains opt-in and approval-gated.\n",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--surface-out-dir", type=Path)
    parser.add_argument("--helper-source", type=Path, default=surface_probe.HELPER_SOURCE)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = repo_path(args.out_dir)
    surface_out_dir = repo_path(args.surface_out_dir) if args.surface_out_dir else out_dir / "surface"
    analysis = load_json(args.analysis_manifest)
    surface = surface_probe.classify(build_surface_args(args, surface_out_dir))
    dispositions = build_dispositions(analysis, surface)
    checks = build_checks(analysis, surface, dispositions)
    pass_ok, decision, reason = classify_decision(checks, dispositions)
    manifest = {
        "created": now_iso(),
        "mode": "cnss-warning-disposition",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "analysis_manifest": str(repo_path(args.analysis_manifest)),
        "surface_out_dir": str(surface_out_dir),
        "out_dir": str(out_dir),
        "host_metadata": collect_host_metadata(),
        "references": REFERENCE_URLS,
        "analysis_warnings": analysis.get("warnings", []),
        "surface_decision": surface.get("decision"),
        "surface_findings": surface.get("findings", []),
        "dispositions": dispositions,
        "checks": checks,
        "guardrails": [
            "no cnss-daemon execution",
            "no cnss_diag execution",
            "no property/perfd/kmsg mutation",
            "no QRTR/QMI request transmission",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no rfkill unblock, ICNSS bind/unbind, Android partition write, or reboot",
        ],
    }
    store = EvidenceStore(out_dir)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {reason}")
    print(f"out_dir: {out_dir}")
    for item in dispositions:
        print(f"disposition: {item['code']} {item['status']} {item['classification']}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

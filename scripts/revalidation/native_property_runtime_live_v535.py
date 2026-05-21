#!/usr/bin/env python3
"""V535 rmt_storage private property runtime live deploy and lookup proof.

This deploys the V535 host-only property layout to a versioned private SD
workspace and verifies only selected read-only property lookups against that
private root.  It does not replace global `/dev/__properties__`, create a
global property-service socket, start daemons, or bring Wi-Fi up.
"""

from __future__ import annotations

from pathlib import Path

import native_property_runtime_live_v472 as live


live.__doc__ = __doc__
live.DEFAULT_OUT_DIR = Path("tmp/wifi/v535-rmt-property-runtime-live")
live.DEFAULT_V471 = Path("tmp/wifi/v535-rmt-storage-private-property-runtime/manifest.json")
live.DEFAULT_HELPER_SHA256 = "3c41c86852c43eb475b991628ca2d9e1234f635b8b6ca80463ffa62978e230a4"
live.REMOTE_WORKDIR = "/mnt/sdext/a90/private-property-v317/v535"
live.REMOTE_PROP_ROOT = live.REMOTE_WORKDIR + "/dev/__properties__"
live.APPROVAL_PHRASE = (
    "approve v535 rmt-storage private property runtime deploy only; "
    "no daemon start and no Wi-Fi bring-up"
)
live.LOOKUP_KEYS = (
    "ro.property_service.version",
    "ro.baseband",
    "debug.ld.app.rmt_storage",
    "arm64.memtag.process.rmt_storage",
    "persist.log.tag.vendor.rmt_storage",
    "log.tag.vendor.rmt_storage",
    "persist.log.semlevel",
    "init.svc.vendor.rmt_storage",
)


def build_checks(args, layout, files, records, lookups):
    bad_files = [item.relative_path for item in files if item.status != "pass"]
    sha_text = "\n".join(
        Path(record.file).name + " " + live.repo_path(args.out_dir).joinpath(record.file).read_text(encoding="utf-8", errors="replace")
        for record in records
        if record.name == "sha-helper"
    )
    lookup_failures = [item.key for item in lookups if not item.ok]
    command_failures = [record.name for record in records if not record.ok]
    return [
        live.Check(
            "v535-layout",
            "pass" if layout.get("decision") == "v535-rmt-storage-private-property-runtime-ready" and bool(layout.get("pass")) else "blocked",
            "blocker",
            f"decision={layout.get('decision')} pass={layout.get('pass')}",
            [str(layout.get("path", ""))],
            "regenerate V535 before live deploy",
        ),
        live.Check(
            "layout-files",
            "pass" if files and not bad_files else "blocked",
            "blocker",
            f"files={len(files)} bad={len(bad_files)} bytes={sum(item.bytes for item in files)}",
            bad_files[:8],
            "fix local V535 layout before live deploy",
        ),
        live.Check(
            "approval-gate",
            "pass" if live.approved(args) else "needs-operator",
            "approval",
            f"phrase_match={args.approval_phrase == live.APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}",
            [live.APPROVAL_PHRASE],
            "provide exact approval phrase and flags before live private deploy",
        ),
        live.Check(
            "helper-v67",
            "pass" if args.command == "plan" or args.helper_sha256 in sha_text else "blocked",
            "blocker",
            f"expected_sha={args.helper_sha256}",
            [line for line in sha_text.splitlines() if args.helper in line][:2],
            "deploy helper v67 before property lookup proof",
        ),
        live.Check(
            "device-commands",
            "pass" if not command_failures else "blocked",
            "blocker",
            f"failed={len(command_failures)}",
            command_failures[:10],
            "inspect command evidence and recover native control before retry",
        ),
        live.Check(
            "property-lookups",
            "pass" if args.command not in ("lookup", "run") or (lookups and not lookup_failures) else "blocked",
            "blocker",
            f"lookups={len(lookups)} failures={len(lookup_failures)}",
            lookup_failures[:12],
            "fix V535 property layout before rmt_storage proof",
        ),
    ]


def decide(args, checks, live_error):
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    approvals = [check.name for check in checks if check.severity == "approval" and check.status != "pass"]
    if args.command == "plan":
        return "v535-rmt-property-runtime-plan-ready", True, "plan generated without device mutation", "run preflight"
    if blockers:
        return "v535-rmt-property-runtime-blocked", False, "blocked checks: " + ", ".join(blockers), "resolve blockers before live proof"
    if args.command == "preflight":
        return "v535-rmt-property-runtime-preflight-ready", True, "preflight passed; live run still requires exact approval", "run approved V535 private deploy"
    if args.command == "lookup" and not live_error:
        return "v535-rmt-property-runtime-lookup-pass", True, "selected property lookups passed against the deployed V535 private root", "rerun rmt_storage proof against the V535 root"
    if approvals:
        return "v535-rmt-property-runtime-approval-required", False, "missing approval gates: " + ", ".join(approvals), "provide exact approval if live private deploy is intended"
    if live_error:
        return "v535-rmt-property-runtime-failed", False, live_error, "inspect evidence and retry only after cleanup"
    return "v535-rmt-property-runtime-lookup-pass", True, "V535 private property root deployed and selected property lookups passed", "rerun rmt_storage proof against the V535 root"


def render_summary(manifest):
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"]] for item in manifest["checks"]]
    file_rows = [[item["role"], item["relative_path"], str(item["bytes"]), item["status"]] for item in manifest["files"]]
    lookup_rows = [
        [item["key"], item["expected"], item["actual"], str(item["context_warning_count"]), str(item["access_denied_count"]), str(item["ok"])]
        for item in manifest["lookups"]
    ]
    return "\n".join([
        "# V535 rmt_storage Private Property Runtime Live Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- remote_property_root: `{manifest['remote_property_root']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        live.markdown_table(["name", "status", "severity", "detail"], check_rows),
        "",
        "## Files",
        "",
        live.markdown_table(["role", "relative_path", "bytes", "status"], file_rows),
        "",
        "## Lookups",
        "",
        live.markdown_table(["key", "expected", "actual", "context_warnings", "access_denied", "ok"], lookup_rows),
        "",
        "## Blocked Actions",
        "",
        "\n".join(f"- `{item}`" for item in manifest["blocked_actions"]),
        "",
    ])


live.build_checks = build_checks
live.decide = decide
live.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(live.main())

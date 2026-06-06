#!/usr/bin/env python3
"""V1862 read-only remote preflight for the private SDX50M cnss-daemon artifact."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import native_wifi_bridge_readonly_smoke_v1860 as base
import native_wifi_bridge_direct_prereq_v1861 as prev1861


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1862"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1862-remote-sdx50m-artifact-preflight"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1862_REMOTE_SDX50M_ARTIFACT_PREFLIGHT_2026-06-03.md"
)
V1857_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1857-sdx50m-bridge-artifact-plumbing" / "manifest.json"
V1861_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1861-bridge-direct-prereq" / "manifest.json"
A90CTL = REPO_ROOT / "scripts" / "revalidation" / "a90ctl.py"
REMOTE_ARTIFACT = "/cache/bin/cnss-daemon.sdx50m"
TOYBOX = "/cache/bin/toybox"
PAYLOAD_CHAR_LIMIT = 6000

READS: tuple[tuple[str, list[str], float], ...] = (
    ("toybox-stat", ["stat", TOYBOX], 8.0),
    ("remote-artifact-stat", ["stat", REMOTE_ARTIFACT], 8.0),
    ("remote-artifact-sha256", ["run", TOYBOX, "sha256sum", REMOTE_ARTIFACT], 12.0),
)


def rel(path: Path) -> str:
    return base.rel(path)


def load_json(path: Path) -> dict[str, Any]:
    return base.load_json(path)


def clean_lines(text: str) -> list[str]:
    return base.clean_lines(text)


def redact(text: str) -> str:
    return base.redact(text)


def strip_protocol(text: str) -> str:
    return base.strip_protocol(text)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else REPO_ROOT / path


def local_artifact(v1857: dict[str, Any]) -> dict[str, Any]:
    inputs = (v1857.get("details") or {}).get("inputs") or {}
    artifact = inputs.get("private_cnss_artifact") or {}
    path = resolve_repo_path(str(artifact.get("path", "")))
    exists = path.exists()
    return {
        "path": rel(path),
        "exists": exists,
        "size": path.stat().st_size if exists else 0,
        "sha256": sha256_file(path) if exists else "",
        "expected_size": int(artifact.get("size") or 0),
        "expected_sha256": str(artifact.get("sha256") or ""),
        "v1857_decision": v1857.get("decision", ""),
        "v1857_label": v1857.get("label", ""),
        "v1857_pass": bool(v1857.get("pass")),
    }


def run_a90ctl(name: str, command: list[str], timeout: float) -> dict[str, Any]:
    python3 = shutil.which("python3")
    if not python3:
        return {
            "name": name,
            "command": command,
            "host_available": False,
            "host_rc": 127,
            "parsed_json": False,
            "protocol_rc": None,
            "protocol_status": "host-python3-missing",
            "hide_retry_triggered": False,
            "payload": "",
            "payload_lines": [],
            "stderr_lines": ["python3 not found"],
        }
    host_command = [
        python3,
        str(A90CTL),
        "--json",
        "--allow-error",
        "--hide-on-busy",
        "--timeout",
        f"{timeout:.1f}",
        *command,
    ]
    try:
        completed = subprocess.run(
            host_command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout + 4.0,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = redact(exc.stdout or "")
        stderr = redact(exc.stderr or "timeout")
        payload = strip_protocol(stdout)[:PAYLOAD_CHAR_LIMIT]
        return {
            "name": name,
            "command": command,
            "host_available": True,
            "host_rc": 124,
            "parsed_json": False,
            "protocol_rc": None,
            "protocol_status": "host-timeout",
            "hide_retry_triggered": "sending hide" in stderr,
            "payload": payload,
            "payload_lines": base.truncated_lines(payload),
            "stderr_lines": base.truncated_lines(stderr, 12),
        }
    stderr = redact(completed.stderr)
    parsed: dict[str, Any] | None = None
    try:
        loaded = json.loads(completed.stdout)
        if isinstance(loaded, dict):
            parsed = loaded
    except json.JSONDecodeError:
        parsed = None
    text = str(parsed.get("text", "")) if parsed else redact(completed.stdout)
    payload = strip_protocol(redact(text))
    if len(payload) > PAYLOAD_CHAR_LIMIT:
        payload = payload[:PAYLOAD_CHAR_LIMIT] + "\n[truncated]\n"
    end = parsed.get("end", {}) if parsed else {}
    return {
        "name": name,
        "command": command,
        "host_available": True,
        "host_rc": completed.returncode,
        "parsed_json": parsed is not None,
        "protocol_rc": parsed.get("rc") if parsed else None,
        "protocol_status": parsed.get("status") if parsed else "json-parse-failed",
        "begin": parsed.get("begin", {}) if parsed else {},
        "end": end if isinstance(end, dict) else {},
        "hide_retry_triggered": "sending hide" in stderr,
        "payload": payload,
        "payload_lines": base.truncated_lines(payload),
        "stderr_lines": base.truncated_lines(stderr, 12),
    }


def command_terminal(record: dict[str, Any]) -> bool:
    return prev1861.command_terminal(record)


def command_ok(record: dict[str, Any]) -> bool:
    return base.command_ok(record)


def find_record(records: list[dict[str, Any]], name: str) -> dict[str, Any]:
    return base.find_record(records, name)


def extract_sha256(text: str) -> str:
    match = re.search(r"\b([0-9a-fA-F]{64})\b", text)
    return match.group(1).lower() if match else ""


def remote_artifact(records: list[dict[str, Any]]) -> dict[str, Any]:
    stat = find_record(records, "remote-artifact-stat")
    sha = find_record(records, "remote-artifact-sha256")
    stat_payload = str(stat.get("payload", ""))
    sha_payload = str(sha.get("payload", ""))
    no_such = any(
        "No such file" in line or "No such file or directory" in line
        for line in clean_lines(stat_payload + "\n" + sha_payload)
    )
    return {
        "path": REMOTE_ARTIFACT,
        "stat_terminal": command_terminal(stat),
        "stat_ok": command_ok(stat),
        "sha_terminal": command_terminal(sha),
        "sha_ok": command_ok(sha),
        "sha256": extract_sha256(sha_payload),
        "missing": bool(no_such),
        "stat_payload_lines": stat.get("payload_lines", []),
        "sha_payload_lines": sha.get("payload_lines", []),
    }


def collect(v1857: dict[str, Any], v1861: dict[str, Any]) -> dict[str, Any]:
    git_status = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    records = [run_a90ctl(name, command, timeout) for name, command, timeout in READS]
    local = local_artifact(v1857)
    remote = remote_artifact(records)
    return {
        "v1861": {
            "path": rel(V1861_MANIFEST),
            "decision": v1861.get("decision", ""),
            "label": v1861.get("label", ""),
            "pass": bool(v1861.get("pass")),
        },
        "host": {
            "git_clean": git_status.returncode == 0 and git_status.stdout == "",
            "git_status_lines": clean_lines(git_status.stdout)[:20],
        },
        "commands": records,
        "summary": {
            "local_artifact": local,
            "remote_artifact": remote,
            "toybox_ok": command_ok(find_record(records, "toybox-stat")),
            "remote_sha_matches_local": bool(remote.get("sha256")) and remote.get("sha256") == local.get("sha256"),
            "hide_retry_count": sum(1 for record in records if record.get("hide_retry_triggered")),
        },
        "safety": {
            "read_only_a90ctl_commands_executed": True,
            "toybox_sha256sum_read_executed": True,
            "remote_artifact_written": False,
            "remote_artifact_executed": False,
            "serial_bridge_started": False,
            "flash_executed": False,
            "reboot_executed": False,
            "stage_properties_executed": False,
            "start_actors_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "direct_subsys_esoc0_open_executed": False,
            "pmic_gpio_gdsc_write_executed": False,
            "esoc_ioctl_notify_executed": False,
            "forced_rc1_or_pci_rescan_executed": False,
        },
    }


def forbidden_safety_clean(details: dict[str, Any]) -> bool:
    allowed = {"read_only_a90ctl_commands_executed", "toybox_sha256sum_read_executed"}
    return not any(value for key, value in details["safety"].items() if key not in allowed)


def classify(details: dict[str, Any]) -> tuple[str, str, str, bool]:
    summary = details["summary"]
    local = summary["local_artifact"]
    remote = summary["remote_artifact"]
    input_ready = (
        details["v1861"]["pass"]
        and details["v1861"]["label"] == "direct-prereq-pre-wifi-gap-confirmed"
        and local["v1857_pass"]
        and local["v1857_label"] == "artifact-plumbing-dry-run-ready"
    )
    if not input_ready:
        return "input-review", "v1862-input-review", "V1857/V1861 inputs are missing or not at the expected bridge preflight state", False
    if not forbidden_safety_clean(details):
        return "safety-review", "v1862-safety-review", "Remote artifact preflight claims a forbidden action", False
    if not local["exists"] or local["sha256"] != local["expected_sha256"] or local["size"] != local["expected_size"]:
        return "local-artifact-review", "v1862-local-artifact-review", "Local private SDX50M artifact no longer matches V1857", False
    if not summary["toybox_ok"]:
        return (
            "remote-toybox-missing",
            "v1862-remote-toybox-missing-host-pass",
            "Remote toybox is not readable through the bridge, so deploy/readback tooling must be repaired before artifact promotion",
            True,
        )
    if remote["stat_ok"] and remote["sha_ok"] and summary["remote_sha_matches_local"]:
        return (
            "remote-sdx50m-artifact-ready",
            "v1862-remote-sdx50m-artifact-ready-host-pass",
            "Remote private SDX50M cnss-daemon artifact exists and its SHA matches the local V1857 artifact; the next bridge unit can focus on v356 private-mount integration",
            True,
        )
    if remote["missing"] or remote["sha_terminal"]:
        return (
            "remote-sdx50m-artifact-deploy-needed",
            "v1862-remote-sdx50m-artifact-deploy-needed-host-pass",
            "Remote private SDX50M cnss-daemon artifact is missing or SHA-mismatched; a deploy-only cache write gate is required before any live private-mount bridge",
            True,
        )
    return (
        "remote-sdx50m-artifact-readback-incomplete",
        "v1862-remote-sdx50m-artifact-readback-incomplete",
        "Remote artifact stat/SHA readback did not complete cleanly enough to classify deploy readiness",
        False,
    )


def command_table(records: list[dict[str, Any]]) -> list[str]:
    rows = ["| name | command | host rc | protocol | terminal |", "| --- | --- | ---: | --- | --- |"]
    for record in records:
        rows.append(
            "| {name} | `{command}` | `{host_rc}` | `{status}/{rc}` | `{terminal}` |".format(
                name=record["name"],
                command=" ".join(record["command"]),
                host_rc=record["host_rc"],
                status=record["protocol_status"],
                rc=record["protocol_rc"],
                terminal=command_terminal(record),
            )
        )
    return rows


def render_report(result: dict[str, Any]) -> str:
    details = result["details"]
    summary = details["summary"]
    local = summary["local_artifact"]
    remote = summary["remote_artifact"]
    return "\n".join([
        "# Native Init V1862 Remote SDX50M Artifact Preflight",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: live read-only remote artifact preflight for the SDX50M bridge path",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Input",
        "",
        f"- V1861: `{details['v1861']['decision']}` / `{details['v1861']['label']}` / pass `{details['v1861']['pass']}`",
        f"- V1857 local artifact: `{local['v1857_decision']}` / `{local['v1857_label']}` / pass `{local['v1857_pass']}`",
        "",
        "## Artifact State",
        "",
        f"- local artifact: `{local['path']}` exists `{local['exists']}` size `{local['size']}` sha `{local['sha256']}`",
        f"- expected local size/SHA: `{local['expected_size']}` / `{local['expected_sha256']}`",
        f"- remote artifact: `{remote['path']}` stat_ok `{remote['stat_ok']}` sha_ok `{remote['sha_ok']}` missing `{remote['missing']}` sha `{remote['sha256']}`",
        f"- remote SHA matches local: `{summary['remote_sha_matches_local']}`",
        f"- remote toybox ok: `{summary['toybox_ok']}`",
        f"- hide retry count: `{summary['hide_retry_count']}`",
        f"- git clean: `{details['host']['git_clean']}`",
        "",
        "## Commands",
        "",
        *command_table(details["commands"]),
        "",
        "## Safety Scope",
        "",
        "This preflight used only read-only bridge observations: `stat` and `toybox sha256sum` on the remote target. It did not write or execute the remote artifact, start a serial bridge, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        "- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "- If remote artifact is missing or mismatched, run a separate deploy-only cache-write gate before any private-mount bridge live unit.",
        "- If remote artifact is ready, the next useful unit is v356 private-mount bridge integration under the existing rollback and lower-publication guardrails.",
        "",
    ])


def main() -> int:
    details = collect(load_json(V1857_MANIFEST), load_json(V1861_MANIFEST))
    label, decision, reason, passed = classify(details)
    result = {
        "cycle": CYCLE,
        "decision": decision,
        "label": label,
        "pass": passed,
        "reason": reason,
        "out_dir": rel(OUT_DIR),
        "report": rel(REPORT_PATH),
        "details": details,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("decision", "label", "pass", "reason", "out_dir", "report")}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

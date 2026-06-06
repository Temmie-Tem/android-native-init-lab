#!/usr/bin/env python3
"""Classify CNSS start-only live evidence without executing device commands."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90_kernel_tools import collect_host_metadata, repo_path  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402
from wifi_cnss_zombie_audit import parse_ps_stat_comm, summarize_cnss_processes  # noqa: E402


DEFAULT_RUN_DIR = Path("tmp/wifi/v257-cnss-live-start-only-run")
DEFAULT_OUT_DIR = Path("tmp/wifi/v258-cnss-live-evidence-analysis")
KEYVAL_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
STATUS_RE = re.compile(r"^([A-Za-z0-9_()]+):\s*(.*)$")
WLAN_RE = re.compile(r"^\s*wlan\S*:", re.MULTILINE)


REQUIRED_CONTEXT_KEYS = (
    "helper_status",
    "context.target.exists",
    "context.dev_null.exists",
    "context.selinux_null.exists",
    "context.data_vendor_wifi.exists",
    "context.data_vendor_wifi_sockets.exists",
    "context.ld_config.exists",
    "context.apex_libraries.exists",
    "context.apex_runtime.exists",
    "context.apex_vndk_v30_libcutils.exists",
    "context.vendor_lib64.exists",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")


def maybe_read(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return read_text(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_keyvals(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = KEYVAL_RE.match(line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


def section(text: str, begin: str, end: str) -> str:
    start = text.find(begin)
    if start < 0:
        return ""
    start = text.find("\n", start)
    if start < 0:
        return ""
    finish = text.find(end, start + 1)
    if finish < 0:
        finish = len(text)
    return text[start + 1:finish].strip("\n")


def prefix_dict(values: dict[str, str], prefix: str) -> dict[str, str]:
    marker = prefix + "."
    return {key[len(marker):]: value for key, value in values.items() if key.startswith(marker)}


def parse_proc_status(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in text.splitlines():
        match = STATUS_RE.match(line)
        if match:
            data[match.group(1)] = match.group(2).strip()
    return data


def normalize_root_path(path: str) -> str:
    marker = "/root"
    index = path.find(marker)
    if index >= 0:
        return path[index + len(marker):] or "/"
    return path


def parse_maps(text: str) -> dict[str, Any]:
    paths: list[str] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 6:
            raw_path = parts[-1]
            if raw_path.startswith("/"):
                paths.append(normalize_root_path(raw_path))
    unique = sorted(set(paths))
    categories = {
        "target": 0,
        "vendor": 0,
        "system": 0,
        "apex": 0,
        "other": 0,
    }
    for path in unique:
        if path == "/vendor/bin/cnss-daemon":
            categories["target"] += 1
        elif path.startswith("/vendor/"):
            categories["vendor"] += 1
        elif path.startswith("/system/"):
            categories["system"] += 1
        elif path.startswith("/apex/"):
            categories["apex"] += 1
        else:
            categories["other"] += 1
    qmi_paths = [path for path in unique if "qmi" in path.lower() or "peripheral" in path.lower() or "cld80211" in path.lower()]
    return {
        "path_count": len(unique),
        "categories": categories,
        "qmi_related_paths": qmi_paths,
        "paths": unique,
    }


def parse_daemon_messages(text: str) -> list[str]:
    messages: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("cnss-daemon "):
            messages.append(stripped)
    return messages


def post_pidof_absent(text: str) -> bool | None:
    if not text:
        return None
    if "pidof cnss-daemon" not in text:
        return None
    if "[exit 1]" in text and "status=error" in text:
        return True
    return False


def post_no_wlan(text: str) -> bool | None:
    if not text:
        return None
    return WLAN_RE.search(text) is None


def post_wifiinv_no_wlan_like(text: str) -> bool | None:
    if not text:
        return None
    if "wlan_like=0" in text:
        return True
    if "wlan_like=" in text:
        return False
    return None


def bool_key(value: str | None) -> bool:
    return value in {"1", "true", "True", "yes", "ok"}


def add_check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str, *, severity: str = "critical") -> None:
    checks.append({"name": name, "pass": passed, "severity": severity, "detail": detail})


def classify(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = repo_path(args.run_dir)
    out_dir = repo_path(args.out_dir)
    transcript_path = run_dir / "commands" / "cnss-start-only-run.txt"
    manifest_path = run_dir / "manifest.json"
    transcript = read_text(transcript_path)
    runner_manifest = load_json(manifest_path)
    keyvals = parse_keyvals(transcript)
    cnss_start = prefix_dict(keyvals, "cnss_start")
    cnss_child = prefix_dict(keyvals, "cnss_child")
    identity_before = prefix_dict(keyvals, "cnss.identity.before")
    identity_after = prefix_dict(keyvals, "cnss.identity.after")
    stderr_text = section(transcript, "A90_EXECNS_STDERR_BEGIN", "A90_EXECNS_STDERR_END")
    status_text = section(transcript, "A90_EXECNS_CNSS_PROC_status_BEGIN", "A90_EXECNS_CNSS_PROC_status_END")
    maps_text = section(transcript, "A90_EXECNS_CNSS_PROC_maps_BEGIN", "A90_EXECNS_CNSS_PROC_maps_END")
    proc_status = parse_proc_status(status_text)
    maps_summary = parse_maps(maps_text)
    daemon_messages = parse_daemon_messages(transcript)

    post_pidof = maybe_read(repo_path(args.post_pidof) if args.post_pidof else None)
    post_netdev = maybe_read(repo_path(args.post_netdev) if args.post_netdev else None)
    post_wifiinv = maybe_read(repo_path(args.post_wifiinv) if args.post_wifiinv else None)
    post_status = maybe_read(repo_path(args.post_status) if args.post_status else None)
    post_processes = maybe_read(repo_path(args.post_processes) if args.post_processes else None)

    checks: list[dict[str, Any]] = []
    runner_decision = runner_manifest.get("decision")
    runner_pass = runner_manifest.get("pass") is True
    add_check(checks, "runner-start-only-pass", runner_decision == "start-only-pass" and runner_pass, f"decision={runner_decision} pass={runner_manifest.get('pass')}")
    add_check(checks, "trusted-cnss-markers", bool_key(cnss_start.get("begin")) and bool_key(cnss_start.get("end")), f"begin={cnss_start.get('begin')} end={cnss_start.get('end')}")
    add_check(checks, "start-observable", bool_key(cnss_start.get("observable")) and bool_key(cnss_start.get("child_started")), f"observable={cnss_start.get('observable')} child_started={cnss_start.get('child_started')}")
    add_check(checks, "cleanup-reaped-safe", bool_key(cnss_start.get("reaped")) and bool_key(cnss_start.get("postflight_safe")), f"reaped={cnss_start.get('reaped')} postflight_safe={cnss_start.get('postflight_safe')}")

    groups = {item for item in identity_after.get("groups.values", "").split(",") if item}
    identity_ok = (
        identity_after.get("uid.effective") == "1000"
        and identity_after.get("gid.effective") == "1000"
        and {"1010", "3003", "3005"}.issubset(groups)
        and identity_after.get("cap.net_admin.effective") == "1"
    )
    add_check(checks, "identity-and-capability", identity_ok, json.dumps({
        "uid": identity_after.get("uid.effective"),
        "gid": identity_after.get("gid.effective"),
        "groups": sorted(groups),
        "cap_net_admin": identity_after.get("cap.net_admin.effective"),
    }, sort_keys=True))

    context_missing = [key for key in REQUIRED_CONTEXT_KEYS if (keyvals.get(key) != "1" if key != "helper_status" else keyvals.get(key) != "namespace-ready")]
    add_check(checks, "namespace-context", not context_missing, json.dumps({"missing_or_bad": context_missing}, sort_keys=True))
    add_check(checks, "proc-status-captured", bool(status_text) and proc_status.get("Name") == "cnss-daemon", f"Name={proc_status.get('Name')} State={proc_status.get('State')} Threads={proc_status.get('Threads')}")
    add_check(checks, "maps-captured", maps_summary["path_count"] > 0 and maps_summary["categories"]["target"] >= 1, json.dumps(maps_summary["categories"], sort_keys=True))

    pidof_absent = post_pidof_absent(post_pidof)
    no_wlan = post_no_wlan(post_netdev)
    wifiinv_no_wlan = post_wifiinv_no_wlan_like(post_wifiinv)
    cnss_process_summary = summarize_cnss_processes(parse_ps_stat_comm(post_processes)) if post_processes else None
    add_check(checks, "post-pidof-absent", pidof_absent is True, f"pidof_absent={pidof_absent}")
    add_check(checks, "post-netdev-no-wlan", no_wlan is True, f"no_wlan={no_wlan}")
    add_check(checks, "post-wifiinv-no-wlan-like", wifiinv_no_wlan is True, f"wifiinv_no_wlan_like={wifiinv_no_wlan}", severity="warning")
    if cnss_process_summary is None:
        add_check(checks, "post-cnss-process-audit-present", False, "post-process ps evidence was not provided", severity="warning")
    else:
        add_check(
            checks,
            "post-cnss-process-clean",
            bool(cnss_process_summary["clean"]),
            json.dumps({
                "target_process_count": cnss_process_summary["target_process_count"],
                "target_zombie_count": cnss_process_summary["target_zombie_count"],
                "target_running_count": cnss_process_summary["target_running_count"],
            }, sort_keys=True),
        )

    warnings: list[dict[str, str]] = []
    if any("Failed to become a perfd client" in line for line in daemon_messages):
        warnings.append({"code": "perfd-client-unavailable", "detail": "cnss-daemon reported Failed to become a perfd client"})
    if "can't create /dev/kmsg" in stderr_text:
        warnings.append({"code": "kmsg-write-denied", "detail": "helper/daemon shell path could not write /dev/kmsg"})
    if "no closing quote" in stderr_text:
        warnings.append({"code": "shell-quote-noise", "detail": "stderr contains shell quote noise from logging path"})

    critical_pass = all(item["pass"] for item in checks if item["severity"] == "critical")
    decision = "cnss-start-only-evidence-classified" if critical_pass else "cnss-start-only-evidence-incomplete"
    next_candidates = [
        "Treat any postflight CNSS target zombie as a cleanup blocker before another live CNSS retry.",
        "Classify whether perfd client absence is benign for CNSS start-only or needs a private perfd/property shim.",
        "Inspect QRTR/QMI socket/device-node interaction without scan/connect/link-up.",
        "Fix /dev/kmsg logging quote/no-permission noise in helper instrumentation before broader live operations.",
    ]
    manifest = {
        "created": now_iso(),
        "mode": "cnss-live-evidence-analysis",
        "run_dir": str(run_dir),
        "out_dir": str(out_dir),
        "decision": decision,
        "pass": critical_pass,
        "reason": "critical start-only evidence classified" if critical_pass else "one or more critical checks failed",
        "host_metadata": collect_host_metadata(),
        "runner": {
            "decision": runner_decision,
            "pass": runner_manifest.get("pass"),
            "reason": runner_manifest.get("reason"),
            "daemon_start_executed": runner_manifest.get("daemon_start_executed"),
        },
        "cnss_start": cnss_start,
        "cnss_child": cnss_child,
        "identity_before": identity_before,
        "identity_after": identity_after,
        "proc_status": proc_status,
        "maps_summary": {key: value for key, value in maps_summary.items() if key != "paths"},
        "daemon_messages": daemon_messages,
        "stderr_lines": [line for line in stderr_text.splitlines() if line.strip()],
        "postflight": {
            "pidof_absent": pidof_absent,
            "netdev_no_wlan": no_wlan,
            "wifiinv_no_wlan_like": wifiinv_no_wlan,
            "cnss_process_summary": cnss_process_summary,
            "status_contains_selftest_fail_0": "selftest:" in post_status and "fail=0" in post_status if post_status else None,
        },
        "warnings": warnings,
        "checks": checks,
        "next_candidates": next_candidates,
        "guardrails": [
            "analyzer does not execute device commands",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing authorization",
            "start-only pass is not full Wi-Fi readiness",
        ],
    }
    store = EvidenceStore(out_dir)
    store.write_json("manifest.json", manifest)
    store.write_json("cnss-keyvals.json", {
        "all": keyvals,
        "cnss_start": cnss_start,
        "cnss_child": cnss_child,
        "identity_before": identity_before,
        "identity_after": identity_after,
    })
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# CNSS Live Evidence Analysis\n\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- pass: `{manifest['pass']}`\n",
        f"- reason: `{manifest['reason']}`\n",
        f"- run_dir: `{manifest['run_dir']}`\n\n",
        "## Checks\n\n",
    ]
    for item in manifest["checks"]:
        lines.append(f"- {'PASS' if item['pass'] else 'FAIL'} `{item['name']}` ({item['severity']}): {item['detail']}\n")
    lines.append("\n## Runtime Warnings\n\n")
    if manifest["warnings"]:
        for item in manifest["warnings"]:
            lines.append(f"- WARN `{item['code']}`: {item['detail']}\n")
    else:
        lines.append("- none\n")
    lines.append("\n## Next Candidates\n\n")
    for item in manifest["next_candidates"]:
        lines.append(f"- {item}\n")
    return "".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--post-pidof", type=Path, default=Path("tmp/wifi/v257-live-post-pidof.txt"))
    parser.add_argument("--post-netdev", type=Path, default=Path("tmp/wifi/v257-live-post-proc-net-dev.txt"))
    parser.add_argument("--post-status", type=Path, default=Path("tmp/wifi/v257-live-post-status.txt"))
    parser.add_argument("--post-wifiinv", type=Path, default=Path("tmp/wifi/v257-live-post-wifiinv-full.txt"))
    parser.add_argument("--post-processes", type=Path, default=Path("tmp/wifi/v257-live-post-processes.txt"))
    return parser.parse_args()


def main() -> int:
    manifest = classify(parse_args())
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"out_dir: {manifest['out_dir']}")
    if manifest["warnings"]:
        print("warnings: " + ", ".join(item["code"] for item in manifest["warnings"]))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

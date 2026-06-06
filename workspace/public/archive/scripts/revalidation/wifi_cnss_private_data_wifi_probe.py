#!/usr/bin/env python3
"""v253 no-start private /data/vendor/wifi materialization probe."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import DEFAULT_EXPECT_VERSION, capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore
from wifi_cnss_start_only_runner import DEFAULT_HELPER_SHA256, parse_cnss_start_keys

DEFAULT_OUT_DIR = Path("tmp/wifi/v253-private-data-wifi-probe")
DEFAULT_V252_MANIFEST = Path("tmp/wifi/v252-cnss-data-wifi-surface/manifest.json")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"

DENIED_COMMAND_PATTERNS = (
    re.compile(r"--allow-cnss-start-only", re.IGNORECASE),
    re.compile(r"\bcnss_diag\b", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set_network|enable_network)\b", re.IGNORECASE),
    re.compile(r"\b(?:wpa_supplicant|wificond|hostapd|android\.hardware\.wifi)\b", re.IGNORECASE),
)

LIVE_COMMANDS: tuple[tuple[str, list[str], float, bool], ...] = (
    ("version", ["version"], 10.0, True),
    ("status", ["status"], 10.0, True),
    ("pidof-cnss-daemon", ["run", "/cache/bin/toybox", "pidof", "cnss-daemon"], 10.0, False),
    ("sha-helper", ["run", "/cache/bin/toybox", "sha256sum", DEFAULT_HELPER], 10.0, True),
    ("stat-real-data-vendor-wifi", ["stat", "/data/vendor/wifi"], 10.0, False),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def load_manifest(path: Path) -> dict[str, Any]:
    full = repo_path(path)
    if not full.exists():
        return {"missing": True, "path": str(full), "decision": "missing", "pass": False}
    data = json.loads(full.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full)
    return data


def helper_command(args: argparse.Namespace) -> list[str]:
    return [
        "run",
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        "cnss-start-only",
        "--null-device-mode",
        "dev-null-selinux",
        "--data-wifi-mode",
        "private-empty",
        "--vndk-apex-alias-mode",
        "v30-to-current",
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        "/cache/bin/a90_real_ld.config.txt",
        "--apex-libraries-source",
        "/cache/bin/a90_real_apex.libraries.config.txt",
        "--timeout-sec",
        str(args.helper_timeout_sec),
    ]


def validate_no_denied_commands(args: argparse.Namespace) -> None:
    text = "\n".join(" ".join(argv) for _, argv, _, _ in LIVE_COMMANDS)
    text += "\n" + " ".join(helper_command(args))
    for pattern in DENIED_COMMAND_PATTERNS:
        if pattern.search(text):
            raise AssertionError(f"denied command pattern present: {pattern.pattern}")


def capture_commands(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    captures: list[dict[str, Any]] = []
    store.mkdir("captures")
    for name, command, timeout, required in LIVE_COMMANDS:
        actual_command = [args.helper if part == DEFAULT_HELPER else part for part in command]
        capture = run_capture(args, name, actual_command, timeout=timeout)
        store.write_text(f"captures/{safe_name(name)}.txt", capture.text if capture.text else capture.error + "\n")
        item = capture_to_manifest(capture)
        item["required"] = required
        captures.append(item)
    helper_capture = run_capture(args, "helper-private-data-wifi-noallow", helper_command(args), timeout=args.timeout + args.helper_timeout_sec + 10.0)
    store.write_text("helper-private-data-wifi-noallow.txt", helper_capture.text if helper_capture.text else helper_capture.error + "\n")
    helper_item = capture_to_manifest(helper_capture)
    helper_item["required"] = True
    helper_item["cnss_start"] = parse_cnss_start_keys(helper_capture.text)
    captures.append(helper_item)
    return captures


def by_name(captures: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["name"]): item for item in captures}


def capture_ok(captures: dict[str, dict[str, Any]], name: str) -> bool:
    item = captures.get(name, {})
    return bool(item.get("ok")) and item.get("rc") == 0 and item.get("status") == "ok"


def capture_rc(captures: dict[str, dict[str, Any]], name: str) -> int | None:
    value = captures.get(name, {}).get("rc")
    return value if isinstance(value, int) else None


def capture_text(captures: dict[str, dict[str, Any]], name: str) -> str:
    item = captures.get(name, {})
    return strip_cmdv1_text(str(item.get("text", ""))) if item.get("text") else ""


def context_value(text: str, key: str) -> str:
    prefix = key + "="
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(prefix):
            return line[len(prefix):]
    return ""


def build_checks(args: argparse.Namespace, v252: dict[str, Any], captures: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    helper = captures.get("helper-private-data-wifi-noallow", {})
    helper_text = str(helper.get("text", ""))
    helper_keys = helper.get("cnss_start", {})
    sha_text = capture_text(captures, "sha-helper")
    return [
        {"name": "v252-prerequisite", "pass": bool(v252.get("pass")) and v252.get("decision") == "cnss-data-wifi-surface-missing", "detail": v252.get("decision", "missing")},
        {"name": "required-control-captures", "pass": all(capture_ok(captures, name) for name, _, _, required in LIVE_COMMANDS if required), "detail": "required cmdv1 captures returned rc=0/status=ok"},
        {"name": "helper-sha", "pass": args.helper_sha256 in sha_text, "detail": args.helper_sha256},
        {"name": "cnss-daemon-absent", "pass": capture_rc(captures, "pidof-cnss-daemon") == 1, "detail": "pidof cnss-daemon returns rc=1"},
        {"name": "real-data-wifi-still-missing", "pass": capture_rc(captures, "stat-real-data-vendor-wifi") == -2, "detail": "real /data/vendor/wifi remains absent"},
        {"name": "helper-namespace-ready", "pass": "helper_status=namespace-ready" in helper_text, "detail": "helper namespace-ready"},
        {"name": "helper-noallow-guard", "pass": helper_keys.get("result") == "start-only-blocked" and helper_keys.get("exec_attempted") == "0", "detail": json.dumps(helper_keys, sort_keys=True)},
        {"name": "private-data-wifi", "pass": context_value(helper_text, "context.data_vendor_wifi.exists") == "1" and context_value(helper_text, "context.data_vendor_wifi.type") == "directory", "detail": "private /data/vendor/wifi directory exists"},
        {"name": "private-data-wifi-sockets", "pass": context_value(helper_text, "context.data_vendor_wifi_sockets.exists") == "1" and context_value(helper_text, "context.data_vendor_wifi_sockets.type") == "directory", "detail": "private /data/vendor/wifi/sockets directory exists"},
        {"name": "private-data-wifi-owner", "pass": context_value(helper_text, "context.data_vendor_wifi.uid") == "1000" and context_value(helper_text, "context.data_vendor_wifi.gid") == "1010", "detail": "private /data/vendor/wifi owner system:wifi"},
    ]


def classify(checks: list[dict[str, Any]]) -> tuple[bool, str, str]:
    if all(item["pass"] for item in checks):
        return True, "private-data-wifi-materialization-pass", "helper private namespace can materialize data Wi-Fi tree without executing target"
    return False, "private-data-wifi-materialization-blocked", "required private data Wi-Fi materialization check failed"


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[i["name"], "PASS" if i["pass"] else "FAIL", i["detail"]] for i in manifest["checks"]]
    return "".join([
        "# v253 Private Data Wi-Fi Materialization\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- reason: `{manifest['reason']}`\n",
        "- daemon start: `not executed`\n",
        f"- output: `{manifest['out_dir']}`\n\n",
        "## Checks\n\n",
        markdown_table(["check", "result", "detail"], rows),
        "\n\n## Guardrails\n\n",
        "- Real `/data/vendor/wifi` was not created.\n",
        "- No userdata mount/remount or ownership/permission mutation.\n",
        "- No `cnss-daemon` execution.\n",
        "- No Wi-Fi scan/connect/link-up action.\n",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v252-manifest", type=Path, default=DEFAULT_V252_MANIFEST)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-timeout-sec", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_no_denied_commands(args)
    store = EvidenceStore(repo_path(args.out_dir))
    v252 = load_manifest(args.v252_manifest)
    captures_list = capture_commands(args, store)
    captures = by_name(captures_list)
    checks = build_checks(args, v252, captures)
    pass_ok, decision, reason = classify(checks)
    manifest = {
        "created": now_iso(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(repo_path(args.out_dir)),
        "daemon_start_executed": False,
        "host_metadata": collect_host_metadata(),
        "checks": checks,
        "captures": captures_list,
        "helper_sha256": args.helper_sha256,
        "guardrails": [
            "no real /data/vendor/wifi creation",
            "no userdata mount/remount",
            "no cnss-daemon execution",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
    }
    store.write_json("live-captures.json", {"captures": captures_list})
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"out_dir: {repo_path(args.out_dir)}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

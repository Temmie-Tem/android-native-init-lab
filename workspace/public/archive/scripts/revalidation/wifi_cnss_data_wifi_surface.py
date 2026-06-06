#!/usr/bin/env python3
"""v252 no-start /data/vendor/wifi runtime surface classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import DEFAULT_EXPECT_VERSION, capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore

DEFAULT_OUT_DIR = Path("tmp/wifi/v252-cnss-data-wifi-surface")
DEFAULT_V251_MANIFEST = Path("tmp/wifi/v251-cnss-property-surface/manifest.json")
DEFAULT_CNSS_DAEMON = Path("tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon")

DENIED_COMMAND_PATTERNS = (
    re.compile(r"\b/vendor/bin/cnss-daemon\b.*\b(?:-n|-l)\b", re.IGNORECASE),
    re.compile(r"\bcnss_diag\b.*\b(?:-q|-f|-t)\b", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set_network|enable_network)\b", re.IGNORECASE),
    re.compile(r"\b(?:wpa_supplicant|wificond|hostapd|android\.hardware\.wifi)\b", re.IGNORECASE),
    re.compile(r"\b(?:mkdir|mount|umount|chown|chmod)\b.*\b/data/vendor/wifi\b", re.IGNORECASE),
)

LIVE_COMMANDS: tuple[tuple[str, list[str], float, bool], ...] = (
    ("version", ["version"], 10.0, True),
    ("status", ["status"], 10.0, True),
    ("pidof-cnss-daemon", ["run", "/cache/bin/toybox", "pidof", "cnss-daemon"], 10.0, False),
    ("stat-data", ["stat", "/data"], 10.0, True),
    ("stat-data-vendor", ["stat", "/data/vendor"], 10.0, False),
    ("stat-data-vendor-wifi", ["stat", "/data/vendor/wifi"], 10.0, False),
    ("stat-data-vendor-wifi-sockets", ["stat", "/data/vendor/wifi/sockets"], 10.0, False),
    ("ls-data-wifi-path", ["run", "/cache/bin/toybox", "ls", "-ld", "/data", "/data/vendor", "/data/vendor/wifi", "/data/vendor/wifi/sockets"], 10.0, False),
    ("find-data-wifi-cnss", ["run", "/cache/bin/toybox", "find", "/data", "-maxdepth", "4", "-name", "*wifi*", "-o", "-name", "*cnss*", "-o", "-name", "*socket*"], 20.0, False),
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


def run_host(command: list[str], timeout: int = 20) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=repo_path(Path(".")),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return {"command": command, "rc": result.returncode, "text": result.stdout, "error": ""}
    except Exception as exc:  # noqa: BLE001 - evidence collector preserves failure
        return {"command": command, "rc": None, "text": "", "error": str(exc)}


def data_wifi_strings(binary: Path) -> tuple[dict[str, Any], list[str]]:
    result = run_host(["strings", "-a", str(binary)])
    values: list[str] = []
    if result["rc"] == 0:
        for line in result["text"].splitlines():
            if "/data/vendor/wifi" in line or "cnss_user_socket" in line:
                values.append(line.strip())
    return result, sorted(set(v for v in values if v))


def validate_no_denied_commands() -> None:
    command_text = "\n".join(" ".join(argv) for _, argv, _, _ in LIVE_COMMANDS)
    for pattern in DENIED_COMMAND_PATTERNS:
        if pattern.search(command_text):
            raise AssertionError(f"denied command pattern present: {pattern.pattern}")


def capture_commands(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    captures: list[dict[str, Any]] = []
    store.mkdir("captures")
    for name, command, timeout, required in LIVE_COMMANDS:
        capture = run_capture(args, name, command, timeout=timeout)
        store.write_text(f"captures/{safe_name(name)}.txt", capture.text if capture.text else capture.error + "\n")
        item = capture_to_manifest(capture)
        item["required"] = required
        captures.append(item)
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


def build_checks(v251: dict[str, Any], captures: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "name": "v251-prerequisite",
            "pass": bool(v251.get("pass")) and v251.get("decision") == "cnss-property-read-only-surface",
            "detail": v251.get("decision", "missing"),
        },
        {
            "name": "required-control-captures",
            "pass": all(capture_ok(captures, name) for name, _, _, required in LIVE_COMMANDS if required),
            "detail": "required cmdv1 captures returned rc=0/status=ok",
        },
        {
            "name": "cnss-daemon-absent",
            "pass": capture_rc(captures, "pidof-cnss-daemon") == 1,
            "detail": "pidof cnss-daemon returns rc=1",
        },
        {"name": "data-root-present", "pass": capture_ok(captures, "stat-data"), "detail": "/data exists"},
        {"name": "data-vendor-present", "pass": capture_ok(captures, "stat-data-vendor"), "detail": "/data/vendor exists"},
        {"name": "data-vendor-wifi-present", "pass": capture_ok(captures, "stat-data-vendor-wifi"), "detail": "/data/vendor/wifi exists"},
        {"name": "data-vendor-wifi-sockets-present", "pass": capture_ok(captures, "stat-data-vendor-wifi-sockets"), "detail": "/data/vendor/wifi/sockets exists"},
    ]


def classify(checks: list[dict[str, Any]]) -> tuple[bool, str, str]:
    hard = {"v251-prerequisite", "required-control-captures", "cnss-daemon-absent", "data-root-present"}
    failed_hard = [item for item in checks if item["name"] in hard and not item["pass"]]
    if failed_hard:
        return False, "cnss-data-wifi-surface-blocked", "hard read-only data surface check failed: " + ", ".join(item["name"] for item in failed_hard)
    needed = {"data-vendor-present", "data-vendor-wifi-present", "data-vendor-wifi-sockets-present"}
    missing = [item for item in checks if item["name"] in needed and not item["pass"]]
    if missing:
        return True, "cnss-data-wifi-surface-missing", "runtime data Wi-Fi path is absent without mutation: " + ", ".join(item["name"] for item in missing)
    return True, "cnss-data-wifi-surface-ready", "runtime data Wi-Fi path exists read-only"


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[i["name"], "PASS" if i["pass"] else "FAIL", i["detail"]] for i in manifest["checks"]]
    string_rows = [[item] for item in manifest["cnss_data_wifi_strings"]]
    return "".join([
        "# v252 CNSS Data Wi-Fi Runtime Surface\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- reason: `{manifest['reason']}`\n",
        "- daemon start: `not executed`\n",
        f"- output: `{manifest['out_dir']}`\n\n",
        "## Checks\n\n",
        markdown_table(["check", "result", "detail"], check_rows),
        "\n\n## CNSS Data Wi-Fi Strings\n\n",
        markdown_table(["string"], string_rows or [["none"]]),
        "\n\n## Guardrails\n\n",
        "- No `/data/vendor/wifi` directory was created.\n",
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
    parser.add_argument("--v251-manifest", type=Path, default=DEFAULT_V251_MANIFEST)
    parser.add_argument("--binary", type=Path, default=DEFAULT_CNSS_DAEMON)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_no_denied_commands()
    store = EvidenceStore(repo_path(args.out_dir))
    v251 = load_manifest(args.v251_manifest)
    strings_result, cnss_data_strings = data_wifi_strings(repo_path(args.binary))
    captures_list = capture_commands(args, store)
    captures = by_name(captures_list)
    checks = build_checks(v251, captures)
    pass_ok, decision, reason = classify(checks)
    manifest = {
        "created": now_iso(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(repo_path(args.out_dir)),
        "daemon_start_executed": False,
        "host_metadata": collect_host_metadata(),
        "v251_decision": v251.get("decision", "missing"),
        "cnss_binary": str(repo_path(args.binary)),
        "cnss_strings_rc": strings_result["rc"],
        "cnss_data_wifi_strings": cnss_data_strings,
        "checks": checks,
        "captures": captures_list,
        "data_listing": capture_text(captures, "ls-data-wifi-path"),
        "find_data_hints": capture_text(captures, "find-data-wifi-cnss"),
        "guardrails": [
            "no /data/vendor/wifi creation",
            "no userdata mount/remount",
            "no cnss-daemon execution",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
    }
    store.write_json("live-captures.json", {"captures": captures_list})
    store.write_text("cnss-data-wifi-strings.txt", "\n".join(cnss_data_strings) + ("\n" if cnss_data_strings else ""))
    store.write_json("data-wifi-surface.json", manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"out_dir: {repo_path(args.out_dir)}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

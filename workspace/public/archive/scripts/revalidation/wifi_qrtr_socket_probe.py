#!/usr/bin/env python3
"""v250 no-start AF_QIPCRTR socket probe runner."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import DEFAULT_EXPECT_VERSION, capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore

DEFAULT_OUT_DIR = Path("tmp/wifi/v250-qrtr-socket-probe")
DEFAULT_V249_MANIFEST = Path("tmp/wifi/v249-cnss-runtime-gap-classifier/manifest.json")
DEFAULT_HELPER = "/cache/bin/a90_qrtr_probe"
DEFAULT_HELPER_SHA256 = "92500fa51a7c910877d59b704210b915dfeed4abb0daca36d894b10f319be8a5"

REFERENCE_URLS = {
    "linux_qrtr_kconfig": "https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/refs/heads/master/net/qrtr/Kconfig",
    "linux_qrtr_af": "https://codebrowser.dev/linux/linux/net/qrtr/af_qrtr.c.html",
}

DENIED_COMMAND_PATTERNS = (
    re.compile(r"\b/vendor/bin/cnss-daemon\b.*\b(?:-n|-l)\b", re.IGNORECASE),
    re.compile(r"\bcnss_diag\b.*\b(?:-q|-f|-t)\b", re.IGNORECASE),
    re.compile(r"--allow-cnss-start-only", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set_network|enable_network)\b", re.IGNORECASE),
    re.compile(r"\b(?:wpa_supplicant|wificond|hostapd|android\.hardware\.wifi)\b", re.IGNORECASE),
    re.compile(r"\b(?:dhcpcd|udhcpc|dnsmasq)\b", re.IGNORECASE),
    re.compile(r"\b/sys/bus/platform/drivers/icnss/(?:bind|unbind)\b", re.IGNORECASE),
    re.compile(r"\bsetprop\b|\bctl\.start\b|\bclass_start\b", re.IGNORECASE),
)

LIVE_COMMANDS: tuple[tuple[str, list[str], float, bool], ...] = (
    ("version", ["version"], 10.0, True),
    ("status", ["status"], 10.0, True),
    ("pidof-cnss-daemon", ["run", "/cache/bin/toybox", "pidof", "cnss-daemon"], 10.0, False),
    ("cat-proc-net-protocols", ["cat", "/proc/net/protocols"], 10.0, True),
    ("cat-proc-net-netlink", ["cat", "/proc/net/netlink"], 10.0, False),
    ("stat-helper", ["stat", DEFAULT_HELPER], 10.0, True),
    ("sha-helper", ["run", "/cache/bin/toybox", "sha256sum", DEFAULT_HELPER], 10.0, True),
    ("qrtr-probe", ["run", DEFAULT_HELPER], 10.0, True),
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


def validate_no_denied_commands() -> None:
    command_text = "\n".join(" ".join(argv) for _, argv, _, _ in LIVE_COMMANDS)
    for pattern in DENIED_COMMAND_PATTERNS:
        if pattern.search(command_text):
            raise AssertionError(f"denied command pattern present: {pattern.pattern}")


def capture_commands(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    captures: list[dict[str, Any]] = []
    store.mkdir("captures")
    for name, command, timeout, required in LIVE_COMMANDS:
        actual_command = [args.helper if part == DEFAULT_HELPER else part for part in command]
        capture = run_capture(args, name, actual_command, timeout=timeout)
        store.write_text(f"captures/{safe_name(name)}.txt", capture.text if capture.text else capture.error + "\n")
        if name == "qrtr-probe":
            store.write_text("qrtr-probe.txt", capture.text if capture.text else capture.error + "\n")
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


def parse_probe_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("qrtr_probe.") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        keys[key.removeprefix("qrtr_probe.")] = value
    return keys


def build_checks(args: argparse.Namespace, v249: dict[str, Any], captures: dict[str, dict[str, Any]], probe_keys: dict[str, str]) -> list[dict[str, Any]]:
    protocols = capture_text(captures, "cat-proc-net-protocols")
    sha_text = capture_text(captures, "sha-helper")
    return [
        {
            "name": "v249-prerequisite",
            "pass": bool(v249.get("pass")) and v249.get("decision") == "cnss-runtime-gaps-classified",
            "detail": v249.get("decision", "missing"),
        },
        {
            "name": "required-control-captures",
            "pass": all(capture_ok(captures, name) for name, _, _, required in LIVE_COMMANDS if required),
            "detail": "required cmdv1 captures returned rc=0/status=ok",
        },
        {
            "name": "helper-sha",
            "pass": args.helper_sha256 in sha_text,
            "detail": args.helper_sha256,
        },
        {
            "name": "cnss-daemon-absent",
            "pass": capture_rc(captures, "pidof-cnss-daemon") == 1,
            "detail": "pidof cnss-daemon returns rc=1",
        },
        {
            "name": "qipcrtr-protocol-listed",
            "pass": bool(re.search(r"^QIPCRTR\s", protocols, re.MULTILINE)),
            "detail": "QIPCRTR present in /proc/net/protocols",
        },
        {
            "name": "qrtr-socket-open",
            "pass": probe_keys.get("socket.rc") == "0",
            "detail": json.dumps({k: probe_keys[k] for k in sorted(probe_keys) if k.startswith("socket") or k in {"status", "af"}}, sort_keys=True),
        },
        {
            "name": "qrtr-local-bind",
            "pass": probe_keys.get("status") == "bind-pass",
            "detail": json.dumps({k: probe_keys[k] for k in sorted(probe_keys) if k.startswith("bind") or k == "status"}, sort_keys=True),
        },
        {
            "name": "no-send-connect",
            "pass": probe_keys.get("send_attempted") == "0" and probe_keys.get("connect_attempted") == "0",
            "detail": "helper reports no send/connect attempts",
        },
    ]


def classify(checks: list[dict[str, Any]], probe_keys: dict[str, str]) -> tuple[bool, str, str]:
    hard = {"v249-prerequisite", "required-control-captures", "helper-sha", "cnss-daemon-absent", "qipcrtr-protocol-listed", "qrtr-socket-open", "no-send-connect"}
    failed_hard = [item for item in checks if item["name"] in hard and not item["pass"]]
    if failed_hard:
        return False, "qrtr-socket-blocked", "hard QRTR no-start check failed: " + ", ".join(item["name"] for item in failed_hard)
    if probe_keys.get("status") == "bind-pass":
        return True, "qrtr-socket-local-bind-pass", "AF_QIPCRTR socket opened and local ephemeral bind worked without send/connect"
    return True, "qrtr-socket-open-only", "AF_QIPCRTR socket opened but local bind did not pass"


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[i["name"], "PASS" if i["pass"] else "FAIL", i["detail"]] for i in manifest["checks"]]
    probe_rows = [[k, v] for k, v in sorted(manifest["probe_keys"].items())]
    ref_rows = [[k, v] for k, v in manifest["references"].items()]
    return "".join(
        [
            "# v250 QRTR Socket No-Start Probe\n\n",
            f"- generated: `{manifest['created']}`\n",
            f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
            f"- decision: `{manifest['decision']}`\n",
            f"- reason: `{manifest['reason']}`\n",
            "- daemon start: `not executed`\n",
            f"- output: `{manifest['out_dir']}`\n\n",
            "## Checks\n\n",
            markdown_table(["check", "result", "detail"], check_rows),
            "\n\n## Probe Keys\n\n",
            markdown_table(["key", "value"], probe_rows[:80]),
            "\n\n## References\n\n",
            markdown_table(["reference", "url"], ref_rows),
            "\n\n## Guardrails\n\n",
            "- No `cnss-daemon` or `cnss_diag` process was started.\n",
            "- QRTR helper did not send payloads or connect to remote services.\n",
            "- No Wi-Fi scan/connect/link-up/credential/DHCP/routing action was attempted.\n",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v249-manifest", type=Path, default=DEFAULT_V249_MANIFEST)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_no_denied_commands()
    store = EvidenceStore(repo_path(args.out_dir))
    v249 = load_manifest(args.v249_manifest)
    captures_list = capture_commands(args, store)
    captures = by_name(captures_list)
    probe_text = capture_text(captures, "qrtr-probe")
    probe_keys = parse_probe_keys(probe_text)
    checks = build_checks(args, v249, captures, probe_keys)
    pass_ok, decision, reason = classify(checks, probe_keys)
    manifest = {
        "created": now_iso(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(repo_path(args.out_dir)),
        "daemon_start_executed": False,
        "host_metadata": collect_host_metadata(),
        "references": REFERENCE_URLS,
        "checks": checks,
        "probe_keys": probe_keys,
        "captures": captures_list,
        "guardrails": [
            "no cnss-daemon execution",
            "no cnss_diag execution",
            "no QRTR send/connect/nameservice packet",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no rfkill write, ICNSS bind/unbind, firmware mutation, or Android partition write",
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

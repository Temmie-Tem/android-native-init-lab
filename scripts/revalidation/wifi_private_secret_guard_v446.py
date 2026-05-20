#!/usr/bin/env python3
"""V446 Wi-Fi private policy and secret guard.

V446 is host-side only.  It scans repository-visible files for accidental
Wi-Fi private policy files, raw target identifiers, and credential material
before V445 live explicit scan/connect is allowed to proceed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v446-wifi-private-secret-guard")
MAX_FILE_BYTES = 2 * 1024 * 1024
REQUIRED_GITIGNORE_PATTERNS = [
    ".env",
    ".env.*",
    "!.env.example",
    "!.env.*.example",
    "wifi-target-policy.private.json",
    "wifi-target-policy.local.json",
    "WIFI_TARGET_ALLOWLIST*.private.json",
    "WIFI_TARGET_ALLOWLIST*.local.json",
]
TEXT_EXTENSIONS_FOR_JSON_FIELDS = {
    ".conf",
    ".env",
    ".json",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
}
KNOWN_SYNTHETIC_VALUES = {
    "12345678",
    "codex-test-network",
}

ENV_ASSIGN_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:export\s+)?(?P<name>A90_WIFI_(?:SSID|PSK))="
    r"(?:'(?P<sq>[^']*)'|\"(?P<dq>[^\"]*)\"|(?P<bare>[^\s\\;#]+))"
)
JSON_SECRET_FIELD_RE = re.compile(
    r'"(?P<key>ssid|bssid|password|passphrase|psk|pre_shared_key|targetConfigKey)"'
    r"\s*:\s*(?P<value>\"[^\"\n]{0,160}\"|[^,\s}\]]{1,160})",
    re.IGNORECASE,
)
CONNECT_RE = re.compile(r"\bcmd\s+wifi\s+connect-network\b(?P<args>[^\n`]*)", re.IGNORECASE)
CONNECT_SECURITY_RE = re.compile(r"\b(open|owe|wpa2|wpa3)\b", re.IGNORECASE)
CONNECTED_SSID_RE = re.compile(r'Wifi is connected to "(?P<value>[^"\n]+)"', re.IGNORECASE)
SSID_EQUALS_RE = re.compile(r'(?<![A-Za-z0-9_])SSID="(?P<value>[^"\n]+)"')
BRACKET_SSID_RE = re.compile(r"\[(?:SSID|BSSID)\]:\s*\[(?P<value>[^\]]+)\]", re.IGNORECASE)
BSSID_EQUALS_RE = re.compile(r"\bBSSID=(?P<value>(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2})")
MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")
PRIVATE_PATH_RE = re.compile(
    r"(?i)(^|/)(?:wifi-target-policy\.(?:private|local)\.json|"
    r"WIFI_TARGET_ALLOWLIST.*\.(?:private|local)\.json|"
    r"wpa_supplicant\.conf|\.env(?:\..*)?)$"
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--include-untracked", action="store_true")
    parser.add_argument("--max-findings", type=int, default=200)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def run_git(args: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_path("."),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
    return [item for item in result.stdout.decode("utf-8", errors="surrogateescape").split("\0") if item]


def candidate_paths(include_untracked: bool) -> tuple[list[dict[str, str]], list[str]]:
    rows: list[dict[str, str]] = []
    errors: list[str] = []
    try:
        rows.extend({"path": item, "source": "tracked"} for item in run_git(["ls-files", "-z"]))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"tracked file listing failed: {exc}")
    if include_untracked:
        try:
            rows.extend({"path": item, "source": "untracked"} for item in run_git(["ls-files", "--others", "--exclude-standard", "-z"]))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"untracked file listing failed: {exc}")
    unique: dict[str, dict[str, str]] = {}
    for row in rows:
        unique.setdefault(row["path"], row)
    return sorted(unique.values(), key=lambda row: row["path"]), errors


def normalize_value(value: str) -> str:
    return value.strip().strip("'\"").strip()


def placeholder_value(value: str) -> bool:
    value = normalize_value(value)
    lowered = value.lower()
    return (
        not value
        or value in KNOWN_SYNTHETIC_VALUES
        or value.startswith("$A90_WIFI_")
        or value.startswith("env:A90_WIFI_")
        or (value.startswith("<") and value.endswith(">"))
        or lowered in {"-", "none", "null", "redacted", "<redacted>", "placeholder"}
    )


def placeholder_mac(value: str) -> bool:
    octets = value.lower().split(":")
    return len(octets) == 6 and (len(set(octets)) == 1 and octets[0] in {"00", "ff"})


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def line_at(text: str, offset: int) -> str:
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    if end < 0:
        end = len(text)
    return text[start:end]


def add_finding(
    findings: list[dict[str, Any]],
    path: str,
    source: str,
    line: int,
    rule: str,
    detail: str,
    max_findings: int,
) -> None:
    if len(findings) >= max_findings:
        return
    findings.append(
        {
            "path": path,
            "source": source,
            "line": line,
            "rule": rule,
            "detail": detail,
        }
    )


def gitignore_findings(max_findings: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = repo_path(".gitignore")
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    present = {line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")}
    missing = [pattern for pattern in REQUIRED_GITIGNORE_PATTERNS if pattern not in present]
    findings: list[dict[str, Any]] = []
    for pattern in missing:
        add_finding(findings, ".gitignore", "tracked", 1, "missing-ignore-pattern", f"missing required ignore pattern {pattern}", max_findings)
    return findings, {"required": REQUIRED_GITIGNORE_PATTERNS, "missing": missing}


def text_suffix(path: str) -> str:
    name = Path(path).name
    if name.startswith(".env"):
        return ".env"
    return Path(path).suffix.lower()


def scan_path(row: dict[str, str], max_findings: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rel = row["path"]
    source = row["source"]
    path = repo_path(rel)
    findings: list[dict[str, Any]] = []
    summary = {"path": rel, "source": source, "read": False, "skipped": ""}

    if PRIVATE_PATH_RE.search(rel):
        add_finding(findings, rel, source, 1, "private-secret-path", "private Wi-Fi policy/env file is repository-visible", max_findings)

    if not path.is_file():
        summary["skipped"] = "not-file"
        return findings, summary
    try:
        data = path.read_bytes()
    except Exception as exc:  # noqa: BLE001
        summary["skipped"] = f"read-error: {exc}"
        return findings, summary
    if len(data) > MAX_FILE_BYTES:
        summary["skipped"] = f"too-large: {len(data)}"
        return findings, summary
    if b"\0" in data:
        summary["skipped"] = "binary"
        return findings, summary

    text = data.decode("utf-8", errors="replace")
    summary["read"] = True
    for match in ENV_ASSIGN_RE.finditer(text):
        value = match.group("sq") if match.group("sq") is not None else match.group("dq") if match.group("dq") is not None else match.group("bare") or ""
        if not placeholder_value(value):
            add_finding(findings, rel, source, line_number(text, match.start()), "wifi-env-assignment", f"{match.group('name')} assignment uses a non-placeholder value", max_findings)

    for match in CONNECT_RE.finditer(text):
        window = text[match.start() : min(len(text), match.end() + 160)]
        if not CONNECT_SECURITY_RE.search(window):
            continue
        if any(token in window for token in ("$A90_WIFI_SSID", "<ssid>", "<passphrase>", "env placeholder", "env-derived")):
            continue
        if "appears without env placeholder" in window:
            continue
        args = match.group("args")
        if "$A90_WIFI_SSID" not in args and "<" not in args and "env-derived" not in args:
            add_finding(findings, rel, source, line_number(text, match.start()), "raw-connect-network-command", "cmd wifi connect-network appears without env placeholder", max_findings)

    for pattern, rule, detail in (
        (CONNECTED_SSID_RE, "raw-connected-ssid", "Android Wi-Fi status appears to contain a raw connected SSID"),
        (SSID_EQUALS_RE, "raw-ssid-status", "SSID status appears to contain a raw SSID"),
        (BRACKET_SSID_RE, "raw-bracketed-ssid-bssid", "bracketed SSID/BSSID output appears to contain a raw value"),
    ):
        for match in pattern.finditer(text):
            if "re.compile(" in line_at(text, match.start()):
                continue
            if not placeholder_value(match.group("value")):
                add_finding(findings, rel, source, line_number(text, match.start()), rule, detail, max_findings)

    for match in BSSID_EQUALS_RE.finditer(text):
        if not placeholder_mac(match.group("value")):
            add_finding(findings, rel, source, line_number(text, match.start()), "raw-bssid-status", "BSSID status contains a raw MAC address", max_findings)

    for match in MAC_RE.finditer(text):
        if placeholder_mac(match.group(0)):
            continue
        start = max(0, match.start() - 80)
        end = min(len(text), match.end() + 80)
        context = text[start:end].lower()
        if any(term in context for term in ("bssid", "ssid", "wifi", "wlan", "scan")):
            add_finding(findings, rel, source, line_number(text, match.start()), "raw-wifi-adjacent-mac", "Wi-Fi-adjacent text contains a raw MAC address", max_findings)

    if text_suffix(rel) in TEXT_EXTENSIONS_FOR_JSON_FIELDS:
        for match in JSON_SECRET_FIELD_RE.finditer(text):
            value = match.group("value")
            if not placeholder_value(value):
                add_finding(findings, rel, source, line_number(text, match.start()), "raw-wifi-json-field", f"raw Wi-Fi JSON field {match.group('key')} is forbidden", max_findings)

    return findings, summary


def classify(command: str, findings: list[dict[str, Any]], listing_errors: list[str]) -> dict[str, Any]:
    if command == "plan":
        return {
            "decision": "v446-wifi-private-secret-guard-plan-ready",
            "pass": True,
            "reason": "private Wi-Fi secret guard plan generated",
            "next_gate": "run V446 guard before V443/V444/V445 live credential flow",
        }
    if listing_errors:
        return {
            "decision": "v446-wifi-private-secret-guard-scan-error",
            "pass": False,
            "reason": "repository file listing failed",
            "next_gate": "fix git listing errors before private Wi-Fi credential work",
        }
    if findings:
        return {
            "decision": "v446-wifi-private-secret-guard-findings",
            "pass": False,
            "reason": "repository-visible Wi-Fi private data risks were found",
            "next_gate": "remove or ignore private data before V443/V444/V445 live flow",
        }
    return {
        "decision": "v446-wifi-private-secret-guard-pass",
        "pass": True,
        "reason": "no repository-visible Wi-Fi private policy or credential leaks were found",
        "next_gate": "local private env can be materialized through V443, then V444/V445 can proceed",
    }


def guardrails() -> list[str]:
    return [
        "host-side repository scan only",
        "does not read ignored tmp Wi-Fi evidence or operator shell history",
        "does not print secret values in findings",
        "blocks private policy/env files if they become repository-visible",
        "runs before V443/V444/V445 live explicit scan/connect",
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    scan = manifest.get("scan") or {}
    findings = manifest.get("findings") or []
    finding_rows = [
        [item["path"], item["source"], str(item["line"]), item["rule"], item["detail"]]
        for item in findings[:50]
    ]
    ignore = manifest.get("gitignore") or {}
    return "\n".join(
        [
            "# V446 Wi-Fi Private Secret Guard",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_gate: `{manifest['classification']['next_gate']}`",
            f"- scanned_paths: `{scan.get('path_count', 0)}`",
            f"- text_paths_read: `{scan.get('text_paths_read', 0)}`",
            f"- finding_count: `{len(findings)}`",
            f"- missing_ignore_patterns: `{len(ignore.get('missing') or [])}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Findings",
            "",
            markdown_table(["path", "source", "line", "rule", "detail"], finding_rows if finding_rows else [["-", "-", "-", "-", "-"]]),
            "",
            "## Guardrails",
            "",
            *[f"- {item}" for item in manifest["guardrails"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    listing_errors: list[str] = []
    path_rows: list[dict[str, str]] = []
    scan_rows: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    gitignore: dict[str, Any] = {"required": REQUIRED_GITIGNORE_PATTERNS, "missing": []}

    if args.command == "run":
        ignore_findings, gitignore = gitignore_findings(args.max_findings)
        findings.extend(ignore_findings)
        path_rows, listing_errors = candidate_paths(args.include_untracked)
        for row in path_rows:
            path_findings, summary = scan_path(row, args.max_findings)
            scan_rows.append(summary)
            findings.extend(path_findings)
            if len(findings) >= args.max_findings:
                break

    classification = classify(args.command, findings, listing_errors)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "host": collect_host_metadata(),
        "classification": classification,
        "gitignore": gitignore,
        "scan": {
            "include_untracked": bool(args.include_untracked),
            "path_count": len(path_rows),
            "text_paths_read": sum(1 for row in scan_rows if row.get("read")),
            "listing_errors": listing_errors,
            "max_findings": args.max_findings,
        },
        "findings": findings,
        "guardrails": guardrails(),
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"findings: {len(findings)}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""v251 host-only CNSS property surface classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore

DEFAULT_OUT_DIR = Path("tmp/wifi/v251-cnss-property-surface")
DEFAULT_V250_MANIFEST = Path("tmp/wifi/v250-qrtr-socket-probe/manifest.json")
DEFAULT_CNSS_DAEMON = Path("tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon")

PROPERTY_READ_SYMBOL_RE = re.compile(r"\b(property_get(?:_int32)?|__system_property_get|__system_property_find|__system_property_read(?:_callback)?)\b")
PROPERTY_WRITE_SYMBOL_RE = re.compile(r"\b(property_set|__system_property_set|__system_property_update|__system_property_add|SetProperty)\b")
PROPERTY_STRING_RE = re.compile(r"(?:^|[^A-Za-z0-9_./-])((?:ro|persist|vendor|wlan|wifi|ctl)\.[A-Za-z0-9_.-]+|[A-Za-z0-9_.-]*cnss[A-Za-z0-9_.-]*)", re.IGNORECASE)

REFERENCE_URLS = {
    "android_property_service": "https://android.googlesource.com/platform/system/core/+/refs/heads/android11-release/init/property_service.cpp",
    "bionic_system_properties": "https://android.googlesource.com/platform/bionic/+/cc9b100/libc/system_properties/system_properties.cpp",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


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


def unique_sorted(values: list[str]) -> list[str]:
    return sorted(set(v.strip() for v in values if v.strip()))


def parse_symbols(readelf_text: str) -> tuple[list[str], list[str]]:
    read_symbols: list[str] = []
    write_symbols: list[str] = []
    for line in readelf_text.splitlines():
        if " UND " not in line and " GLOBAL " not in line:
            continue
        read_symbols.extend(match.group(1) for match in PROPERTY_READ_SYMBOL_RE.finditer(line))
        write_symbols.extend(match.group(1) for match in PROPERTY_WRITE_SYMBOL_RE.finditer(line))
    return unique_sorted(read_symbols), unique_sorted(write_symbols)


def parse_property_strings(strings_text: str) -> list[str]:
    values: list[str] = []
    for line in strings_text.splitlines():
        for match in PROPERTY_STRING_RE.finditer(line):
            values.append(match.group(1))
    return unique_sorted(values)


def classify(v250: dict[str, Any], binary: Path, file_result: dict[str, Any], readelf: dict[str, Any], strings_result: dict[str, Any], write_symbols: list[str]) -> tuple[bool, str, str]:
    if not (bool(v250.get("pass")) and v250.get("decision") == "qrtr-socket-local-bind-pass"):
        return False, "cnss-property-surface-blocked", "v250 prerequisite missing or stale"
    if not binary.exists():
        return False, "cnss-property-surface-blocked", "exported cnss-daemon binary missing"
    if file_result["rc"] != 0 or readelf["rc"] != 0 or strings_result["rc"] != 0:
        return False, "cnss-property-surface-blocked", "host static analysis command failed"
    if write_symbols:
        return False, "cnss-property-write-surface-review", "property write/control symbols detected"
    return True, "cnss-property-read-only-surface", "property read symbols/strings present with no write/control symbols detected"


def render_summary(manifest: dict[str, Any]) -> str:
    symbol_rows = [["read", item] for item in manifest["property_read_symbols"]] + [["write", item] for item in manifest["property_write_symbols"]]
    string_rows = [[item] for item in manifest["property_strings"]]
    ref_rows = [[k, v] for k, v in manifest["references"].items()]
    return "".join([
        "# v251 CNSS Property Surface\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- reason: `{manifest['reason']}`\n",
        "- daemon start: `not executed`\n",
        f"- binary: `{manifest['binary']}`\n\n",
        "## Property Symbols\n\n",
        markdown_table(["kind", "symbol"], symbol_rows or [["none", "none"]]),
        "\n\n## Property-Like Strings\n\n",
        markdown_table(["string"], string_rows or [["none"]]),
        "\n\n## References\n\n",
        markdown_table(["reference", "url"], ref_rows),
        "\n\n## Guardrails\n\n",
        "- Host-only static analysis.\n",
        "- No `cnss-daemon` execution.\n",
        "- No property service emulation or property area write.\n",
        "- No Wi-Fi scan/connect/link-up action.\n",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v250-manifest", type=Path, default=DEFAULT_V250_MANIFEST)
    parser.add_argument("--binary", type=Path, default=DEFAULT_CNSS_DAEMON)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v250 = load_manifest(args.v250_manifest)
    binary = repo_path(args.binary)
    file_result = run_host(["file", str(binary)])
    readelf = run_host(["readelf", "-Ws", str(binary)])
    strings_result = run_host(["strings", "-a", str(binary)])
    read_symbols, write_symbols = parse_symbols(readelf["text"])
    property_strings = parse_property_strings(strings_result["text"])
    pass_ok, decision, reason = classify(v250, binary, file_result, readelf, strings_result, write_symbols)
    manifest = {
        "created": now_iso(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "binary": str(binary),
        "out_dir": str(repo_path(args.out_dir)),
        "daemon_start_executed": False,
        "host_metadata": collect_host_metadata(),
        "references": REFERENCE_URLS,
        "file": file_result,
        "readelf_rc": readelf["rc"],
        "strings_rc": strings_result["rc"],
        "property_read_symbols": read_symbols,
        "property_write_symbols": write_symbols,
        "property_strings": property_strings,
        "v250_decision": v250.get("decision", "missing"),
    }
    store.write_text("readelf-symbols.txt", readelf["text"] if readelf["text"] else readelf["error"] + "\n")
    store.write_text("strings-property-lines.txt", "\n".join(property_strings) + ("\n" if property_strings else ""))
    store.write_json("property-surface.json", manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"out_dir: {repo_path(args.out_dir)}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

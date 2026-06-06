#!/usr/bin/env python3
"""V1653 source/build-only gate for a90_xbl_context_probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_SOURCE = REPO_ROOT / "stage3/linux_init/helpers/a90_xbl_context_probe.c"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp/wifi/v1653-xbl-context-probe-build"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V1653_XBL_CONTEXT_PROBE_BUILD_2026-06-02.md"
HELPER_NAME = "a90_xbl_context_probe_v1653"
HELPER_MARKER = "a90_xbl_context_probe v1653"

REQUIRED_SOURCE_STRINGS = [
    'PROBE_VERSION "a90_xbl_context_probe v1653"',
    "raw_string_output=0",
    "record artifact=",
    "string_sha256=",
    "tokens=",
    "class=",
    "pon-pshold-pmic-context",
    "rpmh-aop-pmic-context",
]

REQUIRED_BINARY_STRINGS = [
    HELPER_MARKER,
    "raw_string_output=0",
    "--range",
    "--artifact",
    "--path",
    "pon-pshold-pmic-context",
    "rpmh-aop-pmic-context",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_host(command: list[str], output_file: Path, timeout: float = 180.0) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
        write_private_text(output_file, result.stdout)
        return {"command": command, "rc": result.returncode, "timeout": False, "file": rel(output_file)}
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        write_private_text(output_file, output + "\n[TIMEOUT]\n")
        return {"command": command, "rc": None, "timeout": True, "file": rel(output_file)}


def build(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    output = store.path(HELPER_NAME)
    logs = store.mkdir("logs")
    source = args.source
    compile_result = run_host([
        args.cross_gcc,
        "-static",
        "-Os",
        "-Wall",
        "-Wextra",
        "-o",
        str(output),
        str(source),
    ], logs / "build.txt")
    strip_result = run_host([args.strip, str(output)], logs / "strip.txt") if output.exists() else {}
    file_result = run_host(["file", str(output)], logs / "file.txt") if output.exists() else {}
    readelf_program = run_host([args.readelf, "-l", str(output)], logs / "readelf-program.txt") if output.exists() else {}
    readelf_dynamic = run_host([args.readelf, "-d", str(output)], logs / "readelf-dynamic.txt") if output.exists() else {}
    strings_result = run_host(["strings", str(output)], logs / "strings.txt") if output.exists() else {}
    if output.exists():
        output.chmod(0o600)

    source_text = source.read_text(encoding="utf-8", errors="replace") if source.exists() else ""
    strings_text = (logs / "strings.txt").read_text(encoding="utf-8", errors="replace") if (logs / "strings.txt").exists() else ""
    readelf_program_text = (logs / "readelf-program.txt").read_text(encoding="utf-8", errors="replace") if (logs / "readelf-program.txt").exists() else ""
    readelf_dynamic_text = (logs / "readelf-dynamic.txt").read_text(encoding="utf-8", errors="replace") if (logs / "readelf-dynamic.txt").exists() else ""

    return {
        "source": {
            "path": rel(source),
            "exists": source.exists(),
            "required_strings": {item: item in source_text for item in REQUIRED_SOURCE_STRINGS},
        },
        "compile": compile_result,
        "strip": strip_result,
        "file": file_result,
        "readelf_program": readelf_program,
        "readelf_dynamic": readelf_dynamic,
        "strings": strings_result,
        "output": rel(output),
        "output_exists": output.exists(),
        "output_size": output.stat().st_size if output.exists() else 0,
        "output_sha256": sha256(output) if output.exists() else "",
        "file_static": "statically linked" in ((logs / "file.txt").read_text(encoding="utf-8", errors="replace") if (logs / "file.txt").exists() else ""),
        "static_no_interp": "INTERP" not in readelf_program_text,
        "static_no_dynamic": "There is no dynamic section" in readelf_dynamic_text,
        "required_binary_strings": {item: item in strings_text for item in REQUIRED_BINARY_STRINGS},
    }


def classify(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    info = build(args, store)
    checks = {
        "source_exists": info["source"]["exists"],
        "source_contract_strings_present": all(info["source"]["required_strings"].values()),
        "compile_ok": info["compile"].get("rc") == 0 and info["output_exists"],
        "strip_ok": info["strip"].get("rc") == 0,
        "file_static": info["file_static"],
        "static_no_interp": info["static_no_interp"],
        "static_no_dynamic": info["static_no_dynamic"],
        "binary_contract_strings_present": all(info["required_binary_strings"].values()),
        "artifact_private_tmp": info["output"].startswith("tmp/"),
        "no_device_command": True,
        "no_live_write_gate": True,
    }
    decision = "v1653-xbl-context-probe-build-pass" if all(checks.values()) else "v1653-xbl-context-probe-build-review"
    return {
        "cycle": "V1653",
        "type": "source/build-only XBL context probe helper",
        "decision": decision,
        "pass": all(checks.values()),
        "checks": checks,
        "build": info,
        "next": {
            "recommended_cycle": "V1654",
            "type": "private live range-context extraction gate",
            "shape": "deploy/run helper against temporary XBL devnodes, read only V1652 ranges, commit only redacted records",
            "mutation": False,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    build = result["build"]
    lines = [
        "# Native Init V1653 XBL Context Probe Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1653`",
        "- Type: source/build-only XBL context probe helper",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Source: `{build['source']['path']}`",
        f"- Artifact: `{build['output']}`",
        f"- Artifact SHA256: `{build['output_sha256']}`",
        f"- Artifact size: `{build['output_size']}`",
        "- Reason: build a static helper that reads only bounded XBL ranges and emits tracked-safe redacted records.",
        "",
        "## Checks",
        "",
    ]
    for key, value in result["checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Contract",
        "",
        "- Input: `--path PATH --artifact LABEL --range START:END`.",
        "- Output: version, mode, range summaries, and `record` lines containing only artifact/range/offset/length/truncated/string_sha256/tokens/class.",
        "- No raw string text is emitted in tracked output.",
        "- Artifact is built under ignored private `tmp/` evidence, not committed as a binary.",
        "",
        "## Next",
        "",
        "V1654 may deploy/run this helper against temporary XBL devnodes and only the V1652 ranges. Tracked reports must include only redacted records. No partition write, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, PCI rescan, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--cross-gcc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--strip", default="aarch64-linux-gnu-strip")
    parser.add_argument("--readelf", default="aarch64-linux-gnu-readelf")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    result = classify(args, store)
    store.write_json("manifest.json", result)
    report = render_report(result)
    write_private_text(args.out_dir / "summary.md", report)
    write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "artifact": result["build"]["output"],
        "sha256": result["build"]["output_sha256"],
        "report": rel(args.report_path),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

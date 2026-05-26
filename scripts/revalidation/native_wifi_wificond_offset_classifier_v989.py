#!/usr/bin/env python3
"""V989 host-side classifier for V988 wificond crash offsets."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v989-wificond-offset-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v989-wificond-offset-classifier.txt")
DEFAULT_TRANSCRIPT = Path("tmp/wifi/v988-android-service-window-live-v167/native/mdm-helper-cnss-before-esoc.txt")
DEFAULT_RAW_BASE64 = DEFAULT_OUT_DIR / "wificond-base64-raw.txt"
DEFAULT_BINARY = DEFAULT_OUT_DIR / "wificond"
EXPECTED_WIFICOND_SHA256 = "4f97f4bcb5c375d3e9d84a0f1712ef4513521b06e185279f9c8ef9b52c84a3de"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--transcript", type=Path, default=DEFAULT_TRANSCRIPT)
    parser.add_argument("--raw-base64", type=Path, default=DEFAULT_RAW_BASE64)
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--force-decode", action="store_true")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def sha256(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    digest = hashlib.sha256()
    with resolved.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_host(command: list[str], timeout: int = 30) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return result.returncode, result.stdout


def decode_raw_base64(raw_path: Path, binary_path: Path, force: bool) -> bool:
    raw_resolved = repo_path(raw_path)
    binary_resolved = repo_path(binary_path)
    if binary_resolved.exists() and not force:
        return False
    if not raw_resolved.exists():
        return False
    lines = raw_resolved.read_text(errors="replace").splitlines()
    encoded: list[str] = []
    collect = False
    for line in lines:
        if line.startswith("run: pid="):
            collect = True
            continue
        if line.startswith("[exit "):
            break
        if collect and line and not line.startswith("A90P1 "):
            encoded.append(line.strip())
    data = base64.b64decode("".join(encoded), validate=True)
    binary_resolved.parent.mkdir(parents=True, exist_ok=True)
    binary_resolved.write_bytes(data)
    binary_resolved.chmod(0o700)
    return True


def parse_offsets(transcript: str) -> dict[str, str]:
    offsets: dict[str, str] = {}
    patterns = {
        "pc": r"capture\.crash\.maprow\.pc\.relative_offset=(0x[0-9a-fA-F]+)",
        "lr": r"capture\.crash\.maprow\.lr\.relative_offset=(0x[0-9a-fA-F]+)",
        "frame0_ra": r"capture\.crash\.maprow\.frame0_ra\.relative_offset=(0x[0-9a-fA-F]+)",
        "frame1_ra": r"capture\.crash\.maprow\.frame1_ra\.relative_offset=(0x[0-9a-fA-F]+)",
        "frame2_ra": r"capture\.crash\.maprow\.frame2_ra\.relative_offset=(0x[0-9a-fA-F]+)",
        "frame3_ra": r"capture\.crash\.maprow\.frame3_ra\.relative_offset=(0x[0-9a-fA-F]+)",
    }
    for name, pattern in patterns.items():
        match = re.search(pattern, transcript)
        if match:
            offsets[name] = match.group(1).lower()
    return offsets


def read_c_string(binary: bytes, offset: int, limit: int = 160) -> str:
    chunk = binary[offset : offset + limit]
    end = chunk.find(b"\0")
    if end >= 0:
        chunk = chunk[:end]
    return chunk.decode("utf-8", errors="replace")


def addr2line(binary: Path, offsets: dict[str, str]) -> dict[str, str]:
    output: dict[str, str] = {}
    for name, offset in offsets.items():
        rc, text = run_host(
            ["aarch64-linux-gnu-addr2line", "-Cfpie", str(repo_path(binary)), offset],
            timeout=10,
        )
        output[name] = text.strip() if rc == 0 else f"addr2line-error rc={rc}: {text.strip()}"
    return output


def objdump_window(binary: Path, start: int, stop: int) -> str:
    rc, text = run_host(
        [
            "aarch64-linux-gnu-objdump",
            "-d",
            "--demangle",
            f"--start-address=0x{start:x}",
            f"--stop-address=0x{stop:x}",
            str(repo_path(binary)),
        ],
        timeout=20,
    )
    return text if rc == 0 else f"objdump-error rc={rc}\n{text}"


def classify(binary: Path, transcript: str) -> dict[str, Any]:
    binary_resolved = repo_path(binary)
    binary_bytes = binary_resolved.read_bytes() if binary_resolved.exists() else b""
    offsets = parse_offsets(transcript)
    symbols = addr2line(binary, offsets) if binary_bytes else {}
    strings = {
        "main_cpp": read_c_string(binary_bytes, 0xB693) if binary_bytes else "",
        "check_failed": read_c_string(binary_bytes, 0xD66F) if binary_bytes else "",
        "condition": read_c_string(binary_bytes, 0xB86F) if binary_bytes else "",
        "actual_prefix": read_c_string(binary_bytes, 0xE16F) if binary_bytes else "",
        "expected_name": read_c_string(binary_bytes, 0xE2C2) if binary_bytes else "",
        "expected_prefix": read_c_string(binary_bytes, 0xE5A5) if binary_bytes else "",
        "suffix": read_c_string(binary_bytes, 0xF42F) if binary_bytes else "",
    }
    checks = {
        "binary_exists": binary_resolved.exists(),
        "binary_sha_matches_device": sha256(binary) == EXPECTED_WIFICOND_SHA256,
        "v988_trace_has_wificond_crash_stop": "wifi_hal_composite_start.child.wificond.trace.crash_stop=1" in transcript,
        "v988_trace_has_sigabrt": "capture.crash.siginfo.signo=6" in transcript,
        "frame3_is_main_check_block": offsets.get("frame3_ra") == "0x199b4",
        "frame0_symbol_is_logd_logger": "android::base::LogdLogger::LogdLogger" in symbols.get("frame0_ra", ""),
        "frame1_symbol_is_scoped_log_severity": "android::base::ScopedLogSeverity" in symbols.get("frame1_ra", ""),
        "frame2_symbol_is_log_message_destructor": "android::base::LogMessage::~LogMessage" in symbols.get("frame2_ra", ""),
        "main_check_strings_match": (
            strings["main_cpp"] == "system/connectivity/wificond/main.cpp"
            and strings["check_failed"] == "Check failed: "
            and strings["condition"] == "sm->addService(android::String16(kServiceName), service)"
            and strings["expected_name"] == "android::NO_ERROR"
        ),
    }
    passed = all(checks.values())
    return {
        "decision": "v989-wificond-addservice-check-failed"
        if passed
        else "v989-wificond-offset-classification-incomplete",
        "pass": passed,
        "reason": (
            "wificond abort maps to main.cpp service registration check: sm->addService(...) == android::NO_ERROR"
            if passed
            else "missing checks: " + ", ".join(name for name, ok in checks.items() if not ok)
        ),
        "next_step": (
            "repair or emulate the service-manager addService success path before another service-window retry"
            if passed
            else "collect matching wificond binary or improve offset parsing"
        ),
        "checks": checks,
        "offsets": offsets,
        "symbols": symbols,
        "strings": strings,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [(name, "PASS" if ok else "FAIL") for name, ok in manifest["checks"].items()]
    offset_rows = [(name, value, manifest["symbols"].get(name, "")) for name, value in manifest["offsets"].items()]
    string_rows = [(name, value) for name, value in manifest["strings"].items()]
    return "\n".join(
        [
            "# V989 Wificond Offset Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- binary: `{manifest['binary']}`",
            f"- binary sha256: `{manifest['binary_sha256']}`",
            f"- next: {manifest['next_step']}",
            "",
            "## Checks",
            "",
            markdown_table(["check", "result"], rows),
            "",
            "## Offsets",
            "",
            markdown_table(["name", "offset", "symbol"], offset_rows),
            "",
            "## Strings",
            "",
            markdown_table(["name", "value"], string_rows),
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    decoded = decode_raw_base64(args.raw_base64, args.binary, args.force_decode)
    transcript = read_text(args.transcript)
    classification = classify(args.binary, transcript)
    objdump_main = objdump_window(args.binary, 0x19880, 0x19A80)
    objdump_frames = "\n".join(
        [
            objdump_window(args.binary, 0x2AA40, 0x2AB80),
            objdump_window(args.binary, 0x2BB80, 0x2BCA0),
            objdump_window(args.binary, 0x2C4E0, 0x2C590),
        ]
    )
    write_private_text(store.run_dir / "objdump-main-check.txt", objdump_main)
    write_private_text(store.run_dir / "objdump-crash-frames.txt", objdump_frames)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "transcript": str(repo_path(args.transcript)),
        "raw_base64": str(repo_path(args.raw_base64)),
        "binary": str(repo_path(args.binary)),
        "binary_decoded_from_raw": decoded,
        "binary_sha256": sha256(args.binary),
        "expected_wificond_sha256": EXPECTED_WIFICOND_SHA256,
        "device_commands_executed": False,
        "device_mutations": False,
        "actor_start_executed": False,
        "wifi_bringup_executed": False,
        **classification,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

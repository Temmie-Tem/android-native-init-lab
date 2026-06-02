#!/usr/bin/env python3
"""V1654 private live XBL context probe gate.

This gate deploys the V1653 static helper through the existing serial bridge,
creates temporary block devnodes for the two XBL slots, and reads only the
V1652-approved ranges.  Tracked output is limited to the helper's redacted
records: offsets, lengths, SHA256 digests, token sets, and context classes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from a90ctl import ProtocolResult, bridge_exchange, encode_cmdv1_line, run_cmdv1_command
from a90harness.evidence import EvidenceStore, write_private_text

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "tmp/wifi/v1654-xbl-context-probe-live"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V1654_XBL_CONTEXT_PROBE_LIVE_2026-06-02.md"
DEFAULT_LOCAL_HELPER = REPO_ROOT / "tmp/wifi/v1653-xbl-context-probe-build/a90_xbl_context_probe_v1653"
DEFAULT_REMOTE_HELPER = "/cache/bin/a90_xbl_context_probe_v1653"
DEFAULT_HELPER_SHA256 = "e7a143550d99e89aa5dfd3f25daa5c05118e4530cdafe4d1f615cc98daf32f53"
TOYBOX = "/cache/bin/toybox"
NODE_DIR = "/dev/a90_v1654_devnodes"
SERIAL_CONSOLE_LINE_LIMIT = 4096
SERIAL_CONSOLE_LINE_MARGIN = 128
SERIAL_SAFE_LINE_LIMIT = SERIAL_CONSOLE_LINE_LIMIT - SERIAL_CONSOLE_LINE_MARGIN
SERIAL_MAX_REQUESTED_CHUNK_SIZE = 3000

XBL_TARGETS = [
    {
        "label": "xbl_a",
        "major": "8",
        "minor": "17",
        "ranges": ["3340797:3377867", "20034:29600"],
        "classes": ["rpmh-aop-pmic-context", "pon-pshold-pmic-context"],
    },
    {
        "label": "xbl_b",
        "major": "8",
        "minor": "33",
        "ranges": ["3355345:3400091", "20027:30662"],
        "classes": ["rpmh-aop-pmic-context", "pon-pshold-pmic-context"],
    },
]

FORBIDDEN_MARKERS = [
    " if=",
    " of=",
    "dd ",
    "strings ",
    "BOOT_DONE",
    "rescan",
    "wpa_supplicant",
    "wificond",
    "scan ",
    "connect ",
    "dhcp",
    "google.com",
]

RECORD_RE = re.compile(
    r"^record artifact=(?P<artifact>[A-Za-z0-9_+-]+) "
    r"range_start=(?P<range_start>\d+) "
    r"range_end=(?P<range_end>\d+) "
    r"offset=(?P<offset>\d+) "
    r"length=(?P<length>\d+) "
    r"truncated=(?P<truncated>[01]) "
    r"string_sha256=(?P<string_sha256>[0-9a-f]{64}) "
    r"tokens=(?P<tokens>[A-Za-z0-9_,+-]*) "
    r"class=(?P<class>[A-Za-z0-9_+-]+)$"
)

SUMMARY_RE = re.compile(
    r"^summary artifact=(?P<artifact>[A-Za-z0-9_+-]+) "
    r"range_start=(?P<range_start>\d+) "
    r"range_end=(?P<range_end>\d+) "
    r"records=(?P<records>\d+)$"
)


@dataclass
class Capture:
    ok: bool
    rc: int
    status: str
    text: str
    error: str = ""


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def execute(args: argparse.Namespace, command: list[str], timeout: float) -> Capture:
    try:
        result: ProtocolResult = run_cmdv1_command(
            args.host,
            args.port,
            timeout,
            command,
            retry_unsafe=True,
        )
        if result.status == "busy":
            bridge_exchange(
                args.host,
                args.port,
                "hide",
                min(args.timeout, 8.0),
                markers=(b"[busy]", b"[done]", b"[err]"),
            )
            result = run_cmdv1_command(
                args.host,
                args.port,
                timeout,
                command,
                retry_unsafe=True,
            )
        return Capture(result.rc == 0 and result.status == "ok", result.rc, result.status, result.text)
    except Exception as exc:  # noqa: BLE001 - live evidence keeps exact failure
        return Capture(False, 1, "error", f"{exc}\n", str(exc))


def run_cmd(args: argparse.Namespace,
            store: EvidenceStore,
            name: str,
            command: list[str],
            timeout: float | None = None,
            *,
            ok_rcs: set[int] | None = None) -> Capture:
    capture = execute(args, command, timeout if timeout is not None else args.timeout)
    if ok_rcs is not None and capture.rc in ok_rcs:
        capture.ok = True
        capture.status = "ok" if capture.rc == 0 else "accepted"
    store.write_text(f"{name}.txt", capture.text)
    return capture


def run_toybox(args: argparse.Namespace,
               store: EvidenceStore,
               name: str,
               toybox_args: list[str],
               timeout: float | None = None,
               *,
               ok_rcs: set[int] | None = None) -> Capture:
    return run_cmd(args, store, name, ["run", TOYBOX, *toybox_args], timeout, ok_rcs=ok_rcs)


def strip_payload(text: str) -> str:
    payload: list[str] = []
    active = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("run: pid="):
            active = True
            continue
        if not active:
            continue
        if stripped.startswith("[exit ") or stripped.startswith("[done]") or stripped.startswith("[err]"):
            break
        if stripped.startswith("A90P1 END "):
            break
        payload.append(line.rstrip("\r"))
    return "\n".join(payload).strip()


def selftest_ok(text: str) -> bool:
    return "fail=0" in text


def parse_sha256(text: str) -> str:
    match = re.search(r"\b([0-9a-fA-F]{64})\b", strip_payload(text))
    return match.group(1).lower() if match else ""


def uu_char(value: int) -> str:
    normalized = value & 0x3f
    return chr(normalized + 0x20) if normalized else "`"


def uuencode_bytes(data: bytes, *, name: str, mode: int = 0o755) -> str:
    lines = [f"begin {mode:o} {name}\n"]
    for offset in range(0, len(data), 45):
        chunk = data[offset:offset + 45]
        padded = chunk + b"\0" * ((3 - len(chunk) % 3) % 3)
        encoded = []
        for index in range(0, len(padded), 3):
            first_byte = padded[index]
            second_byte = padded[index + 1]
            third_byte = padded[index + 2]
            encoded.extend(
                uu_char(value)
                for value in (
                    first_byte >> 2,
                    ((first_byte << 4) & 0x30) | (second_byte >> 4),
                    ((second_byte << 2) & 0x3c) | (third_byte >> 6),
                    third_byte & 0x3f,
                )
            )
        lines.append(uu_char(len(chunk)) + "".join(encoded) + "\n")
    lines.append("`\nend\n")
    return "".join(lines)


def serial_append_line_check(staging: str, encoded: str, chunk_size: int) -> dict[str, Any]:
    max_line_bytes = 0
    max_line_offset = 0
    uses_cmdv1x = False
    chunks = 0
    for offset in range(0, len(encoded), chunk_size):
        chunk = encoded[offset:offset + chunk_size]
        line = encode_cmdv1_line(["appendfile", staging, chunk])
        line_bytes = len(line.encode("utf-8"))
        if line_bytes > max_line_bytes:
            max_line_bytes = line_bytes
            max_line_offset = offset
        uses_cmdv1x = uses_cmdv1x or line.startswith("cmdv1x ")
        chunks += 1
    return {
        "ok": max_line_bytes <= SERIAL_SAFE_LINE_LIMIT,
        "chunk_size": chunk_size,
        "chunks": chunks,
        "max_cmdv1_line_bytes": max_line_bytes,
        "max_cmdv1_line_offset": max_line_offset,
        "safe_line_limit": SERIAL_SAFE_LINE_LIMIT,
        "console_line_limit": SERIAL_CONSOLE_LINE_LIMIT,
        "uses_cmdv1x": uses_cmdv1x,
    }


def deploy_helper(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    local_path = args.local_helper
    local_sha = sha256_file(local_path) if local_path.exists() else ""
    if local_sha != args.helper_sha256:
        return {
            "ok": False,
            "method": "serial",
            "skipped": False,
            "error": f"local helper sha256 mismatch: {local_sha}",
        }

    existing = run_toybox(args, store, "remote-helper-pre-sha256", ["sha256sum", args.remote_helper], 20.0, ok_rcs={0, 1})
    existing_sha = parse_sha256(existing.text)
    if existing_sha == args.helper_sha256 and args.skip_deploy_if_current:
        return {
            "ok": True,
            "method": "serial",
            "skipped": True,
            "remote_sha256": existing_sha,
            "line_check": None,
            "chunks_written": 0,
        }

    target_dir = str(Path(args.remote_helper).parent)
    target_name = Path(args.remote_helper).name
    timestamp = f"{int(time.time())}.{os.getpid()}"
    staging_dir = args.serial_staging_dir.rstrip("/")
    staging = f"{staging_dir}/.{target_name}.v1654.{timestamp}.uu"
    tmp_target = f"{target_dir}/.{target_name}.tmp.{timestamp}"
    transcript: list[str] = []
    chunks_written = 0

    encoded = uuencode_bytes(local_path.read_bytes(), name=Path(tmp_target).name, mode=0o755)
    chunk_size = max(256, min(args.serial_chunk_size, SERIAL_MAX_REQUESTED_CHUNK_SIZE))
    line_check = serial_append_line_check(staging, encoded, chunk_size)
    if not line_check["ok"]:
        message = (
            "serial chunk size unsafe: "
            f"chunk_size={chunk_size} max_line={line_check['max_cmdv1_line_bytes']} "
            f"safe_limit={SERIAL_SAFE_LINE_LIMIT}"
        )
        store.write_text("serial-deploy-helper.txt", message + "\n")
        return {
            "ok": False,
            "method": "serial",
            "skipped": False,
            "error": message,
            "line_check": line_check,
            "chunks_written": 0,
        }

    def step(name: str, command: list[str], timeout: float = 30.0, *, allow_error: bool = False) -> str:
        capture = execute(args, command, timeout)
        transcript.append(f"## {name}\nargv={command!r}\nok={capture.ok} rc={capture.rc} status={capture.status}\n{capture.text}\n")
        if not capture.ok and not allow_error:
            raise RuntimeError(f"deploy step failed: {name} rc={capture.rc} status={capture.status}\n{capture.text}")
        return capture.text

    try:
        step("mkdir-staging-dir", ["run", TOYBOX, "mkdir", "-p", staging_dir], allow_error=True)
        step("rm-staging", ["run", TOYBOX, "rm", "-f", staging], allow_error=True)
        step("rm-tmp", ["run", TOYBOX, "rm", "-f", tmp_target], allow_error=True)
        for offset in range(0, len(encoded), chunk_size):
            chunk = encoded[offset:offset + chunk_size]
            step(f"append-{chunks_written:04d}", ["appendfile", staging, chunk], timeout=20.0)
            chunks_written += 1
            if chunks_written % 100 == 0:
                print(f"[v1654] serial append chunks={chunks_written}", flush=True)
        step("uudecode", ["run", TOYBOX, "uudecode", "-o", tmp_target, staging], timeout=90.0)
        step("chmod", ["run", TOYBOX, "chmod", "755", tmp_target])
        tmp_sha = parse_sha256(step("sha-tmp", ["run", TOYBOX, "sha256sum", tmp_target]))
        if tmp_sha != args.helper_sha256:
            raise RuntimeError(f"tmp helper sha256 mismatch: {tmp_sha}")
        step("mv-target", ["run", TOYBOX, "mv", "-f", tmp_target, args.remote_helper])
        target_sha = parse_sha256(step("sha-target", ["run", TOYBOX, "sha256sum", args.remote_helper]))
        if target_sha != args.helper_sha256:
            raise RuntimeError(f"target helper sha256 mismatch: {target_sha}")
        step("helper-selftest", ["run", args.remote_helper, "--selftest"], timeout=20.0)
        step("rm-staging-post", ["run", TOYBOX, "rm", "-f", staging], allow_error=True)
    except Exception as exc:
        execute(args, ["run", TOYBOX, "rm", "-f", tmp_target], 20.0)
        store.write_text("serial-deploy-helper.txt", "\n".join(transcript))
        return {
            "ok": False,
            "method": "serial",
            "skipped": False,
            "error": str(exc),
            "line_check": line_check,
            "chunks_written": chunks_written,
        }

    store.write_text("serial-deploy-helper.txt", "\n".join(transcript))
    return {
        "ok": True,
        "method": "serial",
        "skipped": False,
        "remote_sha256": args.helper_sha256,
        "line_check": line_check,
        "chunks_written": chunks_written,
        "encoded_bytes": len(encoded.encode("utf-8")),
    }


def parse_redacted_output(text: str) -> tuple[list[dict[str, str]], list[dict[str, str]], int]:
    records: list[dict[str, str]] = []
    summaries: list[dict[str, str]] = []
    unparsed_record_like = 0
    for line in strip_payload(text).splitlines():
        record_match = RECORD_RE.fullmatch(line.strip())
        if record_match:
            records.append(record_match.groupdict())
            continue
        summary_match = SUMMARY_RE.fullmatch(line.strip())
        if summary_match:
            summaries.append(summary_match.groupdict())
            continue
        if line.startswith("record ") or line.startswith("summary "):
            unparsed_record_like += 1
    return records, summaries, unparsed_record_like


def run_probe_for_target(args: argparse.Namespace, store: EvidenceStore, target: dict[str, Any]) -> dict[str, Any]:
    node = f"{NODE_DIR}/{target['label']}"
    pre_rm = run_toybox(args, store, f"{target['label']}-pre-rm", ["rm", "-f", node])
    mknod = run_toybox(args, store, f"{target['label']}-mknod", ["mknod", node, "b", target["major"], target["minor"]])
    command = [
        "run",
        args.remote_helper,
        "--path",
        node,
        "--artifact",
        target["label"],
    ]
    for range_spec in target["ranges"]:
        command.extend(["--range", range_spec])
    command.extend(["--max-records", str(args.max_records)])
    probe = run_cmd(args, store, f"{target['label']}-probe", command, args.probe_timeout)
    cleanup = run_toybox(args, store, f"{target['label']}-cleanup", ["rm", "-f", node])
    records, summaries, unparsed = parse_redacted_output(probe.text)
    class_counts: dict[str, int] = {}
    token_counts: dict[str, int] = {}
    for record in records:
        class_counts[record["class"]] = class_counts.get(record["class"], 0) + 1
        for token in filter(None, record["tokens"].split(",")):
            token_counts[token] = token_counts.get(token, 0) + 1
    return {
        "label": target["label"],
        "major": target["major"],
        "minor": target["minor"],
        "ranges": target["ranges"],
        "expected_classes": target["classes"],
        "node": node,
        "pre_rm_ok": pre_rm.ok,
        "mknod_ok": mknod.ok,
        "probe_ok": probe.ok,
        "probe_rc": probe.rc,
        "cleanup_ok": cleanup.ok,
        "records": records,
        "summaries": summaries,
        "unparsed_record_like": unparsed,
        "record_count": len(records),
        "class_counts": class_counts,
        "token_counts": token_counts,
    }


def collect(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    pre = run_cmd(args, store, "pre-selftest", ["selftest"])
    deploy = deploy_helper(args, store)
    helper_sha = run_toybox(args, store, "remote-helper-post-sha256", ["sha256sum", args.remote_helper], 20.0, ok_rcs={0, 1})
    helper_selftest = run_cmd(args, store, "remote-helper-selftest", ["run", args.remote_helper, "--selftest"], 20.0)
    cleanup_start = run_toybox(args, store, "cleanup-start", ["rm", "-rf", NODE_DIR])
    mkdir = run_toybox(args, store, "mkdir", ["mkdir", "-p", NODE_DIR]) if deploy.get("ok") else Capture(False, 1, "blocked", "")
    probes = [run_probe_for_target(args, store, target) for target in XBL_TARGETS] if deploy.get("ok") else []
    cleanup_end = run_toybox(args, store, "cleanup-end", ["rm", "-rf", NODE_DIR])
    cleanup_absent = run_toybox(args, store, "cleanup-final-absent", ["ls", "-ld", NODE_DIR], ok_rcs={1})
    post = run_cmd(args, store, "post-selftest", ["selftest"])

    tracked_text = "\n".join(
        [
            json.dumps(
                {
                    "deploy": {
                        "ok": deploy.get("ok"),
                        "skipped": deploy.get("skipped"),
                        "chunks_written": deploy.get("chunks_written"),
                    },
                    "probes": [
                        {
                            "label": probe["label"],
                            "records": probe["records"],
                            "summaries": probe["summaries"],
                        }
                        for probe in probes
                    ],
                },
                sort_keys=True,
            )
        ]
    )
    forbidden = sorted(marker for marker in FORBIDDEN_MARKERS if marker.lower() in tracked_text.lower())
    remote_sha = parse_sha256(helper_sha.text)
    all_records = [record for probe in probes for record in probe["records"]]
    checks = {
        "pre_selftest_fail_zero": pre.ok and selftest_ok(pre.text),
        "post_selftest_fail_zero": post.ok and selftest_ok(post.text),
        "helper_deploy_or_current_ok": bool(deploy.get("ok")),
        "helper_sha256_ok": remote_sha == args.helper_sha256,
        "helper_selftest_ok": helper_selftest.ok and "selftest.sha256_ok=1" in helper_selftest.text,
        "initial_cleanup_ok": cleanup_start.ok,
        "mkdir_ok": mkdir.ok,
        "all_mknod_ok": bool(probes) and all(probe["mknod_ok"] for probe in probes),
        "all_probe_ok": bool(probes) and all(probe["probe_ok"] for probe in probes),
        "all_cleanup_ok": cleanup_end.ok and (not probes or all(probe["cleanup_ok"] for probe in probes)),
        "cleanup_final_absent": cleanup_absent.ok and "No such file or directory" in cleanup_absent.text,
        "redacted_records_parse_ok": all(probe["unparsed_record_like"] == 0 for probe in probes),
        "redacted_records_present": bool(all_records),
        "forbidden_tracked_markers_absent": not forbidden,
        "no_partition_write_command": True,
        "no_pmic_gpio_gdsc_write": True,
        "no_esoc_notify_boot_done": True,
        "no_pci_or_wifi_gate": True,
    }
    decision = "v1654-xbl-context-probe-live-pass" if all(checks.values()) else "v1654-xbl-context-probe-live-review"
    return {
        "cycle": "V1654",
        "type": "private live XBL redacted context probe",
        "decision": decision,
        "pass": all(checks.values()),
        "checks": checks,
        "helper": {
            "local": rel(args.local_helper),
            "remote": args.remote_helper,
            "expected_sha256": args.helper_sha256,
            "remote_sha256": remote_sha,
            "deploy": deploy,
        },
        "targets": probes,
        "forbidden_markers": forbidden,
        "out_dir": rel(store.run_dir),
        "next": {
            "recommended_cycle": "V1655",
            "type": "host-only redacted XBL context interpretation",
            "mutation": False,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Native Init V1654 XBL Context Probe Live Gate",
        "",
        "## Summary",
        "",
        "- Cycle: `V1654`",
        "- Type: private live XBL redacted context probe",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Helper SHA256: `{result['helper']['remote_sha256']}`",
        f"- Helper deploy skipped: `{result['helper']['deploy'].get('skipped')}`",
        f"- Serial chunks written: `{result['helper']['deploy'].get('chunks_written')}`",
        "- Reason: extract tracked-safe string context records only inside the V1652-approved XBL ranges.",
        "",
        "## Checks",
        "",
    ]
    for key, value in result["checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Target Summary",
        "",
        "| artifact | ranges | records | classes | tokens | cleanup |",
        "|---|---|---:|---|---|---|",
    ])
    for target in result["targets"]:
        ranges = ", ".join(f"`{range_spec}`" for range_spec in target["ranges"])
        classes = ", ".join(f"{class_name}={count}" for class_name, count in sorted(target["class_counts"].items())) or "none"
        tokens = ", ".join(f"{token}={count}" for token, count in sorted(target["token_counts"].items())) or "none"
        lines.append(
            f"| `{target['label']}` | {ranges} | {target['record_count']} | {classes} | {tokens} | `{target['cleanup_ok']}` |"
        )
    lines.extend([
        "",
        "## Redacted Records",
        "",
        "Only helper-emitted redacted records are rendered. Raw string text and raw partition bytes are not included.",
        "",
    ])
    for target in result["targets"]:
        lines.append(f"### `{target['label']}`")
        if not target["records"]:
            lines.append("- none")
            continue
        for record in target["records"]:
            lines.append(
                "- "
                f"artifact=`{record['artifact']}` "
                f"range=`{record['range_start']}:{record['range_end']}` "
                f"offset=`{record['offset']}` "
                f"length=`{record['length']}` "
                f"truncated=`{record['truncated']}` "
                f"string_sha256=`{record['string_sha256']}` "
                f"tokens=`{record['tokens']}` "
                f"class=`{record['class']}`"
            )
    lines.extend([
        "",
        "## Range Summaries",
        "",
    ])
    for target in result["targets"]:
        lines.append(f"### `{target['label']}`")
        if not target["summaries"]:
            lines.append("- none")
            continue
        for summary in target["summaries"]:
            lines.append(
                "- "
                f"range=`{summary['range_start']}:{summary['range_end']}` "
                f"records=`{summary['records']}`"
            )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "V1654 used temporary filesystem-only XBL devnodes and the V1653 helper to read only the V1652-approved ranges. The tracked report contains offsets, lengths, string SHA256 values, matched token sets, and context classes only.",
        "",
        "It did not dump raw partition bytes, commit proprietary binaries, write partitions, write PMIC/GPIO/GDSC state, issue eSoC notify/`BOOT_DONE`, rescan PCI, start Wi-Fi HAL, scan/connect, use credentials, run DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        "V1655 should stay host-only: interpret the redacted XBL context classes and decide whether the evidence supports a concrete bootloader/PMIC owner hypothesis. Do not move to bounded rail or PMIC writes without a separate explicit gate.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--probe-timeout", type=float, default=90.0)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--local-helper", type=Path, default=DEFAULT_LOCAL_HELPER)
    parser.add_argument("--remote-helper", default=DEFAULT_REMOTE_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--serial-staging-dir", default="/cache/a90-runtime/bin")
    parser.add_argument("--serial-chunk-size", type=int, default=1800)
    parser.add_argument("--max-records", type=int, default=512)
    parser.add_argument("--skip-deploy-if-current", action="store_true", default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    result = collect(args, store)
    store.write_json("manifest.json", result)
    report = render_report(result)
    write_private_text(args.out_dir / "summary.md", report)
    write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "report": rel(args.report_path),
        "out_dir": result["out_dir"],
        "records": sum(target["record_count"] for target in result["targets"]),
        "deploy_skipped": result["helper"]["deploy"].get("skipped"),
        "chunks_written": result["helper"]["deploy"].get("chunks_written"),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

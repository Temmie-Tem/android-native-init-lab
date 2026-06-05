#!/usr/bin/env python3
"""V1945 read-only export of the dynamic RIL implementation named by rild."""

from __future__ import annotations

import argparse
import base64
import binascii
import datetime as dt
import re
from collections import deque
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture
from a90harness.evidence import EvidenceStore
import native_wifi_qcril_vendor_artifact_export_v1942 as base


CYCLE = "V1945"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
DEFAULT_OUT_DIR = repo_path("tmp/wifi/v1945-ril-impl-export")
REPORT_PATH = repo_path("docs/reports/NATIVE_INIT_V1945_RIL_IMPL_EXPORT_2026-06-04.md")
PROBE_PREFIX = "/tmp/a90-v1945-"
DIRECT_TARGETS = (
    "lib64/libsec-ril.so",
    "lib64/libsec-ril-dsds.so",
    "lib64/libsec-ril-shannon.so",
    "lib64/libsecril-client.so",
    "lib64/libsitril-client.so",
    "lib64/libsitril.so",
    "lib/libsec-ril.so",
    "lib/libsec-ril-dsds.so",
    "lib/libsec-ril-shannon.so",
    "lib/libsecril-client.so",
    "lib/libsitril-client.so",
    "lib/libsitril.so",
    "etc/init/rild.rc",
    "etc/init/init.rilcommon.rc",
    "etc/init/init.rilchip.rc",
    "etc/init/vendor.rild.rc",
    "build.prop",
    "etc/prop.default",
)
SCAN_DIRS = ("lib64", "lib", "etc/init", "etc")
RIL_IMPL_RE = re.compile(r"(?:^|/)lib(?:sec[-_]?ril|sec.*ril|secril|sitril|ril).*\.so$|(?:^|/).*ril.*\.rc$|(?:^|/)(?:build\.prop|prop\.default)$", re.IGNORECASE)
PROPERTY_RE = re.compile(r"(vendor\.sec\.rild\.libpath|vendor\.rild\.libpath|rilLibPath|libsec-ril|RIL_Init|pm_client|peripheral)", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--max-file-bytes", type=int, default=96 * 1024 * 1024)
    parser.add_argument("--max-total-bytes", type=int, default=192 * 1024 * 1024)
    parser.add_argument("--max-targets", type=int, default=80)
    parser.add_argument("--chunk-threshold-bytes", type=int, default=1024 * 1024)
    parser.add_argument("--chunk-bytes", type=int, default=128 * 1024)
    parser.add_argument("--skip-libs", action="store_true")
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def make_probe_paths(run_id: str, major: str, minor: str) -> base.ProbePaths:
    safe_run = base.safe_name(run_id)
    probe_base = f"{PROBE_PREFIX}{safe_run}"
    return base.ProbePaths(
        run_id=run_id,
        base=probe_base,
        node=f"{probe_base}/{base.BLOCK_NAME}",
        mountpoint=f"{probe_base}/vendor",
        major=major,
        minor=minor,
    )


def validate_command_guard() -> None:
    probe = make_probe_paths("guard", "259", "29")
    commands = [
        ["version"],
        ["selftest"],
        ["cat", "/sys/class/block/sda29/dev"],
        ["mkdir", probe.base],
        ["mkdir", probe.mountpoint],
        ["mknodb", probe.node, probe.major, probe.minor],
        ["run", "/cache/bin/toybox", "mount", "-t", "ext4", "-o", "ro,noload", probe.node, probe.mountpoint],
        ["ls", base.remote_path(probe, "lib64")],
        ["stat", base.remote_path(probe, "lib64/libsec-ril.so")],
        ["run", "/cache/bin/toybox", "base64", "-w", "0", base.remote_path(probe, "lib64/libsec-ril.so")],
        ["umount", probe.mountpoint],
    ]
    for command in commands:
        base.validate_command(command, probe)
    validate_chunk_command(
        chunk_command(probe, "lib64/libsec-ril.so", 0, 128 * 1024),
        probe,
        "lib64/libsec-ril.so",
        0,
        128 * 1024,
    )


def chunk_shell(probe: base.ProbePaths, relative_path: str, chunk_index: int, chunk_bytes: int) -> str:
    remote = base.remote_path(probe, relative_path)
    return (
        f"/cache/bin/toybox dd if={remote} bs={chunk_bytes} skip={chunk_index} count=1 2>/dev/null "
        f"| /cache/bin/toybox base64 -w 0"
    )


def chunk_command(probe: base.ProbePaths, relative_path: str, chunk_index: int, chunk_bytes: int) -> list[str]:
    return ["run", "/cache/bin/busybox", "sh", "-c", chunk_shell(probe, relative_path, chunk_index, chunk_bytes)]


def validate_chunk_command(command: list[str],
                           probe: base.ProbePaths,
                           relative_path: str,
                           chunk_index: int,
                           chunk_bytes: int) -> None:
    if chunk_index < 0 or chunk_bytes <= 0:
        raise RuntimeError("invalid chunk parameters")
    expected = chunk_command(probe, relative_path, chunk_index, chunk_bytes)
    if command != expected:
        raise RuntimeError(f"unexpected chunk command: {' '.join(command)}")


def capture_chunk(store: EvidenceStore,
                  args: argparse.Namespace,
                  probe: base.ProbePaths,
                  name: str,
                  relative_path: str,
                  chunk_index: int,
                  chunk_bytes: int) -> dict[str, Any]:
    command = chunk_command(probe, relative_path, chunk_index, chunk_bytes)
    validate_chunk_command(command, probe, relative_path, chunk_index, chunk_bytes)
    capture = run_capture(args, name, command, timeout=max(args.timeout, 60.0))
    file_path = base.write_capture(store, name, capture.text or capture.error)
    return {
        "name": name,
        "command": capture.command,
        "ok": capture.ok,
        "rc": capture.rc,
        "status": capture.status,
        "duration_sec": capture.duration_sec,
        "file": file_path,
        "text": capture.text,
        "error": capture.error,
    }


def pull_remote_file_bounded(store: EvidenceStore,
                             args: argparse.Namespace,
                             probe: base.ProbePaths,
                             vendor_source: Path,
                             relative_path: str,
                             reason: str,
                             total_bytes: int,
                             captures: list[dict[str, Any]]) -> tuple[base.PulledFile | None, int, dict[str, Any]]:
    stat_record = base.capture_device(store, args, probe, f"stat-{relative_path}", ["stat", base.remote_path(probe, relative_path)], timeout=25.0)
    captures.append(stat_record)
    if not stat_record["ok"]:
        return None, total_bytes, {"path": relative_path, "reason": "stat-failed", "record": stat_record["file"]}
    expected_size = base.parse_stat_size(stat_record["text"])
    if expected_size is None:
        return None, total_bytes, {"path": relative_path, "reason": "stat-size-missing", "record": stat_record["file"]}
    if expected_size > args.max_file_bytes:
        return None, total_bytes, {"path": relative_path, "reason": f"file-too-large:{expected_size}", "record": stat_record["file"]}
    if total_bytes + expected_size > args.max_total_bytes:
        return None, total_bytes, {"path": relative_path, "reason": f"total-size-limit:{total_bytes + expected_size}", "record": stat_record["file"]}
    if expected_size <= args.chunk_threshold_bytes:
        pulled, next_total, evidence = base.pull_remote_file(store, args, probe, vendor_source, relative_path, reason, total_bytes)
        return pulled, next_total, evidence

    payload = bytearray()
    chunk_count = (expected_size + args.chunk_bytes - 1) // args.chunk_bytes
    for chunk_index in range(chunk_count):
        record = capture_chunk(
            store,
            args,
            probe,
            f"chunk-{relative_path}-{chunk_index:04d}",
            relative_path,
            chunk_index,
            args.chunk_bytes,
        )
        captures.append(record)
        if not record["ok"]:
            return None, total_bytes, {"path": relative_path, "reason": f"chunk-failed:{chunk_index}", "record": record["file"]}
        try:
            chunk = base64.b64decode(base.extract_base64_payload(record["text"]), validate=True)
        except (binascii.Error, RuntimeError) as exc:
            return None, total_bytes, {"path": relative_path, "reason": f"chunk-decode-failed:{chunk_index}:{exc}", "record": record["file"]}
        expected_chunk_size = min(args.chunk_bytes, expected_size - len(payload))
        if len(chunk) != expected_chunk_size:
            return None, total_bytes, {"path": relative_path, "reason": f"chunk-size-mismatch:{chunk_index}:{len(chunk)}!={expected_chunk_size}", "record": record["file"]}
        payload.extend(chunk)
    data = bytes(payload)
    if len(data) != expected_size:
        return None, total_bytes, {"path": relative_path, "reason": f"size-mismatch:{len(data)}!={expected_size}"}
    base.write_vendor_file(vendor_source, relative_path, data)
    pulled = base.PulledFile(relative_path, len(data), base.sha256_bytes(data), base.remote_path(probe, relative_path), f"{reason}:chunked")
    return pulled, total_bytes + len(data), {"path": relative_path, "reason": "copied-chunked", "chunks": chunk_count}


def discover_targets(listings: dict[str, list[str]], max_targets: int) -> tuple[list[tuple[str, str]], list[dict[str, Any]]]:
    discovered: list[tuple[str, str]] = []
    notes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for relative_path in DIRECT_TARGETS:
        discovered.append((relative_path, "direct-target"))
        seen.add(relative_path)
    for directory, names in listings.items():
        for name in names:
            relative_path = f"{directory}/{name}"
            if relative_path in seen:
                continue
            if RIL_IMPL_RE.search(relative_path):
                discovered.append((relative_path, "directory-match"))
                seen.add(relative_path)
    if len(discovered) > max_targets:
        notes.append({"path": "target-discovery", "reason": f"truncated:{len(discovered)}>{max_targets}"})
        discovered = discovered[:max_targets]
    return discovered, notes


def scan_text_hits(vendor_source: Path, pulled_files: list[base.PulledFile]) -> dict[str, dict[str, Any]]:
    hits: dict[str, dict[str, Any]] = {}
    for pulled in pulled_files:
        full_path = vendor_source / pulled.relative_path
        if not full_path.exists():
            continue
        try:
            data = full_path.read_bytes()
        except OSError as exc:
            hits[pulled.relative_path] = {"status": f"read-failed:{exc}", "count": 0, "samples": []}
            continue
        text = data.decode("utf-8", errors="ignore") if b"\x00" not in data[:4096] else base.run_strings_hits(full_path, limit=20).get("samples", [])
        if isinstance(text, list):
            samples = [line for line in text if PROPERTY_RE.search(line)]
            hits[pulled.relative_path] = {"status": "strings", "count": len(samples), "samples": samples[:20]}
            continue
        samples = [line.strip()[:240] for line in text.splitlines() if PROPERTY_RE.search(line)]
        hits[pulled.relative_path] = {"status": "text", "count": len(samples), "samples": samples[:20]}
    return hits


def decide(pulled_files: list[base.PulledFile], cleanup_ok: bool, version_matches: bool, post_selftest_fail0: bool) -> tuple[str, str, bool]:
    pulled_paths = {item.relative_path for item in pulled_files}
    ril_impl_paths = sorted(path for path in pulled_paths if re.search(r"lib(?:sec|secril|sitril).*\.so$", Path(path).name, re.IGNORECASE))
    if not cleanup_ok:
        return "ril-impl-export-cleanup-review", "temporary vendor mount cleanup did not fully pass", False
    if not version_matches or not post_selftest_fail0:
        return "ril-impl-export-baseline-review", "native version or post selftest baseline did not verify", False
    if ril_impl_paths:
        return "ril-impl-artifacts-exported-readonly", "bounded dynamic RIL implementation artifacts were exported read-only for host callgraph analysis", True
    return "ril-impl-artifacts-absent-from-sda29-candidates", "bounded scan did not copy libsec/secril/sitril RIL implementation candidates", True


def build_report(manifest: dict[str, Any]) -> str:
    pulled_rows = [
        [item["relative_path"], str(item["size"]), item["sha256"][:16], item["reason"]]
        for item in manifest["pulled_files"]
    ]
    hit_rows = [
        [path, summary["status"], str(summary["count"]), " | ".join(summary["samples"][:4])]
        for path, summary in manifest["property_hits"].items()
        if summary["count"] > 0
    ]
    skipped_rows = [[item["path"], item["reason"]] for item in manifest["missing_or_skipped_files"][:40]]
    return "\n".join(
        [
            "# Native Init V1945 RIL Implementation Export",
            "",
            "## Summary",
            "",
            f"- Cycle: `{manifest['cycle']}`",
            "- Type: live read-only bounded export from `sda29` for rild dynamic RIL implementation",
            f"- Decision: `{manifest['decision']}`",
            f"- Label: `{manifest['label']}`",
            f"- Pass: `{manifest['pass']}`",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            "",
            "## Matrix",
            "",
            markdown_table(
                ["area", "value", "detail"],
                [
                    ["version matches", manifest["version_matches"], manifest["expect_version"]],
                    ["post selftest fail=0", manifest["post_selftest_fail0"], manifest["post_selftest_file"]],
                    ["cleanup ok", manifest["probe"]["cleanup_ok"], manifest["probe"]["mountpoint"]],
                    ["target count", manifest["target_count"], "direct libsec/secril/sitril plus bounded directory matches"],
                    ["pulled files", manifest["pulled_file_count"], f"{manifest['pulled_total_bytes']} bytes"],
                    ["skip libs", manifest["limits"]["skip_libs"], "direct RIL artifacts only when true"],
                ],
            ),
            "",
            "## Pulled RIL Implementation Candidates",
            "",
            markdown_table(["path", "size", "sha256 prefix", "reason"], pulled_rows or [["none", "0", "", ""]]),
            "",
            "## Property / Loader Hits",
            "",
            markdown_table(["path", "mode", "hit count", "sample"], hit_rows or [["none", "", "0", ""]]),
            "",
            "## Missing / Skipped Sample",
            "",
            markdown_table(["path", "reason"], skipped_rows or [["none", "none"]]),
            "",
            "## Interpretation",
            "",
            "- This keeps V1944 bounded: observe the `libsec-ril*`/secril/sitril implementation candidates and related RIL rc/property evidence only.",
            "- Next host-only step: run the V1944 PM-client symbol/string/callgraph scan over these exported RIL implementation artifacts, without executing rild/radio/QCRIL.",
            "",
            "## Safety Scope",
            "",
            "- Temporary `sda29` mount only, exact `ext4 ro,noload`.",
            "- No vendor/firmware/partition write, no remount-write, no daemon execution.",
            "- No `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO/regulator action, restart-PD, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    validate_command_guard()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    vendor_source = out_dir / "vendor-source"
    base.reset_private_dir(vendor_source)

    created = dt.datetime.now(dt.timezone.utc).isoformat()
    run_id = args.run_id or "live-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    captures: list[dict[str, Any]] = []
    missing_or_skipped: list[dict[str, Any]] = []
    pulled_files: list[base.PulledFile] = []
    dependencies: list[dict[str, Any]] = []
    listings: dict[str, list[str]] = {}
    total_bytes = 0
    cleanup_ok = True
    version_matches = False
    post_selftest_fail0 = False
    post_selftest_file = ""
    probe: base.ProbePaths | None = None

    captures.append(base.capture_device(store, args, None, "version", ["version"], timeout=15.0))
    version_matches = args.expect_version in captures[-1]["text"]
    captures.append(base.capture_device(store, args, None, "pre-selftest", ["selftest"], timeout=15.0))
    block_dev = base.capture_device(store, args, None, "sys-sda29-dev", ["cat", "/sys/class/block/sda29/dev"], timeout=20.0)
    captures.append(block_dev)
    major, minor = base.parse_block_dev(block_dev["text"])
    probe = make_probe_paths(run_id, major, minor)

    try:
        for name, command, timeout in (
            ("mkdir-base", ["mkdir", probe.base], 20.0),
            ("mkdir-mountpoint", ["mkdir", probe.mountpoint], 20.0),
            ("mknodb-sda29", ["mknodb", probe.node, probe.major, probe.minor], 20.0),
            ("safe-ro-noload-mount", ["run", "/cache/bin/toybox", "mount", "-t", "ext4", "-o", "ro,noload", probe.node, probe.mountpoint], 45.0),
            ("mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0),
        ):
            record = base.capture_device(store, args, probe, name, command, timeout=timeout)
            captures.append(record)
            if not record["ok"]:
                raise RuntimeError(f"{name} failed; see {record['file']}")

        for directory in SCAN_DIRS:
            record = base.capture_device(store, args, probe, f"ls-{directory}", ["ls", base.remote_path(probe, directory)], timeout=25.0)
            captures.append(record)
            if record["ok"]:
                listings[directory] = base.parse_ls_names(record["text"])
            else:
                missing_or_skipped.append({"path": directory, "reason": "ls-failed", "record": record["file"]})

        targets, discovery_notes = discover_targets(listings, args.max_targets)
        missing_or_skipped.extend(discovery_notes)
        queue: deque[tuple[str, str]] = deque(targets)
        requested = {path for path, _reason in targets}
        while queue:
            relative_path, reason = queue.popleft()
            if any(item.relative_path == relative_path for item in pulled_files):
                continue
            pulled, total_bytes, evidence = pull_remote_file_bounded(
                store,
                args,
                probe,
                vendor_source,
                relative_path,
                reason,
                total_bytes,
                captures,
            )
            if pulled is None:
                missing_or_skipped.append(evidence)
                continue
            pulled_files.append(pulled)
            if not args.skip_libs and relative_path.endswith(".so"):
                base.queue_needed_libraries(vendor_source, relative_path, queue, requested, dependencies)
    except Exception as exc:
        missing_or_skipped.append({"path": "live-export", "reason": str(exc)})
    finally:
        if probe is not None:
            cleanup_record = base.capture_device(store, args, probe, "cleanup-umount", ["umount", probe.mountpoint], timeout=25.0)
            captures.append(cleanup_record)
            cleanup_ok = cleanup_record["ok"]
            post_record = base.capture_device(store, args, probe, "post-proc-mounts", ["cat", "/proc/mounts"], timeout=20.0)
            captures.append(post_record)
            if probe.mountpoint in post_record["text"]:
                cleanup_ok = False
                missing_or_skipped.append({"path": probe.mountpoint, "reason": "still-mounted-after-cleanup"})
        post_selftest = base.capture_device(store, args, None, "post-selftest", ["selftest"], timeout=15.0)
        captures.append(post_selftest)
        post_selftest_fail0 = "fail=0" in post_selftest["text"]
        post_selftest_file = post_selftest["file"]

    label, reason, pass_ok = decide(pulled_files, cleanup_ok, version_matches, post_selftest_fail0)
    targets, _notes = discover_targets(listings, args.max_targets)
    manifest = {
        "created": created,
        "cycle": CYCLE,
        "pass": pass_ok,
        "decision": f"v1945-{label}-{'pass' if pass_ok else 'review'}",
        "label": label,
        "reason": reason,
        "mode": "native-ril-impl-readonly-export",
        "run_id": run_id,
        "expect_version": args.expect_version,
        "version_matches": version_matches,
        "post_selftest_fail0": post_selftest_fail0,
        "post_selftest_file": post_selftest_file,
        "out_dir": rel(out_dir),
        "output_vendor_source": rel(vendor_source if pulled_files else out_dir),
        "target_count": len(targets),
        "pulled_file_count": len(pulled_files),
        "pulled_total_bytes": total_bytes,
        "pulled_files": [asdict(item) for item in pulled_files],
        "property_hits": scan_text_hits(vendor_source, pulled_files),
        "missing_or_skipped_files": missing_or_skipped,
        "dependencies": dependencies,
        "listings": listings,
        "probe": {
            "block": base.BLOCK_NAME,
            "major": probe.major if probe else None,
            "minor": probe.minor if probe else None,
            "base": probe.base if probe else None,
            "node": probe.node if probe else None,
            "mountpoint": probe.mountpoint if probe else None,
            "cleanup_ok": cleanup_ok,
        },
        "captures": [{key: value for key, value in record.items() if key != "text"} for record in captures],
        "limits": {
            "max_file_bytes": args.max_file_bytes,
            "max_total_bytes": args.max_total_bytes,
            "max_targets": args.max_targets,
            "skip_libs": args.skip_libs,
        },
        "guardrails": [
            "temporary vendor mount only",
            "mount command is exact ext4 ro,noload",
            "no vendor or firmware writes",
            "no daemon execution",
            "no /dev/subsys_esoc0, eSoC, PCIe, GDSC, PMIC, GPIO, regulator action",
            "no Wi-Fi HAL, scan, connect, credentials, DHCP, routes, external ping",
        ],
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    REPORT_PATH.write_text(build_report(manifest), encoding="utf-8")
    print(f"{'PASS' if pass_ok else 'FAIL'} out_dir={out_dir} decision={manifest['decision']} reason={reason}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

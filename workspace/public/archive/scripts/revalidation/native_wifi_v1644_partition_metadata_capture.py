#!/usr/bin/env python3
"""V1644 read-only live partition metadata/hash capture for SDX power-owner evidence."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from a90ctl import ProtocolResult, bridge_exchange, run_cmdv1_command
from a90harness.evidence import EvidenceStore, write_private_text

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp/wifi/v1644-partition-metadata-capture"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V1644_PARTITION_METADATA_CAPTURE_2026-06-02.md"
TOYBOX = "/cache/bin/toybox"

PARTITIONS = [
    "xbl",
    "xblbak",
    "abl",
    "ablbak",
    "aop",
    "aopbak",
    "devcfg",
    "devcfgbak",
    "tz",
    "tzbak",
    "hyp",
    "hypbak",
    "keymaster",
    "keymasterbak",
    "cmnlib",
    "cmnlibbak",
    "cmnlib64",
    "cmnlib64bak",
    "qupfw",
    "qupfwbak",
    "modem",
    "NON-HLOS",
    "bluetooth",
    "dsp",
]

DISKS = ["sda", "sdb", "sdc", "sdd", "mmcblk0"]

SENSITIVE_EXCLUSIONS = {
    "userdata",
    "metadata",
    "persist",
    "efs",
    "modemst1",
    "modemst2",
    "fsg",
    "fsc",
    "keystore",
    "sec_efs",
}

FORBIDDEN_OUTPUT_MARKERS = [
    "case=11",
    "rc_sel=2",
    "BOOT_DONE",
    "rescan",
    "bind",
    "unbind",
    "wpa_supplicant",
    "wificond",
    "scan ",
    "connect ",
    "dhcp",
    "8.8.8.8",
    "google.com",
]


@dataclass
class Capture:
    name: str
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


def execute_command(args: argparse.Namespace, command: list[str], timeout: float) -> Capture:
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
        return Capture("", result.rc == 0 and result.status == "ok", result.rc, result.status, result.text)
    except Exception as exc:  # noqa: BLE001 - evidence collector must preserve failure reason
        text = f"{exc}\n"
        return Capture("", False, 1, "error", text, str(exc))


def run_capture(args: argparse.Namespace, store: EvidenceStore, name: str, command: list[str], timeout: float) -> Capture:
    capture = execute_command(args, command, timeout)
    capture.name = name
    store.write_text(f"{name}.txt", capture.text)
    return capture


def selftest_fail_zero(text: str) -> bool:
    return bool(re.search(r"\bselftest:\s+pass=\d+\s+warn=\d+\s+fail=0\b", text))


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "_", name)


def strip_run_payload(text: str) -> str:
    lines = text.splitlines()
    payload: list[str] = []
    in_payload = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("run: pid="):
            in_payload = True
            continue
        if not in_payload:
            continue
        if stripped.startswith("[exit ") or stripped.startswith("[done]") or stripped.startswith("[err]"):
            break
        if stripped.startswith("A90P1 END "):
            break
        payload.append(line.rstrip("\r"))
    return "\n".join(payload).strip()


def run_toybox(args: argparse.Namespace,
               store: EvidenceStore,
               name: str,
               toybox_args: list[str],
               timeout: float | None = None) -> Capture:
    return run_capture(
        args,
        store,
        name,
        ["run", TOYBOX, *toybox_args],
        timeout if timeout is not None else args.timeout,
    )


def run_toybox_transient(args: argparse.Namespace, toybox_args: list[str], timeout: float | None = None) -> Capture:
    capture = execute_command(
        args,
        ["run", TOYBOX, *toybox_args],
        timeout if timeout is not None else args.timeout,
    )
    return capture


def first_payload_line(text: str) -> str:
    payload = strip_run_payload(text)
    for line in payload.splitlines():
        if line.strip():
            return line.strip()
    return ""


def collect_partition(args: argparse.Namespace, store: EvidenceStore, name: str) -> dict[str, str]:
    path = f"/dev/block/by-name/{name}"
    prefix = f"part-{safe_name(name)}"
    ls_capture = run_toybox(args, store, f"{prefix}-ls", ["ls", "-l", path], args.timeout)
    if not ls_capture.ok:
        return {"name": name, "present": "false"}

    readlink_capture = run_toybox(args, store, f"{prefix}-readlink", ["readlink", "-f", path], args.timeout)
    size_capture = run_toybox(args, store, f"{prefix}-size", ["blockdev", "--getsize64", path], args.timeout)
    sha_capture = run_toybox(args, store, f"{prefix}-sha256", ["sha256sum", path], args.capture_timeout)

    size_line = first_payload_line(size_capture.text)
    sha_line = first_payload_line(sha_capture.text)
    sha_match = re.match(r"(?P<sha>[0-9a-fA-F]{64})\s+", sha_line)
    return {
        "name": name,
        "present": "true",
        "path": path,
        "target": first_payload_line(readlink_capture.text),
        "ls": first_payload_line(ls_capture.text),
        "size": size_line if re.fullmatch(r"\d+", size_line) else "",
        "sha256": sha_match.group("sha").lower() if sha_match else "",
        "ls_ok": str(ls_capture.ok),
        "readlink_ok": str(readlink_capture.ok),
        "size_ok": str(size_capture.ok),
        "sha256_ok": str(sha_capture.ok),
    }


def parse_key_values(payload: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in payload.splitlines():
        if "=" not in line:
            continue
        key, value = line.strip().split("=", 1)
        values[key] = value
    return values


def list_disk_partitions(args: argparse.Namespace, store: EvidenceStore, disk: str) -> list[str]:
    capture = run_toybox(args, store, f"sysfs-{safe_name(disk)}-ls", ["ls", "-l", f"/sys/block/{disk}/"], args.timeout)
    if not capture.ok:
        return []
    payload = strip_run_payload(capture.text)
    if disk.startswith("mmcblk"):
        pattern = re.compile(rf"\b{re.escape(disk)}p\d+\b")
    else:
        pattern = re.compile(rf"\b{re.escape(disk)}\d+\b")
    return sorted(set(pattern.findall(payload)), key=lambda name: int(re.search(r"(\d+)$", name).group(1)))


def collect_sysfs_inventory(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, str]]:
    inventory: list[dict[str, str]] = []
    target_names = {name.lower() for name in PARTITIONS}
    for disk in DISKS:
        for devname in list_disk_partitions(args, store, disk):
            uevent = run_toybox_transient(args, ["cat", f"/sys/block/{disk}/{devname}/uevent"], args.timeout)
            if not uevent.ok:
                continue
            fields = parse_key_values(strip_run_payload(uevent.text))
            partname = fields.get("PARTNAME", "")
            sensitive = partname.lower() in SENSITIVE_EXCLUSIONS
            target = partname.lower() in target_names
            if sensitive:
                store.write_text(f"sysfs-{safe_name(devname)}-redacted.txt", f"DEVNAME={devname}\nPARTNAME=<sensitive-excluded>\n")
                continue
            if not target:
                continue
            size = run_toybox_transient(args, ["cat", f"/sys/block/{disk}/{devname}/size"], args.timeout)
            start = run_toybox_transient(args, ["cat", f"/sys/block/{disk}/{devname}/start"], args.timeout)
            dev_path = f"/dev/block/{devname}"
            dev_ls = run_toybox_transient(args, ["ls", "-l", dev_path], args.timeout)
            sha256 = ""
            if dev_ls.ok:
                sha = run_toybox(args, store, f"sysfs-{safe_name(devname)}-sha256", ["sha256sum", dev_path], args.capture_timeout)
                sha_line = first_payload_line(sha.text)
                sha_match = re.match(r"(?P<sha>[0-9a-fA-F]{64})\s+", sha_line)
                sha256 = sha_match.group("sha").lower() if sha_match else ""
            item = {
                "name": partname,
                "present": "true",
                "devname": fields.get("DEVNAME", devname),
                "disk": disk,
                "partn": fields.get("PARTN", ""),
                "sysfs": f"/sys/block/{disk}/{devname}",
                "devnode": dev_path if dev_ls.ok else "",
                "devnode_present": str(dev_ls.ok),
                "start_sector": first_payload_line(start.text),
                "size_sectors": first_payload_line(size.text),
                "size": str(int(first_payload_line(size.text)) * 512) if first_payload_line(size.text).isdigit() else "",
                "sha256": sha256,
            }
            inventory.append(item)
            store.write_text(f"sysfs-{safe_name(devname)}-{safe_name(partname)}.json", json.dumps(item, indent=2, sort_keys=True) + "\n")
    return sorted(inventory, key=lambda item: (item["disk"], int(item.get("partn") or "0")))


def summarize(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    pre = run_capture(args, store, "pre-selftest", ["selftest"], args.timeout)
    map_capture = run_toybox(args, store, "by-name-map", ["ls", "-l", "/dev/block/by-name"], args.timeout)
    sysfs_block_map = run_toybox(args, store, "sysfs-block-map", ["ls", "-l", "/sys/block"], args.timeout)
    parts = collect_sysfs_inventory(args, store)
    post = run_capture(args, store, "post-selftest", ["selftest"], args.timeout)

    present = [part for part in parts if part.get("present") == "true"]
    collected_sensitive = sorted(
        part["name"] for part in present if part.get("name", "").lower() in SENSITIVE_EXCLUSIONS
    )
    combined_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in store.run_dir.glob("*.txt")
    )
    forbidden = sorted(marker for marker in FORBIDDEN_OUTPUT_MARKERS if marker.lower() in combined_text.lower())
    sha_ok = [
        part for part in present
        if re.fullmatch(r"[0-9a-f]{64}", part.get("sha256", ""))
    ]
    checks = {
        "pre_selftest_fail_zero": pre.ok and selftest_fail_zero(pre.text),
        "post_selftest_fail_zero": post.ok and selftest_fail_zero(post.text),
        "by_name_map_ok_or_absent": map_capture.ok or "No such file or directory" in map_capture.text,
        "sysfs_block_map_ok": sysfs_block_map.ok,
        "partition_map_present": bool(strip_run_payload(sysfs_block_map.text)),
        "present_partition_count_positive": len(present) > 0,
        "present_partitions_have_metadata": all(
            part.get("name") and part.get("devname") and part.get("partn") and part.get("size_sectors")
            for part in present
        ),
        "existing_devnodes_have_sha256": len(sha_ok) == len([part for part in present if part.get("devnode_present") == "True"]),
        "sensitive_partitions_not_collected": not collected_sensitive,
        "forbidden_markers_absent": not forbidden,
        "no_write_gate": True,
    }
    decision = (
        "v1644-read-only-partition-metadata-captured"
        if all(checks.values())
        else "v1644-partition-metadata-review"
    )
    return {
        "cycle": "V1644",
        "type": "read-only live partition metadata/hash capture",
        "decision": decision,
        "pass": all(checks.values()),
        "checks": checks,
        "captures": {
            "pre_selftest": {"ok": pre.ok, "rc": pre.rc, "status": pre.status, "file": rel(store.path("pre-selftest.txt"))},
            "by_name_map": {"ok": map_capture.ok, "rc": map_capture.rc, "status": map_capture.status, "file": rel(store.path("by-name-map.txt"))},
            "sysfs_block_map": {"ok": sysfs_block_map.ok, "rc": sysfs_block_map.rc, "status": sysfs_block_map.status, "file": rel(store.path("sysfs-block-map.txt"))},
            "post_selftest": {"ok": post.ok, "rc": post.rc, "status": post.status, "file": rel(store.path("post-selftest.txt"))},
        },
        "partitions": parts,
        "present_partition_count": len(present),
        "sha256_partition_count": len(sha_ok),
        "collected_sensitive": collected_sensitive,
        "forbidden_markers": forbidden,
        "out_dir": rel(store.run_dir),
        "next": {
            "recommended_cycle": "V1645",
            "type": "host-only PMIC/bootloader artifact interpretation from V1644 metadata",
            "mutation": False,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Native Init V1644 Partition Metadata Capture",
        "",
        "## Summary",
        "",
        "- Cycle: `V1644`",
        "- Type: read-only live partition metadata/hash capture",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        "- Reason: collect bootloader / PMIC ownership evidence metadata without dumping or committing proprietary partitions.",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Checks",
        "",
    ]
    for key, value in result["checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Capture Files",
        "",
    ])
    for name, info in result["captures"].items():
        lines.append(f"- `{name}`: ok=`{info['ok']}` rc=`{info['rc']}` status=`{info['status']}` file=`{info['file']}`")
    lines.extend([
        "",
        "## Partition Metadata",
        "",
        "| name | devname | partn | size bytes | devnode | sha256 |",
        "|---|---|---:|---:|---|---|",
    ])
    for part in result["partitions"]:
        lines.append(
            f"| `{part.get('name', '')}` | `{part.get('devname', '')}` | "
            f"{part.get('partn', '')} | {part.get('size', '')} | "
            f"`{part.get('devnode', '')}` | `{part.get('sha256', '')}` |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        f"V1644 captured `{result['present_partition_count']}` candidate partitions from sysfs GPT metadata and `{result['sha256_partition_count']}` SHA256 values for candidates that already had exposed `/dev/block/*` nodes. This remains a metadata-only evidence gate: no partition body, firmware blob, credential, Wi-Fi HAL action, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, PCI rescan, or platform bind/unbind was performed.",
        "",
        "## Next",
        "",
        "V1645 should interpret this metadata host-only: identify which available bootloader / firmware artifacts are worth private offline strings or diff analysis, and keep raw proprietary dumps out of git. Do not design a PMIC/GPIO/GDSC write gate unless a concrete owner/control surface and sequence constraint is identified.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--capture-timeout", type=float, default=240.0)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    result = summarize(args, store)
    store.write_json("manifest.json", result)
    report = render_report(result)
    write_private_text(args.out_dir / "summary.md", report)
    write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "present_partition_count": result["present_partition_count"],
        "sha256_partition_count": result["sha256_partition_count"],
        "out_dir": result["out_dir"],
        "report": rel(args.report_path),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

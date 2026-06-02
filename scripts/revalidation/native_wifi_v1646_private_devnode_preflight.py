#!/usr/bin/env python3
"""V1646 read-only preflight for private devnode-based artifact access."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from a90ctl import ProtocolResult, bridge_exchange, run_cmdv1_command
from a90harness.evidence import EvidenceStore, write_private_text

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "tmp/wifi/v1646-private-devnode-preflight"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V1646_PRIVATE_DEVNODE_PREFLIGHT_2026-06-02.md"
TOYBOX = "/cache/bin/toybox"

SELECTED = [
    {"label": "xbl_a", "name": "xbl", "disk": "sdb", "devname": "sdb1", "reason": "early bootloader PMIC owner candidate"},
    {"label": "xbl_b", "name": "xbl", "disk": "sdc", "devname": "sdc1", "reason": "alternate early bootloader copy"},
    {"label": "aop", "name": "aop", "disk": "sdd", "devname": "sdd7", "reason": "always-on power / RPMh-side firmware candidate"},
    {"label": "devcfg", "name": "devcfg", "disk": "sdd", "devname": "sdd22", "reason": "board resource configuration candidate"},
    {"label": "abl", "name": "abl", "disk": "sdd", "devname": "sdd8", "reason": "late bootloader handoff context"},
]

REQUIRED_TOYBOX = ["mknod", "mkdir", "rm", "sha256sum", "ls", "cat"]


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
    except Exception as exc:  # noqa: BLE001 - keep failure evidence
        return Capture(False, 1, "error", f"{exc}\n", str(exc))


def run_toybox(args: argparse.Namespace,
               store: EvidenceStore,
               name: str,
               toybox_args: list[str],
               timeout: float | None = None) -> Capture:
    capture = execute(args, ["run", TOYBOX, *toybox_args], timeout if timeout is not None else args.timeout)
    store.write_text(f"{name}.txt", capture.text)
    return capture


def strip_payload(text: str) -> str:
    lines = text.splitlines()
    payload: list[str] = []
    active = False
    for line in lines:
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


def first_line(text: str) -> str:
    for line in strip_payload(text).splitlines():
        if line.strip():
            return line.strip()
    return ""


def parse_uevent(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in strip_payload(text).splitlines():
        if "=" not in line:
            continue
        key, value = line.strip().split("=", 1)
        result[key] = value
    return result


def collect_selected(args: argparse.Namespace, store: EvidenceStore, item: dict[str, str]) -> dict[str, str]:
    base = f"/sys/block/{item['disk']}/{item['devname']}"
    label = item["label"]
    uevent = run_toybox(args, store, f"{label}-uevent", ["cat", f"{base}/uevent"])
    dev = run_toybox(args, store, f"{label}-dev", ["cat", f"{base}/dev"])
    size = run_toybox(args, store, f"{label}-size", ["cat", f"{base}/size"])
    start = run_toybox(args, store, f"{label}-start", ["cat", f"{base}/start"])
    ro = run_toybox(args, store, f"{label}-ro", ["cat", f"{base}/ro"])
    fields = parse_uevent(uevent.text)
    major_minor = first_line(dev.text)
    major = ""
    minor = ""
    if re.fullmatch(r"\d+:\d+", major_minor):
        major, minor = major_minor.split(":", 1)
    return {
        **item,
        "sysfs": base,
        "uevent_ok": str(uevent.ok),
        "dev_ok": str(dev.ok),
        "size_ok": str(size.ok),
        "start_ok": str(start.ok),
        "ro_ok": str(ro.ok),
        "partname": fields.get("PARTNAME", ""),
        "partn": fields.get("PARTN", ""),
        "major_minor": major_minor,
        "major": major,
        "minor": minor,
        "size_sectors": first_line(size.text),
        "size_bytes": str(int(first_line(size.text)) * 512) if first_line(size.text).isdigit() else "",
        "start_sector": first_line(start.text),
        "read_only_flag": first_line(ro.text),
    }


def collect(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    pre = execute(args, ["selftest"], args.timeout)
    store.write_text("pre-selftest.txt", pre.text)
    toybox = run_toybox(args, store, "toybox-commands", [])
    selected = [collect_selected(args, store, item) for item in SELECTED]
    post = execute(args, ["selftest"], args.timeout)
    store.write_text("post-selftest.txt", post.text)

    toybox_words = set(re.findall(r"\b[A-Za-z0-9_.+-]+\b", strip_payload(toybox.text)))
    tool_checks = {name: name in toybox_words for name in REQUIRED_TOYBOX}
    checks = {
        "pre_selftest_fail_zero": "fail=0" in pre.text,
        "post_selftest_fail_zero": "fail=0" in post.text,
        "toybox_command_list_ok": toybox.ok,
        "required_toybox_tools_present": all(tool_checks.values()),
        "selected_count": len(selected) == len(SELECTED),
        "selected_major_minor_present": all(item["major"] and item["minor"] for item in selected),
        "selected_names_match": all(item["partname"] == item["name"] for item in selected),
        "selected_size_present": all(item["size_bytes"] for item in selected),
        "no_devnode_created": True,
        "no_partition_content_read": True,
        "no_live_write_gate": True,
    }
    decision = (
        "v1646-private-devnode-preflight-ready"
        if all(checks.values())
        else "v1646-private-devnode-preflight-review"
    )
    return {
        "cycle": "V1646",
        "type": "read-only private devnode artifact access preflight",
        "decision": decision,
        "pass": all(checks.values()),
        "checks": checks,
        "tool_checks": tool_checks,
        "selected": selected,
        "out_dir": rel(store.run_dir),
        "next": {
            "recommended_cycle": "V1647",
            "type": "private temporary-devnode SHA256 gate for selected small candidates",
            "allowed": "filesystem-only temporary devnode creation under private ignored path, sha256sum selected candidates, cleanup, no raw binary commit",
            "forbidden": "partition writes, PMIC/GPIO/GDSC writes, eSoC notify/BOOT_DONE, PCI rescan, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
        },
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Native Init V1646 Private Devnode Preflight",
        "",
        "## Summary",
        "",
        "- Cycle: `V1646`",
        "- Type: read-only private devnode artifact access preflight",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Evidence: `{result['out_dir']}`",
        "- Reason: verify whether selected high-priority partitions have enough sysfs major/minor metadata to support a later private temporary-devnode SHA256 gate.",
        "",
        "## Checks",
        "",
    ]
    for key, value in result["checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Tool Checks", ""])
    for key, value in result["tool_checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Selected Partitions",
        "",
        "| label | name | devname | major:minor | size bytes | start | ro | reason |",
        "|---|---|---|---|---:|---:|---|---|",
    ])
    for item in result["selected"]:
        lines.append(
            f"| `{item['label']}` | `{item['name']}` | `{item['devname']}` | "
            f"`{item['major_minor']}` | {item['size_bytes']} | {item['start_sector']} | "
            f"`{item['read_only_flag']}` | {item['reason']} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "V1646 does not create devnodes and does not read partition contents. It only proves the selected `xbl`, `aop`, `devcfg`, and `abl` candidates have sysfs major/minor metadata and that the required toybox helpers exist for a later private SHA256-only gate.",
        "",
        "## Next",
        "",
        "V1647 may create temporary private devnodes under ignored evidence storage, compute SHA256 for the selected small candidates, remove the devnodes, and document only hashes/metadata. Raw proprietary binaries must stay out of git. Do not write partitions or enter PMIC/GPIO/GDSC, eSoC notify/`BOOT_DONE`, PCI rescan, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping paths.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
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
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

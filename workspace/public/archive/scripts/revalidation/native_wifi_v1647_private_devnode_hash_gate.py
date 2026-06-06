#!/usr/bin/env python3
"""V1647 temporary-devnode SHA256 gate for selected bootloader artifacts."""

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
DEFAULT_OUT_DIR = REPO_ROOT / "tmp/wifi/v1647-private-devnode-hash-gate"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V1647_PRIVATE_DEVNODE_HASH_GATE_2026-06-02.md"
TOYBOX = "/cache/bin/toybox"
NODE_DIR = "/dev/a90_v1647_devnodes"

SELECTED = [
    {"label": "xbl_a", "name": "xbl", "devname": "sdb1", "major": "8", "minor": "17", "size": "4194304"},
    {"label": "xbl_b", "name": "xbl", "devname": "sdc1", "major": "8", "minor": "33", "size": "4194304"},
    {"label": "aop", "name": "aop", "devname": "sdd7", "major": "8", "minor": "55", "size": "524288"},
    {"label": "devcfg", "name": "devcfg", "devname": "sdd22", "major": "259", "minor": "9", "size": "131072"},
    {"label": "abl", "name": "abl", "devname": "sdd8", "major": "8", "minor": "56", "size": "4194304"},
]

FORBIDDEN_MARKERS = [
    " dd ",
    " if=",
    " of=",
    "BOOT_DONE",
    "rescan",
    "wpa_supplicant",
    "wificond",
    "scan ",
    "connect ",
    "dhcp",
    "google.com",
]


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


def run_cmd(args: argparse.Namespace,
            store: EvidenceStore,
            name: str,
            command: list[str],
            timeout: float | None = None) -> Capture:
    capture = execute(args, command, timeout if timeout is not None else args.timeout)
    store.write_text(f"{name}.txt", capture.text)
    return capture


def run_toybox(args: argparse.Namespace,
               store: EvidenceStore,
               name: str,
               toybox_args: list[str],
               timeout: float | None = None) -> Capture:
    return run_cmd(args, store, name, ["run", TOYBOX, *toybox_args], timeout)


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


def parse_sha(text: str) -> str:
    match = re.search(r"\b([0-9a-fA-F]{64})\b", strip_payload(text))
    return match.group(1).lower() if match else ""


def selftest_ok(text: str) -> bool:
    return "fail=0" in text


def hash_one(args: argparse.Namespace, store: EvidenceStore, item: dict[str, str]) -> dict[str, str]:
    node = f"{NODE_DIR}/{item['label']}"
    pre_rm = run_toybox(args, store, f"{item['label']}-pre-rm", ["rm", "-f", node])
    mknod = run_toybox(args, store, f"{item['label']}-mknod", ["mknod", node, "b", item["major"], item["minor"]])
    ls = run_toybox(args, store, f"{item['label']}-ls", ["ls", "-l", node])
    sha = run_toybox(args, store, f"{item['label']}-sha256", ["sha256sum", node], args.hash_timeout)
    cleanup = run_toybox(args, store, f"{item['label']}-cleanup", ["rm", "-f", node])
    return {
        **item,
        "node": node,
        "pre_rm_ok": str(pre_rm.ok),
        "mknod_ok": str(mknod.ok),
        "ls_ok": str(ls.ok),
        "sha256_ok": str(sha.ok),
        "cleanup_ok": str(cleanup.ok),
        "sha256": parse_sha(sha.text),
    }


def collect(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    pre = run_cmd(args, store, "pre-selftest", ["selftest"])
    cleanup_start = run_toybox(args, store, "cleanup-start", ["rm", "-rf", NODE_DIR])
    mkdir = run_toybox(args, store, "mkdir", ["mkdir", "-p", NODE_DIR])
    rows = [hash_one(args, store, item) for item in SELECTED]
    list_after = run_toybox(args, store, "list-after", ["ls", "-la", NODE_DIR])
    cleanup_end = run_toybox(args, store, "cleanup-end", ["rm", "-rf", NODE_DIR])
    cleanup_absent = run_toybox(args, store, "cleanup-final-absent", ["ls", "-ld", NODE_DIR])
    post = run_cmd(args, store, "post-selftest", ["selftest"])

    combined = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in store.run_dir.glob("*.txt"))
    forbidden = sorted(marker for marker in FORBIDDEN_MARKERS if marker.lower() in combined.lower())
    hashes = [row["sha256"] for row in rows if re.fullmatch(r"[0-9a-f]{64}", row["sha256"])]
    duplicate_groups: dict[str, list[str]] = {}
    for row in rows:
        duplicate_groups.setdefault(row["sha256"], []).append(row["label"])
    checks = {
        "pre_selftest_fail_zero": pre.ok and selftest_ok(pre.text),
        "post_selftest_fail_zero": post.ok and selftest_ok(post.text),
        "initial_cleanup_ok": cleanup_start.ok,
        "mkdir_ok": mkdir.ok,
        "all_mknod_ok": all(row["mknod_ok"] == "True" for row in rows),
        "all_sha256_ok": len(hashes) == len(rows),
        "all_cleanup_ok": all(row["cleanup_ok"] == "True" for row in rows) and cleanup_end.ok,
        "cleanup_final_absent": (not cleanup_absent.ok) and "No such file or directory" in cleanup_absent.text,
        "no_raw_dump_command": not forbidden,
        "no_partition_write_command": True,
        "no_wifi_or_pmic_gate": True,
    }
    decision = (
        "v1647-private-devnode-sha256-captured"
        if all(checks.values())
        else "v1647-private-devnode-sha256-review"
    )
    return {
        "cycle": "V1647",
        "type": "temporary private devnode SHA256 gate",
        "decision": decision,
        "pass": all(checks.values()),
        "checks": checks,
        "selected": rows,
        "duplicates": {key: value for key, value in duplicate_groups.items() if key and len(value) > 1},
        "forbidden_markers": forbidden,
        "captures": {
            "list_after": {"ok": list_after.ok, "file": rel(store.path("list-after.txt"))},
            "cleanup_final_absent": {"ok": cleanup_absent.ok, "file": rel(store.path("cleanup-final-absent.txt"))},
        },
        "out_dir": rel(store.run_dir),
        "next": {
            "recommended_cycle": "V1648",
            "type": "host-only hash interpretation and optional bounded strings plan",
            "mutation": False,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Native Init V1647 Private Devnode SHA256 Gate",
        "",
        "## Summary",
        "",
        "- Cycle: `V1647`",
        "- Type: temporary private devnode SHA256 gate",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Evidence: `{result['out_dir']}`",
        "- Reason: compute hashes for selected small bootloader / PMIC-owner candidates without dumping raw proprietary partitions.",
        "",
        "## Checks",
        "",
    ]
    for key, value in result["checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Hashes",
        "",
        "| label | name | devname | major:minor | size | sha256 | cleanup |",
        "|---|---|---|---|---:|---|---|",
    ])
    for row in result["selected"]:
        lines.append(
            f"| `{row['label']}` | `{row['name']}` | `{row['devname']}` | "
            f"`{row['major']}:{row['minor']}` | {row['size']} | `{row['sha256']}` | `{row['cleanup_ok']}` |"
        )
    lines.extend([
        "",
        "## Duplicate Groups",
        "",
    ])
    if result["duplicates"]:
        for digest, labels in result["duplicates"].items():
            lines.append(f"- `{digest}`: {', '.join(f'`{label}`' for label in labels)}")
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "V1647 created temporary filesystem-only devnodes, computed SHA256 for the selected small candidates, and removed the nodes. It did not dump raw partition bytes, commit proprietary binaries, write partitions, write PMIC/GPIO/GDSC state, issue eSoC notify/`BOOT_DONE`, rescan PCI, start Wi-Fi HAL, scan/connect, use credentials, run DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        "V1648 should stay host-only first: interpret the hashes, decide whether `xbl` duplicate copies match, and define a bounded strings-only or external offline analysis gate only if needed. Do not proceed to modem-rail writes or Wi-Fi HAL until an actual SDX50M power-owner hypothesis is supported.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--hash-timeout", type=float, default=60.0)
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

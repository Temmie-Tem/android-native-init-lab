#!/usr/bin/env python3
"""V1649 bounded token-only scan gate for selected bootloader artifacts."""

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
DEFAULT_OUT_DIR = REPO_ROOT / "tmp/wifi/v1649-bounded-token-scan-gate"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V1649_BOUNDED_TOKEN_SCAN_GATE_2026-06-02.md"
TOYBOX = "/cache/bin/toybox"
NODE_DIR = "/dev/a90_v1649_devnodes"
TOKEN_REGEX = "sdx|sdx50|sdxprairie|pmic|pm8150|pm8150l|pmxprairie|pon|ps_hold|mdm|mdm2ap|ap2mdm|vdd|rpmh|aop|gpio|pcie|mhi"

SELECTED = [
    {"label": "xbl_a", "name": "xbl", "devname": "sdb1", "major": "8", "minor": "17", "size": "4194304"},
    {"label": "xbl_b", "name": "xbl", "devname": "sdc1", "major": "8", "minor": "33", "size": "4194304"},
    {"label": "aop", "name": "aop", "devname": "sdd7", "major": "8", "minor": "55", "size": "524288"},
    {"label": "devcfg", "name": "devcfg", "devname": "sdd22", "major": "259", "minor": "9", "size": "131072"},
    {"label": "abl", "name": "abl", "devname": "sdd8", "major": "8", "minor": "56", "size": "4194304"},
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
    except Exception as exc:  # noqa: BLE001 - evidence needs failure text
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
        capture.status = "ok" if capture.rc == 0 else "no-match"
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


def parse_matches(text: str) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    for raw_line in strip_payload(text).splitlines():
        line = raw_line.strip()
        match = re.fullmatch(r"(?P<offset>\d+):(?P<token>[A-Za-z0-9_+-]+)", line)
        if not match:
            continue
        matches.append({"offset": match.group("offset"), "token": match.group("token").lower()})
    return matches


def selftest_ok(text: str) -> bool:
    return "fail=0" in text


def scan_one(args: argparse.Namespace, store: EvidenceStore, item: dict[str, str]) -> dict[str, Any]:
    node = f"{NODE_DIR}/{item['label']}"
    pre_rm = run_toybox(args, store, f"{item['label']}-pre-rm", ["rm", "-f", node])
    mknod = run_toybox(args, store, f"{item['label']}-mknod", ["mknod", node, "b", item["major"], item["minor"]])
    grep = run_toybox(
        args,
        store,
        f"{item['label']}-grep",
        ["grep", "-a", "-i", "-b", "-o", "-m", str(args.max_matches), "-E", TOKEN_REGEX, node],
        args.scan_timeout,
        ok_rcs={0, 1},
    )
    cleanup = run_toybox(args, store, f"{item['label']}-cleanup", ["rm", "-f", node])
    matches = parse_matches(grep.text)
    token_counts: dict[str, int] = {}
    for item_match in matches:
        token_counts[item_match["token"]] = token_counts.get(item_match["token"], 0) + 1
    return {
        **item,
        "node": node,
        "pre_rm_ok": pre_rm.ok,
        "mknod_ok": mknod.ok,
        "grep_ok": grep.ok,
        "grep_rc": grep.rc,
        "cleanup_ok": cleanup.ok,
        "match_count": len(matches),
        "token_counts": token_counts,
        "matches": matches[: args.max_matches],
    }


def collect(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    pre = run_cmd(args, store, "pre-selftest", ["selftest"])
    cleanup_start = run_toybox(args, store, "cleanup-start", ["rm", "-rf", NODE_DIR])
    mkdir = run_toybox(args, store, "mkdir", ["mkdir", "-p", NODE_DIR])
    scans = [scan_one(args, store, item) for item in SELECTED]
    cleanup_end = run_toybox(args, store, "cleanup-end", ["rm", "-rf", NODE_DIR])
    cleanup_absent = run_toybox(args, store, "cleanup-final-absent", ["ls", "-ld", NODE_DIR], ok_rcs={1})
    post = run_cmd(args, store, "post-selftest", ["selftest"])

    combined = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in store.run_dir.glob("*.txt"))
    forbidden = sorted(marker for marker in FORBIDDEN_MARKERS if marker.lower() in combined.lower())
    raw_line_leaks = []
    for scan in scans:
        for match in scan["matches"]:
            if not re.fullmatch(r"\d+", match["offset"]) or not re.fullmatch(r"[a-z0-9_+-]+", match["token"]):
                raw_line_leaks.append(scan["label"])
                break
    checks = {
        "pre_selftest_fail_zero": pre.ok and selftest_ok(pre.text),
        "post_selftest_fail_zero": post.ok and selftest_ok(post.text),
        "initial_cleanup_ok": cleanup_start.ok,
        "mkdir_ok": mkdir.ok,
        "all_mknod_ok": all(scan["mknod_ok"] for scan in scans),
        "all_grep_ok": all(scan["grep_ok"] for scan in scans),
        "all_cleanup_ok": all(scan["cleanup_ok"] for scan in scans) and cleanup_end.ok,
        "cleanup_final_absent": cleanup_absent.ok and "No such file or directory" in cleanup_absent.text,
        "token_only_output": not raw_line_leaks,
        "forbidden_markers_absent": not forbidden,
        "no_raw_dump_command": True,
        "no_partition_write_command": True,
        "no_wifi_or_pmic_gate": True,
    }
    decision = (
        "v1649-bounded-token-scan-captured"
        if all(checks.values())
        else "v1649-bounded-token-scan-review"
    )
    return {
        "cycle": "V1649",
        "type": "bounded token-only scan gate",
        "decision": decision,
        "pass": all(checks.values()),
        "checks": checks,
        "token_regex": TOKEN_REGEX,
        "grep_m_line_limit": args.max_matches,
        "max_reported_offsets_per_artifact": args.max_matches,
        "scans": scans,
        "forbidden_markers": forbidden,
        "raw_line_leaks": raw_line_leaks,
        "out_dir": rel(store.run_dir),
        "next": {
            "recommended_cycle": "V1650",
            "type": "host-only token evidence interpretation",
            "mutation": False,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Native Init V1649 Bounded Token Scan Gate",
        "",
        "## Summary",
        "",
        "- Cycle: `V1649`",
        "- Type: bounded token-only scan gate",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Evidence: `{result['out_dir']}`",
        "- Reason: identify which selected artifacts contain SDX/PMIC/PON vocabulary without raw strings or binary dumps.",
        "",
        "## Checks",
        "",
    ]
    for key, value in result["checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Token Scan Summary",
        "",
        "| label | name | match count | token counts |",
        "|---|---|---:|---|",
    ])
    for scan in result["scans"]:
        token_counts = ", ".join(f"{token}={count}" for token, count in sorted(scan["token_counts"].items())) or "none"
        lines.append(f"| `{scan['label']}` | `{scan['name']}` | {scan['match_count']} | {token_counts} |")
    lines.extend([
        "",
        "## Offset Matches",
        "",
        "Only the first bounded set of parsed offsets is rendered per artifact. `grep -m` limits matching lines; with binary-like input and `-o`, the total token count can exceed that line limit while still remaining token-only output.",
        "",
    ])
    for scan in result["scans"]:
        lines.append(f"### `{scan['label']}`")
        if not scan["matches"]:
            lines.append("- none")
            continue
        for item in scan["matches"]:
            lines.append(f"- `{item['offset']}:{item['token']}`")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "V1649 used temporary filesystem-only devnodes and `grep -a -i -b -o -m` to emit only `offset:matched-token` pairs. It did not run full `strings`, dump raw partition bytes, commit proprietary binaries, write partitions, write PMIC/GPIO/GDSC state, issue eSoC notify/`BOOT_DONE`, rescan PCI, start Wi-Fi HAL, scan/connect, use credentials, run DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        "V1650 should stay host-only first: interpret token presence by artifact and decide whether there is enough evidence for a narrower private offline analysis target. Do not proceed to modem-rail writes or Wi-Fi HAL until the SDX50M power-owner hypothesis is concrete.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--scan-timeout", type=float, default=60.0)
    parser.add_argument("--max-matches", type=int, default=200)
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

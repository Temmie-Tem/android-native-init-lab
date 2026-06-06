#!/usr/bin/env python3
"""V1178 host-only classifier for PM dependency object initialization/order parity.

This consumes V1177 live evidence, V1176 disassembly artifacts, and V1160 Android
timing to classify why the PM state-0 dependency object is already in state=1 when
native state-0 arrives.

No device contact, no PM actors, no mdm_helper, no Wi-Fi HAL, no scan/connect,
no credentials, no DHCP/routes, no external ping, no flash, no partition write.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text, write_private_json


DEFAULT_OUT_DIR = Path("tmp/wifi/v1178-pm-dependency-init-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1178-pm-dependency-init-classifier.txt")
DEFAULT_V1177 = Path("tmp/wifi/v1177-pm-dependency-flag-live-after-v490/manifest.json")
DEFAULT_V1176 = Path("tmp/wifi/v1176-pm-state3-dependency-classifier")
DEFAULT_V1160 = Path("tmp/wifi/v1160-pm-esoc-trigger-reconcile/manifest.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1177", type=Path, default=DEFAULT_V1177)
    parser.add_argument("--v1176-dir", type=Path, default=DEFAULT_V1176)
    parser.add_argument("--v1160", type=Path, default=DEFAULT_V1160)
    return parser.parse_args()


def read_text(path: Path, limit: int = 8_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        return {}


# ── Address arithmetic helpers ─────────────────────────────────────────────

def fmt_addr(a: int) -> str:
    return f"0x{a:016x}"


def classify_offset(peripheral: int, obj: int) -> str:
    delta = obj - peripheral
    if delta >= 0:
        return f"peripheral+0x{delta:x}"
    return f"peripheral-0x{abs(delta):x}"


# ── V1177 trace event extraction ───────────────────────────────────────────

LINE_RE = re.compile(
    r"(?P<comm>[^\-]+-\d+)\s+\[\d+\].*?"
    r"(?P<time>\d+\.\d+):\s+(?P<label>pm_(?:ack|dep)[^:]+):\s+(?P<rest>.+)"
)


def parse_v1177_lines(reason: str) -> list[dict[str, Any]]:
    """Extract raw uprobe lines from the V1177 manifest reason string."""
    events: list[dict[str, Any]] = []
    for match in re.finditer(r"'line': '([^']+)'", reason):
        line = match.group(1)
        m = LINE_RE.match(line)
        if not m:
            continue
        values: dict[str, str] = {}
        for kv in re.finditer(r"(\w+)=(0x[0-9a-f]+)", m.group("rest")):
            values[kv.group(1)] = kv.group(2)
        events.append(
            {
                "comm": m.group("comm").strip(),
                "time": float(m.group("time")),
                "label": m.group("label").strip(),
                "values": values,
            }
        )
    return events


def extract_addresses(events: list[dict[str, Any]]) -> dict[str, int]:
    """Extract key addresses from the trace event list."""
    out: dict[str, int] = {}
    for e in events:
        v = e["values"]
        label = e["label"]
        if label == "pm_ack_impl_client_match" and "client" in v and "peripheral" not in out:
            out["peripheral"] = int(v["client"], 16)
        if label == "pm_ack_state2_dependency_ptr" and "dependency" in v:
            out["state2_dep"] = int(v["dependency"], 16)
        if label == "pm_ack_state2_dependency_flag" and "dependency_flag" in v:
            out["state2_dep_flag"] = int(v["dependency_flag"], 16)
        if label == "pm_dep_state0_dependency_present" and "dependency" in v:
            out["state0_dep"] = int(v["dependency"], 16)
        if label == "pm_dep_state0_dependency_state_first" and "dependency_state" in v:
            if "state0_dep_state_first" not in out:
                out["state0_dep_state_first"] = int(v["dependency_state"], 16)
        if label == "pm_dep_state0_dependency_state_second" and "dependency_state" in v:
            out["state0_dep_state_second"] = int(v["dependency_state"], 16)
    return out


def extract_state_sequence(events: list[dict[str, Any]]) -> list[tuple[float, int]]:
    """Return (time, state) for each pm_ack_state_core_entry event."""
    out: list[tuple[float, int]] = []
    for e in events:
        if e["label"] == "pm_ack_state_core_entry":
            state = int(e["values"].get("state", "0xff"), 16)
            out.append((e["time"], state))
    return out


# ── Disassembly checks ────────────────────────────────────────────────────

DISASM_CHECKS = {
    "state2_dep_ptr_load_0x148": r"88e0:.*ldr\s+x\d+,\s*\[x\d+,\s*#328\]",
    "state2_dep_flag_load_0x140": r"88e8:.*ldrb\s+w\d+,\s*\[x\d+,\s*#320\]",
    "state2_dep_flag_cbz_skip": r"88ec:.*cbz\s+w\d+,\s*8988",
    "state2_dep_state_check_ne3": r"8908:.*cmp\s+w\d+,\s*#0x3",
    "state2_dep_state_check_ne2": r"892c:.*cmp\s+w\d+,\s*#0x2",
    "state2_dep_flag_set_store": r"8984:.*strb\s+wzr,\s*\[x\d+,\s*#320\]",
    "state2_flag_set_offset_0x140": r"8b94:.*strb\s+w\d+,\s*\[x\d+,\s*#320\]",
    "state0_branch_cbz": r"88cc:.*cbz\s+w\d+,\s*8a10",
    "state1_branch_beq": r"88d4:.*b\.eq\s+8b9c",
}


def check_disassembly(disasm_text: str) -> dict[str, bool]:
    results: dict[str, bool] = {}
    for key, pattern in DISASM_CHECKS.items():
        results[key] = bool(re.search(pattern, disasm_text))
    return results


# ── Android timing extraction ─────────────────────────────────────────────

def extract_android_timing(v1160: dict[str, Any]) -> dict[str, float]:
    try:
        times = v1160["analysis"]["android_v1159"]["times"]
        return {k: float(v) for k, v in times.items()}
    except (KeyError, TypeError, ValueError):
        return {}


# ── Dependency parity classification ─────────────────────────────────────

def classify_dep_parity(
    addrs: dict[str, int],
    state_seq: list[tuple[float, int]],
    android_times: dict[str, float],
) -> dict[str, Any]:
    """
    Core classifier: compare dep-object states and timing with Android.

    Returns a dict of classification findings.
    """
    peripheral = addrs.get("peripheral", 0)
    state2_dep = addrs.get("state2_dep", 0)
    state0_dep = addrs.get("state0_dep", 0)
    state2_flag = addrs.get("state2_dep_flag", -1)
    s0_state1 = addrs.get("state0_dep_state_first", -1)
    s0_state2 = addrs.get("state0_dep_state_second", -1)

    state2_times = [t for t, s in state_seq if s == 2]
    state3_times = [t for t, s in state_seq if s == 3]
    state0_times = [t for t, s in state_seq if s == 0]
    state1_times = [t for t, s in state_seq if s == 1]

    t_state2 = state2_times[0] if state2_times else None
    t_state0 = state0_times[0] if state0_times else None
    gap_s2_s0 = (t_state0 - t_state2) if (t_state0 is not None and t_state2 is not None) else None

    # Offset arithmetic
    state2_dep_offset = state2_dep - peripheral if peripheral and state2_dep else None
    state0_dep_offset = state0_dep - peripheral if peripheral and state0_dep else None

    # Android per_proxy vs per_proxy_helper timing
    pph_start = android_times.get("pm_proxy_helper_start")
    pp_start = android_times.get("per_proxy_start")
    esoc0_get = android_times.get("pm_service_esoc0_get")
    mdm_helper_start = android_times.get("mdm_helper_start")
    wlan0_time = android_times.get("wlan0")

    # Per_proxy connects within ~2s of per_proxy_helper in Android
    pp_pph_delta = (pp_start - pph_start) if (pp_start and pph_start) else None

    # Root cause classification
    gap_explanation = (
        "native per_proxy starts late (after mdm_helper esoc-0 fd), by which point "
        "per_proxy_helper has completed its own PM state machine and the dependency "
        "object at peripheral+0x40 is already in state=1; "
        "Android per_proxy connects within ~{:.1f}s of per_proxy_helper so the dependency "
        "is in an earlier state when the parent peripheral's state-0 arrives".format(
            pp_pph_delta if pp_pph_delta is not None else float("nan")
        )
    )

    # Repair strategy
    repair_strategy = (
        "Start per_proxy (pm-proxy) BEFORE per_proxy_helper's PM state machine completes "
        "(i.e., within ~2s of per_proxy_helper start, not after mdm_helper esoc-0 fd). "
        "This matches the Android timing where per_proxy_start(~8.82s) - per_proxy_helper_start(~6.67s) ≈ 2.16s. "
        "Do NOT simply remove the mdm_helper esoc-0 gate without first proving that the "
        "dependency object transitions correctly."
    )

    return {
        "peripheral": fmt_addr(peripheral) if peripheral else "unknown",
        "state2_dep_addr": fmt_addr(state2_dep) if state2_dep else "unknown",
        "state2_dep_offset": (
            f"peripheral{state2_dep_offset:+#x}" if state2_dep_offset is not None else "unknown"
        ),
        "state2_dep_flag": state2_flag,
        "state0_dep_addr": fmt_addr(state0_dep) if state0_dep else "unknown",
        "state0_dep_offset": (
            f"peripheral+0x{state0_dep_offset:x}" if state0_dep_offset is not None else "unknown"
        ),
        "state0_dep_state_first": s0_state1,
        "state0_dep_state_second": s0_state2,
        "dep_already_state1_before_state0": s0_state1 == 1,
        "state_sequence": [s for _, s in state_seq],
        "t_state2_s": t_state2,
        "t_state0_s": t_state0,
        "t_state2_to_state0_gap_s": round(gap_s2_s0, 3) if gap_s2_s0 is not None else None,
        "android_pph_start_s": pph_start,
        "android_pp_start_s": pp_start,
        "android_pp_pph_delta_s": round(pp_pph_delta, 3) if pp_pph_delta is not None else None,
        "android_esoc0_get_s": esoc0_get,
        "android_mdm_helper_start_s": mdm_helper_start,
        "android_wlan0_s": wlan0_time,
        "root_cause_gap": gap_explanation,
        "repair_strategy": repair_strategy,
        "dep_identity_hypothesis": (
            "The dependency at peripheral+0x40 (state-0 dep) is the first entry in the "
            "peripheral's client list or is per_proxy_helper's own PM session sub-object. "
            "It reaches state=1 when per_proxy_helper's own PM state machine completes. "
            "In native: per_proxy_helper starts early so this object is state=1 by t=993s. "
            "In Android: the parent peripheral's state-0 is processed before the dep "
            "reaches state=1, so the flag-set path runs and arms dep_flag=1 for the next state-2."
        ),
        "state2_dep_identity_hypothesis": (
            "The state-2 dependency at peripheral-0x180 (state2_dep) is a co-located "
            "peripheral or dependency-tracker object for the eSoC/mdm3 subsystem. "
            "Its flag field at peripheral+0x140 would be set to 1 by the state-0 flag-set path. "
            "With flag=0, the state-2 branch skips __subsystem_get(esoc0) and opens "
            "/dev/subsys_modem instead."
        ),
        "v1179_next_step": (
            "V1179 should arm uprobes BEFORE per_proxy_helper/per_proxy/pm-service startup "
            "to capture ALL peripheral state transitions from t=0, specifically: "
            "(1) when does the dep at peripheral+0x40 transition from state=0 to state=1, "
            "(2) is this transition triggered by per_proxy_helper's own ack sequence or "
            "by per_proxy connecting, (3) prove that starting per_proxy within ~2s of "
            "per_proxy_helper keeps the dep in state=0 when the parent peripheral's "
            "state-0 is processed. "
            "Keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, "
            "boot image write, partition write, and flash blocked."
        ),
    }


# ── Summary markdown ──────────────────────────────────────────────────────

def build_summary(
    c: dict[str, Any],
    disasm_checks: dict[str, bool],
    android_times: dict[str, float],
) -> str:
    rows_addr = [
        ("peripheral", c["peripheral"]),
        ("state-2 dep addr", c["state2_dep_addr"]),
        ("state-2 dep offset", c["state2_dep_offset"]),
        ("state-2 dep flag", hex(c["state2_dep_flag"]) if c["state2_dep_flag"] >= 0 else "?"),
        ("state-0 dep addr", c["state0_dep_addr"]),
        ("state-0 dep offset", c["state0_dep_offset"]),
        ("state-0 dep state (first read)", hex(c["state0_dep_state_first"]) if c["state0_dep_state_first"] >= 0 else "?"),
        ("state-0 dep state (second read)", hex(c["state0_dep_state_second"]) if c["state0_dep_state_second"] >= 0 else "?"),
        ("dep already state=1 before state-0", str(c["dep_already_state1_before_state0"])),
        ("native state sequence", str(c["state_sequence"])),
        ("native state-2 time (s)", str(c["t_state2_s"])),
        ("native state-0 time (s)", str(c["t_state0_s"])),
        ("state-2 → state-0 gap (s)", str(c["t_state2_to_state0_gap_s"])),
    ]

    rows_android = [
        ("per_proxy_helper start (s)", str(android_times.get("pm_proxy_helper_start", "?"))),
        ("per_proxy start (s)", str(android_times.get("per_proxy_start", "?"))),
        ("per_proxy − per_proxy_helper delta (s)", str(c["android_pp_pph_delta_s"])),
        ("pm_service esoc0 get (s)", str(android_times.get("pm_service_esoc0_get", "?"))),
        ("mdm_helper start (s)", str(android_times.get("mdm_helper_start", "?"))),
        ("wlan0 created (s)", str(android_times.get("wlan0", "?"))),
    ]

    rows_disasm = [(k, "pass" if v else "FAIL") for k, v in disasm_checks.items()]

    lines = [
        "# V1178 PM Dependency Init Classifier",
        "",
        "## Address Structure",
        "",
        markdown_table(["key", "value"], rows_addr),
        "",
        "## Android Timing Reference (V1160)",
        "",
        markdown_table(["key", "value"], rows_android),
        "",
        "## Disassembly Checks",
        "",
        markdown_table(["check", "result"], rows_disasm),
        "",
        "## Root Cause Gap",
        "",
        c["root_cause_gap"],
        "",
        "## Dep Identity Hypotheses",
        "",
        "### State-0 dep (peripheral+0x40)",
        "",
        c["dep_identity_hypothesis"],
        "",
        "### State-2 dep (peripheral-0x180)",
        "",
        c["state2_dep_identity_hypothesis"],
        "",
        "## Repair Strategy",
        "",
        c["repair_strategy"],
        "",
        "## Next Gate (V1179)",
        "",
        c["v1179_next_step"],
        "",
    ]
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()
    out_dir = repo_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    v1177 = load_json(args.v1177)
    v1160 = load_json(args.v1160)
    v1176_disasm = read_text(args.v1176_dir / "host" / "pm-service-state-machine-disassembly.txt")

    # Parse events from V1177
    reason = v1177.get("reason", "")
    events = parse_v1177_lines(reason)
    addrs = extract_addresses(events)
    state_seq = extract_state_sequence(events)

    # Disassembly checks
    disasm_checks = check_disassembly(v1176_disasm)

    # Android timing
    android_times = extract_android_timing(v1160)

    # Core classification
    c = classify_dep_parity(addrs, state_seq, android_times)

    # Build outputs
    summary_text = build_summary(c, disasm_checks, android_times)

    decision = "v1178-pm-dep-init-order-gap-classified"
    pass_flag = (
        addrs.get("peripheral") is not None
        and addrs.get("state2_dep") is not None
        and addrs.get("state0_dep") is not None
        and c["dep_already_state1_before_state0"]
        and all(disasm_checks.values())
        and bool(android_times)
    )

    manifest: dict[str, Any] = {
        "cycle": "v1178",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_flag,
        "device_commands_executed": False,
        "device_mutations": False,
        "pm_actor_executed": False,
        "mdm_helper_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "flash_executed": False,
        "partition_write_executed": False,
        "tracefs_write_executed": False,
        "host": collect_host_metadata(),
        "inputs": {
            "v1177": str(args.v1177),
            "v1176_dir": str(args.v1176_dir),
            "v1160": str(args.v1160),
        },
        "address_structure": {
            k: v for k, v in addrs.items()
        },
        "classification": c,
        "disasm_checks": disasm_checks,
        "android_timing": android_times,
        "next_step": c["v1179_next_step"],
        "reason": repr(c),
    }

    write_private_text(out_dir / "summary.md", summary_text)
    write_private_json(out_dir / "manifest.json", manifest)

    # Update latest pointer
    pointer = repo_path(LATEST_POINTER)
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(str(out_dir) + "\n")

    print(f"decision : {decision}")
    print(f"pass     : {pass_flag}")
    print(f"out_dir  : {out_dir}")
    print()
    print("=== Address Structure ===")
    for k, v in addrs.items():
        display = hex(v) if isinstance(v, int) else v
        print(f"  {k}: {display}")
    print()
    print("=== Native state sequence ===")
    print(f"  {c['state_sequence']}")
    print(f"  state-2 at t={c['t_state2_s']}s  state-0 at t={c['t_state0_s']}s  gap={c['t_state2_to_state0_gap_s']}s")
    print()
    print("=== Android timing ===")
    print(f"  per_proxy_helper start : {android_times.get('pm_proxy_helper_start')}s")
    print(f"  per_proxy start        : {android_times.get('per_proxy_start')}s")
    print(f"  per_proxy - pph delta  : {c['android_pp_pph_delta_s']}s")
    print(f"  pm_service esoc0 get   : {android_times.get('pm_service_esoc0_get')}s")
    print(f"  wlan0                  : {android_times.get('wlan0')}s")
    print()
    print("=== Root cause ===")
    print(f"  dep state-0: {c['state0_dep_state_first']} (state=1 → flag-set path never reached)")
    print(f"  dep flag: {c['state2_dep_flag']} (flag=0 → esoc0 branch skipped at state-2)")
    print()
    print("=== Disassembly checks ===")
    for k, v in disasm_checks.items():
        print(f"  {'pass' if v else 'FAIL'} {k}")
    print()
    print("Next gate: V1179")
    print(c["v1179_next_step"])


if __name__ == "__main__":
    main()

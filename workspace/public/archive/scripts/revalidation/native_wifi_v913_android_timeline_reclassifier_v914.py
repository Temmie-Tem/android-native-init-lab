#!/usr/bin/env python3
"""V914 host-only reclassifier for V913 Android eSoC/GPIO evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v914-v913-android-timeline-reclassifier")
LATEST_POINTER = Path("tmp/wifi/latest-v914-v913-android-timeline-reclassifier.txt")
DEFAULT_HANDOFF_MANIFEST = Path("tmp/wifi/v913-android-esoc-gpio-timeline-handoff-live/manifest.json")
DEFAULT_COLLECTOR_DIR = Path(
    "tmp/wifi/v913-android-esoc-gpio-timeline-handoff-live/v913-android-esoc-gpio-timeline-run"
)
TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")
IRQ_RE = re.compile(
    r"^\s*(?P<irq>\d+):(?P<counts>(?:\s+\d+)+)\s+(?P<controller>\S+)\s+"
    r"(?P<gpio>\d+)\s+(?P<trigger>\S+)\s+(?P<name>.+?)\s*$"
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--handoff-manifest", type=Path, default=DEFAULT_HANDOFF_MANIFEST)
    parser.add_argument("--collector-dir", type=Path, default=DEFAULT_COLLECTOR_DIR)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def command_text(collector_dir: Path, name: str) -> str:
    return read_text(collector_dir / "android" / "commands" / f"{name}.txt")


def dmesg_time(line: str) -> float | None:
    match = TIME_RE.search(line)
    return float(match.group("time")) if match else None


def first_line(text: str, pattern: str) -> dict[str, Any]:
    regex = re.compile(pattern, re.IGNORECASE)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("$ "):
            continue
        if regex.search(line):
            return {"present": True, "time": dmesg_time(line), "line": line}
    return {"present": False, "time": None, "line": ""}


def selected_lines(text: str, pattern: str, limit: int = 40) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("$ ") or line in seen:
            continue
        if regex.search(line):
            seen.add(line)
            lines.append(line)
            if len(lines) >= limit:
                break
    return lines


def parse_irq(text: str) -> dict[str, Any]:
    for line in text.splitlines():
        if "mdm status" not in line.lower():
            continue
        match = IRQ_RE.search(line)
        if not match:
            continue
        counts = [int(value) for value in match.group("counts").split()]
        return {
            "present": True,
            "line": line.strip(),
            "irq": int(match.group("irq")),
            "gpio": int(match.group("gpio")),
            "count_total": sum(counts),
            "controller": match.group("controller"),
            "trigger": match.group("trigger"),
            "name": match.group("name").strip(),
        }
    return {"present": False, "line": "", "count_total": 0}


def parse_state_values(text: str) -> list[str]:
    values: list[str] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("FILE ") or not line.endswith("/state"):
            continue
        for candidate in lines[index + 1:index + 5]:
            value = candidate.strip()
            if value and not value.startswith("FILE ") and not value.startswith("PATH "):
                values.append(value)
                break
    return values


def process_has_current_ks(text: str) -> bool:
    for line in text.splitlines():
        if not line.startswith("PROC "):
            continue
        if re.search(r"\bcomm=ks\b|cmd=/vendor/bin/ks(?:\s|$)", line):
            return True
    return False


def classify(handoff: dict[str, Any], collector_dir: Path) -> dict[str, Any]:
    dmesg_full = command_text(collector_dir, "dmesg-full")
    dmesg_focus = command_text(collector_dir, "dmesg-focus")
    interrupts = command_text(collector_dir, "interrupts")
    subsys = command_text(collector_dir, "subsys-state")
    process_fd = command_text(collector_dir, "process-fd")
    timeline_text = dmesg_full if dmesg_full else dmesg_focus
    boot_complete = bool(((handoff.get("context") or {}).get("comparison") or {}).get("boot_complete"))
    timeline = {
        "servnotif_180_connect": first_line(timeline_text, r"service_notifier_new_server: Connection established.*180 service"),
        "servnotif_74_connect": first_line(timeline_text, r"service_notifier_new_server: Connection established.*74 service"),
        "wlfw_start": first_line(timeline_text, r"cnss-daemon wlfw_start: Starting"),
        "wlan_pd_indication": first_line(timeline_text, r"msm/modem/wlan_pd.*state:"),
        "bdf_regdb": first_line(timeline_text, r"BDF file\s*:\s*regdb\.bin"),
        "bdf_bdwlan": first_line(timeline_text, r"BDF file\s*:\s*bdwlan\.bin"),
        "wlan0": first_line(timeline_text, r"\bwlan0\b"),
        "gpio142_request": first_line(timeline_text, r"msm_gpio_request: off\[142\]|gpio142|mdm2ap"),
        "pcie_link_specific": first_line(timeline_text, r"LTSSM_L0|link initialized|mhi_pci_probe|mhi_arch_esoc_ops_power_on"),
    }
    state_values = parse_state_values(subsys)
    irq = parse_irq(interrupts)
    process = {
        "mdm_helper_esoc0": bool(re.search(r"comm=mdm_helper[\s\S]{0,240}-> /dev/esoc-0", process_fd)),
        "pm_service_subsys_modem": bool(re.search(r"comm=pm-service[\s\S]{0,240}-> /dev/subsys_modem", process_fd)),
        "pm_service_subsys_esoc0": bool(re.search(r"comm=pm-service[\s\S]{0,240}-> /dev/subsys_esoc0", process_fd)),
        "current_ks": process_has_current_ks(process_fd),
        "mhi_pipe": bool(re.search(r"->\s*/dev/mhi_0305_01\.01\.00_pipe_10\b", process_fd)),
    }
    upper_positive = all(
        timeline[name]["present"]
        for name in ("wlfw_start", "wlan_pd_indication", "bdf_regdb", "bdf_bdwlan", "wlan0")
    )
    lower_postboot_negative = (
        "OFFLINING" in state_values
        and irq.get("present")
        and irq.get("count_total") == 0
        and not process["current_ks"]
        and not process["mhi_pipe"]
    )
    if boot_complete and upper_positive and lower_postboot_negative:
        decision = "v914-v913-upper-positive-lower-postboot-negative"
        pass_ok = True
        reason = (
            "V913 Android evidence proves the upper Wi-Fi bring-up sequence "
            "while post-boot mdm3/GPIO142/ks/MHI samples remain non-positive; "
            "those lower samples are not valid required success criteria for the native trigger."
        )
        next_step = (
            "Update the next native trigger gate to treat WLFW/BDF/wlan0 progression as the primary success path "
            "and collect lower eSoC markers only as diagnostics."
        )
    elif boot_complete and upper_positive:
        decision = "v914-v913-upper-positive-review-lower"
        pass_ok = True
        reason = "V913 Android evidence proves upper Wi-Fi bring-up, but lower post-boot marker classification needs review."
        next_step = "Review lower marker parsing before live native subsystem trigger."
    else:
        decision = "v914-v913-android-positive-incomplete"
        pass_ok = False
        reason = "V913 evidence does not prove the Android upper Wi-Fi positive path."
        next_step = "Recapture Android earlier or with a tighter collector."
    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "boot_complete": boot_complete,
        "timeline": timeline,
        "irq": irq,
        "subsys_state_values": state_values,
        "process": process,
        "upper_positive": upper_positive,
        "lower_postboot_negative": lower_postboot_negative,
        "selected_lines": {
            "upper_wifi": selected_lines(timeline_text, r"wlfw_start|wlan_pd|BDF file|wlan0", limit=40),
            "lower_gpio": selected_lines(timeline_text + "\n" + interrupts + "\n" + subsys, r"off\\[142\\]|mdm status|subsys9/state|OFFLINING", limit=40),
            "process_fd": selected_lines(process_fd, r"comm=mdm_helper|comm=pm-service|/dev/esoc-0|/dev/subsys_modem|/dev/subsys_esoc0|/dev/mhi", limit=40),
        },
    }


def build_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    timeline_rows = [
        [name, str(data.get("present")), str(data.get("time")), data.get("line", "")[:180]]
        for name, data in classification["timeline"].items()
    ]
    process_rows = [[name, str(value)] for name, value in classification["process"].items()]
    return "\n".join(
        [
            "# V914 V913 Android Timeline Reclassifier Summary",
            "",
            f"decision: {manifest['decision']}",
            f"pass: {manifest['pass']}",
            f"reason: {manifest['reason']}",
            f"next: {manifest['next_step']}",
            "",
            "## Process Surface",
            "",
            markdown_table(["marker", "value"], process_rows),
            "",
            "## Timeline",
            "",
            markdown_table(["marker", "present", "time", "line"], timeline_rows),
            "",
            "## IRQ / Subsystem",
            "",
            "```json",
            json.dumps(
                {
                    "irq": classification["irq"],
                    "subsys_state_values": classification["subsys_state_values"],
                    "upper_positive": classification["upper_positive"],
                    "lower_postboot_negative": classification["lower_postboot_negative"],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            "```",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    handoff = load_json(args.handoff_manifest)
    classification = classify(handoff, args.collector_dir)
    manifest = {
        "schema": "v914-v913-android-timeline-reclassifier",
        "created_at": now_iso(),
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "host": collect_host_metadata(),
        "inputs": {
            "handoff_manifest": str(args.handoff_manifest),
            "collector_dir": str(args.collector_dir),
        },
        "classification": classification,
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_bringup_executed": False,
        "credential_use_executed": False,
        "external_ping_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

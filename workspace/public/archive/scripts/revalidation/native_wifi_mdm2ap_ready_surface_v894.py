#!/usr/bin/env python3
"""V894 MDM2AP status/ready observer-surface classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v894-mdm2ap-ready-surface")
LATEST_POINTER = Path("tmp/wifi/latest-v894-mdm2ap-ready-surface.txt")
DEFAULT_V893_MANIFEST = Path("tmp/wifi/v893-esoc-post-img-xfer-classifier/manifest.json")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 30.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
SDX5XM_DTS = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/arch/arm64/boot/dts/qcom/sdx5xm-external-soc.dtsi")
SM8150_SDX50M_DTS = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/arch/arm64/boot/dts/qcom/sm8150-sdx50m.dtsi")
MDM4X_SOURCE = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc-mdm-4x.c")


ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
INTERRUPT_RE = re.compile(
    r"^\s*(?P<irq>\d+):(?P<counts>(?:\s+\d+)+)\s+(?P<controller>\S+)\s+(?P<gpio>\d+)\s+(?P<trigger>\S+)\s+(?P<name>.+?)\s*$",
    re.MULTILINE,
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v893-manifest", type=Path, default=DEFAULT_V893_MANIFEST)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--no-device", action="store_true")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
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


def line_hits(path: Path, patterns: dict[str, str]) -> dict[str, dict[str, Any]]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {name: {"present": False, "path": str(path), "line": 0, "text": ""} for name in patterns}
    lines = resolved.read_text(encoding="utf-8", errors="replace").splitlines()
    hits: dict[str, dict[str, Any]] = {}
    for name, pattern in patterns.items():
        regex = re.compile(pattern)
        found = {"present": False, "path": str(path), "line": 0, "text": ""}
        for index, line in enumerate(lines, start=1):
            if regex.search(line):
                found = {"present": True, "path": str(path), "line": index, "text": line.strip()}
                break
        hits[name] = found
    return hits


def collect_sources() -> dict[str, Any]:
    return {
        "dts": line_hits(SDX5XM_DTS, {
            "mdm2ap_status_gpio": r"qcom,mdm2ap-status-gpio\s*=\s*<.*142",
            "ap2mdm_status_gpio": r"qcom,ap2mdm-status-gpio\s*=\s*<.*135",
            "ap2mdm_soft_reset_gpio": r"qcom,ap2mdm-soft-reset-gpio",
        }),
        "sdx50m": line_hits(SM8150_SDX50M_DTS, {
            "compatible": r"compatible\s*=\s*\"qcom,ext-sdx50m\"",
            "mhi_esoc_names": r"esoc-names\s*=\s*\"mdm\"",
        }),
        "mdm4x": line_hits(MDM4X_SOURCE, {
            "status_irq": r"MDM2AP_STATUS IRQ received",
            "status_value_one": r"value\s*==\s*1",
            "ready_set": r"mdm->ready\s*=\s*true",
            "img_xfer_schedules_check": r"schedule_delayed_work.*mdm2ap_status_check_work",
        }),
    }


def device_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "echo ==sysfs-esoc==; "
        "for p in /sys/bus/esoc/devices/esoc0 /sys/devices/platform/soc/soc:qcom,mdm3/esoc0 /sys/devices/platform/soc/soc:qcom,mdm3/subsys9 /sys/bus/msm_subsys/devices/subsys9; do "
        "echo PATH=$p; $BB ls -la \"$p\" 2>&1 | $BB sed -r 's/\\x1b\\[[0-9;]*[A-Za-z]//g'; "
        "for f in dev name state uevent esoc_link esoc_name esoc_link_info firmware_name crash_count restart_level system_debug; do "
        "[ -e \"$p/$f\" ] && { echo FILE=$p/$f; $BB cat \"$p/$f\" 2>&1; echo; }; "
        "done; done; "
        "echo ==interrupts-mdm==; "
        "$BB grep -iE 'mdm status|mdm errfatal|error_ready_interrupt|qcom,smp2p| modem$' /proc/interrupts 2>&1 || true; "
        "echo ==debugfs-availability==; "
        "for p in /sys/kernel/debug/gpio /sys/kernel/debug/pinctrl /sys/kernel/debug/irq; do echo PATH=$p; $BB ls -la \"$p\" 2>&1 | $BB head -n 20; done; "
        "echo ==gpio-class==; "
        "$BB ls -la /sys/class/gpio 2>&1 | $BB head -n 80; "
        "true"
    )


def run_device(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    capture = run_capture(args, "mdm2ap-ready-surface", ["run", args.busybox, "sh", "-c", device_script(args)], timeout=args.timeout)
    payload = ANSI_RE.sub("", strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n")
    store.write_text("native/mdm2ap-ready-surface.txt", payload.rstrip() + "\n")
    return {
        "ok": capture.ok,
        "rc": capture.rc,
        "status": capture.status,
        "duration_sec": round(capture.duration_sec, 3),
        "error": capture.error,
        "file": "native/mdm2ap-ready-surface.txt",
        "text": payload,
    }


def parse_interrupts(text: str) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if re.search(r"mdm status|mdm errfatal|error_ready_interrupt", line, re.IGNORECASE)]
    mdm_status = ""
    for line in lines:
        if re.search(r"\bmdm status\b", line, re.IGNORECASE):
            mdm_status = line
            break
    parsed: dict[str, Any] = {"lines": lines, "mdm_status_line": mdm_status, "mdm_status_present": bool(mdm_status)}
    match = INTERRUPT_RE.search(mdm_status) if mdm_status else None
    if match:
        counts = [int(value) for value in match.group("counts").split()]
        parsed.update({
            "irq": int(match.group("irq")),
            "controller": match.group("controller"),
            "gpio": int(match.group("gpio")),
            "trigger": match.group("trigger"),
            "name": match.group("name").strip(),
            "count_total": sum(counts),
        })
    return parsed


def analyze_device(capture: dict[str, Any]) -> dict[str, Any]:
    text = str(capture.get("text") or "")
    return {
        "capture_ok": bool(capture.get("ok")),
        "subsys9_state_offlining": "FILE=/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state\nOFFLINING" in text
        or "FILE=/sys/bus/msm_subsys/devices/subsys9/state\nOFFLINING" in text,
        "debugfs_gpio_present": "PATH=/sys/kernel/debug/gpio\nls:" not in text,
        "gpio_class_present": "gpiochip0" in text,
        "interrupts": parse_interrupts(text),
    }


def extract_v893(manifest: dict[str, Any]) -> dict[str, Any]:
    classification = manifest.get("classification") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": manifest.get("pass", False),
        "next_gate": classification.get("next_gate", ""),
        "get_status_zero_meaning": classification.get("get_status_zero_meaning", ""),
        "boot_done_policy": classification.get("boot_done_policy", ""),
    }


def decide(v893: dict[str, Any], sources: dict[str, Any], device: dict[str, Any]) -> tuple[str, bool, str, str, dict[str, Any]]:
    source_ok = all(hit.get("present") for group in sources.values() for hit in group.values())
    interrupt = (device.get("interrupts") or {})
    device_ok = bool(device.get("capture_ok")) and bool(interrupt.get("mdm_status_present")) and interrupt.get("gpio") == 142
    classification = {
        "read_only_ready_surface": "/proc/interrupts mdm status line for GPIO 142",
        "sysfs_state_surface": "/sys/bus/msm_subsys/devices/subsys9/state remains useful but coarse",
        "debugfs_gpio_surface": "not available in current native boot",
        "next_gate": "bounded live V895 should sample mdm status IRQ count before IMG_XFER_DONE, during GET_STATUS polling, and after cleanup",
    }
    if not v893.get("pass"):
        return "v894-v893-evidence-missing", False, f"v893={v893}", "restore or rerun V893 before V894", classification
    if not source_ok:
        return "v894-source-evidence-incomplete", False, "required DTS/source markers missing", "restore staged DTS/source before observer planning", classification
    if not device_ok:
        return "v894-device-ready-surface-incomplete", False, f"device={device}", "inspect current native read-only surfaces before live observer", classification
    return (
        "v894-mdm2ap-ready-surface-classified",
        True,
        "GPIO142 mdm status IRQ is available as a read-only readiness observer",
        "implement bounded V895 helper sampling around IMG_XFER_DONE; keep BOOT_DONE blocked",
        classification,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    source_rows: list[list[Any]] = []
    for group, hits in (manifest.get("sources") or {}).items():
        for name, hit in hits.items():
            source_rows.append([group, name, hit.get("present"), hit.get("path"), hit.get("line")])
    return "\n".join([
        "# V894 MDM2AP Ready Surface Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## V893 Basis",
        "",
        markdown_table(["field", "value"], [[key, value] for key, value in manifest.get("v893", {}).items()]),
        "",
        "## Device Surface",
        "",
        markdown_table(["field", "value"], [[key, json.dumps(value, sort_keys=True)] for key, value in manifest.get("device_analysis", {}).items()]),
        "",
        "## Classification",
        "",
        markdown_table(["field", "value"], [[key, value] for key, value in manifest.get("classification", {}).items()]),
        "",
        "## Source Markers",
        "",
        markdown_table(["group", "marker", "present", "path", "line"], source_rows),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v893 = extract_v893(load_json(args.v893_manifest))
    sources = collect_sources()
    device_capture = {"ok": False, "skipped": True, "text": ""}
    if args.command == "run" and not args.no_device:
        device_capture = run_device(args, store)
    device_analysis = analyze_device(device_capture)
    decision, pass_ok, reason, next_step, classification = decide(v893, sources, device_analysis)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v893_manifest": str(args.v893_manifest),
        "v893": v893,
        "sources": sources,
        "device_capture": {key: value for key, value in device_capture.items() if key != "text"},
        "device_analysis": device_analysis,
        "classification": classification,
        "live_device_mutation": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {reason}")
    print(f"next: {next_step}")
    print(f"live_device_mutation: {manifest['live_device_mutation']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

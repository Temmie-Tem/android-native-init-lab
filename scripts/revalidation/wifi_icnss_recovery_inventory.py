#!/usr/bin/env python3
"""Inventory ICNSS/CNSS debug and recovery surfaces without writing them."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    DEFAULT_EXPECT_VERSION,
    REPO_ROOT,
    capture_to_manifest,
    collect_host_metadata,
    markdown_table,
    repo_path,
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore


ICNSS_NODE = "/sys/devices/platform/soc/18800000.qcom,icnss"
ICNSS_DRIVER = "/sys/bus/platform/drivers/icnss"
DEBUG_ROOT = "/sys/kernel/debug"

DEFAULT_V215_MANIFEST = Path("tmp/wifi/v215-icnss-cnss-lifecycle/manifest.json")
DEFAULT_V215_NATIVE_MANIFEST = Path("tmp/wifi/v215-icnss-cnss-lifecycle-native/manifest.json")
DEFAULT_V216_MANIFEST = Path("tmp/wifi/v216-service-replay-model/manifest.json")

ACTIVE_PATTERNS = (
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set)\b", re.IGNORECASE),
    re.compile(r"\bNL80211_CMD_TRIGGER_SCAN\b", re.IGNORECASE),
    re.compile(r"\bNL80211_CMD_SET_INTERFACE\b", re.IGNORECASE),
    re.compile(r"\b(?:insmod|rmmod|modprobe)\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bcmd\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bctl\.(?:start|restart)\b", re.IGNORECASE),
    re.compile(r"(?:^|[;&]\s*)(?:/[^ ]*/)?(?:cnss-daemon|cnss_diag|wificond|wpa_supplicant|hostapd)\b", re.IGNORECASE),
    re.compile(r">\s*/sys/", re.IGNORECASE),
    re.compile(r"\b(?:tee|printf|echo)\b.*\s/sys/", re.IGNORECASE),
    re.compile(r"\bmount\b|\bumount\b", re.IGNORECASE),
)

NATIVE_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 15.0),
    ("status", ["status"], 25.0),
    ("bootstatus", ["bootstatus"], 25.0),
    ("icnss-uevent", ["cat", f"{ICNSS_NODE}/uevent"], 20.0),
    ("icnss-node-stat", ["stat", ICNSS_NODE], 20.0),
    ("icnss-driver-stat", ["stat", ICNSS_DRIVER], 20.0),
    ("icnss-tree", ["run", "/cache/bin/toybox", "find", ICNSS_NODE, "-maxdepth", "8"], 45.0),
    ("icnss-driver-tree", ["run", "/cache/bin/toybox", "find", ICNSS_DRIVER, "-maxdepth", "3"], 30.0),
    ("debug-root", ["ls", DEBUG_ROOT], 20.0),
    ("debug-tree", ["run", "/cache/bin/toybox", "find", DEBUG_ROOT, "-maxdepth", "6"], 60.0),
    ("dmesg", ["run", "/cache/bin/toybox", "dmesg"], 60.0),
)

SOURCE_HINTS = (
    {
        "name": "icnss_debugfs_create",
        "risk": "debug-state",
        "hint": "ICNSS source creates debugfs root and stats/fw_debug/reg_read/reg_write variants.",
        "url": "https://android.googlesource.com/kernel/msm.git/+/03c2d42aa4bc362578b3824a81583638e2e23151/drivers/soc/qcom/icnss.c",
    },
    {
        "name": "icnss_enable_recovery",
        "risk": "ramdump-crash-evidence",
        "hint": "ICNSS source registers ramdump, SSR, and PDR recovery support during probe.",
        "url": "https://android.googlesource.com/kernel/msm/+/289f176f9259d8f663478a246542cf6be4ed3d24/drivers/soc/qcom/icnss.c",
    },
    {
        "name": "icnss_driver_model_reprobe",
        "risk": "write-only-dangerous",
        "hint": "v214 proved generic platform driver bind/unbind is not a safe recovery path.",
        "url": "https://docs.kernel.org/6.7/driver-api/driver-model/driver.html",
    },
    {
        "name": "icnss_q6_wlan_control",
        "risk": "source-hint-only",
        "hint": "ICNSS binding describes QMI WLAN on/off and PD restart interaction.",
        "url": "https://android.googlesource.com/kernel/msm/+/157ab4a1b7d2bf3275a20ee90d855bec184d742e/Documentation/devicetree/bindings/cnss/icnss.txt",
    },
)

DANGEROUS_RE = re.compile(
    r"(?:^|/)(?:bind|unbind|driver_override|reg_write|force_fw_assert|fw_assert|assert|crash|shutdown|"
    r"recovery|rejuvenate|testmode|test_mode|force_collect|trigger|restart)(?:$|/|_)",
    re.IGNORECASE,
)
STATE_RE = re.compile(
    r"(?:uevent|modalias|state|status|stats|version|firmware|pdr|ssr|service|driver|device)",
    re.IGNORECASE,
)
RAMDUMP_RE = re.compile(r"ramdump|rddm|dump", re.IGNORECASE)
DEBUG_RE = re.compile(r"debug|debugfs|fw_debug|reg_read|stats", re.IGNORECASE)
ICNSS_LINE_RE = re.compile(r"(/(?:sys|proc|dev)/[A-Za-z0-9_./,:@+-]*(?:icnss|cnss|wlan|wcss|ramdump)[A-Za-z0-9_./,:@+-]*)", re.IGNORECASE)
MODE_LINE_RE = re.compile(r"^(?P<mode>[bcdlps-][rwxStTs-]{9})\s+(?P<rest>.*?)(?P<path>/[^\s]+)\s*$")


@dataclass
class ControlEntry:
    path: str
    origin: str
    file_type: str
    mode: str
    readable: str
    writable: str
    read_attempted: bool
    risk: str
    reason: str
    source_hint: str


def default_out_dir() -> Path:
    return REPO_ROOT / "tmp" / "wifi" / "v217-icnss-debug-recovery-inventory"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", "--bridge-host", dest="host", default="127.0.0.1")
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--v215-manifest", type=Path, default=DEFAULT_V215_MANIFEST)
    parser.add_argument("--v215-native-manifest", type=Path, default=DEFAULT_V215_NATIVE_MANIFEST)
    parser.add_argument("--v216-manifest", type=Path, default=DEFAULT_V216_MANIFEST)
    parser.add_argument("--native-bridge", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    full_path = repo_path(path)
    if not full_path.exists():
        return {"missing": True, "path": str(full_path)}
    data = json.loads(full_path.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full_path)
    return data


def capture_file_text(manifest: dict[str, Any], capture_name: str) -> str:
    manifest_path = manifest.get("_manifest_path")
    if not isinstance(manifest_path, str):
        return ""
    base = Path(manifest_path).parent
    for capture in manifest.get("captures", []):
        if not isinstance(capture, dict) or capture.get("name") != capture_name:
            continue
        rel = capture.get("file")
        if not isinstance(rel, str):
            continue
        path = base / rel
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


def classification_values(manifest: dict[str, Any], key: str) -> list[str]:
    classification = manifest.get("classification")
    if not isinstance(classification, dict):
        return []
    values = classification.get(key)
    if not isinstance(values, list):
        return []
    return [str(value) for value in values]


def validate_no_active_commands() -> None:
    command_text = "\n".join(" ".join(argv) for _, argv, _ in NATIVE_COMMANDS)
    for pattern in ACTIVE_PATTERNS:
        if pattern.search(command_text):
            raise AssertionError(f"active command pattern present: {pattern.pattern}")


def redact_text(text: str) -> str:
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    text = re.sub(r"(?i)(androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|serialno)=([^\s]+)", r"\1=<redacted>", text)
    return text


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def collect_native(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    captures: list[dict[str, Any]] = []
    for name, argv, timeout in NATIVE_COMMANDS:
        capture = run_capture(args, name, argv, timeout=timeout)
        text = capture.text if capture.text else capture.error
        store.write_text(f"native/commands/{safe_name(name)}.txt", redact_text(text).rstrip() + "\n")
        data = capture_to_manifest(capture)
        data["file"] = f"native/commands/{safe_name(name)}.txt"
        data["mode"] = "native"
        captures.append(data)
    return captures


def file_type_from_mode(mode: str) -> str:
    if not mode:
        return "unknown"
    return {
        "-": "regular",
        "d": "directory",
        "l": "symlink",
        "c": "char",
        "b": "block",
        "p": "fifo",
        "s": "socket",
    }.get(mode[0], "unknown")


def mode_readable(mode: str) -> str:
    if len(mode) >= 4 and "r" in (mode[1], mode[4], mode[7]):
        return "yes"
    return "unknown"


def mode_writable(mode: str) -> str:
    if mode.startswith("l"):
        return "no"
    if len(mode) >= 4 and "w" in (mode[2], mode[5], mode[8]):
        return "yes"
    if len(mode) >= 10:
        return "no"
    return "unknown"


def classify_path(path: str, mode: str) -> tuple[str, str, str]:
    lower = path.lower()
    writable = mode_writable(mode)
    if path in {f"{ICNSS_DRIVER}/bind", f"{ICNSS_DRIVER}/unbind"} or DANGEROUS_RE.search(path):
        return "write-only-dangerous", "name matches known mutating recovery/debug control", "icnss_driver_model_reprobe"
    if lower.endswith("/power/control") or "/rfkill" in lower and lower.endswith(("/soft", "/state")):
        return "writable-unknown", "state path may accept writes and is not part of the read-only recovery model", ""
    if RAMDUMP_RE.search(path):
        return "ramdump-crash-evidence", "path appears to expose ramdump/crash evidence", "icnss_enable_recovery"
    if DEBUG_RE.search(path) or "/sys/kernel/debug" in lower:
        if writable == "yes":
            return "writable-unknown", "debug path is writable or write semantics are not proven safe", "icnss_debugfs_create"
        return "debug-state", "debug path is read-only or mode is unknown; read only with bounded output", "icnss_debugfs_create"
    if writable == "yes":
        return "writable-unknown", "writable sysfs/debugfs path with unknown semantics", ""
    if STATE_RE.search(path) or lower.startswith(ICNSS_NODE.lower()):
        return "read-only-state", "state-looking ICNSS/CNSS path", ""
    return "source-hint-only", "candidate path requires manual source correlation", ""


def extract_controls_from_text(text: str, origin: str) -> list[ControlEntry]:
    controls: dict[str, ControlEntry] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        mode = ""
        path = ""
        mode_match = MODE_LINE_RE.match(line)
        if mode_match:
            mode = mode_match.group("mode")
            path = mode_match.group("path")
        else:
            path_match = ICNSS_LINE_RE.search(line)
            if path_match:
                path = path_match.group(1).rstrip(":,")
        if not path:
            continue
        risk, reason, source_hint = classify_path(path, mode)
        controls[path] = ControlEntry(
            path=path,
            origin=origin,
            file_type=file_type_from_mode(mode),
            mode=mode or "unknown",
            readable=mode_readable(mode),
            writable=mode_writable(mode),
            read_attempted=False,
            risk=risk,
            reason=reason,
            source_hint=source_hint,
        )
    return sorted(controls.values(), key=lambda item: item.path)


def collect_manifest_candidates(v215: dict[str, Any], v215_native: dict[str, Any]) -> list[ControlEntry]:
    chunks: list[tuple[str, str]] = []
    for key in ("debug_recovery_candidates", "icnss_evidence", "log_evidence"):
        chunks.append(("v215", "\n".join(classification_values(v215, key))))
        chunks.append(("v215-native", "\n".join(classification_values(v215_native, key))))
    for name in ("icnss-tree", "icnss-driver", "debug-icnss-tree", "debug-root", "dmesg"):
        chunks.append(("v215-native", capture_file_text(v215_native, name)))

    controls: dict[str, ControlEntry] = {}
    for origin, text in chunks:
        for entry in extract_controls_from_text(text, origin):
            existing = controls.get(entry.path)
            if existing is None or existing.mode == "unknown":
                controls[entry.path] = entry
    if v215_native.get("classification", {}).get("has_icnss") or controls:
        for path in (f"{ICNSS_DRIVER}/bind", f"{ICNSS_DRIVER}/unbind"):
            risk, reason, source_hint = classify_path(path, "-w-------")
            controls[path] = ControlEntry(
                path=path,
                origin="v214/v215-known-driver-control",
                file_type="regular",
                mode="-w-------",
                readable="unknown",
                writable="yes",
                read_attempted=False,
                risk=risk,
                reason=reason,
                source_hint=source_hint,
            )
    return sorted(controls.values(), key=lambda item: item.path)


def collect_native_candidates(captures: list[dict[str, Any]]) -> list[ControlEntry]:
    controls: dict[str, ControlEntry] = {}
    for capture in captures:
        text = strip_cmdv1_text(str(capture.get("text", "")))
        for entry in extract_controls_from_text(text, "native"):
            controls[entry.path] = entry
    return sorted(controls.values(), key=lambda item: item.path)


def merge_controls(*groups: list[ControlEntry]) -> list[ControlEntry]:
    merged: dict[str, ControlEntry] = {}
    risk_rank = {
        "write-only-dangerous": 0,
        "writable-unknown": 1,
        "ramdump-crash-evidence": 2,
        "debug-state": 3,
        "read-only-state": 4,
        "source-hint-only": 5,
    }
    for group in groups:
        for entry in group:
            existing = merged.get(entry.path)
            if existing is None:
                merged[entry.path] = entry
                continue
            if risk_rank.get(entry.risk, 99) < risk_rank.get(existing.risk, 99):
                merged[entry.path] = entry
            elif existing.mode == "unknown" and entry.mode != "unknown":
                merged[entry.path] = entry
    return sorted(merged.values(), key=lambda item: item.path)


def summarize_controls(controls: list[ControlEntry]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for entry in controls:
        summary[entry.risk] = summary.get(entry.risk, 0) + 1
    return summary


def decide(v215: dict[str, Any], v216: dict[str, Any], controls: list[ControlEntry]) -> tuple[str, str, bool]:
    if v215.get("decision") != "lifecycle-map-ready":
        return "insufficient-evidence", "v215 lifecycle decision is not lifecycle-map-ready", False
    if v216.get("decision") != "replay-model-ready":
        return "insufficient-evidence", "v216 replay model is not ready", False

    summary = summarize_controls(controls)
    dangerous = summary.get("write-only-dangerous", 0) + summary.get("writable-unknown", 0)
    state = summary.get("read-only-state", 0) + summary.get("debug-state", 0) + summary.get("ramdump-crash-evidence", 0)
    if state and dangerous:
        return "state-only-inventory", "state evidence exists but writable/recovery controls remain unsafe", True
    if state:
        return "safe-control-candidate", "only read-only/state-like ICNSS controls were classified", True
    return "no-safe-control", "no usable ICNSS debug/recovery surface was identified; reboot remains recovery", True


def build_summary(manifest: dict[str, Any]) -> str:
    control_rows = []
    for entry in manifest["controls"][:40]:
        control_rows.append([
            entry["path"],
            entry["origin"],
            entry["mode"],
            entry["risk"],
            entry["reason"],
        ])
    lines = [
        "# v217 ICNSS Debug / Recovery Inventory",
        "",
        f"- generated: `{manifest['created']}`",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: `{manifest['reason']}`",
        f"- controls: `{len(manifest['controls'])}`",
        "",
        "## Risk Summary",
        "",
    ]
    for key, value in sorted(manifest["risk_summary"].items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Controls",
        "",
        markdown_table(["path", "origin", "mode", "risk", "reason"], control_rows),
        "",
        "## Source Hints",
        "",
    ])
    for hint in manifest["source_hints"]:
        lines.append(f"- `{hint['name']}`: {hint['hint']} ({hint['url']})")
    lines.extend([
        "",
        "## Guardrails",
        "",
    ])
    for guardrail in manifest["guardrails"]:
        lines.append(f"- {guardrail}")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- This inventory is not a recovery execution plan.",
        "- Writable ICNSS/debugfs paths remain denied until a later explicit opt-in plan.",
        "- `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, supplicant, scan, and connect remain blocked.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    validate_no_active_commands()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)

    v215 = load_json(args.v215_manifest)
    v215_native = load_json(args.v215_native_manifest)
    v216 = load_json(args.v216_manifest)

    captures: list[dict[str, Any]] = []
    native_controls: list[ControlEntry] = []
    if args.native_bridge:
        captures = collect_native(args, store)
        native_controls = collect_native_candidates(captures)

    manifest_controls = collect_manifest_candidates(v215, v215_native)
    controls = merge_controls(manifest_controls, native_controls)
    decision, reason, pass_ok = decide(v215, v216, controls)

    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "mode": "native" if args.native_bridge else "manifest-only",
        "inputs": {
            "v215_manifest": str(repo_path(args.v215_manifest)),
            "v215_native_manifest": str(repo_path(args.v215_native_manifest)),
            "v216_manifest": str(repo_path(args.v216_manifest)),
        },
        "captures": captures,
        "controls": [asdict(entry) for entry in controls],
        "risk_summary": summarize_controls(controls),
        "source_hints": list(SOURCE_HINTS),
        "guardrails": [
            "no ICNSS bind/unbind",
            "no ICNSS sysfs/debugfs writes",
            "no recovery/rejuvenate/shutdown/ramdump trigger writes",
            "no service start",
            "no Wi-Fi enablement",
            "no rfkill write",
            "no link-up",
            "no scan/connect",
        ],
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_json("controls.json", {"controls": manifest["controls"], "risk_summary": manifest["risk_summary"]})
    store.write_json("source-hints.json", {"source_hints": manifest["source_hints"]})
    store.write_text("summary.md", build_summary(manifest))
    print(f"{'PASS' if pass_ok else 'FAIL'} out_dir={out_dir} decision={decision} reason={reason}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

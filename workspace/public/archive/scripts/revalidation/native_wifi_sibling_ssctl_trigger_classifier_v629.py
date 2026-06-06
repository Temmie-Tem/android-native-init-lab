#!/usr/bin/env python3
"""V629 host-only safe sibling-SSCTL trigger classifier.

V628 narrowed the service-notifier 74 gap to the sibling SLPI/CDSP/ADSP SSCTL
layer. This classifier compares Android vendor init triggers, current native
source, V627 safe native evidence, and V619 unsafe direct-DSP evidence to choose
the next gate.

It does not contact the device, write sysfs, build or flash a boot image, start
daemons, start service-manager, start Wi-Fi HAL, scan/connect/link-up, use
credentials, run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v629-sibling-ssctl-trigger-classifier")
DEFAULT_VENDOR_SNAPSHOT = Path("tmp/wifi/v614-mdm3-trigger-path-classifier/native/vendor-init-readonly-snapshot.txt")
DEFAULT_NATIVE_SOURCE = Path("stage3/linux_init/v319/90_main.inc.c")
DEFAULT_NATIVE_SOURCE_ROOT = Path("stage3/linux_init")
DEFAULT_ANDROID_V622_MANIFEST = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run/manifest.json"
)
DEFAULT_NATIVE_V627_MANIFEST = Path("tmp/wifi/v627-post-180-observer-live-v2/manifest.json")
DEFAULT_NATIVE_V619_MANIFEST = Path("tmp/wifi/v619-android-order-post-sysmon-observer-run/manifest.json")
DEFAULT_V628_MANIFEST = Path("tmp/wifi/v628-service74-publisher-classifier/manifest.json")

BOOT_NODES = {
    "adsp": "/sys/kernel/boot_adsp/boot",
    "cdsp": "/sys/kernel/boot_cdsp/boot",
    "slpi": "/sys/kernel/boot_slpi/boot",
}

NON_CANDIDATE_NODES = {
    "boot_wlan": "/sys/kernel/boot_wlan/boot_wlan",
    "qcwlanstate": "/sys/wifi/qcwlanstate",
    "shutdown_wlan": "/sys/kernel/shutdown_wlan/shutdown",
}

FORBIDDEN_ACTIONS = [
    "device command",
    "sysfs write",
    "boot image build/flash",
    "DSP boot-node live retry",
    "esoc0 open",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--vendor-snapshot", type=Path, default=DEFAULT_VENDOR_SNAPSHOT)
    parser.add_argument("--native-source", type=Path, default=DEFAULT_NATIVE_SOURCE)
    parser.add_argument("--native-source-root", type=Path, default=DEFAULT_NATIVE_SOURCE_ROOT)
    parser.add_argument("--android-v622-manifest", type=Path, default=DEFAULT_ANDROID_V622_MANIFEST)
    parser.add_argument("--native-v627-manifest", type=Path, default=DEFAULT_NATIVE_V627_MANIFEST)
    parser.add_argument("--native-v619-manifest", type=Path, default=DEFAULT_NATIVE_V619_MANIFEST)
    parser.add_argument("--v628-manifest", type=Path, default=DEFAULT_V628_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {"exists": False, "path": str(repo_path(path))}
    data = json.loads(text)
    if isinstance(data, dict):
        data.setdefault("exists", True)
        data.setdefault("path", str(repo_path(path)))
        return data
    return {"exists": True, "path": str(repo_path(path)), "value": data}


def source_tree_text(root: Path) -> str:
    resolved = repo_path(root)
    if not resolved.exists():
        return ""
    parts: list[str] = []
    for path in sorted(resolved.rglob("*")):
        if path.is_file() and path.suffix in {".c", ".h"}:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if any(node in text for node in (*BOOT_NODES.values(), *NON_CANDIDATE_NODES.values())):
                parts.append(f"A90_SOURCE_FILE:{path.relative_to(repo_path('.'))}\n{text}")
    return "\n".join(parts)


def context_line(text: str, pattern: str) -> str:
    regex = re.compile(pattern, re.I)
    for line in text.splitlines():
        if regex.search(line):
            return line.strip()
    return "missing"


def context_block(text: str, needle: str, before: int = 6, after: int = 4) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if needle in line:
            start = max(0, index - before)
            end = min(len(lines), index + after + 1)
            return "\n".join(lines[start:end])
    return ""


def find_write_contexts(snapshot: str) -> dict[str, dict[str, Any]]:
    contexts: dict[str, dict[str, Any]] = {}
    for name, node in BOOT_NODES.items():
        block = context_block(snapshot, f"write {node} 1")
        contexts[name] = {
            "node": node,
            "android_write_present": f"write {node} 1" in snapshot,
            "android_context": block,
            "android_phase": "early-boot" if re.search(r"on early-boot[\s\S]{0,600}" + re.escape(f"write {node} 1"), snapshot) else "unknown",
            "native_source_ref_present": False,
            "native_late_live_safe": False,
        }
    return contexts


def native_source_summary(native_tree: str) -> dict[str, Any]:
    refs = {
        name: node in native_tree
        for name, node in BOOT_NODES.items()
    }
    non_candidate_refs = {
        name: node in native_tree
        for name, node in NON_CANDIDATE_NODES.items()
    }
    return {
        "boot_node_refs": refs,
        "non_candidate_refs": non_candidate_refs,
        "any_boot_node_ref": any(refs.values()),
        "first_boot_ref": context_line(native_tree, r"/sys/kernel/boot_(adsp|cdsp|slpi)/boot"),
    }


def android_summary(android: dict[str, Any]) -> dict[str, Any]:
    summary = android.get("android_summary") or {}
    counts = summary.get("counts") or {}
    deltas = summary.get("deltas_ms") or {}
    return {
        "decision": android.get("decision"),
        "pass": android.get("pass"),
        "has_sibling_sysmon": all(int(counts.get(marker, 0) or 0) > 0 for marker in ("sysmon_slpi", "sysmon_cdsp", "sysmon_adsp")),
        "has_service74": int(counts.get("service_notifier_74", 0) or 0) > 0,
        "counts": counts,
        "deltas_ms": {
            "sysmon_modem_to_sysmon_slpi": deltas.get("sysmon_modem_to_sysmon_slpi"),
            "sysmon_modem_to_sysmon_cdsp": deltas.get("sysmon_modem_to_sysmon_cdsp"),
            "sysmon_modem_to_sysmon_adsp": deltas.get("sysmon_modem_to_sysmon_adsp"),
            "service_notifier_180_to_service_notifier_74": deltas.get("service_notifier_180_to_service_notifier_74"),
        },
    }


def native_v627_summary(native: dict[str, Any]) -> dict[str, Any]:
    live = native.get("live") or {}
    observer = live.get("post_180_observer") or {}
    counts = observer.get("counts") or {}
    return {
        "decision": native.get("decision"),
        "pass": native.get("pass"),
        "has_sibling_sysmon": any(int(counts.get(marker, 0) or 0) > 0 for marker in ("sysmon_slpi", "sysmon_cdsp", "sysmon_adsp")),
        "has_service_locator": int(counts.get("service_locator", 0) or 0) > 0 or "servloc:" in str(live.get("dmesg_delta") or ""),
        "has_service180": int(counts.get("service_notifier_180", 0) or 0) > 0,
        "has_service74": int(counts.get("service_notifier_74", 0) or 0) > 0,
        "post_180_window_sec": observer.get("observed_post_180_window_sec"),
        "kernel_warning": int(counts.get("kernel_warning", 0) or 0),
        "wifi_bringup_executed": native.get("wifi_bringup_executed"),
        "counts": counts,
    }


def native_v619_summary(native: dict[str, Any]) -> dict[str, Any]:
    live = native.get("live") or {}
    dsp = live.get("dsp_counts") or {}
    marker_counts = ((live.get("markers") or {}).get("counts") or {})
    return {
        "decision": native.get("decision"),
        "pass": native.get("pass"),
        "boot_nodes_written": live.get("boot_nodes_written") or {},
        "has_sibling_sysmon": all(int(dsp.get(marker, 0) or 0) > 0 for marker in ("slpi_sysmon", "cdsp_sysmon", "adsp_sysmon")),
        "has_service74": int(dsp.get("service_notifier_74", 0) or 0) > 0,
        "kernel_warning": int(marker_counts.get("kernel_warning", 0) or 0),
        "dsp_counts": dsp,
    }


def candidate_rows(manifest: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    native_refs = manifest["native_source"]["boot_node_refs"]
    for name, candidate in manifest["android_boot_candidates"].items():
        rows.append([
            name,
            candidate["node"],
            candidate["android_phase"],
            "present" if candidate["android_write_present"] else "missing",
            "present" if native_refs.get(name) else "missing",
            "boot-time opt-in only; late live retry blocked",
        ])
    for name, node in NON_CANDIDATE_NODES.items():
        rows.append([
            name,
            node,
            "not-now",
            "context-only",
            "n/a",
            "blocked until service 74/WLAN-PD or firmware-ready advances",
        ])
    return rows


def evidence_rows(manifest: dict[str, Any]) -> list[list[str]]:
    android = manifest["android_v622"]
    native_v627 = manifest["native_v627"]
    native_v619 = manifest["native_v619"]
    native_source = manifest["native_source"]
    return [
        [
            "Android trigger contract",
            "early-boot DSP writes",
            (
                f"adsp/cdsp/slpi writes={manifest['android_all_boot_candidates_present']}; "
                f"sibling_sysmon={android['has_sibling_sysmon']}; service74={android['has_service74']}"
            ),
            "candidate is Android-equivalent boot-time path, not late live write",
        ],
        [
            "Native v319 source",
            "missing equivalent",
            (
                f"any_boot_node_ref={native_source['any_boot_node_ref']}; "
                f"first_ref={native_source['first_boot_ref']}"
            ),
            "native boot image does not currently perform the Android-equivalent early writes",
        ],
        [
            "V627 safe path",
            "modem-only lower partial positive",
            (
                f"service_locator={native_v627['has_service_locator']}; "
                f"service180={native_v627['has_service180']}; service74={native_v627['has_service74']}; "
                f"sibling_sysmon={native_v627['has_sibling_sysmon']}"
            ),
            "needs a lower sibling trigger before HAL/connect",
        ],
        [
            "V619 late direct write",
            "unsafe negative",
            (
                f"boot_nodes={native_v619['boot_nodes_written']}; "
                f"sibling_sysmon={native_v619['has_sibling_sysmon']}; "
                f"kernel_warning={native_v619['kernel_warning']}; service74={native_v619['has_service74']}"
            ),
            "do not repeat late direct boot-node live retry",
        ],
        [
            "Next gate",
            "bounded boot-time opt-in proof",
            "requires rollback image, rescue path, marker-only success, and no Wi-Fi bring-up",
            "prepare V630 boot image experiment instead of HAL/qcwlanstate/connect",
        ],
    ]


def classify(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    android = manifest["android_v622"]
    native_v627 = manifest["native_v627"]
    native_v619 = manifest["native_v619"]
    native_source = manifest["native_source"]
    candidates_present = manifest["android_all_boot_candidates_present"]
    native_missing_equiv = not native_source["any_boot_node_ref"]
    safe_partial_positive = (
        native_v627["has_service_locator"]
        and native_v627["has_service180"]
        and not native_v627["has_service74"]
        and not native_v627["has_sibling_sysmon"]
        and native_v627["kernel_warning"] == 0
    )
    late_live_unsafe = (
        native_v619["has_sibling_sysmon"]
        and native_v619["kernel_warning"] > 0
        and not native_v619["has_service74"]
    )
    android_contract_matches_gap = android["has_sibling_sysmon"] and android["has_service74"]
    if candidates_present and native_missing_equiv and safe_partial_positive and late_live_unsafe and android_contract_matches_gap:
        return (
            "v629-boot-time-sibling-ssctl-candidate-classified",
            True,
            (
                "Android's visible sibling-SSCTL trigger is early-boot ADSP/CDSP/SLPI boot-node writes; "
                "native v319 lacks an equivalent boot-time path, V627 proves the safe modem-only path stops at service 180, "
                "and V619 proves late direct writes are unsafe and still do not publish service 74."
            ),
            "V630 should be a rollback-ready, opt-in boot-time one-shot sibling-SSCTL proof; keep HAL/qcwlanstate/connect blocked",
        )
    return (
        "v629-sibling-ssctl-trigger-evidence-gap",
        False,
        (
            f"candidates_present={candidates_present} native_missing_equiv={native_missing_equiv} "
            f"safe_partial_positive={safe_partial_positive} late_live_unsafe={late_live_unsafe} "
            f"android_contract_matches_gap={android_contract_matches_gap}"
        ),
        "refresh Android/native evidence before designing a boot-time proof",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    snapshot = read_text(args.vendor_snapshot)
    native_tree = source_tree_text(args.native_source_root)
    android_boot_candidates = find_write_contexts(snapshot)
    native_source = native_source_summary(native_tree + "\n" + read_text(args.native_source))
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "inputs": {
            "vendor_snapshot": str(repo_path(args.vendor_snapshot)),
            "native_source": str(repo_path(args.native_source)),
            "native_source_root": str(repo_path(args.native_source_root)),
            "android_v622_manifest": str(repo_path(args.android_v622_manifest)),
            "native_v627_manifest": str(repo_path(args.native_v627_manifest)),
            "native_v619_manifest": str(repo_path(args.native_v619_manifest)),
            "v628_manifest": str(repo_path(args.v628_manifest)),
        },
        "v628": {
            "decision": load_json(args.v628_manifest).get("decision"),
            "pass": load_json(args.v628_manifest).get("pass"),
        },
        "android_boot_candidates": android_boot_candidates,
        "android_all_boot_candidates_present": all(item["android_write_present"] for item in android_boot_candidates.values()),
        "native_source": native_source,
        "android_v622": android_summary(load_json(args.android_v622_manifest)),
        "native_v627": native_v627_summary(load_json(args.native_v627_manifest)),
        "native_v619": native_v619_summary(load_json(args.native_v619_manifest)),
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "sysfs_writes_executed": False,
        "boot_image_write_executed": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
    }
    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v629-sibling-ssctl-trigger-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V629 host-only classifier",
        )
    else:
        decision, pass_ok, reason, next_step = classify(manifest)
    manifest.update({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
    })
    manifest["candidate_rows"] = candidate_rows(manifest)
    manifest["evidence_rows"] = evidence_rows(manifest)
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V629 Sibling-SSCTL Trigger Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- sysfs_writes_executed: `{manifest['sysfs_writes_executed']}`",
        f"- boot_image_write_executed: `{manifest['boot_image_write_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Evidence Matrix",
        "",
        markdown_table(["subject", "classification", "evidence", "next"], manifest["evidence_rows"]),
        "",
        "## Candidate Matrix",
        "",
        markdown_table(["name", "node", "android_phase", "android", "native", "classification"], manifest["candidate_rows"]),
        "",
        "## Android Candidate Contexts",
        "",
        "\n\n".join(
            f"### {name}\n\n```text\n{candidate['android_context'] or 'missing'}\n```"
            for name, candidate in manifest["android_boot_candidates"].items()
        ),
        "",
        "## Timing Summary",
        "",
        "### Android V622",
        "",
        markdown_table(["key", "value"], [[key, str(value)] for key, value in manifest["android_v622"]["deltas_ms"].items()]),
        "",
        "### Native V627",
        "",
        markdown_table(["key", "value"], [[key, str(value)] for key, value in manifest["native_v627"].items() if key not in {"counts"}]),
        "",
        "### Native V619",
        "",
        markdown_table(["key", "value"], [[key, str(value)] for key, value in manifest["native_v619"].items() if key not in {"dsp_counts"}]),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

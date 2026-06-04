#!/usr/bin/env python3
"""V2099 host-only reparse of the V2098 tombstone/vendor-perms handoff."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_wifi_tftp_tombstone_vendor_perms_handoff_v2098 as prev2098


CYCLE = "V2099"
REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2098-tftp-tombstone-rfs-vendor-perms-handoff"
SOURCE_HANDOFF_DIR = SOURCE_OUT_DIR / "v2097-handoff"
SOURCE_MANIFEST = SOURCE_OUT_DIR / "manifest.json"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2099-tftp-tombstone-vendor-perms-postparse"
MANIFEST_PATH = OUT_DIR / "manifest.json"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2099_TFTP_TOMBSTONE_VENDOR_PERMS_POSTPARSE_2026-06-05.md"
)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def intish(value: object) -> int:
    return prev2098.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2098.markdown_table(headers, rows)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def helper_text() -> str:
    parts: list[str] = []
    for path in (
        SOURCE_HANDOFF_DIR / "test-v1393-helper-result.stdout.txt",
        SOURCE_HANDOFF_DIR / "test-v1393-helper-result.stderr.txt",
        SOURCE_HANDOFF_DIR / "test-v1393-log.stdout.txt",
        SOURCE_HANDOFF_DIR / "test-v1393-summary.stdout.txt",
    ):
        if path.exists():
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and " " not in key:
            fields[key] = value.strip()
    return fields


def get_path_snapshot(fields: dict[str, str], name: str) -> dict[str, Any]:
    prefix = f"wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.{name}"
    return {
        "absolute": fields.get(f"{prefix}.absolute", ""),
        "exists": intish(fields.get(f"{prefix}.exists")),
        "is_dir": intish(fields.get(f"{prefix}.is_dir")),
        "mode": fields.get(f"{prefix}.mode", ""),
        "uid": intish(fields.get(f"{prefix}.uid")),
        "gid": intish(fields.get(f"{prefix}.gid")),
        "statfs_ok": intish(fields.get(f"{prefix}.statfs_ok")),
        "fs_type": fields.get(f"{prefix}.fs_type", ""),
        "errno": intish(fields.get(f"{prefix}.errno")),
    }


def collect_tombstone(fields: dict[str, str], text: str) -> dict[str, Any]:
    paths = {name: get_path_snapshot(fields, name) for name in ("tombstones", "rfs", "modem", "lpass", "tn")}
    tombstone_auto_dir = prev2098.count_lines(text, "Failed to auto_dir", "/data/vendor/tombstones")
    tombstone_mkdir = prev2098.count_lines(text, "mkdir failed", "/data/vendor/tombstones")
    persist_auto_dir = prev2098.count_lines(text, "Failed to auto_dir", "/mnt/vendor/persist/rfs")
    persist_mkdir = prev2098.count_lines(text, "mkdir failed", "/mnt/vendor/persist/rfs")
    vendor_perms = intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.vendor_rfs_perms")) == 1
    safe = (
        intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.enabled")) == 1
        and intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.vendor_rfs_perms")) == 1
        and intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.enabled")) == 1
        and vendor_perms
        and intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.rootfs_namespace_only")) == 1
        and intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.sda29_write")) == 0
        and intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.ota_ruleset_created")) == 0
        and all(path["exists"] == 1 and path["is_dir"] == 1 for path in paths.values())
        and all(path["uid"] == 2903 and path["gid"] == 2903 for path in paths.values())
    )
    return {
        "enabled": intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.enabled")),
        "pre_enabled": intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.enabled")),
        "vendor_rfs_perms": 1 if vendor_perms else 0,
        "rootfs_namespace_only": intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.rootfs_namespace_only")),
        "sda29_write": intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.sda29_write")),
        "ota_ruleset_created": intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.ota_ruleset_created")),
        "paths": paths,
        "safe": safe,
        "auto_dir_error_count": tombstone_auto_dir,
        "mkdir_failed_count": tombstone_mkdir,
        "total_auto_dir_error_count": text.count("Failed to auto_dir"),
        "total_mkdir_failed_count": text.count("mkdir failed"),
        "persist_auto_dir_error_count": persist_auto_dir,
        "persist_mkdir_failed_count": persist_mkdir,
        "tombstone_token_count": text.count("/data/vendor/tombstones"),
    }


def classify(base: dict[str, Any], details: dict[str, Any]) -> dict[str, Any]:
    tombstone = details.get("tftp_tombstone_rfs_tmpfs") if isinstance(details.get("tftp_tombstone_rfs_tmpfs"), dict) else {}
    branch = details.get("tftp_tombstone_branch") if isinstance(details.get("tftp_tombstone_branch"), dict) else {}
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    tombstone_auto_dir = intish(tombstone.get("auto_dir_error_count"))
    tombstone_mkdir = intish(tombstone.get("mkdir_failed_count"))
    persist_auto_dir = intish(tombstone.get("persist_auto_dir_error_count"))
    persist_mkdir = intish(tombstone.get("persist_mkdir_failed_count"))
    server_payload = str(branch.get("server_check", {}).get("payload", ""))
    post_up_server = branch.get("server_after_wlan_pd_ms")
    wlanmdsp_seen = bool(base.get("wlanmdsp_seen"))
    ota_seen = bool(base.get("ota_seen"))
    fw_ready = intish(cascade.get("fw_ready")) > 0
    wlan0 = intish(cascade.get("wlan0")) > 0

    if tombstone_auto_dir == 0 and tombstone_mkdir == 0 and (persist_auto_dir > 0 or persist_mkdir > 0) and not wlanmdsp_seen and not ota_seen:
        label = "tombstone-cleared-persist-rfs-auto-dir-still-fails-post-up-server-check"
        reason = (
            "vendor-owned tombstone dirs cleared tombstone auto-dir errors, but tftp_server still hit "
            "persist-RFS auto-dir EACCES and native still only produced a late post-UP server_check with no ota/wlanmdsp"
        )
    elif wlan0:
        label = "postparse-wlan0-progress"
        reason = "native reached wlan0 in the source handoff"
    elif fw_ready:
        label = "postparse-fw-ready-progress"
        reason = "native reached FW_READY in the source handoff"
    else:
        label = str(base.get("label", "postparse-review"))
        reason = str(base.get("reason", "host-only postparse preserved the source classification"))

    passed = bool(base.get("pass", True))
    return {
        **base,
        "decision": f"v2099-{label}-host-postparse-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "tombstone_auto_dir_error_count": tombstone_auto_dir,
        "tombstone_mkdir_failed_count": tombstone_mkdir,
        "persist_auto_dir_error_count": persist_auto_dir,
        "persist_mkdir_failed_count": persist_mkdir,
        "server_check_payload": server_payload,
        "server_after_wlan_pd_ms": post_up_server,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    tombstone = details.get("tftp_tombstone_rfs_tmpfs", {}) if isinstance(details.get("tftp_tombstone_rfs_tmpfs"), dict) else {}
    branch = details.get("tftp_tombstone_branch", {}) if isinstance(details.get("tftp_tombstone_branch"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    summary = prev2098.prev2096.prev2083.logdw_summary(details)
    paths = tombstone.get("paths", {}) if isinstance(tombstone.get("paths"), dict) else {}
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["source_steps"]
    ]
    return "\n".join([
        "# Native Init V2099 TFTP Tombstone Vendor-Perms Postparse",
        "",
        "## Summary",
        "",
        "- Cycle: `V2099`",
        "- Type: host-only reparse of V2098; no device boot, flash, capture, or mutation was run.",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Source manifest: `{manifest['source_manifest']}`",
        f"- Source evidence: `{manifest['source_out_dir']}`",
        "",
        "## Corrected Matrix",
        "",
        markdown_table(
            ["area", "value", "detail"],
            [
                ["tombstone_auto_dir", classification.get("tombstone_auto_dir_error_count"), f"mkdir_failed={classification.get('tombstone_mkdir_failed_count')} tokens={tombstone.get('tombstone_token_count')}"],
                ["persist_rfs_auto_dir", classification.get("persist_auto_dir_error_count"), f"mkdir_failed={classification.get('persist_mkdir_failed_count')} total_auto_dir={tombstone.get('total_auto_dir_error_count')}"],
                ["server_check", classification.get("server_check_payload"), f"after_wlan_pd_ms={classification.get('server_after_wlan_pd_ms')} logdw={branch.get('logdw_server_check')}"],
                ["ota_firewall", classification.get("ota_seen"), f"logdw={branch.get('logdw_ota_firewall')} file={branch.get('ota', {}).get('index')}"],
                ["wlanmdsp", classification.get("wlanmdsp_seen"), f"logdw={branch.get('logdw_wlanmdsp')} summary={summary.get('wlanmdsp')}/{summary.get('fallback_wlanmdsp')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## Tombstone Paths",
        "",
        markdown_table(
            ["path", "exists", "dir", "mode", "uid", "gid", "fs"],
            [
                [name, item.get("exists"), item.get("is_dir"), item.get("mode"), item.get("uid"), item.get("gid"), item.get("fs_type")]
                for name, item in paths.items()
                if isinstance(item, dict)
            ],
        ),
        "",
        "## Interpretation",
        "",
        "- V2098 should not be read as `tombstone auto-dir still fails`: no captured `Failed to auto_dir` or `mkdir failed` line targets `/data/vendor/tombstones` after vendor-perms parity.",
        "- The remaining `tftp_server` startup failures target `/mnt/vendor/persist/rfs/{shared,msm/mpss,msm/adsp}`.",
        "- The producer gap is unchanged: native still reaches `wlan_pd` UP and an `icnss_qmi` connection, but the Android-order `ota_firewall -> wlanmdsp` branch does not appear and `server_check.txt` remains late post-UP.",
        "- MAC/macloader remains bounded as downstream/cosmetic: no real `icnss: Assigning MAC from Macloader` appeared incidentally in this source capture.",
        "",
        "## Source Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- Host-only parse; no new adb command, reboot, test boot, flash, QMI send, DIAG, strace, QRTR matrix, ptrace, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or off-path eSoC/PCIe/GDSC/PMIC/GPIO action was run.",
        "",
    ])


def main() -> int:
    source = load_json(SOURCE_MANIFEST)
    handoff = load_json(REPO_ROOT / source["handoff_manifest"])
    hook = prev2098.artifact_hook_check()
    text = helper_text()
    fields = parse_fields(text)
    details = dict(source["details"])
    details["tftp_tombstone_rfs_tmpfs"] = collect_tombstone(fields, text)
    details["tftp_tombstone_branch"] = prev2098.prev2096.collect_tftp_branch(fields, details)
    base = prev2098.classify(handoff, hook, source["steps"], details)
    classification = classify(base, details)
    manifest = {
        "cycle": CYCLE,
        "created": datetime.now(timezone.utc).isoformat(),
        "source_manifest": rel(SOURCE_MANIFEST),
        "source_out_dir": rel(SOURCE_OUT_DIR),
        "source_decision": source.get("decision"),
        "source_label": source.get("label"),
        "source_steps": source.get("steps", []),
        "artifact_hook": hook,
        "details": details,
        "classification": classification,
        "decision": classification["decision"],
        "label": classification["label"],
        "pass": classification["pass"],
        "reason": classification["reason"],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    print(f"PASS label={manifest['label']} out_dir={rel(OUT_DIR)} report={rel(REPORT_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""V965 host-only route classifier after V963/V964 post-provider trigger stall."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v965-v964-route-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v965-v964-route-classifier.txt")
DEFAULT_V964 = Path("tmp/wifi/v964-v963-post-provider-trigger-classifier/manifest.json")
DEFAULT_V960_REPORT = Path("docs/reports/NATIVE_INIT_V960_V959_FULL_SURFACE_CLASSIFIER_2026-05-26.md")
DEFAULT_V919_REPORT = Path("docs/reports/NATIVE_INIT_V919_SDX50M_SOFT_RESET_BLOCKER_CLASSIFIER_2026-05-26.md")
DEFAULT_V580_REPORT = Path("docs/reports/NATIVE_INIT_V580_POSTFLIGHT_ICNSS_CLASSIFIER_2026-05-22.md")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v964", type=Path, default=DEFAULT_V964)
    parser.add_argument("--v960-report", type=Path, default=DEFAULT_V960_REPORT)
    parser.add_argument("--v919-report", type=Path, default=DEFAULT_V919_REPORT)
    parser.add_argument("--v580-report", type=Path, default=DEFAULT_V580_REPORT)
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    return json.loads(text)


def classify(v964: dict[str, Any], v960: str, v919: str, v580: str) -> dict[str, Any]:
    checks = {
        "v964_trigger_stalls_in_sdx50m_reset": (
            v964.get("decision") == "v964-post-provider-trigger-stalls-in-sdx50m-reset"
            and bool(v964.get("pass"))
        ),
        "v964_no_wifi_bringup": not bool((v964.get("summary") or {}).get("wifi_bringup_executed")),
        "v960_provider_cnss_netlink_repaired": all(
            token in v960
            for token in (
                "provider lifecycle or CNSS netlink reachability",
                "The remaining blocker is",
                "the post-provider WLFW path",
                "MHI devices, WLFW/BDF, and `wlan0` remain absent",
            )
        ),
        "v919_android_wlfw_precedes_esoc0": all(
            token in v919
            for token in (
                "cnss-daemon wlfw_start: Starting",
                "__subsystem_get(): __subsystem_get: esoc0 count:0",
                "Android orders vendor.mdm_helper and cnss-daemon wlfw_start before esoc0 subsystem_get",
            )
        ),
        "v919_direct_trigger_already_demoted": "do not repeat /dev/subsys_esoc0 open" in v919,
        "v580_qcwlanstate_retry_demoted": all(
            token in v580
            for token in (
                "qcwlanstate EINVAL",
                "icnss: Modules not initialized just return",
                "Keep qcwlanstate retry, `IWifi.start()`, scan, connect, and ping blocked",
            )
        ),
    }
    passed = all(checks.values())
    return {
        "decision": "v965-select-wlfw-start-trigger-attribution"
        if passed
        else "v965-route-classifier-incomplete",
        "pass": passed,
        "reason": (
            "V963/V964 confirms direct post-provider /dev/subsys_esoc0 still stalls; existing Android evidence shows cnss-daemon wlfw_start must precede esoc0 subsystem_get, while qcwlanstate/IWifi retries remain demoted"
            if passed
            else "missing checks: " + ", ".join(name for name, ok in checks.items() if not ok)
        ),
        "next_step": (
            "build V966 host-only Android wlfw_start trigger attribution from existing same-boot Android dmesg/process evidence before any new live trigger"
            if passed
            else "repair evidence inputs before selecting the next live gate"
        ),
        "checks": checks,
        "selected_route": {
            "do_not_repeat": [
                "blind /dev/subsys_esoc0 open",
                "qcwlanstate ON retry",
                "IWifi.start retry",
                "Wi-Fi HAL scan/connect",
                "credential/DHCP/external ping",
            ],
            "next_focus": [
                "cnss-daemon wlfw_start trigger source",
                "Android event ordering immediately before wlfw_start",
                "whether HAL/framework, qcwlanstate, init property, or mdm_helper queue causes wlfw_start",
            ],
        },
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [(name, "PASS" if ok else "FAIL") for name, ok in manifest["checks"].items()]
    route = manifest["selected_route"]
    return "\n".join(
        [
            "# V965 V964 Route Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next: {manifest['next_step']}",
            "",
            markdown_table(["check", "result"], rows),
            "",
            "## Do Not Repeat",
            "",
            *[f"- {item}" for item in route["do_not_repeat"]],
            "",
            "## Next Focus",
            "",
            *[f"- {item}" for item in route["next_focus"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    v964 = load_json(args.v964)
    v960 = read_text(args.v960_report)
    v919 = read_text(args.v919_report)
    v580 = read_text(args.v580_report)
    classification = classify(v964, v960, v919, v580)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v964": str(repo_path(args.v964)),
            "v960_report": str(repo_path(args.v960_report)),
            "v919_report": str(repo_path(args.v919_report)),
            "v580_report": str(repo_path(args.v580_report)),
        },
        "device_commands_executed": False,
        "device_mutations": False,
        **classification,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""V1857 non-executing artifact plumbing for the v356 SDX50M bridge skeleton."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1857"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1857-sdx50m-bridge-artifact-plumbing"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1857_SDX50M_BRIDGE_ARTIFACT_PLUMBING_2026-06-03.md"
)
V1220_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1220-cnss-daemon-sdx50m-patch"
    / "manifest.json"
)
V1856_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1856-sdx50m-bridge-v356-delta-skeleton"
    / "manifest.json"
)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def default_artifact_path() -> Path:
    manifest = load_json(V1220_MANIFEST)
    return resolve_path(Path(str(manifest.get("output", ""))))


def default_test_image_path() -> Path:
    manifest = load_json(V1856_MANIFEST)
    image_path = (((manifest.get("details") or {}).get("inputs") or {}).get("image") or {}).get("boot_image", "")
    return resolve_path(Path(str(image_path)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("dry-run", "live"), default="dry-run")
    parser.add_argument("--private-cnss-artifact", type=Path, default=default_artifact_path())
    parser.add_argument("--test-image", type=Path, default=default_test_image_path())
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def file_info(path: Path) -> dict[str, Any]:
    resolved = resolve_path(path)
    exists = resolved.exists()
    return {
        "path": rel(resolved),
        "exists": exists,
        "size": resolved.stat().st_size if exists else 0,
        "sha256": sha256_file(resolved) if exists else "",
    }


def collect_inputs(private_cnss_artifact: Path, test_image: Path) -> dict[str, Any]:
    v1220 = load_json(V1220_MANIFEST)
    v1856 = load_json(V1856_MANIFEST)
    image = (((v1856.get("details") or {}).get("inputs") or {}).get("image") or {})
    return {
        "v1220": {
            "path": rel(V1220_MANIFEST),
            "decision": v1220.get("decision", ""),
            "pass": bool(v1220.get("pass")),
            "host_only": bool(v1220.get("host_only")),
            "output": v1220.get("output", ""),
            "output_sha256": v1220.get("output_sha256", ""),
            "output_size": intish(v1220.get("output_size")),
            "cnss_daemon_executed": bool(v1220.get("cnss_daemon_executed")),
            "device_command_executed": bool(v1220.get("device_command_executed")),
            "wifi_hal_start_executed": bool(v1220.get("wifi_hal_start_executed")),
            "scan_connect_executed": bool(v1220.get("scan_connect_executed")),
            "credential_use_executed": bool(v1220.get("credential_use_executed")),
            "dhcp_route_executed": bool(v1220.get("dhcp_route_executed")),
            "external_ping_executed": bool(v1220.get("external_ping_executed")),
            "partition_write_executed": bool(v1220.get("partition_write_executed")),
            "flash_executed": bool(v1220.get("flash_executed")),
        },
        "v1856": {
            "path": rel(V1856_MANIFEST),
            "decision": v1856.get("decision", ""),
            "label": v1856.get("label", ""),
            "pass": bool(v1856.get("pass")),
            "image_boot_sha256_ok": bool(image.get("boot_sha256_ok")),
            "image_helper_marker": image.get("helper_marker", ""),
            "image_boot_path": image.get("boot_image", ""),
        },
        "private_cnss_artifact": file_info(private_cnss_artifact),
        "test_image": file_info(test_image),
    }


def plumbing_contract(requested_mode: str) -> dict[str, Any]:
    return {
        "cycle": CYCLE,
        "requested_mode": requested_mode,
        "supported_modes": ["dry-run"],
        "live_implemented": False,
        "device_command_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
        "stage_properties_executed": False,
        "start_actors_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "direct_subsys_esoc0_open_executed": False,
        "direct_pmic_gpio_gdsc_write_executed": False,
        "direct_esoc_ioctl_notify_executed": False,
        "forced_rc1_or_pci_rescan_executed": False,
        "plumbed_arguments": [
            "--private-cnss-artifact",
            "--test-image",
            "--mode",
        ],
    }


def classify(inputs: dict[str, Any], contract: dict[str, Any]) -> tuple[str, str, str, bool, int]:
    if contract["requested_mode"] != "dry-run":
        return (
            "artifact-plumbing-live-denied",
            "v1857-artifact-plumbing-live-denied",
            "V1857 only validates artifact plumbing; live execution requires a later reviewed unit",
            False,
            2,
        )
    v1220_ok = (
        inputs["v1220"]["pass"]
        and inputs["v1220"]["decision"] == "v1220-private-cnss-daemon-sdx50m-patch-ready"
        and inputs["v1220"]["host_only"]
        and not inputs["v1220"]["cnss_daemon_executed"]
        and not inputs["v1220"]["device_command_executed"]
        and not inputs["v1220"]["wifi_hal_start_executed"]
        and not inputs["v1220"]["scan_connect_executed"]
        and not inputs["v1220"]["credential_use_executed"]
        and not inputs["v1220"]["dhcp_route_executed"]
        and not inputs["v1220"]["external_ping_executed"]
        and not inputs["v1220"]["partition_write_executed"]
        and not inputs["v1220"]["flash_executed"]
    )
    v1856_ok = (
        inputs["v1856"]["pass"]
        and inputs["v1856"]["label"] == "bridge-v356-dry-run-ready"
        and inputs["v1856"]["image_boot_sha256_ok"]
        and inputs["v1856"]["image_helper_marker"] == "a90_android_execns_probe v356"
    )
    artifact_ok = (
        inputs["private_cnss_artifact"]["exists"]
        and inputs["private_cnss_artifact"]["sha256"] == inputs["v1220"]["output_sha256"]
        and inputs["private_cnss_artifact"]["size"] == inputs["v1220"]["output_size"]
    )
    image_ok = (
        inputs["test_image"]["exists"]
        and inputs["test_image"]["path"] == inputs["v1856"]["image_boot_path"]
    )
    no_actions = not any(
        bool(value)
        for key, value in contract.items()
        if key.endswith("_executed")
    )
    if not v1220_ok:
        return "v1220-input-review", "v1857-v1220-input-review", "V1220 private artifact input is not host-only clean", False, 1
    if not v1856_ok:
        return "v1856-input-review", "v1857-v1856-input-review", "V1856 v356 skeleton input is not ready", False, 1
    if not artifact_ok:
        return "artifact-review", "v1857-artifact-review", "Private CNSS artifact path, size, or SHA does not match V1220", False, 1
    if not image_ok:
        return "test-image-review", "v1857-test-image-review", "Test image path does not match V1856 readiness input", False, 1
    if not no_actions:
        return "action-safety-review", "v1857-action-safety-review", "Artifact plumbing contract claims an executed live or Wi-Fi action", False, 1
    return (
        "artifact-plumbing-dry-run-ready",
        "v1857-artifact-plumbing-dry-run-ready-host-pass",
        "Non-executing plumbing for the private SDX50M artifact and v356 test image is ready; live mode remains denied and no Wi-Fi credentials or network actions are used",
        True,
        0,
    )


def render_report(result: dict[str, Any]) -> str:
    inputs = result["details"]["inputs"]
    contract = result["details"]["contract"]
    return "\n".join([
        "# Native Init V1857 SDX50M Bridge Artifact Plumbing",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: host-only non-executing argument plumbing for the v356 SDX50M bridge skeleton",
        f"- Requested mode: `{contract['requested_mode']}`",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Inputs",
        "",
        f"- V1220: `{inputs['v1220']['decision']}` / host_only `{inputs['v1220']['host_only']}`",
        f"- private artifact: `{inputs['private_cnss_artifact']['path']}` exists `{inputs['private_cnss_artifact']['exists']}` size `{inputs['private_cnss_artifact']['size']}` sha `{inputs['private_cnss_artifact']['sha256']}`",
        f"- V1856: `{inputs['v1856']['decision']}` / `{inputs['v1856']['label']}` helper `{inputs['v1856']['image_helper_marker']}`",
        f"- test image: `{inputs['test_image']['path']}` exists `{inputs['test_image']['exists']}` sha `{inputs['test_image']['sha256']}`",
        "",
        "## Contract",
        "",
        f"- supported modes: `{contract['supported_modes']}`",
        f"- plumbed arguments: `{contract['plumbed_arguments']}`",
        f"- live/device/flash/reboot executed: `{contract['live_implemented']}` / `{contract['device_command_executed']}` / `{contract['flash_executed']}` / `{contract['reboot_executed']}`",
        f"- Wi-Fi/credential/network executed: `{contract['wifi_hal_start_executed']}` / `{contract['scan_connect_executed']}` / `{contract['credential_use_executed']}` / `{contract['dhcp_route_executed']}` / `{contract['external_ping_executed']}`",
        f"- lower mutation executed: subsys_esoc0 `{contract['direct_subsys_esoc0_open_executed']}`, PMIC/GPIO/GDSC `{contract['direct_pmic_gpio_gdsc_write_executed']}`, eSoC ioctl/notify `{contract['direct_esoc_ioctl_notify_executed']}`, forced RC1/rescan `{contract['forced_rc1_or_pci_rescan_executed']}`",
        "",
        "## Interpretation",
        "",
        "- V1857 adds argument-level plumbing only. It does not execute the private SDX50M artifact or flash/run the v356 image.",
        "- The artifact and image hashes are pinned so a later reviewed unit can fail closed on drift before any device action.",
        "- Wi-Fi connect and ping remain blocked until WLFW service 69 and `wlan0` are observed first.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This plumbing check did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        "- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "- Next candidate is a source-only preflight that validates host/device availability for a future one-run bridge gate without executing it.",
        "",
    ])


def write_outputs(out_dir: Path, report_path: Path, result: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    result["out_dir"] = rel(out_dir)
    result["report"] = rel(report_path)
    (out_dir / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(render_report(result), encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = resolve_path(args.out_dir)
    report_path = resolve_path(args.report)
    inputs = collect_inputs(args.private_cnss_artifact, args.test_image)
    contract = plumbing_contract(args.mode)
    label, decision, reason, passed, rc = classify(inputs, contract)
    result = {
        "cycle": CYCLE,
        "decision": decision,
        "label": label,
        "pass": passed,
        "reason": reason,
        "out_dir": rel(out_dir),
        "report": rel(report_path),
        "details": {
            "inputs": inputs,
            "contract": contract,
        },
    }
    write_outputs(out_dir, report_path, result)
    print(json.dumps({key: result[key] for key in ("decision", "label", "pass", "reason", "out_dir", "report")}, indent=2))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

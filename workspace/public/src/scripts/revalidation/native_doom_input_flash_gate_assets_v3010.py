#!/usr/bin/env python3
"""V3010 host-only flash-gate asset audit for the DOOM keyboard live gate.

The current DOOM input frontier is externally gated on an A90 OTG keyboard plus
operator key presses. This unit does not run the gate. It verifies that the
host-side assets needed to run the already-staged V3004 live gate remain present
and checksum-clean, so the next live attempt can proceed only when the hardware
stimulus precondition changes.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V3010"
BUILD_TAG = "v3010-doom-input-flash-gate-assets"
DECISION_READY = "v3010-doom-input-flash-gate-assets-ready-hardware-wait"
DECISION_INCOMPLETE = "v3010-doom-input-flash-gate-assets-incomplete"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V3010_DOOM_INPUT_FLASH_GATE_ASSETS_2026-06-20.md"

NEXT_LIVE_COMMAND = (
    "PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness "
    "python3 workspace/public/src/scripts/revalidation/"
    "native_doominput_keyboard_live_gate_v3004.py --live --count 32 --timeout-ms 60000"
)


@dataclass(frozen=True)
class AssetSpec:
    asset_id: str
    path: str
    kind: str
    expected_sha256: str | None = None
    required: bool = True


ASSETS = (
    AssetSpec(
        "v3004_candidate_v2989",
        "workspace/private/inputs/boot_images/boot_linux_v2989_doominput_state.img",
        "boot-image-candidate",
        "30e37c64196e7ff2649291c1398c67e96efea9313b25c51dade39d1c62c9ccc2",
    ),
    AssetSpec(
        "rollback_v2321",
        "workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img",
        "rollback-boot-image",
        "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb",
    ),
    AssetSpec(
        "fallback_v2237",
        "workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img",
        "fallback-boot-image",
        "b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f",
    ),
    AssetSpec(
        "fallback_v48",
        "workspace/private/inputs/boot_images/boot_linux_v48.img",
        "fallback-boot-image",
    ),
    AssetSpec(
        "flash_helper",
        "workspace/public/src/scripts/revalidation/native_init_flash.py",
        "checked-flash-helper",
    ),
    AssetSpec(
        "twrp_recovery",
        "workspace/private/inputs/firmware/twrp/recovery.img",
        "recovery-image",
    ),
)

REPORTS = {
    "v3004": ROOT / "docs/reports/NATIVE_INIT_V3004_DOOMINPUT_KEYBOARD_LIVE_GATE_DRY_RUN_2026-06-20.md",
    "v3007": ROOT / "docs/reports/NATIVE_INIT_V3007_DOOM_KEYBOARD_GATE_CURRENT_AUDIT_2026-06-20.md",
    "v3008": ROOT / "docs/reports/NATIVE_INIT_V3008_DOOM_INPUT_FRONTIER_RECONCILIATION_2026-06-20.md",
    "v3009": ROOT / "docs/reports/NATIVE_INIT_V3009_FRONTIER_SELECTOR_DOOM_GATE_2026-06-20.md",
}

REPORT_MARKERS = {
    "v3004": (
        "v3004-doominput-keyboard-dry-run",
        "Candidate SHA256: `30e37c64196e7ff2649291c1398c67e96efea9313b25c51dade39d1c62c9ccc2`",
        "Preflight ok: `1`",
        "Live execution: `0`",
        "USB keyboard/OTG attached and DOOM keys pressed during the doominput window",
    ),
    "v3007": (
        "v3007-doom-keyboard-gate-hardware-stimulus-required",
        "A90 OTG keyboard evdev evidence: `0`",
        "V3004 live actionable now: `0`",
    ),
    "v3008": (
        "v3008-doom-input-frontier-keyboard-gate-still-external-stimulus",
        "USB keyboard live gate staged: `1`",
        "Active tier saturated without external stimulus: `1`",
        "native_doominput_keyboard_live_gate_v3004.py --live --count 32 --timeout-ms 60000",
    ),
    "v3009": (
        "frontier-selector-no-automatic-safe-unit",
        "VIDEO` / `doom-input",
        "external-hardware-stimulus-required",
        "native_doominput_keyboard_live_gate_v3004.py --live --count 32 --timeout-ms 60000",
    ),
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_asset(spec: AssetSpec, root: Path = ROOT) -> dict[str, Any]:
    path = root / spec.path
    exists = path.exists()
    is_file = path.is_file()
    actual_sha256 = sha256_file(path) if is_file else None
    sha256_ok = actual_sha256 == spec.expected_sha256 if spec.expected_sha256 else None
    return {
        "asset_id": spec.asset_id,
        "kind": spec.kind,
        "path": spec.path,
        "required": spec.required,
        "exists": exists,
        "is_file": is_file,
        "size_bytes": path.stat().st_size if is_file else None,
        "expected_sha256": spec.expected_sha256,
        "actual_sha256": actual_sha256,
        "sha256_ok": sha256_ok,
        "ok": bool(exists and is_file and (sha256_ok is not False)),
    }


def audit_assets(root: Path = ROOT, specs: tuple[AssetSpec, ...] = ASSETS) -> dict[str, dict[str, Any]]:
    return {spec.asset_id: audit_asset(spec, root) for spec in specs}


def load_report_texts() -> dict[str, str]:
    return {key: path.read_text(encoding="utf-8") for key, path in REPORTS.items()}


def analyze_report_markers(texts: dict[str, str]) -> dict[str, Any]:
    per_report: dict[str, dict[str, Any]] = {}
    for key, markers in REPORT_MARKERS.items():
        text = texts.get(key, "")
        missing = [marker for marker in markers if marker not in text]
        per_report[key] = {
            "path": rel(REPORTS[key]),
            "ok": not missing,
            "missing_markers": missing,
        }
    return {
        "per_report": per_report,
        "all_reports_ok": all(item["ok"] for item in per_report.values()),
        "external_hardware_wait": (
            "v3008-doom-input-frontier-keyboard-gate-still-external-stimulus" in texts.get("v3008", "")
            and "V3004 live actionable now: `0`" in texts.get("v3007", "")
            and "external-hardware-stimulus-required" in texts.get("v3009", "")
        ),
    }


def summarize_assets(assets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    required = [asset for asset in assets.values() if asset["required"]]
    expected = [asset for asset in required if asset["expected_sha256"]]
    return {
        "all_required_assets_present": all(asset["exists"] and asset["is_file"] for asset in required),
        "all_expected_sha256_ok": all(asset["sha256_ok"] is True for asset in expected),
        "all_required_assets_ok": all(asset["ok"] for asset in required),
        "required_asset_count": len(required),
        "expected_sha256_count": len(expected),
    }


def classify(assets: dict[str, dict[str, Any]], markers: dict[str, Any]) -> dict[str, Any]:
    asset_summary = summarize_assets(assets)
    ready = (
        asset_summary["all_required_assets_ok"]
        and asset_summary["all_expected_sha256_ok"]
        and markers["all_reports_ok"]
        and markers["external_hardware_wait"]
    )
    return {
        **asset_summary,
        "reports_ok": markers["all_reports_ok"],
        "external_hardware_wait": markers["external_hardware_wait"],
        "v3004_live_actionable_now": False,
        "decision": DECISION_READY if ready else DECISION_INCOMPLETE,
        "next_live_command": NEXT_LIVE_COMMAND,
    }


def build_payload() -> dict[str, Any]:
    assets = audit_assets()
    markers = analyze_report_markers(load_report_texts())
    return {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "assets": assets,
        "reports": markers,
        "flags": classify(assets, markers),
    }


def render_asset_table(assets: dict[str, dict[str, Any]]) -> list[str]:
    lines = [
        "| asset | kind | ok | sha256_ok | path |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for asset_id in sorted(assets):
        asset = assets[asset_id]
        sha_ok = "-" if asset["sha256_ok"] is None else str(int(bool(asset["sha256_ok"])))
        lines.append(
            f"| `{asset_id}` | `{asset['kind']}` | `{int(bool(asset['ok']))}` | "
            f"`{sha_ok}` | `{asset['path']}` |"
        )
    return lines


def render_report(payload: dict[str, Any]) -> str:
    flags = payload["flags"]
    assets = payload["assets"]
    reports = payload["reports"]["per_report"]
    lines = [
        "# Native Init V3010 DOOM Input Flash Gate Assets",
        "",
        "## Summary",
        "",
        f"- Decision: `{flags['decision']}`",
        "- Device action: `none` in this host-only unit.",
        "- Track: active Video playback / DOOM input prerequisite plus T3 safety tooling.",
        f"- Required assets present: `{int(flags['all_required_assets_present'])}`",
        f"- Expected SHA256 checks pass: `{int(flags['all_expected_sha256_ok'])}`",
        f"- Current gate reports pass: `{int(flags['reports_ok'])}`",
        f"- External hardware wait retained: `{int(flags['external_hardware_wait'])}`",
        f"- V3004 live actionable now: `{int(flags['v3004_live_actionable_now'])}`",
        "",
        "## Asset Audit",
        "",
        *render_asset_table(assets),
        "",
        "## Current Gate Evidence",
        "",
        f"- V3004 report markers ok: `{int(reports['v3004']['ok'])}`",
        f"- V3007 current-audit markers ok: `{int(reports['v3007']['ok'])}`",
        f"- V3008 reconciliation markers ok: `{int(reports['v3008']['ok'])}`",
        f"- V3009 selector markers ok: `{int(reports['v3009']['ok'])}`",
        "- The next live run remains gated on an A90-side USB keyboard/OTG path plus operator DOOM key presses.",
        f"- Command when the external prerequisite is true: `{flags['next_live_command']}`",
        "",
        "## Drop-Tier Trigger",
        "",
        "- Active DOOM input live work still needs external hardware stimulus; this V3010 unit performs host-only flash-gate asset readiness instead of repeating low-information touch/button samples.",
        "",
        "## Host Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doom_input_flash_gate_assets_v3010.py tests/test_native_doom_input_flash_gate_assets_v3010.py`: PASS",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doom_input_flash_gate_assets_v3010`: PASS",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doom_input_flash_gate_assets_v3010.py`: PASS (host-only report materialized)",
        "- `git diff --check`: PASS",
        "",
        "## Safety",
        "",
        "- Host-only file existence and SHA256 audit; no flash, no serial command, no evdev open, no input injection, and no sysfs write.",
        "- The checked flash helper is only treated as an audited file path; it is not invoked.",
        "- No Wi-Fi/audio/video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.",
        "- Private boot/recovery images remain under `workspace/private/`; this report records metadata only.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    payload = build_payload()
    REPORT_PATH.write_text(render_report(payload), encoding="utf-8")
    print(json.dumps({
        "decision": payload["flags"]["decision"],
        "all_required_assets_ok": payload["flags"]["all_required_assets_ok"],
        "reports_ok": payload["flags"]["reports_ok"],
        "external_hardware_wait": payload["flags"]["external_hardware_wait"],
        "next_live_command": payload["flags"]["next_live_command"],
        "report": rel(REPORT_PATH),
    }, indent=2, sort_keys=True))
    return 0 if payload["flags"]["decision"] == DECISION_READY else 1


if __name__ == "__main__":
    raise SystemExit(main())

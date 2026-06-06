#!/usr/bin/env python3
"""V1797 host-only PM-service dual-devnode access-gate classifier."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1797-pm-service-dual-devnode-access-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1797_PM_SERVICE_DUAL_DEVNODE_ACCESS_CLASSIFIER_2026-06-03.md"
)
INPUTS = {
    "v1789_manifest": REPO_ROOT / "tmp" / "wifi" / "v1789-pm-add-peripheral-init-fail-static" / "manifest.json",
    "v1796_manifest": REPO_ROOT / "tmp" / "wifi" / "v1796-pm-service-count-sample-handoff" / "manifest.json",
}


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False, "path": display_path(path)}
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data["present"] = True
        return data
    return {"present": True, "value": data}


def intish(value: Any) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def csv_set(value: Any) -> set[str]:
    return {item.strip() for item in str(value or "").split(",") if item.strip()}


def table_row(table: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for row in table:
        if row.get("name") == name:
            return row
    return {}


def classify(facts: dict[str, Any]) -> tuple[str, str, str, bool]:
    if not facts["inputs_present"]:
        return (
            "v1797-pm-dual-devnode-access-input-missing",
            "input-missing",
            "required V1789 static or V1796 live evidence is missing",
            False,
        )
    if not facts["v1796_pass"] or not facts["v1796_rollback_ok"]:
        return (
            "v1797-pm-dual-devnode-access-live-baseline-blocked",
            "live-baseline-blocked",
            "V1796 did not produce a rollback-verified live discriminator",
            False,
        )
    if not facts["v1789_access_model_ok"]:
        return (
            "v1797-pm-dual-devnode-access-static-model-blocked",
            "static-model-blocked",
            "V1789 static model does not confirm add-peripheral access(F_OK) on record devnode",
            False,
        )
    if (
        facts["v1796_label"] == "modem-devnode-access-fail"
        and facts["v1796_first_count"] == 2
        and facts["v1796_second_count"] == 0
        and facts["v1796_list_commit_hits"] == 0
        and facts["v1796_init_fail_hits"] == 2
        and facts["v1796_first_names"] == {"SDX50M", "modem"}
        and facts["v1796_init_fail_names"] == {"SDX50M", "modem"}
        and facts["static_sdx50m_enabled"]
        and facts["static_modem_enabled"]
    ):
        return (
            "v1797-pm-dual-devnode-access-gate-host-pass",
            "pm-dual-devnode-access-gate",
            "V1796 live evidence confirms both primary candidates reach pm-service add-peripheral and both fail at the V1789 access(F_OK) devnode gate before list commit",
            True,
        )
    return (
        "v1797-pm-dual-devnode-access-unclassified-host-pass",
        "pm-dual-devnode-access-unclassified",
        "host inputs are present, but the V1796/V1789 join did not match the fixed dual-devnode access-gate model",
        True,
    )


def render_report(manifest: dict[str, Any]) -> str:
    facts = manifest["facts"]
    return "\n".join(
        [
            "# Native Init V1797 PM-service Dual Devnode Access Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1797`",
            "- Type: host-only static/live-evidence join classifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Label: `{manifest['label']}`",
            f"- Result: {'PASS' if manifest['pass'] else 'BLOCKED'}",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            "",
            "## Inputs",
            "",
            *[f"- {name}: `{path}`" for name, path in manifest["inputs"].items()],
            "",
            "## V1796 Live Evidence",
            "",
            f"- decision: `{facts['v1796_decision']}`",
            f"- rollback ok: `{facts['v1796_rollback_ok']}`",
            f"- count/sample label: `{facts['v1796_label']}`",
            f"- first/second count: `{facts['v1796_first_count']}` / `{facts['v1796_second_count']}`",
            f"- first-loop names: `{','.join(sorted(facts['v1796_first_names']))}`",
            f"- init-fail names: `{','.join(sorted(facts['v1796_init_fail_names']))}`",
            f"- first add call/fail hits: `{facts['v1796_first_add_hits']}` / `{facts['v1796_first_fail_hits']}`",
            f"- add-peripheral entry/init-fail/list-commit hits: `{facts['v1796_entry_hits']}` / `{facts['v1796_init_fail_hits']}` / `{facts['v1796_list_commit_hits']}`",
            f"- PM register no-peripheral requested: `{facts['v1796_no_peripheral_name']}`",
            "",
            "## V1789 Static Access Model",
            "",
            f"- decision: `{facts['v1789_decision']}`",
            f"- access model ok: `{facts['v1789_access_model_ok']}`",
            f"- record devnode offset: `{facts['record_devnode_offset']}`",
            f"- devnode format: `{facts['mdmdetect_devnode_format']}`",
            f"- access-fail string: `{facts['pm_devnode_access_fail_string']}`",
            f"- init-fail string: `{facts['pm_init_fail_string']}`",
            f"- static `SDX50M` enabled/devnode-kind: `{facts['static_sdx50m_enabled']}` / `{facts['static_sdx50m_kind']}`",
            f"- static `modem` enabled/devnode-kind: `{facts['static_modem_enabled']}` / `{facts['static_modem_kind']}`",
            "",
            "## Interpretation",
            "",
            "- `libmdmdetect` populated two primary candidates and PM-service attempted both.",
            "- Both candidates failed before supported-list insertion at the same static add-peripheral access gate.",
            "- Repairing only one candidate path is not justified by V1796; the next gate must classify the minimal safe devnode/access parity gap for both candidates.",
            "",
            "## Safety Scope",
            "",
            "- Host-only. No live device command, flash, reboot, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, PM repair, devnode open, eSoC/RC1 action, restart-PD request, firmware write, partition write, PMIC/GPIO/GDSC write, PCI rescan, platform bind/unbind, BPF attach, or tracefs write.",
            "",
            "## Next",
            "",
            "- V1798 should remain source/build-only or read-only host planning: derive a no-open access-parity observer/plan for both `SDX50M` and `modem` before any devnode materialization or PM repair.",
            "",
        ]
    )


def build_manifest() -> dict[str, Any]:
    v1789 = load_json(INPUTS["v1789_manifest"])
    v1796 = load_json(INPUTS["v1796_manifest"])
    v1789_facts = v1789.get("facts") if isinstance(v1789.get("facts"), dict) else {}
    v1796_gate = v1796.get("gate") if isinstance(v1796.get("gate"), dict) else {}
    static_table = v1789_facts.get("pm_static_peripheral_table")
    static_table = static_table if isinstance(static_table, list) else []
    sdx50m_row = table_row(static_table, "SDX50M")
    modem_row = table_row(static_table, "modem")
    first_names = csv_set(v1796_gate.get("pm_service_first_add_names"))
    init_fail_names = csv_set(v1796_gate.get("pm_service_init_fail_names"))
    facts: dict[str, Any] = {
        "inputs_present": bool(v1789.get("present")) and bool(v1796.get("present")),
        "v1789_decision": v1789.get("decision", ""),
        "v1789_pass": bool(v1789.get("pass")),
        "v1789_access_model_ok": (
            bool(v1789.get("pass"))
            and bool(v1789_facts.get("pm_add_peripheral_calls_devnode_access"))
            and bool(v1789_facts.get("pm_add_peripheral_known_name_before_init"))
            and str(v1789_facts.get("mdmdetect_record_devnode_offset")) == "0x44"
        ),
        "record_devnode_offset": v1789_facts.get("mdmdetect_record_devnode_offset", ""),
        "mdmdetect_devnode_format": v1789_facts.get("mdmdetect_devnode_format", ""),
        "pm_devnode_access_fail_string": v1789_facts.get("pm_devnode_access_fail_string", ""),
        "pm_init_fail_string": v1789_facts.get("pm_init_fail_string", ""),
        "static_sdx50m_enabled": intish(sdx50m_row.get("enabled")) == 1,
        "static_sdx50m_kind": sdx50m_row.get("kind", ""),
        "static_modem_enabled": intish(modem_row.get("enabled")) == 1,
        "static_modem_kind": modem_row.get("kind", ""),
        "v1796_decision": v1796.get("decision", ""),
        "v1796_pass": bool(v1796.get("pass")),
        "v1796_rollback_ok": bool((v1796.get("rollback") or {}).get("ok")),
        "v1796_label": v1796_gate.get("pm_service_count_sample_label", ""),
        "v1796_first_count": intish(v1796_gate.get("pm_service_first_count")),
        "v1796_second_count": intish(v1796_gate.get("pm_service_second_count")),
        "v1796_first_names": sorted(first_names),
        "v1796_init_fail_names": sorted(init_fail_names),
        "v1796_first_add_hits": intish(v1796_gate.get("pm_service_init_first_add_peripheral_call_hits")),
        "v1796_first_fail_hits": intish(v1796_gate.get("pm_service_init_first_add_peripheral_fail_log_hits")),
        "v1796_entry_hits": intish(v1796_gate.get("pm_service_add_peripheral_entry_hits")),
        "v1796_init_fail_hits": intish(v1796_gate.get("pm_service_add_peripheral_init_fail_hits")),
        "v1796_list_commit_hits": intish(v1796_gate.get("pm_service_add_peripheral_list_commit_hits")),
        "v1796_no_peripheral_name": v1796_gate.get("pm_server_register_no_peripheral_name", ""),
    }
    classify_facts = {**facts, "v1796_first_names": first_names, "v1796_init_fail_names": init_fail_names}
    decision, label, reason, pass_ok = classify(classify_facts)
    return {
        "cycle": "V1797",
        "decision": decision,
        "label": label,
        "pass": pass_ok,
        "reason": reason,
        "inputs": {name: display_path(path) for name, path in INPUTS.items()},
        "facts": facts,
        "out_dir": display_path(OUT_DIR),
        "report": display_path(REPORT_PATH),
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    report = render_report(manifest)
    (OUT_DIR / "summary.md").write_text(report, encoding="utf-8")
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"]}, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

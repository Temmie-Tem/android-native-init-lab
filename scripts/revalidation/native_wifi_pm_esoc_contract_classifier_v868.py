#!/usr/bin/env python3
"""V868 host-only PM/eSoC contract classifier.

This folds V867's `pm_proxy_helper` D-state result into the local Samsung OSRC
eSoC ioctl contract. It does not contact the device, start daemons, load
modules, write boot images, or perform Wi-Fi scan/connect work.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text, workspace_private_input_path


DEFAULT_OUT_DIR = Path("tmp/wifi/v868-pm-esoc-contract-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v868-pm-esoc-contract-classifier.txt")
DEFAULT_SOURCE_ROOT = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel')
DEFAULT_ESOC_DOC = Path("docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md")
DEFAULT_V867_MANIFEST = Path("tmp/wifi/v867-pm-init-contract-live-r3/manifest.json")
DEFAULT_V867_REPORT = Path("docs/reports/NATIVE_INIT_V867_PM_INIT_CONTRACT_START_ONLY_2026-05-25.md")

ESOC_UAPI = Path("include/uapi/linux/esoc_ctrl.h")
SUBSYSTEM_RESTART = Path("drivers/soc/qcom/subsystem_restart.c")

EXPECTED_V867_DECISION = "v867-residual-actor-cleanup-required"
FORBIDDEN_SECRET_ENV_NAMES = ("A90_WIFI_SSID", "A90_WIFI_PSK")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--esoc-doc", type=Path, default=DEFAULT_ESOC_DOC)
    parser.add_argument("--v867-manifest", type=Path, default=DEFAULT_V867_MANIFEST)
    parser.add_argument("--v867-report", type=Path, default=DEFAULT_V867_REPORT)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "error": str(exc)}
    if not isinstance(payload, dict):
        return {"exists": True, "path": str(resolved), "error": "not-json-object"}
    payload.setdefault("exists", True)
    payload.setdefault("path", str(resolved))
    return payload


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "pass"}


def nested(data: Any, *keys: Any) -> Any:
    current: Any = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list) and isinstance(key, int) and 0 <= key < len(current):
            current = current[key]
        else:
            return None
    return current


def line_of(text: str, pattern: str, flags: int = 0) -> int | None:
    regex = re.compile(pattern, flags)
    for line_number, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return line_number
    return None


def extract_ioctl_numbers(esoc_text: str) -> dict[str, Any]:
    macros: dict[str, Any] = {}
    define_re = re.compile(r"#define\s+(ESOC_[A-Z0-9_]+)\s+_IO(?:R|W|WR)?\(\s*ESOC_CODE\s*,\s*(\d+)")
    enum_explicit_re = re.compile(r"\b(ESOC_[A-Z0-9_]+)\s*=\s*(0x[0-9a-fA-F]+|\d+)\s*,?")
    enum_implicit_re = re.compile(r"\b(ESOC_[A-Z0-9_]+)\s*,")
    enum_active = False
    enum_next_value: int | None = None
    for line in esoc_text.splitlines():
        define = define_re.search(line)
        if define:
            macros[define.group(1)] = int(define.group(2))
            continue
        stripped = line.strip()
        if stripped.startswith("enum esoc_"):
            enum_active = True
            enum_next_value = 0
            continue
        if enum_active and stripped.startswith("};"):
            enum_active = False
            enum_next_value = None
            continue
        if not enum_active:
            continue
        enum_explicit = enum_explicit_re.search(line)
        if enum_explicit:
            value = int(enum_explicit.group(2), 0)
            macros[enum_explicit.group(1)] = value
            enum_next_value = value + 1
            continue
        enum_implicit = enum_implicit_re.search(line)
        if enum_implicit and enum_next_value is not None:
            macros[enum_implicit.group(1)] = enum_next_value
            enum_next_value += 1
    macros["ESOC_CODE_present"] = "ESOC_CODE" in esoc_text and "0xCC" in esoc_text
    return macros


def source_summary(source_root: Path) -> dict[str, Any]:
    root = repo_path(source_root)
    esoc_path = root / ESOC_UAPI
    ssr_path = root / SUBSYSTEM_RESTART
    esoc_text = read_text(source_root / ESOC_UAPI)
    ssr_text = read_text(source_root / SUBSYSTEM_RESTART)
    macros = extract_ioctl_numbers(esoc_text)
    expected = {
        "ESOC_CMD_EXE": 1,
        "ESOC_WAIT_FOR_REQ": 2,
        "ESOC_NOTIFY": 3,
        "ESOC_GET_STATUS": 4,
        "ESOC_GET_ERR_FATAL": 5,
        "ESOC_WAIT_FOR_CRASH": 6,
        "ESOC_REG_REQ_ENG": 7,
        "ESOC_REG_CMD_ENG": 8,
        "ESOC_PWR_ON": 1,
        "ESOC_IMG_XFER_DONE": 1,
        "ESOC_BOOT_DONE": 2,
    }
    expected_ok = {name: macros.get(name) == value for name, value in expected.items()}
    return {
        "source_root": str(root),
        "esoc_uapi": {
            "path": str(esoc_path),
            "exists": esoc_path.exists(),
            "line_ESOC_REG_REQ_ENG": line_of(esoc_text, r"ESOC_REG_REQ_ENG"),
            "line_ESOC_REG_CMD_ENG": line_of(esoc_text, r"ESOC_REG_CMD_ENG"),
            "line_ESOC_PWR_ON": line_of(esoc_text, r"ESOC_PWR_ON\s*=\s*1"),
            "macros": macros,
            "expected_ok": expected_ok,
            "all_expected_ok": bool(expected_ok) and all(expected_ok.values()),
        },
        "subsystem_restart": {
            "path": str(ssr_path),
            "exists": ssr_path.exists(),
            "line_pm_proxy_helper": line_of(ssr_text, r"pm_proxy_helper"),
            "line_poff_depends_on": line_of(ssr_text, r"poff_depends_on"),
            "has_pm_proxy_helper_exception": "pm_proxy_helper" in ssr_text and "poff_depends_on" in ssr_text,
        },
    }


def v867_summary(manifest_path: Path, report_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    report = read_text(report_path)
    helper = manifest.get("helper") if isinstance(manifest.get("helper"), dict) else {}
    children = helper.get("children") if isinstance(helper.get("children"), dict) else {}
    per_proxy_helper = children.get("per_proxy_helper") if isinstance(children.get("per_proxy_helper"), dict) else {}
    return {
        "manifest_path": str(repo_path(manifest_path)),
        "report_path": str(repo_path(report_path)),
        "manifest_exists": bool_value(manifest.get("exists")),
        "decision": manifest.get("decision"),
        "pass": bool_value(manifest.get("pass")),
        "expected_decision": manifest.get("decision") == EXPECTED_V867_DECISION,
        "pm_proxy_helper": {
            "pid": per_proxy_helper.get("pid"),
            "exited": per_proxy_helper.get("exited"),
            "postflight_safe": per_proxy_helper.get("postflight_safe"),
            "actual_attr_current": per_proxy_helper.get("actual_attr_current"),
            "fd_targets": per_proxy_helper.get("fd_targets", []),
            "holds_subsys": bool_value(helper.get("per_proxy_helper_holds_subsys")),
        },
        "report_has_dstate": "D-state" in report or " Ds " in report,
        "report_has_no_mdm_helper_gate": "No `mdm_helper` or `ks` start." in report,
        "report_has_next_v868": "V868" in report,
    }


def doc_summary(path: Path) -> dict[str, Any]:
    text = read_text(path)
    stale_public_ioctl_lines = [
        line.strip()
        for line in text.splitlines()
        if "ESOC_IOCTL_TYPE" in line or "_IO(ESOC_IOCTL_TYPE" in line
    ]
    return {
        "path": str(repo_path(path)),
        "exists": bool(text),
        "has_android_chain": "완전한 Android mdm3 bring-up 체인" in text,
        "has_v868_section": "V868 필요 조건" in text,
        "has_pm_proxy_equals_mdm_helper": "pm_proxy_helper = mdm_helper" in text,
        "has_local_osrc_ioctl_note": "A90 로컬 Samsung OSRC 기준 값" in text,
        "stale_public_ioctl_lines": stale_public_ioctl_lines,
    }


def decide(source: dict[str, Any], v867: dict[str, Any], doc: dict[str, Any]) -> tuple[str, bool, str, str]:
    if not source["esoc_uapi"]["exists"] or not source["subsystem_restart"]["exists"]:
        return (
            "v868-source-missing",
            False,
            "local Samsung OSRC source files are missing",
            "restore OSRC source before planning a live eSoC gate",
        )
    if not source["esoc_uapi"]["all_expected_ok"]:
        return (
            "v868-esoc-uapi-mismatch",
            False,
            "local eSoC ioctl numbers did not match the expected A90 contract",
            "do not implement helper ioctl calls until uapi mismatch is resolved",
        )
    if not source["subsystem_restart"]["has_pm_proxy_helper_exception"]:
        return (
            "v868-pm-proxy-helper-exception-missing",
            False,
            "local subsystem_restart.c does not expose the pm_proxy_helper eSoC exception",
            "classify kernel source mismatch before using Android PM model",
        )
    if not v867["manifest_exists"] or not v867["expected_decision"]:
        return (
            "v868-v867-evidence-missing-or-unexpected",
            False,
            "V867 residual D-state evidence is missing or not the expected decision",
            "rerun or relink V867 evidence before selecting V869",
        )
    if not v867["report_has_dstate"]:
        return (
            "v868-dstate-not-proven",
            False,
            "V867 report does not prove pm_proxy_helper D-state",
            "collect stronger wait-state evidence before changing helper model",
        )
    if not doc["exists"] or not doc["has_v868_section"]:
        return (
            "v868-research-doc-missing",
            False,
            "ESOC/PeripheralManager research input is missing",
            "restore or rewrite the V868 research input",
        )
    if doc["stale_public_ioctl_lines"]:
        return (
            "v868-research-doc-stale-ioctl-values",
            False,
            "research doc still contains non-A90 public ioctl macro values",
            "correct the research doc to local Samsung OSRC values",
        )
    return (
        "v868-esoc-req-eng-precondition-selected",
        True,
        "V867 pm_proxy_helper D-state is best explained by missing /dev/esoc-0 CMD/REQ engine registration before /dev/subsys_esoc0 hold",
        "V869 should be source/build-only helper design for A90 eSoC control preflight; live PWR_ON remains blocked until a separate gate",
    )


def forbidden_secret_env_hits(payload: str) -> list[str]:
    hits: list[str] = []
    for env_name in FORBIDDEN_SECRET_ENV_NAMES:
        value = os.environ.get(env_name)
        if value and value in payload:
            hits.append(env_name)
    return hits


def write_summary(out_dir: Path, manifest: dict[str, Any]) -> None:
    rows = [
        ["decision", manifest["decision"]],
        ["pass", str(manifest["pass"])],
        ["reason", manifest["reason"]],
        ["next", manifest["next_step"]],
        ["source", manifest["source"]["esoc_uapi"]["path"]],
        ["V867 evidence", manifest["v867"]["manifest_path"]],
    ]
    lines = [
        "# V868 PM/eSoC Contract Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        "",
        "## Decision",
        "",
        markdown_table(["key", "value"], rows),
        "",
        "## Local A90 eSoC UAPI",
        "",
        markdown_table(
            ["macro", "value", "expected_ok"],
            [
                [name, str(manifest["source"]["esoc_uapi"]["macros"].get(name)), str(ok)]
                for name, ok in manifest["source"]["esoc_uapi"]["expected_ok"].items()
            ],
        ),
        "",
        "## Interpretation",
        "",
        "- `pm_proxy_helper` should not be retried alone; V867 already proved that path can leave an unkillable D-state actor.",
        "- The next implementation target is not Wi-Fi HAL or scan/connect. It is the eSoC control contract around `/dev/esoc-0`.",
        "- `ESOC_REG_REQ_ENG`, `ESOC_REG_CMD_ENG`, and `ESOC_PWR_ON` must use the local A90 OSRC UAPI values, not public example offsets.",
        "",
        "## Guardrails",
        "",
        "- Host-only classifier: no bridge/device contact.",
        "- No daemon start, no `mdm_helper`, no `ks`, no Wi-Fi HAL, no scan/connect, no credentials, no DHCP/routes, no external ping.",
        "- No GPIO/sysfs/debugfs/subsystem state write, module load/unload, boot image write, or partition write.",
    ]
    write_private_text(out_dir / "summary.md", "\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    out_dir = repo_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    source = source_summary(args.source_root)
    v867 = v867_summary(args.v867_manifest, args.v867_report)
    doc = doc_summary(args.esoc_doc)
    decision, passed, reason, next_step = decide(source, v867, doc)
    manifest = {
        "schema": "a90.native_wifi.pm_esoc_contract_classifier.v868",
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "device_contacted": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "mdm_helper_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
        "forbidden_secret_env_hits": forbidden_secret_env_hits(json.dumps([source, v867, doc], ensure_ascii=False)),
        "source": source,
        "v867": v867,
        "research_doc": doc,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
    }
    write_private_text(out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    write_summary(out_dir, manifest)
    evidence = EvidenceStore(out_dir)
    evidence.write_json("manifest.copy.json", manifest)
    write_private_text(repo_path(LATEST_POINTER), str(out_dir) + "\n")
    print(f"decision: {decision}")
    print(f"pass: {passed}")
    print(f"reason: {reason}")
    print(f"next: {next_step}")
    print(f"evidence: {out_dir}")
    return 0 if passed or args.command == "plan" else 1


if __name__ == "__main__":
    raise SystemExit(main())

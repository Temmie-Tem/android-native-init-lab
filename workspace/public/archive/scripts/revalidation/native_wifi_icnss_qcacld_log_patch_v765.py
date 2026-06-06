#!/usr/bin/env python3
"""V765 host-only ICNSS/QCACLD log patch generator.

V764 proved `mdm_helper` can start under the service180 gate but still does not
advance mdm3/WLAN-PD/WLFW. V765 returns to the source-backed instrumentation
route selected by V757/V758 and unblocked by V760/V763: generate a minimal
reviewable printk-only patch from staged Samsung OSRC source. It does not modify
kernel_build, build a kernel, write a boot image, or talk to the device.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import json
import re
import tarfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text, workspace_private_input_path


DEFAULT_OUT_DIR = Path("tmp/wifi/v765-icnss-qcacld-log-patch")
DEFAULT_SOURCE_ARCHIVE = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel.tar.gz')
DEFAULT_V760_MANIFEST = Path("tmp/wifi/v760-source-staging/manifest.json")
DEFAULT_V763_REPORT = Path("docs/reports/NATIVE_INIT_V763_ICNSS_ARCH_REBASE_2026-05-24.md")
DEFAULT_V764_MANIFEST = Path("tmp/wifi/v764-mdm-helper-service180-retry/manifest.json")
PATCH_PREFIX = "A90V765"


@dataclass(frozen=True)
class Edit:
    file_suffix: str
    anchor: str
    insert_after: bool
    text: str
    purpose: str


@dataclass(frozen=True)
class AppliedEdit:
    file: str
    anchor: str
    line: int
    status: str
    purpose: str
    text: str


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


ICNSS_QMI = "drivers/soc/qcom/icnss_qmi.c"
ICNSS_CORE = "drivers/soc/qcom/icnss.c"
PLD_SNOC = "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/pld/src/pld_snoc.c"
HDD_MAIN = "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_main.c"
HDD_OPS = "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c"


EDITS = (
    Edit(ICNSS_QMI, r"^\s*ret = qmi_handle_init\(&priv->qmi,", False,
         '\ticnss_pr_info("A90V765 icnss_register_fw_service enter state:0x%lx\\n", priv ? priv->state : 0);',
         "prove WLFW service lookup registration function is entered"),
    Edit(ICNSS_QMI, r"^\s*icnss_pr_dbg\(\"WLFW server arrive: node %u port %u\\n\",", False,
         '\ticnss_pr_info("A90V765 wlfw_new_server enter node:%u port:%u state:0x%lx\\n", service ? service->node : 0, service ? service->port : 0, priv->state);',
         "prove WLFW service 69 arrival callback fires"),
    Edit(ICNSS_CORE, r"^\s*set_bit\(ICNSS_WLFW_EXISTS, &penv->state\);", False,
         '\ticnss_pr_info("A90V765 icnss_server_arrive enter state:0x%lx\\n", penv ? penv->state : 0);',
         "prove ICNSS processes WLFW server arrival"),
    Edit(ICNSS_CORE, r"^\s*set_bit\(ICNSS_FW_READY, &penv->state\);", False,
         '\ticnss_pr_info("A90V765 icnss_fw_ready_ind enter state:0x%lx\\n", penv ? penv->state : 0);',
         "prove FW-ready indication reaches ICNSS"),
    Edit(ICNSS_CORE, r"^\s*if \(penv->ops\)", False,
         '\ticnss_pr_info("A90V765 icnss_register_event enter state:0x%lx fw_ready:%d\\n", penv ? penv->state : 0, penv ? test_bit(ICNSS_FW_READY, &penv->state) : -1);',
         "prove QCACLD registration event and FW-ready gate state"),
    Edit(ICNSS_CORE, r"^\s*if \(!priv->ops \|\| !priv->ops->probe\)", False,
         '\ticnss_pr_info("A90V765 icnss_call_driver_probe enter state:0x%lx ops:%p probe:%p\\n", priv ? priv->state : 0, priv ? priv->ops : NULL, (priv && priv->ops) ? priv->ops->probe : NULL);',
         "prove ICNSS attempts QCACLD probe handoff"),
    Edit(ICNSS_CORE, r"^\s*icnss_pr_dbg\(\"Registering driver, state: 0x%lx\\n\", penv->state\);", False,
         '\ticnss_pr_info("A90V765 __icnss_register_driver enter penv:%p pdev:%p ops:%p probe:%p\\n", penv, penv ? penv->pdev : NULL, ops, ops ? ops->probe : NULL);',
         "prove QCACLD registers with ICNSS"),
    Edit(PLD_SNOC, r"^\s*pld_context = pld_get_global_context\(\);", False,
         '\tpr_err("A90V765 pld_snoc_probe enter dev:%p\\n", dev);',
         "prove PLD-SNOC probe callback fires"),
    Edit(PLD_SNOC, r"^\s*int\s+pld_snoc_register_driver\s*\(", True,
         '\tpr_err("A90V765 pld_snoc_register_driver enter\\n");',
         "prove PLD registers driver with ICNSS"),
    Edit(HDD_MAIN, r"^\s*static\s+ssize_t\s+wlan_boot_cb\s*\(", True,
         '\thdd_err("A90V765 wlan_boot_cb enter loaded_state:%d count:%zu", wlan_loader ? wlan_loader->loaded_state : -1, count);',
         "prove native boot_wlan callback enters"),
    Edit(HDD_MAIN, r"^\s*pr_err\(\"%s: Loading driver v%s\\n\",", False,
         '\thdd_err("A90V765 hdd_driver_load enter con_mode:%d", con_mode);',
         "prove HDD driver load starts"),
    Edit(HDD_MAIN, r"^\s*status = hdd_qdf_init\(\);", False,
         '\thdd_err("A90V765 hdd_driver_load before hdd_qdf_init");',
         "locate first HDD init stage"),
    Edit(HDD_MAIN, r"^\s*errno = hdd_init\(\);", False,
         '\thdd_err("A90V765 hdd_driver_load before hdd_init");',
         "locate hdd_init entry"),
    Edit(HDD_MAIN, r"^\s*errno = wlan_hdd_state_ctrl_param_create\(\);", False,
         '\thdd_err("A90V765 hdd_driver_load before qcwlanstate_create");',
         "locate qcwlanstate create stage"),
    Edit(HDD_MAIN, r"^\s*errno = pld_init\(\);", False,
         '\thdd_err("A90V765 hdd_driver_load before pld_init");',
         "locate PLD init entry"),
    Edit(HDD_MAIN, r"^\s*errno = wlan_hdd_register_driver\(\);", False,
         '\thdd_err("A90V765 hdd_driver_load before wlan_hdd_register_driver");',
         "locate register-driver entry"),
    Edit(HDD_MAIN, r"^\s*hdd_debug\(\"%s: driver loaded\"", False,
         '\thdd_err("A90V765 hdd_driver_load before driver_loaded_marker");',
         "prove path reaches final driver-loaded marker"),
    Edit(HDD_MAIN, r"^\s*status = wlan_hdd_cache_chann_mutex_create\(hdd_ctx\);", False,
         '\thdd_err("A90V765 hdd_wlan_startup enter hdd_ctx:%p", hdd_ctx);',
         "prove full HDD startup starts after probe"),
    Edit(HDD_OPS, r"^\s*int\s+wlan_hdd_register_driver\s*\(", True,
         '\tpr_err("A90V765 wlan_hdd_register_driver enter\\n");',
         "prove HDD register-driver wrapper is entered"),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--source-archive", type=Path, default=DEFAULT_SOURCE_ARCHIVE)
    parser.add_argument("--v760-manifest", type=Path, default=DEFAULT_V760_MANIFEST)
    parser.add_argument("--v763-report", type=Path, default=DEFAULT_V763_REPORT)
    parser.add_argument("--v764-manifest", type=Path, default=DEFAULT_V764_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve_path(path: Path) -> Path:
    return path.expanduser() if path.is_absolute() else repo_path(path)


def read_text(path: Path) -> str:
    resolved = resolve_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def source_archive_info(path: Path) -> dict[str, Any]:
    resolved = resolve_path(path)
    return {
        "path": str(resolved),
        "exists": resolved.exists(),
        "is_file": resolved.is_file() if resolved.exists() else False,
        "size": resolved.stat().st_size if resolved.exists() and resolved.is_file() else None,
    }


def member_map(archive: tarfile.TarFile) -> dict[str, tarfile.TarInfo]:
    suffixes = sorted({edit.file_suffix for edit in EDITS})
    found: dict[str, tarfile.TarInfo] = {}
    for member in archive:
        normalized = member.name.strip("/")
        for suffix in suffixes:
            if normalized.endswith(suffix) and suffix not in found:
                found[suffix] = member
    return found


def line_has_open_brace(lines: list[str], index: int) -> bool:
    for candidate in lines[index : min(len(lines), index + 8)]:
        if "{" in candidate:
            return True
        if ";" in candidate:
            return False
    return False


def insertion_index(lines: list[str], edit: Edit) -> int | None:
    pattern = re.compile(edit.anchor)
    for idx, line in enumerate(lines):
        if not pattern.search(line):
            continue
        if not edit.insert_after:
            return idx
        if not line_has_open_brace(lines, idx):
            continue
        for brace_idx in range(idx, min(len(lines), idx + 8)):
            if "{" in lines[brace_idx]:
                return brace_idx + 1
    return None


def apply_edits(original: dict[str, list[str]]) -> tuple[dict[str, list[str]], list[AppliedEdit]]:
    modified = {name: list(lines) for name, lines in original.items()}
    applied: list[AppliedEdit] = []
    for edit in EDITS:
        lines = modified.get(edit.file_suffix)
        if lines is None:
            applied.append(AppliedEdit(edit.file_suffix, edit.anchor, 0, "missing-file", edit.purpose, edit.text))
            continue
        idx = insertion_index(lines, edit)
        if idx is None:
            applied.append(AppliedEdit(edit.file_suffix, edit.anchor, 0, "missing-anchor", edit.purpose, edit.text))
            continue
        lines.insert(idx, edit.text)
        applied.append(AppliedEdit(edit.file_suffix, edit.anchor, idx + 1, "applied", edit.purpose, edit.text))
    return modified, applied


def load_sources(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, list[str]], dict[str, str]]:
    archive_info = source_archive_info(args.source_archive)
    sources: dict[str, list[str]] = {}
    member_names: dict[str, str] = {}
    if not archive_info["exists"] or not archive_info["is_file"]:
        return {"archive": archive_info, "source_files": {}}, sources, member_names
    with tarfile.open(resolve_path(args.source_archive), "r:gz") as archive:
        found = member_map(archive)
        for suffix, member in found.items():
            extracted = archive.extractfile(member)
            if extracted is None:
                continue
            sources[suffix] = extracted.read().decode("utf-8", errors="replace").splitlines()
            member_names[suffix] = member.name
    return {
        "archive": archive_info,
        "source_files": {
            suffix: {"member": member_names.get(suffix, ""), "line_count": len(lines)}
            for suffix, lines in sources.items()
        },
    }, sources, member_names


def unified_patch(original: dict[str, list[str]], modified: dict[str, list[str]], member_names: dict[str, str]) -> str:
    chunks: list[str] = []
    for suffix in sorted(modified):
        before = list(original[suffix])
        after = list(modified[suffix])
        if before == after:
            continue
        name = member_names.get(suffix, suffix).strip("/")
        chunks.extend(difflib.unified_diff(
            before,
            after,
            fromfile=f"a/{name}",
            tofile=f"b/{name}",
            lineterm="",
        ))
    return "\n".join(chunks) + ("\n" if chunks else "")


def build_checks(args: argparse.Namespace, analysis: dict[str, Any], applied: list[AppliedEdit]) -> list[Check]:
    v760 = analysis["inputs"]["v760"]
    v764 = analysis["inputs"]["v764"]
    missing = [edit for edit in applied if edit.status != "applied"]
    checks = [
        Check(
            "v760-source-targets",
            "pass" if v760.get("decision") == "v760-source-targets-verified" and v760.get("pass") else "blocked",
            "blocker",
            f"decision={v760.get('decision', '')} pass={bool(v760.get('pass'))}",
            "rerun/fix V760 before source patch generation",
        ),
        Check(
            "v763-architecture-rebase",
            "pass" if "v763-icnss-architecture-rebased" in analysis["inputs"]["v763_report"] else "blocked",
            "blocker",
            "ICNSS/QCACLD architecture correction is recorded",
            "record V763 before source patch generation",
        ),
        Check(
            "v764-mdm-helper-retry",
            "pass" if v764.get("decision") == "v764-mdm-helper-started-no-lower-progress" and v764.get("pass") else "blocked",
            "blocker",
            f"decision={v764.get('decision', '')} pass={bool(v764.get('pass'))}",
            "complete V764 before returning to source instrumentation",
        ),
        Check(
            "patch-edits",
            "pass" if not missing else "blocked",
            "blocker",
            f"applied={len(applied) - len(missing)} missing={len(missing)}",
            "review source anchor drift before patch/build gates",
        ),
        Check(
            "patch-scope",
            "pass" if analysis["route"]["patch_prefix"] == PATCH_PREFIX and analysis["route"]["source_mutation_executed"] is False else "blocked",
            "blocker",
            f"prefix={analysis['route']['patch_prefix']} source_mutation={analysis['route']['source_mutation_executed']}",
            "V765 must remain patch-file-only",
        ),
    ]
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], patch_text: str) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v765-icnss-qcacld-log-patch-plan-ready",
            True,
            "plan-only; no source patch generated",
            "run V765 host-only patch generator",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v765-icnss-qcacld-log-patch-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "clear blockers before source patch/build gates",
        )
    if not patch_text.strip():
        return (
            "v765-icnss-qcacld-log-patch-empty",
            False,
            "patch generator produced no diff",
            "inspect source anchors",
        )
    return (
        "v765-icnss-qcacld-log-patch-ready",
        True,
        "minimal A90V765 ICNSS/QCACLD log patch generated for review only",
        "V766 should review/apply/build in a separate gate; no boot image write yet",
    )


def build_analysis(args: argparse.Namespace) -> tuple[dict[str, Any], list[AppliedEdit], str]:
    source, original, member_names = load_sources(args)
    modified, applied = apply_edits(original)
    patch_text = unified_patch(original, modified, member_names)
    v760 = load_json(args.v760_manifest)
    v764 = load_json(args.v764_manifest)
    analysis = {
        "inputs": {
            "v760": {"manifest": str(resolve_path(args.v760_manifest)), "decision": v760.get("decision", ""), "pass": bool(v760.get("pass"))},
            "v763_report": read_text(args.v763_report),
            "v764": {"manifest": str(resolve_path(args.v764_manifest)), "decision": v764.get("decision", ""), "pass": bool(v764.get("pass"))},
        },
        "source": source,
        "route": {
            "target_architecture": "ICNSS/QCACLD SNOC",
            "patch_prefix": PATCH_PREFIX,
            "patch_file": "a90-v765-icnss-qcacld-log.patch",
            "patch_edits": len(applied),
            "patch_bytes": len(patch_text.encode("utf-8")),
            "source_mutation_executed": False,
            "kernel_build_executed": False,
            "boot_image_write_executed": False,
            "next_cycle": "v766-review-apply-build-gate",
        },
    }
    return analysis, applied, patch_text


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    edits = manifest.get("applied_edits") or []
    route = manifest.get("analysis", {}).get("route", {})
    return "\n".join([
        "# V765 ICNSS/QCACLD Log Patch Generator",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- source_mutation_executed: `{manifest['source_mutation_executed']}`",
        f"- kernel_build_executed: `{manifest['kernel_build_executed']}`",
        f"- boot_image_write_executed: `{manifest['boot_image_write_executed']}`",
        "",
        "## Route",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in route.items()]),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in checks
        ]) if checks else "- plan only",
        "",
        "## Edits",
        "",
        markdown_table(["file", "line", "status", "purpose"], [
            [edit["file"], edit["line"], edit["status"], edit["purpose"]]
            for edit in edits
        ]) if edits else "- plan only",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis: dict[str, Any] = {
        "inputs": {},
        "source": {"archive": source_archive_info(args.source_archive), "source_files": {}},
        "route": {
            "patch_prefix": PATCH_PREFIX,
            "source_mutation_executed": False,
            "kernel_build_executed": False,
            "boot_image_write_executed": False,
        },
    }
    applied: list[AppliedEdit] = []
    patch_text = ""
    checks: list[Check] = []
    if args.command != "plan":
        analysis, applied, patch_text = build_analysis(args)
        checks = build_checks(args, analysis, applied)
    decision, ok, reason, next_step = decide(args.command, checks, patch_text)
    manifest: dict[str, Any] = {
        "cycle": "v765",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "source_mutation_executed": False,
        "kernel_build_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "applied_edits": [asdict(edit) for edit in applied],
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    if patch_text:
        store.write_text("a90-v765-icnss-qcacld-log.patch", patch_text)
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    latest = repo_path("tmp/wifi/latest-v765-icnss-qcacld-log-patch.txt")
    write_private_text(latest, str(store.run_dir.relative_to(repo_path(Path(".")))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"source_mutation_executed: {manifest['source_mutation_executed']}")
    print(f"kernel_build_executed: {manifest['kernel_build_executed']}")
    print(f"boot_image_write_executed: {manifest['boot_image_write_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

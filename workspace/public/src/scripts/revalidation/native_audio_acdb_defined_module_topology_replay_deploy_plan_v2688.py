#!/usr/bin/env python3
"""V2688 host-only deploy plan for defined-module-only topology replay.

V2686 proved the V2684 core-derived minimal cal_type 14 payload reaches the DSP
but is rejected by ASM_CMD_ADD_TOPOLOGIES. V2687 classified that selected
0x10005000 record as containing two module IDs absent from the available stock
audio source. This plan builds a V2639-compatible replay manifest that is
identical to V2684 except that cal_type 10 and 14 use the V2687 private
"defined-modules-only" candidates.

No device action occurs here.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2688"
BUILD_TAG = "v2688-acdb-defined-module-topology-replay-deploy-plan"
DEFAULT_BASE_MANIFEST = ROOT / "workspace/private/builds/audio/v2684-acdb-core-topology-replay-deploy-plan/deploy-plan.json"
DEFAULT_CANDIDATE_DIR = ROOT / "workspace/private/builds/audio/v2687-acdb-topology-rejection-candidates"
DEFAULT_PRIVATE_MANIFEST = ROOT / "workspace/private/builds/audio" / BUILD_TAG / "deploy-plan.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2688_AUDIO_ACDB_DEFINED_MODULE_TOPOLOGY_REPLAY_DEPLOY_PLAN_2026-06-18.md"
DEFAULT_REMOTE_DIR = "/cache/a90-acdb-setcal-replay-v2688"
OLD_REMOTE_DIR = "/cache/a90-acdb-setcal-replay-v2684"
CANDIDATES = {
    10: {
        "role": "ADM_CUSTOM_TOPOLOGY_DEFINED_MODULES_ONLY_0x10004000",
        "filename": "cal10-topology-0x10004000-defined-modules-only.bin",
        "topology_id": 0x10004000,
        "expected_sha256": "f8e81e666ee39945a1b4b29f46b1d79f013ad3f944ea7cb19851d2528bf9ab5b",
        "expected_size": 396,
        "remote_name": "01-defined-modules-payload-cal10-topo10004000.bin",
        "replaces_role": "ADM_CUSTOM_TOPOLOGY_FROM_CORE_SELECTED_0x10004000",
        "removed_modules": [0x0001031F, 0x00010943],
    },
    14: {
        "role": "ASM_CUSTOM_TOPOLOGY_DEFINED_MODULES_ONLY_0x10005000",
        "filename": "cal14-topology-0x10005000-defined-modules-only.bin",
        "topology_id": 0x10005000,
        "expected_sha256": "c02c2226a07d8204bde278c141c1be10b63bd1f33307c443401f287132e788c4",
        "expected_size": 396,
        "remote_name": "02-defined-modules-payload-cal14-topo10005000.bin",
        "replaces_role": "ASM_CUSTOM_TOPOLOGY_FROM_CORE_SELECTED_0x10005000",
        "removed_modules": [0x10001F30, 0x10001F10],
    },
}


def rel(path: Path | str) -> str:
    target = Path(path)
    try:
        return str(target.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_all_zero(path: Path) -> bool:
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            if any(chunk):
                return False
    return True


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], *, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if mode is not None:
        path.chmod(mode)


def verify_file(path: Path, *, expected_size: int, expected_sha256: str) -> dict[str, Any]:
    state: dict[str, Any] = {
        "local_path_private": rel(path),
        "exists": path.exists(),
        "ok": False,
        "private_only": True,
    }
    if not path.exists() or not path.is_file():
        return state
    size = path.stat().st_size
    digest = sha256_file(path)
    state.update({
        "mode": oct(path.stat().st_mode & 0o777),
        "size": size,
        "sha256": digest,
        "nonzero": not is_all_zero(path),
        "size_matches": size == expected_size,
        "sha256_matches": digest == expected_sha256,
    })
    state["ok"] = bool(state["nonzero"] and state["size_matches"] and state["sha256_matches"])
    return state


def replace_strings(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, str):
        out = value
        for old, new in replacements.items():
            out = out.replace(old, new)
        return out
    if isinstance(value, list):
        return [replace_strings(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: replace_strings(item, replacements) for key, item in value.items()}
    return value


def file_by_remote(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item.get("remote_path")): item for item in manifest.get("files") or [] if item.get("remote_path")}


def build_plan(base_manifest: Path, candidate_dir: Path, *, remote_dir: str = DEFAULT_REMOTE_DIR) -> dict[str, Any]:
    base = read_json(base_manifest)
    plan = replace_strings(copy.deepcopy(base), {OLD_REMOTE_DIR: remote_dir})
    remote_replacements: dict[str, str] = {}
    for cal_type, meta in CANDIDATES.items():
        old_remote = next(
            entry["payload_remote"] for entry in plan["replay_entries"]
            if int(entry.get("cal_type")) == cal_type and entry.get("entry_kind") == "basic-payload"
        )
        remote_replacements[str(old_remote)] = f"{remote_dir.rstrip('/')}/{meta['remote_name']}"
    plan = replace_strings(plan, remote_replacements)

    files_by = file_by_remote(plan)
    candidate_states: dict[int, dict[str, Any]] = {}
    for cal_type, meta in CANDIDATES.items():
        candidate_path = candidate_dir / str(meta["filename"])
        state = verify_file(candidate_path, expected_size=int(meta["expected_size"]), expected_sha256=str(meta["expected_sha256"]))
        candidate_states[cal_type] = state
        remote_path = f"{remote_dir.rstrip('/')}/{meta['remote_name']}"
        file_entry = files_by.get(remote_path)
        if not file_entry:
            raise ValueError(f"missing remote file entry for cal_type {cal_type}: {remote_path}")
        file_entry["local"] = state
        file_entry["ok"] = bool(state.get("ok"))
        file_entry["remote_sha256_command"] = f"sha256sum {remote_path}"

    for entry in plan.get("replay_entries") or []:
        cal_type = int(entry.get("cal_type"))
        if cal_type not in CANDIDATES or entry.get("entry_kind") != "basic-payload":
            continue
        meta = CANDIDATES[cal_type]
        entry["role"] = meta["role"]
        entry["source"] = "V2687 defined-modules-only candidate after V2686 ADSP_EBADPARAM"
        entry["topology_id"] = meta["topology_id"]
        entry["removed_module_ids"] = meta["removed_modules"]
        entry["ok"] = bool(candidate_states[cal_type].get("ok"))

    basic_payloads = []
    for entry in plan.get("replay_entries") or []:
        if entry.get("entry_kind") == "basic-payload":
            basic_payloads.append(copy.deepcopy(entry))
    plan.update({
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": False,
        "flash_action": False,
        "native_calibration_ioctls_run": False,
        "source_base_manifest": rel(base_manifest),
        "source_v2687_candidate_dir": rel(candidate_dir),
        "remote_dir": remote_dir,
        "private_manifest_path": rel(DEFAULT_PRIVATE_MANIFEST),
        "variant": "defined-modules-only-cal10-cal14",
        "basic_payloads": basic_payloads,
    })
    all_inputs_ok = all(bool(item.get("ok")) for item in plan.get("files") or []) and all(
        bool(entry.get("ok")) for entry in plan.get("replay_entries") or []
    )
    plan["all_inputs_ok"] = all_inputs_ok
    plan["ok"] = all_inputs_ok
    plan["native_replay_ready"] = all_inputs_ok
    plan["safe_to_run_native_replay"] = all_inputs_ok
    plan["replay_blockers"] = [] if all_inputs_ok else ["one or more V2688 input files failed verification"]
    plan["summary"] = {
        "decision": "v2688-defined-module-topology-replay-deploy-plan-ready" if all_inputs_ok else "v2688-defined-module-topology-replay-deploy-plan-blocked",
        "replay_entry_count": len(plan.get("replay_entries") or []),
        "file_count": len(plan.get("files") or []),
        "cal_order": [int(entry.get("cal_type")) for entry in plan.get("replay_entries") or []],
        "final_set_index": len(plan.get("replay_entries") or []) - 1,
        "replaced_cal_types": sorted(CANDIDATES),
    }
    return plan


def redacted_files(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for item in files:
        clone = copy.deepcopy(item)
        local = clone.get("local") or {}
        local.pop("local_path_private", None)
        clone["local"] = local
        output.append(clone)
    return output


def table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    out = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join("---" for _ in rows[0]) + " |"]
    out.extend("| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |" for row in rows[1:])
    return "\n".join(out)


def markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# NATIVE_INIT V2688 — ACDB defined-module topology replay deploy plan",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only construction of a V2639-compatible replay manifest using V2687 defined-modules-only cal_type 10/14 candidates. No device action, flash, calibration ioctl, route write, or PCM probe occurred.",
        "",
        "## Result",
        "",
        f"- decision: `{plan['summary']['decision']}`",
        f"- native_replay_ready: `{plan['native_replay_ready']}`",
        f"- private_manifest_path: `{plan['private_manifest_path']}`",
        f"- source_base_manifest: `{plan['source_base_manifest']}`",
        f"- source_v2687_candidate_dir: `{plan['source_v2687_candidate_dir']}`",
        "",
        "## Replay order",
        "",
    ]
    rows = [["seq", "kind", "cal_type", "role", "ok", "payload_remote"]]
    for entry in plan.get("replay_entries") or []:
        rows.append([
            str(entry.get("sequence")),
            str(entry.get("entry_kind")),
            str(entry.get("cal_type")),
            f"`{entry.get('role')}`",
            f"`{entry.get('ok')}`",
            f"`{entry.get('payload_remote')}`" if entry.get("payload_remote") else "none",
        ])
    lines.append(table(rows))
    lines.extend(["", "## Replacement payloads", ""])
    rows = [["cal_type", "topology", "removed modules", "bytes", "sha256", "private path"]]
    files_by = file_by_remote(plan)
    for cal_type, meta in CANDIDATES.items():
        remote = f"{plan['remote_dir'].rstrip('/')}/{meta['remote_name']}"
        local = (files_by[remote].get("local") or {})
        rows.append([
            str(cal_type),
            f"`0x{meta['topology_id']:08x}`",
            ", ".join(f"`0x{x:08x}`" for x in meta["removed_modules"]),
            str(local.get("size")),
            f"`{local.get('sha256')}`",
            f"`{local.get('local_path_private')}`",
        ])
    lines.append(table(rows))
    lines.extend([
        "",
        "## Interpretation",
        "",
        "V2688 is the direct follow-up to V2687. It does not re-run the dominated `cal14-current-unique-plus` branch. Instead, it keeps the V2684 replay order and route/probe contract but replaces only the forged cal_type `10` and `14` topology payloads with candidates whose module IDs are all defined in the available stock audio source.",
        "",
        "This does not prove the DSP will accept the result. It makes the next live run falsifiable: if `ASM_CMD_ADD_TOPOLOGIES` still returns `ADSP_EBADPARAM`, the problem is not merely the two undefined `0x10001f30`/`0x10001f10` module IDs, and the next branch should return to ACDB request-tuple recovery rather than more core-derived guessing.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_defined_module_topology_replay_deploy_plan_v2688.py tests/test_native_audio_acdb_defined_module_topology_replay_deploy_plan_v2688.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_defined_module_topology_replay_deploy_plan_v2688 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_defined_module_topology_replay_deploy_plan_v2688.py --write-report`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_runner_plan_v2638.py --v2636-manifest workspace/private/builds/audio/v2688-acdb-defined-module-topology-replay-deploy-plan/deploy-plan.json --private-manifest workspace/private/builds/audio/v2688-acdb-defined-module-topology-replay-deploy-plan/runner-plan.json`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover -s tests -v`",
        "- `git diff --check`",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-manifest", type=Path, default=DEFAULT_BASE_MANIFEST)
    parser.add_argument("--candidate-dir", type=Path, default=DEFAULT_CANDIDATE_DIR)
    parser.add_argument("--private-manifest", type=Path, default=DEFAULT_PRIVATE_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--remote-dir", default=DEFAULT_REMOTE_DIR)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    plan = build_plan(args.base_manifest, args.candidate_dir, remote_dir=args.remote_dir)
    plan["private_manifest_path"] = rel(args.private_manifest)
    plan["files_redacted"] = redacted_files(plan.get("files") or [])
    write_json(args.private_manifest, plan, mode=0o600)
    if args.write_report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(markdown(plan), encoding="utf-8")
    print(json.dumps({
        "decision": plan["summary"]["decision"],
        "native_replay_ready": plan["native_replay_ready"],
        "manifest": rel(args.private_manifest),
        "report": rel(args.report) if args.write_report else None,
        "replaced_cal_types": plan["summary"]["replaced_cal_types"],
    }, indent=2, sort_keys=True))
    return 0 if plan["native_replay_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

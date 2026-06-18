#!/usr/bin/env python3
"""V2694 host-only ASM custom-topology geometry audit.

This reconciles the V2680/V2689 ADSP_EBADPARAM failure with the stock q6asm
source and the private replay payload metadata.  It does not run a device step,
flash, or issue any audio calibration ioctl.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import analyze_audio_acdb_core_topology_bridge_v2683 as v2683

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2694"
DEFAULT_SOURCE_ROOT = ROOT / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio"
DEFAULT_Q6ASM = DEFAULT_SOURCE_ROOT / "dsp/q6asm.c"
DEFAULT_CAL_UTILS = DEFAULT_SOURCE_ROOT / "dsp/audio_cal_utils.c"
DEFAULT_UAPI = DEFAULT_SOURCE_ROOT / "include/uapi/linux/msm_audio_calibration.h"
DEFAULT_V2679_MANIFEST = ROOT / "workspace/private/builds/audio/v2679-acdb-custom-topology-replay-deploy-plan/deploy-plan.json"
DEFAULT_V2688_MANIFEST = ROOT / "workspace/private/builds/audio/v2688-acdb-defined-module-topology-replay-deploy-plan/deploy-plan.json"
DEFAULT_V2680_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2680_AUDIO_ACDB_CUSTOM_TOPOLOGY_REPLAY_LIVE_2026-06-18.md"
DEFAULT_V2689_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2689_AUDIO_ACDB_DEFINED_MODULE_TOPOLOGY_LIVE_REPLAY_2026-06-18.md"
DEFAULT_V2676_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2676_AUDIO_ACDB_ADM_CUSTOM_TOPOLOGY_GET_RECON_2026-06-18.md"
DEFAULT_V2693_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2693_AUDIO_ACDB_LOWER_PTRTARGET_CAPTURE_LIVE_HANDOFF_2026-06-18.md"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2694_AUDIO_ACDB_ASM_TOPOLOGY_GEOMETRY_AUDIT_2026-06-18.md"
TARGET_CAL_TYPES = (10, 14, 24)
ASM_CAL_TYPE = 14


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(errors="ignore") if path.exists() else ""


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_remote_file_map(manifest: dict[str, Any]) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for entry in manifest.get("files") or []:
        remote = entry.get("remote_path")
        local = ((entry.get("local") or {}).get("local_path_private"))
        if remote and local:
            path = Path(local)
            out[str(remote)] = path if path.is_absolute() else ROOT / path
    return out


def load_manifest_set_args(path: Path) -> dict[int, dict[str, Any]]:
    if not path.exists():
        return {}
    manifest = read_json(path)
    remote_to_local = manifest_remote_file_map(manifest)
    out: dict[int, dict[str, Any]] = {}

    def ingest(entry: dict[str, Any], default_kind: str) -> None:
        if not entry.get("cal_type"):
            return
        cal_type = int(entry.get("cal_type"))
        if cal_type not in TARGET_CAL_TYPES:
            return
        arg_remote = str(entry.get("arg_remote") or "")
        payload_remote = str(entry.get("payload_remote") or "")
        if not payload_remote:
            return
        current = out.get(cal_type)
        # Prefer exact captured SET args when present; otherwise keep generated/basic payload entries.
        if current and current.get("arg_remote"):
            return
        arg_path = remote_to_local.get(arg_remote)
        payload_path = remote_to_local.get(payload_remote)
        out[cal_type] = {
            "cal_type": cal_type,
            "role": str(entry.get("role") or ""),
            "entry_kind": str(entry.get("entry_kind") or default_kind),
            "arg_path": arg_path,
            "payload_path": payload_path,
            "arg_remote": arg_remote,
            "payload_remote": payload_remote,
            "source_manifest": path,
        }

    for entry in manifest.get("set_args") or []:
        ingest(entry, "exact-set")
    for entry in manifest.get("basic_payloads") or []:
        ingest(entry, "basic-payload")
    for entry in manifest.get("replay_entries") or []:
        ingest(entry, "replay-entry")
    return out


def decode_audio_cal_basic(data: bytes) -> dict[str, Any]:
    if len(data) < 32:
        raise ValueError(f"audio_cal_basic requires 32 bytes, got {len(data)}")
    words = struct.unpack("<8i", data[:32])
    return {
        "data_size": words[0],
        "version": words[1],
        "cal_type": words[2],
        "cal_type_size": words[3],
        "cal_hdr_version": words[4],
        "buffer_number": words[5],
        "cal_size": words[6],
        "mem_handle": words[7],
        "arg_len": len(data),
        "sha256": sha256(data),
    }


def parse_fixed_payload_summary(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {"exists": False}
    data = path.read_bytes()
    summary: dict[str, Any] = {
        "exists": True,
        "path_private": rel(path),
        "size": len(data),
        "sha256": sha256(data),
    }
    try:
        records = v2683.parse_fixed_payload(data)
    except Exception as exc:  # noqa: BLE001 - report parser failure as data.
        summary.update({"parse_ok": False, "parse_error": str(exc)})
        return summary
    summary.update({
        "parse_ok": True,
        "topology_count": len(records),
        "topologies": [
            {
                "topology_id": record.topology_id,
                "topology_hex": f"0x{record.topology_id:08x}",
                "module_count": len(record.modules),
                "modules": [
                    {"module_id": module_id, "module_hex": f"0x{module_id:08x}", "instance_id": instance_id, "instance_hex": f"0x{instance_id:08x}"}
                    for module_id, instance_id in record.modules
                ],
            }
            for record in records
        ],
    })
    return summary


def summarize_manifest(path: Path) -> dict[str, Any]:
    set_args = load_manifest_set_args(path)
    entries: dict[str, Any] = {}
    for cal_type, entry in sorted(set_args.items()):
        arg_path = entry["arg_path"]
        payload_path = entry["payload_path"]
        arg_summary = {"exists": False}
        if arg_path and arg_path.exists():
            arg_summary = decode_audio_cal_basic(arg_path.read_bytes())
            arg_summary["exists"] = True
            arg_summary["path_private"] = rel(arg_path)
        entries[str(cal_type)] = {
            "role": entry["role"],
            "entry_kind": entry.get("entry_kind", ""),
            "arg": arg_summary,
            "payload": parse_fixed_payload_summary(payload_path),
        }
    return {"path_private": rel(path), "exists": path.exists(), "entries": entries}


def line_no_for(path: Path, needle: str) -> int | None:
    if not path.exists():
        return None
    for index, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
        if needle in line:
            return index
    return None


def source_markers(q6asm: Path, cal_utils: Path, uapi: Path) -> dict[str, Any]:
    q6asm_text = read_text(q6asm)
    cal_utils_text = read_text(cal_utils)
    uapi_text = read_text(uapi)
    markers = {
        "q6asm_uses_get_only_cal_block": "cal_utils_get_only_cal_block(cal_data[ASM_CUSTOM_TOP_CAL])" in q6asm_text,
        "q6asm_sets_payload_size_from_cal_data_size": "asm_top.payload_size = cal_block->cal_data.size" in q6asm_text,
        "q6asm_sets_payload_addr_from_cal_data_paddr": "asm_top.payload_addr_lsw = lower_32_bits(cal_block->cal_data.paddr)" in q6asm_text,
        "q6asm_sends_asm_cmd_add_topologies": "asm_top.hdr.opcode = ASM_CMD_ADD_TOPOLOGIES" in q6asm_text,
        "q6asm_sets_custom_topology_dirty_on_set_cal": "set_custom_topology = 1" in q6asm_text,
        "cal_utils_set_cal_copies_only_cal_info_not_payload": "cal_block->cal_data.size = basic_data->cal_data.cal_size" in cal_utils_text and "memcpy(cal_block->cal_info" in cal_utils_text,
        "cal_utils_create_block_imports_dma_buf_from_mem_handle": "basic_cal->cal_data.mem_handle > 0" in cal_utils_text and "cal_block_ion_alloc" in cal_utils_text,
        "uapi_audio_cal_basic_32_shape": "struct audio_cal_basic" in uapi_text and "struct audio_cal_header" in uapi_text and "struct audio_cal_type_basic" in uapi_text,
    }
    refs = {
        "send_asm_custom_topology": line_no_for(q6asm, "int send_asm_custom_topology"),
        "payload_size_from_cal_data_size": line_no_for(q6asm, "asm_top.payload_size = cal_block->cal_data.size"),
        "asm_cmd_add_topologies": line_no_for(q6asm, "asm_top.hdr.opcode = ASM_CMD_ADD_TOPOLOGIES"),
        "q6asm_set_custom_topology": line_no_for(q6asm, "set_custom_topology = 1"),
        "cal_utils_set_cal": line_no_for(cal_utils, "int cal_utils_set_cal"),
        "cal_utils_size_assignment": line_no_for(cal_utils, "cal_block->cal_data.size = basic_data->cal_data.cal_size"),
        "audio_cal_basic": line_no_for(uapi, "struct audio_cal_basic"),
    }
    return {"markers": markers, "refs": refs}


def report_contains(path: Path, needle: str) -> bool:
    return needle in read_text(path)


def classify(summary: dict[str, Any]) -> dict[str, Any]:
    v2679_asm = summary["manifests"]["v2679"]["entries"].get(str(ASM_CAL_TYPE), {})
    v2688_asm = summary["manifests"]["v2688"]["entries"].get(str(ASM_CAL_TYPE), {})
    arg = v2679_asm.get("arg") or {}
    payload = v2679_asm.get("payload") or {}
    src = summary["source"]
    markers = src["markers"]
    asm_arg_shape_ok = (
        arg.get("data_size") == 32
        and arg.get("cal_type") == ASM_CAL_TYPE
        and arg.get("cal_type_size") == 16
        and arg.get("cal_size") == payload.get("size")
        and int(arg.get("mem_handle") or 0) > 0
    )
    asm_payload_fixed_ok = bool(payload.get("parse_ok"))
    q6asm_path_ok = all(markers.get(key) for key in (
        "q6asm_uses_get_only_cal_block",
        "q6asm_sets_payload_size_from_cal_data_size",
        "q6asm_sets_payload_addr_from_cal_data_paddr",
        "q6asm_sends_asm_cmd_add_topologies",
        "q6asm_sets_custom_topology_dirty_on_set_cal",
        "cal_utils_create_block_imports_dma_buf_from_mem_handle",
    ))
    v2680_asm_rejected = summary["reports"]["v2680"]["asm_ebadparam"]
    v2689_asm_rejected = summary["reports"]["v2689"]["asm_ebadparam"]
    defined_payload = v2688_asm.get("payload") or {}
    defined_payload_differs = payload.get("sha256") != defined_payload.get("sha256")
    decision = "v2694-asm-ebadparam-classified-as-dsp-payload-semantics"
    if not asm_arg_shape_ok or not asm_payload_fixed_ok or not q6asm_path_ok:
        decision = "v2694-asm-host-geometry-still-ambiguous"
    return {
        "decision": decision,
        "asm_arg_shape_ok": asm_arg_shape_ok,
        "asm_payload_fixed_ok": asm_payload_fixed_ok,
        "q6asm_path_ok": q6asm_path_ok,
        "v2680_asm_rejected": v2680_asm_rejected,
        "v2689_asm_rejected": v2689_asm_rejected,
        "defined_payload_differs_from_exact_capture": defined_payload_differs,
        "interpretation": (
            "Host SET geometry is not the active blocker: q6asm sends the allocated cal14 dma-buf "
            "payload and size directly to ASM_CMD_ADD_TOPOLOGIES, V2679/V2688 SETs were accepted, "
            "and both the exact captured cal14 payload and the defined-modules-only variant still ended "
            "at ADSP_EBADPARAM. The remaining evidence points to DSP-side payload semantics or to a "
            "still-missing exact ASM topology record, not to replay arg/memhandle shape."
            if decision == "v2694-asm-ebadparam-classified-as-dsp-payload-semantics"
            else "The source/payload checks did not all pass; do not infer DSP semantics yet."
        ),
        "next_action": (
            "Do not rerun existing cal14/defined-only manifests. Return to exact lower ACDB ASM topology recovery or route-specific Android-good capture; if no exact cal14 can be recovered, mark native speaker as blocked on DSP topology semantics rather than SET delivery."
            if decision == "v2694-asm-ebadparam-classified-as-dsp-payload-semantics"
            else "Close the failed geometry check before another live replay."
        ),
    }


def summarize(args: argparse.Namespace) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "run_id": RUN_ID,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": False,
        "native_calibration_ioctls_run": False,
        "source": source_markers(args.q6asm, args.cal_utils, args.uapi),
        "manifests": {
            "v2679": summarize_manifest(args.v2679_manifest),
            "v2688": summarize_manifest(args.v2688_manifest),
        },
        "reports": {
            "v2676": {
                "path": rel(args.v2676_report),
                "cal10_absent_not_capture_gap": report_contains(args.v2676_report, "cal_type 10 is not a V2675 capture-plumbing miss"),
            },
            "v2680": {
                "path": rel(args.v2680_report),
                "all_set_ok": report_contains(args.v2680_report, "A90_SETCAL_REPLAY_ALL_SET_OK"),
                "asm_ebadparam": report_contains(args.v2680_report, "send_asm_custom_topology: DSP returned error[ADSP_EBADPARAM]"),
            },
            "v2689": {
                "path": rel(args.v2689_report),
                "defined_modules_only_rejected": report_contains(args.v2689_report, "V2689 falsifies the narrow") or report_contains(args.v2689_report, "defined-module topology"),
                "asm_ebadparam": report_contains(args.v2689_report, "send_asm_custom_topology: DSP returned error[ADSP_EBADPARAM]"),
            },
            "v2693": {
                "path": rel(args.v2693_report),
                "ptrtarget_status_only": report_contains(args.v2693_report, "v2693-ptrtarget-status-only"),
                "block_snapshots_for_10_14_24": report_contains(args.v2693_report, "block_snapshot_cal_types: `[10, 14, 24]`"),
            },
        },
    }
    summary["classification"] = classify(summary)
    return summary


def md_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    header = rows[0]
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    out.extend("| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |" for row in rows[1:])
    return "\n".join(out)


def fmt_bool(value: Any) -> str:
    return f"`{bool(value)}`"


def markdown(summary: dict[str, Any]) -> str:
    c = summary["classification"]
    lines = [
        "# NATIVE_INIT V2694 — ACDB ASM topology geometry audit",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only audit after V2693 and the repeated V2680/V2689 `send_asm_custom_topology` `ADSP_EBADPARAM` failures. No device action, flash, `/dev/msm_audio_cal` ioctl, mixer write, or PCM probe occurred. Private payload bytes were read only for metadata, SHA-256, and topology grammar checks; raw bytes are not included here.",
        "",
        "## Result",
        "",
        f"- decision: `{c['decision']}`",
        f"- host_only: `{summary['host_only']}`",
        f"- device_action: `{summary['device_action']}`",
        f"- asm_arg_shape_ok: `{c['asm_arg_shape_ok']}`",
        f"- asm_payload_fixed_ok: `{c['asm_payload_fixed_ok']}`",
        f"- q6asm_path_ok: `{c['q6asm_path_ok']}`",
        f"- v2680_asm_rejected: `{c['v2680_asm_rejected']}`",
        f"- v2689_asm_rejected: `{c['v2689_asm_rejected']}`",
        "",
        "## Source Contract",
        "",
    ]
    refs = summary["source"]["refs"]
    rows = [["marker", "present", "source ref"]]
    for key, value in summary["source"]["markers"].items():
        ref_key = {
            "q6asm_uses_get_only_cal_block": "send_asm_custom_topology",
            "q6asm_sets_payload_size_from_cal_data_size": "payload_size_from_cal_data_size",
            "q6asm_sets_payload_addr_from_cal_data_paddr": "send_asm_custom_topology",
            "q6asm_sends_asm_cmd_add_topologies": "asm_cmd_add_topologies",
            "q6asm_sets_custom_topology_dirty_on_set_cal": "q6asm_set_custom_topology",
            "cal_utils_set_cal_copies_only_cal_info_not_payload": "cal_utils_size_assignment",
            "cal_utils_create_block_imports_dma_buf_from_mem_handle": "cal_utils_set_cal",
            "uapi_audio_cal_basic_32_shape": "audio_cal_basic",
        }.get(key, "")
        line = refs.get(ref_key) if ref_key else None
        source_ref = "-"
        if line:
            source_path = "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/q6asm.c"
            if ref_key.startswith("cal_utils"):
                source_path = "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/dsp/audio_cal_utils.c"
            elif ref_key == "audio_cal_basic":
                source_path = "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/include/uapi/linux/msm_audio_calibration.h"
            source_ref = f"`{source_path}:{line}`"
        rows.append([f"`{key}`", f"`{value}`", source_ref])
    lines.append(md_table(rows))
    lines.extend(["", "## Manifest Geometry", ""])
    rows = [["manifest", "cal_type", "role", "arg", "payload"]]
    for name, manifest in summary["manifests"].items():
        for cal in (10, 14, 24):
            entry = manifest["entries"].get(str(cal))
            if not entry:
                rows.append([name, str(cal), "absent", "-", "-"])
                continue
            arg = entry["arg"]
            payload = entry["payload"]
            arg_text = "missing"
            if arg.get("exists"):
                arg_text = f"data_size={arg['data_size']} cal_type={arg['cal_type']} cal_type_size={arg['cal_type_size']} cal_size={arg['cal_size']} mem_handle={arg['mem_handle']} sha=`{arg['sha256']}`"
            payload_text = "missing"
            if payload.get("exists"):
                topologies = ", ".join(t["topology_hex"] for t in payload.get("topologies") or [])
                payload_text = f"size={payload['size']} parse_ok={payload.get('parse_ok')} topologies={topologies or '-'} sha=`{payload['sha256']}`"
            role = f"`{entry['role']}`"
            if entry.get("entry_kind"):
                role += f" ({entry['entry_kind']})"
            rows.append([name, str(cal), role, arg_text, payload_text])
    lines.append(md_table(rows))
    lines.extend([
        "",
        "## Prior Run Reconciliation",
        "",
    ])
    rows = [["run", "check", "value"]]
    for run_name, report in summary["reports"].items():
        for key, value in report.items():
            if key == "path":
                continue
            rows.append([run_name, f"`{key}`", f"`{value}`"])
    lines.append(md_table(rows))
    lines.extend([
        "",
        "## Interpretation",
        "",
        c["interpretation"],
        "",
        "The important source fact is that `send_asm_custom_topology()` does not reinterpret or rebuild the topology payload. `cal_utils_set_cal()` stores the captured `cal_size`; `send_asm_custom_topology()` maps the same dma-buf allocation and sends `payload_addr`, `mem_map_handle`, and `payload_size` directly in `ASM_CMD_ADD_TOPOLOGIES`. Therefore the V2680 and V2689 failures are past the host replay interface and inside ADSP topology validation.",
        "",
        "V2693 remains useful because it proved lower-node block snapshots fire for cal_types `10`, `14`, and `24`; however it only produced `ptrtarget_unmapped` status records and did not recover new raw topology bytes. That does not justify another same-route pointer-target retry before the request/argument model is changed.",
        "",
        "## Next Unit",
        "",
        c["next_action"],
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_asm_topology_geometry_v2694.py tests/test_analyze_audio_acdb_asm_topology_geometry_v2694.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_asm_topology_geometry_v2694 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_asm_topology_geometry_v2694.py --write-report`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover tests -v`",
        "- `git diff --check`",
        "",
    ])
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--q6asm", type=Path, default=DEFAULT_Q6ASM)
    parser.add_argument("--cal-utils", type=Path, default=DEFAULT_CAL_UTILS)
    parser.add_argument("--uapi", type=Path, default=DEFAULT_UAPI)
    parser.add_argument("--v2679-manifest", type=Path, default=DEFAULT_V2679_MANIFEST)
    parser.add_argument("--v2688-manifest", type=Path, default=DEFAULT_V2688_MANIFEST)
    parser.add_argument("--v2676-report", type=Path, default=DEFAULT_V2676_REPORT)
    parser.add_argument("--v2680-report", type=Path, default=DEFAULT_V2680_REPORT)
    parser.add_argument("--v2689-report", type=Path, default=DEFAULT_V2689_REPORT)
    parser.add_argument("--v2693-report", type=Path, default=DEFAULT_V2693_REPORT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    summary = summarize(args)
    if args.write_report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(markdown(summary), encoding="utf-8")
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(json.dumps({
            "decision": summary["classification"]["decision"],
            "asm_arg_shape_ok": summary["classification"]["asm_arg_shape_ok"],
            "asm_payload_fixed_ok": summary["classification"]["asm_payload_fixed_ok"],
            "q6asm_path_ok": summary["classification"]["q6asm_path_ok"],
            "report": rel(args.report) if args.write_report else None,
        }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

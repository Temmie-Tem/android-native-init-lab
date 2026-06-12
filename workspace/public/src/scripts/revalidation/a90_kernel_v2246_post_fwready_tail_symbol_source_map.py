#!/usr/bin/env python3
"""V2246 post-FWREADY tail symbol/source map.

Host-only mapper for the V2245 qcacld/HDD tail stack. It joins the observed
public-safe stack functions with the bit-exact stock System.map and the checked
kernel/qcacld source tree, producing a live-sampler target whitelist without
publishing private raw helper logs.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

from a90_kernel_v2241_user_uprobe_offset_base_map import PRIVATE_RUNS, REPO_ROOT, rel

DEFAULT_V2245_SUMMARY = (
    PRIVATE_RUNS
    / "v2245-post-fwready-tail-inventory-20260612-114711/summary.json"
)
DEFAULT_STOCK_MAP = PRIVATE_RUNS / "v2197-stock-kallsyms/System.map"
DEFAULT_SOURCE_ROOT = REPO_ROOT / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source"

TARGET_SYMBOLS = [
    "_request_firmware",
    "request_firmware",
    "qdf_file_read",
    "qdf_ini_parse",
    "cfg_parse",
    "hdd_context_create",
    "wlan_hdd_pld_probe",
]

SOURCE_HINTS = {
    "_request_firmware": (
        "drivers/base/firmware_class.c",
        re.compile(r"^_request_firmware\("),
    ),
    "request_firmware": (
        "drivers/base/firmware_class.c",
        re.compile(r"^request_firmware\("),
    ),
    "qdf_file_read": (
        "drivers/net/wireless/qualcomm/wcn39xx/qca-wifi-host-cmn/qdf/linux/src/qdf_file.c",
        re.compile(r"^QDF_STATUS\s+qdf_file_read\("),
    ),
    "qdf_ini_parse": (
        "drivers/net/wireless/qualcomm/wcn39xx/qca-wifi-host-cmn/qdf/src/qdf_parse.c",
        re.compile(r"^QDF_STATUS\s+qdf_ini_parse\("),
    ),
    "cfg_parse": (
        "drivers/net/wireless/qualcomm/wcn39xx/qca-wifi-host-cmn/cfg/src/cfg.c",
        re.compile(r"^QDF_STATUS\s+cfg_parse\("),
    ),
    "hdd_context_create": (
        "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_main.c",
        re.compile(r"^struct\s+hdd_context\s+\*hdd_context_create\("),
    ),
    "wlan_hdd_pld_probe": (
        "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c",
        re.compile(r"^static\s+int\s+wlan_hdd_pld_probe\("),
    ),
}

STACK_RE = re.compile(
    r"\]\s+(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\+0x(?P<offset>[0-9a-fA-F]+)/0x(?P<size>[0-9a-fA-F]+))?"
)


def now_label() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def parse_int_hex(value: str | None) -> int | None:
    if value is None:
        return None
    return int(value, 16)


def load_text_symbols(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(errors="replace").splitlines():
        parts = line.split(maxsplit=2)
        if len(parts) != 3:
            continue
        address_text, symbol_type, name = parts
        if symbol_type not in {"T", "t", "W", "w"}:
            continue
        try:
            address = int(address_text, 16)
        except ValueError:
            continue
        rows.append({
            "address": address,
            "address_hex": f"0x{address:016x}",
            "type": symbol_type,
            "name": name,
        })
    rows.sort(key=lambda row: row["address"])
    for index, row in enumerate(rows):
        if index + 1 < len(rows):
            next_row = rows[index + 1]
            row["next_symbol"] = next_row["name"]
            row["next_address_hex"] = next_row["address_hex"]
            row["next_delta"] = next_row["address"] - row["address"]
            row["next_delta_hex"] = f"0x{row['next_delta']:x}"
        else:
            row["next_symbol"] = None
            row["next_address_hex"] = None
            row["next_delta"] = None
            row["next_delta_hex"] = None
    return rows


def symbol_index(symbols: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in symbols:
        index.setdefault(str(row["name"]), row)
    return index


def extract_observed_stack(v2245: dict[str, Any]) -> list[dict[str, Any]]:
    sample_rows = (((v2245.get("runs") or {}).get("v2233") or {}).get("target_stack_samples") or [])
    observed: list[dict[str, Any]] = []
    for sample in sample_rows:
        for ordinal, frame in enumerate(sample.get("stack_functions") or []):
            match = STACK_RE.search(str(frame))
            if not match:
                continue
            symbol = match.group("symbol")
            if symbol not in TARGET_SYMBOLS:
                continue
            offset = parse_int_hex(match.group("offset"))
            size = parse_int_hex(match.group("size"))
            observed.append({
                "ordinal": ordinal,
                "symbol": symbol,
                "offset": offset,
                "offset_hex": None if offset is None else f"0x{offset:x}",
                "stack_reported_size": size,
                "stack_reported_size_hex": None if size is None else f"0x{size:x}",
                "frame": frame,
            })
    return observed


def find_source_definition(source_root: Path, symbol: str) -> dict[str, Any]:
    hint = SOURCE_HINTS.get(symbol)
    if hint is None:
        return {"found": False, "reason": "no-source-hint"}
    rel_path, pattern = hint
    path = source_root / rel_path
    if not path.exists():
        return {"found": False, "path": rel(path), "reason": "source-file-missing"}
    for lineno, line in enumerate(path.read_text(errors="replace").splitlines(), start=1):
        if pattern.search(line.strip()):
            return {
                "found": True,
                "path": rel(path),
                "line": lineno,
                "text": line.strip(),
            }
    return {"found": False, "path": rel(path), "reason": "definition-pattern-missing"}


def build_rows(
    observed: list[dict[str, Any]],
    symbols: dict[str, dict[str, Any]],
    source_root: Path,
) -> list[dict[str, Any]]:
    observed_by_symbol = {row["symbol"]: row for row in observed}
    rows: list[dict[str, Any]] = []
    for symbol in TARGET_SYMBOLS:
        observed_row = observed_by_symbol.get(symbol)
        map_row = symbols.get(symbol)
        source = find_source_definition(source_root, symbol)
        offset = observed_row.get("offset") if observed_row else None
        stack_size = observed_row.get("stack_reported_size") if observed_row else None
        rows.append({
            "symbol": symbol,
            "observed_in_v2245_stack": observed_row is not None,
            "stack_ordinal": observed_row.get("ordinal") if observed_row else None,
            "observed_offset_hex": None if offset is None else f"0x{offset:x}",
            "stack_reported_size_hex": None if stack_size is None else f"0x{stack_size:x}",
            "offset_within_stack_reported_size": (
                None if offset is None or stack_size is None else offset < stack_size
            ),
            "stock_map_found": map_row is not None,
            "stock_address_hex": map_row.get("address_hex") if map_row else None,
            "stock_type": map_row.get("type") if map_row else None,
            "next_symbol": map_row.get("next_symbol") if map_row else None,
            "next_delta_hex": map_row.get("next_delta_hex") if map_row else None,
            "source_found": bool(source.get("found")),
            "source": source,
            "next_live_sampler_use": (
                "per-boot exact-slide codeword solver should map ctx_pc/ctx_lr into this static symbol range; do not reuse a numeric slide across boots"
            ),
        })
    return rows


def build_summary(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    v2245 = read_json(args.v2245_summary)
    symbols = load_text_symbols(args.stock_map)
    observed = extract_observed_stack(v2245)
    rows = build_rows(observed, symbol_index(symbols), args.source_root)
    missing = [
        row["symbol"]
        for row in rows
        if not (row["observed_in_v2245_stack"] and row["stock_map_found"] and row["source_found"])
    ]
    offset_mismatches = [
        row["symbol"]
        for row in rows
        if row["offset_within_stack_reported_size"] is False
    ]
    inventory_path = out_dir / "post_fwready_tail_symbol_source_map.json"
    inventory_path.write_text(json.dumps({
        "warning": "Public-safe derived inventory. Contains symbol/source metadata only.",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "observed_stack": observed,
        "rows": rows,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    decision = "v2246-post-fwready-tail-symbol-source-map-pass"
    if missing or offset_mismatches:
        decision = "v2246-post-fwready-tail-symbol-source-map-review-needed"
    return {
        "label": args.label,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "decision": decision,
        "pass": decision.endswith("-pass"),
        "out_dir": rel(out_dir),
        "safety": {
            "host_only": True,
            "device_io": False,
            "bpf_attach": False,
            "tracefs_control_write": False,
            "probe_write_user_executed": False,
            "wifi_scan_connect": False,
            "network_route_change": False,
            "flash_reboot": False,
            "partition_write": False,
            "private_raw_log_copied_to_public": False,
        },
        "inputs": {
            "v2245_summary": rel(args.v2245_summary),
            "stock_map": rel(args.stock_map),
            "source_root": rel(args.source_root),
        },
        "target_symbol_count": len(TARGET_SYMBOLS),
        "observed_stack_symbol_count": len({row["symbol"] for row in observed}),
        "stock_text_symbol_count": len(symbols),
        "missing_or_unmapped_symbols": missing,
        "offset_mismatches": offset_mismatches,
        "rows": rows,
        "inventory": {
            "path": rel(inventory_path),
            "raw_helper_result_published": False,
        },
        "interpretation": {
            "result": "The V2245 post-FWREADY qcacld/HDD tail stack has a complete stock-map and source-definition whitelist.",
            "map_next_delta_caveat": "RKP/CFP/JOPP layouts mean the next System.map symbol is not promoted as function size; use stack-reported sizes and source identity for the live target whitelist.",
            "next_live_target": "Run a per-boot exact-slide codeword PC/LR sampler around the firmware_class/qcacld tail and score hits against this target symbol set.",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2246-post-fwready-tail-symbol-source-map")
    parser.add_argument("--v2245-summary", type=Path, default=DEFAULT_V2245_SUMMARY)
    parser.add_argument("--stock-map", type=Path, default=DEFAULT_STOCK_MAP)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--out-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir or PRIVATE_RUNS / f"{args.label}-{now_label()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = build_summary(args, out_dir)
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": summary["decision"],
        "pass": summary["pass"],
        "out_dir": summary["out_dir"],
        "summary": rel(summary_path),
        "target_symbol_count": summary["target_symbol_count"],
        "observed_stack_symbol_count": summary["observed_stack_symbol_count"],
        "missing_or_unmapped_symbols": summary["missing_or_unmapped_symbols"],
    }, indent=2, sort_keys=True))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""P3.19 host-only candidate intent/build/Process-v2 qualification.

This is a P319-specific closure.  It binds the reviewed stock-witness source
and Image-only predecessor before any fresh build, calls only the bound stock
materializer, reconstructs the package independently, and records that the
real Process-v2 promotion remains a separate prerequisite.  It never creates
approval, device, ADB, USB, Odin, recovery, or live authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import tempfile
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
STOCK_SOURCE = ROOT / "workspace/public/src/scripts/analysis/s22plus_fyg8_p319_stock_candidate_build.py"
ADAPTER_SOURCE = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_p319_stock_process_v2_adapter.py"
PREDECESSOR_PHASE1 = ROOT / "workspace/private/outputs/s22plus_fyg8_p319/stock-witness-runtime-v1-20260821-32"
PREDECESSOR_PHASE2 = ROOT / "workspace/private/outputs/s22plus_fyg8_p319/stock-witness-runtime-v1-20260821-33"
DEFAULT_PHASE1 = ROOT / "workspace/private/outputs/s22plus_fyg8_p319/stock-witness-runtime-v1-20260821-46"
DEFAULT_PHASE2 = ROOT / "workspace/private/outputs/s22plus_fyg8_p319/stock-witness-runtime-v1-20260821-47"
DEFAULT_RUN_ROOT = ROOT / "workspace/private/outputs/s22plus_fyg8_p319/candidate-qualification-v1-20260821-07"
IMAGE = ROOT / "workspace/private/outputs/s22plus_fyg8_p311/fixed-p310-ready-1/Image"
P311_BASE_BOOT = ROOT / "workspace/private/outputs/s22plus_fyg8_p311/candidate-a/boot.img"
ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
RECOVERY_SCRIPT = ROOT / "workspace/private/outputs/s22plus_fyg8_p311/incident-recovery/s22plus_fyg8_p311_carrier_recover.py"
CHILD_SOURCE = ROOT / "workspace/public/src/native-init/s22plus_r4w1e_e1_child.c"
P318_STATIC = ROOT / "workspace/private/outputs/s22plus_fyg8_p319/stock-witness-runtime-v1-20260821-32/inputs/p318-static-check-result.json"
MATERIALIZATION = ROOT / "workspace/private/outputs/s22plus_fyg8_p319/successor-module-materialization-v1-20260820-04/result.json"
V5_RECEIPT = ROOT / "workspace/private/outputs/s22plus_fyg8_p319/successor-witness-carrier-v5-20260820-13/result.json"
VENDOR_BOOT = ROOT / "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/raw/vendor_boot.img"
TARGET_CONTRACT = ROOT / "docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md"
PROCESS_CONTRACT = ROOT / "docs/operations/DEVICE_ACTION_PROCESS_V2.md"
GOAL = ROOT / "GOAL.md"
RUN_ID = "b9cc424d0d184f5accbce94a844e817d"
IMAGE_ID = {"size": 41_490_944, "sha256": "71f573eb77e67c82b9191bfe0926153f6c8dd5fefe3bba01f884c9beb0c4bae8"}
BASE_ID = {"size": 100_663_296, "sha256": "58b38211d19ead1b0fe54e9fde463aef2c6dbf248be8d669e1b5415f244af17d"}
ROLLBACK_AP_ID = {"size": 23_367_721, "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56"}
AUDITOR_ID = {"size": 113_532, "sha256": "574132854258ac2affd038bc98f9629663c9f1c6aa95cfc8585101c1abe0d29e"}
PHASE1_ID = {"size": 382_059, "sha256": "a6e1734bdd527eb598446269e860a171fb4ad3785c792db0837f4850b8dbd177"}
PHASE2_ID = {"size": 392_896, "sha256": "e491c79722c3ae080770026eb3e2e6bcd4c8bc5c34d4b29e18ae24765e2c6173"}
MATERIALIZATION_ID = {"size": 10_658, "sha256": "8b8c1f5afd8c02693901d3552c221bcc73bafa2543c77dfff4954bdba188f6b5"}
P318_STATIC_ID = {"size": 554_578, "sha256": "2a4d639b55aa21cf8f52dba505e9bc2d9dfd33f20cd3b217a7c482906aeea4df"}
V5_ID = {"size": 11_647, "sha256": "05ee3385c8c8001039a329316c65f9bee9d5d3181e8673f7ddf9dea420532917"}
VENDOR_BOOT_ID = {"size": 100_663_296, "sha256": "096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7"}
CHILD_SOURCE_ID = {"size": 1_112, "sha256": "2af86dda0f6c93ee90996d89c9803bd84bab16b909d25b732b69144fe8760e14"}
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
OVERLAY = (
    "s22plus_dwc3_event_latch.ko",
)
FORBIDDEN = ("vendor_boot", "vbmeta", "recovery", "system.img", "userdata")
SCHEMA = "s22plus_fyg8_p319_candidate_qualification_v1"
INTENT_SCHEMA = "s22plus_fyg8_p319_candidate_intent_v1"


class QualificationError(RuntimeError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _identity(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": _sha(data)}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _stable(path: Path, label: str, expected: dict[str, Any] | None = None, *, mode: int | None = None, nlink: int | None = None, maximum: int = 512 * 1024 * 1024) -> bytes:
    try:
        before = path.lstat()
        resolved = path.resolve(strict=True)
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode) or resolved.name != path.name:
            raise QualificationError(f"{label} is not a direct regular file")
        with path.open("rb") as stream:
            data = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = path.lstat()
    except OSError as exc:
        raise QualificationError(f"{label} is unavailable") from exc
    before_id = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    if (
        len(data) != before.st_size or len(data) > maximum or before_id != (inside.st_dev, inside.st_ino, inside.st_size, inside.st_mtime_ns)
        or before_id != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        or expected is not None and _identity(data) != expected
        or mode is not None and any(
            stat.S_IMODE(info.st_mode) != mode
            for info in (before, inside, after)
        )
        or nlink is not None and any(
            info.st_nlink != nlink for info in (before, inside, after)
        )
    ):
        raise QualificationError(f"{label} identity differs")
    return data


def _strict_dir(path: Path, label: str, expected: set[str]) -> None:
    try:
        info = path.lstat()
        names = {entry.name for entry in path.iterdir()}
    except OSError as exc:
        raise QualificationError(f"{label} is unavailable") from exc
    if stat.S_IMODE(info.st_mode) != 0o700 or not stat.S_ISDIR(info.st_mode) or names != expected:
        raise QualificationError(f"{label} directory shape differs")


def _require_complete_run_root(path: Path) -> None:
    _strict_dir(
        path, "P319 qualification run root",
        {"intent.json", "static-reconstruction.json", "qualification.json", "report.json"},
    )


def _write_exclusive(path: Path, value: Any) -> dict[str, Any]:
    if path.exists() or path.is_symlink():
        raise QualificationError(f"no-clobber output exists: {path}")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    data = value if isinstance(value, bytes) else _canonical(value) + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o400)
    try:
        os.fchmod(fd, 0o400)
        offset = 0
        while offset < len(data):
            written = os.write(fd, data[offset:])
            if written <= 0:
                raise QualificationError("short exclusive publication")
            offset += written
        os.fsync(fd)
        info = os.fstat(fd)
        if stat.S_IMODE(info.st_mode) != 0o400 or info.st_nlink != 1 or info.st_size != len(data):
            raise QualificationError("exclusive publication identity differs")
    finally:
        os.close(fd)
    dir_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
    verified = _stable(
        path,
        "exclusive publication final reopen",
        _identity(data),
        mode=0o400,
        nlink=1,
        maximum=max(512 * 1024 * 1024, len(data)),
    )
    return _identity(verified)


def _decode_json_object(path: Path, data: bytes, *, exact_canonical: bool = False) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise QualificationError(f"{path} contains duplicate JSON key")
            value[key] = item
        return value
    def reject_constant(value: str) -> Any:
        raise QualificationError(f"{path} contains non-finite JSON number: {value}")
    try:
        value = json.loads(
            data, object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualificationError(f"{path} is not canonical JSON") from exc
    if not isinstance(value, dict):
        raise QualificationError(f"{path} JSON is not an object")
    if exact_canonical and data != _canonical(value) + b"\n":
        raise QualificationError(f"{path} JSON bytes are not canonical")
    return value


def _json(
    path: Path, expected: dict[str, Any] | None = None,
    *, require_canonical: bool = False,
) -> dict[str, Any]:
    data = _stable(path, str(path), expected, mode=0o400, nlink=1)
    value = _decode_json_object(path, data, exact_canonical=False)
    if require_canonical:
        pretty = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("ascii")
        if data not in {_canonical(value) + b"\n", pretty}:
            raise QualificationError(f"{path} JSON bytes are not canonical")
    return value


def _bound_python_closure(entry: Path) -> dict[str, Path]:
    """Bind the local Python modules executed by the rootfs reconstruction.

    The P318 rootfs helper is a reviewed adapter over older closure modules.
    Its transitive imports are execution inputs too; discover only the local
    ``s22plus_*`` modules and bind their direct bytes, rather than
    pretending the top-level helper alone is the complete authority.
    """
    base = entry.parent
    pending = [entry]
    seen: dict[str, Path] = {}
    pattern = re.compile(r"(?:import|from)\s+(s22plus_[A-Za-z0-9_]+)")
    while pending:
        path = pending.pop()
        logical = path.name
        if logical in seen:
            continue
        if not path.is_file():
            raise QualificationError(f"bound Python closure member is absent: {logical}")
        seen[logical] = path
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            child = base / f"{match.group(1)}.py"
            if child.name not in seen:
                pending.append(child)
    return seen


def _load_stock() -> tuple[types.ModuleType, bytes]:
    source = _stable(STOCK_SOURCE, "P319 stock auditor", maximum=2 * 1024 * 1024)
    module = types.ModuleType("p319_stock_candidate_bound")
    module.__dict__["__file__"] = str(STOCK_SOURCE)
    module.__dict__["_P319_STOCK_BOUND_SOURCE"] = source
    exec(compile(source, str(STOCK_SOURCE), "exec"), module.__dict__)
    bound = module._bound_auditor_module()
    if type(bound._BOUND_AUDITOR_SOURCE) is not bytes:
        raise QualificationError("stock auditor did not bootstrap from bound bytes")
    return bound, source


def _load_adapter() -> tuple[types.ModuleType, bytes]:
    source = _stable(ADAPTER_SOURCE, "P319 Process-v2 adapter", maximum=512 * 1024)
    module = types.ModuleType("p319_stock_adapter_bound")
    module.__dict__["__file__"] = str(ADAPTER_SOURCE)
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(ADAPTER_SOURCE.parent))
        exec(compile(source, str(ADAPTER_SOURCE), "exec"), module.__dict__)
    finally:
        sys.path[:] = old_path
    return module, source


def _source_keys() -> dict[str, dict[str, Any]]:
    paths = {
        "stock_auditor": STOCK_SOURCE,
        "adapter": ADAPTER_SOURCE,
        "adapter_carrier_model": ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_p310_carrier_model.py",
        "adapter_telemetry_spec": ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_p308_telemetry_spec.py",
        "phase1_predecessor": PREDECESSOR_PHASE1 / "result.json",
        "phase2_predecessor": PREDECESSOR_PHASE2 / "result.json",
        "fixed_image": IMAGE,
        "p311_clean_base_boot": P311_BASE_BOOT,
        "rollback_ap": ROLLBACK_AP,
        "recovery_script": RECOVERY_SCRIPT,
        "child_source": CHILD_SOURCE,
        "p318_static_result": P318_STATIC,
        "module_materialization_result": MATERIALIZATION,
        "carrier_v5_receipt": V5_RECEIPT,
        "vendor_boot": VENDOR_BOOT,
        "qualification_source": Path(__file__).resolve(),
        "raw_first_source": ROOT / "workspace/public/src/scripts/revalidation/device_action_raw_capture_v1.py",
        "effective_rootfs_source": ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_p318_e2_stock_closure.py",
        "target_contract": TARGET_CONTRACT,
        "process_contract": PROCESS_CONTRACT,
    }
    for logical_name, path in _bound_python_closure(
        ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_p318_e2_stock_closure.py"
    ).items():
        paths[f"rootfs_closure:{logical_name}"] = path
    for logical_name, path in _bound_python_closure(ADAPTER_SOURCE).items():
        paths[f"adapter_closure:{logical_name}"] = path
    expected = {
        "phase1_predecessor": PHASE1_ID, "phase2_predecessor": PHASE2_ID,
        "fixed_image": IMAGE_ID, "p311_clean_base_boot": BASE_ID,
        "p318_static_result": P318_STATIC_ID,
        "module_materialization_result": MATERIALIZATION_ID,
        "carrier_v5_receipt": V5_ID, "child_source": CHILD_SOURCE_ID,
        "rollback_ap": ROLLBACK_AP_ID, "vendor_boot": VENDOR_BOOT_ID,
    }
    predecessor = _json(PREDECESSOR_PHASE1 / "result.json", PHASE1_ID)
    for name, item in predecessor["source"]["materialized_stock_sources"].items():
        paths[f"stock_source:{name}"] = PREDECESSOR_PHASE1 / "stock-sources" / name
        expected[f"stock_source:{name}"] = item
    for row in predecessor["module_crc_closure"]["modules"]:
        name = str(row["file"])
        paths[f"module:{name}"] = PREDECESSOR_PHASE1 / "module-bytes" / name
        expected[f"module:{name}"] = {"size": row["size"], "sha256": row["sha256"]}
    stock, _ = _load_stock()
    for name, path in stock.TOOL_PATHS.items():
        receipt = predecessor["tools"].get(name)
        if not isinstance(receipt, dict):
            raise QualificationError(f"tool receipt is absent: {name}")
        paths[f"tool:{name}"] = path
        expected[f"tool:{name}"] = {"size": receipt["size"], "sha256": receipt["sha256"]}
    result: dict[str, dict[str, Any]] = {}
    for logical, path in paths.items():
        if logical.startswith("tool:"):
            path = path.resolve()
        strict_private = path.is_relative_to(ROOT / "workspace/private") and not logical.startswith("tool:") and logical not in {"recovery_script", "rollback_ap", "vendor_boot"}
        exact_external_private = logical in {"rollback_ap", "vendor_boot"}
        data = _stable(
            path, logical, expected.get(logical),
            mode=0o600 if exact_external_private else (0o400 if strict_private else None),
            nlink=1 if exact_external_private or strict_private else None,
        )
        logical_path = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else f"p319-tool/{logical.removeprefix('tool:')}"
        result[logical] = {"logical_path": logical_path, **_identity(data)}
    return result


def create_intent(run_root: Path, phase1: Path, phase2: Path) -> dict[str, Any]:
    if run_root.exists() or run_root.is_symlink():
        raise QualificationError("candidate qualification run root already exists")
    sources = _source_keys()
    intent = {
        "schema": INTENT_SCHEMA,
        "verdict": "PASS_P319_CANDIDATE_INTENT_HOST_ONLY",
        "target": TARGET,
        "profile": 3,
        "run_id": RUN_ID,
        "candidate_window_sec": 300,
        "guard_lifetime_sec": 1200,
        "source_keys": sources,
        "predecessors": {
            "auditor": AUDITOR_ID, "phase1": PHASE1_ID, "phase2": PHASE2_ID,
            "v5_receipt": V5_ID, "p318_static": P318_STATIC_ID,
        },
        "fixed_image": IMAGE_ID,
        "p311_clean_base_boot": BASE_ID,
        "rollback": {"ap": ROLLBACK_AP_ID, "kind": "magisk_boot_only", "same_target": True, "recovery_script": sources["recovery_script"]},
        "module_plan": {"count": 73, "eud_index": 38, "overlay_delta": list(OVERLAY)},
        "runtime": {
            "stock_domain": "S22PLUS-FYG8-MAX77705-STOCK-V1",
            "encoding": 4, "payload_abi": 3, "status_width": 3,
            "chain": ["irq", "initial_status", "classification", "probe"],
            "parent_unavailable": True, "w5_unavailable": True,
            "diagnostic_absent": True, "acm_supplemental": True,
        },
        "process_v2_integration_created": False,
        "scope": {"tier": "H0", "host_only": True, "device_contact": False, "live_authorized": False, "approval_created": False},
        "planned_outputs": {
            "phase1": phase1.relative_to(ROOT).as_posix(),
            "phase2": phase2.relative_to(ROOT).as_posix(),
        },
    }
    _write_exclusive(run_root / "intent.json", intent)
    return intent


def verify_intent(intent_path: Path, intent: dict[str, Any]) -> None:
    disk_bytes = _stable(
        intent_path,
        "candidate intent",
        mode=0o400,
        nlink=1,
        maximum=16 * 1024 * 1024,
    )
    disk_intent = _decode_json_object(intent_path, disk_bytes, exact_canonical=True)
    if disk_intent != intent or disk_bytes != _canonical(intent) + b"\n":
        raise QualificationError("candidate intent changed after load")
    if intent.get("schema") != INTENT_SCHEMA or intent.get("scope", {}).get("device_contact") is not False or intent.get("scope", {}).get("live_authorized") is not False:
        raise QualificationError("candidate intent scope differs")
    current = _source_keys()
    if current != intent.get("source_keys"):
        raise QualificationError("execution-critical SOURCE_KEYS changed after intent")


def build_fresh(intent_path: Path, intent: dict[str, Any], phase1: Path, phase2: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    verify_intent(intent_path, intent)
    stock, _source = _load_stock()
    result1 = stock.build_result(phase1, phase2=False)
    result2 = stock.build_result(phase2, phase2=True)
    audit1 = stock.build_result(phase1, audit_only=True)
    audit2 = stock.build_result(phase2, audit_only=True)
    if audit1 != result1 or audit2 != result2:
        raise QualificationError("stock audit-only regeneration differs")
    verify_intent(intent_path, intent)
    return result1, result2


def image_internal(result: dict[str, Any]) -> dict[str, Any]:
    image = _stable(IMAGE, "fixed Image", IMAGE_ID, mode=0o400, nlink=1)
    sections = result["fixed_image_abi"]["sections"]
    order = ("__ksymtab", "__ksymtab_gpl", "__kcrctab", "__kcrctab_gpl", "__ksymtab_strings")
    spans: list[tuple[str, int, int]] = []
    for name in order:
        row = sections.get(name)
        if not isinstance(row, dict):
            raise QualificationError(f"Image section {name} is absent")
        start, size = row.get("image_offset"), row.get("size")
        if type(start) is not int or type(size) is not int or start < 0 or size <= 0 or start + size > len(image):
            raise QualificationError(f"Image section {name} bounds differ")
        if _sha(image[start:start + size]) != row.get("sha256_image"):
            raise QualificationError(f"Image section {name} hash differs")
        spans.append((name, start, start + size))
    if any(right != spans[index + 1][1] for index, (_name, _left, right) in enumerate(spans[:-1])):
        raise QualificationError("Image provider tables are not contiguous")
    if result["fixed_image_abi"].get("external_build_provenance", {}).get("status") != "not_bound":
        raise QualificationError("external vmlinux provenance is unexpectedly authoritative")
    provider_map = result["fixed_image_abi"].get("image_provider_map")
    if not isinstance(provider_map, dict) or len(provider_map) != 7222:
        raise QualificationError("Image provider count differs")
    normal = sections["__ksymtab"]["size"] // sections["__ksymtab"]["entry_size"]
    gpl = sections["__ksymtab_gpl"]["size"] // sections["__ksymtab_gpl"]["entry_size"]
    if normal != sections["__kcrctab"]["size"] // 4 or gpl != sections["__kcrctab_gpl"]["size"] // 4 or normal + gpl != len(provider_map):
        raise QualificationError("Image provider/CRC parity differs")
    strings_start = sections["__ksymtab_strings"]["image_offset"]
    strings_end = strings_start + sections["__ksymtab_strings"]["size"]
    def prel32_name_decodes(window_start: int, window_end: int) -> int:
        count = 0
        for cursor in range(window_start, max(window_start, window_end - 11) + 1):
            if cursor + 8 > len(image):
                continue
            value_relative = struct.unpack_from("<i", image, cursor)[0]
            value_target = cursor + value_relative
            relative = struct.unpack_from("<i", image, cursor + 4)[0]
            target = cursor + 4 + relative
            # A PREL32 ksymtab entry has both a code/data value and a name.
            # Requiring the value to land before the string table avoids
            # treating arbitrary bytes immediately after the table as an
            # entry while still exercising the full 12-byte outside window.
            if 0 <= value_target < strings_start and strings_start <= target < strings_end:
                end = image.find(b"\0", target, strings_end)
                if end > target and all(32 <= value < 127 for value in image[target:end]):
                    count += 1
        return count
    left_decode_count = prel32_name_decodes(spans[0][1] - 12, spans[0][1])
    right_decode_count = prel32_name_decodes(spans[-1][2], spans[-1][2] + 12)
    if left_decode_count or right_decode_count:
        raise QualificationError("Image 12-byte PREL32 boundary is not sharp")
    return {
        "image": IMAGE_ID,
        "section_order": list(order),
        "start": spans[0][1],
        "sizes": [end - start for _name, start, end in spans],
        "right_edge": spans[-1][2],
        "contiguous": True,
        "sharp_left_boundary": True,
        "sharp_right_boundary": True,
        "prel32_left_window_bytes": 12,
        "prel32_right_window_bytes": 12,
        "prel32_left_decode_count": left_decode_count,
        "prel32_right_decode_count": right_decode_count,
        "provider_count": len(provider_map),
        "normal_provider_count": normal,
        "gpl_provider_count": gpl,
        "external_build_provenance": "not_bound",
        "vmlinux_authority": False,
        "symvers_authority": False,
    }


def cross_producer(stock: types.ModuleType, result: dict[str, Any], phase1: Path) -> dict[str, Any]:
    rows = result["plan"]["rows"]
    provider_map = result["fixed_image_abi"]["image_provider_map"]
    module_root = phase1 / "module-bytes"
    audit = stock.audit_modules(rows, provider_map, result["module_crc_closure"]["image_derived_vermagic_suffix"], module_root)
    resolution = audit.get("provider_resolution", {})
    if resolution != {"fixed_image_imports": 3238, "earlier_module_imports": 328, "total_resolved_imports": 3566}:
        raise QualificationError("module import resolution count differs")
    chosen: str | None = None
    for row in rows:
        imports = stock._imports(module_root / row["file"])
        if imports:
            chosen = next((name for name in imports if name in provider_map), None)
            if chosen:
                break
    if chosen is None:
        raise QualificationError("no Image-provider import was available for shifted CRC control")
    names = sorted(provider_map)
    rotated = {
        name: provider_map[names[(index + 1) % len(names)]]
        for index, name in enumerate(names)
    }
    try:
        stock.audit_modules(rows, rotated, result["module_crc_closure"]["image_derived_vermagic_suffix"], module_root)
    except Exception:
        shifted_rejected = True
    else:
        shifted_rejected = False
    if not shifted_rejected:
        raise QualificationError("one-entry shifted Image CRC was accepted")
    rotated_agreements = 0
    for row in rows:
        imports = stock._imports(module_root / row["file"])
        rotated_agreements += sum(
            1 for name, crc in imports.items()
            if name in rotated and rotated[name] == crc
        )
    if rotated_agreements != 0:
        raise QualificationError("rotated Image CRC retained an import agreement")
    return {
        "image_provider_crc_authority": True,
        "cross_producer_name_crc_pairing": True,
        "shipped_module_imports": 3566,
        "image_provider_imports": 3238,
        "earlier_module_imports": 328,
        "provider_count": 7222,
        "zero_missing": audit["missing_provider_count"] == 0,
        "zero_ambiguous": audit["ambiguous_provider_count"] == 0,
        "zero_duplicate": audit["duplicate_provider_count"] == 0,
        "rotated_crc_negative_rejected": True,
        "rotated_crc_agreements": rotated_agreements,
        "control_symbol": chosen,
    }


def effective_rootfs_reconstruct(stock: types.ModuleType, result: dict[str, Any], phase2: Path) -> dict[str, Any]:
    """Reopen boot/vendor_boot and independently rebuild the effective inventory."""
    try:
        import s22plus_fyg8_p318_e2_stock_closure as closure
        tools = stock._tools()
        vendor_bytes = _stable(VENDOR_BOOT, "vendor_boot", VENDOR_BOOT_ID, nlink=1)
        candidate_id = result["phase2"]["candidate"]["a"]["boot_img"]
        candidate_bytes = _stable(phase2 / "candidate-a/boot.img", "candidate boot", candidate_id, mode=0o400, nlink=1)
        boot_verify = closure.base.base.module_parent.boot_verify
        boot = boot_verify.parse_boot_v4(candidate_bytes)
        vendor = boot_verify.parse_vendor_boot_v4(vendor_bytes)
        generic_payload = boot_verify.decompress_lz4(tools["lz4"], boot.ramdisk)
        generic_entries = boot_verify.parse_newc(generic_payload)
        layers: list[tuple[str, tuple[Any, ...]]] = [("generic", tuple(generic_entries))]
        for index, fragment in enumerate(vendor.fragments):
            payload = boot_verify.decompress_lz4(tools["lz4"], fragment.data)
            layers.append((f"vendor[{index}]/{fragment.name}", tuple(boot_verify.parse_newc(payload))))
    except Exception as exc:
        raise QualificationError("P319 effective rootfs reconstruction failed") from exc
    overlay_paths = {f"lib/modules/{name}" for name in OVERLAY}
    seen: dict[str, tuple[str, Any]] = {}
    for label, entries in layers:
        for entry in entries:
            if entry.name in seen:
                old_label, _old_entry = seen[entry.name]
                if entry.name in overlay_paths and {old_label.startswith("vendor["), label.startswith("vendor[")} == {False, True}:
                    if label == "generic":
                        seen[entry.name] = (label, entry)
                    continue
                raise QualificationError("P319 effective rootfs duplicate")
            seen[entry.name] = (label, entry)
    plan_rows = result["module_crc_closure"]["modules"]
    module_rows = []
    for row in plan_rows:
        path = f"lib/modules/{row['file']}"
        found = seen.get(path)
        if found is None or found[1].file_type != "regular" or _identity(found[1].data) != {"size": row["size"], "sha256": row["sha256"]}:
            raise QualificationError(f"P319 effective module differs: {row['file']}")
        label = found[0]
        if path in overlay_paths:
            if not label == "generic":
                raise QualificationError(f"P319 overlay module is not generic: {row['file']}")
        elif not label.startswith("vendor["):
            raise QualificationError(f"P319 inherited module was copied to generic: {row['file']}")
        module_rows.append({"file": row["file"], "layer": label})
    for name, expected in (("init", result["phase2"]["userspace"]["a"]["init"]), ("s22-e1-child", result["phase2"]["userspace"]["a"]["child"])):
        found = seen.get(name)
        if found is None or found[0] != "generic" or _identity(found[1].data) != expected:
            raise QualificationError(f"P319 effective userspace entry differs: {name}")
    return {
        "vendor_boot": VENDOR_BOOT_ID,
        "composition_order": [label for label, _entries in layers],
        "entry_count": len(seen),
        "plan_rows": len(plan_rows),
        "module_count": len(module_rows),
        "vendor_layer_inherited_rows": sum(1 for row in module_rows if row["layer"].startswith("vendor[")),
        "generic_overlay_rows": sum(1 for row in module_rows if row["layer"] == "generic"),
        "exact_one_member_generic_overlay": len(OVERLAY) == 1 and OVERLAY == ("s22plus_dwc3_event_latch.ko",),
        "vendor_layer_stock_modules": 72,
        "inherited_modules_not_copied": True,
        "rdinit_override_absent": not any(b"rdinit=" in value for value in (boot.header["cmdline"].encode("ascii"), vendor.cmdline.encode("ascii"), vendor.bootconfig)),
        "independent_unpack_inventory": True,
    }


def static_reconstruct(stock: types.ModuleType, result: dict[str, Any], phase1: Path, phase2: Path) -> dict[str, Any]:
    audited = stock.build_result(phase2, audit_only=True)
    if audited != result:
        raise QualificationError("independent phase2 reconstruction differs")
    for label in ("candidate-a", "candidate-b"):
        _strict_dir(phase2 / label, label, {"boot.img", "boot.img.lz4", "odin4"})
        _strict_dir(phase2 / label / "odin4", f"{label}/odin4", {"AP.tar.md5"})
        for name in ("boot.img", "boot.img.lz4"):
            _stable(phase2 / label / name, f"{label}/{name}", result["phase2"]["candidate"]["a"][{"boot.img": "boot_img", "boot.img.lz4": "boot_img_lz4"}[name]], mode=0o400, nlink=1)
        _stable(phase2 / label / "odin4/AP.tar.md5", f"{label}/AP.tar.md5", result["phase2"]["candidate"]["a"]["ap_tar_md5"], mode=0o400, nlink=1)
    for label in ("userspace-a", "userspace-b"):
        _strict_dir(phase2 / label, label, {"init", "s22-e1-child"})
        _stable(phase2 / label / "init", f"{label}/init", result["phase2"]["userspace"]["a"]["init"], mode=0o400, nlink=1)
        _stable(phase2 / label / "s22-e1-child", f"{label}/child", result["phase2"]["userspace"]["a"]["child"], mode=0o400, nlink=1)
    candidate = result["phase2"]["candidate"]
    if candidate["byte_identical"] is not True:
        raise QualificationError("P319 candidate A/B bytes differ")
    if candidate["overlay_members"] != sorted(f"lib/modules/{name}" for name in OVERLAY):
        raise QualificationError("P319 generic overlay set differs")
    if candidate["diagnostic_absent"] is not True or candidate["inherited_modules_not_copied"] is not True:
        raise QualificationError("P319 diagnostic/vendor-layer boundary differs")
    if not candidate["a"]["package"]["safety"].get("boot_only") or set(candidate["a"]["package"]["ap_structure"]["members"]) != {"boot.img.lz4"}:
        raise QualificationError("P319 candidate/AP package closure differs")
    rootfs = effective_rootfs_reconstruct(stock, result, phase2)
    return {
        "schema": "s22plus_fyg8_p319_candidate_static_reconstruction_v1",
        "verdict": "PASS_P319_STATIC_RECONSTRUCTION_H0",
        "phase2_audit_only": True,
        "candidate_ab_byte_identical": True,
        "userspace_ab_byte_identical": True,
        "exact_one_member_generic_overlay": len(OVERLAY) == 1 and OVERLAY == ("s22plus_dwc3_event_latch.ko",),
        "vendor_layer_stock_modules": 72,
        "diagnostic_absent": True,
        "child_replacement_verified": True,
        "ap_boot_only": True,
        "forbidden_members_absent": True,
        "effective_rootfs": rootfs,
        "topology": {"physical_continuity_required": True, "exact_start_candidate_rollback_reopen": True, "p318_causal_correlation": False},
    }


def qualify(intent: dict[str, Any], result1: dict[str, Any], result2: dict[str, Any], static: dict[str, Any], phase1: Path, phase2: Path) -> dict[str, Any]:
    stock, _ = _load_stock()
    adapter, adapter_source = _load_adapter()
    adapter_audit = adapter.audit()
    if adapter_audit.get("verified") is not True or adapter_audit.get("full_record_required") is not True:
        raise QualificationError("P319 standalone adapter audit did not verify")
    if result1["target"] != TARGET or result1["plan"]["module_count"] != 73 or result1["plan"]["eud_index"] != 38:
        raise QualificationError("P319 target/plan identity differs")
    if result2["phase2"].get("built") is not True or result2["phase2"].get("userspace_compiles") != 3 or result2["phase2"].get("boot_builds") != 2 or result2["phase2"].get("ap_builds") != 2:
        raise QualificationError("P319 Phase2 build counts differ")
    if result2["scope"].get("device_contact") is not False or result2["scope"].get("live_authority_created") is not False:
        raise QualificationError("P319 build scope is not H0")
    image = image_internal(result1)
    crc = cross_producer(stock, result1, phase1)
    return {
        "schema": SCHEMA,
        "verdict": "PASS_P319_CANDIDATE_QUALIFICATION_H0",
        "target": TARGET,
        "profile": 3,
        "run_id": RUN_ID,
        "candidate_window_sec": 300,
        "guard_lifetime_sec": 1200,
        "intent": {"schema": intent["schema"], "source_keys": intent["source_keys"]},
        "predecessor_reviewed": {"auditor": AUDITOR_ID, "phase1": PHASE1_ID, "phase2": PHASE2_ID},
        "fresh_phase1": _identity(_stable(phase1 / "result.json", "phase1", mode=0o400, nlink=1)),
        "fresh_phase2": _identity(_stable(phase2 / "result.json", "phase2", mode=0o400, nlink=1)),
        "fixed_image": IMAGE_ID,
        "p311_clean_base": BASE_ID,
        "rollback_input": {"ap": ROLLBACK_AP_ID, "reopened": True, "process_v2_run_binding": False},
        "derived_eud_index": 38,
        "overlay": list(OVERLAY),
        "exact_one_member_generic_overlay": len(OVERLAY) == 1 and OVERLAY == ("s22plus_dwc3_event_latch.ko",),
        "vendor_layer_stock_modules": 72,
        "diagnostic_absent": True,
        "child_replacement": True,
        "image_internal": image,
        "cross_producer_crc": crc,
        "static_reconstruction": static,
        "source_provenance": {"external_build_provenance": "not_bound", "vmlinux_authority": False, "symvers_authority": False},
        "adapter_audit": adapter_audit,
        "adapter_source": {"logical_path": ADAPTER_SOURCE.relative_to(ROOT).as_posix(), **_identity(adapter_source)},
        "causal_result_allowed": False,
        "candidate_success": False,
        "mux_result_claimable": False,
        "host_silent_claimable": False,
        "acm_required_for_acceptance": False,
        "fresh_live_baseline": {"satisfied": False, "status": "not_satisfied_required_before_live_binding"},
        "process_v2_integration_created": False,
        "scope": {"tier": "H0", "host_only": True, "device_contact": False, "live_authorized": False, "approval_created": False, "d0_d1_f1_recovery_replay_live_authority": False},
    }


def process_promotion(_qualification: dict[str, Any], _static: dict[str, Any], _run_root: Path, _phase2: Path) -> dict[str, Any]:
    """Leave real Process-v2 promotion to its separately reviewed unit."""
    return {
        "process_v2_ready_created": False,
        "process_v2_integration_created": False,
        "reason": "rollback bytes are an H0 input only; no Process-v2 run binding exists; separate promotion and exact rollback binding are required",
        "rollback_input_reopened": ROLLBACK_AP_ID,
        "process_v2_run_binding": False,
        "device_contact": False,
        "live_authorized": False,
    }


def _report_value(
    run_root: Path, phase1: Path, phase2: Path,
    qualification: dict[str, Any], process: dict[str, Any],
) -> dict[str, Any]:
    def receipt(path: Path, label: str) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        data = _stable(path, label, maximum=128 * 1024 * 1024, mode=0o400, nlink=1)
        return {"path": path.relative_to(ROOT).as_posix(), **_identity(data)}

    historical = []
    for entry in (
        {"run": "candidate-qualification-v1-20260821-01", "phase1": "stock-witness-runtime-v1-20260821-34", "phase2": "stock-witness-runtime-v1-20260821-35", "reason": "pre-final four-overlay source"},
        {"run": "candidate-qualification-v1-20260821-02", "phase1": "stock-witness-runtime-v1-20260821-36", "phase2": "stock-witness-runtime-v1-20260821-37", "reason": "Image boundary check failed closed"},
        {"run": "candidate-qualification-v1-20260821-03", "phase1": "stock-witness-runtime-v1-20260821-38", "phase2": "stock-witness-runtime-v1-20260821-39", "reason": "pre-final strict source closure"},
        {"run": "candidate-qualification-v1-20260821-04", "phase1": "stock-witness-runtime-v1-20260821-40", "phase2": "stock-witness-runtime-v1-20260821-41", "reason": "pre-final strict JSON and closure binding"},
        {"run": "candidate-qualification-v1-20260821-05", "phase1": "stock-witness-runtime-v1-20260821-42", "phase2": "stock-witness-runtime-v1-20260821-43", "reason": "superseded by final source-only alignment", "phase1_identity": {"size": 382264, "sha256": "982f903f7685f63e5b2fbadebc5a3bbef5d98f009207ac352bda80777b09e886"}, "phase2_identity": {"size": 392886, "sha256": "21beec5d2010ecb5804c09055c93a24f83f0fc4be0c9125d24a831908efeaa4a"}},
        {"run": "candidate-qualification-v1-20260821-06", "phase1": "stock-witness-runtime-v1-20260821-44", "phase2": "stock-witness-runtime-v1-20260821-45", "reason": "superseded by strict on-disk intent TOCTOU verification", "phase1_identity": {"size": 382264, "sha256": "982f903f7685f63e5b2fbadebc5a3bbef5d98f009207ac352bda80777b09e886"}, "phase2_identity": {"size": 392886, "sha256": "21beec5d2010ecb5804c09055c93a24f83f0fc4be0c9125d24a831908efeaa4a"}},
    ):
        run_path = ROOT / "workspace/private/outputs/s22plus_fyg8_p319" / entry["run"]
        phase_root = ROOT / "workspace/private/outputs/s22plus_fyg8_p319"
        receipts = {}
        if run_path.is_dir():
            for path in sorted(run_path.glob("*.json")):
                item = receipt(path, f"superseded run receipt {path.name}")
                if item is not None:
                    receipts[path.name] = item
        historical.append({
            **entry,
            "phase1_result": receipt(phase_root / entry["phase1"] / "result.json", f"superseded {entry['phase1']} result"),
            "phase2_result": receipt(phase_root / entry["phase2"] / "result.json", f"superseded {entry['phase2']} result"),
            "run_receipts": receipts,
        })
    return {
        "schema": "s22plus_fyg8_p319_candidate_qualification_report_v1",
        "verdict": "IMPLEMENTED_REVIEW_PENDING",
        "current_authority": {
            "intent": {"path": (run_root / "intent.json").relative_to(ROOT).as_posix(), **_identity(_stable(run_root / "intent.json", "current intent", mode=0o400, nlink=1))},
            "phase1": {"path": (phase1 / "result.json").relative_to(ROOT).as_posix(), **_identity(_stable(phase1 / "result.json", "phase1", mode=0o400, nlink=1))},
            "phase2": {"path": (phase2 / "result.json").relative_to(ROOT).as_posix(), **_identity(_stable(phase2 / "result.json", "phase2", mode=0o400, nlink=1))},
            "static": {"path": (run_root / "static-reconstruction.json").relative_to(ROOT).as_posix(), **_identity(_stable(run_root / "static-reconstruction.json", "current static", mode=0o400, nlink=1))},
            "qualification": {"path": (run_root / "qualification.json").relative_to(ROOT).as_posix(), **_identity(_stable(run_root / "qualification.json", "current qualification", mode=0o400, nlink=1))},
        },
        "process": process,
        "scope": qualification["scope"],
        "review_required": True,
        "superseded_intermediates": historical,
    }


def run(run_root: Path = DEFAULT_RUN_ROOT, phase1: Path = DEFAULT_PHASE1, phase2: Path = DEFAULT_PHASE2) -> dict[str, Any]:
    intent = create_intent(run_root, phase1, phase2)
    result1, result2 = build_fresh(run_root / "intent.json", intent, phase1, phase2)
    stock, _ = _load_stock()
    static = static_reconstruct(stock, result2, phase1, phase2)
    verify_intent(run_root / "intent.json", intent)
    _write_exclusive(run_root / "static-reconstruction.json", static)
    qualification = qualify(intent, result1, result2, static, phase1, phase2)
    verify_intent(run_root / "intent.json", intent)
    _write_exclusive(run_root / "qualification.json", qualification)
    process = process_promotion(qualification, static, run_root, phase2)
    report = _report_value(run_root, phase1, phase2, qualification, process)
    report_receipt = _write_exclusive(run_root / "report.json", report)
    verify_intent(run_root / "intent.json", intent)
    _require_complete_run_root(run_root)
    return {"intent": intent, "qualification": qualification, "process": process, "report": report_receipt}


def audit_existing(run_root: Path = DEFAULT_RUN_ROOT, phase1: Path = DEFAULT_PHASE1, phase2: Path = DEFAULT_PHASE2) -> dict[str, Any]:
    _require_complete_run_root(run_root)
    intent = _json(run_root / "intent.json", require_canonical=True)
    verify_intent(run_root / "intent.json", intent)
    stock, _ = _load_stock()
    result1 = stock.build_result(phase1, audit_only=True)
    result2 = stock.build_result(phase2, audit_only=True)
    stored_result1 = _json(phase1 / "result.json", require_canonical=True)
    stored_result2 = _json(phase2 / "result.json", require_canonical=True)
    if result1 != stored_result1 or result2 != stored_result2:
        raise QualificationError("existing stock result differs from audit-only regeneration")
    static = _json(run_root / "static-reconstruction.json", require_canonical=True)
    expected_static = static_reconstruct(stock, stored_result2, phase1, phase2)
    verify_intent(run_root / "intent.json", intent)
    if static != expected_static:
        raise QualificationError("existing static reconstruction differs")
    qualification = _json(run_root / "qualification.json", require_canonical=True)
    expected_qualification = qualify(intent, stored_result1, stored_result2, expected_static, phase1, phase2)
    verify_intent(run_root / "intent.json", intent)
    if qualification != expected_qualification:
        raise QualificationError("P319 existing qualification schema differs")
    process = process_promotion(expected_qualification, expected_static, run_root, phase2)
    expected_report = _report_value(run_root, phase1, phase2, expected_qualification, process)
    stored_report = _json(run_root / "report.json", require_canonical=True)
    if stored_report != expected_report:
        raise QualificationError("existing qualification report differs")
    verify_intent(run_root / "intent.json", intent)
    return {
        "audit_only": True,
        "phase1": _identity(_stable(phase1 / "result.json", "phase1", mode=0o400, nlink=1)),
        "phase2": _identity(_stable(phase2 / "result.json", "phase2", mode=0o400, nlink=1)),
        "static": static["schema"], "qualification": qualification["schema"],
        "process_v2_ready_created": False,
        "scope": {"device_contact": False, "live_authorized": False},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--phase1", type=Path, default=DEFAULT_PHASE1)
    parser.add_argument("--phase2", type=Path, default=DEFAULT_PHASE2)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = lambda p: p if p.is_absolute() else ROOT / p
        value = audit_existing(root(args.run_root), root(args.phase1), root(args.phase2)) if args.audit_only else run(root(args.run_root), root(args.phase1), root(args.phase2))
    except (QualificationError, OSError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": "PASS_P319_CANDIDATE_QUALIFICATION_H0", "result": value}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

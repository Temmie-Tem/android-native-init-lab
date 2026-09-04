#!/usr/bin/env python3
"""Build the host-only P3.40 identity-only boot/AP successor.

The P3.39 -04 result and source closure are reopened by exact identity.  The
P3.40 delta is limited to one same-length Image identity transform, the fixed
runtime command marker, and the compiler-bound ``/init`` run ID.  Packaging is
delegated to the existing pinned P3.19 helper; no device, ADB, Odin, or live
authority operation is performed.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import os
import stat
import subprocess
import sys
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = Path(__file__).resolve().parent
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for _directory in (ANALYSIS, REVALIDATION):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import s22plus_fyg8_p340_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p340_open_read_branch_runtime as runtime  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P339_OUTPUT = ROOT / "workspace/private/outputs/s22plus_fyg8_p339/stock-candidate-build-v1-20260905-04"
P339_RESULT = P339_OUTPUT / "result.json"
P339_RESULT_IDENTITY = {"size": 64_362, "sha256": "990f94cff5e28bc8360ede119eaa962a19dd1e75647489b9d1580dcf7f2bd338"}
P339_BUILDER_SOURCE = ANALYSIS / "s22plus_fyg8_p339_stock_candidate_build.py"
P339_BUILDER_IDENTITY = {"size": 30_794, "sha256": "eeee7703592ce35b370a32a2d11e5f9288073af30e8a048259507be2c5257dc1"}
P319_PACKAGER_SOURCE = ANALYSIS / "s22plus_fyg8_p319_stock_candidate_build.py"
P319_PACKAGER_IDENTITY = {"size": 114_260, "sha256": "544b03e02ce5490bb2db03a4bbdbbda806ea2bb354026162efc54b0173610058"}
P339_ARTIFACT_SOURCE = REVALIDATION / "s22plus_fyg8_p339_artifact_identity.py"
P339_RUNTIME_SOURCE = REVALIDATION / "s22plus_fyg8_p339_open_read_branch_runtime.py"
P339_OBSERVER_SOURCE = REVALIDATION / "s22plus_fyg8_p339_open_read_branch_acm_observer.py"
P340_ARTIFACT_SOURCE = REVALIDATION / "s22plus_fyg8_p340_artifact_identity.py"
P340_RUNTIME_SOURCE = REVALIDATION / "s22plus_fyg8_p340_open_read_branch_runtime.py"
P340_OBSERVER_SOURCE = REVALIDATION / "s22plus_fyg8_p340_open_read_branch_acm_observer.py"
P340_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p340_stock_process_v2_adapter.py"
ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
ROLLBACK_IDENTITY = {"size": 23_367_721, "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56"}
DEFAULT_OUTPUT_ROOT = ROOT / "workspace/private/outputs/s22plus_fyg8_p340/stock-candidate-build-v1-20260905-01"
SCHEMA = "s22plus-fyg8-p340-stock-candidate-build-v1"
VERDICT = "PASS_P340_STOCK_CANDIDATE_BUILD_H0_IDENTITY_ONLY"
STATUS = "IMPLEMENTED_H0_IDENTITY_ONLY_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
P339_RUN_ID_HEX = artifact.P339_PREDECESSOR_RUN_ID_HEX
P339_RUN_ID = artifact.P339_PREDECESSOR_RUN_ID
P340_RUN_ID_HEX = artifact.P340_RUN_ID_HEX
P340_RUN_ID = artifact.P340_RUN_ID
P339_IMAGE_IDENTITY = artifact.P339_IMAGE_IDENTITY
P339_AP_IDENTITY = artifact.P339_AP_IDENTITY


class AuditError(RuntimeError):
    """The exact P3.39 predecessor or P3.40 identity closure differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _stable(path: Path, label: str, maximum: int, expected: Mapping[str, Any] | None = None, *, mode: int | None = None, nlink: int | None = None) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AuditError(f"{label} is unavailable") from exc
    def inode(value: os.stat_result) -> tuple[int, ...]:
        return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink, value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    if (
        direct != resolved or stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1 or inode(before) != inode(inside) or inode(before) != inode(after)
        or len(payload) != before.st_size or len(payload) > maximum
        or (expected is not None and identity(payload) != dict(expected))
        or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
        or (nlink is not None and before.st_nlink != nlink)
    ):
        raise AuditError(f"{label} identity differs")
    return payload


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("ascii")


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def unique(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise AuditError(f"{label} has duplicate key {key}")
            result[key] = value
        return result
    try:
        value = json.loads(payload.decode("ascii"), object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} is not an object")
    return value


def _mkdir(path: Path) -> None:
    path.mkdir(mode=0o700)
    path.chmod(0o700)


def _write_exclusive(path: Path, payload: bytes, mode: int = 0o400) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    try:
        os.fchmod(descriptor, mode)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise AuditError(f"short publication: {path}")
            offset += written
        state = os.fstat(descriptor)
        if not stat.S_ISREG(state.st_mode) or state.st_nlink != 1 or state.st_size != len(payload) or stat.S_IMODE(state.st_mode) != mode:
            raise AuditError(f"publication identity differs: {path}")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _strict_children(path: Path, expected: set[str], label: str) -> None:
    try:
        state = path.lstat()
        children = {child.name for child in path.iterdir()}
    except OSError as exc:
        raise AuditError(f"{label} is unavailable") from exc
    if stat.S_ISLNK(state.st_mode) or not stat.S_ISDIR(state.st_mode) or stat.S_IMODE(state.st_mode) != 0o700 or children != expected:
        raise AuditError(f"{label} child set differs")


def _copy(source: Path, destination: Path, expected: Mapping[str, Any], label: str, *, maximum: int = 128 << 20) -> dict[str, Any]:
    payload = _stable(source, label, maximum, expected)
    _write_exclusive(destination, payload)
    return identity(payload)


def _replace_image(base_boot: bytes, old_image: bytes, new_image: bytes) -> tuple[bytes, dict[str, Any]]:
    if len(old_image) != len(new_image) or base_boot.count(old_image) != 1:
        raise AuditError("P311 base boot Image replacement is not one same-length span")
    offset = base_boot.find(old_image)
    if offset != 4096:
        raise AuditError("P311 Image offset differs")
    result = base_boot[:offset] + new_image + base_boot[offset + len(old_image):]
    if len(result) != len(base_boot) or result[:offset] != base_boot[:offset] or result[offset + len(new_image):] != base_boot[offset + len(old_image):]:
        raise AuditError("P340 base boot changed outside Image")
    return result, {"offset": offset, "size": len(old_image), "old_image": identity(old_image), "new_image": identity(new_image), "old_occurrences": 1, "outside_image_unchanged": True}


def _predecessor() -> tuple[dict[str, Any], bytes]:
    payload = _stable(P339_RESULT, "P3.39 result", 4 << 20, P339_RESULT_IDENTITY, mode=0o400, nlink=1)
    value = _strict_json(payload, "P3.39 result")
    candidate = value.get("phase2", {}).get("candidate")
    if value.get("schema") != "s22plus-fyg8-p339-stock-candidate-build-v1" or value.get("run_id_hex") != P339_RUN_ID_HEX or value.get("target") != TARGET or not isinstance(candidate, dict) or candidate.get("a") != candidate.get("b") or candidate.get("a", {}).get("ap_tar_md5") != P339_AP_IDENTITY or candidate.get("a", {}).get("package", {}).get("members") != ["boot.img.lz4"]:
        raise AuditError("P3.39 predecessor result differs")
    closure = value.get("source_closure")
    if not isinstance(closure, dict) or len(closure) != 12:
        raise AuditError("P3.39 source closure differs")
    for name, expected in sorted(closure.items()):
        _stable(P339_OUTPUT / "stock-sources" / name, f"P3.39 source {name}", 2 << 20, expected, mode=0o400, nlink=1)
    for label in ("a", "b"):
        _strict_children(P339_OUTPUT / f"candidate-{label}", {"boot.img", "boot.img.lz4", "odin4"}, f"P3.39 candidate {label} root")
        _strict_children(P339_OUTPUT / f"candidate-{label}/odin4", {"AP.tar.md5"}, f"P3.39 candidate {label} AP")
        _stable(P339_OUTPUT / f"candidate-{label}/odin4/AP.tar.md5", f"P3.39 candidate {label}", 128 << 20, P339_AP_IDENTITY)
    return value, payload


def _load_packager() -> tuple[types.ModuleType, bytes]:
    source = _stable(P319_PACKAGER_SOURCE, "P319 packaging helper", 2 << 20, P319_PACKAGER_IDENTITY)
    module = types.ModuleType("s22plus_fyg8_p319_packager_bound_for_p340")
    module.__file__ = str(P319_PACKAGER_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(source, str(P319_PACKAGER_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("P319 packaging helper failed to load") from exc
    module.RUN_ID = P340_RUN_ID
    module._ACTIVE_TOOLS = None
    module._bind_tools()
    return module, source


def _runtime_receipt(before: bytes, after: bytes) -> dict[str, Any]:
    key = runtime.predecessor._materialized_key(before)
    value = runtime.validate_transform(before, after, auth_key_sha256=hashlib.sha256(key).hexdigest())
    value = copy.deepcopy(value)
    def normalize(node: Any) -> Any:
        if isinstance(node, dict):
            result = {key: normalize(item) for key, item in node.items()}
            if isinstance(result.get("default_commands"), (tuple, list)):
                result["default_commands"] = [identity(item) if type(item) is bytes else item for item in result["default_commands"]]
            if isinstance(result.get("open_read_branch_ordinals"), dict):
                result["open_read_branch_ordinals"] = {str(key): item for key, item in result["open_read_branch_ordinals"].items()}
            return result
        if isinstance(node, (tuple, list)):
            return [normalize(item) for item in node]
        return node
    return normalize(value)


def _fresh_package(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result["package"]["schema"] = "s22plus_fyg8_p340_boot_only_identity_package_v1"
    result["package"]["verdict"] = "PASS_P340_DETERMINISTIC_BOOT_ONLY_IDENTITY_PACKAGE_H0"
    return result


def _package_from_p339(
    packager: types.ModuleType,
    template: Path,
    predecessor_candidate: dict[str, Any],
    image: bytes,
    init: bytes,
    child: bytes,
    module_payloads: dict[str, bytes],
    output: Path,
    label: str,
) -> dict[str, Any]:
    """Repack the exact P339 ramdisk, replacing only Image and /init."""
    tools = packager._tools()
    magiskboot = tools["magiskboot"]
    lz4 = tools["lz4"]
    old_image = _stable(template, f"P3.39 {label} template", 128 << 20, predecessor_candidate["boot_img"])
    with __import__("tempfile").TemporaryDirectory(prefix=f"p340-package-{label}-") as name:
        work = Path(name); unpack = work / "unpack"; final = work / "final"; audit = work / "audit"
        unpack.mkdir(); final.mkdir(); audit.mkdir()
        base = work / "base.boot.img"; base.write_bytes(old_image)
        init_path = work / "init"; init_path.write_bytes(init)
        packager._run_tool([magiskboot, "unpack", "-h", base], unpack, f"P340 {label} template unpack")
        kernel = unpack / "kernel"
        if identity(kernel.read_bytes()) != predecessor_candidate.get("fixed_image_identity", P339_IMAGE_IDENTITY):
            raise AuditError(f"P339 {label} template Image differs")
        kernel.write_bytes(image)
        ramdisk = unpack / "ramdisk.cpio"
        packager._run_tool([magiskboot, "cpio", ramdisk, f"add 750 init {init_path}"], unpack, f"P340 {label} init replacement")
        boot = work / "boot.img"
        packager._run_tool([magiskboot, "repack", base, boot], unpack, f"P340 {label} repack")
        packager._run_tool([magiskboot, "unpack", "-h", boot], final, f"P340 {label} final unpack")
        if (final / "kernel").read_bytes() != image:
            raise AuditError(f"P340 {label} Image differs after repack")
        final_ramdisk = final / "ramdisk.cpio"
        extracted_init = final / "init.final"
        extracted_child = final / "child.final"
        packager._run_tool([magiskboot, "cpio", final_ramdisk, f"extract init {extracted_init}"], final, f"P340 {label} init extract")
        packager._run_tool([magiskboot, "cpio", final_ramdisk, f"extract s22-e1-child {extracted_child}"], final, f"P340 {label} child extract")
        if extracted_init.read_bytes() != init or extracted_child.read_bytes() != child:
            raise AuditError(f"P340 {label} userspace differs after repack")
        expected_busybox = predecessor_candidate.get("busybox")
        if isinstance(expected_busybox, dict):
            busybox = final / "busybox.final"
            packager._run_tool([magiskboot, "cpio", final_ramdisk, f"extract bin/busybox {busybox}"], final, f"P340 {label} BusyBox extract")
            if identity(busybox.read_bytes()) != expected_busybox:
                raise AuditError(f"P339 {label} BusyBox changed")
        for module_name, payload in module_payloads.items():
            extracted = final / f"{module_name}.final"
            packager._run_tool([magiskboot, "cpio", final_ramdisk, f"extract lib/modules/{module_name} {extracted}"], final, f"P340 {label} module extract")
            if extracted.read_bytes() != payload:
                raise AuditError(f"P339 {label} module changed")
        frame = work / "boot.img.lz4"
        packager._run_tool([lz4, "--content-size", "-B6", "-f", "-q", boot, frame], work, f"P340 {label} LZ4 compression")
        ap_dir = work / "odin4"; ap_dir.mkdir(mode=0o700)
        ap_path = ap_dir / "AP.tar.md5"
        ap_structure = packager._write_deterministic_boot_ap(frame.read_bytes(), ap_path)
        output.mkdir(mode=0o700); output.chmod(0o700)
        for source, target in ((boot, output / "boot.img"), (frame, output / "boot.img.lz4"), (ap_path, output / "odin4/AP.tar.md5")):
            target.parent.mkdir(mode=0o700, exist_ok=True); target.parent.chmod(0o700)
            _write_exclusive(target, source.read_bytes())
        _fsync_directory(output / "odin4"); _fsync_directory(output)
        return {
            "boot_img": identity(boot.read_bytes()), "boot_img_lz4": identity(frame.read_bytes()), "ap_tar_md5": identity(ap_path.read_bytes()),
            "diagnostic_absent": True, "fixed_image": True, "exact_one_member_generic_overlay": True,
            "vendor_layer_stock_modules": 72, "overlay_members": ["lib/modules/s22plus_dwc3_event_latch.ko"],
            "inherited_modules_not_copied": True, "busybox": expected_busybox,
            "busybox_mode": predecessor_candidate.get("busybox_mode", "0755"), "busybox_path": predecessor_candidate.get("busybox_path", "bin/busybox"),
            "busybox_static_aarch64": predecessor_candidate.get("busybox_static_aarch64", True),
            "package": {"schema": "s22plus_fyg8_p340_boot_only_identity_package_v1", "verdict": "PASS_P340_DETERMINISTIC_BOOT_ONLY_IDENTITY_PACKAGE_H0", "boot_img": identity(boot.read_bytes()), "boot_img_lz4": identity(frame.read_bytes()), "ap_tar_md5": identity(ap_path.read_bytes()), "ap_structure": ap_structure, "paths": {"boot_img_lz4": "boot.img.lz4", "ap_tar_md5": "odin4/AP.tar.md5"}, "members": ["boot.img.lz4"], "verified": True, "safety": {"host_only": True, "boot_only": True, "device_contact": False, "device_write": False, "odin_invoked": False, "live_authorized": False}},
        }


def _adapter_audit(predecessor: dict[str, Any]) -> dict[str, Any]:
    """Keep build host-only; parent may replace this projection at registration."""
    try:
        import s22plus_fyg8_p340_stock_process_v2_adapter as adapter  # type: ignore[import-not-found]
        return adapter.audit()
    except (ImportError, AttributeError):
        value = copy.deepcopy(predecessor.get("adapter_audit", {}))
        value.update({"schema": "s22plus_fyg8_p340_stock_process_v2_adapter_pending_v1", "run_id": P340_RUN_ID_HEX, "predecessor_run_id": P339_RUN_ID_HEX, "predecessor_run_id_rejected": P339_RUN_ID_HEX, "device_contact": False, "live_authorized": False, "candidate_success": False, "causal_result_allowed": False, "registration_pending": True})
        return value


def _build_once(output_root: Path) -> dict[str, Any]:
    predecessor, predecessor_payload = _predecessor()
    p339_image = _stable(P339_OUTPUT / "inputs/fixed-Image", "P3.39 fixed Image", 64 << 20, P339_IMAGE_IDENTITY, mode=0o400, nlink=1)
    try:
        image, image_transform = artifact.transform_image(p339_image)
        artifact.validate_image(image)
    except Exception as exc:
        raise AuditError(str(exc)) from exc
    p339_runtime = _stable(P339_OUTPUT / "stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c", "P3.39 runtime include", 2 << 20, predecessor["source_closure"]["s22plus_fyg8_p290_e3_runtime.inc.c"], mode=0o400, nlink=1)
    key = runtime.predecessor._materialized_key(p339_runtime)
    try:
        transformed_runtime = runtime.transform_runtime_include(p339_runtime, key)
        runtime_repair = _runtime_receipt(p339_runtime, transformed_runtime)
    except Exception as exc:
        raise AuditError(str(exc)) from exc
    if output_root.exists() or output_root.is_symlink():
        raise AuditError("P340 output already exists")
    output_root.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    output_root.parent.chmod(0o700)
    _mkdir(output_root)
    inputs = output_root / "inputs"; _mkdir(inputs)
    input_receipts: dict[str, dict[str, Any]] = {}
    input_receipts["p339-result.json"] = _copy(P339_RESULT, inputs / "p339-result.json", P339_RESULT_IDENTITY, "P3.39 result input", maximum=4 << 20)
    input_receipts["p339-stock-candidate-build.py"] = _copy(P339_BUILDER_SOURCE, inputs / "p339-stock-candidate-build.py", P339_BUILDER_IDENTITY, "P3.39 builder input", maximum=2 << 20)
    input_receipts["p319-stock-candidate-build.py"] = _copy(P319_PACKAGER_SOURCE, inputs / "p319-stock-candidate-build.py", P319_PACKAGER_IDENTITY, "P319 packaging helper input", maximum=2 << 20)
    for name, path in (("p339-artifact-identity.py", P339_ARTIFACT_SOURCE), ("p339-runtime.py", P339_RUNTIME_SOURCE), ("p339-observer.py", P339_OBSERVER_SOURCE), ("p340-artifact-identity.py", P340_ARTIFACT_SOURCE), ("p340-runtime.py", P340_RUNTIME_SOURCE), ("p340-observer.py", P340_OBSERVER_SOURCE), ("p340-adapter.py", P340_ADAPTER_SOURCE), ("p340-stock-candidate-build.py", SELF_SOURCE)):
        payload = _stable(path, f"{name} source", 2 << 20)
        _write_exclusive(inputs / name, payload)
        input_receipts[name] = identity(payload)
    input_receipts["fixed-Image"] = identity(image)
    _write_exclusive(inputs / "fixed-Image", image)
    input_receipts["p311-base-boot.img"] = _copy(P339_OUTPUT / "inputs/p311-base-boot.img", inputs / "p311-base-boot.img", predecessor["inputs"]["p311-base-boot.img"], "P311 base boot input")
    input_receipts["child-source.c"] = _copy(P339_OUTPUT / "inputs/child-source.c", inputs / "child-source.c", predecessor["inputs"]["child-source.c"], "child source input", maximum=64 << 10)
    source_root = output_root / "stock-sources"; _mkdir(source_root)
    source_receipts: dict[str, dict[str, Any]] = {}
    for name, expected in sorted(predecessor["source_closure"].items()):
        before = _stable(P339_OUTPUT / "stock-sources" / name, f"P3.39 source {name}", 2 << 20, expected, mode=0o400, nlink=1)
        payload = transformed_runtime if name == "s22plus_fyg8_p290_e3_runtime.inc.c" else before
        _write_exclusive(source_root / name, payload)
        source_receipts[name] = identity(payload)
    module_root = output_root / "module-bytes"; _mkdir(module_root)
    module_identity = predecessor["module_bytes"]["s22plus_dwc3_event_latch.ko"]
    _copy(P339_OUTPUT / "module-bytes/s22plus_dwc3_event_latch.ko", module_root / "s22plus_dwc3_event_latch.ko", module_identity, "P3.39 latch module", maximum=8 << 20)
    base = _stable(inputs / "p311-base-boot.img", "P340 base boot", 128 << 20, input_receipts["p311-base-boot.img"], mode=0o400, nlink=1)
    old_image = _stable(artifact.P319_IMAGE, "P319 source Image", 64 << 20, artifact.P319_IMAGE_IDENTITY)
    prepared_base, replacement = _replace_image(base, old_image, image)
    packager, packager_source = _load_packager()
    userspace_a = packager._compile_userspace(source_root, output_root / "userspace-a", label="a")
    userspace_b = packager._compile_userspace(source_root, output_root / "userspace-b", label="b")
    init = _stable(output_root / "userspace-a/init", "P340 /init", 2 << 20, userspace_a["init"], mode=0o400, nlink=1)
    child = _stable(output_root / "userspace-a/s22-e1-child", "P340 child", 2 << 20, userspace_a["child"], mode=0o400, nlink=1)
    module_payloads = {"s22plus_dwc3_event_latch.ko": _stable(module_root / "s22plus_dwc3_event_latch.ko", "P340 latch", 8 << 20, module_identity, mode=0o400, nlink=1)}
    overlay = ("s22plus_dwc3_event_latch.ko",)
    candidate_a = _package_from_p339(packager, P339_OUTPUT / "candidate-a/boot.img", predecessor["phase2"]["candidate"]["a"], image, init, child, module_payloads, output_root / "candidate-a", "a")
    candidate_b = _package_from_p339(packager, P339_OUTPUT / "candidate-b/boot.img", predecessor["phase2"]["candidate"]["b"], image, init, child, module_payloads, output_root / "candidate-b", "b")
    if candidate_a != candidate_b:
        raise AuditError("P340 candidate A/B differs")
    try:
        ap_a = artifact.inspect_ap(output_root / "candidate-a/odin4/AP.tar.md5", expected_run_id=P340_RUN_ID, expected_image=image, expected_init=init, expected_child=child, expected_ap=candidate_a["ap_tar_md5"], label="P340 candidate A AP")
        ap_b = artifact.inspect_ap(output_root / "candidate-b/odin4/AP.tar.md5", expected_run_id=P340_RUN_ID, expected_image=image, expected_init=init, expected_child=child, expected_ap=candidate_b["ap_tar_md5"], label="P340 candidate B AP")
        rollback = artifact.validate_rollback_ap(ROLLBACK_AP, ROLLBACK_IDENTITY)
    except Exception as exc:
        raise AuditError(str(exc)) from exc
    candidate = {
        "a": candidate_a, "b": candidate_b, "ab_artifact_identity_equal": True, "byte_identical": True,
        "fixed_image": True, "fixed_image_identity": identity(image), "base_boot_replacement": replacement,
        "differs_from_consumed_p339": True, "one_boot_img_lz4_member": True, "overlay_members": ["lib/modules/s22plus_dwc3_event_latch.ko"],
        "vendor_layer_stock_modules": 72, "inherited_modules_not_copied": True,
        "run_id_join": {"run_id_hex": P340_RUN_ID_HEX, "image_run_id_hex": P340_RUN_ID_HEX, "init_run_id_hex": P340_RUN_ID_HEX, "joined": True, "a": ap_a, "b": ap_b},
    }
    phase2 = {"ap_builds": 2, "boot_builds": 2, "built": True, "static_aarch64": True, "userspace": {"a": userspace_a, "b": userspace_b, "byte_identical": userspace_a == userspace_b}, "candidate": candidate, "rollback": {"artifact_identity": rollback}}
    result = copy.deepcopy(predecessor)
    result.update({"schema": SCHEMA, "verdict": VERDICT, "status": STATUS, "target": TARGET, "run_id_hex": P340_RUN_ID_HEX, "phase2": phase2, "inputs": input_receipts, "source_closure": source_receipts, "module_bytes": {"s22plus_dwc3_event_latch.ko": module_identity}, "tools": {name: dict(value) for name, value in sorted(packager.TOOL_IDENTITIES.items())}, "adapter_audit": _adapter_audit(predecessor)})
    result["scope"] = {"tier": "H0", "host_only": True, "device_contact": False, "adb_commands": 0, "odin_invocations": 0, "candidate_transfers": 0, "rollback_transfers": 0, "live_authority_created": False, "replay": False}
    result["lineage"] = {"construction_base_run_id": P339_RUN_ID_HEX, "construction_base_result": P339_RESULT_IDENTITY, "construction_base_ap": P339_AP_IDENTITY, "predecessor_run_id": P339_RUN_ID_HEX, "predecessor_result": P339_RESULT_IDENTITY, "predecessor_ap": P339_AP_IDENTITY, "fresh_run_id": P340_RUN_ID_HEX, "image_transform": image_transform, "runtime_repair": runtime_repair, "p339_source_closure_reopened": True}
    result["helper_sources"] = {"p319_stock_candidate_build.py": identity(packager_source), "p339_stock_candidate_build.py": identity(P339_BUILDER_SOURCE.read_bytes()), "p339_artifact_identity.py": identity(P339_ARTIFACT_SOURCE.read_bytes()), "p339_open_read_branch_runtime.py": identity(P339_RUNTIME_SOURCE.read_bytes()), "p339_open_read_branch_acm_observer.py": identity(P339_OBSERVER_SOURCE.read_bytes()), "p340_stock_candidate_build.py": identity(SELF_SOURCE.read_bytes()), "p340_artifact_identity.py": identity(P340_ARTIFACT_SOURCE.read_bytes()), "p340_open_read_branch_runtime.py": identity(P340_RUNTIME_SOURCE.read_bytes()), "p340_open_read_branch_acm_observer.py": identity(P340_OBSERVER_SOURCE.read_bytes()), "p340_stock_process_v2_adapter.py": identity(P340_ADAPTER_SOURCE.read_bytes())}
    result["runtime_transform"] = runtime_repair
    result["fixed_image"] = True; result["byte_identical"] = True; result["boot_only"] = True
    result["framed_exec"] = copy.deepcopy(predecessor["framed_exec"]); result["resident"] = copy.deepcopy(predecessor["resident"])
    for section in (result["framed_exec"], result["resident"]):
        section.update({"runtime_contract": runtime.CONTRACT_ID, "observer_contract": "s22plus-fyg8-p340-open-header-capture-acm-observer-v1", "commands": [identity(item) for item in runtime.DEFAULT_COMMANDS], "command_count_per_session": len(runtime.DEFAULT_COMMANDS), "open_read_branch_count": len(runtime.OPEN_READ_BRANCHES), "open_header_word_stages": list(runtime.OPEN_HEADER_WORD_STAGES), "open_header_size": runtime.OPEN_HEADER_SIZE, "open_header_capture_best_effort": True})
    result["preservation"] = copy.deepcopy(predecessor.get("preservation", {}))
    result["preservation"].update({"p339_consumed_candidate_unchanged": True, "p339_source_closure_reopened": True, "runtime_delta_identity_only": True, "runtime_delta_header_capture_unchanged": True, "image_size_and_layout_preserved": True, "ab_artifact_identity_equal": True, "rollback_untouched": True})
    result["limitations"] = ["P340 changes only the run-ID-bearing Image, fixed runtime command marker, and compiler-bound /init identity.", "P339 stage-3 grammar=1, semantic=4, and four header-word diagnostics are unchanged.", "P340 reuses the existing pinned P319 packaging helper and exact P339 -04 source closure.", "Only boot is packaged; exact Magisk rollback remains mandatory.", "This H0 unit creates no device, approval, D0/D1/F1/recovery/replay/live authority."]
    _write_exclusive(output_root / "result.json", _json_bytes(result))
    for directory in (inputs, source_root, module_root, output_root / "userspace-a", output_root / "userspace-b", output_root / "candidate-a/odin4", output_root / "candidate-b/odin4", output_root):
        _fsync_directory(directory)
    return result


def build_result(output_root: Path = DEFAULT_OUTPUT_ROOT, *, audit_only: bool = False) -> dict[str, Any]:
    output_root = output_root.absolute()
    if audit_only:
        return audit_existing(output_root)
    return _build_once(output_root)


def audit_existing(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.absolute()
    result_payload = _stable(output_root / "result.json", "P340 result", 4 << 20, mode=0o400, nlink=1)
    result = _strict_json(result_payload, "P340 result")
    if result.get("schema") != SCHEMA or result.get("verdict") != VERDICT or result.get("status") != STATUS or result.get("target") != TARGET or result.get("run_id_hex") != P340_RUN_ID_HEX:
        raise AuditError("P340 result header differs")
    _strict_children(output_root, {"inputs", "stock-sources", "module-bytes", "userspace-a", "userspace-b", "candidate-a", "candidate-b", "result.json"}, "P340 output root")
    predecessor, _payload = _predecessor()
    for name, expected in sorted(predecessor["source_closure"].items()):
        before = _stable(P339_OUTPUT / "stock-sources" / name, f"P3.39 audit source {name}", 2 << 20, expected, mode=0o400, nlink=1)
        expected_after = before
        if name == "s22plus_fyg8_p290_e3_runtime.inc.c":
            key = runtime.predecessor._materialized_key(before)
            expected_after = runtime.transform_runtime_include(before, key)
        _stable(output_root / "stock-sources" / name, f"P340 audit source {name}", 2 << 20, identity(expected_after), mode=0o400, nlink=1)
    p339_image = _stable(P339_OUTPUT / "inputs/fixed-Image", "P3.39 audit Image", 64 << 20, P339_IMAGE_IDENTITY, mode=0o400, nlink=1)
    image, image_transform = artifact.transform_image(p339_image)
    _stable(output_root / "inputs/fixed-Image", "P340 audit Image", 64 << 20, identity(image), mode=0o400, nlink=1)
    if result.get("lineage", {}).get("image_transform") != image_transform:
        raise AuditError("P340 Image transform receipt differs")
    before = _stable(P339_OUTPUT / "stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c", "P3.39 audit runtime", 2 << 20, predecessor["source_closure"]["s22plus_fyg8_p290_e3_runtime.inc.c"], mode=0o400, nlink=1)
    key = runtime.predecessor._materialized_key(before)
    after = runtime.transform_runtime_include(before, key)
    _stable(output_root / "stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c", "P340 audit runtime", 2 << 20, identity(after), mode=0o400, nlink=1)
    if result.get("runtime_transform") != _runtime_receipt(before, after):
        raise AuditError("P340 runtime transform receipt differs")
    packager, _ = _load_packager()
    candidate = result.get("phase2", {}).get("candidate", {})
    userspace = result.get("phase2", {}).get("userspace", {})
    init = _stable(output_root / "userspace-a/init", "P340 audit init", 2 << 20, userspace["a"]["init"], mode=0o400, nlink=1)
    child = _stable(output_root / "userspace-a/s22-e1-child", "P340 audit child", 2 << 20, userspace["a"]["child"], mode=0o400, nlink=1)
    modules = {"s22plus_dwc3_event_latch.ko": _stable(output_root / "module-bytes/s22plus_dwc3_event_latch.ko", "P340 audit latch", 8 << 20, result["module_bytes"]["s22plus_dwc3_event_latch.ko"], mode=0o400, nlink=1)}
    for label in ("a", "b"):
        packager._verify_packaged_candidate(output_root / f"candidate-{label}", candidate[label], init, child, modules, image, ("s22plus_dwc3_event_latch.ko",), f"P340-audit-candidate-{label}")
        artifact.inspect_ap(output_root / f"candidate-{label}/odin4/AP.tar.md5", expected_run_id=P340_RUN_ID, expected_image=image, expected_init=init, expected_child=child, expected_ap=candidate[label]["ap_tar_md5"], label=f"P340 audit candidate {label} AP")
    artifact.validate_rollback_ap(ROLLBACK_AP, ROLLBACK_IDENTITY)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = __import__("argparse").ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    output = args.out if args.out.is_absolute() else ROOT / args.out
    try:
        result = build_result(output, audit_only=args.audit_only)
    except (AuditError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": result["verdict"], "output": str(output), "result": identity((output / "result.json").read_bytes()), "created": not args.audit_only, "device_contact": False, "live_authorized": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

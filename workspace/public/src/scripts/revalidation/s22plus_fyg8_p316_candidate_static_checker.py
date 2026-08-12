#!/usr/bin/env python3
"""Independently reconstruct and audit the reproducible P3.16 candidate."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Iterator

import build_s22plus_fyg8_p316_candidate as candidate
import s22plus_fyg8_max77705_custom_surface_contract as surface
import s22plus_fyg8_p286_candidate_static_checker as base
import s22plus_fyg8_p311_candidate_static_checker as p311_static
import s22plus_fyg8_p315_candidate_static_checker as inherited
import s22plus_fyg8_p316_candidate_contract as contract
import s22plus_fyg8_p316_e2_stock_closure as closure
import s22plus_fyg8_p316_lifecycle_audit as lifecycle
import s22plus_fyg8_p316_overlay_contract as overlay
import s22plus_fyg8_p316_qualification_closure as qualification
import s22plus_fyg8_p316_runtime_fixture as runtime_fixture
import s22plus_fyg8_p316_sidecar_positive_control as sidecar_control
import s22plus_fyg8_p316_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p316_candidate_static_checker_v1"
VERDICT = "PASS_P316_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
EXPECTED_MODULE_PLAN_COUNT = 64
RESULT_PREFIX = "p316"
TARGET = contract.TARGET
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_CANDIDATE_B = qualification.DEFAULT_CANDIDATE_B
DEFAULT_IMAGE = candidate.DEFAULT_IMAGE
DEFAULT_REPRO_RESULT = candidate.DEFAULT_REPRO_RESULT
DEFAULT_USERSPACE = candidate.DEFAULT_USERSPACE
DEFAULT_BASE_BOOT = candidate.DEFAULT_BASE_BOOT
DEFAULT_VENDOR_RAMDISK = candidate.DEFAULT_VENDOR_RAMDISK
DEFAULT_VENDOR_BOOT = inherited.DEFAULT_VENDOR_BOOT
DEFAULT_LZ4 = candidate.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = candidate.DEFAULT_MAGISKBOOT
DEFAULT_DIAGNOSTIC = candidate.DEFAULT_DIAGNOSTIC
DEFAULT_SOURCE = contract.DEFAULT_SOURCE
DEFAULT_INTENT = contract.DEFAULT_INTENT
DEFAULT_PATCH = contract.DEFAULT_PATCH
DEFAULT_QUALIFICATION = qualification.DEFAULT_OUT
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p316/static-check-result.json")
CheckError = base.CheckError
ARTIFACT_LIMITS = base.ARTIFACT_LIMITS
repo_root = contract.intent.repo_root
stable_read = base.stable_read


def _resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


resolve = _resolve


@contextmanager
def _rootfs_entrypoint_context(payloads: dict[str, bytes]) -> Iterator[None]:
    try:
        entrypoints = {
            "init": base.e1_static.inspect_static_elf(
                payloads["init"], "P3.16 exact /init"
            )["entrypoint"],
            "child": base.e1_static.inspect_static_elf(
                payloads["child"], "P3.16 exact child"
            )["entrypoint"],
        }
    except (KeyError, base.e1_static.CheckError) as exc:
        raise CheckError("P3.16 exact userspace entrypoint is invalid") from exc
    if any(
        isinstance(value, bool) or not isinstance(value, int)
        for value in entrypoints.values()
    ):
        raise CheckError("P3.16 exact userspace entrypoint is malformed")
    entrypoint_api = closure.P310.parent.p286.p282.p280
    with entrypoint_api._expected_entrypoints(entrypoints):  # noqa: SLF001
        with closure.exact_init_authority(payloads["init"]):
            yield


def _userspace(
    root: Path, directory: Path, exact: dict[str, Any]
) -> tuple[dict[str, bytes], dict[str, Any], dict[str, Any]]:
    if directory.is_symlink() or not directory.is_dir() or {
        path.name for path in directory.iterdir()
    } != {"init", "s22-e1-child", "userspace-result.json"}:
        raise CheckError("P3.16 userspace inventory differs")
    value, payload = base.read_json(
        directory / "userspace-result.json", "P3.16 userspace result", 16 * 1024 * 1024
    )
    if (
        value.get("schema") != userspace.SCHEMA
        or value.get("verdict") != userspace.VERDICT
        or value.get("candidate_contract") != exact
        or value.get("source_contract") != userspace._source_contract(exact)  # noqa: SLF001
        or value.get("two_build_byte_identical") is not True
        or value.get("module_plan_count") != EXPECTED_MODULE_PLAN_COUNT
        or value.get("late_diagnostic_payload_count") != 1
    ):
        raise CheckError("P3.16 userspace result differs")
    paths = {"init": directory / "init", "child": directory / "s22-e1-child"}
    data = {
        name: base.stable_read(path, f"P3.16 {name}", 1024 * 1024)
        for name, path in paths.items()
    }
    for name, path in paths.items():
        base.require_receipt(
            base.receipt(data[name]), value.get("outputs", {}).get(name), name
        )
        if path.stat(follow_symlinks=False).st_mode & 0o777 != 0o755:
            raise CheckError(f"P3.16 {name} mode differs")
    qemu_path = Path(userspace.base.require_tools()["qemu-aarch64"])
    qemu = base.stable_read(qemu_path, "P3.16 qemu-aarch64", 32 * 1024 * 1024)
    with tempfile.TemporaryDirectory(prefix="s22-p316-child-") as name:
        staged_qemu = Path(name) / "qemu-aarch64"
        staged_child = Path(name) / "s22-e1-child"
        staged_qemu.write_bytes(qemu)
        staged_child.write_bytes(data["child"])
        staged_qemu.chmod(0o700)
        staged_child.chmod(0o700)
        completed = subprocess.run(
            [staged_qemu, staged_child],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
    if (
        completed.returncode != userspace.base.CHILD_EXIT
        or completed.stdout != userspace.base.CHILD_TOKEN
        or completed.stderr
    ):
        raise CheckError("P3.16 child check failed")
    return (
        data,
        {
            "result": base.receipt(payload),
            "init": base.receipt(data["init"]),
            "child": base.receipt(data["child"]),
            "two_build_byte_identical": True,
            "verified": True,
        },
        base.receipt(qemu),
    )


def _candidate_payloads(directory: Path, label: str) -> tuple[dict[str, bytes], dict]:
    if directory.is_symlink() or not directory.is_dir() or {
        path.name for path in directory.iterdir()
    } != {"artifact-result.json", "boot.img", "boot.img.lz4", "odin4"}:
        raise CheckError(f"P3.16 candidate {label} inventory differs")
    odin = directory / "odin4"
    if odin.is_symlink() or not odin.is_dir() or {
        path.name for path in odin.iterdir()
    } != {"AP.tar.md5"}:
        raise CheckError(f"P3.16 candidate {label} Odin inventory differs")
    if any((directory / name).exists() for name in ("manifest.json", "run-manifest.json")):
        raise CheckError(f"P3.16 candidate {label} unexpectedly has a manifest")
    paths = {
        "artifact_result": directory / "artifact-result.json",
        "boot_img": directory / "boot.img",
        "boot_img_lz4": directory / "boot.img.lz4",
        "ap_tar_md5": odin / "AP.tar.md5",
    }
    payloads = {
        name: base.stable_read(path, f"P3.16 {label} {name}", base.ARTIFACT_LIMITS[name])
        for name, path in paths.items()
    }
    try:
        value = json.loads(payloads["artifact_result"].decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError(f"P3.16 candidate {label} result is invalid") from exc
    if not isinstance(value, dict):
        raise CheckError(f"P3.16 candidate {label} result root differs")
    return payloads, value


def _verify_artifact_result(
    value: dict[str, Any],
    *,
    exact: dict[str, Any],
    outputs: dict[str, bytes],
    prepackaging_receipt: dict[str, Any],
    module_closure: dict[str, Any],
) -> None:
    construction = value.get("construction", {})
    safety = value.get("safety", {})
    if (
        value.get("schema") != candidate.SCHEMA
        or value.get("verdict") != candidate.VERDICT
        or value.get("candidate_contract") != exact
        or value.get("prepackaging_closure") != prepackaging_receipt
        or value.get("module_closure") != module_closure
        or any(
            value.get("outputs", {}).get(name) != base.receipt(outputs[name])
            for name in ("boot_img", "boot_img_lz4", "ap_tar_md5")
        )
        or construction.get("diagnostic_module")
        != {
            "size": surface.DIAG_MODULE_IDENTITY[0],
            "sha256": surface.DIAG_MODULE_IDENTITY[1],
        }
        or construction.get("diagnostic_staged_path")
        != candidate.DIAGNOSTIC_RAMDISK_PATH
        or construction.get("diagnostic_staged_exactly_once") is not True
        or construction.get("diagnostic_absent_from_base") is not True
        or construction.get("diagnostic_absent_from_early_plan") is not True
        or safety.get("custom_module_binaries_injected") != 1
        or safety.get("fixed_p310_image") is not True
        or safety.get("boot_only_ap") is not True
        or safety.get("device_contact") is not False
    ):
        raise CheckError("P3.16 candidate artifact result differs")


def audit(args: argparse.Namespace) -> dict[str, Any]:
    root = contract.intent.repo_root()
    intent_path = _resolve(root, args.intent)
    exact = overlay.verify_intent(root, intent_path)
    qualification_payload, qualified = qualification._read_json(  # noqa: SLF001
        _resolve(root, args.qualification), "P3.16 final qualification"
    )
    trees = (
        qualification._tree_receipts(_resolve(root, args.candidate)),  # noqa: SLF001
        qualification._tree_receipts(_resolve(root, args.candidate_b)),  # noqa: SLF001
    )
    if trees[0] != trees[1]:
        raise CheckError("P3.16 qualification candidate trees differ")
    qualification.validate_qualification_artifact(
        qualified, root=root, candidate_tree=trees[0], intent_path=intent_path
    )
    prepackaging_receipt = qualified.get("prepackaging_receipt")
    if not isinstance(prepackaging_receipt, dict):
        raise CheckError("P3.16 prepackaging receipt is absent")
    image = base.stable_read(
        _resolve(root, args.image), "P3.16 fixed Image", candidate.KERNEL_END - candidate.KERNEL_START
    )
    if base.receipt(image) != overlay.EXPECTED_IMAGE:
        raise CheckError("P3.16 fixed Image differs")
    base.boot_verify.parse_arm64_header(image)
    payloads_user, userspace_closure, qemu_receipt = _userspace(
        root, _resolve(root, args.userspace), exact
    )
    diagnostic = base.stable_read(
        _resolve(root, args.diagnostic), "P3.16 diagnostic module", 4 * 1024 * 1024
    )
    if base.receipt(diagnostic) != {
        "size": surface.DIAG_MODULE_IDENTITY[0],
        "sha256": surface.DIAG_MODULE_IDENTITY[1],
    }:
        raise CheckError("P3.16 diagnostic module differs")
    plan_header = intent_path.parent / "materialized-sources" / "s22plus_fyg8_p286_e3_plan.h"
    module_closure = closure.derive_module_closure(
        root,
        _resolve(root, args.vendor_ramdisk),
        _resolve(root, args.lz4),
        plan_header=plan_header,
    )
    if len(module_closure.get("modules", ())) != EXPECTED_MODULE_PLAN_COUNT:
        raise CheckError("P3.16 early module closure differs")
    payloads_a, result_a = _candidate_payloads(_resolve(root, args.candidate), "A")
    payloads_b, result_b = _candidate_payloads(_resolve(root, args.candidate_b), "B")
    if payloads_a != payloads_b or result_a != result_b:
        raise CheckError("P3.16 candidate A/B bytes differ")
    _verify_artifact_result(
        result_a,
        exact=exact,
        outputs=payloads_a,
        prepackaging_receipt=prepackaging_receipt,
        module_closure=module_closure,
    )
    ap_info, ap_frame = base.boot_verify.parse_ap_tar_md5(payloads_a["ap_tar_md5"])
    if ap_frame != payloads_a["boot_img_lz4"] or ap_info["member"]["name"] != "boot.img.lz4":
        raise CheckError("P3.16 AP frame differs")
    base_boot = base.carrier.read_exact_file(
        _resolve(root, args.base_boot), candidate.BOOT_SIZE,
        base.carrier.EXPECTED_BASE_BOOT_SHA256, "P3.16 base boot"
    )
    lz4 = base.carrier.read_exact_file(
        _resolve(root, args.lz4), base.carrier.r4w1b.LZ4_SIZE,
        base.carrier.r4w1b.LZ4_SHA256, "P3.16 lz4"
    )
    magiskboot = base.carrier.read_exact_file(
        _resolve(root, args.magiskboot), base.carrier.MAGISKBOOT_SIZE,
        base.carrier.MAGISKBOOT_SHA256, "P3.16 magiskboot"
    )
    vendor_boot = base.carrier.read_exact_file(
        _resolve(root, args.vendor_boot), base.e1_static.base_static.VENDOR_BOOT_SIZE,
        base.e1_static.base_static.VENDOR_BOOT_SHA256, "P3.16 vendor_boot"
    )
    effective_rootfs = None
    with tempfile.TemporaryDirectory(prefix="s22-p316-static-") as name:
        work = Path(name)
        tools = work / "tools"
        base_unpack = work / "base-unpack"
        candidate_unpack = work / "candidate-unpack"
        tools.mkdir(); base_unpack.mkdir(); candidate_unpack.mkdir()
        paths = {
            "lz4": tools / "lz4",
            "magiskboot": tools / "magiskboot",
            "base": tools / "base.boot.img",
            "init": tools / "init",
            "child": tools / "s22-e1-child",
            "diag": tools / candidate.DIAGNOSTIC_NAME,
            "frame": tools / "boot.img.lz4",
            "candidate": tools / "candidate.boot.img",
        }
        for key, data, executable in (
            ("lz4", lz4, True), ("magiskboot", magiskboot, True),
            ("base", base_boot, False), ("init", payloads_user["init"], True),
            ("child", payloads_user["child"], True), ("diag", diagnostic, False),
            ("frame", ap_frame, False), ("candidate", payloads_a["boot_img"], False),
        ):
            paths[key].write_bytes(data); paths[key].chmod(0o700 if executable else 0o600)
        roundtrip = tools / "roundtrip.boot.img"
        base.run([paths["lz4"], "-d", "-f", "-q", paths["frame"], roundtrip], work, "P3.16 LZ4 roundtrip")
        if roundtrip.read_bytes() != payloads_a["boot_img"]:
            raise CheckError("P3.16 independent LZ4 roundtrip differs")
        base.run([paths["magiskboot"], "unpack", "-h", paths["base"]], base_unpack, "P3.16 unpack base")
        ramdisk = base_unpack / "ramdisk.cpio"
        exists = subprocess.run(
            [paths["magiskboot"], "cpio", ramdisk, f"exists {candidate.DIAGNOSTIC_RAMDISK_PATH}"],
            cwd=base_unpack, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False, timeout=30,
        )
        if exists.returncode != 1:
            raise CheckError("P3.16 diagnostic unexpectedly exists in base")
        for mode, member, source in (
            (750, "init", paths["init"]),
            (750, "s22-e1-child", paths["child"]),
            (644, candidate.DIAGNOSTIC_RAMDISK_PATH, paths["diag"]),
        ):
            base.run(
                [paths["magiskboot"], "cpio", ramdisk, f"add {mode} {member} {source}"],
                base_unpack, f"P3.16 independently add {member}",
            )
        carrier_path = tools / "reconstructed.carrier.img"
        base.run([paths["magiskboot"], "repack", paths["base"], carrier_path], base_unpack, "P3.16 independent repack")
        carrier_bytes = carrier_path.read_bytes()
        expected = carrier_bytes[:candidate.KERNEL_START] + image + carrier_bytes[candidate.KERNEL_END:]
        if expected != payloads_a["boot_img"]:
            raise CheckError("P3.16 candidate differs from independent reconstruction")
        base.run([paths["magiskboot"], "unpack", "-h", paths["candidate"]], candidate_unpack, "P3.16 unpack candidate")
        final_ramdisk = candidate_unpack / "ramdisk.cpio"
        extracted = {}
        for key, member in (("init", "init"), ("child", "s22-e1-child"), ("diag", candidate.DIAGNOSTIC_RAMDISK_PATH)):
            target = tools / f"extracted.{key}"
            base.run([paths["magiskboot"], "cpio", final_ramdisk, f"extract {member} {target}"], candidate_unpack, f"P3.16 extract {key}")
            extracted[key] = target.read_bytes()
        if (
            extracted["init"] != payloads_user["init"]
            or extracted["child"] != payloads_user["child"]
            or extracted["diag"] != diagnostic
            or (candidate_unpack / "kernel").read_bytes() != image
        ):
            raise CheckError("P3.16 extracted content differs")
        try:
            with _rootfs_entrypoint_context(payloads_user):
                effective_rootfs = closure.rootfs_audit(
                    payloads_a["boot_img"], vendor_boot, paths["lz4"],
                    expected_init=base.receipt(payloads_user["init"]),
                    expected_child=base.receipt(payloads_user["child"]),
                    run_id=bytes.fromhex(exact["run_id"]),
                    module_closure=module_closure,
                )
        except closure.ClosureError as exc:
            raise CheckError("P3.16 effective rootfs audit failed") from exc
    p311_static.p310_static._configure()  # noqa: SLF001
    repro, repro_receipt = p311_static.verify_repro(root, args, exact)
    runtime = runtime_fixture.audit(root)
    lifecycle_value = lifecycle.audit(root)
    sidecar = sidecar_control.audit(root)
    result = {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": VERDICT,
        "candidate_contract": exact,
        "build_repro": {
            "result": repro_receipt,
            "image": base.receipt(image),
            "fresh_reverification": True,
            "two_clean_builds_byte_identical": True,
            "linked_audit_verified": True,
        },
        "candidate": {
            "artifacts": {name: base.receipt(data) for name, data in payloads_a.items()},
            "candidate_b_artifacts": {name: base.receipt(data) for name, data in payloads_b.items()},
            "base_boot": base.receipt(base_boot),
            "ap": ap_info,
            "fixed_interval": {
                "kernel_start": candidate.KERNEL_START,
                "kernel_end_exclusive": candidate.KERNEL_END,
                "header_preserved": True,
                "ramdisk_preserved": True,
                "outside_interval_changed_byte_count": 0,
                "verified": True,
            },
            "userspace": userspace_closure,
            "module_closure": module_closure,
            "effective_rootfs": effective_rootfs,
            "stock_vendor_boot": base.receipt(vendor_boot),
            "diagnostic_module": base.receipt(diagnostic),
            "diagnostic_ramdisk_path": candidate.DIAGNOSTIC_RAMDISK_PATH,
            "independent_reconstruction": True,
            "independent_lz4_roundtrip": True,
            "independent_magiskboot_unpack": True,
            "writer_exclusion_verified": True,
            "two_package_builds_byte_identical": True,
            "manifest_absent": True,
            "boot_only_ap": True,
            "verified": True,
        },
        f"{RESULT_PREFIX}_runtime_fixture": runtime,
        f"{RESULT_PREFIX}_late_loader_lifecycle": lifecycle_value,
        f"{RESULT_PREFIX}_process_v2_adapter_fixture": exact["process_v2_adapter_fixture"],
        f"{RESULT_PREFIX}_sidecar_positive_control": sidecar,
        f"{RESULT_PREFIX}_qualification_closure": qualified,
        f"{RESULT_PREFIX}_telemetry": exact["telemetry"],
        f"{RESULT_PREFIX}_observer": exact["observer"],
        "tools": {"lz4": base.receipt(lz4), "magiskboot": base.receipt(magiskboot), "qemu_aarch64": qemu_receipt},
        "limits": [
            "host-only artifact qualification grants no D0, D1, F1, or live authority",
            "candidate execution and retained observation remain unproved",
        ],
        "safety": {
            "host_only": True, "device_contact": False, "device_write": False,
            "odin_invoked": False, "flash": False, "partition_write": False,
            "manifest_created": False, "live_authorized": False,
        },
    }
    if repro.get("verified") is not True or qualification_payload != base.stable_read(
        _resolve(root, args.qualification), "P3.16 qualification reread", 64 * 1024 * 1024
    ):
        raise CheckError("P3.16 qualification/repro changed during audit")
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--candidate-b", type=Path, default=DEFAULT_CANDIDATE_B)
    parser.add_argument("--qualification", type=Path, default=DEFAULT_QUALIFICATION)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--repro-result", type=Path, default=DEFAULT_REPRO_RESULT)
    parser.add_argument("--userspace", type=Path, default=DEFAULT_USERSPACE)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--vendor-ramdisk", type=Path, default=DEFAULT_VENDOR_RAMDISK)
    parser.add_argument("--vendor-boot", type=Path, default=DEFAULT_VENDOR_BOOT)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--diagnostic", type=Path, default=DEFAULT_DIAGNOSTIC)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--intent", type=Path, default=DEFAULT_INTENT)
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        result = audit(args)
        encoded = json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode("ascii") + b"\n"
        base.durable_create(_resolve(contract.intent.repo_root(), args.out), encoded)
    except (
        CheckError, candidate.BuildError, qualification.QualificationError,
        contract.ContractError, contract.intent.IntentError,
        overlay.OverlayContractError, closure.ClosureError,
        subprocess.TimeoutExpired, OSError, ValueError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": result["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

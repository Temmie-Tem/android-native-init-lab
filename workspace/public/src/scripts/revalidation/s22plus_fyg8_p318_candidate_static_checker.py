#!/usr/bin/env python3
"""Independently reconstruct and audit the reproducible P3.18 candidate."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

import build_s22plus_fyg8_p318_candidate as candidate
import s22plus_fyg8_p316_candidate_static_checker as inherited
import s22plus_fyg8_p318_candidate_contract as contract
import s22plus_fyg8_p318_e2_stock_closure as closure
import s22plus_fyg8_p318_overlay_contract as overlay
import s22plus_fyg8_p318_qualification_closure as qualification
import s22plus_fyg8_p318_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p318_candidate_static_checker_v1"
VERDICT = "PASS_P318_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
TARGET = contract.TARGET
EXPECTED_MODULE_PLAN_COUNT = 70
EXPECTED_STOCK_MODULE_COUNT = 69
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
DEFAULT_LATCH = candidate.DEFAULT_LATCH
DEFAULT_DIAGNOSTIC = candidate.DEFAULT_DIAGNOSTIC
DEFAULT_SOURCE = contract.DEFAULT_SOURCE
DEFAULT_INTENT = contract.DEFAULT_INTENT
DEFAULT_PATCH = contract.DEFAULT_PATCH
DEFAULT_QUALIFICATION = qualification.DEFAULT_OUT
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p318/static-check-result.json")
CheckError = inherited.CheckError
util = inherited.base
repo_root = contract.intent.repo_root
stable_read = util.stable_read
ARTIFACT_LIMITS = util.ARTIFACT_LIMITS


def _resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


resolve = _resolve


@contextmanager
def _rootfs_entrypoint_context(payloads: dict[str, bytes]):
    try:
        entrypoints = {
            "init": util.e1_static.inspect_static_elf(
                payloads["init"], "P3.18 exact /init"
            )["entrypoint"],
            "child": util.e1_static.inspect_static_elf(
                payloads["child"], "P3.18 exact child"
            )["entrypoint"],
        }
    except (KeyError, util.e1_static.CheckError) as exc:
        raise CheckError("P3.18 exact userspace entrypoint is invalid") from exc
    if any(
        isinstance(value, bool) or not isinstance(value, int)
        for value in entrypoints.values()
    ):
        raise CheckError("P3.18 exact userspace entrypoint is malformed")
    entrypoint_api = closure.base.P310.parent.p286.p282.p280
    with entrypoint_api._expected_entrypoints(entrypoints):  # noqa: SLF001
        with closure.exact_init_authority(payloads["init"]):
            yield


def _read_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    payload = util.stable_read(path, label, 64 * 1024 * 1024)
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError(f"{label} is not ASCII JSON") from exc
    if not isinstance(value, dict):
        raise CheckError(f"{label} root differs")
    return value, payload


def _candidate_payloads(directory: Path, label: str) -> tuple[dict[str, bytes], dict[str, Any]]:
    if directory.is_symlink() or not directory.is_dir() or {
        path.name for path in directory.iterdir()
    } != {"artifact-result.json", "boot.img", "boot.img.lz4", "odin4"}:
        raise CheckError(f"P3.18 candidate {label} inventory differs")
    odin = directory / "odin4"
    if odin.is_symlink() or not odin.is_dir() or {
        path.name for path in odin.iterdir()
    } != {"AP.tar.md5"}:
        raise CheckError(f"P3.18 candidate {label} Odin inventory differs")
    paths = {
        "artifact_result": directory / "artifact-result.json",
        "boot_img": directory / "boot.img",
        "boot_img_lz4": directory / "boot.img.lz4",
        "ap_tar_md5": odin / "AP.tar.md5",
    }
    payloads = {
        name: util.stable_read(path, f"P3.18 {label} {name}", util.ARTIFACT_LIMITS[name])
        for name, path in paths.items()
    }
    try:
        value = json.loads(payloads["artifact_result"].decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError(f"P3.18 candidate {label} result is invalid") from exc
    if not isinstance(value, dict):
        raise CheckError(f"P3.18 candidate {label} result root differs")
    return payloads, value


def _userspace(root: Path, directory: Path, exact: dict[str, Any]):
    if directory.is_symlink() or not directory.is_dir() or {
        path.name for path in directory.iterdir()
    } != {"init", "s22-e1-child", "userspace-result.json"}:
        raise CheckError("P3.18 userspace inventory differs")
    value, result_payload = _read_json(directory / "userspace-result.json", "P3.18 userspace result")
    if (
        value.get("schema") != userspace.SCHEMA
        or value.get("verdict") != userspace.VERDICT
        or value.get("candidate_contract") != exact
        or value.get("source_contract") != userspace._source_contract(exact)  # noqa: SLF001
        or value.get("two_build_byte_identical") is not True
        or value.get("module_plan_count") != EXPECTED_MODULE_PLAN_COUNT
        or value.get("stock_early_module_count") != EXPECTED_STOCK_MODULE_COUNT
        or value.get("custom_early_module_count") != 1
        or value.get("late_diagnostic_payload_count") != 1
    ):
        raise CheckError("P3.18 userspace result differs")
    init = util.stable_read(directory / "init", "P3.18 exact init", 1024 * 1024)
    child = util.stable_read(directory / "s22-e1-child", "P3.18 exact child", 1024 * 1024)
    for path in (directory / "init", directory / "s22-e1-child"):
        if path.stat(follow_symlinks=False).st_mode & 0o777 != 0o755:
            raise CheckError("P3.18 userspace mode differs")
    if any(
        {
            key: value.get("outputs", {}).get(label, {}).get(key)
            for key in ("size", "sha256")
        }
        != util.receipt(payload)
        for label, payload in (("init", init), ("child", child))
    ):
        raise CheckError("P3.18 userspace receipt differs")
    qemu_path = Path(userspace.base.require_tools()["qemu-aarch64"])
    qemu = util.stable_read(qemu_path, "P3.18 qemu-aarch64", 32 * 1024 * 1024)
    with tempfile.TemporaryDirectory(prefix="s22-p318-child-") as name:
        staged_qemu = Path(name) / "qemu-aarch64"
        staged_child = Path(name) / "s22-e1-child"
        staged_qemu.write_bytes(qemu)
        staged_child.write_bytes(child)
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
        raise CheckError("P3.18 child check failed")
    return (
        {"init": init, "child": child},
        util.receipt(result_payload),
        util.receipt(qemu),
    )


def _exists(magiskboot: Path, ramdisk: Path, member: str, cwd: Path) -> bool:
    completed = subprocess.run(
        [magiskboot, "cpio", ramdisk, f"exists {member}"],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    if completed.returncode not in (0, 1):
        raise CheckError(f"P3.18 static existence check failed: {member}")
    return completed.returncode == 0


def audit(args: argparse.Namespace) -> dict[str, Any]:
    root = contract.intent.repo_root()
    intent_path = _resolve(root, args.intent)
    exact = overlay.verify_intent(root, intent_path)
    qualification_value, qualification_payload = _read_json(
        _resolve(root, args.qualification), "P3.18 final qualification"
    )
    trees = (
        qualification._tree_receipts(_resolve(root, args.candidate)),  # noqa: SLF001
        qualification._tree_receipts(_resolve(root, args.candidate_b)),  # noqa: SLF001
    )
    if trees[0] != trees[1]:
        raise CheckError("P3.18 qualification candidate trees differ")
    qualification.validate_qualification_artifact(
        qualification_value,
        root=root,
        candidate_tree=trees[0],
        intent_path=intent_path,
    )
    prepackaging_receipt = qualification_value.get("prepackaging_receipt")
    if not isinstance(prepackaging_receipt, dict):
        raise CheckError("P3.18 prepackaging receipt is absent")
    userspace_payloads, userspace_result, qemu_receipt = _userspace(
        root, _resolve(root, args.userspace), exact
    )
    image = util.stable_read(
        _resolve(root, args.image), "P3.18 fixed Image",
        candidate.KERNEL_END - candidate.KERNEL_START,
    )
    if util.receipt(image) != overlay.EXPECTED_IMAGE:
        raise CheckError("P3.18 fixed Image differs")
    util.boot_verify.parse_arm64_header(image)
    latch = util.stable_read(_resolve(root, args.latch), "P3.18 latch", 4 * 1024 * 1024)
    diagnostic = util.stable_read(_resolve(root, args.diagnostic), "P3.18 diagnostic", 4 * 1024 * 1024)
    for payload, key in ((latch, "early_latch"), (diagnostic, "late_diagnostic")):
        if util.receipt(payload) != {
            name: exact["module_identities"][key][name]
            for name in ("size", "sha256")
        }:
            raise CheckError(f"P3.18 {key} identity differs")
    plan_header = intent_path.parent / "materialized-sources/s22plus_fyg8_p286_e3_plan.h"
    module_closure = closure.derive_module_closure(
        root,
        _resolve(root, args.vendor_ramdisk),
        _resolve(root, args.lz4),
        plan_header=plan_header,
    )
    if len(module_closure.get("modules", ())) != EXPECTED_STOCK_MODULE_COUNT:
        raise CheckError("P3.18 69-stock module closure differs")
    payloads_a, result_a = _candidate_payloads(_resolve(root, args.candidate), "A")
    payloads_b, result_b = _candidate_payloads(_resolve(root, args.candidate_b), "B")
    if payloads_a != payloads_b or result_a != result_b:
        raise CheckError("P3.18 candidate A/B bytes differ")
    if (
        result_a.get("candidate_contract") != exact
        or result_a.get("module_closure") != module_closure
        or any(
            result_a.get("outputs", {}).get(name) != util.receipt(payloads_a[name])
            for name in ("boot_img", "boot_img_lz4", "ap_tar_md5")
        )
    ):
        raise CheckError("P3.18 candidate artifact result closure differs")
    qualification._validate_candidate_result(  # noqa: SLF001
        result_a, prepackaging_receipt=prepackaging_receipt
    )
    ap_info, ap_frame = util.boot_verify.parse_ap_tar_md5(payloads_a["ap_tar_md5"])
    if ap_frame != payloads_a["boot_img_lz4"] or ap_info["member"]["name"] != "boot.img.lz4":
        raise CheckError("P3.18 AP frame differs")
    base_boot = util.carrier.read_exact_file(
        _resolve(root, args.base_boot), candidate.BOOT_SIZE,
        util.carrier.EXPECTED_BASE_BOOT_SHA256, "P3.18 base boot",
    )
    lz4 = util.carrier.read_exact_file(
        _resolve(root, args.lz4), util.carrier.r4w1b.LZ4_SIZE,
        util.carrier.r4w1b.LZ4_SHA256, "P3.18 lz4",
    )
    magiskboot = util.carrier.read_exact_file(
        _resolve(root, args.magiskboot), util.carrier.MAGISKBOOT_SIZE,
        util.carrier.MAGISKBOOT_SHA256, "P3.18 magiskboot",
    )
    vendor_boot = util.carrier.read_exact_file(
        _resolve(root, args.vendor_boot),
        util.e1_static.base_static.VENDOR_BOOT_SIZE,
        util.e1_static.base_static.VENDOR_BOOT_SHA256,
        "P3.18 vendor_boot",
    )
    effective_rootfs = None
    with tempfile.TemporaryDirectory(prefix="s22-p318-static-") as name:
        work = Path(name)
        tools = work / "tools"
        unpack = work / "userspace-unpack"
        module_unpack = work / "module-unpack"
        final_unpack = work / "final-unpack"
        tools.mkdir(); unpack.mkdir(); module_unpack.mkdir(); final_unpack.mkdir()
        staged = {
            "magiskboot": tools / "magiskboot",
            "lz4": tools / "lz4",
            "base": tools / "base.boot.img",
            "init": tools / "init",
            "child": tools / "s22-e1-child",
            "latch": tools / candidate.LATCH_NAME,
            "diagnostic": tools / candidate.DIAGNOSTIC_NAME,
            "frame": tools / "boot.img.lz4",
            "candidate": tools / "candidate.boot.img",
        }
        for key, payload, executable in (
            ("magiskboot", magiskboot, True), ("lz4", lz4, True),
            ("base", base_boot, False), ("init", userspace_payloads["init"], True),
            ("child", userspace_payloads["child"], True), ("latch", latch, False),
            ("diagnostic", diagnostic, False), ("frame", ap_frame, False),
            ("candidate", payloads_a["boot_img"], False),
        ):
            staged[key].write_bytes(payload)
            staged[key].chmod(0o700 if executable else 0o600)
        roundtrip = tools / "roundtrip.boot.img"
        util.run([staged["lz4"], "-d", "-f", "-q", staged["frame"], roundtrip], work, "P3.18 LZ4 roundtrip")
        if roundtrip.read_bytes() != payloads_a["boot_img"]:
            raise CheckError("P3.18 independent LZ4 roundtrip differs")
        util.run([staged["magiskboot"], "unpack", "-h", staged["base"]], unpack, "P3.18 unpack base")
        ramdisk = unpack / "ramdisk.cpio"
        if any(_exists(staged["magiskboot"], ramdisk, member, unpack) for member in (
            candidate.LATCH_RAMDISK_PATH,
            candidate.DIAGNOSTIC_RAMDISK_PATH,
            candidate.OLD_DIAGNOSTIC_RAMDISK_PATH,
        )):
            raise CheckError("P3.18 base custom module inventory differs")
        for mode, member, source in (
            (750, "init", staged["init"]),
            (750, "s22-e1-child", staged["child"]),
        ):
            util.run([staged["magiskboot"], "cpio", ramdisk, f"add {mode} {member} {source}"], unpack, f"P3.18 independently add {member}")
        userspace_carrier = tools / "userspace.carrier.img"
        util.run([staged["magiskboot"], "repack", staged["base"], userspace_carrier], unpack, "P3.18 independent userspace repack")
        userspace_carrier_bytes = userspace_carrier.read_bytes()
        userspace_candidate = tools / "userspace.candidate.img"
        userspace_candidate.write_bytes(
            userspace_carrier_bytes[:candidate.KERNEL_START]
            + image
            + userspace_carrier_bytes[candidate.KERNEL_END:]
        )
        util.run(
            [staged["magiskboot"], "unpack", "-h", userspace_candidate],
            module_unpack,
            "P3.18 unpack independent userspace candidate",
        )
        module_ramdisk = module_unpack / "ramdisk.cpio"
        if any(_exists(staged["magiskboot"], module_ramdisk, member, module_unpack) for member in (
            candidate.LATCH_RAMDISK_PATH,
            candidate.DIAGNOSTIC_RAMDISK_PATH,
            candidate.OLD_DIAGNOSTIC_RAMDISK_PATH,
        )):
            raise CheckError("P3.18 independent module-stage base differs")
        for member, source in (
            (candidate.LATCH_RAMDISK_PATH, staged["latch"]),
            (candidate.DIAGNOSTIC_RAMDISK_PATH, staged["diagnostic"]),
        ):
            util.run(
                [staged["magiskboot"], "cpio", module_ramdisk, f"add 644 {member} {source}"],
                module_unpack,
                f"P3.18 independently add {member}",
            )
        reconstructed = tools / "reconstructed.boot.img"
        util.run(
            [staged["magiskboot"], "repack", userspace_candidate, reconstructed],
            module_unpack,
            "P3.18 independent module repack",
        )
        expected = reconstructed.read_bytes()
        if expected != payloads_a["boot_img"]:
            raise CheckError("P3.18 candidate differs from independent reconstruction")
        util.run([staged["magiskboot"], "unpack", "-h", staged["candidate"]], final_unpack, "P3.18 unpack candidate")
        final_ramdisk = final_unpack / "ramdisk.cpio"
        expected_members = {
            "init": ("init", userspace_payloads["init"]),
            "child": ("s22-e1-child", userspace_payloads["child"]),
            "latch": (candidate.LATCH_RAMDISK_PATH, latch),
            "diagnostic": (candidate.DIAGNOSTIC_RAMDISK_PATH, diagnostic),
        }
        for label, (member, expected_payload) in expected_members.items():
            target = tools / f"extract.{label}"
            util.run([staged["magiskboot"], "cpio", final_ramdisk, f"extract {member} {target}"], final_unpack, f"P3.18 extract {label}")
            if target.read_bytes() != expected_payload:
                raise CheckError(f"P3.18 extracted {label} differs")
        if _exists(staged["magiskboot"], final_ramdisk, candidate.OLD_DIAGNOSTIC_RAMDISK_PATH, final_unpack):
            raise CheckError("P3.18 old diagnostic survived")
        if (final_unpack / "kernel").read_bytes() != image:
            raise CheckError("P3.18 extracted Image differs")
        try:
            with _rootfs_entrypoint_context(userspace_payloads):
                effective_rootfs = closure.rootfs_audit(
                    payloads_a["boot_img"],
                    vendor_boot,
                    staged["lz4"],
                    expected_init=util.receipt(userspace_payloads["init"]),
                    expected_child=util.receipt(userspace_payloads["child"]),
                    run_id=bytes.fromhex(exact["run_id"]),
                    module_closure=module_closure,
                )
        except closure.ClosureError as exc:
            raise CheckError("P3.18 effective rootfs audit failed") from exc
    inherited.p311_static.p310_static._configure()  # noqa: SLF001
    repro, repro_receipt = inherited.p311_static.verify_repro(root, args, exact)
    if repro.get("verified") is not True:
        raise CheckError("P3.18 fixed Image reproducibility differs")
    if qualification_payload != util.stable_read(
        _resolve(root, args.qualification),
        "P3.18 qualification reread",
        64 * 1024 * 1024,
    ):
        raise CheckError("P3.18 qualification changed during audit")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "candidate_contract": exact,
        "build_repro": {
            "result": repro_receipt,
            "image": util.receipt(image),
            "fresh_reverification": True,
            "two_clean_builds_byte_identical": True,
            "linked_audit_verified": True,
        },
        "candidate": {
            "artifacts": {name: util.receipt(data) for name, data in payloads_a.items()},
            "candidate_b_artifacts": {name: util.receipt(data) for name, data in payloads_b.items()},
            "base_boot": util.receipt(base_boot),
            "ap": ap_info,
            "fixed_interval": {
                "kernel_start": candidate.KERNEL_START,
                "kernel_end_exclusive": candidate.KERNEL_END,
                "header_preserved": True,
                "ramdisk_preserved": True,
                "outside_interval_changed_byte_count": 0,
                "verified": True,
            },
            "userspace": {
                "result": userspace_result,
                "init": util.receipt(userspace_payloads["init"]),
                "child": util.receipt(userspace_payloads["child"]),
                "two_build_byte_identical": True,
                "verified": True,
            },
            "module_closure": module_closure,
            "effective_rootfs": effective_rootfs,
            "stock_vendor_boot": util.receipt(vendor_boot),
            "latch_module": util.receipt(latch),
            "latch_ramdisk_path": candidate.LATCH_RAMDISK_PATH,
            "diagnostic_module": util.receipt(diagnostic),
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
        "p318_runtime_qualification": exact["runtime_qualification"],
        "p318_envelope_qualification": exact["envelope_qualification"],
        "p318_process_v2_adapter_fixture": exact["process_v2_adapter_fixture"],
        "p318_topology_receipt": exact["topology_receipt"],
        "p318_qualification_closure": qualification_value,
        "p318_telemetry": exact["telemetry"],
        "p318_observer": exact["observer"],
        "tools": {
            "lz4": util.receipt(lz4),
            "magiskboot": util.receipt(magiskboot),
            "qemu_aarch64": qemu_receipt,
        },
        "limits": [
            "host-only artifact qualification grants no D0, D1, F1, or live authority",
            "candidate execution and retained observation remain unproved",
        ],
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "flash": False,
            "partition_write": False,
            "manifest_created": False,
            "live_authorized": False,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--candidate-b", type=Path, default=DEFAULT_CANDIDATE_B)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--repro-result", type=Path, default=DEFAULT_REPRO_RESULT)
    parser.add_argument("--userspace", type=Path, default=DEFAULT_USERSPACE)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--vendor-ramdisk", type=Path, default=DEFAULT_VENDOR_RAMDISK)
    parser.add_argument("--vendor-boot", type=Path, default=DEFAULT_VENDOR_BOOT)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--latch", type=Path, default=DEFAULT_LATCH)
    parser.add_argument("--diagnostic", type=Path, default=DEFAULT_DIAGNOSTIC)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--intent", type=Path, default=DEFAULT_INTENT)
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    parser.add_argument("--qualification", type=Path, default=DEFAULT_QUALIFICATION)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        result = audit(args)
        output = _resolve(contract.intent.repo_root(), args.out)
        util.durable_create(
            output,
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode("ascii") + b"\n",
        )
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

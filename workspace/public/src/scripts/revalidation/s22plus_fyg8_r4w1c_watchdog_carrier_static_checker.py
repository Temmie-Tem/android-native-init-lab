#!/usr/bin/env python3
"""Independently qualify two FYG8 R4W1-C watchdog carrier reproductions.

Host-only: no adb, USB enumeration, Odin invocation, or device write exists in
this checker.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import s22plus_boot_verify as verify


SCHEMA = "s22plus_fyg8_r4w1c_watchdog_carrier_static_checker_v1"
VERDICT = "PASS_R4W1C_WATCHDOG_CARRIER_TWO_REPRO_STATIC_CONTRACT"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"

BOOT_SIZE = 100_663_296
KERNEL_START = 4_096
KERNEL_END = 41_495_040
KERNEL_SIZE = KERNEL_END - KERNEL_START

IMAGE_SIZE = KERNEL_SIZE
IMAGE_SHA256 = "350bc71815a7dbf22caf5d42434e4f99ace846329fd11e599b3be2d9c5e080d3"
SOURCE_SIZE = 15_181
SOURCE_SHA256 = "bd75506f821beb26bc1740a016176d9e5b764b2b693c2895af922df9d9e97420"
VENDOR_RAMDISK_SIZE = 21_813_545
VENDOR_RAMDISK_SHA256 = (
    "41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193"
)
LZ4_SIZE = 218_696
LZ4_SHA256 = "91975bf197d485b81475dfa6267aa2284550b844e8e8d64a4e7e35d9a1fa9fb8"
MAGISKBOOT_SIZE = 943_848
MAGISKBOOT_SHA256 = (
    "a18ecbd7981179494b7d281453d6c4e25b5c719e7d2ef7f6eba3c6be3043c58e"
)

CARRIER_SHA256 = "fc10d94eb0e41a97b40d657e320f8f815870a41b7a6b6df0bc7a51b540a2fe57"
CANDIDATE_SHA256 = "1d394028714c48cfc0fd220acade9ead9a49ea21a81c59b2b87f88e61de704b0"
FRAME_SIZE = 27_057_849
FRAME_SHA256 = "abe6b9069b1bfd04c0aeac4b022e367d5d8450101302d623ea2c9efe3b0c0d66"
AP_SIZE = 27_064_361
AP_SHA256 = "85514e79e3400de30b7146606a9e86c3655fc7a8766daba5f054ae1bd54fd42f"
MANIFEST_SIZE = 15_635
MANIFEST_SHA256 = (
    "bfb932fd840104b54d41a957b13d56459c635d8939899c6f50d773aa7474ab76"
)
INIT_SIZE = 65_984
INIT_SHA256 = "6bf7c60ca8f9b9561a9d38f0591028b23291595dd224853015807993ce97703d"

R4W1B_MARKER = (
    b"\n[[S22R4W1B|id=36dc5462adedcf136176f2ddcfee08a8|"
    b"phase=DIRECT_INIT_EXEC_ACCEPTED|pid=1|path=/init]]\n"
)
R4W1B_FAMILY = b"[[S22R4W1B|"

MODULE_SPECS = [
    (
        "smem.ko",
        "smem",
        28_704,
        "27a80d5598329d6a526384d09806de63983204988748ea4e7d3fccfafc24a524",
    ),
    (
        "minidump.ko",
        "minidump",
        37_312,
        "e5e6f4dfe1ddac2cd4f8d15c11a50d4d32b6e9de278fedbed44747630a5c554d",
    ),
    (
        "qcom-scm.ko",
        "qcom_scm",
        218_384,
        "e12ba8661808c2c47acf42c9939157e509fcdb5b98f6e650f79b92dba18a1af3",
    ),
    (
        "qcom_wdt_core.ko",
        "qcom_wdt_core",
        48_640,
        "ef484fb4f1f17586ff63852e0ea9579d07f275f7966ad117d20039055c2d7599",
    ),
    (
        "gh_virt_wdt.ko",
        "gh_virt_wdt",
        18_944,
        "f030c5486a41b1fbe4b0ea3aa85a401dd16daa1f1a551a626f6ea424ee90dd39",
    ),
]
FORBIDDEN_MODULES = {
    "qcom_soc_wdt.ko",
    "sec_qc_qcom_wdt_core.ko",
    "phy-msm-ssusb-qmp.ko",
    "dwc3-msm.ko",
    "usb_f_ss_acm.ko",
    "eud.ko",
}

DEFAULT_REPRO_A = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1c_watchdog_carrier/reproduction-h"
)
DEFAULT_REPRO_B = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1c_watchdog_carrier/reproduction-i"
)
DEFAULT_IMAGE = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1b_candidate_inputs/Image"
)
DEFAULT_SOURCE = Path(
    "workspace/public/src/native-init/s22plus_init_r4w1c_wdt_carrier.c"
)
DEFAULT_VENDOR_RAMDISK = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/unpack-vendor-boot/vendor_ramdisk00"
)
DEFAULT_LZ4 = Path(
    "workspace/private/work/s22plus_fyg8_kernel_rebuild_r0/kernel_platform/"
    "prebuilts/kernel-build-tools/linux-x86/bin/lz4"
)
DEFAULT_MAGISKBOOT = Path("workspace/private/tools/magisk-v30.7/magiskboot")
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1c_watchdog_carrier/"
    "static-check-result-v3.json"
)


class CheckError(ValueError):
    """A fail-closed static qualification error."""


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise CheckError("repository root not found")


def resolve(root: Path, value: Path) -> Path:
    candidate = value if value.is_absolute() else root / value
    return Path(os.path.abspath(candidate))


def read_pinned(
    path: Path, size: int, digest: str, label: str
) -> tuple[dict[str, Any], bytes]:
    try:
        return verify.read_pinned_stable(path, size, digest, label)
    except verify.BootVerifyError as exc:
        raise CheckError(str(exc)) from exc


def run(
    argv: list[str | Path],
    *,
    cwd: Path | None = None,
    input_bytes: bytes | None = None,
    timeout: int = 180,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(part) for part in argv],
        cwd=cwd,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def require_ok(result: subprocess.CompletedProcess[bytes], label: str) -> None:
    if result.returncode != 0:
        output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        raise CheckError(f"{label} failed rc={result.returncode}: {output}")


def stage_file(path: Path, data: bytes, *, executable: bool = False) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(path, flags, 0o700 if executable else 0o400)
    try:
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                raise CheckError(f"short write while staging {path.name}")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def module_basename(value: str) -> str:
    return value.rsplit("/", 1)[-1]


def nonempty_lines(value: str) -> list[str]:
    return [
        line.strip()
        for line in value.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def derive_module_closure(
    vendor_ramdisk: Path, lz4_tool: Path
) -> dict[str, Any]:
    _vendor_receipt, vendor_data = read_pinned(
        vendor_ramdisk,
        VENDOR_RAMDISK_SIZE,
        VENDOR_RAMDISK_SHA256,
        "FYG8 vendor ramdisk",
    )
    decompressed = run([lz4_tool, "-dc"], input_bytes=vendor_data)
    require_ok(decompressed, "independent vendor ramdisk decompression")
    metadata_paths = [
        "lib/modules/modules.dep",
        "lib/modules/modules.load.recovery",
    ]
    module_paths = [f"lib/modules/{spec[0]}" for spec in MODULE_SPECS]
    with tempfile.TemporaryDirectory(prefix="s22-r4w1c-vendor-audit-") as temporary:
        directory = Path(temporary)
        extracted = run(
            [
                "cpio",
                "-id",
                "--no-absolute-filenames",
                *metadata_paths,
                *module_paths,
            ],
            cwd=directory,
            input_bytes=decompressed.stdout,
        )
        require_ok(extracted, "independent watchdog metadata extraction")
        dep_lines = nonempty_lines(
            (directory / metadata_paths[0]).read_text(
                encoding="utf-8", errors="strict"
            )
        )
        recovery = [
            module_basename(value)
            for value in nonempty_lines(
                (directory / metadata_paths[1]).read_text(
                    encoding="utf-8", errors="strict"
                )
            )
        ]
        dependency_map: dict[str, list[str]] = {}
        for line in dep_lines:
            left, separator, right = line.partition(":")
            name = module_basename(left.strip())
            if separator != ":" or not name or name in dependency_map:
                raise CheckError("malformed or duplicate modules.dep entry")
            dependency_map[name] = [
                module_basename(item) for item in right.split()
            ]
        order = {name: index for index, name in enumerate(recovery)}
        visiting: set[str] = set()
        visited: set[str] = set()
        derived: list[str] = []

        def visit(name: str) -> None:
            if name in visited:
                return
            if name in visiting or name not in dependency_map:
                raise CheckError(f"invalid watchdog dependency: {name}")
            if name in FORBIDDEN_MODULES:
                raise CheckError(f"forbidden watchdog dependency: {name}")
            visiting.add(name)
            dependencies = sorted(
                dependency_map[name], key=lambda item: (order.get(item, 10**9), item)
            )
            for dependency in dependencies:
                visit(dependency)
            visiting.remove(name)
            visited.add(name)
            derived.append(name)

        visit("gh_virt_wdt.ko")
        expected = [spec[0] for spec in MODULE_SPECS]
        if derived != expected:
            raise CheckError(f"independent watchdog closure drifted: {derived}")

        modules: list[dict[str, Any]] = []
        for file_name, runtime_name, size, digest in MODULE_SPECS:
            path = directory / "lib/modules" / file_name
            receipt, _data = read_pinned(
                path, size, digest, f"independent module {file_name}"
            )
            modinfo = run(["modinfo", "-F", "name", path])
            require_ok(modinfo, f"independent modinfo {file_name}")
            observed_name = modinfo.stdout.decode("ascii", errors="strict").strip()
            if observed_name != runtime_name:
                raise CheckError(f"module runtime name drifted: {file_name}")
            modules.append(
                {
                    "file": file_name,
                    "runtime": runtime_name,
                    **receipt,
                }
            )
    return {
        "files": derived,
        "runtime_names": [spec[1] for spec in MODULE_SPECS],
        "count": len(derived),
        "modules": modules,
        "derived_independently": True,
    }


def compile_expected_init(source: Path) -> tuple[dict[str, Any], bytes]:
    _source_receipt, source_data = read_pinned(
        source, SOURCE_SIZE, SOURCE_SHA256, "R4W1-C PID1 source"
    )
    with tempfile.TemporaryDirectory(prefix="s22-r4w1c-init-audit-") as temporary:
        directory = Path(temporary)
        staged_source = directory / "s22plus_init_r4w1c_wdt_carrier.c"
        output = directory / "init"
        stage_file(staged_source, source_data)
        result = run(
            [
                "aarch64-linux-gnu-gcc",
                "-nostdlib",
                "-static",
                "-ffreestanding",
                "-fno-builtin",
                "-fno-stack-protector",
                "-fno-asynchronous-unwind-tables",
                "-fno-unwind-tables",
                "-Os",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-Wl,--build-id=none",
                "-Wl,-e,_start",
                "-Wl,-z,noexecstack",
                "-o",
                output,
                staged_source,
            ]
        )
        require_ok(result, "independent R4W1-C init compilation")
        require_ok(
            run(["aarch64-linux-gnu-strip", "-s", output]),
            "independent R4W1-C init strip",
        )
        data = output.read_bytes()
    digest = verify.sha256_bytes(data)
    if len(data) != INIT_SIZE or digest != INIT_SHA256:
        raise CheckError(f"independently compiled init mismatch: {len(data)} {digest}")
    required = (
        b"S22_NATIVE_INIT_R4W1C_WDT_CARRIER",
        b"exact_finit_rc=0",
        b"proc_modules_exact=1",
        b"phase=module_load_complete count=5",
        b"phase=proc_modules_verified count=5 exact=1",
        b"phase=park_enter",
        b"module_closure_visible=1",
        b"watchdog_ownership=not_directly_proven",
        b"functional_proof=bounded_live_survival",
    )
    if any(value not in data for value in required):
        raise CheckError("independently compiled init lacks runtime contract")
    forbidden = (
        b"/dev/block",
        b"/config",
        b"usb_gadget",
        b"ttyGS0",
        b"reboot_request=download",
        b"/system/bin/init",
    )
    if any(value in data for value in forbidden):
        raise CheckError("independently compiled init has forbidden capability")
    return {"size": len(data), "sha256": digest}, data


def validate_manifest(encoded: bytes) -> dict[str, Any]:
    try:
        data = json.loads(encoded.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError("invalid R4W1-C manifest JSON") from exc
    expected_top = {
        "schema": "s22plus_fyg8_r4w1c_watchdog_carrier_build_v1",
        "target": TARGET,
        "rung": "R4W1-C",
        "verdict": "PASS_R4W1C_WATCHDOG_CARRIER_BUILT_HOST_ONLY",
        "blockers": [
            "independent static checker not yet passed",
            "no connected read-only gate or live policy exists",
        ],
    }
    for key, expected in expected_top.items():
        if data.get(key) != expected:
            raise CheckError(f"manifest top-level mismatch: {key}")
    expected_outputs = {
        "carrier_boot": {"size": BOOT_SIZE, "sha256": CARRIER_SHA256},
        "boot_img": {"size": BOOT_SIZE, "sha256": CANDIDATE_SHA256},
        "boot_img_lz4": {"size": FRAME_SIZE, "sha256": FRAME_SHA256},
        "ap_tar_md5": {"size": AP_SIZE, "sha256": AP_SHA256},
    }
    for key, expected in expected_outputs.items():
        if data.get("outputs", {}).get(key) != expected:
            raise CheckError(f"manifest output mismatch: {key}")
    if data.get("outputs", {}).get("init", {}).get("sha256") != INIT_SHA256:
        raise CheckError("manifest init hash mismatch")
    closure = data.get("module_closure", {})
    if closure.get("files") != [spec[0] for spec in MODULE_SPECS]:
        raise CheckError("manifest module filenames mismatch")
    if closure.get("runtime_names") != [spec[1] for spec in MODULE_SPECS]:
        raise CheckError("manifest runtime module names mismatch")
    runtime = data.get("runtime_contract", {})
    required_runtime = {
        "finit_module_success_required": True,
        "proc_modules_eof_complete": True,
        "proc_modules_exact_set_required": True,
        "park_only_after_module_visibility_verification": True,
        "module_closure_load_and_visibility_only": True,
        "watchdog_functional_ownership_directly_proven": False,
        "watchdog_functional_proof_required": "bounded live survival",
        "observation_target_sec": 120,
    }
    if any(runtime.get(key) != value for key, value in required_runtime.items()):
        raise CheckError("manifest runtime contract mismatch")
    required_safety = {
        "host_only": True,
        "device_contact": False,
        "device_write": False,
        "odin_invoked": False,
        "odin_transfer": False,
        "flash": False,
        "live_authorized": False,
        "boot_only_ap": True,
        "ap_members": ["boot.img.lz4"],
        "no_android_handoff": True,
        "no_usb_or_configfs": True,
        "no_persistent_mount": True,
        "no_block_write": True,
        "no_reboot_syscall": True,
        "requires_new_committed_live_policy": True,
    }
    safety = data.get("safety", {})
    if any(safety.get(key) != value for key, value in required_safety.items()):
        raise CheckError("manifest safety contract mismatch")
    if data.get("construction", {}).get("kernel_witness_preserved") is not True:
        raise CheckError("manifest does not preserve the kernel witness")
    return {
        "schema": data["schema"],
        "verdict": data["verdict"],
        "consistent": True,
    }


def extract_final_init(
    magiskboot: Path, candidate: bytes
) -> tuple[dict[str, Any], bytes]:
    with tempfile.TemporaryDirectory(prefix="s22-r4w1c-boot-audit-") as temporary:
        directory = Path(temporary)
        boot_path = directory / "boot.img"
        boot_path.write_bytes(candidate)
        unpack = run([magiskboot, "unpack", "-h", boot_path], cwd=directory)
        require_ok(unpack, "independent final boot unpack")
        ramdisk = (directory / "ramdisk.cpio").read_bytes()
    entries = verify.parse_newc(ramdisk)
    matching = [entry for entry in entries if entry.name == "init"]
    if len(matching) != 1:
        raise CheckError(f"final ramdisk requires one init, got {len(matching)}")
    init = matching[0]
    if init.file_type != "regular" or (init.mode & 0o7777) != 0o750:
        raise CheckError("final ramdisk /init type or mode mismatch")
    names = {entry.name for entry in entries}
    if "s22plus_m31b_wdt_managed.modules" in names:
        raise CheckError("legacy external module list leaked into R4W1-C ramdisk")
    return {
        "ramdisk_size": len(ramdisk),
        "ramdisk_sha256": verify.sha256_bytes(ramdisk),
        "entry_count": len(entries),
        "init": init.summary(),
        "legacy_module_list_absent": True,
    }, init.data


def inspect_reproduction(
    directory: Path,
    image: bytes,
    lz4_tool: Path,
    magiskboot: Path,
    expected_init: bytes,
) -> dict[str, Any]:
    carrier_receipt, carrier = read_pinned(
        directory / "carrier.boot.img",
        BOOT_SIZE,
        CARRIER_SHA256,
        "R4W1-C carrier boot",
    )
    candidate_receipt, candidate = read_pinned(
        directory / "boot.img",
        BOOT_SIZE,
        CANDIDATE_SHA256,
        "R4W1-C candidate boot",
    )
    frame_receipt, frame = read_pinned(
        directory / "boot.img.lz4",
        FRAME_SIZE,
        FRAME_SHA256,
        "R4W1-C LZ4 frame",
    )
    ap_receipt, ap = read_pinned(
        directory / "odin4/AP.tar.md5",
        AP_SIZE,
        AP_SHA256,
        "R4W1-C boot-only AP",
    )
    manifest_receipt, manifest = read_pinned(
        directory / "manifest.json",
        MANIFEST_SIZE,
        MANIFEST_SHA256,
        "R4W1-C manifest",
    )
    init_receipt, built_init = read_pinned(
        directory / "build/s22plus_init_r4w1c_wdt_carrier",
        INIT_SIZE,
        INIT_SHA256,
        "R4W1-C built init",
    )
    if built_init != expected_init:
        raise CheckError("built init differs from independent compilation")
    expected_candidate = carrier[:KERNEL_START] + image + carrier[KERNEL_END:]
    if candidate != expected_candidate:
        raise CheckError("candidate differs from independent fixed-slice construction")
    boot = verify.parse_boot_v4(candidate)
    if boot.kernel != image:
        raise CheckError("parsed candidate kernel differs from qualified Image")
    marker = verify.sha256_bytes(R4W1B_MARKER)
    if (
        image.count(R4W1B_MARKER) != 1
        or image.count(R4W1B_FAMILY) != 1
        or candidate.count(R4W1B_MARKER) != 1
        or candidate.count(R4W1B_FAMILY) != 1
    ):
        raise CheckError("R4W1-B kernel witness cardinality mismatch")
    ap_structure, ap_frame = verify.parse_ap_tar_md5(ap)
    if ap_frame != frame:
        raise CheckError("AP member differs from standalone LZ4 frame")
    frame_structure = verify.parse_lz4_frame(frame)
    decoded = verify.decompress_lz4(lz4_tool, frame, BOOT_SIZE)
    if decoded != candidate:
        raise CheckError("LZ4 roundtrip differs from candidate")
    ramdisk_receipt, final_init = extract_final_init(magiskboot, candidate)
    if final_init != expected_init:
        raise CheckError("final boot ramdisk init differs from independent build")
    return {
        "directory": directory.name,
        "carrier": carrier_receipt,
        "candidate": candidate_receipt,
        "frame": frame_receipt,
        "ap": ap_receipt,
        "manifest": {**manifest_receipt, **validate_manifest(manifest)},
        "init": init_receipt,
        "boot_v4": boot.header,
        "kernel_witness": {
            "marker_sha256": marker,
            "exact_count": 1,
            "family_count": 1,
        },
        "ap_structure": ap_structure,
        "frame_structure": frame_structure,
        "ramdisk": ramdisk_receipt,
        "fixed_slice_exact": True,
        "lz4_roundtrip_exact": True,
    }


def check(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    repro_a = resolve(root, args.repro_a)
    repro_b = resolve(root, args.repro_b)
    image_path = resolve(root, args.image)
    source = resolve(root, args.source)
    vendor_ramdisk = resolve(root, args.vendor_ramdisk)
    lz4_tool = resolve(root, args.lz4)
    magiskboot = resolve(root, args.magiskboot)

    _image_receipt, image = read_pinned(
        image_path, IMAGE_SIZE, IMAGE_SHA256, "qualified R4W1-B Image"
    )
    _lz4_receipt, lz4_data = read_pinned(
        lz4_tool, LZ4_SIZE, LZ4_SHA256, "pinned lz4"
    )
    _magiskboot_receipt, magiskboot_data = read_pinned(
        magiskboot,
        MAGISKBOOT_SIZE,
        MAGISKBOOT_SHA256,
        "pinned magiskboot",
    )
    init_receipt, expected_init = compile_expected_init(source)
    with tempfile.TemporaryDirectory(prefix="s22-r4w1c-tools-audit-") as temporary:
        tool_dir = Path(temporary)
        staged_lz4 = tool_dir / "lz4"
        staged_magiskboot = tool_dir / "magiskboot"
        stage_file(staged_lz4, lz4_data, executable=True)
        stage_file(staged_magiskboot, magiskboot_data, executable=True)
        module_closure = derive_module_closure(vendor_ramdisk, staged_lz4)
        reproductions = [
            inspect_reproduction(
                directory,
                image,
                staged_lz4,
                staged_magiskboot,
                expected_init,
            )
            for directory in (repro_a, repro_b)
        ]
    comparable_keys = (
        "carrier",
        "candidate",
        "frame",
        "ap",
        "manifest",
        "init",
        "kernel_witness",
        "ap_structure",
        "frame_structure",
        "ramdisk",
    )
    for key in comparable_keys:
        if reproductions[0][key] != reproductions[1][key]:
            raise CheckError(f"reproductions differ: {key}")
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "reproductions": reproductions,
        "module_closure": module_closure,
        "independent_init": init_receipt,
        "reproducible": True,
        "device_contact": False,
        "device_write": False,
        "odin_invoked": False,
        "flash": False,
        "live_authorized": False,
        "blockers": [
            "no connected read-only gate exists",
            "no committed one-shot live policy exists",
        ],
        "verdict": VERDICT,
    }


def write_result(path: Path, result: dict[str, Any]) -> None:
    encoded = (
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("ascii")
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        offset = 0
        while offset < len(encoded):
            offset += os.write(descriptor, encoded[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    parent = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repro-a", type=Path, default=DEFAULT_REPRO_A)
    parser.add_argument("--repro-b", type=Path, default=DEFAULT_REPRO_B)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument(
        "--vendor-ramdisk", type=Path, default=DEFAULT_VENDOR_RAMDISK
    )
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--stdout-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = check(args)
        if not args.stdout_only:
            write_result(resolve(repo_root(), args.out), result)
    except (
        CheckError,
        verify.BootVerifyError,
        OSError,
        subprocess.SubprocessError,
        UnicodeError,
    ) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)},
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "verdict": result["verdict"],
                "reproducible": result["reproducible"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

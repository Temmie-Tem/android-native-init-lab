#!/usr/bin/env python3
"""Build and audit the bounded FYG8 Max77705 MUX diagnostic module.

This helper is host-only.  It reconstructs the exact P3.10 external-module
ABI from the preserved source tree, P3.10 patch, fixed A/B ``.config`` and
``vmlinux.symvers`` artifacts, and the Android clang toolchain.  It builds the
same external module twice at one path and then audits the linked ELF surface.

It does not package a boot image, alter a candidate, or contact a device.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "s22plus_fyg8_max77705_mux_diag_build_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"

BASE_WORK_TREE = Path(
    "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae"
)
BASE_COMMON = BASE_WORK_TREE / "kernel_platform/common"
BASE_BUILD = BASE_WORK_TREE / "kernel_platform/build"
BASE_ARCHIVE = Path(
    "workspace/private/inputs/s22plus_kernel_source/"
    "SM-S906N_15_base_osrc/Kernel.tar.gz"
)
DELTA_ARCHIVE = Path(
    "workspace/private/inputs/s22plus_kernel_source/"
    "S906NKSS7FYG8_osrc/S906NKSS7FYG8_kernel.tar.gz"
)
OVERLAY_AUDIT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_kernel_overlay_audit.py"
)
P310_PATCH = Path("workspace/private/outputs/s22plus_fyg8_p310/intent/candidate.patch")
P310_FIXED_A = Path("workspace/private/outputs/s22plus_fyg8_p310/immutable-a-v6")
P310_FIXED_B = Path("workspace/private/outputs/s22plus_fyg8_p310/immutable-b-v6")
MODULE_SOURCE_DIR = Path(
    "workspace/public/src/kernel-modules/s22plus_max77705_mux_diag"
)
SOURCE_CONTRACT_HELPER = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_max77705_custom_surface_contract.py"
)
TOOLCHAIN = Path(
    "workspace/private/work/toolchains/aosp-clang-android12-release/"
    "clang-r416183b"
)

DEFAULT_OUTPUT_DIR = Path(
    "workspace/private/outputs/s22plus_fyg8_max77705_gate0/"
    "custom-module-build-20260812-07"
)

SOURCE_DATE_EPOCH = "1754027756"
STOCK_TIMESTAMP = "Fri Aug 1 05:55:56 UTC 2025"
STOCK_LOCALVERSION = "-30958166-abS906NKSS7FYG8"
STOCK_KERNEL_RELEASE = "5.10.226-android12-9-30958166-abS906NKSS7FYG8"
EXPECTED_VERMAGIC = (
    STOCK_KERNEL_RELEASE + " SMP preempt mod_unload modversions aarch64"
)
MIN_FREE_BYTES = 4 * 1024**3

BASE_SOURCE_MANIFEST_IDENTITY = (
    2_042,
    "98edbcdbdefbf0736c2bdb5ed88947d78d7d78c9921fd9a242194a39d2a31b3a",
)
BASE_SOURCE_MANIFEST = Path(
    "workspace/private/outputs/s22plus_fyg8_p290/full-lto-2ec2bbae-v1/"
    "preflight-a/source-overlay-audit/manifest.json"
)
EXPECTED_FINAL_MEMBERS_SHA256 = (
    "946789ba7bae742893e2b9e94db76614775ce770e04aaeb4254c960c907f0b58"
)
OVERLAY_AUDIT_SHA256 = (
    "61a07c07aea3df5000cf8bb45f874d73dde20ea7509184a419ce5f77760d2556"
)
BASE_ARCHIVE_IDENTITY = (
    566_244_738,
    "86e2f73412c65fadff0b15bbf0eac9140610f70250514ac0bddbf3b53fb5f7bf",
)
DELTA_ARCHIVE_IDENTITY = (
    1_421_025,
    "23ef2b27de8843e271d41405b3c0b1a71bfa668615c8f0f12a1e5c4395ec851a",
)
P310_PATCH_IDENTITY = (
    42_020,
    "7199cb454fcea31f3fe1289586eb2c3423959876e97b2041957ac892753ddc93",
)
MODULE_SOURCE_IDENTITIES = {
    "Makefile": (
        59,
        "fd9878269e29f517f685ed8643682190419ab537eefaf1a930a1196409dea1ab",
    ),
    "s22plus_max77705_mux_diag.c": (
        11_470,
        "2cdc1e58bc77d804f61cd7e5e4efeb1bfa6fd285b7e7160b6d834cc9dc741f24",
    ),
}

FIXED_ABI_IDENTITIES = {
    ".config": (
        185_508,
        "6adf58c7204695e6f5a8deaf0f5995bca91a79ce4cc5f7b74e7b247128e0673b",
    ),
    "vmlinux.symvers": (
        439_646,
        "fd75413401617a427ddf6c264d0ae4f5452b46cde02b4575b9af09f19601ca19",
    ),
    "vmlinux": (
        479_162_024,
        "5635ccdbb2c79a7dc0457b91c76833ffd4f36e8558d0081d50a829629e5a4a1d",
    ),
    "Image": (
        41_490_944,
        "9c2115bb8cd396d0396490c737b39713abdeac311d2ba49679a1bacd9a41e609",
    ),
}

BASE_PATCHED_FILES = {
    "arch/arm64/configs/gki_defconfig": (
        "12661b7d249fb8f80135c3fdcd331733b86d5215f2f4e88e356d1516831ab493",
        "0d4c366a500aae1364a2e00fc74f6a742c18bb937a644dbc1fa1a295d6842432",
    ),
    "init/Kconfig": (
        "8273d233a441c21df2fcb1d5d17a590321d758205fd5babd8b8dcb4e6a334019",
        "2a0c7a293f46532916b185b21a6ff07252116a329a8738c3ee33312876a59122",
    ),
    "init/main.c": (
        "7d281c86ca63646083b9f489eed28281c7d2518f397f34ceccf34c223eaa663a",
        "a3287a4c36da19abbb0a0323b9a92c123f8091ea170a511669566f0e41f2d612",
    ),
    "drivers/usb/dwc3/gadget.c": (
        "c121003d37f4fc9ab951f5d8811fe32736b21dadab985214996606578160c730",
        "a08c37921fdcd95895a19ee7e1524b17da5e6165a8369f666f7932e309c93717",
    ),
}

# The exact P3.10 build predates five later additions now present in the
# resident build.config.gki.aarch64.  Re-derive the fixed whitelist from the
# 25 source lists actually represented by the preserved P3.10 raw list.
KMI_SYMBOL_LISTS = (
    "abi_gki_aarch64",
    "abi_gki_aarch64_type_visibility",
    "abi_gki_aarch64_arg",
    "abi_gki_aarch64_core",
    "abi_gki_aarch64_db845c",
    "abi_gki_aarch64_exynos",
    "abi_gki_aarch64_exynosauto",
    "abi_gki_aarch64_fips140",
    "abi_gki_aarch64_galaxy",
    "abi_gki_aarch64_generic",
    "abi_gki_aarch64_hikey960",
    "abi_gki_aarch64_honor",
    "abi_gki_aarch64_imx",
    "abi_gki_aarch64_lenovo",
    "abi_gki_aarch64_moto",
    "abi_gki_aarch64_mtk",
    "abi_gki_aarch64_nothing",
    "abi_gki_aarch64_oplus",
    "abi_gki_aarch64_qcom",
    "abi_gki_aarch64_rockchip",
    "abi_gki_aarch64_unisoc",
    "abi_gki_aarch64_virtual_device",
    "abi_gki_aarch64_vivo",
    "abi_gki_aarch64_xiaomi",
    "abi_gki_aarch64_zebra",
)
COMBINED_KMI_IDENTITY = (
    828_087,
    "7f2920be349931527c84efe360fae4f8e43d2347f55988e70c41f8b10a2aee17",
)
RAW_KMI_IDENTITY = (
    162_294,
    "d8589008b44105c76eb33fd76d7063830070bbf3986d6090e48175f1d1709fd0",
)
RAW_KMI_LINES = 6_958

TOOL_IDENTITIES = {
    "clang": "b2ce016755bddbab76549895bca07b1dc8d14a3e315b8b3567097fef04eadae1",
    "lld": "51dc9705420c136f583478ac08a3258cd970710296928b3bf24dc3ee2e6208e3",
    "llvm-nm": "29eaac8489f8251a486ddd2ead349c037bcd1c2a066de533279e4bbb8f3f2f05",
    "llvm-objcopy": "92073832011b5611bc08d85ef4a9c59a101e344803a2e8fa087f23dfc86da448",
    "llvm-objdump": "4514d38133823efefc7c35bad3c6fa462422becc8af694232fe638ea29ac9051",
    "llvm-readobj": "7dba5d36ce452e63910e21540c86f9b021a321695fd47e35ee2c98b47186cdba",
}

EXPECTED_UNDEFINED = frozenset(
    {
        "__stack_chk_fail",
        "__stack_chk_guard",
        "arm64_const_caps_ready",
        "bin2hex",
        "cpu_hwcap_keys",
        "devm_i2c_new_dummy_device",
        "i2c_del_driver",
        "i2c_register_driver",
        "i2c_smbus_read_byte_data",
        "i2c_smbus_read_i2c_block_data",
        "i2c_smbus_write_byte_data",
        "i2c_smbus_write_i2c_block_data",
        "msleep",
        "scnprintf",
        "usleep_range",
    }
)
EXPECTED_CALL_RELOCATIONS = {
    "bin2hex": 4,
    "devm_i2c_new_dummy_device": 1,
    "i2c_del_driver": 1,
    "i2c_register_driver": 1,
    "i2c_smbus_read_byte_data": 6,
    "i2c_smbus_read_i2c_block_data": 1,
    "i2c_smbus_write_byte_data": 2,
    "i2c_smbus_write_i2c_block_data": 2,
    "msleep": 1,
    "scnprintf": 6,
    "usleep_range": 2,
}
EXPECTED_MODINFO = {
    "description": ["Bounded S22+ Max77705 CONTROL1 MUX diagnostic"],
    "license": ["GPL v2"],
    "depends": [""],
    "name": ["s22plus_max77705_mux_diag"],
    "vermagic": [EXPECTED_VERMAGIC],
    "parm": ["result:cached bounded Max77705 MUX diagnostic result"],
}

PROTOCOL_SOURCE_IDENTITIES = {
    "usbc": (
        Path("kernel_platform/msm-kernel/drivers/usb/typec/maxim/max77705_usbc.c"),
        124_569,
        "4dabc4b25e99e26c662748934a6a98775073683832f08652e15762f4689a3e3d",
    ),
    "muic": (
        Path("kernel_platform/msm-kernel/drivers/usb/typec/maxim/max77705-muic.c"),
        76_141,
        "bfdb034d7571ca233202221cdc8cdfe68bab3e837afea9c4b5a37378ed7acbab",
    ),
    "muic_header": (
        Path("kernel_platform/msm-kernel/include/linux/usb/typec/maxim/max77705-muic.h"),
        13_948,
        "3f7f2b9790940d61ec6bb636f87fd750f7971f1c609c06e6380d11907f701cb1",
    ),
    "register_header": (
        Path("kernel_platform/msm-kernel/include/linux/usb/typec/maxim/max77705.h"),
        13_686,
        "ff2498061ddb20c1891cb9fe6611edde655c3e1cda8fa4446d0c876a476ff1c7",
    ),
}


class BuildError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "AGENTS.md").is_file() and (parent / "GOAL.md").is_file():
            return parent
    raise BuildError("repository root not found")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (root / path).resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_file(path: Path, identity: tuple[int, str], label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise BuildError(f"{label} is missing or not a regular file: {path}")
    actual = (path.stat().st_size, sha256_file(path))
    if actual != identity:
        raise BuildError(f"{label} identity mismatch: {actual} != {identity}")
    return {"path": str(path), "size": actual[0], "sha256": actual[1]}


def validate_precompile_source_contract(root: Path) -> dict[str, Any]:
    helper_path = resolve(root, SOURCE_CONTRACT_HELPER)
    if not helper_path.is_file() or helper_path.is_symlink():
        raise BuildError(f"source-contract helper is missing or non-regular: {helper_path}")
    source_path = resolve(root, MODULE_SOURCE_DIR) / "s22plus_max77705_mux_diag.c"
    helper_name = "s22plus_fyg8_max77705_precompile_source_contract"
    script_dir = str(helper_path.parent)
    sys.path.insert(0, script_dir)
    try:
        spec = importlib.util.spec_from_file_location(helper_name, helper_path)
        if spec is None or spec.loader is None:
            raise BuildError("cannot load source-contract helper")
        helper = importlib.util.module_from_spec(spec)
        sys.modules[helper_name] = helper
        spec.loader.exec_module(helper)
        validator = helper.validate_diag_source_text
        validation = validator(source_path.read_text(encoding="utf-8"))
        function_text = inspect.getsource(validator).encode("utf-8")
    except (AttributeError, UnicodeDecodeError, ValueError) as error:
        raise BuildError(f"precompile source-contract validation failed: {error}") from error
    finally:
        sys.modules.pop(helper_name, None)
        sys.path.remove(script_dir)
    if validation.get("source_contract_satisfied") is not True:
        raise BuildError("precompile source-contract validator did not pass")
    return {
        "verified_before_compile": True,
        "helper": {
            "path": str(helper_path),
            "size": helper_path.stat().st_size,
            "sha256": sha256_file(helper_path),
        },
        "validator_function_sha256": hashlib.sha256(function_text).hexdigest(),
        "module_source_sha256": sha256_file(source_path),
        "validation": validation,
    }


def run_checked(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    if stdout_path is None and stderr_path is None:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    else:
        if stdout_path is None or stderr_path is None:
            raise BuildError("both command log paths are required")
        with stdout_path.open("w", encoding="utf-8") as stdout_log, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr_log:
            completed = subprocess.run(
                command,
                cwd=cwd,
                env=env,
                text=True,
                stdout=stdout_log,
                stderr=stderr_log,
                check=False,
            )
    if completed.returncode != 0:
        detail = ""
        if stderr_path is not None and stderr_path.is_file():
            detail = stderr_path.read_text(errors="replace")[-4000:]
        elif completed.stderr:
            detail = completed.stderr[-4000:]
        raise BuildError(f"command failed rc={completed.returncode}: {command}: {detail}")
    return completed


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="ascii", dir=path.parent, delete=False
    ) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def parse_symvers(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in text.splitlines():
        fields = raw.split("\t")
        if len(fields) < 4 or not re.fullmatch(r"0x[0-9a-fA-F]{8}", fields[0]):
            raise BuildError(f"malformed vmlinux.symvers row: {raw!r}")
        crc, symbol = fields[0].lower(), fields[1]
        if symbol in result:
            raise BuildError(f"duplicate vmlinux.symvers symbol: {symbol}")
        result[symbol] = crc
    if not result:
        raise BuildError("empty vmlinux.symvers")
    return result


def parse_modversions(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in text.splitlines():
        fields = raw.split()
        if len(fields) != 2 or not re.fullmatch(r"0x[0-9a-fA-F]{8}", fields[0]):
            raise BuildError(f"malformed module version row: {raw!r}")
        crc, symbol = fields[0].lower(), fields[1]
        if symbol in result:
            raise BuildError(f"duplicate module version symbol: {symbol}")
        result[symbol] = crc
    if not result:
        raise BuildError("module has no modversions")
    return result


def parse_modinfo(text: str) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for raw in text.splitlines():
        key, separator, value = raw.partition(":")
        if separator:
            fields.setdefault(key.strip(), []).append(value.strip())
    return fields


def parse_undefined_symbols(text: str) -> frozenset[str]:
    result = set()
    for raw in text.splitlines():
        fields = raw.split()
        if fields:
            result.add(fields[-1])
    return frozenset(result)


def parse_defined_symbols(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for raw in text.splitlines():
        fields = raw.split()
        if len(fields) >= 3 and re.fullmatch(r"[0-9a-fA-F]+", fields[2]):
            result[fields[0]] = int(fields[2], 16)
    return result


def call_relocation_counts(text: str) -> dict[str, int]:
    counts: collections.Counter[str] = collections.Counter()
    for match in re.finditer(
        r"^\s*0x[0-9A-Fa-f]+\s+R_AARCH64_CALL26\s+(\S+)\s+0x[0-9A-Fa-f]+\s*$",
        text,
        re.M,
    ):
        counts[match.group(1)] += 1
    return dict(counts)


def relocation_section(text: str, name: str) -> str:
    match = re.search(
        rf"^\s*Section \(\d+\) {re.escape(name)} \{{\n(.*?)^\s*\}}$",
        text,
        re.M | re.S,
    )
    if match is None:
        raise BuildError(f"linked relocation section is missing: {name}")
    return match.group(1)


def audit_protocol_authority(root: Path) -> dict[str, Any]:
    receipts: dict[str, Any] = {}
    texts: dict[str, str] = {}
    base = resolve(root, BASE_WORK_TREE)
    for label, (relative, size, digest) in PROTOCOL_SOURCE_IDENTITIES.items():
        path = base / relative
        receipts[label] = validate_file(path, (size, digest), f"protocol {label}")
        texts[label] = path.read_text(encoding="utf-8")

    requirements = {
        "usbc": (
            "ret = max77705_bulk_write(usbc_data->muic, OPCODE_WRITE,",
            "max77705_write_reg(usbc_data->muic, OPCODE_WRITE_END, 0x00);",
            "max77705_bulk_read(usbc_data->muic, OPCODE_READ, OPCODE_SIZE, values);",
            "max77705_bulk_read(usbc_data->muic, OPCODE_READ + OPCODE_SIZE,",
        ),
        "muic": (
            "write_data.opcode = COMMAND_CONTROL1_WRITE;",
            "write_data.write_length = 1;",
            "write_data.read_length = 0;",
        ),
        "muic_header": (
            "COMMAND_CONTROL1_READ\t\t= 0x05,",
            "COMMAND_CONTROL1_WRITE\t\t= 0x06,",
        ),
        "register_header": (
            "#define OPCODE_WRITE 0x21",
            "#define OPCODE_WRITE_END 0x41",
            "#define OPCODE_READ 0x51",
        ),
    }
    for label, tokens in requirements.items():
        missing = [token for token in tokens if token not in texts[label]]
        if missing:
            raise BuildError(f"protocol authority tokens missing in {label}: {missing}")
    return {
        "verified": True,
        "receipts": receipts,
        "interpretation": (
            "stock CONTROL1 uses opcode 0x05/0x06, writes opcode plus payload at "
            "0x21, terminates at 0x41, and reads opcode plus declared data from 0x51"
        ),
        "physical_switch_state_ceiling": (
            "firmware command readback may be a control-plane shadow; silent readback "
            "tuples cannot refute physical D+/D- continuity"
        ),
    }


def validate_fixed_abi(root: Path) -> dict[str, Any]:
    results: dict[str, Any] = {}
    paths = {"a": resolve(root, P310_FIXED_A), "b": resolve(root, P310_FIXED_B)}
    for side, directory in paths.items():
        results[side] = {
            name: validate_file(directory / name, identity, f"P3.10 {side} {name}")
            for name, identity in FIXED_ABI_IDENTITIES.items()
        }
    return {
        "verified": True,
        "a_b_identity": all(
            results["a"][name]["sha256"] == results["b"][name]["sha256"]
            for name in FIXED_ABI_IDENTITIES
        ),
        "artifacts": results,
    }


def audit_module(root: Path, ko: Path, symvers_path: Path) -> dict[str, Any]:
    toolchain = resolve(root, TOOLCHAIN) / "bin"
    llvm_nm = toolchain / "llvm-nm"
    llvm_readobj = toolchain / "llvm-readobj"
    modinfo = Path("/usr/sbin/modinfo")
    modprobe = Path("/usr/sbin/modprobe")
    for path in (llvm_nm, llvm_readobj, modinfo, modprobe):
        if not path.is_file():
            raise BuildError(f"required audit tool is missing: {path}")

    header = run_checked(
        [str(llvm_readobj), "--file-headers", str(ko)], cwd=root
    ).stdout
    for token in (
        "Format: elf64-littleaarch64",
        "Arch: aarch64",
        "Type: Relocatable",
        "Machine: EM_AARCH64",
    ):
        if token not in header:
            raise BuildError(f"module ELF header is missing {token!r}")

    undefined_text = run_checked(
        [str(llvm_nm), "--undefined-only", str(ko)], cwd=root
    ).stdout
    undefined = parse_undefined_symbols(undefined_text)
    if undefined != EXPECTED_UNDEFINED:
        raise BuildError(
            "undefined import surface mismatch: "
            f"missing={sorted(EXPECTED_UNDEFINED - undefined)} "
            f"extra={sorted(undefined - EXPECTED_UNDEFINED)}"
        )

    defined_text = run_checked(
        [str(llvm_nm), "--defined-only", "--format=posix", str(ko)], cwd=root
    ).stdout
    defined = parse_defined_symbols(defined_text)
    required_cfi = {
        "__cfi_check",
        "s22plus_max77705_result_get.cfi_jt",
        "s22plus_max77705_diag_probe.cfi_jt",
    }
    if not required_cfi.issubset(defined):
        raise BuildError(f"linked CFI symbols missing: {sorted(required_cfi - set(defined))}")

    relocations = run_checked(
        [str(llvm_readobj), "--relocations", str(ko)], cwd=root
    ).stdout
    calls = call_relocation_counts(relocations)
    actual_calls = {name: calls.get(name, 0) for name in EXPECTED_CALL_RELOCATIONS}
    if actual_calls != EXPECTED_CALL_RELOCATIONS:
        raise BuildError(
            f"linked call relocation surface mismatch: {actual_calls} "
            f"!= {EXPECTED_CALL_RELOCATIONS}"
        )
    external_calls = {name: calls.get(name, 0) for name in EXPECTED_UNDEFINED}
    unexpected_external_calls = {
        name: count
        for name, count in external_calls.items()
        if count and name not in EXPECTED_CALL_RELOCATIONS and name != "__stack_chk_fail"
    }
    if unexpected_external_calls:
        raise BuildError(f"unexpected external call relocations: {unexpected_external_calls}")

    result_ops = relocation_section(
        relocations, ".rela.rodata.s22plus_max77705_result_ops"
    )
    driver = relocation_section(
        relocations, ".rela.data.s22plus_max77705_diag_driver"
    )
    result_jt = defined["s22plus_max77705_result_get.cfi_jt"]
    probe_jt = defined["s22plus_max77705_diag_probe.cfi_jt"]
    if not re.search(rf"R_AARCH64_ABS64\s+\.text\s+0x{result_jt:X}\b", result_ops):
        raise BuildError("module-param getter is not relocated to its CFI jump table")
    if not re.search(rf"R_AARCH64_ABS64\s+\.text\s+0x{probe_jt:X}\b", driver):
        raise BuildError("I2C probe is not relocated to its CFI jump table")

    sections = run_checked(
        [str(llvm_readobj), "--sections", str(ko)], cwd=root
    ).stdout
    if "Name: __versions" not in sections:
        raise BuildError("linked module lacks __versions")
    if re.search(r"Name: _{2,3}ksymtab", sections):
        raise BuildError("diagnostic module unexpectedly exports a symbol")

    modinfo_text = run_checked([str(modinfo), str(ko)], cwd=root).stdout
    modinfo_fields = parse_modinfo(modinfo_text)
    for key, expected in EXPECTED_MODINFO.items():
        if modinfo_fields.get(key) != expected:
            raise BuildError(
                f"modinfo field mismatch for {key}: {modinfo_fields.get(key)} != {expected}"
            )
    forbidden_modinfo = sorted(set(modinfo_fields) & {"alias", "firmware", "softdep"})
    if forbidden_modinfo:
        raise BuildError(f"unexpected module metadata surface: {forbidden_modinfo}")

    versions_text = run_checked(
        [str(modprobe), "--dump-modversions", str(ko)], cwd=root
    ).stdout
    versions = parse_modversions(versions_text)
    expected_version_symbols = set(EXPECTED_UNDEFINED) | {"module_layout"}
    if set(versions) != expected_version_symbols:
        raise BuildError(
            "module modversion surface mismatch: "
            f"missing={sorted(expected_version_symbols - set(versions))} "
            f"extra={sorted(set(versions) - expected_version_symbols)}"
        )
    symvers = parse_symvers(symvers_path.read_text(encoding="ascii"))
    mismatch = {
        symbol: (crc, symvers.get(symbol))
        for symbol, crc in versions.items()
        if symvers.get(symbol) != crc
    }
    if mismatch:
        raise BuildError(f"module modversion CRC mismatch: {mismatch}")

    return {
        "verified": True,
        "path": str(ko),
        "size": ko.stat().st_size,
        "sha256": sha256_file(ko),
        "elf": "elf64-littleaarch64 relocatable",
        "undefined_imports": sorted(undefined),
        "modversions": dict(sorted(versions.items())),
        "call_relocations": actual_calls,
        "cfi": {
            "cfi_check_present": True,
            "result_get_cfi_jump_table": f"0x{result_jt:x}",
            "probe_cfi_jump_table": f"0x{probe_jt:x}",
            "callback_relocations_target_cfi_jump_tables": True,
        },
        "exports": [],
        "modinfo": {key: modinfo_fields[key] for key in EXPECTED_MODINFO},
    }


def audit_build(root: Path, build_dir: Path) -> dict[str, Any]:
    fixed = validate_fixed_abi(root)
    symvers = resolve(root, P310_FIXED_A) / "vmlinux.symvers"
    ko_paths = {
        "a": build_dir / "immutable-a/s22plus_max77705_mux_diag.ko",
        "b": build_dir / "immutable-b/s22plus_max77705_mux_diag.ko",
    }
    for side, path in ko_paths.items():
        if not path.is_file() or path.is_symlink():
            raise BuildError(f"linked module {side} is missing or non-regular: {path}")
    modules = {side: audit_module(root, path, symvers) for side, path in ko_paths.items()}
    byte_identical = ko_paths["a"].read_bytes() == ko_paths["b"].read_bytes()
    if not byte_identical:
        raise BuildError("external module A/B outputs are not byte-identical")
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "host_only": True,
        "fixed_p310_abi": fixed,
        "protocol_authority": audit_protocol_authority(root),
        "modules": modules,
        "a_b_byte_identical": True,
        "linked_surface": {
            "firmware_update": False,
            "reset": False,
            "irq": False,
            "workqueue": False,
            "notifier": False,
            "power_supply": False,
            "exported_symbols": 0,
            "conditional_control1_write_maximum": 1,
            "control1_read_count": 3,
            "retention_window_ms": 30_000,
        },
        "safety": {
            "device_contact": False,
            "partition_write": False,
            "image_packaging": False,
            "module_insertion": False,
        },
        "verdict": "PASS_AB_REPRODUCIBLE_LINKED_ABI_AUDITED",
        "authority": "H0_BUILD_ONLY_NO_DEVICE_AUTHORITY",
    }


def build_environment(root: Path, output_dir: Path) -> dict[str, str]:
    base = resolve(root, BASE_WORK_TREE)
    clang_bin = resolve(root, TOOLCHAIN) / "bin"
    host_sysroot = base / "kernel_platform/build/build-tools/sysroot"
    host_tools = base / "kernel_platform/prebuilts/kernel-build-tools/linux-x86"
    return {
        "PATH": os.pathsep.join((str(clang_bin), "/usr/bin", "/bin")),
        "LC_ALL": "C",
        "TZ": "UTC",
        "ARCH": "arm64",
        "SUBARCH": "arm64",
        "LLVM": "1",
        "LLVM_IAS": "1",
        "CROSS_COMPILE": "aarch64-linux-gnu-",
        "GOOGLE_BRANCH": "android12-5.10",
        "KMI_GENERATION": "9",
        "LOCALVERSION": STOCK_LOCALVERSION,
        "SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH,
        "KBUILD_BUILD_TIMESTAMP": STOCK_TIMESTAMP,
        "KBUILD_BUILD_USER": "build-user",
        "KBUILD_BUILD_HOST": "build-host",
        "KBUILD_BUILD_VERSION": "1",
        "KCFLAGS": "-D__ANDROID_COMMON_KERNEL__",
        "GIT_CEILING_DIRECTORIES": str(output_dir),
        "HOSTCFLAGS": f"--sysroot={host_sysroot} -I{host_tools / 'include'}",
        "HOSTLDFLAGS": (
            f"--sysroot={host_sysroot} "
            f"-Wl,-rpath,{host_tools / 'lib64'} -L {host_tools / 'lib64'}"
            " -fuse-ld=lld --rtlib=compiler-rt"
        ),
    }


def validate_tools(root: Path) -> dict[str, Any]:
    toolchain_bin = resolve(root, TOOLCHAIN) / "bin"
    receipts: dict[str, Any] = {}
    for name, digest in TOOL_IDENTITIES.items():
        path = (toolchain_bin / name).resolve()
        if not path.is_file() or sha256_file(path) != digest:
            raise BuildError(f"toolchain identity mismatch: {name} -> {path}")
        receipts[name] = {
            "path": str(path),
            "size": path.stat().st_size,
            "sha256": digest,
        }
    version = run_checked([str(toolchain_bin / "clang"), "--version"], cwd=root).stdout
    if (
        "Android (7284624, based on r416183b) clang version 12.0.5" not in version
        or "c935d99d7cf2016289302412d708641d52d2f7ee" not in version
    ):
        raise BuildError(f"unexpected clang version: {version!r}")
    return {"verified": True, "tools": receipts, "clang_version": version.splitlines()}


def validate_source_authority(root: Path, output_dir: Path) -> dict[str, Any]:
    base = resolve(root, BASE_WORK_TREE)
    manifest_path = resolve(root, BASE_SOURCE_MANIFEST)
    historical = validate_file(
        manifest_path, BASE_SOURCE_MANIFEST_IDENTITY, "base source manifest"
    )
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    if (
        manifest.get("target") != TARGET
        or manifest.get("resident_tree", {}).get("match") is not True
        or manifest.get("resident_tree", {}).get("checked_members") != 166_037
        or manifest.get("artifacts", {})
        .get("reconstructed-final-members.jsonl", {})
        .get("sha256")
        != EXPECTED_FINAL_MEMBERS_SHA256
    ):
        raise BuildError("historical base source authority mismatch")
    validate_file(resolve(root, BASE_ARCHIVE), BASE_ARCHIVE_IDENTITY, "base archive")
    validate_file(resolve(root, DELTA_ARCHIVE), DELTA_ARCHIVE_IDENTITY, "delta archive")
    overlay = resolve(root, OVERLAY_AUDIT)
    if sha256_file(overlay) != OVERLAY_AUDIT_SHA256:
        raise BuildError("source overlay audit helper identity mismatch")

    live_dir = output_dir / "source-overlay-audit"
    command = [
        sys.executable,
        str(overlay),
        "--base",
        str(resolve(root, BASE_ARCHIVE)),
        "--delta",
        str(resolve(root, DELTA_ARCHIVE)),
        "--resident-tree",
        str(base),
        "--out",
        str(live_dir),
    ]
    completed = run_checked(command, cwd=root)
    live_manifest_path = live_dir / "manifest.json"
    if not live_manifest_path.is_file():
        raise BuildError("live source overlay audit did not emit manifest.json")
    live = json.loads(live_manifest_path.read_text(encoding="ascii"))
    if (
        live.get("resident_tree", {}).get("match") is not True
        or live.get("resident_tree", {}).get("checked_members") != 166_037
        or live.get("artifacts", {})
        .get("reconstructed-final-members.jsonl", {})
        .get("sha256")
        != EXPECTED_FINAL_MEMBERS_SHA256
    ):
        raise BuildError("live source overlay audit failed")
    return {
        "verified": True,
        "historical_manifest": historical,
        "live_manifest": {
            "path": str(live_manifest_path),
            "size": live_manifest_path.stat().st_size,
            "sha256": sha256_file(live_manifest_path),
            "stdout": completed.stdout.strip(),
        },
    }


def generate_fixed_kmi(root: Path, output_dir: Path, source_common: Path) -> dict[str, Any]:
    combined = output_dir / "abi_symbollist"
    raw = (
        output_dir
        / "source/out/msm-waipio-waipio-gki/gki_kernel/common/abi_symbollist.raw"
    )
    raw.parent.mkdir(parents=True, exist_ok=True)
    paths = [source_common / "android" / name for name in KMI_SYMBOL_LISTS]
    for path in paths:
        if not path.is_file():
            raise BuildError(f"KMI source list is missing: {path}")
    with combined.open("wb") as destination:
        for index, path in enumerate(paths):
            if index:
                destination.write(b"\n")
            destination.write(path.read_bytes())
    validate_file(combined, COMBINED_KMI_IDENTITY, "combined P3.10 KMI list")
    flatten = resolve(root, BASE_BUILD) / "abi/flatten_symbol_list"
    completed = subprocess.run(
        [str(flatten)],
        cwd=root,
        input=combined.read_bytes(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise BuildError(
            "flatten_symbol_list failed: "
            + completed.stderr[-4000:].decode(errors="replace")
        )
    raw.write_bytes(completed.stdout)
    receipt = validate_file(raw, RAW_KMI_IDENTITY, "raw P3.10 KMI list")
    if sum(1 for _ in raw.open("rb")) != RAW_KMI_LINES:
        raise BuildError("raw P3.10 KMI line count mismatch")
    return {
        "verified": True,
        "source_list_count": len(paths),
        "source_lists": [path.name for path in paths],
        "combined": validate_file(combined, COMBINED_KMI_IDENTITY, "combined KMI"),
        "raw": {**receipt, "line_count": RAW_KMI_LINES},
    }


def run_build(root: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise BuildError(f"output directory already exists: {output_dir}")
    if shutil.disk_usage(output_dir.parent).free < MIN_FREE_BYTES:
        raise BuildError("less than 4 GiB free before external-module build")
    output_dir.mkdir(parents=True)

    source_authority = validate_source_authority(root, output_dir)
    tools = validate_tools(root)
    fixed_abi = validate_fixed_abi(root)
    protocol = audit_protocol_authority(root)
    patch = validate_file(resolve(root, P310_PATCH), P310_PATCH_IDENTITY, "P3.10 patch")
    module_sources = {
        name: validate_file(
            resolve(root, MODULE_SOURCE_DIR) / name, identity, f"module source {name}"
        )
        for name, identity in MODULE_SOURCE_IDENTITIES.items()
    }
    precompile_source_contract = validate_precompile_source_contract(root)

    source_root = output_dir / "source"
    copied_common = source_root / "kernel_platform/common"
    copied_common.parent.mkdir(parents=True)
    run_checked(
        [
            "/usr/bin/cp",
            "-a",
            str(resolve(root, BASE_COMMON)),
            str(copied_common),
        ],
        cwd=root,
    )
    for relative, (before, _) in BASE_PATCHED_FILES.items():
        if sha256_file(copied_common / relative) != before:
            raise BuildError(f"pre-patch source identity mismatch: {relative}")
    patch_stdout = output_dir / "patch.stdout.log"
    patch_stderr = output_dir / "patch.stderr.log"
    run_checked(
        [
            "/usr/bin/patch",
            "--batch",
            "--forward",
            "--fuzz=0",
            "-p1",
            "-i",
            str(resolve(root, P310_PATCH)),
        ],
        cwd=source_root,
        stdout_path=patch_stdout,
        stderr_path=patch_stderr,
    )
    for relative, (_, after) in BASE_PATCHED_FILES.items():
        if sha256_file(copied_common / relative) != after:
            raise BuildError(f"post-patch source identity mismatch: {relative}")
        if sha256_file(resolve(root, BASE_COMMON) / relative) != BASE_PATCHED_FILES[relative][0]:
            raise BuildError(f"resident source changed while patching copy: {relative}")

    kmi = generate_fixed_kmi(root, output_dir, copied_common)
    kernel_out = output_dir / "kernel-out"
    kernel_out.mkdir()
    fixed_a = resolve(root, P310_FIXED_A)
    shutil.copy2(fixed_a / ".config", kernel_out / ".config")
    environment = build_environment(root, output_dir)
    make_base = [
        "/usr/bin/make",
        "-C",
        str(copied_common),
        f"O={kernel_out}",
        "-j2",
    ]
    run_checked(
        [*make_base, "modules_prepare"],
        cwd=root,
        env=environment,
        stdout_path=output_dir / "modules-prepare.stdout.log",
        stderr_path=output_dir / "modules-prepare.stderr.log",
    )
    validate_file(kernel_out / ".config", FIXED_ABI_IDENTITIES[".config"], "prepared config")
    shutil.copy2(fixed_a / "vmlinux.symvers", kernel_out / "Module.symvers")
    validate_file(
        kernel_out / "Module.symvers",
        FIXED_ABI_IDENTITIES["vmlinux.symvers"],
        "external-module Module.symvers",
    )

    module_stage = output_dir / "module-stage"
    module_stage.mkdir()
    for name in MODULE_SOURCE_IDENTITIES:
        shutil.copy2(resolve(root, MODULE_SOURCE_DIR) / name, module_stage / name)
    module_make = [*make_base, f"M={module_stage}"]
    build_receipts: dict[str, Any] = {}
    for side in ("a", "b"):
        run_checked(
            [*module_make, "modules"],
            cwd=root,
            env=environment,
            stdout_path=output_dir / f"module-{side}.stdout.log",
            stderr_path=output_dir / f"module-{side}.stderr.log",
        )
        ko = module_stage / "s22plus_max77705_mux_diag.ko"
        if not ko.is_file():
            raise BuildError(f"external module build {side} produced no .ko")
        immutable = output_dir / f"immutable-{side}"
        immutable.mkdir()
        destination = immutable / ko.name
        shutil.copy2(ko, destination)
        build_receipts[side] = {
            "path": str(destination),
            "size": destination.stat().st_size,
            "sha256": sha256_file(destination),
        }
        if side == "a":
            run_checked(
                [*module_make, "clean"],
                cwd=root,
                env=environment,
                stdout_path=output_dir / "module-clean.stdout.log",
                stderr_path=output_dir / "module-clean.stderr.log",
            )
            for name, identity in MODULE_SOURCE_IDENTITIES.items():
                validate_file(module_stage / name, identity, f"post-clean module source {name}")

    result = audit_build(root, output_dir)
    result["source_authority"] = source_authority
    result["toolchain"] = tools
    result["protocol_authority"] = protocol
    result["p310_patch"] = patch
    result["module_sources"] = module_sources
    result["precompile_source_contract"] = precompile_source_contract
    result["kmi_whitelist"] = kmi
    result["builds"] = build_receipts
    result["build_environment"] = {
        key: environment[key]
        for key in (
            "ARCH",
            "SUBARCH",
            "LLVM",
            "LLVM_IAS",
            "CROSS_COMPILE",
            "GOOGLE_BRANCH",
            "KMI_GENERATION",
            "LOCALVERSION",
            "SOURCE_DATE_EPOCH",
            "KBUILD_BUILD_TIMESTAMP",
            "KBUILD_BUILD_USER",
            "KBUILD_BUILD_HOST",
            "KBUILD_BUILD_VERSION",
            "KCFLAGS",
            "GIT_CEILING_DIRECTORIES",
        )
    }
    result["free_bytes_after"] = shutil.disk_usage(output_dir).free
    atomic_json(output_dir / "build-audit.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build", help="build A/B and audit")
    build_parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    audit_parser = subparsers.add_parser("audit", help="audit an existing A/B build")
    audit_parser.add_argument("--build-dir", type=Path, required=True)
    audit_parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    root = repo_root()
    try:
        if args.command == "build":
            output_dir = resolve(root, args.output_dir)
            result = run_build(root, output_dir)
            result_path = output_dir / "build-audit.json"
        else:
            build_dir = resolve(root, args.build_dir)
            result = audit_build(root, build_dir)
            result_path = resolve(root, args.output) if args.output else None
            if result_path is not None:
                atomic_json(result_path, result)
        print(json.dumps({"verdict": result["verdict"], "result": str(result_path)}))
        return 0
    except (BuildError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

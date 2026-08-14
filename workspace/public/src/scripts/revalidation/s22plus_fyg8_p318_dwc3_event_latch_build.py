#!/usr/bin/env python3
"""Build and audit the P3.18 early DWC3 event-latch module twice.

This is H0-only.  It reconstructs the fixed P3.10 kernel ABI, builds the same
GPL tracepoint consumer twice, executes the decoder's real C implementation on
the host, and audits the resulting AArch64 module surface.  It does not package
or load the module and grants no device authority.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import s22plus_fyg8_max77705_mux_diag_build as base


SCHEMA = "s22plus_fyg8_p318_dwc3_event_latch_build_v2"
TARGET = base.TARGET
VERDICT = "PASS_P318_DWC3_EVENT_LATCH_AB_ABI_QUALIFIED_H0"
MODULE_NAME = "s22plus_dwc3_event_latch"
MODULE_SOURCE_DIR = Path(
    "workspace/public/src/kernel-modules/s22plus_dwc3_event_latch"
)
FIXTURE_SOURCE = Path(
    "workspace/public/src/native-init/"
    "s22plus_fyg8_p318_dwc3_event_decoder_fixture.c"
)
DEFAULT_OUTPUT_DIR = Path(
    "workspace/private/outputs/s22plus_fyg8_p318/"
    "dwc3-event-latch-build-20260814-01"
)

MODULE_SOURCE_IDENTITIES = {
    "Makefile": (
        88,
        "1e9b89397482ba8d643410854a6a5ae61cc8d84be0fc54f44204d6e68c18d1d6",
    ),
    "s22plus_dwc3_event_decode.h": (
        1_940,
        "6e12bbe4c6d62966d59557d04c14f6b6212e12a55fe2ca89469472dec8029180",
    ),
    "s22plus_dwc3_event_latch.c": (
        7_076,
        "a731a64921e75fc716087c4100c75629f40b0e4d5391862b36cc961e9b98ab8c",
    ),
}
FIXTURE_SOURCE_IDENTITY = (
    2_120,
    "b6b9781b3fafb78b6c6ff69d4f6c24eb2f5639e485b04be154f8aa0453f4874e",
)
DWC3_SOURCE_IDENTITIES = {
    "drivers/usb/dwc3/core.h": (
        53_381,
        "97c2a45cf624cd3e99061dec403d1c4c55a2f69798fd2768a54bddba536b711b",
    ),
    "drivers/usb/dwc3/trace.h": (
        9_321,
        "2e6cfc33cdd912352afc06778be8aaaa5617c9ce260051330faa42bc7c245281",
    ),
    "drivers/usb/dwc3/trace.c": (
        536,
        "ac75ee0a16c79a940714732a894735bed700235160ba0698ed1ea8e764d60bdf",
    ),
    "drivers/usb/dwc3/gadget.c": (
        125_778,
        "a08c37921fdcd95895a19ee7e1524b17da5e6165a8369f666f7932e309c93717",
    ),
    "drivers/usb/gadget/udc/core.c": (
        50_119,
        "630ffab76668143456679d7538b44ec1bc11444feb69dde66e49bdff96d563f1",
    ),
}
P260_RUNTIME_SOURCE = Path(
    "workspace/public/src/native-init/s22plus_fyg8_p260_e3_runtime.inc.c"
)
P260_RUNTIME_IDENTITY = (
    20_665,
    "767bd359de56cb24be84c4479cd01d4f710a676490c23f966617b996fe5cc612",
)

EXPECTED_UNDEFINED = frozenset(
    {
        "__tracepoint_dwc3_event",
        "arm64_const_caps_ready",
        "cpu_hwcap_keys",
        "ktime_get",
        "scnprintf",
        "strcmp",
        "synchronize_rcu",
        "synchronize_srcu",
        "tracepoint_probe_register",
        "tracepoint_probe_unregister",
        "tracepoint_srcu",
    }
)
EXPECTED_CALL_RELOCATIONS = {
    "ktime_get": 3,
    "scnprintf": 2,
    "strcmp": 1,
    "synchronize_rcu": 1,
    "synchronize_srcu": 1,
    "tracepoint_probe_register": 1,
    "tracepoint_probe_unregister": 1,
}
EXPECTED_MODINFO = {
    "description": ["S22+ FYG8 one-shot DWC3 host-event latch"],
    "license": ["GPL v2"],
    "depends": [""],
    "name": [MODULE_NAME],
    "vermagic": [base.EXPECTED_VERMAGIC],
    "parm": [
        "snapshot:write-once DWC3 event latch snapshot",
        (
            "expose_gate:write-once pre-UDC exposure gate; reads 0 before "
            "and 1 after capture"
        ),
    ],
}


class LatchBuildError(RuntimeError):
    """Raised when the fixed latch build or audit differs."""


def _text(data: bytes, label: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LatchBuildError(f"{label} is not UTF-8") from exc


def _function(source: str, marker: str) -> str:
    start = source.find(marker)
    if start < 0:
        raise LatchBuildError(f"missing function marker: {marker}")
    brace = source.find("{", start)
    if brace < 0:
        raise LatchBuildError(f"missing function body: {marker}")
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise LatchBuildError(f"unterminated function body: {marker}")


def _ordered(source: str, label: str, tokens: tuple[str, ...]) -> None:
    cursor = -1
    for token in tokens:
        found = source.find(token, cursor + 1)
        if found < 0:
            raise LatchBuildError(f"{label} lacks ordered token {token!r}")
        cursor = found


def audit_udc_name_authority(
    module: str, udc_core: str, p260_runtime: str
) -> dict[str, Any]:
    add = _function(udc_core, "int usb_add_gadget(")
    _ordered(
        add,
        "UDC parent-derived sysfs naming",
        (
            "udc->dev.parent = gadget->dev.parent;",
            'ret = dev_set_name(&udc->dev, "%s",',
            "kobject_name(&gadget->dev.parent->kobj)",
        ),
    )
    observed = re.findall(
        r'"/sys/class/udc/([^/\"]+)/state"', p260_runtime
    )
    if observed != ["a600000.dwc3"]:
        raise LatchBuildError(f"P2.60 observed UDC name differs: {observed}")
    target = re.findall(
        r'^#define S22PLUS_DWC3_TARGET_NAME "([^\"]+)"$', module, re.MULTILINE
    )
    if target != observed:
        raise LatchBuildError(
            f"latch target {target} differs from source-bound UDC name {observed}"
        )
    return {
        "verified": True,
        "kernel_name_producer": (
            "usb_add_gadget dev_set_name from gadget parent kobject_name"
        ),
        "observed_p260_sysfs_state_path": (
            "/sys/class/udc/a600000.dwc3/state"
        ),
        "latch_exact_target": target[0],
        "self_referential_literal_count_forbidden": True,
    }


def audit_latch_source(
    module_data: bytes,
    decoder_data: bytes,
    udc_core_data: bytes,
    p260_runtime_data: bytes,
) -> dict[str, Any]:
    module = _text(module_data, "DWC3 latch module")
    decoder = _text(decoder_data, "DWC3 raw decoder")
    udc_core = _text(udc_core_data, "fixed UDC core")
    p260_runtime = _text(p260_runtime_data, "P2.60 runtime UDC observation")
    probe = _function(module, "static void s22plus_dwc3_event_probe(")
    _ordered(
        probe,
        "latch callback",
        (
            "if (smp_load_acquire(&s22plus_latch.event_ready))",
            "if (!s22plus_dwc3_exact_target(dwc))",
            "ep0state = (u32)READ_ONCE(dwc->ep0state);",
            "kind = s22plus_dwc3_decode_host_event(raw, ep0state);",
            "if (kind == S22PLUS_DWC3_EVENT_NONE)",
            "if (s22plus_dwc3_count_before_gate())",
            "atomic_cmpxchg(&s22plus_latch.event_claimed, 0, 1)",
            "s22plus_latch.first_event_ns = ktime_get_ns();",
            "s22plus_latch.first_event_raw = raw;",
            "s22plus_latch.first_event_kind = (u8)kind;",
            "smp_store_release(&s22plus_latch.event_ready, 1);",
        ),
    )
    if probe.count("ktime_get_ns()") != 1:
        raise LatchBuildError("event callback clock sample count differs")
    count_before = _function(module, "static bool s22plus_dwc3_count_before_gate(")
    _ordered(
        count_before,
        "pre-gate event/gate linearization",
        (
            "atomic_read(&s22plus_latch.exposure_state)",
            "S22PLUS_DWC3_GATE_READY",
            "S22PLUS_DWC3_PRE_GATE_COUNT_MASK",
            "atomic_cmpxchg(",
            "&s22plus_latch.exposure_state, state_value, state_value + 1",
        ),
    )
    publish_gate = _function(module, "static int s22plus_dwc3_publish_gate(")
    _ordered(
        publish_gate,
        "gate/pre-event shared atomic publication",
        (
            "atomic_read(&s22plus_latch.exposure_state)",
            "S22PLUS_DWC3_GATE_READY",
            "atomic_cmpxchg(",
            "state_value | (int)S22PLUS_DWC3_GATE_READY",
        ),
    )
    gate = _function(module, "static int s22plus_dwc3_expose_gate_set(")
    _ordered(
        gate,
        "exposure gate",
        (
            "if (!s22plus_dwc3_exact_one(value))",
            "if (!smp_load_acquire(&s22plus_latch.install_ready))",
            "atomic_cmpxchg(&s22plus_latch.gate_claimed, 0, 1)",
            "s22plus_latch.gate_write_ns = ktime_get_ns();",
            "s22plus_dwc3_publish_gate()",
            "smp_store_release(&s22plus_latch.gate_ready, 1);",
        ),
    )
    init = _function(module, "static int __init s22plus_dwc3_event_latch_init(")
    _ordered(
        init,
        "latch installation",
        (
            "register_trace_dwc3_event(s22plus_dwc3_event_probe, NULL)",
            "if (rc < 0)",
            "s22plus_latch.latch_install_ns = ktime_get_ns();",
            "smp_store_release(&s22plus_latch.install_ready, 1);",
        ),
    )
    exit_body = _function(module, "static void __exit s22plus_dwc3_event_latch_exit(")
    _ordered(
        exit_body,
        "latch removal",
        (
            "unregister_trace_dwc3_event(s22plus_dwc3_event_probe, NULL);",
            "tracepoint_synchronize_unregister();",
        ),
    )
    udc_name_authority = audit_udc_name_authority(
        module, udc_core, p260_runtime
    )
    for token in (
        "module_param_cb(expose_gate, &s22plus_dwc3_expose_gate_ops, NULL, 0644);",
        "module_param_cb(snapshot, &s22plus_dwc3_snapshot_ops, NULL, 0444);",
        "_Static_assert(sizeof(union dwc3_event) == sizeof(u32)",
        "_Static_assert(EP0_SETUP_PHASE == S22PLUS_DWC3_EP0_SETUP_PHASE",
    ):
        if token not in module:
            raise LatchBuildError(f"latch source lacks {token!r}")
    for token in (
        "S22PLUS_DWC3_EVENT_CLASS_MASK 0x000000feU",
        "S22PLUS_DWC3_DEVICE_TYPE_MASK 0x00000f00U",
        "S22PLUS_DWC3_ENDPOINT_MASK 0x0000003eU",
        "S22PLUS_DWC3_ENDPOINT_EVENT_MASK 0x000003c0U",
        "event_class = (raw & S22PLUS_DWC3_EVENT_CLASS_MASK) >> 1;",
        "event_type = (raw & S22PLUS_DWC3_DEVICE_TYPE_MASK) >> 8;",
        "((raw & S22PLUS_DWC3_ENDPOINT_MASK) >> 1) != 0U",
        "((raw & S22PLUS_DWC3_ENDPOINT_EVENT_MASK) >> 6) !=",
        "ep0state != S22PLUS_DWC3_EP0_SETUP_PHASE",
    ):
        if token not in decoder:
            raise LatchBuildError(f"masked raw decoder lacks {token!r}")
    return {
        "verified": True,
        "event_ready_is_first_callback_guard": True,
        "post_latch_hot_path_loads_event_ready_then_returns": True,
        "qualifying_events_before_gate_are_counted": True,
        "pre_gate_count_and_gate_transition_share_one_atomic_state": True,
        "pre_gate_zero_cannot_race_a_gate_transition": True,
        "exact_a600000_dwc3_filter_precedes_decode": True,
        "udc_name_authority": udc_name_authority,
        "masked_raw_decoder_is_shared_with_host_fixture": True,
        "first_event_claim_is_atomic": True,
        "event_fields_publish_before_release_ready": True,
        "exposure_gate_is_write_once": True,
        "gate_timestamp_publishes_before_release_ready": True,
        "tracepoint_register_precedes_install_timestamp": True,
        "tracepoint_unregister_is_synchronized": True,
        "clock_samples": "ktime_get_ns",
    }


def _source_receipts(root: Path) -> dict[str, Any]:
    rows = {
        name: base.validate_file(
            base.resolve(root, MODULE_SOURCE_DIR) / name,
            identity,
            f"P3.18 latch source {name}",
        )
        for name, identity in MODULE_SOURCE_IDENTITIES.items()
    }
    rows["decoder_fixture"] = base.validate_file(
        base.resolve(root, FIXTURE_SOURCE),
        FIXTURE_SOURCE_IDENTITY,
        "P3.18 decoder fixture",
    )
    rows["p260_runtime_udc_observation"] = base.validate_file(
        base.resolve(root, P260_RUNTIME_SOURCE),
        P260_RUNTIME_IDENTITY,
        "P2.60 runtime UDC observation",
    )
    return rows


def _run_decoder_fixture(root: Path, output_dir: Path) -> dict[str, Any]:
    executable = output_dir / "host-decoder-fixture"
    completed = base.run_checked(
        [
            "/usr/bin/cc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-O2",
            f"-I{base.resolve(root, Path('workspace/public/src'))}",
            str(base.resolve(root, FIXTURE_SOURCE)),
            "-o",
            str(executable),
        ],
        cwd=root,
    )
    run = base.run_checked([str(executable)], cwd=root)
    try:
        value = json.loads(run.stdout)
    except json.JSONDecodeError as exc:
        raise LatchBuildError("decoder fixture output is not JSON") from exc
    if value != {
        "schema": "s22plus_fyg8_p318_dwc3_decoder_fixture_v1",
        "positive": 6,
        "negative": 11,
        "verdict": "PASS",
    }:
        raise LatchBuildError(f"decoder fixture result differs: {value}")
    return {
        "verified": True,
        "compiler_stdout": completed.stdout,
        "executable": {
            "size": executable.stat().st_size,
            "sha256": base.sha256_file(executable),
        },
        "result": value,
        "upper_field_positive_preimages": ["0x01ff0101", "0xabcd3040"],
        "wrong_event_class_negative_preimages": [
            "0x00000007",
            "0x00000009",
            "0x00000107",
            "0x00000209",
        ],
    }


def _audit_module(root: Path, ko: Path, symvers_path: Path) -> dict[str, Any]:
    toolchain = base.resolve(root, base.TOOLCHAIN) / "bin"
    llvm_nm = toolchain / "llvm-nm"
    llvm_readobj = toolchain / "llvm-readobj"
    modinfo = Path("/usr/sbin/modinfo")
    modprobe = Path("/usr/sbin/modprobe")

    header = base.run_checked(
        [str(llvm_readobj), "--file-headers", str(ko)], cwd=root
    ).stdout
    for token in (
        "Format: elf64-littleaarch64",
        "Arch: aarch64",
        "Type: Relocatable",
        "Machine: EM_AARCH64",
    ):
        if token not in header:
            raise LatchBuildError(f"module ELF header lacks {token!r}")

    undefined = base.parse_undefined_symbols(
        base.run_checked(
            [str(llvm_nm), "--undefined-only", str(ko)], cwd=root
        ).stdout
    )
    if undefined != EXPECTED_UNDEFINED:
        raise LatchBuildError(
            "latch import surface differs: "
            f"missing={sorted(EXPECTED_UNDEFINED - undefined)} "
            f"extra={sorted(undefined - EXPECTED_UNDEFINED)}"
        )

    defined = base.parse_defined_symbols(
        base.run_checked(
            [str(llvm_nm), "--defined-only", "--format=posix", str(ko)], cwd=root
        ).stdout
    )
    required_cfi = {
        "__cfi_check",
        "s22plus_dwc3_event_probe.cfi_jt",
        "s22plus_dwc3_expose_gate_set.cfi_jt",
        "s22plus_dwc3_expose_gate_get.cfi_jt",
        "s22plus_dwc3_snapshot_get.cfi_jt",
    }
    if not required_cfi.issubset(defined):
        raise LatchBuildError(
            f"latch CFI surface differs: {sorted(required_cfi - set(defined))}"
        )

    relocations = base.run_checked(
        [str(llvm_readobj), "--relocations", str(ko)], cwd=root
    ).stdout
    calls = base.call_relocation_counts(relocations)
    actual_calls = {
        name: calls.get(name, 0) for name in EXPECTED_CALL_RELOCATIONS
    }
    if actual_calls != EXPECTED_CALL_RELOCATIONS:
        raise LatchBuildError(f"latch call surface differs: {actual_calls}")
    init_relocations = base.relocation_section(relocations, ".rela.init.text")
    event_jt = defined["s22plus_dwc3_event_probe.cfi_jt"]
    if not re.search(
        rf"R_AARCH64_ADR_PREL_PG_HI21\s+\.text\s+0x{event_jt:X}\b",
        init_relocations,
    ):
        raise LatchBuildError("tracepoint registration does not use event CFI jump table")

    sections = base.run_checked(
        [str(llvm_readobj), "--sections", str(ko)], cwd=root
    ).stdout
    if "Name: __versions" not in sections:
        raise LatchBuildError("latch module lacks __versions")
    if re.search(r"Name: _{2,3}ksymtab", sections):
        raise LatchBuildError("latch module unexpectedly exports a symbol")

    fields = base.parse_modinfo(
        base.run_checked([str(modinfo), str(ko)], cwd=root).stdout
    )
    for key, expected in EXPECTED_MODINFO.items():
        if fields.get(key) != expected:
            raise LatchBuildError(
                f"latch modinfo differs for {key}: {fields.get(key)} != {expected}"
            )
    forbidden = sorted(set(fields) & {"alias", "firmware", "softdep"})
    if forbidden:
        raise LatchBuildError(f"latch has forbidden modinfo: {forbidden}")

    versions = base.parse_modversions(
        base.run_checked(
            [str(modprobe), "--dump-modversions", str(ko)], cwd=root
        ).stdout
    )
    expected_versions = set(EXPECTED_UNDEFINED) | {"module_layout"}
    if set(versions) != expected_versions:
        raise LatchBuildError("latch modversion symbol set differs")
    symvers = base.parse_symvers(symvers_path.read_text(encoding="ascii"))
    mismatches = {
        symbol: (crc, symvers.get(symbol))
        for symbol, crc in versions.items()
        if symvers.get(symbol) != crc
    }
    if mismatches:
        raise LatchBuildError(f"latch modversion CRC differs: {mismatches}")

    return {
        "verified": True,
        "path": str(ko),
        "size": ko.stat().st_size,
        "sha256": base.sha256_file(ko),
        "undefined_imports": sorted(undefined),
        "modversions": dict(sorted(versions.items())),
        "call_relocations": actual_calls,
        "cfi": sorted(required_cfi),
        "exports": [],
        "modinfo": {key: fields[key] for key in EXPECTED_MODINFO},
    }


def audit_build(
    root: Path, build_dir: Path, *, require_historical: bool = True
) -> dict[str, Any]:
    fixed = base.validate_fixed_abi(root)
    source_receipts = _source_receipts(root)
    udc_core_path = (
        base.resolve(root, base.BASE_COMMON) / "drivers/usb/gadget/udc/core.c"
    )
    udc_core_receipt = base.validate_file(
        udc_core_path,
        DWC3_SOURCE_IDENTITIES["drivers/usb/gadget/udc/core.c"],
        "fixed UDC naming source",
    )
    source_contract = audit_latch_source(
        (base.resolve(root, MODULE_SOURCE_DIR) / "s22plus_dwc3_event_latch.c").read_bytes(),
        (base.resolve(root, MODULE_SOURCE_DIR) / "s22plus_dwc3_event_decode.h").read_bytes(),
        udc_core_path.read_bytes(),
        base.resolve(root, P260_RUNTIME_SOURCE).read_bytes(),
    )
    source_contract["fixed_udc_naming_source"] = udc_core_receipt
    symvers = base.resolve(root, base.P310_FIXED_A) / "vmlinux.symvers"
    paths = {
        side: build_dir / f"immutable-{side}/{MODULE_NAME}.ko"
        for side in ("a", "b")
    }
    for side, path in paths.items():
        if not path.is_file() or path.is_symlink():
            raise LatchBuildError(f"latch module {side} is missing or non-regular")
    modules = {
        side: _audit_module(root, path, symvers) for side, path in paths.items()
    }
    if paths["a"].read_bytes() != paths["b"].read_bytes():
        raise LatchBuildError("latch A/B modules differ")
    historical_path = build_dir / "build-audit.json"
    historical_ab: dict[str, Any]
    if historical_path.is_file():
        historical = json.loads(historical_path.read_text(encoding="utf-8"))
        historical_sources = historical.get("module_sources", {})
        linked_source_names = tuple(MODULE_SOURCE_IDENTITIES)
        if any(
            historical_sources.get(name, {}).get("sha256")
            != source_receipts[name]["sha256"]
            for name in linked_source_names
        ):
            raise LatchBuildError("current linked module inputs differ from A/B build inputs")
        historical_ab = {
            "artifact": {
                "size": historical_path.stat().st_size,
                "sha256": base.sha256_file(historical_path),
            },
            "linked_module_inputs_unchanged": True,
            "fixture_expansion_does_not_change_module_bytes": True,
        }
    elif require_historical:
        raise LatchBuildError("historical A/B build receipt is missing")
    else:
        historical_ab = {
            "artifact": None,
            "linked_module_inputs_unchanged": True,
            "fixture_expansion_does_not_change_module_bytes": True,
        }
    with tempfile.TemporaryDirectory(prefix="p318-latch-reaudit-") as temporary:
        decoder_fixture = _run_decoder_fixture(root, Path(temporary))
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "host_only": True,
        "fixed_p310_abi": fixed,
        "module_sources": source_receipts,
        "source_contract": source_contract,
        "decoder_fixture": decoder_fixture,
        "historical_ab_build": historical_ab,
        "modules": modules,
        "a_b_byte_identical": True,
        "module_semantics": {
            "tracepoint": "dwc3_event",
            "target": "a600000.dwc3",
            "one_shot_exposure_gate": True,
            "one_shot_first_host_event": True,
            "clock": "ktime_get_ns_via_ktime_get",
            "image_patch": False,
            "kprobe": False,
            "tracefs": False,
        },
        "safety": {
            "device_contact": False,
            "module_insertion": False,
            "image_packaging": False,
            "partition_write": False,
        },
        "verdict": VERDICT,
        "authority": "H0_BUILD_ONLY_NO_DEVICE_AUTHORITY",
    }


def run_build(root: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise LatchBuildError(f"output directory already exists: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(output_dir.parent).free < base.MIN_FREE_BYTES:
        raise LatchBuildError("less than 4 GiB free before latch build")
    output_dir.mkdir(parents=True)

    source_authority = base.validate_source_authority(root, output_dir)
    tools = base.validate_tools(root)
    fixed_abi = base.validate_fixed_abi(root)
    patch = base.validate_file(
        base.resolve(root, base.P310_PATCH), base.P310_PATCH_IDENTITY, "P3.10 patch"
    )
    sources = _source_receipts(root)
    decoder = _run_decoder_fixture(root, output_dir)

    source_root = output_dir / "source"
    copied_common = source_root / "kernel_platform/common"
    copied_common.parent.mkdir(parents=True)
    base.run_checked(
        ["/usr/bin/cp", "-a", str(base.resolve(root, base.BASE_COMMON)), str(copied_common)],
        cwd=root,
    )
    for relative, (before, _) in base.BASE_PATCHED_FILES.items():
        if base.sha256_file(copied_common / relative) != before:
            raise LatchBuildError(f"pre-patch source differs: {relative}")
    base.run_checked(
        [
            "/usr/bin/patch",
            "--batch",
            "--forward",
            "--fuzz=0",
            "-p1",
            "-i",
            str(base.resolve(root, base.P310_PATCH)),
        ],
        cwd=source_root,
        stdout_path=output_dir / "patch.stdout.log",
        stderr_path=output_dir / "patch.stderr.log",
    )
    for relative, (_, after) in base.BASE_PATCHED_FILES.items():
        if base.sha256_file(copied_common / relative) != after:
            raise LatchBuildError(f"post-patch source differs: {relative}")
    dwc3_sources = {
        relative: base.validate_file(
            copied_common / relative, identity, f"fixed DWC3 source {relative}"
        )
        for relative, identity in DWC3_SOURCE_IDENTITIES.items()
    }

    kmi = base.generate_fixed_kmi(root, output_dir, copied_common)
    kernel_out = output_dir / "kernel-out"
    kernel_out.mkdir()
    fixed_a = base.resolve(root, base.P310_FIXED_A)
    shutil.copy2(fixed_a / ".config", kernel_out / ".config")
    environment = base.build_environment(root, output_dir)
    make_base = [
        "/usr/bin/make",
        "-C",
        str(copied_common),
        f"O={kernel_out}",
        "-j2",
    ]
    base.run_checked(
        [*make_base, "modules_prepare"],
        cwd=root,
        env=environment,
        stdout_path=output_dir / "modules-prepare.stdout.log",
        stderr_path=output_dir / "modules-prepare.stderr.log",
    )
    base.validate_file(
        kernel_out / ".config", base.FIXED_ABI_IDENTITIES[".config"], "prepared config"
    )
    shutil.copy2(fixed_a / "vmlinux.symvers", kernel_out / "Module.symvers")
    base.validate_file(
        kernel_out / "Module.symvers",
        base.FIXED_ABI_IDENTITIES["vmlinux.symvers"],
        "latch Module.symvers",
    )

    stage = output_dir / "module-stage"
    stage.mkdir()
    for name in MODULE_SOURCE_IDENTITIES:
        shutil.copy2(base.resolve(root, MODULE_SOURCE_DIR) / name, stage / name)
    module_make = [*make_base, f"M={stage}"]
    builds: dict[str, Any] = {}
    for side in ("a", "b"):
        base.run_checked(
            [*module_make, "modules"],
            cwd=root,
            env=environment,
            stdout_path=output_dir / f"module-{side}.stdout.log",
            stderr_path=output_dir / f"module-{side}.stderr.log",
        )
        ko = stage / f"{MODULE_NAME}.ko"
        if not ko.is_file():
            raise LatchBuildError(f"latch build {side} emitted no module")
        immutable = output_dir / f"immutable-{side}"
        immutable.mkdir()
        destination = immutable / ko.name
        shutil.copy2(ko, destination)
        builds[side] = {
            "path": str(destination),
            "size": destination.stat().st_size,
            "sha256": base.sha256_file(destination),
        }
        if side == "a":
            base.run_checked(
                [*module_make, "clean"],
                cwd=root,
                env=environment,
                stdout_path=output_dir / "module-clean.stdout.log",
                stderr_path=output_dir / "module-clean.stderr.log",
            )
            _source_receipts(root)

    result = audit_build(root, output_dir, require_historical=False)
    result.update(
        {
            "source_authority": source_authority,
            "toolchain": tools,
            "fixed_abi": fixed_abi,
            "p310_patch": patch,
            "module_sources": sources,
            "dwc3_sources": dwc3_sources,
            "decoder_fixture": decoder,
            "kmi_whitelist": kmi,
            "builds": builds,
            "free_bytes_after": shutil.disk_usage(output_dir).free,
        }
    )
    base.atomic_json(output_dir / "build-audit.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("--build-dir", type=Path, required=True)
    audit_parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    root = base.repo_root()
    try:
        if args.command == "build":
            output_dir = base.resolve(root, args.output_dir)
            value = run_build(root, output_dir)
            output = output_dir / "build-audit.json"
        else:
            build_dir = base.resolve(root, args.build_dir)
            value = audit_build(root, build_dir)
            output = base.resolve(root, args.output) if args.output else None
            if output is not None:
                base.atomic_json(output, value)
        print(json.dumps(value, indent=2, sort_keys=True))
        if output is not None:
            print(f"result_path={output}", file=sys.stderr)
        return 0
    except (base.BuildError, LatchBuildError, OSError, subprocess.SubprocessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

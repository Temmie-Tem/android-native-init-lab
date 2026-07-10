#!/usr/bin/env python3
"""Build the host-only V3438 ramoops backend postmortem.

The analysis reads pinned source, binaries, and already-collected V3437 evidence.
It has no device transport, image build, flash, reboot, or fault-trigger path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_v3438_ramoops_backend_postmortem_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"

SOURCE_ARCHIVE = Path(
    "workspace/private/inputs/s22plus_kernel_source/"
    "SM-S906N_15_base_osrc/Kernel.tar.gz"
)
MAGISK_KERNEL = Path(
    "workspace/private/outputs/s22plus_native_init/"
    "v3432_pid1_keystone_v0_1/magiskboot-work/kernel"
)
MODULES_LOAD = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/ramdisk-list/vendor/extract/lib/modules/modules.load"
)
SEC_PMSG = MODULES_LOAD.with_name("sec_pmsg.ko")
V3437_HELPER = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3437_ramoops_positive_control_live_gate.py"
)
V3437_RUN = Path(
    "workspace/private/runs/s22plus_v3437_ramoops_20260710T230320Z"
)
V3437_SESSION = V3437_RUN / "session.json"
V3437_TIMELINE = V3437_RUN / "timeline.json"
V3437_LOG = V3437_RUN / "v3437_live_gate.log"
V3437_LAST_KMSG = V3437_RUN / "postrun/candidate-last_kmsg.bin"
V3437_LAST_KMSG_SUMMARY = (
    V3437_RUN / "postrun/candidate-last_kmsg-summary.json"
)
STOCK_BACKEND_SNAPSHOT = V3437_RUN / "postrun/stock-backend-snapshot.txt"
V3435_CONTRACT = Path("docs/plans/s22plus-v3435-ramoops-console-dtbo-contract.json")
V3436_CONTRACT = Path("docs/plans/s22plus-v3436-ramoops-positive-control-contract.json")

PINS = {
    SOURCE_ARCHIVE: "86e2f73412c65fadff0b15bbf0eac9140610f70250514ac0bddbf3b53fb5f7bf",
    MAGISK_KERNEL: "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff",
    MODULES_LOAD: "8491b842e6e05cfba42694ad003301a6598e8d152ec10cc8f0cc6fb17f10e232",
    SEC_PMSG: "50a38817bf985d9c49000f9f8312a07c0aa8c2df679788dfcd9716af94a3eb88",
    V3437_HELPER: "46a92860ad9bc678080be4fa0fb5920e4fc3f2c16e6d6bc9ef45f213214e5489",
    V3437_SESSION: "9f93bea25ef7f856c19e581d18b661c3691dbc0da851e83daa7346dd383c010f",
    V3437_TIMELINE: "7c453a5ee4bd0aec9c5c86ab739f1b4e310e5d0291786a71157df10a6e863e8b",
    V3437_LOG: "d6f0929d72de701d9c2875bc9e27bb45caa3999a2609dc70e99dae321ff7dfd4",
    V3437_LAST_KMSG: "d6a7bc92b12a472f78ffb2567dae1cdea99dc703ffa0ca26849b154cb5a8c8ae",
    V3437_LAST_KMSG_SUMMARY: "eb034df7257fdae6957d88c8e781a906fb11658b06134a82a9220c7653b5097a",
    STOCK_BACKEND_SNAPSHOT: "3e0bf4805c97ab43a0d14f4b2a2b6aad67079113e9f29d31cf8b80ee184cb6f1",
    V3435_CONTRACT: "ee5761c22f590ec01a398dc75bdb31e87e4c983d34b813d94b1428ca7b4e1680",
    V3436_CONTRACT: "c96ac1ce196e3584fab2af13f728655486d27ea4f417c93fd9b6558707d86de7",
}

RAM_SOURCE = "kernel_platform/msm-kernel/fs/pstore/ram.c"
PSTORE_SOURCE = "kernel_platform/msm-kernel/fs/pstore/platform.c"
OF_PLATFORM_SOURCE = "kernel_platform/msm-kernel/drivers/of/platform.c"

OUTPUT = Path("docs/plans/s22plus-v3438-ramoops-backend-postmortem.json")

EXPECTED_PARAMETERS = {
    "console_size": "524288",
    "mem_size": "2097152",
    "pmsg_size": "1048576",
    "record_size": "262144",
}


class AnalysisError(RuntimeError):
    pass


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").is_dir():
            return parent
    raise AnalysisError("repository root not found")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_pins(root: Path) -> dict[str, str]:
    verified: dict[str, str] = {}
    for relative, expected in PINS.items():
        path = resolve(root, relative)
        if not path.is_file():
            raise AnalysisError(f"missing pinned input: {relative}")
        actual = sha256_file(path)
        if actual != expected:
            raise AnalysisError(f"pin mismatch for {relative}: {actual} != {expected}")
        verified[str(relative)] = actual
    return verified


def tar_texts(archive: Path, members: tuple[str, ...]) -> dict[str, str]:
    pending = set(members)
    output: dict[str, str] = {}
    with tarfile.open(archive, "r:gz") as tar:
        for info in tar:
            if info.name not in pending:
                continue
            extracted = tar.extractfile(info)
            if extracted is None:
                raise AnalysisError(f"could not extract source member: {info.name}")
            output[info.name] = extracted.read().decode("utf-8")
            pending.remove(info.name)
            if not pending:
                break
    if pending:
        raise AnalysisError(f"missing source members: {sorted(pending)}")
    return output


def line_of(text: str, needle: str) -> int:
    if needle not in text:
        raise AnalysisError(f"missing source anchor: {needle}")
    return text[: text.index(needle)].count("\n") + 1


def require_order(text: str, anchors: tuple[str, ...]) -> list[int]:
    positions = []
    cursor = 0
    for anchor in anchors:
        position = text.find(anchor, cursor)
        if position < 0:
            raise AnalysisError(f"missing ordered source anchor: {anchor}")
        positions.append(position)
        cursor = position + len(anchor)
    return [text[:position].count("\n") + 1 for position in positions]


def parse_log_parameters(log_text: str) -> dict[str, str]:
    match = re.search(r"^candidate_ramoops_parameters=(\{.*\})$", log_text, re.M)
    if not match:
        raise AnalysisError("V3437 candidate parameters missing")
    value = json.loads(match.group(1))
    if value != EXPECTED_PARAMETERS:
        raise AnalysisError(f"V3437 candidate parameter mismatch: {value}")
    return value


def module_positions(text: str) -> dict[str, int]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    required = ("sec_log_buf.ko", "sec_debug.ko", "sec_pmsg.ko")
    positions = {}
    for name in required:
        if name not in lines:
            raise AnalysisError(f"missing module load entry: {name}")
        positions[name] = lines.index(name) + 1
    return positions


def parse_key_values(text: str) -> dict[str, str]:
    values = {}
    for line in text.splitlines():
        if "=" not in line:
            raise AnalysisError(f"malformed key/value line: {line}")
        key, value = line.split("=", 1)
        values[key] = value
    return values


def build_analysis(root: Path) -> dict[str, Any]:
    verified = verify_pins(root)
    source = tar_texts(
        resolve(root, SOURCE_ARCHIVE),
        (RAM_SOURCE, PSTORE_SOURCE, OF_PLATFORM_SOURCE),
    )
    ram = source[RAM_SOURCE]
    pstore = source[PSTORE_SOURCE]
    of_platform = source[OF_PLATFORM_SOURCE]

    ram_success_order = (
        "err = pstore_register(&cxt->pstore);",
        "if (err) {",
        "mem_size = pdata->mem_size;",
        "record_size = pdata->record_size;",
        'pr_info("using 0x%lx@0x%llx, ecc: %d\\n",',
    )
    ram_success_lines = require_order(ram, ram_success_order)
    pstore_success_order = (
        "psinfo = psi;",
        "backend = new_backend;",
        'pr_info("Registered %s as persistent store backend\\n", psi->name);',
        "return 0;",
    )
    pstore_success_lines = require_order(pstore, pstore_success_order)

    default_anchors = (
        "#define MIN_MEM_SIZE 4096UL",
        "static ulong record_size = MIN_MEM_SIZE;",
        "static ulong ramoops_console_size = MIN_MEM_SIZE;",
        "static ulong ramoops_pmsg_size = MIN_MEM_SIZE;",
        "static ulong mem_size;",
    )
    default_lines = [line_of(ram, anchor) for anchor in default_anchors]

    of_anchors = (
        '{ .compatible = "ramoops" },',
        "for_each_matching_node(node, reserved_mem_matches)",
        "of_platform_device_create(node, NULL, NULL);",
        "arch_initcall_sync(of_platform_default_populate_init);",
    )
    of_lines = require_order(of_platform, of_anchors)

    session = json.loads(resolve(root, V3437_SESSION).read_text(encoding="utf-8"))
    timeline = json.loads(resolve(root, V3437_TIMELINE).read_text(encoding="utf-8"))
    log_text = resolve(root, V3437_LOG).read_text(encoding="utf-8")
    parameters = parse_log_parameters(log_text)
    last_kmsg = resolve(root, V3437_LAST_KMSG).read_bytes()
    last_summary = json.loads(
        resolve(root, V3437_LAST_KMSG_SUMMARY).read_text(encoding="utf-8")
    )
    first_timestamp = re.search(rb"\[\s*([0-9]+\.[0-9]+)\]", last_kmsg)
    if not first_timestamp:
        raise AnalysisError("candidate last_kmsg has no timestamp")
    first_seconds = float(first_timestamp.group(1))

    kernel = resolve(root, MAGISK_KERNEL).read_bytes()
    kernel_strings = {
        "pstore_registration": b"pstore: Registered %s as persistent store backend" in kernel,
        "ramoops_using": b"ramoops: using 0x%lx@0x%llx, ecc: %d" in kernel,
        "ramoops_probe_failure": b"ramoops: registering with pstore failed" in kernel,
    }
    if not all(kernel_strings.values()):
        raise AnalysisError(f"running kernel string anchors missing: {kernel_strings}")

    sec_pmsg = resolve(root, SEC_PMSG).read_bytes()
    sec_pmsg_facts = {
        "of_alias_present": b"samsung,pstore_pmsg" in sec_pmsg,
        "imports_pstore_register": b"pstore_register" in sec_pmsg,
        "imports_pstore_unregister": b"pstore_unregister" in sec_pmsg,
    }
    if not all(sec_pmsg_facts.values()):
        raise AnalysisError(f"sec_pmsg binary anchors missing: {sec_pmsg_facts}")

    helper = resolve(root, V3437_HELPER).read_text(encoding="utf-8")
    helper_accepts_using_in_capture = (
        "Registered ramoops as persistent store backend|ramoops: using" in helper
    )
    helper_requires_only_registered = (
        'if "Registered ramoops as persistent store backend" not in backend_text:'
        in helper
    )
    if not helper_accepts_using_in_capture or not helper_requires_only_registered:
        raise AnalysisError("V3437 helper gate shape changed")

    modules = module_positions(resolve(root, MODULES_LOAD).read_text(encoding="utf-8"))
    stock_snapshot = parse_key_values(
        resolve(root, STOCK_BACKEND_SNAPSHOT).read_text(encoding="utf-8")
    )
    expected_stock_snapshot = {
        "mem_address": "0",
        "mem_size": "0",
        "record_size": "4096",
        "console_size": "4096",
        "ftrace_size": "4096",
        "pmsg_size": "4096",
        "max_reason": "-1",
        "pstore_backend": "samsung,pstore_pmsg",
    }
    if stock_snapshot != expected_stock_snapshot:
        raise AnalysisError(f"stock backend snapshot mismatch: {stock_snapshot}")
    log_has_registered = "Registered ramoops as persistent store backend" in log_text
    log_has_using = "ramoops: using" in log_text
    retained_has_registered = b"Registered ramoops as persistent store backend" in last_kmsg
    retained_has_using = b"ramoops: using" in last_kmsg

    return {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": "HOST_POSTMORTEM_PASS_V3437_BACKEND_GATE_FALSE_NEGATIVE",
        "safety": {
            "host_only": True,
            "device_contact": False,
            "image_build": False,
            "flash": False,
            "panic": False,
            "live_authorized": False,
        },
        "pins": verified,
        "source_proof": {
            "ramoops_defaults": {
                "mem_size": 0,
                "record_size": 4096,
                "console_size": 4096,
                "pmsg_size": 4096,
                "source_lines": default_lines,
            },
            "platform_device_creation": {
                "reserved_memory_allowlist_contains_ramoops": True,
                "available_matching_nodes_are_created": True,
                "initcall": "arch_initcall_sync",
                "source_lines": of_lines,
            },
            "ramoops_probe_success_order": {
                "steps": list(ram_success_order),
                "source_lines": ram_success_lines,
                "module_parameters_update_only_after_pstore_register_success": True,
            },
            "pstore_registration_order": {
                "steps": list(pstore_success_order),
                "source_lines": pstore_success_lines,
                "backend_sysfs_updates_before_success_log": True,
            },
            "running_kernel_strings": kernel_strings,
        },
        "stock_competing_backend": {
            "live_readonly_snapshot": stock_snapshot,
            "sec_pmsg_module": sec_pmsg_facts,
            "modules_load_positions": modules,
            "ordering_inference": (
                "built-in ramoops reserved-memory probe precedes vendor sec_pmsg module #109"
            ),
        },
        "v3437_observation": {
            "run_id": session["run_id"],
            "contract_result": session["classification"]["result"],
            "panic_attempted": session["panic_attempted"],
            "final_state": session["state"],
            "timeline_events": [event["name"] for event in timeline["events"]],
            "candidate_parameters": parameters,
            "candidate_pstore_mounted": "pstore_mount=1" in log_text,
            "candidate_pmsg0_present": "pmsg0=1" in log_text,
            "registration_log_in_live_capture": log_has_registered,
            "using_log_in_live_capture": log_has_using,
            "last_kmsg": {
                **last_summary,
                "first_retained_timestamp_seconds": first_seconds,
                "registration_log_retained": retained_has_registered,
                "using_log_retained": retained_has_using,
                "starts_after_early_initcalls": first_seconds > 3.0,
            },
        },
        "gate_postmortem": {
            "capture_regex_accepts_registered_or_using": helper_accepts_using_in_capture,
            "final_predicate_requires_registered_only": helper_requires_only_registered,
            "early_success_logs_absent_after_ring_wrap": (
                not log_has_registered
                and not log_has_using
                and not retained_has_registered
                and not retained_has_using
                and first_seconds > 3.0
            ),
            "post_register_side_effect_observed": parameters == EXPECTED_PARAMETERS,
            "backend_registration_conclusion": "PROVEN_BY_POST_REGISTER_PARAMETER_UPDATE",
            "contract_classification": "PRESERVED_AS_HISTORICAL_FAIL_CLOSED_RESULT",
            "technical_interpretation": "FALSE_NEGATIVE_LOG_ONLY_BACKEND_GATE",
        },
        "remaining_unknowns": {
            "direct_candidate_pstore_backend_sysfs": "NOT_CAPTURED",
            "direct_candidate_platform_driver_symlink": "NOT_CAPTURED",
            "ramoops_record_retention_after_panic": "UNTESTED_NO_PANIC_OCCURRED",
            "samsung_sec_pmsg_probe_result_under_candidate": "NOT_CAPTURED",
        },
        "next_unit": {
            "name": "V3439 corrected backend-proof gate",
            "host_change": [
                "accept exact post-register parameter side effect",
                "require /sys/module/pstore/parameters/backend=ramoops",
                "require a bound ramoops platform-device driver link",
                "treat early dmesg strings as corroboration, not mandatory proof",
            ],
            "live_status": "NOT_AUTHORIZED",
            "candidate_rebuild": False,
            "same_dtbo_reuse_requires_fresh_exception": True,
        },
    }


def write_output(root: Path, result: dict[str, Any], output: Path) -> Path:
    path = resolve(root, output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    result = build_analysis(root)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    output = resolve(root, args.output)
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
            raise AnalysisError(f"committed output is stale: {args.output}")
        print(result["verdict"])
        return 0
    write_output(root, result, args.output)
    print(result["verdict"])
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

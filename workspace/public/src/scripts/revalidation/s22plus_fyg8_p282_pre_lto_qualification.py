#!/usr/bin/env python3
"""Assemble and verify the exact P2.82 pre-Full-LTO qualification."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_s22plus_fyg8_p234_candidate as candidate_builder  # noqa: E402
import s22plus_fyg8_p234_candidate_contract as candidate_contract  # noqa: E402
import s22plus_fyg8_p234_userspace_build as userspace  # noqa: E402
import s22plus_fyg8_p280_pre_lto_qualification as p280q  # noqa: E402
import s22plus_fyg8_p282_classifier_qemu as classifier_qemu  # noqa: E402
import s22plus_fyg8_p282_contract_spec as spec  # noqa: E402
import s22plus_fyg8_p282_e2_stock_closure as closure  # noqa: E402
import s22plus_fyg8_p282_source_contract as p282  # noqa: E402
import s22plus_fyg8_p282_trace_contract as trace_contract  # noqa: E402


SCHEMA = "s22plus_fyg8_p282_pre_lto_qualification_v1"
VERDICT = "PASS_P282_PRE_FULL_LTO_QUALIFICATION_HOST_ONLY"
LINKED_META_SCHEMA = "s22plus_fyg8_p282_linked_audit_meta_v1"
LINKED_META_VERDICT = "PASS_P282_LINKED_AUDIT_META_HOST_ONLY"

DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p282_v1/"
    "pre-lto-qualification.json"
)
DEFAULT_LINKED_AUDIT_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p282_v1/"
    "linked-audit-meta.json"
)
DEFAULT_KNOWN_GOOD_LINKED_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p280_v5/"
    "repro-linked-audit-fixed.json"
)
DEFAULT_KNOWN_GOOD_VMLINUX = Path(
    "workspace/private/outputs/s22plus_fyg8_p280_v5/bundle-a/vmlinux"
)
DEFAULT_KNOWN_GOOD_CONFIG = Path(
    "workspace/private/outputs/s22plus_fyg8_p280_v5/bundle-a/.config"
)
DEFAULT_USERSPACE_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p282_v1/"
    "userspace/userspace-result.json"
)
DEFAULT_CLASSIFIER_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p282_classifier_qemu/result.json"
)
DEFAULT_P260_QEMU_RESULT = p280q.DEFAULT_P260_QEMU_RESULT
DEFAULT_KPROBE_RESULT = p280q.DEFAULT_KPROBE_RESULT
DEFAULT_LIFECYCLE_RESULT = p280q.DEFAULT_LIFECYCLE_RESULT

QUALIFICATION_SOURCE = Path(__file__).resolve()
LINKED_AUDIT_MODULE_NAME = "s22plus_fyg8_p282_linked_audit"
LINKED_AUDIT_TEST = Path("tests/test_s22plus_fyg8_p282_linked_audit.py")

FOCUSED_TESTS = (
    Path("tests/test_s22plus_fyg8_p282_contract_spec.py"),
    Path("tests/test_s22plus_fyg8_p282_classifier.py"),
    Path("tests/test_s22plus_fyg8_p282_classifier_qemu.py"),
    Path("tests/test_s22plus_fyg8_p282_e1_decoder.py"),
    Path("tests/test_s22plus_fyg8_p282_source_trace_contract.py"),
    Path("tests/test_s22plus_fyg8_p282_registration.py"),
    Path("tests/test_s22plus_fyg8_p282_pre_lto_qualification.py"),
    Path("tests/test_s22plus_fyg8_p282_build_registration.py"),
)
HISTORICAL_PROCESS_V2_TESTS = (
    Path("tests/test_device_action_f1_v2.py"),
    Path("tests/test_device_action_cdc_acm_observer_v1.py"),
    Path("tests/test_device_action_process_v2_docs.py"),
    Path("tests/test_s22plus_fyg8_p234_process_v2.py"),
)

GATE_IMPLEMENTATION_SOURCES = {
    "qualification": QUALIFICATION_SOURCE,
    "candidate_builder": (
        SCRIPT_DIR / "build_s22plus_fyg8_p234_candidate.py"
    ),
    "userspace_builder": (
        SCRIPT_DIR / "s22plus_fyg8_p234_userspace_build.py"
    ),
    "source_contract": (
        SCRIPT_DIR / "s22plus_fyg8_p282_source_contract.py"
    ),
    "contract_spec": SCRIPT_DIR / "s22plus_fyg8_p282_contract_spec.py",
    "runtime": (
        SCRIPT_DIR.parent.parent
        / "native-init/s22plus_fyg8_p282_e3_runtime.inc.c"
    ),
    "classifier": (
        SCRIPT_DIR.parent.parent
        / "native-init/s22plus_fyg8_p282_classifier.inc.c"
    ),
    "trace_contract": (
        SCRIPT_DIR / "s22plus_fyg8_p282_trace_contract.py"
    ),
    "decoder": SCRIPT_DIR / "s22plus_fyg8_p282_e1_decoder.py",
    "closure": SCRIPT_DIR / "s22plus_fyg8_p282_e2_stock_closure.py",
    "classifier_qemu": (
        SCRIPT_DIR / "s22plus_fyg8_p282_classifier_qemu.py"
    ),
    "p260_qemu": SCRIPT_DIR / "s22plus_fyg8_p260_qemu_harness.py",
    "kprobe_qemu": (
        SCRIPT_DIR / "s22plus_fyg8_p280_kprobe_qemu_control.py"
    ),
    "lifecycle_qemu": (
        SCRIPT_DIR / "s22plus_fyg8_p280_trace_lifecycle_qemu.py"
    ),
    "observer": SCRIPT_DIR / "device_action_cdc_acm_observer_v1.py",
}

GATE_NAMES = (
    "01-exact-identity-external-sequence-banner",
    "02-two-link-derived-entrypoint",
    "03-all-567-tuples-roundtrip",
    "04-production-classifier-aarch64-46-of-46",
    "05-decision-headlines-unique",
    "06-direct-vs-resume-run-stop-distinct",
    "07-reinit-lifecycle-fixtures",
    "08-trace-loss-not-clean-negative",
    "09-cleanup-loss-fails-closed",
    "10-unrelated-event-not-singleton-failure",
    "11-contradictory-event-fails",
    "12-canonical-state-speed-stable-pair",
    "13-required-paths-not-incidental-strings",
    "14-exact-safety-authority",
    "15-pinned-generic-qemu-lifecycle",
    "16-aarch64-link-module-symbol-resolution",
    "17-fixed-45-byte-retained-geometry",
    "18-observer-guard-complete-worst-case",
    "19-focused-and-process-v2-regressions",
)

EXPECTED_OBSERVATION_BASE_SEC = 240
P282_ADDITIONAL_CYCLE_BUDGET_SEC = (
    spec.CYCLE_DEADLINE_SEC * 2
)
MIN_OBSERVATION_TIMEOUT_SEC = (
    EXPECTED_OBSERVATION_BASE_SEC + P282_ADDITIONAL_CYCLE_BUDGET_SEC
)
MIN_GUARD_LIFETIME_SEC = MIN_OBSERVATION_TIMEOUT_SEC + 60
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
TEST_COUNT_RE = re.compile(r"^Ran ([1-9][0-9]*) tests? in ", re.MULTILINE)


class QualificationError(ValueError):
    """A fail-closed P2.82 qualification error."""


def _canonical(value: Any) -> bytes:
    return p280q._canonical(value)


def _receipt_bytes(data: bytes) -> dict[str, Any]:
    return p280q._receipt_bytes(data)


def _material(path: Path, label: str) -> dict[str, Any]:
    try:
        return p280q._material(path, label)
    except p280q.QualificationError as exc:
        raise QualificationError(str(exc)) from exc


def _stable_read(
    path: Path, label: str, maximum: int = 32 * 1024 * 1024
) -> bytes:
    try:
        return p280q._stable_read(path, label, maximum)
    except p280q.QualificationError as exc:
        raise QualificationError(str(exc)) from exc


def _large_material(path: Path, label: str) -> dict[str, Any]:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or not 1 <= before.st_size <= 1024 * 1024 * 1024
        ):
            raise QualificationError(
                f"{label} is not a bounded regular file"
            )
        digest = hashlib.sha256()
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 4 * 1024 * 1024))
            if not chunk:
                raise QualificationError(f"{label} read was short")
            digest.update(chunk)
            remaining -= len(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = os.lstat(path)
    identity_fields = (
        "st_dev",
        "st_ino",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    if any(
        getattr(before, name) != getattr(after, name)
        or getattr(after, name) != getattr(current, name)
        for name in identity_fields
    ):
        raise QualificationError(f"{label} changed while reading")
    return {
        "path": str(path.resolve()),
        "size": before.st_size,
        "sha256": digest.hexdigest(),
    }


def _load_json(
    path: Path, label: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        return p280q._load_json(path, label)
    except p280q.QualificationError as exc:
        raise QualificationError(str(exc)) from exc


def _repo_relative(root: Path, path: Path, label: str) -> str:
    try:
        return p280q._repo_relative(root, path, label)
    except p280q.QualificationError as exc:
        raise QualificationError(str(exc)) from exc


def _receipt_identity(row: Any, label: str) -> dict[str, Any]:
    try:
        return p280q._receipt_identity(row, label)
    except p280q.QualificationError as exc:
        raise QualificationError(str(exc)) from exc


def _result_binding(
    root: Path,
    path: Path,
    receipt: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    return {
        "result": receipt,
        "result_repo_path": _repo_relative(root, path, label),
    }


def _load_linked_audit_module():
    try:
        module = importlib.import_module(LINKED_AUDIT_MODULE_NAME)
    except (ImportError, OSError) as exc:
        raise QualificationError(
            "P2.82 linked-audit module is unavailable"
        ) from exc
    if (
        getattr(module, "EXPECTED_SOURCE_CONTRACT_ID", None)
        != p282.CONTRACT_ID
        or getattr(module, "ADAPTER_ID", None)
        != "s22plus-fyg8-p282-linked-audit-v1"
    ):
        raise QualificationError("P2.82 linked-audit identity drifted")
    return module


def _run_test_command(
    root: Path, paths: tuple[Path, ...], label: str
) -> dict[str, Any]:
    if not paths or len(set(paths)) != len(paths):
        raise QualificationError(f"{label} test inventory is invalid")
    materials = {
        str(path): _material(root / path, f"{label} test {path}")
        for path in paths
    }
    command = [
        sys.executable,
        "-m",
        "unittest",
        "-v",
        *(str(path) for path in paths),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            env={**os.environ, "PYTHONPYCACHEPREFIX": "/tmp/a90_pycache"},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=900,
        )
    except subprocess.TimeoutExpired as exc:
        raise QualificationError(f"{label} tests timed out") from exc
    matches = TEST_COUNT_RE.findall(completed.stdout)
    if completed.returncode != 0 or len(matches) != 1:
        raise QualificationError(f"{label} tests did not pass exactly")
    return {
        "command": command,
        "test_count": int(matches[0]),
        "output_sha256": hashlib.sha256(
            completed.stdout.encode("utf-8")
        ).hexdigest(),
        "sources": materials,
        "verified": True,
    }


def _verify_test_gate(
    stored: Any, root: Path, paths: tuple[Path, ...], label: str
) -> dict[str, Any]:
    expected_command = [
        sys.executable,
        "-m",
        "unittest",
        "-v",
        *(str(path) for path in paths),
    ]
    expected_sources = {
        str(path): _material(root / path, f"{label} test {path}")
        for path in paths
    }
    if (
        not isinstance(stored, dict)
        or set(stored)
        != {
            "command",
            "output_sha256",
            "sources",
            "test_count",
            "verified",
        }
        or stored.get("command") != expected_command
        or stored.get("sources") != expected_sources
        or isinstance(stored.get("test_count"), bool)
        or not isinstance(stored.get("test_count"), int)
        or stored["test_count"] < 1
        or not isinstance(stored.get("output_sha256"), str)
        or HEX64_RE.fullmatch(stored["output_sha256"]) is None
        or stored.get("verified") is not True
    ):
        raise QualificationError(f"{label} test receipt is stale")
    return stored


def create_linked_audit_receipt(root: Path) -> dict[str, Any]:
    module = _load_linked_audit_module()
    test = _run_test_command(root, (LINKED_AUDIT_TEST,), "P2.82 linked audit")
    payload = {
        "schema": LINKED_META_SCHEMA,
        "verdict": LINKED_META_VERDICT,
        "source_contract_id": p282.CONTRACT_ID,
        "adapter_id": module.ADAPTER_ID,
        "module": _material(
            root
            / "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p282_linked_audit.py",
            "P2.82 linked-audit module",
        ),
        "known_good": _known_good_linked_binding(root),
        "test": test,
        "verified": True,
    }
    return {
        **payload,
        "payload_sha256": hashlib.sha256(_canonical(payload)).hexdigest(),
    }


def _verify_linked_audit_receipt(path: Path) -> dict[str, Any]:
    root = candidate_contract.intent.repo_root()
    module = _load_linked_audit_module()
    value, receipt = _load_json(path, "P2.82 linked-audit meta receipt")
    if set(value) != {
        "adapter_id",
        "known_good",
        "module",
        "payload_sha256",
        "schema",
        "source_contract_id",
        "test",
        "verified",
        "verdict",
    }:
        raise QualificationError("P2.82 linked-audit receipt shape drifted")
    payload = dict(value)
    digest = payload.pop("payload_sha256", None)
    if digest != hashlib.sha256(_canonical(payload)).hexdigest():
        raise QualificationError("P2.82 linked-audit receipt digest mismatch")
    if (
        value.get("schema") != LINKED_META_SCHEMA
        or value.get("verdict") != LINKED_META_VERDICT
        or value.get("source_contract_id") != p282.CONTRACT_ID
        or value.get("adapter_id") != module.ADAPTER_ID
        or value.get("verified") is not True
    ):
        raise QualificationError("P2.82 linked-audit receipt is not current")
    expected_module = _material(
        root
        / "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p282_linked_audit.py",
        "P2.82 linked-audit module",
    )
    if value.get("module") != expected_module:
        raise QualificationError("P2.82 linked-audit module changed")
    if value.get("known_good") != _known_good_linked_binding(root):
        raise QualificationError("P2.80 known-good linked artifact changed")
    test = value.get("test")
    expected_command = [
        sys.executable,
        "-m",
        "unittest",
        "-v",
        str(LINKED_AUDIT_TEST),
    ]
    expected_test_source = {
        str(LINKED_AUDIT_TEST): _material(
            root / LINKED_AUDIT_TEST, "P2.82 linked-audit test"
        )
    }
    if (
        not isinstance(test, dict)
        or set(test)
        != {
            "command",
            "output_sha256",
            "sources",
            "test_count",
            "verified",
        }
        or test.get("command") != expected_command
        or test.get("sources") != expected_test_source
        or isinstance(test.get("test_count"), bool)
        or not isinstance(test.get("test_count"), int)
        or test["test_count"] < 1
        or not isinstance(test.get("output_sha256"), str)
        or HEX64_RE.fullmatch(test["output_sha256"]) is None
        or test.get("verified") is not True
    ):
        raise QualificationError("P2.82 linked-audit test receipt drifted")
    return {
        **_result_binding(root, path, receipt, "P2.82 linked-audit receipt"),
        "semantics": {
            "adapter_id": module.ADAPTER_ID,
            "source_contract_id": p282.CONTRACT_ID,
            "test_count": test["test_count"],
            "output_sha256": test["output_sha256"],
            "known_good_vmlinux_sha256": value["known_good"]["vmlinux"][
                "sha256"
            ],
            "known_good_config_sha256": value["known_good"]["config"][
                "sha256"
            ],
        },
        "verified": True,
    }


def _known_good_linked_binding(root: Path) -> dict[str, Any]:
    result_path = root / DEFAULT_KNOWN_GOOD_LINKED_RESULT
    vmlinux_path = root / DEFAULT_KNOWN_GOOD_VMLINUX
    config_path = root / DEFAULT_KNOWN_GOOD_CONFIG
    value, result_receipt = _load_json(
        result_path, "P2.80 known-good linked result"
    )
    linked = value.get("linked_audit")
    build_a = value.get("build_a")
    artifacts = build_a.get("artifacts") if isinstance(build_a, dict) else None
    if (
        value.get("schema")
        != "s22plus_fyg8_p234_build_repro_check_v1"
        or value.get("verdict")
        != "PASS_P234_TWO_CLEAN_BUILD_REPRO_AND_LINKED_AUDIT_HOST_ONLY"
        or value.get("candidate_contract", {}).get("source_contract_id")
        != "s22plus-fyg8-p280-parent-pullup-discriminator-v1"
        or not isinstance(linked, dict)
        or linked.get("audit_adapter")
        != "s22plus-fyg8-p280-linked-audit-v1"
        or linked.get("verified") is not True
        or not isinstance(artifacts, dict)
    ):
        raise QualificationError("P2.80 known-good linked result drifted")
    vmlinux = _large_material(vmlinux_path, "P2.80 known-good vmlinux")
    config = _material(config_path, "P2.80 known-good config")
    if (
        artifacts.get("vmlinux")
        != {"size": vmlinux["size"], "sha256": vmlinux["sha256"]}
        or artifacts.get(".config")
        != {"size": config["size"], "sha256": config["sha256"]}
    ):
        raise QualificationError(
            "P2.80 known-good linked artifacts do not match their result"
        )
    return {
        "result": result_receipt,
        "result_repo_path": _repo_relative(
            root, result_path, "P2.80 known-good linked result"
        ),
        "vmlinux": vmlinux,
        "vmlinux_repo_path": _repo_relative(
            root, vmlinux_path, "P2.80 known-good vmlinux"
        ),
        "config": config,
        "config_repo_path": _repo_relative(
            root, config_path, "P2.80 known-good config"
        ),
        "linked_adapter": linked["audit_adapter"],
        "verified": True,
    }


def _verify_userspace(
    path: Path, exact_contract: dict[str, Any]
) -> dict[str, Any]:
    root = candidate_contract.intent.repo_root()
    value, receipt = _load_json(path, "P2.82 userspace result")
    if (
        set(value)
        != {
            "candidate_contract",
            "compile_flags",
            "outputs",
            "profile",
            "run_id",
            "safety",
            "schema",
            "source_contract",
            "target",
            "two_build_byte_identical",
            "verdict",
        }
        or value.get("schema") != userspace.SCHEMA
        or value.get("verdict") != p282.USERSPACE_VERDICT
        or value.get("candidate_contract") != exact_contract
        or value.get("run_id") != exact_contract.get("run_id")
        or value.get("profile") != p282.PROFILE
        or value.get("two_build_byte_identical") is not True
        or value.get("source_contract", {}).get("verified") is not True
    ):
        raise QualificationError("P2.82 userspace result is not current")
    output = path.resolve().parent
    init = _stable_read(
        output / "init", "P2.82 userspace init", 16 * 1024 * 1024
    )
    child = _stable_read(
        output / "s22-e1-child",
        "P2.82 userspace child",
        16 * 1024 * 1024,
    )
    outputs = value.get("outputs")
    if not isinstance(outputs, dict) or set(outputs) != {"child", "init"}:
        raise QualificationError("P2.82 userspace outputs drifted")
    for name, data in (("init", init), ("child", child)):
        expected = _receipt_bytes(data)
        row = outputs.get(name)
        if not isinstance(row, dict) or any(
            row.get(key) != expected[key] for key in expected
        ):
            raise QualificationError(
                f"P2.82 userspace {name} receipt mismatch"
            )
    entries = (
        SimpleNamespace(name="init", data=init),
        SimpleNamespace(name="s22-e1-child", data=child),
    )
    entrypoints = closure._entrypoints(entries)
    closure._validate_p282_authority_strings(init)
    return {
        **_result_binding(root, path, receipt, "P2.82 userspace result"),
        "semantics": {
            "init": {
                "repo_path": _repo_relative(
                    root, output / "init", "P2.82 userspace init"
                ),
                **_receipt_bytes(init),
            },
            "child": {
                "repo_path": _repo_relative(
                    root,
                    output / "s22-e1-child",
                    "P2.82 userspace child",
                ),
                **_receipt_bytes(child),
            },
            "entrypoints": entrypoints,
            "same_path_two_link_byte_identical": True,
            "authority_strings_verified": True,
        },
        "verified": True,
    }


def _expected_safety(exact_contract: dict[str, Any]) -> dict[str, Any]:
    if (
        exact_contract.get("profile") != p282.PROFILE
        or exact_contract.get("source_contract_id") != p282.CONTRACT_ID
    ):
        raise QualificationError("P2.82 safety contract identity mismatch")
    expected = {
        "host_only": True,
        "device_contact": False,
        "device_write": False,
        "odin_invoked": False,
        "flash": False,
        "partition_write": False,
        "live_authorized": False,
        "boot_only_ap": True,
        "ap_members": ["boot.img.lz4"],
        "no_shell": True,
        "no_block_write": True,
        "no_reboot_syscall": True,
        "userspace_sysfs_configfs_write_scope": (
            spec.SAFETY_USERSPACE_WRITE_SCOPE
        ),
        "usb_scope": spec.SAFETY_USB_SCOPE,
        "module_init_probe_authority": "active-live-unproved",
        **spec.RUNTIME_AUTHORITY,
    }
    actual = candidate_builder.artifact_safety(exact_contract)
    if actual != expected:
        raise QualificationError("P2.82 safety dictionary is not exact")
    return actual


def _verify_classifier_qemu(path: Path) -> dict[str, Any]:
    root = candidate_contract.intent.repo_root()
    value, receipt = _load_json(path, "P2.82 classifier QEMU result")
    try:
        classifier_qemu.validate_result_schema(value)
    except classifier_qemu.HarnessError as exc:
        raise QualificationError(str(exc)) from exc
    if (
        value.get("verdict") != classifier_qemu.VERDICT
        or value.get("details_covered") != 46
        or value.get("tuple_count") != 567
    ):
        raise QualificationError("P2.82 classifier QEMU coverage is incomplete")
    current_classifier = _material(
        root / classifier_qemu.CLASSIFIER_RELATIVE,
        "P2.82 production classifier",
    )
    current_spec = _material(
        root / classifier_qemu.SPEC_RELATIVE,
        "P2.82 classifier contract spec",
    )
    if (
        value.get("production_classifier_sha256")
        != current_classifier["sha256"]
        or value.get("contract_spec_sha256") != current_spec["sha256"]
    ):
        raise QualificationError("P2.82 classifier QEMU source binding changed")
    substrate = value["substrate"]
    expected_pins = {
        "kernel": classifier_qemu.PINNED_KERNEL_SHA256,
        "config": classifier_qemu.PINNED_CONFIG_SHA256,
        "qemu": classifier_qemu.PINNED_QEMU_SHA256,
    }
    for name, digest in expected_pins.items():
        if substrate[name].get("sha256") != digest:
            raise QualificationError(
                f"P2.82 classifier QEMU {name} pin drifted"
            )
        material = _material(
            Path(substrate[name]["path"]),
            f"P2.82 classifier QEMU {name}",
        )
        if material["sha256"] != digest:
            raise QualificationError(
                f"P2.82 classifier QEMU {name} material changed"
            )
    command = value.get("command")
    if (
        not isinstance(command, list)
        or any(not isinstance(item, str) for item in command)
        or command.count("-initrd") != 1
        or command.count("-kernel") != 1
    ):
        raise QualificationError("P2.82 classifier QEMU command drifted")
    initramfs = _material(
        Path(command[command.index("-initrd") + 1]),
        "P2.82 classifier QEMU initramfs",
    )
    if initramfs["sha256"] != value.get("initramfs_sha256"):
        raise QualificationError("P2.82 classifier QEMU initramfs changed")
    return {
        **_result_binding(root, path, receipt, "P2.82 classifier QEMU result"),
        "semantics": {
            "details_covered": 46,
            "tuple_count": 567,
            "production_classifier_sha256": current_classifier["sha256"],
            "contract_spec_sha256": current_spec["sha256"],
            "generated_contract_sha256": value["generated_contract_sha256"],
            "guest_source_sha256": value["guest_source_sha256"],
            "qemu_output_sha256": value["qemu_output_sha256"],
            "elapsed_sec": value["elapsed_sec"],
            "substrate": substrate,
        },
        "verified": True,
    }


def _timing_gate() -> dict[str, Any]:
    source = _stable_read(
        GATE_IMPLEMENTATION_SOURCES["observer"],
        "P2.82 observer source",
        4 * 1024 * 1024,
    )
    matches = re.findall(
        rb"^MAX_SEC = ([0-9]+(?:\.[0-9]+)?)$", source, re.MULTILINE
    )
    if len(matches) != 1:
        raise QualificationError("observer guard lifetime is not explicit")
    guard_lifetime = float(matches[0])
    if guard_lifetime < MIN_GUARD_LIFETIME_SEC:
        raise QualificationError(
            "observer guard lifetime does not cover the P2.82 worst case"
        )
    if (
        spec.CYCLE_DEADLINE_SEC != 30
        or spec.FINAL_DEADLINE_SEC != 30
        or P282_ADDITIONAL_CYCLE_BUDGET_SEC != 60
    ):
        raise QualificationError("P2.82 timing constants drifted")
    return {
        "p280_observation_base_sec": EXPECTED_OBSERVATION_BASE_SEC,
        "p282_added_cycle_budget_sec": P282_ADDITIONAL_CYCLE_BUDGET_SEC,
        "minimum_observation_timeout_sec": MIN_OBSERVATION_TIMEOUT_SEC,
        "minimum_guard_lifetime_sec": MIN_GUARD_LIFETIME_SEC,
        "actual_guard_lifetime_sec": guard_lifetime,
        "exact_banner_survives_guard_loss": True,
        "banner_absence_under_guard_loss_is_indeterminate": True,
        "verified": True,
    }


def _gate_implementation() -> dict[str, Any]:
    result = {
        name: _material(path, f"P2.82 gate implementation {name}")
        for name, path in GATE_IMPLEMENTATION_SOURCES.items()
    }
    linked = _load_linked_audit_module()
    result["linked_audit"] = _material(
        Path(linked.__file__), "P2.82 linked-audit implementation"
    )
    result["verified"] = True
    return result


def _candidate_binding(
    exact_contract: dict[str, Any],
    intent_path: Path,
    patch_path: Path,
) -> dict[str, Any]:
    root = candidate_contract.intent.repo_root()
    intent = _material(intent_path, "P2.82 candidate intent")
    patch = _material(patch_path, "P2.82 candidate patch")
    return {
        "run_id": exact_contract["run_id"],
        "profile": exact_contract["profile"],
        "source_contract_id": exact_contract["source_contract_id"],
        "candidate_contract_sha256": hashlib.sha256(
            _canonical(exact_contract)
        ).hexdigest(),
        "intent": intent,
        "intent_repo_path": _repo_relative(
            root, intent_path, "P2.82 candidate intent"
        ),
        "patch": patch,
        "patch_repo_path": _repo_relative(
            root, patch_path, "P2.82 candidate patch"
        ),
    }


def _gate_matrix(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    dependencies = (
        ("candidate", "implementation", "module_trace", "qemu_substrate"),
        ("userspace",),
        ("implementation", "classifier_qemu"),
        ("classifier_qemu",),
        ("focused_tests",),
        ("focused_tests",),
        ("focused_tests",),
        ("focused_tests",),
        ("focused_tests",),
        ("focused_tests",),
        ("focused_tests",),
        ("focused_tests",),
        ("closure", "focused_tests"),
        ("safety",),
        ("p260_qemu", "kprobe_qemu", "lifecycle_qemu"),
        ("linked_audit", "implementation", "module_trace"),
        ("geometry",),
        ("timing",),
        ("focused_tests", "historical_tests"),
    )
    if len(dependencies) != len(GATE_NAMES):
        raise QualificationError("P2.82 gate matrix cardinality drifted")
    rows = []
    for ordinal, (name, required) in enumerate(
        zip(GATE_NAMES, dependencies, strict=True), start=1
    ):
        if any(
            key not in evidence
            or not isinstance(evidence[key], dict)
            or evidence[key].get("verified") is not True
            for key in required
        ):
            raise QualificationError(f"P2.82 gate {ordinal} is not verified")
        rows.append(
            {
                "ordinal": ordinal,
                "name": name,
                "evidence": list(required),
                "verified": True,
            }
        )
    return rows


def _gate_result_receipts(
    evidence: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    expected = (
        "classifier_qemu",
        "kprobe_qemu",
        "lifecycle_qemu",
        "linked_audit",
        "p260_qemu",
        "userspace",
    )
    result: dict[str, dict[str, Any]] = {}
    for name in expected:
        row = evidence.get(name)
        if not isinstance(row, dict):
            raise QualificationError(
                f"P2.82 {name} gate evidence is missing"
            )
        result[name] = _receipt_identity(
            row.get("result"), f"P2.82 {name} gate result"
        )
    return result


def _stored_result_path(
    root: Path, row: Any, label: str
) -> Path:
    if not isinstance(row, dict):
        raise QualificationError(f"{label} evidence is missing")
    relative = row.get("result_repo_path")
    if (
        not isinstance(relative, str)
        or not relative
        or Path(relative).is_absolute()
        or ".." in Path(relative).parts
    ):
        raise QualificationError(f"{label} result path is invalid")
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise QualificationError(
            f"{label} result path escapes the repository"
        ) from exc
    return path


def _current_evidence(
    exact_contract: dict[str, Any],
    stored: dict[str, Any],
) -> dict[str, Any]:
    root = candidate_contract.intent.repo_root()
    implementation = p282.implementation_result(root)
    _source_data, source_receipts = p282.source_receipts(root)
    implementation_evidence = {
        "schema": implementation["schema"],
        "verdict": implementation["verdict"],
        "generated": implementation["generated"],
        "source_receipts": source_receipts,
        "verified": True,
    }
    module_trace = trace_contract.derive_module_contract(
        dwc3_msm_module=root / p282.DEFAULT_DWC3_MSM_MODULE,
        hsphy_module=root / p282.DEFAULT_HSPHY_MODULE,
    )
    closure_result = closure.build_result(root)
    if (
        closure_result.get("verdict") != closure.VERDICT
        or closure_result.get("verified") is not True
    ):
        raise QualificationError("P2.82 stock closure is stale")
    try:
        p260_gate = p280q._verify_p260_qemu(
            _stored_result_path(
                root, stored.get("p260_qemu"), "P2.60 QEMU"
            )
        )
        kprobe_gate = p280q._verify_kprobe_qemu(
            _stored_result_path(
                root, stored.get("kprobe_qemu"), "P2.80 Kprobe QEMU"
            )
        )
        lifecycle_gate = p280q._verify_lifecycle_qemu(
            _stored_result_path(
                root,
                stored.get("lifecycle_qemu"),
                "P2.80 lifecycle QEMU",
            )
        )
    except p280q.QualificationError as exc:
        raise QualificationError(str(exc)) from exc
    linked_gate = _verify_linked_audit_receipt(
        _stored_result_path(
            root, stored.get("linked_audit"), "P2.82 linked audit"
        )
    )
    reachable = p282.validate_reachable_records(
        bytes.fromhex(exact_contract["run_id"])
    )
    current = {
        "candidate": {
            "contract_sha256": hashlib.sha256(
                _canonical(exact_contract)
            ).hexdigest(),
            "verified": True,
        },
        "implementation": implementation_evidence,
        "module_trace": {**module_trace, "verified": True},
        "qemu_substrate": {
            "kernel_sha256": classifier_qemu.PINNED_KERNEL_SHA256,
            "config_sha256": classifier_qemu.PINNED_CONFIG_SHA256,
            "verified": True,
        },
        "userspace": _verify_userspace(
            _stored_result_path(
                root, stored.get("userspace"), "P2.82 userspace"
            ),
            exact_contract,
        ),
        "classifier_qemu": _verify_classifier_qemu(
            _stored_result_path(
                root,
                stored.get("classifier_qemu"),
                "P2.82 classifier QEMU",
            )
        ),
        "focused_tests": _verify_test_gate(
            stored.get("focused_tests"), root, FOCUSED_TESTS, "P2.82 focused"
        ),
        "closure": {**closure_result, "verified": True},
        "safety": {
            "dictionary": _expected_safety(exact_contract),
            "verified": True,
        },
        "p260_qemu": p260_gate,
        "kprobe_qemu": kprobe_gate,
        "lifecycle_qemu": lifecycle_gate,
        "linked_audit": linked_gate,
        "geometry": {
            "carrier_bytes": 45,
            "terminal_generation": 92,
            "reachable": reachable,
            "verified": True,
        },
        "timing": _timing_gate(),
        "historical_tests": _verify_test_gate(
            stored.get("historical_tests"),
            root,
            HISTORICAL_PROCESS_V2_TESTS,
            "P2.82 Process v2 regression",
        ),
    }
    if set(current) != set(stored):
        raise QualificationError("P2.82 evidence inventory drifted")
    return current


def create(
    *,
    source: Path,
    intent_path: Path,
    patch_path: Path,
    userspace_result: Path,
    p260_qemu_result: Path,
    kprobe_result: Path,
    lifecycle_result: Path,
    classifier_result: Path,
    linked_audit_result: Path,
) -> dict[str, Any]:
    root = candidate_contract.intent.repo_root()
    exact_contract = candidate_contract.verify(
        root, source, intent_path, patch_path
    )
    if exact_contract.get("source_contract_id") != p282.CONTRACT_ID:
        raise QualificationError("qualification is only valid for P2.82")
    implementation = p282.implementation_result(root)
    if implementation.get("verdict") != p282.IMPLEMENTATION_VERDICT:
        raise QualificationError("P2.82 implementation gate did not pass")
    _source_data, source_receipts = p282.source_receipts(root)
    module_trace = trace_contract.derive_module_contract(
        dwc3_msm_module=root / p282.DEFAULT_DWC3_MSM_MODULE,
        hsphy_module=root / p282.DEFAULT_HSPHY_MODULE,
    )
    if (
        module_trace.get("schema")
        != "s22plus_fyg8_p282_module_trace_contract_v1"
        or len(module_trace.get("modules", ())) != 2
    ):
        raise QualificationError("P2.82 module trace contract drifted")
    reachable = p282.validate_reachable_records(
        bytes.fromhex(exact_contract["run_id"])
    )
    closure_result = closure.build_result(root)
    if (
        closure_result.get("verdict") != closure.VERDICT
        or closure_result.get("verified") is not True
        or closure_result.get("module_count") != 60
    ):
        raise QualificationError("P2.82 stock closure did not verify")
    focused = _run_test_command(root, FOCUSED_TESTS, "P2.82 focused")
    historical = _run_test_command(
        root, HISTORICAL_PROCESS_V2_TESTS, "P2.82 Process v2 regression"
    )
    try:
        p260_gate = p280q._verify_p260_qemu(p260_qemu_result)
        kprobe_gate = p280q._verify_kprobe_qemu(kprobe_result)
        lifecycle_gate = p280q._verify_lifecycle_qemu(lifecycle_result)
    except p280q.QualificationError as exc:
        raise QualificationError(str(exc)) from exc
    classifier_gate = _verify_classifier_qemu(classifier_result)
    linked_gate = _verify_linked_audit_receipt(linked_audit_result)
    safety = _expected_safety(exact_contract)
    timing = _timing_gate()
    evidence = {
        "candidate": {
            "contract_sha256": hashlib.sha256(
                _canonical(exact_contract)
            ).hexdigest(),
            "verified": True,
        },
        "implementation": {
            "schema": implementation["schema"],
            "verdict": implementation["verdict"],
            "generated": implementation["generated"],
            "source_receipts": source_receipts,
            "verified": True,
        },
        "module_trace": {**module_trace, "verified": True},
        "qemu_substrate": {
            "kernel_sha256": classifier_qemu.PINNED_KERNEL_SHA256,
            "config_sha256": classifier_qemu.PINNED_CONFIG_SHA256,
            "verified": True,
        },
        "userspace": _verify_userspace(userspace_result, exact_contract),
        "classifier_qemu": classifier_gate,
        "focused_tests": focused,
        "closure": {**closure_result, "verified": True},
        "safety": {"dictionary": safety, "verified": True},
        "p260_qemu": p260_gate,
        "kprobe_qemu": kprobe_gate,
        "lifecycle_qemu": lifecycle_gate,
        "linked_audit": linked_gate,
        "geometry": {
            "carrier_bytes": 45,
            "terminal_generation": 92,
            "reachable": reachable,
            "verified": True,
        },
        "timing": timing,
        "historical_tests": historical,
    }
    gates = _gate_matrix(evidence)
    payload = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "build_allowed": True,
        "candidate": _candidate_binding(
            exact_contract, intent_path, patch_path
        ),
        "implementation": evidence["implementation"],
        "gate_implementation": _gate_implementation(),
        "evidence": evidence,
        "gates": gates,
        "safety": {
            "host_only": True,
            "kernel_built": False,
            "full_lto_started": False,
            "candidate_created": False,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        },
    }
    return {
        **payload,
        "payload_sha256": hashlib.sha256(_canonical(payload)).hexdigest(),
    }


def verify_receipt(
    path: Path,
    exact_contract: dict[str, Any],
    *,
    intent_path: Path,
    patch_path: Path,
) -> dict[str, Any]:
    root = candidate_contract.intent.repo_root()
    value, qualification_receipt = _load_json(
        path, "P2.82 pre-LTO qualification"
    )
    if set(value) != {
        "build_allowed",
        "candidate",
        "evidence",
        "gate_implementation",
        "gates",
        "implementation",
        "payload_sha256",
        "safety",
        "schema",
        "verdict",
    }:
        raise QualificationError("P2.82 qualification schema is not exact")
    payload = dict(value)
    digest = payload.pop("payload_sha256", None)
    if digest != hashlib.sha256(_canonical(payload)).hexdigest():
        raise QualificationError("P2.82 qualification payload digest mismatch")
    if (
        value.get("schema") != SCHEMA
        or value.get("verdict") != VERDICT
        or value.get("build_allowed") is not True
        or exact_contract.get("source_contract_id") != p282.CONTRACT_ID
        or value.get("safety")
        != {
            "host_only": True,
            "kernel_built": False,
            "full_lto_started": False,
            "candidate_created": False,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        }
    ):
        raise QualificationError("P2.82 qualification identity mismatch")
    candidate = value.get("candidate")
    current_candidate = _candidate_binding(
        exact_contract, intent_path, patch_path
    )
    if candidate != current_candidate:
        raise QualificationError(
            "P2.82 qualification is bound to different inputs"
        )
    current_implementation = p282.implementation_result(root)
    _source_data, current_receipts = p282.source_receipts(root)
    expected_implementation = {
        "schema": current_implementation["schema"],
        "verdict": current_implementation["verdict"],
        "generated": current_implementation["generated"],
        "source_receipts": current_receipts,
        "verified": True,
    }
    if value.get("implementation") != expected_implementation:
        raise QualificationError("P2.82 qualification source binding is stale")
    current_gate_implementation = _gate_implementation()
    if value.get("gate_implementation") != current_gate_implementation:
        raise QualificationError(
            "P2.82 qualification implementation binding is stale"
        )
    evidence = value.get("evidence")
    if not isinstance(evidence, dict):
        raise QualificationError("P2.82 qualification evidence is invalid")
    if evidence != _current_evidence(exact_contract, evidence):
        raise QualificationError("P2.82 qualification evidence is stale")
    gates = value.get("gates")
    if (
        not isinstance(gates, list)
        or gates != _gate_matrix(evidence)
        or len(gates) != 19
    ):
        raise QualificationError("P2.82 qualification gate matrix drifted")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "build_allowed": True,
        "run_id": exact_contract["run_id"],
        "source_contract_id": p282.CONTRACT_ID,
        "qualification": qualification_receipt,
        "qualification_repo_path": _repo_relative(
            root, path, "P2.82 pre-LTO qualification"
        ),
        "intent_repo_path": candidate["intent_repo_path"],
        "patch_repo_path": candidate["patch_repo_path"],
        "gate_result_receipts": _gate_result_receipts(evidence),
        "gate_count": 19,
        "verified": True,
    }


def _resolve(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else root / value


def _write_exclusive(path: Path, value: dict[str, Any]) -> None:
    try:
        p280q._write_exclusive(path, value)
    except p280q.QualificationError as exc:
        raise QualificationError(str(exc)) from exc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=candidate_contract.DEFAULT_SOURCE)
    parser.add_argument("--intent", type=Path)
    parser.add_argument("--patch", type=Path)
    parser.add_argument(
        "--userspace-result", type=Path, default=DEFAULT_USERSPACE_RESULT
    )
    parser.add_argument(
        "--p260-qemu-result", type=Path, default=DEFAULT_P260_QEMU_RESULT
    )
    parser.add_argument(
        "--kprobe-result", type=Path, default=DEFAULT_KPROBE_RESULT
    )
    parser.add_argument(
        "--lifecycle-result", type=Path, default=DEFAULT_LIFECYCLE_RESULT
    )
    parser.add_argument(
        "--classifier-result", type=Path, default=DEFAULT_CLASSIFIER_RESULT
    )
    parser.add_argument(
        "--linked-audit-result",
        type=Path,
        default=DEFAULT_LINKED_AUDIT_RESULT,
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--emit-linked-audit-receipt", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = candidate_contract.intent.repo_root()
    try:
        linked_path = _resolve(root, args.linked_audit_result)
        if args.emit_linked_audit_receipt:
            result = create_linked_audit_receipt(root)
            _write_exclusive(linked_path, result)
            printed = {
                "schema": LINKED_META_SCHEMA,
                "verdict": LINKED_META_VERDICT,
                "out": str(linked_path),
            }
        else:
            if args.intent is None or args.patch is None:
                raise QualificationError("--intent and --patch are required")
            result = create(
                source=_resolve(root, args.source),
                intent_path=_resolve(root, args.intent),
                patch_path=_resolve(root, args.patch),
                userspace_result=_resolve(root, args.userspace_result),
                p260_qemu_result=_resolve(root, args.p260_qemu_result),
                kprobe_result=_resolve(root, args.kprobe_result),
                lifecycle_result=_resolve(root, args.lifecycle_result),
                classifier_result=_resolve(root, args.classifier_result),
                linked_audit_result=linked_path,
            )
            out = _resolve(root, args.out)
            _write_exclusive(out, result)
            printed = {
                "schema": SCHEMA,
                "verdict": VERDICT,
                "run_id": result["candidate"]["run_id"],
                "out": str(out),
            }
    except (
        QualificationError,
        candidate_contract.ContractError,
        candidate_contract.intent.IntentError,
        p282.SourceContractError,
        closure.ClosureError,
        classifier_qemu.HarnessError,
        OSError,
        subprocess.TimeoutExpired,
    ) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}
            )
        )
        return 1
    print(json.dumps(printed, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Pre-Full-LTO qualification for the P2.86 bounded-restart successor."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
from typing import Any, Iterator

import build_s22plus_fyg8_p286_candidate as candidate_builder
import s22plus_fyg8_p282_pre_lto_qualification as base
import s22plus_fyg8_p284_sysfs_ingestion_oracle as ingestion
import s22plus_fyg8_p286_candidate_contract as candidate_contract
import s22plus_fyg8_p286_contract_spec as spec
import s22plus_fyg8_p286_e2_stock_closure as closure
import s22plus_fyg8_p286_source_contract as p286


SCHEMA = "s22plus_fyg8_p286_pre_lto_qualification_v1"
VERDICT = "PASS_P286_PRE_FULL_LTO_QUALIFICATION_HOST_ONLY"
LINKED_META_SCHEMA = "s22plus_fyg8_p286_linked_audit_meta_v1"
LINKED_META_VERDICT = "PASS_P286_LINKED_AUDIT_META_HOST_ONLY"
LINKED_AUDIT_MODULE_NAME = "s22plus_fyg8_p286_linked_audit"
LINKED_AUDIT_TEST = Path(
    "tests/test_s22plus_fyg8_p286_change_freeze.py"
)
DEFAULT_LINKED_AUDIT_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p286_pre_lto/"
    "linked-audit-meta.json"
)
DEFAULT_INGESTION_RESULT = ingestion.DEFAULT_OUT
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p286_pre_lto/"
    "qualification.json"
)
FOCUSED_TESTS = (
    *base.FOCUSED_TESTS,
    Path("tests/test_s22plus_fyg8_p284_sysfs_ingestion_oracle.py"),
    Path("tests/test_s22plus_fyg8_p286_change_freeze.py"),
)
GATE_NAMES = (
    *base.GATE_NAMES,
    "20-source-bound-sysfs-ingestion",
)
GATE_IMPLEMENTATION_SOURCES = {
    **base.GATE_IMPLEMENTATION_SOURCES,
    "closure": (
        base.SCRIPT_DIR / "s22plus_fyg8_p286_e2_stock_closure.py"
    ),
    "p286_qualification": Path(__file__).resolve(),
    "p286_source_contract": (
        base.SCRIPT_DIR / "s22plus_fyg8_p286_source_contract.py"
    ),
    "p286_contract_spec": (
        base.SCRIPT_DIR / "s22plus_fyg8_p286_contract_spec.py"
    ),
    "p286_linked_audit": (
        base.SCRIPT_DIR / "s22plus_fyg8_p286_linked_audit.py"
    ),
    "p284_sysfs_ingestion_oracle": (
        base.SCRIPT_DIR / "s22plus_fyg8_p284_sysfs_ingestion_oracle.py"
    ),
}

QualificationError = base.QualificationError


@contextmanager
def _base_context() -> Iterator[None]:
    replacements = {
        "p282": p286,
        "spec": spec,
        "closure": closure,
        "candidate_contract": candidate_contract,
        "candidate_builder": candidate_builder,
        "SCHEMA": SCHEMA,
        "VERDICT": VERDICT,
        "FOCUSED_TESTS": FOCUSED_TESTS,
        "GATE_IMPLEMENTATION_SOURCES": GATE_IMPLEMENTATION_SOURCES,
        "_load_linked_audit_module": _load_linked_audit_module,
        "_verify_linked_audit_receipt": _verify_linked_audit_receipt,
    }
    previous = {name: getattr(base, name) for name in replacements}
    for name, value in replacements.items():
        setattr(base, name, value)
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(base, name, value)


def _load_linked_audit_module():
    try:
        module = importlib.import_module(LINKED_AUDIT_MODULE_NAME)
    except (ImportError, OSError) as exc:
        raise QualificationError(
            "P2.86 linked-audit module is unavailable"
        ) from exc
    if (
        getattr(module, "EXPECTED_SOURCE_CONTRACT_ID", None)
        != p286.CONTRACT_ID
        or getattr(module, "ADAPTER_ID", None)
        != "s22plus-fyg8-p286-linked-audit-v1"
    ):
        raise QualificationError("P2.86 linked-audit identity drifted")
    return module


def create_linked_audit_receipt(root: Path) -> dict[str, Any]:
    module = _load_linked_audit_module()
    test = base._run_test_command(
        root, (LINKED_AUDIT_TEST,), "P2.86 linked audit"
    )
    payload = base._portable_repo_paths(
        root,
        {
            "schema": LINKED_META_SCHEMA,
            "verdict": LINKED_META_VERDICT,
            "source_contract_id": p286.CONTRACT_ID,
            "adapter_id": module.ADAPTER_ID,
            "module": base._material(
                root
                / "workspace/public/src/scripts/revalidation/"
                "s22plus_fyg8_p286_linked_audit.py",
                "P2.86 linked-audit module",
            ),
            "known_good": base._known_good_linked_binding(root),
            "test": test,
            "verified": True,
        },
    )
    return {
        **payload,
        "payload_sha256": hashlib.sha256(
            base._canonical(payload)
        ).hexdigest(),
    }


def _verify_linked_audit_receipt(path: Path) -> dict[str, Any]:
    root = candidate_contract.intent.repo_root()
    module = _load_linked_audit_module()
    value, receipt = base._load_json(path, "P2.86 linked-audit receipt")
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
        raise QualificationError("P2.86 linked-audit receipt shape drifted")
    payload = dict(value)
    digest = payload.pop("payload_sha256", None)
    if digest != hashlib.sha256(base._canonical(payload)).hexdigest():
        raise QualificationError("P2.86 linked-audit receipt digest mismatch")
    expected_module = base._repo_material(
        root,
        root
        / "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p286_linked_audit.py",
        "P2.86 linked-audit module",
    )
    test = value.get("test")
    expected_command = [
        base.sys.executable,
        "-m",
        "unittest",
        "-v",
        str(LINKED_AUDIT_TEST),
    ]
    expected_sources = {
        str(LINKED_AUDIT_TEST): base._repo_material(
            root,
            root / LINKED_AUDIT_TEST,
            "P2.86 linked-audit test",
        )
    }
    if (
        value.get("schema") != LINKED_META_SCHEMA
        or value.get("verdict") != LINKED_META_VERDICT
        or value.get("source_contract_id") != p286.CONTRACT_ID
        or value.get("adapter_id") != module.ADAPTER_ID
        or value.get("module") != expected_module
        or value.get("known_good") != base._known_good_linked_binding(root)
        or value.get("verified") is not True
        or not isinstance(test, dict)
        or set(test)
        != {
            "command",
            "output_sha256",
            "sources",
            "test_count",
            "verified",
        }
        or test.get("command") != expected_command
        or test.get("sources") != expected_sources
        or isinstance(test.get("test_count"), bool)
        or not isinstance(test.get("test_count"), int)
        or test["test_count"] < 1
        or not isinstance(test.get("output_sha256"), str)
        or base.HEX64_RE.fullmatch(test["output_sha256"]) is None
        or test.get("verified") is not True
    ):
        raise QualificationError("P2.86 linked-audit receipt is stale")
    return {
        **base._result_binding(root, path, receipt, "P2.86 linked audit"),
        "semantics": {
            "adapter_id": module.ADAPTER_ID,
            "source_contract_id": p286.CONTRACT_ID,
            "test_count": test.get("test_count"),
            "output_sha256": test.get("output_sha256"),
            "known_good_vmlinux_sha256": value["known_good"]["vmlinux"][
                "sha256"
            ],
            "known_good_config_sha256": value["known_good"]["config"][
                "sha256"
            ],
        },
        "verified": True,
    }


def _verify_ingestion_oracle(
    path: Path, *, verify_materials: bool = True
) -> dict[str, Any]:
    root = candidate_contract.intent.repo_root()
    value, receipt = base._load_json(path, "P2.84 sysfs ingestion result")
    expected_cases = {
        "source_tokens": 9,
        "valid_mismatch_retry": True,
        "empty_read_retry": True,
        "missing_newline_hard": True,
        "overflow_hard": True,
        "retry_errno_count": 3,
        "representative_hard_errno_count": 8,
    }
    if (
        value.get("schema") != ingestion.SCHEMA
        or value.get("verdict") != ingestion.VERDICT
        or value.get("verified") is not True
        or value.get("source_contract", {}).get("verified") is not True
        or value.get("runtime_sources", {}).get("verified") is not True
        or value.get("harness", {}).get("verified") is not True
        or value.get("harness", {}).get("cases") != expected_cases
        or value.get("policy", {}).get("verified") is not True
        or value.get("policy", {}).get(
            "unknown_kernel_errno_is_not_silently_retried"
        )
        is not True
    ):
        raise QualificationError("P2.84 sysfs ingestion result is incomplete")
    source_contract = value["source_contract"]
    expected_hashes = (
        ("dwc3_source", ingestion.PINNED_DWC3_SOURCE_SHA256),
        ("power_source", ingestion.PINNED_POWER_SOURCE_SHA256),
        ("mode_show", ingestion.PINNED_MODE_SHOW_SHA256),
        (
            "runtime_status_show",
            ingestion.PINNED_RUNTIME_STATUS_SHOW_SHA256,
        ),
    )
    if any(
        source_contract.get(name, {}).get("sha256") != digest
        for name, digest in expected_hashes
    ):
        raise QualificationError("P2.84 FYG8 source binding differs")
    runtime_sources = value["runtime_sources"]
    for name, relative in (
        ("p260", ingestion.DEFAULT_RUNTIME_SOURCE),
        ("p282", ingestion.DEFAULT_P282_RUNTIME_SOURCE),
    ):
        current = base._material(root / relative, f"P2.84 {name} runtime")
        if runtime_sources.get(name) != {
            "size": current["size"],
            "sha256": current["sha256"],
        }:
            raise QualificationError(
                f"P2.84 {name} runtime source binding changed"
            )
    if verify_materials:
        for relative, digest, label in (
            (
                ingestion.DEFAULT_DWC3_SOURCE,
                ingestion.PINNED_DWC3_SOURCE_SHA256,
                "FYG8 dwc3-msm source",
            ),
            (
                ingestion.DEFAULT_POWER_SOURCE,
                ingestion.PINNED_POWER_SOURCE_SHA256,
                "FYG8 power sysfs source",
            ),
        ):
            if base._material(root / relative, label)["sha256"] != digest:
                raise QualificationError(f"P2.84 {label} changed")
        for name in ("compiler", "qemu"):
            row = value["harness"].get("substrate", {}).get(name)
            if not isinstance(row, dict):
                raise QualificationError(
                    f"P2.84 {name} substrate is missing"
                )
            current = base._material(Path(row.get("path", "")), name)
            if any(
                row.get(key) != current[key] for key in ("size", "sha256")
            ):
                raise QualificationError(
                    f"P2.84 {name} substrate changed"
                )
            executable = Path(row["path"])
            try:
                version = subprocess.run(
                    [str(executable), "--version"],
                    check=True,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=10,
                ).stdout
            except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                raise QualificationError(
                    f"P2.84 {name} substrate version is unavailable"
                ) from exc
            if row.get("version_sha256") != hashlib.sha256(
                version.encode("utf-8")
            ).hexdigest():
                raise QualificationError(
                    f"P2.84 {name} substrate version changed"
                )
    return {
        **base._result_binding(root, path, receipt, "P2.84 ingestion result"),
        "schema": value["schema"],
        "verdict": value["verdict"],
        "source_contract": source_contract,
        "runtime_sources": runtime_sources,
        "harness": value["harness"],
        "policy": value["policy"],
        "verified": True,
    }


def _gate_implementation() -> dict[str, Any]:
    with _base_context():
        return base._gate_implementation()


def _gate_matrix(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    with _base_context():
        rows = base._gate_matrix(evidence)
    ingestion_row = evidence.get("sysfs_ingestion")
    if not isinstance(ingestion_row, dict) or ingestion_row.get(
        "verified"
    ) is not True:
        raise QualificationError("P2.84 ingestion gate is unverified")
    return [
        *rows,
        {
            "ordinal": 20,
            "name": GATE_NAMES[-1],
            "evidence": ["sysfs_ingestion"],
            "verified": True,
        },
    ]


def _gate_result_receipts(
    evidence: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    result = base._gate_result_receipts(evidence)
    row = evidence.get("sysfs_ingestion")
    if not isinstance(row, dict):
        raise QualificationError("P2.84 ingestion evidence is missing")
    result["sysfs_ingestion"] = base._receipt_identity(
        row.get("result"), "P2.84 ingestion gate result"
    )
    return result


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
    ingestion_result: Path,
) -> dict[str, Any]:
    root = candidate_contract.intent.repo_root()
    with _base_context():
        value = base.create(
            source=source,
            intent_path=intent_path,
            patch_path=patch_path,
            userspace_result=userspace_result,
            p260_qemu_result=p260_qemu_result,
            kprobe_result=kprobe_result,
            lifecycle_result=lifecycle_result,
            classifier_result=classifier_result,
            linked_audit_result=linked_audit_result,
        )
    payload = dict(value)
    payload.pop("payload_sha256")
    payload["evidence"] = {
        **payload["evidence"],
        "sysfs_ingestion": base._portable_repo_paths(
            root, _verify_ingestion_oracle(ingestion_result)
        ),
    }
    payload["gates"] = _gate_matrix(payload["evidence"])
    payload["gate_implementation"] = _gate_implementation()
    return {
        **payload,
        "payload_sha256": hashlib.sha256(
            base._canonical(payload)
        ).hexdigest(),
    }


def _current_evidence(
    exact_contract: dict[str, Any], stored: dict[str, Any]
) -> dict[str, Any]:
    base_stored = dict(stored)
    ingestion_stored = base_stored.pop("sysfs_ingestion", None)
    with _base_context():
        current = base._current_evidence(exact_contract, base_stored)
    current["sysfs_ingestion"] = _verify_ingestion_oracle(
        base._stored_result_path(
            candidate_contract.intent.repo_root(),
            ingestion_stored,
            "P2.84 ingestion",
        ),
        verify_materials=False,
    )
    return base._portable_repo_paths(
        candidate_contract.intent.repo_root(), current
    )


def verify_receipt(
    path: Path,
    exact_contract: dict[str, Any],
    *,
    intent_path: Path,
    patch_path: Path,
) -> dict[str, Any]:
    root = candidate_contract.intent.repo_root()
    value, qualification_receipt = base._load_json(
        path, "P2.86 pre-LTO qualification"
    )
    payload = dict(value)
    digest = payload.pop("payload_sha256", None)
    if (
        set(value)
        != {
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
        }
        or digest != hashlib.sha256(base._canonical(payload)).hexdigest()
        or value.get("schema") != SCHEMA
        or value.get("verdict") != VERDICT
        or value.get("build_allowed") is not True
        or exact_contract.get("source_contract_id") != p286.CONTRACT_ID
    ):
        raise QualificationError("P2.86 qualification header is invalid")
    expected_safety = {
        "host_only": True,
        "kernel_built": False,
        "full_lto_started": False,
        "candidate_created": False,
        "device_contact": False,
        "device_write": False,
        "odin_invoked": False,
        "live_authorized": False,
    }
    if value.get("safety") != expected_safety:
        raise QualificationError("P2.86 qualification safety differs")
    candidate = base._candidate_binding(
        exact_contract, intent_path, patch_path
    )
    if value.get("candidate") != candidate:
        raise QualificationError("P2.86 qualification inputs differ")
    implementation = p286.implementation_result(root)
    _data, receipts = p286.source_receipts(root)
    expected_implementation = {
        "schema": implementation["schema"],
        "verdict": implementation["verdict"],
        "generated": implementation["generated"],
        "source_receipts": receipts,
        "verified": True,
    }
    if value.get("implementation") != expected_implementation:
        raise QualificationError("P2.86 implementation binding is stale")
    if value.get("gate_implementation") != _gate_implementation():
        raise QualificationError("P2.86 gate implementation is stale")
    evidence = value.get("evidence")
    if (
        not isinstance(evidence, dict)
        or evidence != _current_evidence(exact_contract, evidence)
    ):
        raise QualificationError("P2.86 evidence is stale")
    if value.get("gates") != _gate_matrix(evidence):
        raise QualificationError("P2.86 gate matrix drifted")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "build_allowed": True,
        "run_id": exact_contract["run_id"],
        "source_contract_id": p286.CONTRACT_ID,
        "qualification": qualification_receipt,
        "qualification_repo_path": base._repo_relative(
            root, path, "P2.86 qualification"
        ),
        "intent_repo_path": candidate["intent_repo_path"],
        "patch_repo_path": candidate["patch_repo_path"],
        "gate_result_receipts": _gate_result_receipts(evidence),
        "gate_count": 20,
        "verified": True,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=base.candidate_contract.DEFAULT_SOURCE)
    parser.add_argument("--intent", type=Path)
    parser.add_argument("--patch", type=Path)
    parser.add_argument(
        "--userspace-result", type=Path, default=base.DEFAULT_USERSPACE_RESULT
    )
    parser.add_argument(
        "--p260-qemu-result", type=Path, default=base.DEFAULT_P260_QEMU_RESULT
    )
    parser.add_argument(
        "--kprobe-result", type=Path, default=base.DEFAULT_KPROBE_RESULT
    )
    parser.add_argument(
        "--lifecycle-result", type=Path, default=base.DEFAULT_LIFECYCLE_RESULT
    )
    parser.add_argument(
        "--classifier-result", type=Path, default=base.DEFAULT_CLASSIFIER_RESULT
    )
    parser.add_argument(
        "--linked-audit-result",
        type=Path,
        default=DEFAULT_LINKED_AUDIT_RESULT,
    )
    parser.add_argument(
        "--ingestion-result",
        type=Path,
        default=DEFAULT_INGESTION_RESULT,
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--emit-linked-audit-receipt", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = candidate_contract.intent.repo_root()
    try:
        linked_path = base._resolve(root, args.linked_audit_result)
        if args.emit_linked_audit_receipt:
            result = create_linked_audit_receipt(root)
            base._write_exclusive(linked_path, result)
            printed = {
                "schema": LINKED_META_SCHEMA,
                "verdict": LINKED_META_VERDICT,
                "out": str(linked_path),
            }
        else:
            if args.intent is None or args.patch is None:
                raise QualificationError("--intent and --patch are required")
            result = create(
                source=base._resolve(root, args.source),
                intent_path=base._resolve(root, args.intent),
                patch_path=base._resolve(root, args.patch),
                userspace_result=base._resolve(root, args.userspace_result),
                p260_qemu_result=base._resolve(root, args.p260_qemu_result),
                kprobe_result=base._resolve(root, args.kprobe_result),
                lifecycle_result=base._resolve(root, args.lifecycle_result),
                classifier_result=base._resolve(root, args.classifier_result),
                linked_audit_result=linked_path,
                ingestion_result=base._resolve(root, args.ingestion_result),
            )
            out = base._resolve(root, args.out)
            base._write_exclusive(out, result)
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
        p286.SourceContractError,
        closure.ClosureError,
        OSError,
        subprocess.TimeoutExpired,
    ) as exc:
        print(json.dumps({"verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(printed, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

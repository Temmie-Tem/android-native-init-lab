#!/usr/bin/env python3
"""Fixed physical System-return and health closure for consumed A90 H40 run-01."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys


ROOT = Path(__file__).resolve().parents[5]
MODULE_DIR = Path(__file__).resolve().parent
SELF_PATH = Path(__file__).resolve()
ENGINE_PATH = MODULE_DIR / "a90_h28_physical_system_return_reconcile_v1.py"
OWNER_PATH = MODULE_DIR / "a90_boot_only_f1_minimal_v1.py"
FIXED_PYTHON = Path("/usr/bin/python3.14")
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))


class LaunchError(RuntimeError):
    """The fixed H40 entrypoint was not launched as reviewed."""


def _direct_owned_file(path: Path, label: str) -> None:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise LaunchError(f"{label} cannot be inspected") from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_uid != os.getuid()
        or metadata.st_gid != os.getgid()
        or metadata.st_mode & 0o022
    ):
        raise LaunchError(f"{label} identity is not exact")


def _require_launch_contract() -> None:
    if (
        Path(sys.executable) != FIXED_PYTHON
        or sys.dont_write_bytecode != 1
        or getattr(sys.flags, "dont_write_bytecode", 0) != 1
        or getattr(sys.flags, "no_user_site", 0) != 1
        or getattr(sys.flags, "ignore_environment", 0) != 1
        or Path.cwd() != ROOT
        or Path(__file__) != SELF_PATH
        or not sys.argv
        or Path(sys.argv[0]) != SELF_PATH
        or not sys.path
        or Path(sys.path[0]) != MODULE_DIR
    ):
        raise LaunchError("fixed H40 pre-import launch contract is not exact")
    _direct_owned_file(SELF_PATH, "fixed H40 reconciler")
    _direct_owned_file(ENGINE_PATH, "fixed physical-return engine")
    _direct_owned_file(OWNER_PATH, "fixed minimal owner")


def _load_engine():
    name = "_a90_h40_physical_system_return_engine_v1"
    spec = importlib.util.spec_from_file_location(name, ENGINE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("H40 physical-return engine import failed")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    if Path(module.__file__).resolve() != ENGINE_PATH:
        raise RuntimeError("H40 physical-return engine identity changed")
    return module


engine = _load_engine()
owner = engine.owner

CAPABILITY = "A90_H40_PHYSICAL_SYSTEM_RETURN_RECOVERY_V1"
RUN_ID = "a90-h40-f1-20260830-01"
MANIFEST_SHA256 = "a6c101fb2dfa0ad85bba1b73d1ebf9fcf973d46aaaf1e0f11981aba8fcf61ceb"
CANDIDATE_SHA256 = "68e12101e151f9515f2cf519f2749a8c1218e6c79a49aa4c9fcadd96b0728db0"
TERMINAL_SHA256 = "3edd5a2027d1db8b9d4a0acd3aa42e0c9c34644573113bb60f748a0a08824a3c"
ACTIVE_GUARD_SHA256 = "38f3156e5ba39fab4b4a6148a32f40834e6e6eb33e4591666e85ae1c2ef98fe0"
CANDIDATE_GUARD_SHA256 = "c86ffdc52c841f533a624de03455d45737661ee6bad4e5169467133525a1ac88"
QUALIFICATION_REVIEW_SIZE = 1277
QUALIFICATION_REVIEW_SHA256 = "5a3605e7aa915d75e840180f77c795f10fbe5a169a9064a81d58af5bb7869fc3"
QUALIFICATION_CLOSURE_SHA256 = "b7c6809cf0388da2a44f2aa9fbca99cc60e9e00d6fdddc32d39e91c70bc3ce6f"
RECORD_HASHES = {
    "00-prepared.json": "201ae953d84c90e5338f45724df77723351f01a069b3d84b1bf9c4b7ad135cd2",
    "10-approved.json": "8c2866477b9f635e49238360526e1f4ca8b341c4b06c3bcadc3d171e1789ac42",
    "11-recovery-transition-intent.json": "3ce0400e97aba30b7292d72d5466fead379dd03827f0b45653d263d5b4d7b0a4",
    "12-recovery-ready.json": "ccbbe186ee51132d41c16b9c3aacbe30a997c22e2bfc35401b3155b78f983e83",
    "20-candidate-intent.json": "b2ed0c312565e6c82fbdc9643f3e0a2b64327dc854a87439882d2dc846158100",
    "21-candidate-launched.json": "5446bd2e7ad4ac3fea3cf45d2cced7570fd26a1c4298b356959426e7e999c589",
    "22-candidate-result.json": "6fc3617d6043c95f1f2b1abec4292e437669167302fdf297a371876c2f0040a3",
    "26-failed-boot-evidence-intent.json": "fe772162af157b381a5fa5c9fedfeac94f51b3fdd66c64436fdddf899b0d6e55",
    "27-failed-boot-evidence-result.json": "fa1f80d8ad0de37e576a56a3ad509a78a2eeb73b4038aec1cafcc9bc17200f94",
    "30-rollback-intent.json": "d6af074221e27edae74ac592037c5f7d35db573310046f18635479d9879ccb21",
    "31-rollback-launched.json": "42a9642102a0461b6d97b1dad7a5b097c8da2ffd09b70599cd57439644d2b861",
    "32-rollback-result.json": "c9b62568567304ee4a681afcd5f0d25d0a2a0909bc1e16c1875c298e72575c39",
    "40-terminal.json": TERMINAL_SHA256,
}


def configure() -> None:
    source_rels = {
        *owner.EXECUTION_SOURCE_RELS,
        "workspace/public/src/scripts/server-distro/a90_h28_physical_system_return_reconcile_v1.py",
        "workspace/public/src/scripts/server-distro/a90_h40_physical_system_return_reconcile_v1.py",
        "tests/test_a90_h28_physical_system_return_reconcile_v1.py",
        "tests/test_a90_h40_physical_system_return_reconcile_v1.py",
        "AGENTS.md",
        "docs/operations/targets/A90_TARGET_CONTRACT.md",
        "GOAL_A90.md",
        "docs/reports/A90_H40_ROLLBACK_HEALTH_UNPROVED_INCIDENT_2026-08-30.md",
    }
    values = {
        "CAPABILITY": CAPABILITY,
        "SCHEMA": "a90-h40-physical-system-return-reconciliation-v1",
        "INTENT_SCHEMA": "a90-h40-physical-system-return-intent-v1",
        "OBSERVATION_SCHEMA": "a90-h40-native-observation-intent-v1",
        "RUN_ID": RUN_ID,
        "MANIFEST_PATH": ROOT / "workspace/private/manifests/a90-h40-f1-20260830-01.json",
        "MANIFEST_SHA256": MANIFEST_SHA256,
        "HISTORICAL_H28_MANIFEST_SHA256": "0" * 64,
        "HISTORICAL_H28_CANDIDATE_SHA256": CANDIDATE_SHA256,
        "TERMINAL_SHA256": TERMINAL_SHA256,
        "CURRENT_REVIEW_PATH": ROOT / "docs/reports/A90_H40_PHYSICAL_SYSTEM_RETURN_RECOVERY_REVIEW_2026-08-30.json",
        "SIDE_ROOT": owner.RUN_ROOT / "a90-h40-f1-20260830-01-physical-system-return-v1",
        "APPROVAL_PREFIX": "A90-H40-PHYSICAL-SYSTEM-RETURN-V1-APPROVE:",
        "INSTRUCTION": "A90 H40: on the attended A90 handset already showing TWRP, press Reboot -> System once.",
        "REVIEW_SCHEMA": "a90-h40-physical-system-return-independent-review-v1",
        "INCIDENT_NAMES": tuple(owner.CURRENT_ROLLBACK_WITH_FAILED_BOOT_EVIDENCE_PATH),
        "INCIDENT_RECORD_SHA256": RECORD_HASHES,
        "ACTIVE_GUARD_SHA256": ACTIVE_GUARD_SHA256,
        "CANDIDATE_GUARD_SHA256": CANDIDATE_GUARD_SHA256,
        "HISTORICAL_QUALIFICATION_REVIEW_PATH": ROOT / "docs/reports/A90_BOOT_ONLY_F1_MINIMAL_H40_INDEPENDENT_REVIEW_2026-08-30.json",
        "HISTORICAL_QUALIFICATION_REVIEW_SIZE": QUALIFICATION_REVIEW_SIZE,
        "HISTORICAL_QUALIFICATION_REVIEW_SHA256": QUALIFICATION_REVIEW_SHA256,
        "HISTORICAL_QUALIFICATION_CLOSURE_SHA256": QUALIFICATION_CLOSURE_SHA256,
        "EXECUTION_SOURCE_RELS": tuple(sorted(source_rels)),
    }
    for name, value in values.items():
        setattr(engine, name, value)


configure()
execution_closure_sha256 = engine.execution_closure_sha256
prepare = engine.prepare
authorize = engine.authorize
finalize = engine.finalize
ContractError = engine.ContractError


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    subparsers = result.add_subparsers(dest="action", required=True)
    subparsers.add_parser("prepare")
    authorize_parser = subparsers.add_parser("authorize")
    authorize_parser.add_argument("--approval", required=True)
    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument("--operator-attended", action="store_true")
    finalize_parser.add_argument("--physical-system-return-confirmed", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    _require_launch_contract()
    args = parser().parse_args(argv)
    if args.action == "prepare":
        print(prepare())
    elif args.action == "authorize":
        authorize(args.approval)
    else:
        print(json.dumps(finalize(
            operator_attended=args.operator_attended,
            physical_system_return_confirmed=args.physical_system_return_confirmed,
        ), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (LaunchError, ContractError, owner.ContractError) as exc:
        print(f"{CAPABILITY} NO_GO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

#!/usr/bin/env python3
"""Dormant attended Odin boot-only owner for the S20+ P0 PID1 ACM witness.

The implementation exact-loads the already reviewed B0 one-shot transfer and
resident-rollback engine in an isolated module instance.  Its explicit P0
profile binds the candidate, observer, append-only global no-replay registry,
raw ACM evidence, private journal namespace, approval prefixes, and terminal
spelling.  The ordinary B0 module and every closed B0 journal remain untouched.
"""

from __future__ import annotations

import argparse
import contextlib
import contextvars
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence


VERSION = "s20plus-g986n-p0-pid1-odin-f1-v1"
PLAN_SCHEMA = "s20plus_g986n_p0_pid1_odin_f1_plan_v1"
P0_F1_ACTIVE = False
EXPECTED_REVIEWED_NORMALIZED_SHA256 = "5cb67bc9f60e1576325be360b66bd8aff49d00d914f403f582e4a9324f54b410"

ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve()
RUN_ROOT = ROOT / "workspace/private/runs/s20plus-g986n-p0-pid1-odin-f1"
CLAIM_ROOT = RUN_ROOT / "consumed-candidates"
SHARED_GUARD = (
    ROOT / "workspace/private/runs/s20plus-g986n-routine-actions/active-action.json"
)

ENGINE_PATH = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_boot_recovery_canary_b0_f1.py"
)
ENGINE_SIZE = 224_559
ENGINE_SHA256 = "82ec4cee48c3a39aa8dc4de6136e8fda3fbefe88d4821a71bdb0df55d2a17c2a"
BASE_PATH = ROOT / (
    "workspace/public/src/scripts/revalidation/s20plus_g986n_d0_inventory.py"
)
BASE_SIZE = 21_474
BASE_SHA256 = "3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81"
RAW_CAPTURE_PATH = ROOT / (
    "workspace/public/src/scripts/revalidation/device_action_raw_capture_v1.py"
)
RAW_CAPTURE_SIZE = 25_006
RAW_CAPTURE_SHA256 = "410e260129c0c50dca29b008dc7cf1051ee007816ab18bea76aeae62505ca0e4"
BOOT_VERIFY_PATH = ROOT / (
    "workspace/public/src/scripts/revalidation/s22plus_boot_verify.py"
)
BOOT_VERIFY_SIZE = 37_806
BOOT_VERIFY_SHA256 = "e19d604039a744d14bcdbb495951e95f86666b6927061529e440aacb4b63381d"
TRANSPORT_PATH = ROOT / (
    "workspace/public/src/scripts/revalidation/s22plus_boot_only_f1_transport.py"
)
TRANSPORT_SIZE = 10_937
TRANSPORT_SHA256 = "f18e2e453e33078a184653722d4579a184c59b1c3ac10f9eb54d4a4ba437ffea"
OBSERVER_PATH = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_p0_pid1_usb_observer.py"
)
OBSERVER_DORMANT_SIZE = 16_487
OBSERVER_ACTIVE_SIZE = 16_486
OBSERVER_DORMANT_SHA256 = (
    "39ea696119c104952744f3937745bc56906e53e4b8fd4bb5b7128485f8d94041"
)
OBSERVER_ACTIVE_SHA256 = (
    "6e7e9c86d2bc2be412c45896fcab8af87c6f6cb2175ac574e9db3acb1bbdff69"
)
OBSERVER_NORMALIZED_SHA256 = (
    "980c354e4d31a315b0e0389255a8266d027315ec70fe22ed64204875a3a04232"
)
OBSERVER_SHA256_BY_ACTIVE = {
    False: OBSERVER_DORMANT_SHA256,
    True: OBSERVER_ACTIVE_SHA256,
}
OBSERVER_SIZE_BY_ACTIVE = {
    False: OBSERVER_DORMANT_SIZE,
    True: OBSERVER_ACTIVE_SIZE,
}
OBSERVER_SIZE = OBSERVER_SIZE_BY_ACTIVE[P0_F1_ACTIVE]
OBSERVER_SHA256 = OBSERVER_SHA256_BY_ACTIVE[P0_F1_ACTIVE]
BUILDER_PATH = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "build_s20plus_g986n_p0_pid1_acm_h0.py"
)
BUILDER_SIZE = 23_173
BUILDER_SHA256 = "de48f3c86812ac5debb007d8d601964670244a3c5def99438460aa83e13d5545"
INIT_SOURCE_PATH = (
    ROOT / "workspace/public/src/native-init/s20plus_p0_pid1_acm_init.c"
)
INIT_SOURCE_SIZE = 15_549
INIT_SOURCE_SHA256 = "16c21037094529bbce6158658f892aaa6d24412708ceae7251af4f42c4450e51"

OUTPUT_ROOT = ROOT / "workspace/private/outputs/s20plus_g986n/p0_pid1_acm_v2"
CANDIDATE_AP = OUTPUT_ROOT / "AP.tar.md5"
CANDIDATE_AP_SIZE = 25_733_161
CANDIDATE_AP_SHA256 = "58479a25ae2550366d38be4fae6727eafaadcdb98567de4a00c3a1cf5c0015db"
CANDIDATE_MEMBER_SIZE = 25_722_068
CANDIDATE_MEMBER_SHA256 = "c02c1ce1c963942d96de500d6caa89118424c36d211ab9aa788a85db0859c2ee"
CANDIDATE_BOOT_SIZE = 67_108_864
CANDIDATE_BOOT_SHA256 = "5c967babf96b8b625c4afe3edbbd473cf55042e252dacf57def8c3809fc697ff"

ROLLBACK_ROOT = (
    ROOT
    / "workspace/private/outputs/s20plus_g986n/boot_recovery_canary_b0_v1/rollback"
)
ROLLBACK_AP = ROLLBACK_ROOT / "AP.tar.md5"
ROLLBACK_AP_SIZE = 25_835_561
ROLLBACK_AP_SHA256 = "1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2"
ROLLBACK_MEMBER_SIZE = 25_833_304
ROLLBACK_MEMBER_SHA256 = "2003a3db44c35e0a32b6b485ca0260c7feeab4d9c3031b8cf3ec64f87a8b19b5"
ROLLBACK_BOOT_SIZE = 67_108_864
ROLLBACK_BOOT_SHA256 = "d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc"

MANIFEST = OUTPUT_ROOT / "manifest.json"
MANIFEST_SIZE = 14_574
MANIFEST_SHA256 = "75052fd00dd8c1b79aeec85b6dd4599bc81ccec9c0d684cfba7d6ba16b00d916"

APPROVAL_PREFIX = "S20PLUS-G986N-P0-PID1-ODIN-F1-APPROVE:"
PHYSICAL_CONFIRM_PREFIX = "S20PLUS-G986N-P0-PHYSICAL-ROLLBACK-CONFIRM:"
PHYSICAL_REBIND_CONFIRM_PREFIX = (
    "S20PLUS-G986N-P0-PHYSICAL-ROLLBACK-REENUM-CONFIRM:"
)
P0_BASELINE_NAME = "p0-usb-baseline.json"
P0_BASELINE_SCHEMA = "s20plus_g986n_p0_pid1_odin_usb_baseline_v1"
P0_RAW_BANNER_NAME = "p0-acm-banner.raw"
P0_RECEIPT_SCHEMA = "s20plus_g986n_p0_pid1_odin_raw_receipt_v1"
P0_REGISTRY_INTENT_NAME = "p0-global-claim-intent.json"
P0_REGISTRY_RECEIPT_NAME = "p0-global-claim.json"
P0_REGISTRY_UNCERTAIN_NAME = "p0-global-claim-uncertain.json"
P0_REGISTRY_RELEASE_INTENT_NAME = "p0-global-release-intent.json"
P0_REGISTRY_RELEASE_RECEIPT_NAME = "p0-global-release.json"
P0_LOCAL_PROJECTION_RELEASE_NAME = "p0-local-projection-release.json"
P0_CANDIDATE_PREFLIGHT_NAME = "p0-candidate-transfer-preflight.json"
P0_PHYSICAL_REBIND_ARM_NAME = "p0-physical-rollback-rebind-arm.json"
P0_PHYSICAL_REBIND_CONFIRM_NAME = "p0-physical-rollback-rebind-confirmation.json"
P0_PHYSICAL_REBIND_ARRIVAL_NAME = "p0-physical-rollback-rebind-arrival.json"
P0_PHYSICAL_REBIND_MISS_NAME = "p0-physical-rollback-rebind-miss.json"
P0_REGISTRY_INTENT_SCHEMA = "s20plus_g986n_p0_global_claim_intent_v1"
P0_REGISTRY_RECEIPT_SCHEMA = "s20plus_g986n_p0_global_claim_receipt_v1"
P0_REGISTRY_UNCERTAIN_SCHEMA = "s20plus_g986n_p0_global_claim_uncertain_v1"
P0_REGISTRY_RELEASE_INTENT_SCHEMA = "s20plus_g986n_p0_global_release_intent_v1"
P0_REGISTRY_RELEASE_RECEIPT_SCHEMA = "s20plus_g986n_p0_global_release_receipt_v1"
P0_LOCAL_PROJECTION_RELEASE_SCHEMA = (
    "s20plus_g986n_p0_local_projection_release_v1"
)
P0_CAGE_PREPARE_SCHEMA = "s20plus_g986n_p0_process_cage_prepare_v1"
P0_CAGE_BOUND_SCHEMA = "s20plus_g986n_p0_process_cage_bound_v1"
P0_CAGE_RECONCILED_SCHEMA = "s20plus_g986n_p0_process_cage_reconciled_v1"
P0_CANDIDATE_PREFLIGHT_SCHEMA = (
    "s20plus_g986n_p0_candidate_transfer_preflight_v1"
)
P0_PHYSICAL_REBIND_ARM_SCHEMA = (
    "s20plus_g986n_p0_physical_rollback_rebind_arm_v1"
)
P0_PHYSICAL_REBIND_CONFIRM_SCHEMA = (
    "s20plus_g986n_p0_physical_rollback_rebind_confirmation_v1"
)
P0_PHYSICAL_REBIND_ARRIVAL_SCHEMA = (
    "s20plus_g986n_p0_physical_rollback_rebind_arrival_v1"
)
P0_PHYSICAL_REBIND_MISS_SCHEMA = (
    "s20plus_g986n_p0_physical_rollback_rebind_miss_v1"
)
ROLLBACK_PREINTENT_IDENTITY_ERRORS = frozenset(
    {
        "P0 Download identity is unproved",
        "Download endpoint is absent or ambiguous",
        "Odin endpoint is not a direct character device",
        "Download sysfs value is oversized",
        "Download sysfs value is malformed",
        "Download sysfs identity is absent or ambiguous",
        "Download USB identity changed or differs",
        "Download topology is not allowlisted",
    }
)
ROLLBACK_PREINTENT_ENDPOINT_CHANGE_ERRORS = frozenset(
    {
        "Download endpoint changed before transfer intent",
        "Download endpoint changed during transfer preflight",
    }
)
CAGE_KINDS = ("candidate", "rollback", "abort-return", "odin-listing")
CAGE_GENERATION_MAXIMUM = 512
CAGE_NODE_RE = re.compile(
    r"p0-(candidate|rollback|abort-return|odin-listing)-cage-"
    r"([0-9]{4})-(prepare|bound|reconciled)\.json"
)
P0_SUCCESS_ENVIRONMENT = "p0-pid1-acm"
P0_NO_PROOF_ENVIRONMENT = "p0-pid1-acm-no-proof"
P0_ARRIVAL_TIMEOUT_SECONDS = 180
P0_POLL_SECONDS = 0.05
P0_ADB_SERVER_SOCKET = "tcp:5037"
USBFS_RE = re.compile(r"/dev/bus/usb/([0-9]{3})/([0-9]{3})")
USB_NODE_RE = re.compile(r"[0-9]+-[0-9]+(?:\.[0-9]+)*")
HEX64_RE = re.compile(r"[0-9a-f]{64}")

REGISTRY_PATH = ROOT / (
    "workspace/public/src/scripts/revalidation/consumed_candidate_registry_v1.py"
)
REGISTRY_SIZE = 53_811
REGISTRY_SHA256 = "0a112d7dd2633d3465137cdb67ed4539949a3c0c0ec90b178a3ec293735dbdc4"
REGISTRY_ACTIVATION = (
    ROOT / "workspace/private/consumed-candidate-registry-v1/activation.json"
)
REGISTRY_ACTIVATION_SIZE = 21_276
REGISTRY_ACTIVATION_SHA256 = (
    "aa50c211ee86d4b1534399c6d9fd82d4de3550856724e5788d693b012bce471b"
)
P0_LIVE_ACTIVATION = (
    ROOT
    / "workspace/private/runs/s20plus-g986n-p0-pid1-odin-f1/"
    "live-activation-v1.json"
)
P0_LIVE_ACTIVATION_SCHEMA = "s20plus_g986n_p0_pid1_odin_f1_live_activation_v1"
P0_ZERO_FINDING_REVIEW = RUN_ROOT / "zero-finding-review-v1.json"
P0_ZERO_FINDING_REVIEW_SCHEMA = (
    "s20plus_g986n_p0_pid1_odin_f1_zero_finding_review_v1"
)
P0_MECHANICAL_ACTIVATION = RUN_ROOT / "mechanical-activation-v1.json"
P0_MECHANICAL_ACTIVATION_SCHEMA = (
    "s20plus_g986n_p0_pid1_odin_f1_mechanical_activation_v1"
)
P0_REVIEW_TEST_RESULTS_SCHEMA = (
    "s20plus_g986n_p0_pid1_odin_f1_review_test_results_v1"
)
P0_REVIEW_TEST_LOG_ROOT = RUN_ROOT / "review-tests-v1"
P0_ACTIVE_REVIEW_TEST_LOG_ROOT = RUN_ROOT / "active-review-tests-v1"
P0_REVIEW_TEST_REQUIREMENTS = {
    "focused_observer": {
        "modules": ["tests.test_s20plus_g986n_p0_pid1_usb_observer"],
        "tests": 10,
        "skipped": 0,
        "log_name": "focused-observer.log",
    },
    "focused_owner": {
        "modules": ["tests.test_s20plus_g986n_p0_pid1_odin_f1"],
        "tests": 74,
        "skipped": 0,
        "log_name": "focused-owner.log",
    },
    "wider": {
        "modules": [
            "tests.test_s20plus_g986n_p0_pid1_acm_h0",
            "tests.test_s20plus_g986n_p0_pid1_usb_observer",
            "tests.test_s20plus_g986n_p0_pid1_odin_f1",
            "tests.test_s20plus_g986n_boot_recovery_canary_b0_f1",
            "tests.test_s20plus_g986n_boot_recovery_canary_b0_h0",
            "tests.test_s20plus_g986n_p0_twrp_boot_owner_h0",
            "tests.test_device_action_f1_consumed_candidate_registry_v1",
        ],
        "tests": 178,
        "skipped": 10,
        "log_name": "wider.log",
    },
}
P0_ACTIVE_REPORT_MARKER = "Status: `PASS_GO_ACTIVE_ATTENDED_F1`"
P0_ACTIVE_CONTRACT_MARKER = "Status: **ACTIVE - ATTENDED F1 ONLY**"
P0_ACTIVE_GOAL_MARKER = "Status: `P0_PID1_ODIN_F1_ACTIVE_ATTENDED`"
P0_ACTIVE_REGISTRY_MARKER = (
    "reviewed attended native-canary P0 F1 active"
)
P0_DORMANT_REPORT_MARKER = "Status: `H0_REVIEW_PENDING_NOT_ACTIVE`"
P0_DORMANT_CONTRACT_MARKER = "Status: **DEFINED - H0 ONLY - NOT ACTIVE**"
P0_DORMANT_GOAL_MARKER = "Status: `P0_PID1_ODIN_F1_REVIEW_PENDING_NOT_ACTIVE`"
P0_REGISTRY_TARGET_CELL = (
    "Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `G986NKSS8IYC2`)"
)
P0_REGISTRY_GOAL_CELL = "`GOAL_S20PLUS.md`"
P0_REGISTRY_CONTRACT_CELL = (
    "`docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md`"
)
P0_DORMANT_REGISTRY_PROCESS_CELL = (
    "Active exact-target routine D0/D1 including payload-free Download return; "
    "attended fixed root-health D0 active; attended boot-only bootstrap, resident "
    "Magisk, and recovery-canary B0 F1 active; recovery-canary T0 and TWRP T1 F2 "
    "candidates consumed; TWRP T2 recovery retained and candidate consumed; "
    "reviewed attended native-canary R1 active"
)
P0_ACTIVE_REGISTRY_PROCESS_CELL = (
    P0_DORMANT_REGISTRY_PROCESS_CELL + "; " + P0_ACTIVE_REGISTRY_MARKER
)
P0_POLICY_FILES = {
    "repository_contract": ROOT / "AGENTS.md",
    "target_contract": (
        ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
    ),
    "risk_tiers": ROOT / "docs/operations/DEVICE_ACTION_RISK_TIERS.md",
    "process_v2": ROOT / "docs/operations/DEVICE_ACTION_PROCESS_V2.md",
    "current_goal": ROOT / "GOAL_S20PLUS.md",
    "qualification_report": (
        ROOT
        / "docs/reports/"
        "S20PLUS_G986N_P0_PID1_ODIN_F1_OWNER_H0_2026-09-01.md"
    ),
}
P0_TEST_FILES = {
    "p0_owner": ROOT / "tests/test_s20plus_g986n_p0_pid1_odin_f1.py",
    "p0_observer": ROOT / "tests/test_s20plus_g986n_p0_pid1_usb_observer.py",
    "b0_owner": ROOT / "tests/test_s20plus_g986n_boot_recovery_canary_b0_f1.py",
}
P0_ACTIVATION_CHANGE_FILES = {
    "owner": SCRIPT,
    "observer": OBSERVER_PATH,
    "repository_contract": P0_POLICY_FILES["repository_contract"],
    "target_contract": P0_POLICY_FILES["target_contract"],
    "current_goal": P0_POLICY_FILES["current_goal"],
    "qualification_report": P0_POLICY_FILES["qualification_report"],
}
P0_UNCHANGED_POLICY_NAMES = frozenset({"risk_tiers", "process_v2"})
P0_DORMANT_DOCUMENT_SEMANTICS = {
    "repository_contract": P0_DORMANT_REGISTRY_PROCESS_CELL,
    "target_contract": P0_DORMANT_CONTRACT_MARKER,
    "current_goal": P0_DORMANT_GOAL_MARKER,
    "qualification_report": P0_DORMANT_REPORT_MARKER,
}
P0_ACTIVE_DOCUMENT_SEMANTICS = {
    "repository_contract": P0_ACTIVE_REGISTRY_PROCESS_CELL,
    "target_contract": P0_ACTIVE_CONTRACT_MARKER,
    "current_goal": P0_ACTIVE_GOAL_MARKER,
    "qualification_report": P0_ACTIVE_REPORT_MARKER,
}
P0_DOCUMENT_ACTIVATION_PLACEHOLDER = "<P0_REVIEWED_ACTIVATION_STATUS>"
P0_ACTIVATION_CHANGE_RULES = {
    "owner": {"before": "P0_F1_ACTIVE = False", "after": "P0_F1_ACTIVE = True"},
    "observer": {"before": "OBSERVER_ACTIVE = False", "after": "OBSERVER_ACTIVE = True"},
    **{
        name: {
            "before": P0_DORMANT_DOCUMENT_SEMANTICS[name],
            "after": P0_ACTIVE_DOCUMENT_SEMANTICS[name],
        }
        for name in P0_DORMANT_DOCUMENT_SEMANTICS
    },
}


class P0F1Error(RuntimeError):
    pass


def _session_lock_path() -> Path:
    return ROOT / "workspace/private/consumed-candidate-registry-v1" / "target-session.lock"


def _session_lock_identity(descriptor: int) -> tuple[int, int, int, int, int]:
    path = _session_lock_path()
    try:
        opened = os.fstat(descriptor)
        current = path.lstat()
        payload = os.pread(descriptor, len(registry.SESSION_LOCK_PAYLOAD) + 1, 0)
    except (OSError, NameError) as exc:
        raise P0F1Error("S20+ P0 target-session lease identity is unavailable") from exc
    identity = (
        opened.st_dev,
        opened.st_ino,
        opened.st_size,
        opened.st_mode,
        opened.st_nlink,
    )
    if (
        not stat.S_ISREG(opened.st_mode)
        or stat.S_IMODE(opened.st_mode) != 0o600
        or opened.st_nlink != 1
        or (current.st_dev, current.st_ino, current.st_size, current.st_mode, current.st_nlink)
        != identity
        or payload != registry.SESSION_LOCK_PAYLOAD
        or path.is_symlink()
        or path.resolve(strict=True) != path.absolute()
    ):
        raise P0F1Error("S20+ P0 target-session lease identity changed")
    return identity


def _closed_adb_environment(socket_spec: str) -> dict[str, str]:
    if socket_spec != P0_ADB_SERVER_SOCKET:
        raise P0F1Error("P0 ADB server socket is not fixed")
    try:
        account = pwd.getpwuid(os.geteuid())
        home = Path(account.pw_dir).absolute()
        metadata = home.lstat()
    except (KeyError, OSError) as exc:
        raise P0F1Error("P0 operator ADB home is unavailable") from exc
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or home.resolve(strict=True) != home
    ):
        raise P0F1Error("P0 operator ADB home identity differs")
    return {
        "ADB_SERVER_SOCKET": socket_spec,
        "HOME": str(home),
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin",
    }


def _guarded_live_alias(original, label: str):
    def guarded(*args, **kwargs):
        require_active()
        _require_live_transaction()
        return original(*args, **kwargs)

    guarded.__name__ = f"p0_guarded_{label}"
    guarded.__qualname__ = guarded.__name__
    return guarded


def _guarded_host_or_live_alias(original, label: str):
    def guarded(*args, **kwargs):
        if _host_validation_active():
            return original(*args, **kwargs)
        require_active()
        _require_live_transaction()
        return original(*args, **kwargs)

    guarded.__name__ = f"p0_guarded_{label}"
    guarded.__qualname__ = guarded.__name__
    return guarded


def _direct_receipt(path: Path, size: int, sha256: str, label: str) -> dict[str, Any]:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise P0F1Error(f"{label} is unavailable") from exc
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_size != size
        or path.resolve(strict=True) != path.absolute()
    ):
        raise P0F1Error(f"{label} identity differs")
    payload_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    if payload_sha256 != sha256:
        raise P0F1Error(f"{label} bytes differ")
    return {"path": str(path), "size": size, "sha256": sha256}


def _load_exact_module(name: str, path: Path, size: int, sha256: str):
    _direct_receipt(path, size, sha256, name)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise P0F1Error(f"{name} loader is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    if Path(module.__file__).resolve(strict=True) != path:
        raise P0F1Error(f"{name} loaded from a foreign path")
    return module


def _activation_normalized_observer_receipt() -> tuple[dict[str, Any], bool]:
    try:
        metadata = OBSERVER_PATH.lstat()
    except OSError as exc:
        raise P0F1Error("P0 observer is unavailable") from exc
    if (
        OBSERVER_PATH.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or OBSERVER_PATH.resolve(strict=True) != OBSERVER_PATH.absolute()
    ):
        raise P0F1Error("P0 observer identity differs")
    payload = OBSERVER_PATH.read_bytes()
    normalized, count = re.subn(
        rb"^OBSERVER_ACTIVE = (?:False|True)$",
        b"OBSERVER_ACTIVE = <REVIEWED_ACTIVATION_BOOLEAN>",
        payload,
        flags=re.MULTILINE,
    )
    matches = re.findall(
        rb"^OBSERVER_ACTIVE = (False|True)$", payload, flags=re.MULTILINE
    )
    if count != 1 or len(matches) != 1:
        raise P0F1Error("P0 observer activation grammar changed")
    active = matches[0] == b"True"
    payload_sha256 = hashlib.sha256(payload).hexdigest()
    if (
        metadata.st_size != OBSERVER_SIZE_BY_ACTIVE[active]
        or len(payload) != OBSERVER_SIZE_BY_ACTIVE[active]
        or payload_sha256 != OBSERVER_SHA256_BY_ACTIVE[active]
        or hashlib.sha256(normalized).hexdigest() != OBSERVER_NORMALIZED_SHA256
    ):
        raise P0F1Error("P0 observer is outside the reviewed activation pair")
    return (
        {
            "path": str(OBSERVER_PATH),
            "size": len(payload),
            "sha256": payload_sha256,
            "normalized_sha256": OBSERVER_NORMALIZED_SHA256,
        },
        active,
    )


def _load_activation_normalized_observer(name: str):
    before, active = _activation_normalized_observer_receipt()
    spec = importlib.util.spec_from_file_location(name, OBSERVER_PATH)
    if spec is None or spec.loader is None:
        raise P0F1Error(f"{name} loader is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    after, active_after = _activation_normalized_observer_receipt()
    if (
        after != before
        or active_after is not active
        or getattr(module, "OBSERVER_ACTIVE", None) is not active
        or Path(module.__file__).resolve(strict=True) != OBSERVER_PATH
    ):
        raise P0F1Error(f"{name} activation-normalized load changed")
    return module


@contextlib.contextmanager
def _temporary_module_bindings(bindings: dict[str, Any]):
    missing = object()
    previous = {name: sys.modules.get(name, missing) for name in bindings}
    try:
        sys.modules.update(bindings)
        yield
    finally:
        for name, value in previous.items():
            if value is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


_isolated_raw_capture = _load_exact_module(
    "_s20plus_g986n_p0_pid1_bound_raw_capture",
    RAW_CAPTURE_PATH,
    RAW_CAPTURE_SIZE,
    RAW_CAPTURE_SHA256,
)
_isolated_base = _load_exact_module(
    "_s20plus_g986n_p0_pid1_bound_inventory",
    BASE_PATH,
    BASE_SIZE,
    BASE_SHA256,
)
_isolated_boot_verify = _load_exact_module(
    "_s20plus_g986n_p0_pid1_bound_boot_verify",
    BOOT_VERIFY_PATH,
    BOOT_VERIFY_SIZE,
    BOOT_VERIFY_SHA256,
)
with _temporary_module_bindings(
    {
        "device_action_raw_capture_v1": _isolated_raw_capture,
        "s22plus_boot_verify": _isolated_boot_verify,
    }
):
    _isolated_transport = _load_exact_module(
        "_s20plus_g986n_p0_pid1_bound_transport",
        TRANSPORT_PATH,
        TRANSPORT_SIZE,
        TRANSPORT_SHA256,
    )
with _temporary_module_bindings(
    {
        "device_action_raw_capture_v1": _isolated_raw_capture,
        "s20plus_g986n_d0_inventory": _isolated_base,
        "s22plus_boot_only_f1_transport": _isolated_transport,
    }
):
    engine = _load_exact_module(
        "_s20plus_g986n_p0_pid1_bound_b0_engine",
        ENGINE_PATH,
        ENGINE_SIZE,
        ENGINE_SHA256,
    )
observer = _load_activation_normalized_observer(
    "_s20plus_g986n_p0_pid1_bound_usb_observer"
)
registry = _load_exact_module(
    "_s20plus_g986n_p0_pid1_bound_consumed_registry",
    REGISTRY_PATH,
    REGISTRY_SIZE,
    REGISTRY_SHA256,
)


def _deny_registry_initialization(*_args, **_kwargs):
    raise P0F1Error("P0 may not initialize or recreate the global registry")


def _create_capability_system() -> dict[str, Any]:
    """Create non-exported lease and mutation issuers.

    Only the returned verifiers and already-bound wrappers survive module
    initialization.  The sentinels, ContextVars, lease type, mutation type,
    and transaction context manager remain closure-private.
    """

    live_state: contextvars.ContextVar[Any] = contextvars.ContextVar(
        "s20plus_g986n_p0_live_transaction", default=None
    )
    host_state: contextvars.ContextVar[Any] = contextvars.ContextVar(
        "s20plus_g986n_p0_host_validation", default=None
    )
    mutation_state: contextvars.ContextVar[Any] = contextvars.ContextVar(
        "s20plus_g986n_p0_registry_mutation", default=None
    )
    raw_state: contextvars.ContextVar[Any] = contextvars.ContextVar(
        "s20plus_g986n_p0_raw_acquisition", default=None
    )
    live_capability = object()
    host_capability = object()
    mutation_capability = object()
    raw_capability = object()

    class Lease:
        __slots__ = (
            "capability",
            "entrypoint",
            "run_dir",
            "lease_fd",
            "lease_identity",
            "target_serial_sha256",
            "adb_environment",
        )

        def __init__(
            self,
            entrypoint: str,
            run_dir: Path | None,
            lease_fd: int,
            lease_identity: tuple[int, int, int, int, int],
        ) -> None:
            self.capability = live_capability
            self.entrypoint = entrypoint
            self.run_dir = None if run_dir is None else str(run_dir)
            self.lease_fd = lease_fd
            self.lease_identity = lease_identity
            self.target_serial_sha256: str | None = None
            self.adb_environment: dict[str, str] | None = None

    class Mutation:
        __slots__ = ("capability", "event", "run_dir", "lease")

        def __init__(self, event: str, lease: Lease) -> None:
            self.capability = mutation_capability
            self.event = event
            self.run_dir = lease.run_dir
            self.lease = lease

    class RawAcquisition:
        __slots__ = ("capability", "authority", "capture_dir", "name", "writers")

        def __init__(self, authority: Any, capture_dir: Path, name: str) -> None:
            self.capability = raw_capability
            self.authority = authority
            self.capture_dir = capture_dir
            self.name = name
            self.writers: list[Any] = []

    def current_lease() -> Lease:
        value = live_state.get()
        if (
            type(value) is not Lease
            or value.capability is not live_capability
            or type(value.lease_fd) is not int
            or not isinstance(value.lease_identity, tuple)
            or _session_lock_identity(value.lease_fd) != value.lease_identity
        ):
            raise P0F1Error("S20+ P0 live helper lacks the target-session lease")
        return value

    def require_live() -> dict[str, Any]:
        value = current_lease()
        return {"entrypoint": value.entrypoint, "run_dir": value.run_dir}

    def bind_live_run_dir(run_dir: Path) -> None:
        value = current_lease()
        if value.run_dir is not None or run_dir.parent != RUN_ROOT:
            raise P0F1Error("P0 live transaction run binding differs")
        value.run_dir = str(run_dir)
        current_lease()

    def bind_target_rows(rows: Any) -> None:
        lease = current_lease()
        if not isinstance(rows, tuple):
            raise P0F1Error("P0 ADB inventory result type differs")
        matches = [
            row
            for row in rows
            if isinstance(row, dict)
            and engine.EXPECTED_ADB_MODEL in row.get("metadata", set())
        ]
        if len(matches) > 1:
            raise P0F1Error("P0 ADB inventory has multiple exact target rows")
        if not matches:
            return
        serial = matches[0].get("serial")
        if not isinstance(serial, str) or not serial:
            raise P0F1Error("P0 exact ADB row has no serial")
        serial_sha256 = hashlib.sha256(serial.encode()).hexdigest()
        if (
            lease.target_serial_sha256 is not None
            and lease.target_serial_sha256 != serial_sha256
        ):
            raise P0F1Error("P0 exact ADB serial changed inside the target session")
        lease.target_serial_sha256 = serial_sha256

    def require_target_serial(serial: str) -> None:
        lease = current_lease()
        if (
            not isinstance(serial, str)
            or not serial
            or lease.target_serial_sha256 is None
            or hashlib.sha256(serial.encode()).hexdigest()
            != lease.target_serial_sha256
        ):
            raise P0F1Error("P0 command serial is not the bound exact target")

    def host_active() -> bool:
        return host_state.get() is host_capability

    def raw_authority() -> Any:
        if host_active():
            return host_capability
        return current_lease()

    def require_raw() -> RawAcquisition:
        authority = raw_authority()
        value = raw_state.get()
        if (
            type(value) is not RawAcquisition
            or value.capability is not raw_capability
            or value.authority is not authority
            or not isinstance(value.capture_dir, Path)
            or not isinstance(value.name, str)
        ):
            raise P0F1Error("P0 raw writer lacks its exact acquisition capability")
        return value

    @contextlib.contextmanager
    def raw_acquisition(capture_dir: Path, name: str):
        if raw_state.get() is not None:
            raise P0F1Error("P0 raw acquisition cannot be nested")
        authority = raw_authority()
        direct = capture_dir.absolute()
        if authority is host_capability:
            if (
                name != "cage-capability"
                or direct.parent != RUN_ROOT
                or not direct.name.startswith(".cage-capability-")
            ):
                raise P0F1Error("P0 H0 raw acquisition escaped its exact probe")
        elif authority.run_dir is None or direct != Path(authority.run_dir):
            raise P0F1Error("P0 raw acquisition escaped its leased run")
        grant = RawAcquisition(authority, direct, name)
        state_token = raw_state.set(grant)
        leaked_writer = False
        try:
            yield
            require_raw()
        finally:
            if raw_state.get() is grant:
                for writer in tuple(grant.writers):
                    leaked_writer = writer._close_if_unfinalized() or leaked_writer
            raw_state.reset(state_token)
            if leaked_writer:
                raise P0F1Error("P0 raw writer escaped acquisition without finalization")

    def require_mutation(event: str) -> tuple[Lease, Mutation]:
        lease = current_lease()
        value = mutation_state.get()
        if (
            type(value) is not Mutation
            or value.capability is not mutation_capability
            or value.lease is not lease
            or value.event != event
            or value.run_dir != lease.run_dir
        ):
            raise P0F1Error("P0 registry mutation lacks its exact internal capability")
        return lease, value

    @contextlib.contextmanager
    def mutation(event: str):
        lease = current_lease()
        if mutation_state.get() is not None or event not in {"claim", "release"}:
            raise P0F1Error("P0 registry mutation nesting differs")
        grant = Mutation(event, lease)
        state_token = mutation_state.set(grant)
        try:
            yield
            require_mutation(event)
        finally:
            mutation_state.reset(state_token)

    @contextlib.contextmanager
    def transaction(entrypoint: str, run_dir: Path | None):
        if live_state.get() is not None:
            raise P0F1Error("S20+ P0 target-session lease cannot be caller-nested")
        path = _session_lock_path()
        descriptor: int | None = None
        state_token = None
        lease: Lease | None = None
        try:
            descriptor = os.open(
                path,
                os.O_RDWR | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
            )
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lease = Lease(
                entrypoint,
                run_dir,
                descriptor,
                _session_lock_identity(descriptor),
            )
            state_token = live_state.set(lease)
            current_lease()
            yield
            current_lease()
        except (OSError, BlockingIOError) as exc:
            raise P0F1Error("P0 target-session lease is unavailable") from exc
        finally:
            if state_token is not None:
                live_state.reset(state_token)
            if descriptor is not None:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                finally:
                    os.close(descriptor)

    def build_entrypoint(name: str, original, active, resolve_run, reconcile):
        def replacement(*args, **kwargs):
            active()
            run_dir = resolve_run(name, args)
            if live_state.get() is not None:
                current = require_live()
                if run_dir is not None and current["run_dir"] != str(run_dir):
                    raise P0F1Error("nested P0 entrypoint changed the leased run")
                return original(*args, **kwargs)
            with transaction(name, run_dir):
                if run_dir is not None:
                    reconcile(run_dir)
                return original(*args, **kwargs)

        replacement.__name__ = f"p0_{name}"
        return replacement

    def build_prepare_output(reader, active, reconcile):
        def replacement(run_dir: Path) -> dict[str, Any]:
            active()
            run_dir = run_dir.absolute()
            if run_dir.parent != RUN_ROOT:
                raise P0F1Error("P0 prepared output escaped its fixed root")
            with transaction("prepare-output", run_dir):
                reconcile(run_dir)
                return reader(run_dir, phase="candidate")

        return replacement

    def build_host_validation(original):
        def replacement(*, include_candidate: bool, include_rollback: bool):
            if live_state.get() is not None:
                current_lease()
            if host_state.get() is not None:
                raise P0F1Error("P0 host validation cannot be caller-nested")
            state_token = host_state.set(host_capability)
            try:
                return original(
                    include_candidate=include_candidate,
                    include_rollback=include_rollback,
                )
            finally:
                host_state.reset(state_token)

        return replacement

    def adb_client_environment() -> dict[str, str]:
        lease = current_lease()
        expected = _closed_adb_environment(P0_ADB_SERVER_SOCKET)
        if lease.adb_environment is None:
            lease.adb_environment = expected
        elif lease.adb_environment != expected:
            raise P0F1Error("P0 fixed ADB client environment changed")
        return dict(lease.adb_environment)

    def run_bounded_adb(
        command: list[str], timeout: float, maximum: int, environment: dict[str, str]
    ) -> tuple[int, bytes, bytes]:
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as error:
            try:
                process = subprocess.Popen(
                    command,
                    executable=str(engine.ADB),
                    stdin=subprocess.DEVNULL,
                    stdout=output,
                    stderr=error,
                    close_fds=True,
                    cwd=str(ROOT),
                    env=dict(environment),
                    start_new_session=True,
                )
            except OSError as exc:
                raise P0F1Error("P0 fixed ADB client could not start") from exc
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if output.tell() + error.tell() > maximum:
                    process.terminate()
                    try:
                        process.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=1.0)
                    raise P0F1Error("P0 fixed ADB output exceeded its bound")
                if time.monotonic() >= deadline:
                    process.terminate()
                    try:
                        process.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=1.0)
                    raise P0F1Error("P0 fixed ADB command timed out")
                time.sleep(0.02)
            output.seek(0)
            error.seek(0)
            stdout = output.read(maximum + 1)
            stderr = error.read(maximum + 1)
        if len(stdout) + len(stderr) > maximum:
            raise P0F1Error("P0 fixed ADB output exceeded its bound")
        current_lease()
        if environment != adb_client_environment():
            raise P0F1Error("P0 fixed ADB client environment differs")
        if type(process.returncode) is not int:
            raise P0F1Error("P0 fixed ADB return code differs")
        return process.returncode, stdout, stderr

    def base_command(_original):
        def guarded(*args, **kwargs):
            require_active()
            current_lease()
            if kwargs or len(args) != 3:
                raise P0F1Error("P0 bounded command arguments differ")
            argv, timeout, maximum = args
            command = list(argv) if not isinstance(argv, (str, bytes)) else []
            if command == [str(engine.ADB), "devices", "-l"]:
                if timeout != 10 or maximum != engine.MAX_ADB_BYTES:
                    raise P0F1Error("P0 ADB inventory command bounds differ")
            elif len(command) >= 4 and command[:2] == [str(engine.ADB), "-s"]:
                require_target_serial(command[2])
                allowed = (
                    command[3:] == ["get-devpath"]
                    and timeout == 10
                    and maximum == engine.MAX_ADB_BYTES
                ) or (
                    command[3:]
                    == ["exec-out", "sh", "-c", engine.PUBLIC_SNAPSHOT_SCRIPT]
                    and timeout == 20
                    and maximum == engine.MAX_ADB_BYTES
                )
                if not allowed:
                    raise P0F1Error("P0 ADB command is outside the fixed read closure")
            else:
                raise P0F1Error("P0 bounded command is outside the fixed ADB closure")
            fixed_environment = adb_client_environment()
            return run_bounded_adb(command, timeout, maximum, fixed_environment)

        guarded.__name__ = "p0_fixed_base_bounded_command"
        return guarded

    def adb_inventory(original):
        def guarded(*, health_only: bool = False):
            require_active()
            current_lease()
            if type(health_only) is not bool:
                raise P0F1Error("P0 ADB inventory selector differs")
            rows = original(health_only=health_only)
            bind_target_rows(rows)
            return rows

        guarded.__name__ = "p0_fixed_adb_inventory"
        return guarded

    def validate_live_raw_command(
        argv: Any, capture_dir: Path, name: str, kwargs: dict[str, Any]
    ) -> None:
        lease = current_lease()
        command = list(argv) if not isinstance(argv, (str, bytes)) else []
        if lease.run_dir is None or Path(capture_dir).absolute() != Path(lease.run_dir):
            raise P0F1Error("P0 raw command escaped its exact leased run")

        serial_command = len(command) >= 4 and command[:2] == [str(engine.ADB), "-s"]
        if serial_command:
            require_target_serial(command[2])
            root_tail = [
                "shell",
                "su",
                "-c",
                engine.shlex.quote(engine.ROOT_READ_SCRIPT),
            ]
            recovery_scripts = {
                "candidate-transport": engine.RECOVERY_TRANSPORT_SCRIPT,
                "candidate-claim": engine.RECOVERY_CLAIM_SCRIPT,
                "rollback-source": engine.RECOVERY_TRANSPORT_SCRIPT,
            }
            if command[3:] == root_tail:
                expected = {
                    "timeout": 30,
                    "stdout_maximum": 4096,
                    "stderr_maximum": 4096,
                    "stdout_name": f"{name}.stdout",
                    "stderr_name": f"{name}.stderr",
                }
                if kwargs != expected:
                    raise P0F1Error("P0 root-read capture bounds differ")
                return
            if command[3:] == ["reboot", "download"]:
                expected = {
                    "timeout": 20,
                    "stdout_maximum": engine.MAX_ADB_BYTES,
                    "stderr_maximum": engine.MAX_ADB_BYTES,
                    "stdout_name": f"{name}.stdout",
                    "stderr_name": f"{name}.stderr",
                }
                if kwargs != expected:
                    raise P0F1Error("P0 Download-request capture bounds differ")
                return
            if name in recovery_scripts and command[3:] == [
                "exec-out",
                "sh",
                "-c",
                recovery_scripts[name],
            ]:
                expected = {
                    "timeout": 20,
                    "stdout_maximum": 4096,
                    "stderr_maximum": 4096,
                    "stdout_name": f"{name}.stdout",
                    "stderr_name": f"{name}.stderr",
                }
                if kwargs != expected:
                    raise P0F1Error("P0 recovery-read capture bounds differ")
                return
            raise P0F1Error("P0 raw ADB command is outside the fixed profile")

        if len(command) < 7 or command[:3] != [
            str(engine.DASH),
            "-c",
            engine.ODIN_CAGE_ENTRY_SCRIPT,
        ]:
            raise P0F1Error("P0 raw command is outside the fixed ADB/Odin profile")
        cage = command[4]
        if name.startswith("p0-odin-listing-"):
            match = re.fullmatch(r"p0-odin-listing-([0-9]{4})", name)
            if match is None:
                raise P0F1Error("P0 Odin-listing capture name differs")
            generation = int(match.group(1))
            intent = engine.read_json(
                Path(lease.run_dir) / f"{name}-intent.json",
                "P0 Odin-listing raw-command intent",
            )
            expected_command = [
                str(engine.DASH),
                "-c",
                engine.ODIN_CAGE_ENTRY_SCRIPT,
                "s20plus-p0-odin-listing-cage",
                intent.get("process_cage", {}).get("cage"),
                str(engine.CAGE_SLEEP),
                "timeout",
                "-s",
                "KILL",
                "10",
                str(engine.ODIN),
                "-l",
            ]
            expected_kwargs = {
                "timeout": 12,
                "stdout_maximum": engine.MAX_ADB_BYTES,
                "stderr_maximum": engine.MAX_ADB_BYTES,
                "env": engine.ODIN_FIXED_ENV,
                "stdout_name": f"{name}.stdout",
                "stderr_name": f"{name}.stderr",
            }
            if generation < 1 or command != expected_command or kwargs != expected_kwargs:
                raise P0F1Error("P0 Odin-listing raw command differs from its intent")
            return

        intent_names = {
            "candidate-transfer": "candidate-intent.json",
            "rollback-transfer": "rollback-intent.json",
            "abort-return": "abort-return-intent.json",
        }
        intent_name = intent_names.get(name)
        if intent_name is None:
            raise P0F1Error("P0 raw Odin capture name is outside the fixed profile")
        intent = engine.read_json(
            Path(lease.run_dir) / intent_name, f"P0 {name} raw-command intent"
        )
        if cage != intent.get("process_cage", {}).get("cage"):
            raise P0F1Error("P0 raw Odin command differs from its bound cage")
        endpoint = intent.get("endpoint", {}).get("device")
        if name in {"candidate-transfer", "rollback-transfer"}:
            kind = name.removesuffix("-transfer")
            artifact = CANDIDATE_AP if kind == "candidate" else ROLLBACK_AP
            expected_command = [
                str(engine.DASH),
                "-c",
                engine.ODIN_CAGE_ENTRY_SCRIPT,
                "s20plus-b0-odin-cage",
                cage,
                str(engine.ODIN),
                "--reboot",
                "-a",
                str(artifact),
                "-d",
                endpoint,
            ]
            expected_kwargs = {
                "timeout": 300,
                "stdout_maximum": engine.MAX_RAW_BYTES,
                "stderr_maximum": engine.MAX_RAW_BYTES,
                "env": engine.ODIN_FIXED_ENV,
                "stdout_name": f"{kind}.stdout",
                "stderr_name": f"{kind}.stderr",
                "start_new_session": True,
            }
        else:
            expected_command = [
                str(engine.DASH),
                "-c",
                engine.ODIN_CAGE_ENTRY_SCRIPT,
                "s20plus-b0-abort-return-cage",
                cage,
                str(engine.ODIN),
                "--reboot",
                "-d",
                endpoint,
            ]
            expected_kwargs = {
                "timeout": 120,
                "stdout_maximum": engine.MAX_ADB_BYTES,
                "stderr_maximum": engine.MAX_ADB_BYTES,
                "env": engine.ODIN_FIXED_ENV,
                "stdout_name": "abort-return.stdout",
                "stderr_name": "abort-return.stderr",
            }
        if command != expected_command or kwargs != expected_kwargs:
            raise P0F1Error("P0 raw Odin command differs from its fixed intent")

    def raw_command(original):
        def guarded(argv, capture_dir, name, **kwargs):
            command = list(argv) if not isinstance(argv, (str, bytes)) else []
            adb_command = False
            if host_active():
                expected_prefix = [
                    str(engine.DASH),
                    "-c",
                    engine.CAGE_CAPABILITY_SCRIPT,
                    "s20plus-b0-cage-capability",
                ]
                if (
                    list(argv[:4]) != expected_prefix
                    or len(argv) != 6
                    or Path(argv[4]).name != "s20plus-b0-cage-capability"
                    or argv[5] != str(engine.CAGE_SLEEP)
                    or name != "cage-capability"
                    or kwargs.get("timeout") != 0.1
                    or kwargs.get("env") != engine.ODIN_FIXED_ENV
                ):
                    raise P0F1Error(
                        "P0 H0 raw command escaped its exact capability probe"
                    )
            else:
                require_active()
                validate_live_raw_command(argv, Path(capture_dir), name, kwargs)
                adb_command = len(command) >= 4 and command[:2] == [
                    str(engine.ADB),
                    "-s",
                ]
                if adb_command:
                    kwargs = dict(kwargs)
                    kwargs["env"] = adb_client_environment()
            with raw_acquisition(Path(capture_dir), name):
                result = original(argv, capture_dir, name, **kwargs)
            return result

        guarded.__name__ = "p0_dependency_raw_acquire_command"
        return guarded

    def raw_primitive(original, label: str):
        def guarded(*args, **kwargs):
            require_raw()
            return original(*args, **kwargs)

        guarded.__name__ = f"p0_dependency_{label}"
        return guarded

    def raw_writer(original):
        class GuardedRawWriter:
            __slots__ = ("_writer", "_grant", "_finalized")

            def __init__(self, *args, **kwargs) -> None:
                grant = require_raw()
                writer = original(*args, **kwargs)
                self._writer = writer
                self._grant = grant
                self._finalized = False
                grant.writers.append(self)

            def _current(self):
                grant = require_raw()
                if grant is not self._grant or self._finalized:
                    raise P0F1Error("P0 raw writer escaped its acquisition lifetime")
                return self._writer

            @property
            def stdout_size(self) -> int:
                return self._current().stdout_size

            @property
            def stderr_size(self) -> int:
                return self._current().stderr_size

            def write_stdout(self, payload: bytes) -> None:
                self._current().write_stdout(payload)

            def write_stderr(self, payload: bytes) -> None:
                self._current().write_stderr(payload)

            def stream_fds(self) -> tuple[int, int]:
                return self._current().stream_fds()

            def current_sizes(self) -> tuple[int, int]:
                return self._current().current_sizes()

            def finalize(self, **kwargs):
                writer = self._current()
                try:
                    return writer.finalize(**kwargs)
                finally:
                    self._finalized = True

            def _close_if_unfinalized(self) -> bool:
                if self._finalized:
                    return False
                writer = self._writer
                if not writer.finished:
                    for descriptor in (writer.stdout_fd, writer.stderr_fd):
                        try:
                            os.close(descriptor)
                        except OSError:
                            pass
                    writer.finished = True
                self._finalized = True
                return True

        GuardedRawWriter.__name__ = "P0GuardedRawCaptureWriter"
        return GuardedRawWriter

    def raw_direct_directory(original):
        def guarded(path: Path, *, create: bool = False):
            if create:
                require_raw()
            return original(path, create=create)

        guarded.__name__ = "p0_dependency_raw_direct_directory"
        return guarded

    def deny_raw_fixture_publication(*_args, **_kwargs):
        raise P0F1Error("P0 runtime forbids raw fixture publication")

    def make_registry_claim(original):
        def guarded(repo_root: Path, identity: Any):
            require_active()
            lease = current_lease()
            if repo_root != ROOT or not isinstance(lease.run_dir, str):
                raise P0F1Error("P0 registry claim escaped its fixed target session")
            run_dir = Path(lease.run_dir)
            binding_sha256, expected = _minimal_prepared_identity(run_dir)
            if (
                identity != expected
                or not os.path.lexists(run_dir / P0_REGISTRY_INTENT_NAME)
            ):
                raise P0F1Error("P0 registry claim differs from its durable intent")
            _registry_intent(run_dir, binding_sha256, expected)
            with mutation("claim"):
                return original(repo_root, identity)

        guarded.__name__ = "p0_registry_claim"
        return guarded

    def make_registry_release(original):
        def guarded(repo_root: Path, claim_value: Any, **kwargs):
            require_active()
            lease = current_lease()
            if repo_root != ROOT or not isinstance(lease.run_dir, str):
                raise P0F1Error("P0 registry release escaped its fixed target session")
            run_dir = Path(lease.run_dir)
            binding_sha256, identity = _minimal_prepared_identity(run_dir)
            local = _validate_local_registry_receipt(
                run_dir, binding_sha256, identity
            )["active_record"]
            if (
                not os.path.lexists(run_dir / P0_REGISTRY_RELEASE_INTENT_NAME)
                or not isinstance(claim_value, dict)
                or claim_value.get("candidate_key") != identity["candidate_key"]
                or claim_value.get("claim_id") != local["claim_id"]
                or claim_value.get("record") != local
                or kwargs
                != {
                    "release_reason": "odin_local_parse_failure",
                    "device_session_started": False,
                    "partition_transfer": False,
                }
            ):
                raise P0F1Error(
                    "P0 registry release differs from exact local-parse proof"
                )
            with mutation("release"):
                return original(repo_root, claim_value, **kwargs)

        guarded.__name__ = "p0_registry_release"
        return guarded

    def registry_internal(original, label: str):
        def guarded(*args, **kwargs):
            grant = mutation_state.get()
            event = grant.event if type(grant) is Mutation else ""
            if event not in {"claim", "release"}:
                raise P0F1Error(
                    "P0 registry record write lacks a claim or release internal capability"
                )
            require_mutation(event)
            return original(*args, **kwargs)

        guarded.__name__ = f"p0_dependency_{label}"
        return guarded

    def registry_writer(original):
        @contextlib.contextmanager
        def guarded(*args, **kwargs):
            grant = mutation_state.get()
            event = grant.event if type(grant) is Mutation else ""
            if event not in {"claim", "release"}:
                raise P0F1Error(
                    "P0 registry writer lock lacks an exact internal capability"
                )
            require_mutation(event)
            with original(*args, **kwargs):
                yield
                require_mutation(event)

        guarded.__name__ = "p0_dependency_registry_writer"
        return guarded

    return {
        "require_live": require_live,
        "bind_live_run_dir": bind_live_run_dir,
        "host_active": host_active,
        "build_entrypoint": build_entrypoint,
        "build_prepare_output": build_prepare_output,
        "build_host_validation": build_host_validation,
        "base_command": base_command,
        "adb_inventory": adb_inventory,
        "registry_replacements": {
            "claim": make_registry_claim(registry.claim),
            "release": make_registry_release(registry.release),
            "initialize": _deny_registry_initialization,
        },
        "registry_internal_replacements": {
            "_append": registry_internal(registry._append, "registry_append"),
            "_write_no_replace": registry_internal(
                registry._write_no_replace, "registry_write_no_replace"
            ),
            "_write_head": registry_internal(
                registry._write_head, "registry_write_head"
            ),
            "_writer": registry_writer(registry._writer),
        },
        "raw_replacements": {
            "acquire_command": raw_command(engine.raw_capture.acquire_command),
            "RawCaptureWriter": raw_writer(engine.raw_capture.RawCaptureWriter),
            "publish_captured_bytes": deny_raw_fixture_publication,
            "prepare_capture_dir": raw_primitive(
                engine.raw_capture.prepare_capture_dir,
                "raw_capture_prepare_capture_dir",
            ),
            "_direct_directory": raw_direct_directory(
                engine.raw_capture._direct_directory
            ),
            "_open_stream": raw_primitive(
                engine.raw_capture._open_stream, "raw_capture_open_stream"
            ),
            "_write_all": raw_primitive(
                engine.raw_capture._write_all, "raw_capture_write_all"
            ),
            "_durable_create": raw_primitive(
                engine.raw_capture._durable_create, "raw_capture_durable_create"
            ),
            "_fsync_dir": raw_primitive(
                engine.raw_capture._fsync_dir, "raw_capture_fsync_dir"
            ),
        },
    }


_capability_system = _create_capability_system()
_require_live_transaction = _capability_system["require_live"]
_bind_live_run_dir = _capability_system["bind_live_run_dir"]
_host_validation_active = _capability_system["host_active"]
_build_entrypoint_capability = _capability_system["build_entrypoint"]
_build_prepare_output_capability = _capability_system["build_prepare_output"]
_build_host_validation_capability = _capability_system["build_host_validation"]
_build_base_command_capability = _capability_system["base_command"]
_build_adb_inventory_capability = _capability_system["adb_inventory"]
_REGISTRY_MUTATION_REPLACEMENTS = _capability_system["registry_replacements"]
_REGISTRY_INTERNAL_REPLACEMENTS = _capability_system[
    "registry_internal_replacements"
]
_RAW_CAPABILITY_REPLACEMENTS = _capability_system["raw_replacements"]
del _capability_system
del _create_capability_system

_ENGINE_VALIDATE_HOST_CLOSURE = engine.validate_host_closure
_ENGINE_HOST_VALIDATION_CALL = _build_host_validation_capability(
    _ENGINE_VALIDATE_HOST_CLOSURE
)
del _build_host_validation_capability
_ENGINE_VALIDATE_ROLLBACK_CLOSURE = engine.validate_rollback_closure
_ENGINE_VALIDATE_HEALTH_CLOSURE = engine.validate_health_closure
_ENGINE_VALIDATE_MANIFEST = engine.validate_manifest
_ENGINE_REQUIRE_ACTIVE = engine.require_active
_ENGINE_CONSUME_CANDIDATE = _guarded_live_alias(
    engine.consume_candidate_globally, "engine_consume_candidate"
)
_ENGINE_REQUIRE_CANDIDATE_CLAIM = _guarded_live_alias(
    engine.require_candidate_claim, "engine_require_candidate_claim"
)
_ENGINE_OPEN_DIRECT_DIRECTORY = engine.open_direct_directory
_ENGINE_OBSERVE_CANDIDATE = _guarded_live_alias(
    engine.observe_candidate, "engine_observe_candidate"
)
_ENGINE_VALIDATE_CANDIDATE_OBSERVATION = engine._validate_candidate_observation
_ENGINE_VALIDATE_TRANSFER_OUTCOME = engine._validate_transfer_outcome
_ENGINE_VALIDATE_NAMESPACE = engine.validate_namespace
_ENGINE_DERIVE_TERMINAL_VERDICT = engine.derive_terminal_verdict
_ENGINE_CANDIDATE_CLAIM_INTENT = _guarded_live_alias(
    engine._candidate_claim_intent, "engine_candidate_claim_intent"
)

_OBSERVER_LIVE_NAMES = (
    "usb_device_nodes",
    "ttys_for_usb",
    "scan_inventory",
    "capture_baseline",
    "select_arrival",
    "verify_descriptor",
    "read_exact_banner",
    "observe_selected",
    "open_live",
    "observe_attended",
)
_OBSERVER_LIVE_REPLACEMENTS = {
    name: _guarded_live_alias(getattr(observer, name), f"observer_{name}")
    for name in _OBSERVER_LIVE_NAMES
}

_BOUND_OBSERVER_APIS = dict(_OBSERVER_LIVE_REPLACEMENTS)
_BOUND_REGISTRY_APIS = {
    "validate": registry.validate,
    "derive_candidate_identity": registry.derive_candidate_identity,
    "preflight_candidate": registry.preflight_candidate,
    "active_claim": registry.active_claim,
    "target_session_lease": registry.target_session_lease,
    "_validate_record": registry._validate_record,
    **_REGISTRY_MUTATION_REPLACEMENTS,
}
_BASE_RUN_NODE_NAMES = engine.RUN_NODE_NAMES
P0_RUN_NODE_NAMES = frozenset(
    set(_BASE_RUN_NODE_NAMES)
    | {
        P0_BASELINE_NAME,
        P0_RAW_BANNER_NAME,
        P0_REGISTRY_INTENT_NAME,
        P0_REGISTRY_RECEIPT_NAME,
        P0_REGISTRY_UNCERTAIN_NAME,
        P0_REGISTRY_RELEASE_INTENT_NAME,
        P0_REGISTRY_RELEASE_RECEIPT_NAME,
        P0_LOCAL_PROJECTION_RELEASE_NAME,
        P0_CANDIDATE_PREFLIGHT_NAME,
        P0_PHYSICAL_REBIND_ARM_NAME,
        P0_PHYSICAL_REBIND_CONFIRM_NAME,
        P0_PHYSICAL_REBIND_ARRIVAL_NAME,
        P0_PHYSICAL_REBIND_MISS_NAME,
        *(
            f"p0-{kind}-cage-{generation:04d}-{suffix}.json"
            for kind in CAGE_KINDS
            for generation in range(1, CAGE_GENERATION_MAXIMUM + 1)
            for suffix in ("prepare", "bound", "reconciled")
        ),
        *(
            f"p0-odin-listing-{generation:04d}{suffix}"
            for generation in range(1, CAGE_GENERATION_MAXIMUM + 1)
            for suffix in (
                "-intent.json",
                "-result.json",
                ".stdout",
                ".stderr",
                ".capture.json",
            )
        ),
    }
)


def _profile_value_replacements() -> dict[str, Any]:
    return {
        "VERSION": VERSION,
        "PLAN_SCHEMA": PLAN_SCHEMA,
        "B0_F1_ACTIVE": P0_F1_ACTIVE,
        "RUN_ROOT": RUN_ROOT,
        "CLAIM_ROOT": CLAIM_ROOT,
        "SHARED_GUARD": SHARED_GUARD,
        "OUTPUT_ROOT": OUTPUT_ROOT,
        "CANDIDATE_AP": CANDIDATE_AP,
        "CANDIDATE_AP_SIZE": CANDIDATE_AP_SIZE,
        "CANDIDATE_AP_SHA256": CANDIDATE_AP_SHA256,
        "CANDIDATE_MEMBER_SIZE": CANDIDATE_MEMBER_SIZE,
        "CANDIDATE_MEMBER_SHA256": CANDIDATE_MEMBER_SHA256,
        "CANDIDATE_BOOT_SIZE": CANDIDATE_BOOT_SIZE,
        "CANDIDATE_BOOT_SHA256": CANDIDATE_BOOT_SHA256,
        "ROLLBACK_AP": ROLLBACK_AP,
        "ROLLBACK_AP_SIZE": ROLLBACK_AP_SIZE,
        "ROLLBACK_AP_SHA256": ROLLBACK_AP_SHA256,
        "ROLLBACK_MEMBER_SIZE": ROLLBACK_MEMBER_SIZE,
        "ROLLBACK_MEMBER_SHA256": ROLLBACK_MEMBER_SHA256,
        "ROLLBACK_BOOT_SIZE": ROLLBACK_BOOT_SIZE,
        "ROLLBACK_BOOT_SHA256": ROLLBACK_BOOT_SHA256,
        "MANIFEST": MANIFEST,
        "MANIFEST_SIZE": MANIFEST_SIZE,
        "MANIFEST_SHA256": MANIFEST_SHA256,
        "BUILDER": BUILDER_PATH,
        "BUILDER_SIZE": BUILDER_SIZE,
        "BUILDER_SHA256": BUILDER_SHA256,
        "APPROVAL_PREFIX": APPROVAL_PREFIX,
        "PHYSICAL_CONFIRM_PREFIX": PHYSICAL_CONFIRM_PREFIX,
        "RECOVERY_ARRIVAL_SECONDS": P0_ARRIVAL_TIMEOUT_SECONDS,
        "RECOVERY_PREDECESSOR_NORMALIZED_SHA256": frozenset(),
        "RUN_NODE_NAMES": P0_RUN_NODE_NAMES,
    }


def normalized_self_sha256() -> str:
    source = SCRIPT.read_bytes()
    source, active_count = re.subn(
        rb"^P0_F1_ACTIVE = (?:False|True)$",
        b"P0_F1_ACTIVE = <REVIEWED_ACTIVATION_BOOLEAN>",
        source,
        flags=re.MULTILINE,
    )
    source, hash_count = re.subn(
        rb'^EXPECTED_REVIEWED_NORMALIZED_SHA256 = "[0-9a-f]{64}"$',
        b'EXPECTED_REVIEWED_NORMALIZED_SHA256 = "' + b"0" * 64 + b'"',
        source,
        flags=re.MULTILINE,
    )
    if active_count != 1 or hash_count != 1:
        raise P0F1Error("P0 owner normalization grammar changed")
    return hashlib.sha256(source).hexdigest()


def self_receipt() -> dict[str, Any]:
    metadata = SCRIPT.lstat()
    if (
        SCRIPT.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or SCRIPT.resolve(strict=True) != SCRIPT.absolute()
    ):
        raise P0F1Error("P0 owner source is indirect")
    normalized = normalized_self_sha256()
    if normalized != EXPECTED_REVIEWED_NORMALIZED_SHA256:
        raise P0F1Error("P0 owner source is not the reviewed normalized identity")
    return {
        "path": str(SCRIPT),
        "size": metadata.st_size,
        "sha256": hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
        "normalized_sha256": normalized,
    }


def _current_file_receipt(path: Path, label: str) -> dict[str, Any]:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise P0F1Error(f"{label} is unavailable") from exc
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or path.resolve(strict=True) != path.absolute()
    ):
        raise P0F1Error(f"{label} is indirect")
    payload = path.read_bytes()
    if len(payload) != metadata.st_size:
        raise P0F1Error(f"{label} changed while reading")
    return {
        "path": str(path),
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _normalized_observer_sha256() -> str:
    source = OBSERVER_PATH.read_bytes()
    source, count = re.subn(
        rb"^OBSERVER_ACTIVE = (?:False|True)$",
        b"OBSERVER_ACTIVE = <REVIEWED_ACTIVATION_BOOLEAN>",
        source,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise P0F1Error("P0 observer normalization grammar changed")
    return hashlib.sha256(source).hexdigest()


def _read_private_activation_record(
    path: Path, schema: str, label: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise P0F1Error(f"{label} is absent") from exc
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o400
        or metadata.st_nlink != 1
        or path.resolve(strict=True) != path.absolute()
    ):
        raise P0F1Error(f"{label} is indirect")
    value = engine.read_json(path, label)
    if value.get("schema") != schema or value.get("version") != VERSION:
        raise P0F1Error(f"{label} schema differs")
    return value, _current_file_receipt(path, label)


def _reviewed_closure_current() -> dict[str, Any]:
    return {
        "owner": self_receipt(),
        "owner_normalized_sha256": normalized_self_sha256(),
        "observer": _current_file_receipt(OBSERVER_PATH, "P0 observer"),
        "observer_normalized_sha256": _normalized_observer_sha256(),
        "engine": _direct_receipt(
            ENGINE_PATH, ENGINE_SIZE, ENGINE_SHA256, "P0 B0 engine"
        ),
        "registry_source": _direct_receipt(
            REGISTRY_PATH, REGISTRY_SIZE, REGISTRY_SHA256, "P0 registry source"
        ),
        "registry_activation": _direct_receipt(
            REGISTRY_ACTIVATION,
            REGISTRY_ACTIVATION_SIZE,
            REGISTRY_ACTIVATION_SHA256,
            "P0 registry activation",
        ),
        "policy": {
            name: _current_file_receipt(path, f"P0 review policy {name}")
            for name, path in sorted(P0_POLICY_FILES.items())
        },
        "tests": {
            name: _current_file_receipt(path, f"P0 review test {name}")
            for name, path in sorted(P0_TEST_FILES.items())
        },
        "activation_document_semantics": _current_document_semantics(),
        "activation_documents_normalized": (
            _activation_document_normalized_receipts()
        ),
    }


def _stable_regular_identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _read_review_test_log(
    log_root: Path, path: Path, label: str
) -> tuple[dict[str, Any], str]:
    direct = path.absolute()
    try:
        root_metadata = log_root.lstat()
        metadata = direct.lstat()
    except OSError as exc:
        raise P0F1Error(f"{label} is unavailable") from exc
    if (
        log_root.is_symlink()
        or not stat.S_ISDIR(root_metadata.st_mode)
        or stat.S_IMODE(root_metadata.st_mode) != 0o700
        or log_root.resolve(strict=True) != log_root.absolute()
        or direct.parent != log_root
        or direct.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o400
        or metadata.st_nlink != 1
        or not 1 <= metadata.st_size <= 1024 * 1024
        or direct.resolve(strict=True) != direct
    ):
        raise P0F1Error(f"{label} identity differs")
    descriptor = os.open(
        direct, os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        before = os.fstat(descriptor)
        payload = os.read(descriptor, 1024 * 1024 + 1)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = direct.lstat()
    if (
        _stable_regular_identity(before) != _stable_regular_identity(after)
        or _stable_regular_identity(after) != _stable_regular_identity(current)
        or len(payload) != metadata.st_size
    ):
        raise P0F1Error(f"{label} changed while reading")
    try:
        text = payload.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise P0F1Error(f"{label} is not UTF-8") from exc
    if "\r" in text or "\x00" in text:
        raise P0F1Error(f"{label} framing differs")
    return (
        {
            "path": str(direct),
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "mode": "0400",
        },
        text,
    )


def _validate_review_test_results(
    value: Any, reviewed_sha256: str, log_root: Path
) -> None:
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "reviewed_closure_sha256", "suites"}
        or value.get("schema") != P0_REVIEW_TEST_RESULTS_SCHEMA
        or value.get("reviewed_closure_sha256") != reviewed_sha256
        or not isinstance(value.get("suites"), dict)
        or set(value["suites"]) != set(P0_REVIEW_TEST_REQUIREMENTS)
    ):
        raise P0F1Error("P0 review test results shape differs")
    try:
        names = {entry.name for entry in os.scandir(log_root)}
    except OSError as exc:
        raise P0F1Error("P0 review test log namespace is unavailable") from exc
    expected_names = {
        requirement["log_name"] for requirement in P0_REVIEW_TEST_REQUIREMENTS.values()
    }
    if names != expected_names:
        raise P0F1Error("P0 review test log namespace differs")
    for name, requirement in sorted(P0_REVIEW_TEST_REQUIREMENTS.items()):
        suite = value["suites"].get(name)
        if (
            not isinstance(suite, dict)
            or set(suite)
            != {
                "runner",
                "modules",
                "tests",
                "skipped",
                "failures",
                "errors",
                "result",
                "raw_receipt",
            }
            or suite.get("runner") != "python3 -m unittest"
            or suite.get("modules") != requirement["modules"]
            or type(suite.get("tests")) is not int
            or suite.get("tests") != requirement["tests"]
            or type(suite.get("skipped")) is not int
            or suite.get("skipped") != requirement["skipped"]
            or type(suite.get("failures")) is not int
            or suite.get("failures") != 0
            or type(suite.get("errors")) is not int
            or suite.get("errors") != 0
            or suite.get("result") != "OK"
        ):
            raise P0F1Error(f"P0 review test suite differs: {name}")
        receipt, text = _read_review_test_log(
            log_root,
            log_root / requirement["log_name"],
            f"P0 review test log {name}",
        )
        terminal = (
            "OK"
            if requirement["skipped"] == 0
            else f"OK (skipped={requirement['skipped']})"
        )
        ran = re.findall(
            r"(?m)^Ran ([0-9]+) tests? in [0-9]+(?:\.[0-9]+)?s$", text
        )
        if (
            suite.get("raw_receipt") != receipt
            or ran != [str(requirement["tests"])]
            or not text.rstrip().endswith(terminal)
            or "FAILED" in text
            or "Traceback (most recent call last)" in text
        ):
            raise P0F1Error(f"P0 review test raw result differs: {name}")


def _validate_zero_finding_review() -> tuple[dict[str, Any], dict[str, Any]]:
    value, receipt = _read_private_activation_record(
        P0_ZERO_FINDING_REVIEW,
        P0_ZERO_FINDING_REVIEW_SCHEMA,
        "P0 zero-finding review record",
    )
    reviewed = value.get("reviewed_closure")
    verdict = value.get("independent_review")
    if (
        set(value)
        != {
            "schema",
            "version",
            "target",
            "reviewed_closure",
            "reviewed_closure_sha256",
            "independent_review",
            "reviewer_device_contacts",
            "reviewer_writes",
            "tests_run",
            "at",
        }
        or value.get("target") != engine.TARGET
        or not isinstance(reviewed, dict)
        or value.get("reviewed_closure_sha256") != engine.digest(reviewed)
        or verdict
        != {"verdict": "PASS_GO", "high": 0, "medium": 0, "low": 0}
        or value.get("reviewer_device_contacts") != 0
        or value.get("reviewer_writes") != 0
        or type(value.get("tests_run")) is not dict
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise P0F1Error("P0 zero-finding review record differs")
    _validate_review_test_results(
        value["tests_run"],
        value["reviewed_closure_sha256"],
        P0_REVIEW_TEST_LOG_ROOT,
    )
    current = _reviewed_closure_current()
    if (
        set(reviewed) != set(current)
        or reviewed.get("owner", {}).get("path") != current["owner"]["path"]
        or reviewed.get("owner_normalized_sha256")
        != current["owner_normalized_sha256"]
        or reviewed.get("observer", {}).get("path") != current["observer"]["path"]
        or reviewed.get("observer_normalized_sha256")
        != current["observer_normalized_sha256"]
        or reviewed.get("engine") != current["engine"]
        or reviewed.get("registry_source") != current["registry_source"]
        or reviewed.get("registry_activation") != current["registry_activation"]
        or reviewed.get("tests") != current["tests"]
        or set(reviewed.get("policy", {})) != set(current["policy"])
        or any(
            reviewed.get("policy", {}).get(name) != current["policy"][name]
            for name in P0_UNCHANGED_POLICY_NAMES
        )
        or reviewed.get("activation_document_semantics")
        != P0_DORMANT_DOCUMENT_SEMANTICS
        or reviewed.get("activation_documents_normalized")
        != current["activation_documents_normalized"]
        or any(
            reviewed.get("policy", {}).get(name, {}).get("path")
            != str(P0_POLICY_FILES[name])
            for name in P0_DORMANT_DOCUMENT_SEMANTICS
        )
    ):
        raise P0F1Error("P0 reviewed dormant closure drifted")
    return value, receipt


def _semantic_markdown_lines(text: str, label: str) -> list[str]:
    if "\r" in text or "\x00" in text:
        raise P0F1Error(f"P0 {label} text framing differs")
    lines: list[str] = []
    in_comment = False
    fence: str | None = None
    for raw in text.splitlines():
        remaining = raw
        visible = ""
        while remaining:
            if in_comment:
                _hidden, separator, remaining = remaining.partition("-->")
                if not separator:
                    remaining = ""
                    break
                in_comment = False
                continue
            before, separator, after = remaining.partition("<!--")
            visible += before
            if not separator:
                remaining = ""
                break
            in_comment = True
            remaining = after
        stripped = visible.lstrip()
        if fence is not None:
            if stripped.startswith(fence):
                fence = None
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fence = stripped[:3]
            continue
        lines.append(visible)
    if in_comment or fence is not None:
        raise P0F1Error(f"P0 {label} contains an unterminated hidden block")
    return lines


def _section_status(text: str, heading: str, label: str) -> str:
    lines = _semantic_markdown_lines(text, label)
    matches = [index for index, line in enumerate(lines) if line == heading]
    if len(matches) != 1:
        raise P0F1Error(f"P0 {label} authoritative section differs")
    index = matches[0]
    if (
        index + 2 >= len(lines)
        or lines[index + 1] != ""
        or not lines[index + 2].startswith("Status: ")
    ):
        raise P0F1Error(f"P0 {label} authoritative status position differs")
    end = next(
        (
            ordinal
            for ordinal in range(index + 3, len(lines))
            if lines[ordinal].startswith("## ")
        ),
        len(lines),
    )
    statuses = [line for line in lines[index + 2 : end] if line.startswith("Status: ")]
    if statuses != [lines[index + 2]]:
        raise P0F1Error(f"P0 {label} authoritative status differs")
    return lines[index + 2]


def _preamble_status(text: str, label: str) -> str:
    lines = _semantic_markdown_lines(text, label)
    end = next(
        (index for index, line in enumerate(lines) if line.startswith("## ")),
        len(lines),
    )
    fields = [line for line in lines[:end] if line]
    if (
        len(fields) != 5
        or fields[0] != "# S20+ G986N P0 PID1 Odin F1 owner H0 implementation"
        or fields[1] != "Date: 2026-09-01"
        or fields[2]
        != "Target: `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`"
        or fields[3] != "Tier: H0 only"
        or not fields[4].startswith("Status: ")
    ):
        raise P0F1Error(f"P0 {label} preamble structure differs")
    return fields[4]


def _registry_process_cell(text: str) -> str:
    lines = _semantic_markdown_lines(text, "repository registry")
    header = "| Target | Current state | Binding target contract | Binding live process |"
    separator = "|---|---|---|---|"
    headers = [index for index, line in enumerate(lines) if line == header]
    if len(headers) != 1 or headers[0] + 1 >= len(lines):
        raise P0F1Error("P0 repository registry table is absent or ambiguous")
    index = headers[0]
    if lines[index + 1] != separator:
        raise P0F1Error("P0 repository registry header differs")
    rows: list[list[str]] = []
    for line in lines[index + 2 :]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 4:
            raise P0F1Error("P0 repository registry row shape differs")
        rows.append(cells)
    matches = [row for row in rows if row[0] == P0_REGISTRY_TARGET_CELL]
    if (
        len(matches) != 1
        or matches[0][1] != P0_REGISTRY_GOAL_CELL
        or matches[0][2] != P0_REGISTRY_CONTRACT_CELL
    ):
        raise P0F1Error("P0 repository registry row is absent or ambiguous")
    return matches[0][3]


def _current_document_semantics(
    documents: dict[str, str] | None = None,
) -> dict[str, str]:
    if documents is None:
        documents = {
            name: P0_POLICY_FILES[name].read_text("utf-8")
            for name in P0_DORMANT_DOCUMENT_SEMANTICS
        }
    return {
        "repository_contract": _registry_process_cell(documents["repository_contract"]),
        "target_contract": _section_status(
            documents["target_contract"],
            "## P0 PID1 ACM Odin boot-only F1",
            "target contract",
        ),
        "current_goal": _section_status(
            documents["current_goal"],
            "## Current P0 PID1 Odin F1 state",
            "current goal",
        ),
        "qualification_report": _preamble_status(
            documents["qualification_report"], "qualification report"
        ),
    }


def _normalized_activation_document(name: str, text: str, actual: str) -> bytes:
    if name == "repository_contract":
        row = (
            f"| {P0_REGISTRY_TARGET_CELL} | {P0_REGISTRY_GOAL_CELL} | "
            f"{P0_REGISTRY_CONTRACT_CELL} | {actual} |"
        )
        replacement = row.replace(actual, P0_DOCUMENT_ACTIVATION_PLACEHOLDER)
        marker = row
    elif name == "target_contract":
        marker = f"\n## P0 PID1 ACM Odin boot-only F1\n\n{actual}\n"
        replacement = marker.replace(actual, P0_DOCUMENT_ACTIVATION_PLACEHOLDER)
    elif name == "current_goal":
        marker = f"\n## Current P0 PID1 Odin F1 state\n\n{actual}\n"
        replacement = marker.replace(actual, P0_DOCUMENT_ACTIVATION_PLACEHOLDER)
    elif name == "qualification_report":
        marker = f"\nTier: H0 only\n\n{actual}\n\n## Outcome\n"
        replacement = marker.replace(actual, P0_DOCUMENT_ACTIVATION_PLACEHOLDER)
    else:
        raise P0F1Error("P0 activation document name differs")
    if text.count(marker) != 1:
        raise P0F1Error(f"P0 {name} activation marker is absent or ambiguous")
    return text.replace(marker, replacement, 1).encode("utf-8")


def _activation_document_normalized_receipts() -> dict[str, dict[str, Any]]:
    documents = {
        name: P0_POLICY_FILES[name].read_text("utf-8")
        for name in P0_DORMANT_DOCUMENT_SEMANTICS
    }
    semantics = _current_document_semantics(documents)
    receipts: dict[str, dict[str, Any]] = {}
    for name, actual in semantics.items():
        if actual not in {
            P0_DORMANT_DOCUMENT_SEMANTICS[name],
            P0_ACTIVE_DOCUMENT_SEMANTICS[name],
        }:
            raise P0F1Error(f"P0 {name} is neither reviewed dormant nor active")
        normalized = _normalized_activation_document(name, documents[name], actual)
        receipts[name] = {
            "path": str(P0_POLICY_FILES[name]),
            "normalized_sha256": hashlib.sha256(normalized).hexdigest(),
        }
    return receipts


def _active_document_semantics() -> dict[str, str]:
    actual = _current_document_semantics()
    if actual != P0_ACTIVE_DOCUMENT_SEMANTICS:
        raise P0F1Error("P0 active document semantics are incomplete")
    return dict(P0_ACTIVE_DOCUMENT_SEMANTICS)


def _active_test_closure(
    reviewed: dict[str, Any],
    activation_diff: dict[str, Any],
    normalized_closure: dict[str, Any],
) -> dict[str, Any]:
    return {
        "activation_diff_sha256": engine.digest(activation_diff),
        "normalized_closure_sha256": engine.digest(normalized_closure),
        "engine": reviewed["engine"],
        "registry_source": reviewed["registry_source"],
        "registry_activation": reviewed["registry_activation"],
        "tests": reviewed["tests"],
        "unchanged_policy": {
            name: reviewed["policy"][name]
            for name in sorted(P0_UNCHANGED_POLICY_NAMES)
        },
    }


def _validate_mechanical_activation(
    zero_value: dict[str, Any], zero_receipt: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    value, receipt = _read_private_activation_record(
        P0_MECHANICAL_ACTIVATION,
        P0_MECHANICAL_ACTIVATION_SCHEMA,
        "P0 mechanical activation record",
    )
    reviewed = zero_value["reviewed_closure"]
    before = {
        "owner": reviewed["owner"],
        "observer": reviewed["observer"],
        **{
            name: reviewed["policy"][name]
            for name in (
                "repository_contract",
                "target_contract",
                "current_goal",
                "qualification_report",
            )
        },
    }
    after = {
        name: _current_file_receipt(path, f"P0 active file {name}")
        for name, path in sorted(P0_ACTIVATION_CHANGE_FILES.items())
    }
    activation_diff = {
        name: {"before": before[name], "after": after[name]}
        for name in sorted(P0_ACTIVATION_CHANGE_FILES)
    }
    normalized_closure = {
        "owner": reviewed["owner_normalized_sha256"],
        "observer": reviewed["observer_normalized_sha256"],
        "documents": reviewed["activation_documents_normalized"],
    }
    current_normalized_closure = {
        "owner": normalized_self_sha256(),
        "observer": _normalized_observer_sha256(),
        "documents": _activation_document_normalized_receipts(),
    }
    active_test_closure = _active_test_closure(
        reviewed, activation_diff, normalized_closure
    )
    transitions = {
        "owner_active": [False, True],
        "observer_active": [False, True],
        "repository_registry": [
            P0_DORMANT_REGISTRY_PROCESS_CELL,
            P0_ACTIVE_REGISTRY_PROCESS_CELL,
        ],
        "target_contract": [P0_DORMANT_CONTRACT_MARKER, P0_ACTIVE_CONTRACT_MARKER],
        "current_goal": [P0_DORMANT_GOAL_MARKER, P0_ACTIVE_GOAL_MARKER],
        "qualification_report": [
            P0_DORMANT_REPORT_MARKER,
            P0_ACTIVE_REPORT_MARKER,
        ],
    }
    verdict = value.get("independent_review")
    if (
        set(value)
        != {
            "schema",
            "version",
            "target",
            "zero_finding_review",
            "activation_diff",
            "activation_diff_sha256",
            "allowlisted_changes",
            "normalized_closure",
            "normalized_closure_sha256",
            "active_test_closure",
            "active_test_closure_sha256",
            "active_tests_run",
            "semantic_transitions",
            "independent_review",
            "reviewer_device_contacts",
            "reviewer_writes",
            "at",
        }
        or value.get("target") != engine.TARGET
        or value.get("zero_finding_review") != zero_receipt
        or value.get("activation_diff") != activation_diff
        or value.get("activation_diff_sha256") != engine.digest(activation_diff)
        or value.get("allowlisted_changes") != P0_ACTIVATION_CHANGE_RULES
        or normalized_closure != current_normalized_closure
        or value.get("normalized_closure") != normalized_closure
        or value.get("normalized_closure_sha256")
        != engine.digest(normalized_closure)
        or value.get("active_test_closure") != active_test_closure
        or value.get("active_test_closure_sha256")
        != engine.digest(active_test_closure)
        or type(value.get("active_tests_run")) is not dict
        or value.get("semantic_transitions") != transitions
        or verdict
        != {"verdict": "PASS_GO", "high": 0, "medium": 0, "low": 0}
        or value.get("reviewer_device_contacts") != 0
        or value.get("reviewer_writes") != 0
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise P0F1Error("P0 mechanical activation record differs")
    _active_document_semantics()
    _validate_review_test_results(
        value["active_tests_run"],
        value["active_test_closure_sha256"],
        P0_ACTIVE_REVIEW_TEST_LOG_ROOT,
    )
    return value, receipt


def _live_activation_expected() -> dict[str, Any]:
    zero_value, zero_receipt = _validate_zero_finding_review()
    _mechanical_value, mechanical_receipt = _validate_mechanical_activation(
        zero_value, zero_receipt
    )
    closure = {
        "owner": self_receipt(),
        "observer": _direct_receipt(
            OBSERVER_PATH, OBSERVER_SIZE, OBSERVER_SHA256, "P0 observer"
        ),
        "engine": _direct_receipt(
            ENGINE_PATH, ENGINE_SIZE, ENGINE_SHA256, "P0 B0 engine"
        ),
        "registry_source": _direct_receipt(
            REGISTRY_PATH, REGISTRY_SIZE, REGISTRY_SHA256, "P0 global registry source"
        ),
        "registry_activation": _direct_receipt(
            REGISTRY_ACTIVATION,
            REGISTRY_ACTIVATION_SIZE,
            REGISTRY_ACTIVATION_SHA256,
            "P0 global registry activation",
        ),
        "policy": {
            name: _current_file_receipt(path, f"P0 activation policy {name}")
            for name, path in sorted(P0_POLICY_FILES.items())
        },
        "tests": {
            name: _current_file_receipt(path, f"P0 activation test {name}")
            for name, path in sorted(P0_TEST_FILES.items())
        },
        "zero_finding_review": zero_receipt,
        "mechanical_activation": mechanical_receipt,
    }
    return {
        "schema": P0_LIVE_ACTIVATION_SCHEMA,
        "version": VERSION,
        "active": True,
        "target": dict(engine.TARGET),
        "owner_active": True,
        "observer_active": True,
        "mechanical_activation_reviewed": True,
        "independent_review": {
            "verdict": "PASS_GO",
            "high": 0,
            "medium": 0,
            "low": 0,
        },
        "closure": closure,
        "closure_sha256": engine.digest(closure),
        "target_session_lock": {
            "path": str(_session_lock_path()),
            "payload_sha256": hashlib.sha256(
                registry.SESSION_LOCK_PAYLOAD
            ).hexdigest(),
            "mode": "0600",
            "nonblocking_exclusive_flock": True,
        },
        "fresh_prepare_required": True,
        "fresh_exact_approval_required": True,
    }


def _validate_live_activation() -> dict[str, Any]:
    try:
        metadata = P0_LIVE_ACTIVATION.lstat()
    except OSError as exc:
        raise P0F1Error("P0 live activation record is absent") from exc
    if (
        P0_LIVE_ACTIVATION.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o400
        or metadata.st_nlink != 1
        or P0_LIVE_ACTIVATION.resolve(strict=True) != P0_LIVE_ACTIVATION.absolute()
    ):
        raise P0F1Error("P0 live activation record is indirect")
    value = engine.read_json(P0_LIVE_ACTIVATION, "P0 live activation record")
    expected = _live_activation_expected()
    if value != expected:
        raise P0F1Error("P0 live activation record differs from current closure")
    return value


def _assert_profile_installed() -> None:
    expected_values = _profile_value_replacements()
    if any(getattr(engine, name) != value for name, value in expected_values.items()):
        raise P0F1Error("isolated B0 engine P0 profile drifted")
    expected_functions = _profile_function_replacements()
    if any(getattr(engine, name) is not value for name, value in expected_functions.items()):
        raise P0F1Error("isolated B0 engine P0 function profile drifted")
    if any(
        getattr(observer, name) is not value
        for name, value in _BOUND_OBSERVER_APIS.items()
    ):
        raise P0F1Error("P0 observer API was rebound")
    if any(
        getattr(registry, name) is not value
        for name, value in _BOUND_REGISTRY_APIS.items()
    ):
        raise P0F1Error("P0 global registry API was rebound")
    if engine.open_direct_directory is not _ENGINE_OPEN_DIRECT_DIRECTORY:
        raise P0F1Error("P0 raw evidence directory API was rebound")
    if any(
        getattr(module, attribute) is not replacement
        for module, attribute, replacement in _EXECUTION_DEPENDENCY_REPLACEMENTS.values()
    ):
        raise P0F1Error("P0 execution dependency fence was rebound")
    expected_bound = {
        "inventory.bounded_command": _EXECUTION_DEPENDENCY_REPLACEMENTS[
            "base.bounded_command"
        ][2],
        "raw_capture.acquire_command": _EXECUTION_DEPENDENCY_REPLACEMENTS[
            "raw_capture.acquire_command"
        ][2],
    }
    if any(engine._BOUND_APIS.get(name) is not value for name, value in expected_bound.items()):
        raise P0F1Error("P0 inherited dependency identity was not fenced")


def _strict_manifest() -> dict[str, Any]:
    _direct_receipt(MANIFEST, MANIFEST_SIZE, MANIFEST_SHA256, "P0 manifest")
    try:
        value = json.loads(
            MANIFEST.read_text("utf-8"),
            object_pairs_hook=engine._unique_pairs,
            parse_constant=engine._reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise P0F1Error("P0 manifest is malformed") from exc
    outputs = {
        "AP.tar.md5": {"size": CANDIDATE_AP_SIZE, "sha256": CANDIDATE_AP_SHA256},
        "boot.img": {"size": CANDIDATE_BOOT_SIZE, "sha256": CANDIDATE_BOOT_SHA256},
        "boot.img.lz4": {
            "size": CANDIDATE_MEMBER_SIZE,
            "sha256": CANDIDATE_MEMBER_SHA256,
        },
        "s20plus_p0_pid1_init": {
            "size": 3_584,
            "sha256": "2a1e7b4a1c485058c790efca6dcc4fd3df1785496795c5fda299a026f77d40ee",
        },
    }
    observer_contract = value.get("observer_contract", {}) if isinstance(value, dict) else {}
    safety = value.get("safety", {}) if isinstance(value, dict) else {}
    if (
        type(value) is not dict
        or value.get("schema") != "s20plus_g986n_p0_pid1_acm_build_v2"
        or value.get("target") != engine.TARGET
        or value.get("tier") != "H0"
        or value.get("live_authority") is not False
        or value.get("outputs") != outputs
        or observer_contract.get("banner_hex") != observer.BANNER.hex()
        or observer_contract.get("banner_sha256")
        != hashlib.sha256(observer.BANNER).hexdigest()
        or observer_contract.get("banner_size") != len(observer.BANNER)
        or observer_contract.get("pid_value_derived_from_first_getpid_gate") is not True
        or observer_contract.get("usb_vendor") != observer.USB_VENDOR
        or observer_contract.get("usb_product") != observer.USB_PRODUCT
        or observer_contract.get("manufacturer") != observer.USB_MANUFACTURER
        or observer_contract.get("product_string") != observer.USB_PRODUCT_STRING
        or observer_contract.get("serial_descriptor") is not False
        or safety.get("boot_only_output") is not True
        or safety.get("global_pid1_candidate") is not True
        or safety.get("ramdisk_init_replaced") is not True
        or safety.get("kernel_preserved") is not True
        or safety.get("dtb_preserved") is not True
        or safety.get("header_preserved") is not True
        or safety.get("block_device_access") is not False
        or safety.get("persistent_write") is not False
        or safety.get("reboot_syscall") is not False
        or safety.get("tar_members") != ["boot.img.lz4"]
    ):
        raise P0F1Error("P0 manifest closure differs")
    return value


def validate_manifest() -> dict[str, Any]:
    _strict_manifest()
    return _direct_receipt(MANIFEST, MANIFEST_SIZE, MANIFEST_SHA256, "P0 manifest")


def _registry_authority() -> dict[str, Any]:
    source = _direct_receipt(
        REGISTRY_PATH, REGISTRY_SIZE, REGISTRY_SHA256, "P0 global registry source"
    )
    activation = _direct_receipt(
        REGISTRY_ACTIVATION,
        REGISTRY_ACTIVATION_SIZE,
        REGISTRY_ACTIVATION_SHA256,
        "P0 global registry activation",
    )
    try:
        state = registry.validate(ROOT)
        activation_value = engine.read_json(
            REGISTRY_ACTIVATION, "P0 global registry activation"
        )
    except registry.RegistryError as exc:
        raise P0F1Error("P0 global candidate registry failed closed") from exc
    except engine.B0F1Error as exc:
        raise P0F1Error("P0 global registry activation failed closed") from exc
    activation_payload = engine.canonical_bytes(activation_value)
    legacy_candidates = activation_value.get("legacy_candidates")
    if (
        state.get("schema") != registry.REGISTRY_SCHEMA
        or state.get("root") != registry.REGISTRY_DIR_NAME
        or state.get("replay_forbidden") is not True
        or state.get("append_only") is not True
        or state.get("hash_chained") is not True
        or state.get("restart_durable") is not True
        or registry.registry_root(ROOT) != REGISTRY_ACTIVATION.parent
        or len(activation_payload) != REGISTRY_ACTIVATION_SIZE
        or hashlib.sha256(activation_payload).hexdigest()
        != REGISTRY_ACTIVATION_SHA256
        or not isinstance(legacy_candidates, list)
    ):
        raise P0F1Error("P0 global candidate registry authority differs")
    if any(
        isinstance(item, dict)
        and item.get("candidate_ap_sha256") == CANDIDATE_AP_SHA256
        for item in legacy_candidates
    ):
        raise P0F1Error("P0 candidate predates the global registry")
    return {
        "source": source,
        "activation": activation,
        "root": registry.REGISTRY_DIR_NAME,
        "validated_append_only_hash_chain": True,
        "p0_candidate_absent_from_pinned_legacy_activation": True,
    }


def _registry_identity(run_id: str, binding_sha256: str) -> dict[str, Any]:
    profile = {
        "schema": "s20plus_g986n_p0_registry_profile_v1",
        "target": dict(engine.TARGET),
    }
    manifest = {
        "manifest_id": "s20plus-g986n-p0-pid1-acm-v2",
        "run_id": run_id,
        "allowed_member": "boot.img.lz4",
        "candidate_ap": {
            "size": CANDIDATE_AP_SIZE,
            "sha256": CANDIDATE_AP_SHA256,
        },
    }
    receipt = {
        "size": CANDIDATE_AP_SIZE,
        "sha256": CANDIDATE_AP_SHA256,
        "member": {
            "name": "boot.img.lz4",
            "size": CANDIDATE_MEMBER_SIZE,
            "sha256": CANDIDATE_MEMBER_SHA256,
        },
    }
    try:
        return registry.derive_candidate_identity(
            profile,
            manifest,
            CANDIDATE_AP_SHA256,
            approval_binding_sha256=binding_sha256,
            candidate_receipt=receipt,
        )
    except registry.RegistryError as exc:
        raise P0F1Error("P0 global candidate identity is invalid") from exc


def _actual_registry_identity(run_dir: Path, binding_sha256: str) -> dict[str, Any]:
    run_dir = run_dir.absolute()
    if (
        run_dir.parent != RUN_ROOT
        or run_dir.is_symlink()
        or not run_dir.is_dir()
        or run_dir.resolve(strict=True) != run_dir
    ):
        raise P0F1Error("P0 registry run directory is indirect")
    return _registry_identity(run_dir.name, binding_sha256)


def _validate_existing_private_roots() -> None:
    for path, label in (
        (RUN_ROOT, "P0 run root"),
        (CLAIM_ROOT, "P0 local claim root"),
    ):
        try:
            metadata = path.lstat()
        except OSError as exc:
            raise P0F1Error(f"{label} is absent during H0 validation") from exc
        if (
            path.is_symlink()
            or not stat.S_ISDIR(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o700
            or path.resolve(strict=True) != path.absolute()
        ):
            raise P0F1Error(f"{label} is indirect or has the wrong mode")


def _make_private_roots_owner(original):
    def guarded() -> None:
        if _host_validation_active():
            _registry_authority()
            _validate_existing_private_roots()
            return
        require_active()
        transaction = _require_live_transaction()
        try:
            _registry_authority()
        except P0F1Error:
            run_dir_value = transaction.get("run_dir")
            if not isinstance(run_dir_value, str):
                raise
            _allow_degraded_registry_recovery(Path(run_dir_value))
        original()

    return guarded


ensure_private_roots = _make_private_roots_owner(engine.ensure_private_roots)
del _make_private_roots_owner


def candidate_claim_present() -> bool:
    require_active()
    transaction = _require_live_transaction()
    run_dir_value = transaction.get("run_dir")
    if isinstance(run_dir_value, str):
        run_dir = Path(run_dir_value)
        if os.path.lexists(run_dir / P0_REGISTRY_INTENT_NAME):
            _allow_degraded_registry_recovery(run_dir)
            return True
    _registry_authority()
    identity = _registry_identity("p0-preflight-only", "0" * 64)
    try:
        return registry.active_claim(ROOT, identity["candidate_key"]) is not None
    except registry.RegistryError as exc:
        raise P0F1Error("P0 global candidate preflight failed closed") from exc


def _registry_intent(
    run_dir: Path, binding_sha256: str, identity: dict[str, Any]
) -> dict[str, Any]:
    require_active()
    _require_live_transaction()
    path = run_dir / P0_REGISTRY_INTENT_NAME
    if os.path.lexists(path):
        value = engine.read_json(path, "P0 global candidate claim intent")
    else:
        value = {
            "schema": P0_REGISTRY_INTENT_SCHEMA,
            "version": VERSION,
            "binding_sha256": binding_sha256,
            "candidate_identity": identity,
            "candidate_replay_permitted": False,
            "at": engine.utc_now(),
        }
        engine.durable_json(path, value)
    if (
        type(value) is not dict
        or set(value)
        != {
            "schema",
            "version",
            "binding_sha256",
            "candidate_identity",
            "candidate_replay_permitted",
            "at",
        }
        or value.get("schema") != P0_REGISTRY_INTENT_SCHEMA
        or value.get("version") != VERSION
        or value.get("binding_sha256") != binding_sha256
        or value.get("candidate_identity") != identity
        or value.get("candidate_replay_permitted") is not False
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise P0F1Error("P0 global candidate claim intent differs")
    return value


_REGISTRY_IDENTITY_FIELDS = (
    "candidate_key",
    "target_profile_sha256",
    "target_key",
    "candidate_ap_sha256",
    "candidate_ap_size",
    "boot_member_name",
    "boot_member_size",
    "boot_member_sha256",
    "manifest_id",
    "run_id",
    "approval_binding_sha256",
)


def _validate_claim_record(
    record: Any, identity: dict[str, Any], *, event: str
) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise P0F1Error(f"P0 global registry {event} record is absent")
    try:
        registry._validate_record(
            record,
            sequence=record.get("sequence"),
            previous=record.get("previous_record_sha256"),
        )
    except registry.RegistryError as exc:
        raise P0F1Error(f"P0 global registry {event} record is malformed") from exc
    if (
        record.get("event") != event
        or any(
            record.get(name) != identity[name]
            for name in _REGISTRY_IDENTITY_FIELDS
        )
        or HEX64_RE.fullmatch(str(record.get("claim_id"))) is None
    ):
        raise P0F1Error(f"P0 global registry {event} owner differs")
    return record


def _validate_local_registry_receipt(
    run_dir: Path, binding_sha256: str, identity: dict[str, Any]
) -> dict[str, Any]:
    value = engine.read_json(
        run_dir / P0_REGISTRY_RECEIPT_NAME, "P0 global candidate claim receipt"
    )
    if (
        type(value) is not dict
        or set(value)
        != {
            "schema",
            "version",
            "binding_sha256",
            "candidate_identity",
            "active_record",
            "candidate_replay_permitted",
        }
        or value.get("schema") != P0_REGISTRY_RECEIPT_SCHEMA
        or value.get("version") != VERSION
        or value.get("binding_sha256") != binding_sha256
        or value.get("candidate_identity") != identity
        or value.get("candidate_replay_permitted") is not False
    ):
        raise P0F1Error("P0 local global-claim receipt differs")
    _validate_claim_record(value.get("active_record"), identity, event="claim")
    return value


def _registry_uncertain(
    run_dir: Path, binding_sha256: str, identity: dict[str, Any]
) -> dict[str, Any]:
    intent = _registry_intent(run_dir, binding_sha256, identity)
    expected_static = {
        "schema": P0_REGISTRY_UNCERTAIN_SCHEMA,
        "version": VERSION,
        "binding_sha256": binding_sha256,
        "candidate_identity": identity,
        "claim_intent_sha256": engine.digest(intent),
        "registry_state": "unavailable-after-claim-intent",
        "consumed_uncertain": True,
        "candidate_replay_permitted": False,
    }
    path = run_dir / P0_REGISTRY_UNCERTAIN_NAME
    if os.path.lexists(path):
        value = engine.read_json(path, "P0 unavailable-registry receipt")
    else:
        value = {**expected_static, "at": engine.utc_now()}
        engine.durable_json(path, value)
    if (
        type(value) is not dict
        or set(value) != set(expected_static) | {"at"}
        or any(value.get(name) != item for name, item in expected_static.items())
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise P0F1Error("P0 unavailable-registry receipt differs")
    return value


def _minimal_prepared_identity(run_dir: Path) -> tuple[str, dict[str, Any]]:
    value = engine.read_json(run_dir / "prepared.json", "P0 prepared recovery binding")
    binding_sha256 = value.get("binding_sha256")
    binding = value.get("binding")
    if (
        HEX64_RE.fullmatch(str(binding_sha256)) is None
        or not isinstance(binding, dict)
        or engine.digest(binding) != binding_sha256
        or binding.get("run_dir") != str(run_dir)
        or binding.get("target") != engine.TARGET
    ):
        raise P0F1Error("P0 degraded recovery binding differs")
    return binding_sha256, _registry_identity(run_dir.name, binding_sha256)


def _allow_degraded_registry_recovery(run_dir: Path) -> None:
    transaction = _require_live_transaction()
    if transaction.get("run_dir") != str(run_dir):
        raise P0F1Error("P0 degraded recovery escaped its leased run")
    if (
        run_dir.parent != RUN_ROOT
        or run_dir.is_symlink()
        or not run_dir.is_dir()
        or run_dir.resolve(strict=True) != run_dir
    ):
        raise P0F1Error("P0 degraded recovery run is indirect")
    engine.require_guard(run_dir)
    binding_sha256, identity = _minimal_prepared_identity(run_dir)
    if not os.path.lexists(run_dir / P0_REGISTRY_INTENT_NAME):
        raise P0F1Error("P0 registry failed before the candidate-claim boundary")
    _registry_intent(run_dir, binding_sha256, identity)
    receipt_path = run_dir / P0_REGISTRY_RECEIPT_NAME
    uncertain_path = run_dir / P0_REGISTRY_UNCERTAIN_NAME
    receipt_present = os.path.lexists(receipt_path)
    uncertain_present = os.path.lexists(uncertain_path)
    if receipt_present and uncertain_present:
        raise P0F1Error("P0 global claim has contradictory receipt states")
    if receipt_present:
        _validate_local_registry_receipt(run_dir, binding_sha256, identity)
    elif uncertain_present:
        _registry_uncertain(run_dir, binding_sha256, identity)
    else:
        _registry_uncertain(run_dir, binding_sha256, identity)


def _active_registry_record(identity: dict[str, Any]) -> dict[str, Any]:
    try:
        active = registry.active_claim(ROOT, identity["candidate_key"])
    except registry.RegistryError as exc:
        raise P0F1Error("P0 global candidate claim cannot be reopened") from exc
    if active is None or any(
        active.get(name) != identity[name] for name in _REGISTRY_IDENTITY_FIELDS
    ):
        raise P0F1Error("P0 global candidate claim belongs to another run")
    return active


def _registry_receipt(
    run_dir: Path, binding_sha256: str, identity: dict[str, Any]
) -> dict[str, Any]:
    require_active()
    _require_live_transaction()
    path = run_dir / P0_REGISTRY_RECEIPT_NAME
    if os.path.lexists(path):
        return _validate_local_registry_receipt(run_dir, binding_sha256, identity)
    active = _active_registry_record(identity)
    expected = {
        "schema": P0_REGISTRY_RECEIPT_SCHEMA,
        "version": VERSION,
        "binding_sha256": binding_sha256,
        "candidate_identity": identity,
        "active_record": active,
        "candidate_replay_permitted": False,
    }
    engine.durable_json(path, expected)
    return _validate_local_registry_receipt(run_dir, binding_sha256, identity)


def _claim_global_registry(
    run_dir: Path, binding_sha256: str, identity: dict[str, Any]
) -> dict[str, Any]:
    require_active()
    _require_live_transaction()
    _registry_intent(run_dir, binding_sha256, identity)
    try:
        active = registry.active_claim(ROOT, identity["candidate_key"])
        if active is None:
            registry.claim(ROOT, identity)
        elif any(
            active.get(name) != identity[name] for name in _REGISTRY_IDENTITY_FIELDS
        ):
            raise P0F1Error("P0 candidate is already claimed by another run")
    except registry.DuplicateCandidateClaim as exc:
        raise P0F1Error("P0 candidate is already globally consumed") from exc
    except registry.RegistryError as exc:
        raise P0F1Error("P0 global candidate claim failed closed") from exc
    return _registry_receipt(run_dir, binding_sha256, identity)


def _local_parse_result(run_dir: Path, binding_sha256: str) -> dict[str, Any] | None:
    path = run_dir / "candidate-result.json"
    if not os.path.lexists(path):
        return None
    value = engine.read_json(path, "P0 candidate transfer result")
    if value.get("classification") != "odin_local_parse_failure":
        return None
    _ENGINE_VALIDATE_TRANSFER_OUTCOME(
        run_dir, value, "candidate", binding_sha256
    )
    if "receipt" not in value or value.get("host_process_quiescence_proved") is not True:
        raise P0F1Error("P0 local-parse release lacks raw quiescent proof")
    return value


def _registry_release_intent(
    run_dir: Path,
    binding_sha256: str,
    identity: dict[str, Any],
    claim_record: dict[str, Any],
) -> dict[str, Any]:
    expected_static = {
        "schema": P0_REGISTRY_RELEASE_INTENT_SCHEMA,
        "version": VERSION,
        "binding_sha256": binding_sha256,
        "candidate_identity": identity,
        "claim_id": claim_record["claim_id"],
        "claim_record_sha256": claim_record["record_sha256"],
        "release_reason": "odin_local_parse_failure",
        "device_session_started": False,
        "partition_transfer": False,
        "candidate_replay_permitted": False,
    }
    path = run_dir / P0_REGISTRY_RELEASE_INTENT_NAME
    if os.path.lexists(path):
        value = engine.read_json(path, "P0 global release intent")
    else:
        value = {**expected_static, "at": engine.utc_now()}
        engine.durable_json(path, value)
    if (
        type(value) is not dict
        or set(value) != set(expected_static) | {"at"}
        or any(value.get(name) != item for name, item in expected_static.items())
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise P0F1Error("P0 global release intent differs")
    return value


def _validate_registry_release_receipt(
    run_dir: Path,
    binding_sha256: str,
    identity: dict[str, Any],
    claim_record: dict[str, Any],
) -> dict[str, Any]:
    value = engine.read_json(
        run_dir / P0_REGISTRY_RELEASE_RECEIPT_NAME,
        "P0 global release receipt",
    )
    release_record = value.get("release_record") if isinstance(value, dict) else None
    if (
        type(value) is not dict
        or set(value)
        != {
            "schema",
            "version",
            "binding_sha256",
            "candidate_identity",
            "claim_id",
            "claim_record_sha256",
            "release_record",
            "candidate_replay_permitted_for_this_run",
        }
        or value.get("schema") != P0_REGISTRY_RELEASE_RECEIPT_SCHEMA
        or value.get("version") != VERSION
        or value.get("binding_sha256") != binding_sha256
        or value.get("candidate_identity") != identity
        or value.get("claim_id") != claim_record["claim_id"]
        or value.get("claim_record_sha256") != claim_record["record_sha256"]
        or value.get("candidate_replay_permitted_for_this_run") is not False
    ):
        raise P0F1Error("P0 global release receipt differs")
    _validate_claim_record(release_record, identity, event="release")
    if release_record.get("claim_id") != claim_record["claim_id"]:
        raise P0F1Error("P0 global release claim owner differs")
    return value


def _local_claim_value(run_dir: Path, binding_sha256: str) -> dict[str, Any]:
    intent_path = run_dir / "candidate-claim-intent.json"
    if not os.path.lexists(intent_path):
        raise P0F1Error("P0 local recovery projection lacks its intent")
    _intent, claim = _ENGINE_CANDIDATE_CLAIM_INTENT(run_dir, binding_sha256)
    return claim


def _remove_local_recovery_projection(
    run_dir: Path,
    binding_sha256: str,
    release_receipt: dict[str, Any],
) -> dict[str, Any]:
    expected_claim = _local_claim_value(run_dir, binding_sha256)
    expected_static = {
        "schema": P0_LOCAL_PROJECTION_RELEASE_SCHEMA,
        "version": VERSION,
        "binding_sha256": binding_sha256,
        "projection_name": engine.claim_path().name,
        "projection_sha256": hashlib.sha256(
            engine.canonical_bytes(expected_claim)
        ).hexdigest(),
        "global_release_record_sha256": release_receipt["release_record"][
            "record_sha256"
        ],
        "projection_absent": True,
        "candidate_replay_permitted_for_this_run": False,
    }
    result_path = run_dir / P0_LOCAL_PROJECTION_RELEASE_NAME
    if os.path.lexists(result_path):
        value = engine.read_json(result_path, "P0 local projection release")
        if (
            type(value) is not dict
            or set(value) != set(expected_static) | {"at"}
            or any(value.get(name) != item for name, item in expected_static.items())
            or os.path.lexists(engine.claim_path())
        ):
            raise P0F1Error("P0 local projection release differs")
        return value
    parent_fd = _ENGINE_OPEN_DIRECT_DIRECTORY(CLAIM_ROOT)
    try:
        try:
            descriptor = os.open(
                engine.claim_path().name,
                os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=parent_fd,
            )
        except FileNotFoundError:
            descriptor = None
        if descriptor is not None:
            try:
                metadata = os.fstat(descriptor)
                payload = os.read(descriptor, metadata.st_size + 1)
                if (
                    not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_nlink != 1
                    or stat.S_IMODE(metadata.st_mode) != 0o400
                    or payload != engine.canonical_bytes(expected_claim)
                ):
                    raise P0F1Error("P0 local recovery projection differs")
            finally:
                os.close(descriptor)
            os.unlink(engine.claim_path().name, dir_fd=parent_fd)
            os.fsync(parent_fd)
    finally:
        os.close(parent_fd)
    value = {**expected_static, "at": engine.utc_now()}
    engine.durable_json(result_path, value)
    return value


def _release_global_claim_after_local_parse(
    run_dir: Path, binding_sha256: str, identity: dict[str, Any]
) -> bool:
    require_active()
    _require_live_transaction()
    if _local_parse_result(run_dir, binding_sha256) is None:
        return False
    local_receipt = _validate_local_registry_receipt(
        run_dir, binding_sha256, identity
    )
    claim_record = local_receipt["active_record"]
    _registry_release_intent(run_dir, binding_sha256, identity, claim_record)
    receipt_path = run_dir / P0_REGISTRY_RELEASE_RECEIPT_NAME
    if os.path.lexists(receipt_path):
        release_receipt = _validate_registry_release_receipt(
            run_dir, binding_sha256, identity, claim_record
        )
    else:
        claim_value = {
            "candidate_key": identity["candidate_key"],
            "claim_id": claim_record["claim_id"],
            "record": claim_record,
        }
        try:
            released = registry.release(
                ROOT,
                claim_value,
                release_reason="odin_local_parse_failure",
                device_session_started=False,
                partition_transfer=False,
            )
        except registry.RegistryError:
            return False
        release_record = _validate_claim_record(
            released.get("record"), identity, event="release"
        )
        release_receipt = {
            "schema": P0_REGISTRY_RELEASE_RECEIPT_SCHEMA,
            "version": VERSION,
            "binding_sha256": binding_sha256,
            "candidate_identity": identity,
            "claim_id": claim_record["claim_id"],
            "claim_record_sha256": claim_record["record_sha256"],
            "release_record": release_record,
            "candidate_replay_permitted_for_this_run": False,
        }
        engine.durable_json(receipt_path, release_receipt)
        release_receipt = _validate_registry_release_receipt(
            run_dir, binding_sha256, identity, claim_record
        )
    _remove_local_recovery_projection(run_dir, binding_sha256, release_receipt)
    return True


def _cage_node(kind: str, generation: int, suffix: str) -> Path:
    if (
        kind not in CAGE_KINDS
        or type(generation) is not int
        or not 1 <= generation <= CAGE_GENERATION_MAXIMUM
        or suffix not in {"prepare", "bound", "reconciled"}
    ):
        raise P0F1Error("P0 process-cage node identity differs")
    return Path(f"p0-{kind}-cage-{generation:04d}-{suffix}.json")


def _cage_generations(run_dir: Path, kind: str) -> dict[int, set[str]]:
    found: dict[int, set[str]] = {}
    for entry in os.scandir(run_dir):
        match = CAGE_NODE_RE.fullmatch(entry.name)
        if match is None or match.group(1) != kind:
            continue
        generation = int(match.group(2))
        if not 1 <= generation <= CAGE_GENERATION_MAXIMUM:
            raise P0F1Error("P0 process-cage generation exceeds its bound")
        found.setdefault(generation, set()).add(match.group(3))
    if found and sorted(found) != list(range(1, max(found) + 1)):
        raise P0F1Error("P0 process-cage generations are not contiguous")
    if any("prepare" not in suffixes for suffixes in found.values()):
        raise P0F1Error("P0 process-cage generation lacks prepare intent")
    return found


def _validate_cage_prepare(
    run_dir: Path,
    kind: str,
    generation: int,
    binding_sha256: str | None = None,
) -> dict[str, Any]:
    value = engine.read_json(
        run_dir / _cage_node(kind, generation, "prepare"),
        f"P0 {kind} cage prepare",
    )
    parent = Path(str(value.get("parent", ""))) if isinstance(value, dict) else Path()
    stored_binding = value.get("binding_sha256") if isinstance(value, dict) else None
    expected_cage = parent / (
        f"s20plus-p0-{kind}-{str(stored_binding)[:12]}-g{generation:04d}"
    )
    if (
        type(value) is not dict
        or set(value)
        != {
            "schema",
            "version",
            "kind",
            "generation",
            "binding_sha256",
            "parent",
            "parent_identity",
            "cage",
            "host_boot_id_sha256",
            "backend_invoked",
            "candidate_replay_permitted",
            "at",
        }
        or value.get("schema") != P0_CAGE_PREPARE_SCHEMA
        or value.get("version") != VERSION
        or value.get("kind") != kind
        or value.get("generation") != generation
        or HEX64_RE.fullmatch(str(stored_binding)) is None
        or (binding_sha256 is not None and stored_binding != binding_sha256)
        or not parent.is_absolute()
        or parent.parts[:4] != ("/", "sys", "fs", "cgroup")
        or ".." in parent.parts
        or value.get("cage") != str(expected_cage)
        or not isinstance(value.get("parent_identity"), list)
        or len(value["parent_identity"]) != 5
        or any(type(item) is not int for item in value["parent_identity"])
        or HEX64_RE.fullmatch(str(value.get("host_boot_id_sha256"))) is None
        or value.get("backend_invoked") is not False
        or value.get("candidate_replay_permitted") is not False
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise P0F1Error("P0 process-cage prepare intent differs")
    return value


def _validate_cage_bound(
    run_dir: Path,
    kind: str,
    generation: int,
    prepare: dict[str, Any],
) -> dict[str, Any]:
    binding_sha256 = prepare["binding_sha256"]
    value = engine.read_json(
        run_dir / _cage_node(kind, generation, "bound"),
        f"P0 {kind} cage bound",
    )
    bound = value.get("process_cage") if isinstance(value, dict) else None
    if (
        type(value) is not dict
        or set(value)
        != {
            "schema",
            "version",
            "kind",
            "generation",
            "binding_sha256",
            "prepare_sha256",
            "process_cage",
            "backend_invoked",
            "candidate_replay_permitted",
        }
        or value.get("schema") != P0_CAGE_BOUND_SCHEMA
        or value.get("version") != VERSION
        or value.get("kind") != kind
        or value.get("generation") != generation
        or value.get("binding_sha256") != binding_sha256
        or value.get("prepare_sha256") != engine.digest(prepare)
        or not isinstance(bound, dict)
        or set(bound)
        != {
            "schema",
            "version",
            "kind",
            "binding_sha256",
            "parent",
            "parent_identity",
            "cage",
            "host_boot_id_sha256",
            "cage_identity",
            "empty_before_backend",
            "at",
        }
        or bound.get("schema") != "s20plus_g986n_b0_process_cage_binding_v1"
        or bound.get("version") != VERSION
        or bound.get("parent") != prepare["parent"]
        or bound.get("parent_identity") != prepare["parent_identity"]
        or bound.get("cage") != prepare["cage"]
        or bound.get("host_boot_id_sha256") != prepare["host_boot_id_sha256"]
        or bound.get("binding_sha256") != binding_sha256
        or bound.get("kind") != kind
        or not isinstance(bound.get("cage_identity"), list)
        or len(bound["cage_identity"]) != 5
        or any(type(item) is not int for item in bound["cage_identity"])
        or bound.get("empty_before_backend") is not True
        or not isinstance(bound.get("at"), str)
        or not bound["at"]
        or value.get("backend_invoked") is not False
        or value.get("candidate_replay_permitted") is not False
    ):
        raise P0F1Error("P0 process-cage bound receipt differs")
    return value


def _validate_p0_engine_cage_binding(
    value: Any, kind: str, binding_sha256: str
) -> dict[str, Any]:
    if kind not in {"candidate", "rollback", "abort-return"}:
        raise P0F1Error("P0 inherited process-cage kind differs")
    if not isinstance(value, dict):
        raise P0F1Error(f"{kind} P0 process-cage binding is absent")
    parent = Path(str(value.get("parent", "")))
    cage = Path(str(value.get("cage", "")))
    name_match = re.fullmatch(
        rf"s20plus-p0-{re.escape(kind)}-{re.escape(binding_sha256[:12])}-g([0-9]{{4}})",
        cage.name,
    )
    generation = int(name_match.group(1)) if name_match is not None else 0
    if (
        set(value)
        != {
            "schema",
            "version",
            "kind",
            "binding_sha256",
            "parent",
            "parent_identity",
            "cage",
            "host_boot_id_sha256",
            "cage_identity",
            "empty_before_backend",
            "at",
        }
        or value.get("schema") != "s20plus_g986n_b0_process_cage_binding_v1"
        or value.get("version") != VERSION
        or value.get("kind") != kind
        or value.get("binding_sha256") != binding_sha256
        or not parent.is_absolute()
        or parent.parts[:4] != ("/", "sys", "fs", "cgroup")
        or ".." in parent.parts
        or cage.parent != parent
        or name_match is None
        or not 1 <= generation <= CAGE_GENERATION_MAXIMUM
        or not isinstance(value.get("parent_identity"), list)
        or len(value["parent_identity"]) != 5
        or any(type(item) is not int for item in value["parent_identity"])
        or not isinstance(value.get("cage_identity"), list)
        or len(value["cage_identity"]) != 5
        or any(type(item) is not int for item in value["cage_identity"])
        or HEX64_RE.fullmatch(str(value.get("host_boot_id_sha256"))) is None
        or value.get("empty_before_backend") is not True
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise P0F1Error(f"{kind} P0 process-cage binding is malformed")
    return value


def _validate_p0_engine_cage_quiescence(
    run_dir: Path,
    actual: set[str],
    kind: str,
    binding_sha256: str,
    cage_binding: dict[str, Any],
) -> dict[str, Any] | None:
    name = f"{kind}-cage-quiescent.json"
    if name not in actual:
        return None
    cage_binding = _validate_p0_engine_cage_binding(
        cage_binding, kind, binding_sha256
    )
    value = engine.read_json(run_dir / name, f"{kind} P0 process-cage quiescence")
    if (
        set(value)
        != {
            "schema",
            "version",
            "kind",
            "binding_sha256",
            "cage_binding_sha256",
            "kill_requested",
            "cage_absent_before_check",
            "empty_and_removed",
            "at",
        }
        or value.get("schema") != "s20plus_g986n_b0_process_cage_quiescent_v1"
        or value.get("version") != VERSION
        or value.get("kind") != kind
        or value.get("binding_sha256") != binding_sha256
        or value.get("cage_binding_sha256") != engine.digest(cage_binding)
        or type(value.get("kill_requested")) is not bool
        or type(value.get("cage_absent_before_check")) is not bool
        or value.get("empty_and_removed") is not True
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise P0F1Error(f"{kind} P0 process-cage quiescence is malformed")
    matches = 0
    for generation, suffixes in _cage_generations(run_dir, kind).items():
        if "bound" not in suffixes:
            continue
        prepare = _validate_cage_prepare(
            run_dir, kind, generation, binding_sha256
        )
        bound = _validate_cage_bound(
            run_dir, kind, generation, prepare
        )["process_cage"]
        if bound == cage_binding:
            matches += 1
    if matches != 1:
        raise P0F1Error(f"{kind} inherited quiescence lacks one P0 cage generation")
    return value


def _validate_cage_reconciled(
    run_dir: Path,
    kind: str,
    generation: int,
    prepare: dict[str, Any],
) -> dict[str, Any]:
    value = engine.read_json(
        run_dir / _cage_node(kind, generation, "reconciled"),
        f"P0 {kind} cage reconciliation",
    )
    if (
        type(value) is not dict
        or set(value)
        != {
            "schema",
            "version",
            "kind",
            "generation",
            "binding_sha256",
            "prepare_sha256",
            "cage_removed",
            "cage_absent",
            "backend_replayed",
            "candidate_replay_permitted",
            "at",
        }
        or value.get("schema") != P0_CAGE_RECONCILED_SCHEMA
        or value.get("version") != VERSION
        or value.get("kind") != kind
        or value.get("generation") != generation
        or value.get("binding_sha256") != prepare["binding_sha256"]
        or value.get("prepare_sha256") != engine.digest(prepare)
        or type(value.get("cage_removed")) is not bool
        or value.get("cage_absent") is not True
        or value.get("backend_replayed") is not False
        or value.get("candidate_replay_permitted") is not False
        or not isinstance(value.get("at"), str)
        or os.path.lexists(Path(prepare["cage"]))
    ):
        raise P0F1Error("P0 process-cage reconciliation differs")
    return value


def _prepare_p0_process_cage(
    run_dir: Path, kind: str, binding_sha256: str
) -> tuple[Path, dict[str, Any]]:
    require_active()
    transaction = _require_live_transaction()
    if transaction.get("run_dir") != str(run_dir):
        raise P0F1Error("P0 process-cage allocation escaped its leased run")
    if kind not in CAGE_KINDS or HEX64_RE.fullmatch(binding_sha256) is None:
        raise P0F1Error("P0 process-cage allocation identity differs")
    generations = _cage_generations(run_dir, kind)
    for generation, suffixes in generations.items():
        prepare = _validate_cage_prepare(run_dir, kind, generation)
        if "reconciled" not in suffixes:
            raise P0F1Error("P0 previous process-cage generation is unresolved")
        _validate_cage_reconciled(run_dir, kind, generation, prepare)
    generation = len(generations) + 1
    if generation > CAGE_GENERATION_MAXIMUM:
        raise P0F1Error("P0 process-cage recovery generation bound exhausted")
    parent = engine._current_cgroup_parent()
    parent_identity = engine._cgroup_identity(parent)
    cage = parent / f"s20plus-p0-{kind}-{binding_sha256[:12]}-g{generation:04d}"
    if os.path.lexists(cage):
        raise P0F1Error("P0 unjournaled process-cage path already exists")
    prepare = {
        "schema": P0_CAGE_PREPARE_SCHEMA,
        "version": VERSION,
        "kind": kind,
        "generation": generation,
        "binding_sha256": binding_sha256,
        "parent": str(parent),
        "parent_identity": parent_identity,
        "cage": str(cage),
        "host_boot_id_sha256": hashlib.sha256(
            engine._host_boot_id().encode()
        ).hexdigest(),
        "backend_invoked": False,
        "candidate_replay_permitted": False,
        "at": engine.utc_now(),
    }
    engine.durable_json(
        run_dir / _cage_node(kind, generation, "prepare"), prepare
    )
    try:
        os.mkdir(cage, 0o700)
    except OSError as exc:
        raise P0F1Error("P0 process-cage creation failed") from exc
    if engine._cgroup_identity(parent) != parent_identity or engine._cgroup_populated(cage):
        raise P0F1Error("P0 new process cage or parent differs")
    bound = {
        "schema": "s20plus_g986n_b0_process_cage_binding_v1",
        "version": VERSION,
        "kind": kind,
        "binding_sha256": binding_sha256,
        "parent": str(parent),
        "parent_identity": parent_identity,
        "cage": str(cage),
        "host_boot_id_sha256": prepare["host_boot_id_sha256"],
        "cage_identity": engine._cgroup_identity(cage),
        "empty_before_backend": True,
        "at": engine.utc_now(),
    }
    value = {
        "schema": P0_CAGE_BOUND_SCHEMA,
        "version": VERSION,
        "kind": kind,
        "generation": generation,
        "binding_sha256": binding_sha256,
        "prepare_sha256": engine.digest(prepare),
        "process_cage": bound,
        "backend_invoked": False,
        "candidate_replay_permitted": False,
    }
    engine.durable_json(run_dir / _cage_node(kind, generation, "bound"), value)
    _validate_cage_bound(run_dir, kind, generation, prepare)
    return cage, bound


_P0_PREPARE_PROCESS_CAGE = _prepare_p0_process_cage


def _effect_intent_name(kind: str, generation: int | None = None) -> str | None:
    if kind in {"candidate", "rollback"}:
        return f"{kind}-intent.json"
    if kind == "abort-return":
        return "abort-return-intent.json"
    if kind == "odin-listing":
        if generation is None:
            return None
        return f"p0-odin-listing-{generation:04d}-intent.json"
    return None


def _validate_odin_listing_intent(
    run_dir: Path,
    generation: int,
    prepare: dict[str, Any],
    bound: dict[str, Any],
) -> dict[str, Any]:
    value = engine.read_json(
        run_dir / f"p0-odin-listing-{generation:04d}-intent.json",
        "P0 Odin-listing intent",
    )
    if (
        type(value) is not dict
        or set(value)
        != {
            "schema",
            "version",
            "generation",
            "binding_sha256",
            "process_cage",
            "command_shape",
            "no_payload",
            "attempt",
            "no_replay",
            "at",
        }
        or value.get("schema") != "s20plus_g986n_p0_odin_listing_intent_v1"
        or value.get("version") != VERSION
        or value.get("generation") != generation
        or value.get("binding_sha256") != prepare["binding_sha256"]
        or value.get("process_cage") != bound
        or value.get("command_shape") != ["odin4", "-l"]
        or value.get("no_payload") is not True
        or value.get("attempt") != 1
        or value.get("no_replay") is not True
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise P0F1Error("P0 Odin-listing intent differs")
    return value


def _validate_odin_listing_result(
    run_dir: Path,
    generation: int,
    prepare: dict[str, Any],
    intent: dict[str, Any],
) -> dict[str, Any]:
    value = engine.read_json(
        run_dir / f"p0-odin-listing-{generation:04d}-result.json",
        "P0 Odin-listing result",
    )
    handle = engine.raw_capture.load_handle(
        run_dir / f"p0-odin-listing-{generation:04d}.capture.json"
    )
    stdout = engine.raw_capture.read_stdout(
        handle, maximum=engine.MAX_ADB_BYTES
    )
    stderr = engine.raw_capture.read_stderr(
        handle, maximum=engine.MAX_ADB_BYTES
    )
    listing = (
        stdout[len(engine.ODIN_CAGE_ENTRY_MARKER) :]
        if stdout.startswith(engine.ODIN_CAGE_ENTRY_MARKER)
        else b""
    )
    if (
        type(value) is not dict
        or set(value)
        != {
            "schema",
            "version",
            "generation",
            "binding_sha256",
            "intent_sha256",
            "returncode",
            "stdout_sha256",
            "stderr_sha256",
            "listing_sha256",
            "bounded_no_payload_dispatch",
            "same_invocation_replay_permitted",
            "at",
        }
        or value.get("schema") != "s20plus_g986n_p0_odin_listing_result_v1"
        or value.get("version") != VERSION
        or value.get("generation") != generation
        or value.get("binding_sha256") != prepare["binding_sha256"]
        or value.get("intent_sha256") != engine.digest(intent)
        or value.get("returncode") != handle.returncode
        or value.get("stdout_sha256") != hashlib.sha256(stdout).hexdigest()
        or value.get("stderr_sha256") != hashlib.sha256(stderr).hexdigest()
        or value.get("listing_sha256") != hashlib.sha256(listing).hexdigest()
        or value.get("bounded_no_payload_dispatch") is not True
        or value.get("same_invocation_replay_permitted") is not False
        or not engine.raw_dispatch_proved(handle, stderr)
        or not stdout.startswith(engine.ODIN_CAGE_ENTRY_MARKER)
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise P0F1Error("P0 Odin-listing result is not raw-derived")
    return value


def _effect_matches_cage(
    kind: str,
    effect: Any,
    prepare: dict[str, Any],
    bound: dict[str, Any] | None,
) -> bool:
    if not isinstance(effect, dict) or not isinstance(bound, dict):
        return False
    expected_binding = (
        effect.get("cage_binding_sha256")
        if kind == "abort-return"
        else effect.get("binding_sha256")
    )
    return (
        expected_binding == prepare["binding_sha256"]
        and effect.get("process_cage") == bound
    )


def _reconcile_orphan_process_cages(run_dir: Path) -> None:
    require_active()
    transaction = _require_live_transaction()
    if transaction.get("run_dir") != str(run_dir):
        raise P0F1Error("P0 cage recovery escaped its leased run")
    if not run_dir.is_dir() or run_dir.is_symlink() or run_dir.parent != RUN_ROOT:
        raise P0F1Error("P0 cage recovery run is indirect")
    engine.require_guard(run_dir)
    prepared_binding = None
    if os.path.lexists(run_dir / "prepared.json"):
        prepared_binding, _identity = _minimal_prepared_identity(run_dir)
    for kind in CAGE_KINDS:
        persistent_effect = None
        if kind != "odin-listing":
            persistent_name = _effect_intent_name(kind)
            if persistent_name is not None and os.path.lexists(
                run_dir / persistent_name
            ):
                persistent_effect = engine.read_json(
                    run_dir / persistent_name, f"P0 {kind} effect"
                )
        matched_effect_cages = 0
        for generation, suffixes in _cage_generations(run_dir, kind).items():
            effect = persistent_effect
            if kind == "odin-listing":
                effect_name = _effect_intent_name(kind, generation)
                effect = (
                    engine.read_json(run_dir / effect_name, f"P0 {kind} effect")
                    if effect_name is not None
                    and os.path.lexists(run_dir / effect_name)
                    else None
                )
            expected_binding = (
                prepared_binding if kind in {"candidate", "rollback"} else None
            )
            prepare = _validate_cage_prepare(
                run_dir, kind, generation, expected_binding
            )
            reconciled_path = run_dir / _cage_node(kind, generation, "reconciled")
            cage = Path(prepare["cage"])
            bound = None
            if "bound" in suffixes:
                bound = _validate_cage_bound(
                    run_dir, kind, generation, prepare
                )["process_cage"]
            effect_match = _effect_matches_cage(kind, effect, prepare, bound)
            if effect_match:
                matched_effect_cages += 1
            if "reconciled" in suffixes:
                _validate_cage_reconciled(run_dir, kind, generation, prepare)
                if kind == "odin-listing":
                    intent_name = _effect_intent_name(kind, generation)
                    result_name = f"p0-odin-listing-{generation:04d}-result.json"
                    result_present = result_name in {
                        entry.name for entry in os.scandir(run_dir)
                    }
                    if isinstance(effect, dict):
                        if bound is None or not effect_match:
                            raise P0F1Error(
                                "P0 reconciled Odin-listing intent differs from its cage"
                            )
                        intent_value = _validate_odin_listing_intent(
                            run_dir, generation, prepare, bound
                        )
                        if result_present:
                            _validate_odin_listing_result(
                                run_dir, generation, prepare, intent_value
                            )
                    elif result_present or (
                        intent_name is not None
                        and os.path.lexists(run_dir / intent_name)
                    ):
                        raise P0F1Error(
                            "P0 Odin-listing result lacks its intent and bound cage"
                        )
                continue
            claim_cut = (
                kind == "candidate"
                and isinstance(effect, dict)
                and effect.get("global_claim_cut") is True
                and effect.get("backend_invoked") is False
            )
            listing_effect = kind == "odin-listing" and isinstance(effect, dict)
            if isinstance(effect, dict) and not claim_cut:
                if not effect_match:
                    raise P0F1Error("P0 effect lacks its process-cage bound receipt")
                if listing_effect:
                    _validate_odin_listing_intent(
                        run_dir, generation, prepare, bound
                    )
                if not listing_effect:
                    continue
            current_boot = hashlib.sha256(engine._host_boot_id().encode()).hexdigest()
            removed = False
            if current_boot != prepare["host_boot_id_sha256"]:
                if os.path.lexists(cage):
                    raise P0F1Error("P0 stale cage path exists after host reboot")
            else:
                parent = Path(prepare["parent"])
                if engine._cgroup_identity(parent) != prepare["parent_identity"]:
                    raise P0F1Error("P0 process-cage parent changed")
                if os.path.lexists(cage):
                    if (
                        bound is not None
                        and engine._cgroup_identity(cage) != bound.get("cage_identity")
                    ):
                        raise P0F1Error("P0 orphan process-cage identity changed")
                    populated = engine._cgroup_populated(cage)
                    if populated and not listing_effect:
                        raise P0F1Error("P0 orphan process cage is populated")
                    if populated:
                        engine._write_host_control(
                            cage / "cgroup.kill",
                            b"1\n",
                            "P0 Odin-listing cage kill",
                        )
                        deadline = time.monotonic() + 10
                        while engine._cgroup_populated(cage):
                            if time.monotonic() >= deadline:
                                raise P0F1Error(
                                    "P0 Odin-listing cage did not become empty"
                                )
                            time.sleep(0.05)
                    os.rmdir(cage)
                    removed = True
            engine.durable_json(
                reconciled_path,
                {
                    "schema": P0_CAGE_RECONCILED_SCHEMA,
                    "version": VERSION,
                    "kind": kind,
                    "generation": generation,
                    "binding_sha256": prepare["binding_sha256"],
                    "prepare_sha256": engine.digest(prepare),
                    "cage_removed": removed,
                    "cage_absent": not os.path.lexists(cage),
                    "backend_replayed": False,
                    "candidate_replay_permitted": False,
                    "at": engine.utc_now(),
                },
            )
        if (
            isinstance(persistent_effect, dict)
            and not (
                kind == "candidate"
                and persistent_effect.get("global_claim_cut") is True
                and persistent_effect.get("backend_invoked") is False
            )
            and matched_effect_cages != 1
        ):
            raise P0F1Error("P0 effect does not bind exactly one cage generation")


def _p0_bounded_odin_listing() -> str:
    require_active()
    transaction = _require_live_transaction()
    run_dir_value = transaction.get("run_dir")
    if not isinstance(run_dir_value, str):
        raise P0F1Error("P0 Odin listing has no leased run")
    run_dir = Path(run_dir_value)
    generations = _cage_generations(run_dir, "odin-listing")
    generation = len(generations) + 1
    binding_sha256 = engine.digest(
        {
            "schema": "s20plus_g986n_p0_odin_listing_binding_v1",
            "run_dir": str(run_dir),
            "generation": generation,
            "target": dict(engine.TARGET),
            "operation": "odin4-list-no-payload",
        }
    )
    cage, bound = _prepare_p0_process_cage(
        run_dir, "odin-listing", binding_sha256
    )
    intent = {
        "schema": "s20plus_g986n_p0_odin_listing_intent_v1",
        "version": VERSION,
        "generation": generation,
        "binding_sha256": binding_sha256,
        "process_cage": bound,
        "command_shape": ["odin4", "-l"],
        "no_payload": True,
        "attempt": 1,
        "no_replay": True,
        "at": engine.utc_now(),
    }
    engine.durable_json(
        run_dir / f"p0-odin-listing-{generation:04d}-intent.json", intent
    )
    handle = None
    try:
        with engine.transport.pin_regular_file(
            engine.ODIN,
            label="Odin4",
            expected_size=engine.ODIN_SIZE,
            expected_sha256=engine.ODIN_SHA256,
        ) as odin, engine.transport.pin_regular_file(
            engine.DASH,
            label="process-cage shell",
            expected_size=engine.DASH_SIZE,
            expected_sha256=engine.DASH_SHA256,
        ) as cage_shell, engine.transport.pin_regular_file(
            engine.CAGE_SLEEP,
            label="Odin listing watchdog",
            expected_size=engine.CAGE_SLEEP_SIZE,
            expected_sha256=engine.CAGE_SLEEP_SHA256,
        ) as watchdog:
            handle = engine.raw_capture.acquire_command(
                [
                    str(cage_shell.path),
                    "-c",
                    engine.ODIN_CAGE_ENTRY_SCRIPT,
                    "s20plus-p0-odin-listing-cage",
                    str(cage),
                    str(watchdog.path),
                    "timeout",
                    "-s",
                    "KILL",
                    "10",
                    str(odin.path),
                    "-l",
                ],
                run_dir,
                f"p0-odin-listing-{generation:04d}",
                timeout=12,
                stdout_maximum=engine.MAX_ADB_BYTES,
                stderr_maximum=engine.MAX_ADB_BYTES,
                env=engine.ODIN_FIXED_ENV,
                stdout_name=f"p0-odin-listing-{generation:04d}.stdout",
                stderr_name=f"p0-odin-listing-{generation:04d}.stderr",
            )
            engine.transport.revalidate_pinned_path(odin)
            engine.transport.revalidate_pinned_path(cage_shell)
            engine.transport.revalidate_pinned_path(watchdog)
    finally:
        _reconcile_orphan_process_cages(run_dir)
    if handle is None:
        raise P0F1Error("P0 Odin listing capture is unavailable")
    stdout = engine.raw_capture.read_stdout(
        handle, maximum=engine.MAX_ADB_BYTES
    )
    stderr = engine.raw_capture.read_stderr(
        handle, maximum=engine.MAX_ADB_BYTES
    )
    if (
        not engine.raw_dispatch_proved(handle, stderr)
        or not stdout.startswith(engine.ODIN_CAGE_ENTRY_MARKER)
    ):
        raise P0F1Error("P0 Odin listing did not prove bounded dispatch")
    listing = stdout[len(engine.ODIN_CAGE_ENTRY_MARKER) :]
    try:
        text = listing.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise P0F1Error("P0 Odin listing output is malformed") from exc
    engine.durable_json(
        run_dir / f"p0-odin-listing-{generation:04d}-result.json",
        {
            "schema": "s20plus_g986n_p0_odin_listing_result_v1",
            "version": VERSION,
            "generation": generation,
            "binding_sha256": binding_sha256,
            "intent_sha256": engine.digest(intent),
            "returncode": handle.returncode,
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "listing_sha256": hashlib.sha256(listing).hexdigest(),
            "bounded_no_payload_dispatch": True,
            "same_invocation_replay_permitted": False,
            "at": engine.utc_now(),
        },
    )
    return text


def _profile_receipts() -> dict[str, Any]:
    return {
        "p0_owner": self_receipt(),
        "p0_observer": _direct_receipt(
            OBSERVER_PATH, OBSERVER_SIZE, OBSERVER_SHA256, "P0 observer"
        ),
        "p0_init_source": _direct_receipt(
            INIT_SOURCE_PATH, INIT_SOURCE_SIZE, INIT_SOURCE_SHA256, "P0 init source"
        ),
        "p0_global_registry": _registry_authority(),
    }


def validate_host_closure(
    *, include_candidate: bool = True, include_rollback: bool = True
) -> dict[str, Any]:
    _assert_profile_installed()
    if observer.OBSERVER_ACTIVE is not P0_F1_ACTIVE:
        raise P0F1Error("P0 observer and owner activation differ")
    closure = _ENGINE_HOST_VALIDATION_CALL(
        include_candidate=include_candidate,
        include_rollback=include_rollback,
    )
    closure["p0_profile"] = _profile_receipts()
    closure["p0_live_activation"] = {
        "path": str(P0_LIVE_ACTIVATION),
        "present": os.path.lexists(P0_LIVE_ACTIVATION),
        "required_for_live": True,
    }
    if P0_F1_ACTIVE is True:
        closure["p0_live_activation"]["receipt"] = _validate_live_activation()
    return closure


def validate_rollback_closure() -> dict[str, Any]:
    _assert_profile_installed()
    closure = _ENGINE_VALIDATE_ROLLBACK_CLOSURE()
    closure["p0_owner"] = self_receipt()
    return closure


def validate_health_closure() -> dict[str, Any]:
    _assert_profile_installed()
    closure = _ENGINE_VALIDATE_HEALTH_CLOSURE()
    closure["p0_owner"] = self_receipt()
    return closure


def require_active() -> None:
    self_receipt()
    if P0_F1_ACTIVE is not True or observer.OBSERVER_ACTIVE is not True:
        raise P0F1Error("S20+ P0 PID1 Odin F1 is not active")
    _assert_profile_installed()
    _validate_live_activation()


def _download_usb_node(endpoint: dict[str, Any], usb_root: Path | None = None) -> str:
    require_active()
    _require_live_transaction()
    if not isinstance(endpoint, dict):
        raise P0F1Error("P0 Download endpoint is malformed")
    match = USBFS_RE.fullmatch(str(endpoint.get("device", "")))
    if match is None:
        raise P0F1Error("P0 Download endpoint path is malformed")
    bus = str(int(match.group(1)))
    dev = str(int(match.group(2)))
    root = usb_root if usb_root is not None else observer.USB_ROOT
    matches: list[str] = []
    try:
        nodes = sorted(root.iterdir(), key=lambda item: item.name)
    except OSError as exc:
        raise P0F1Error("P0 Download sysfs inventory is unavailable") from exc
    for node in nodes:
        if USB_NODE_RE.fullmatch(node.name) is None:
            continue
        try:
            busnum = observer.read_attr(node / "busnum", "Download busnum")
            devnum = observer.read_attr(node / "devnum", "Download devnum")
        except observer.ObserverError:
            continue
        if busnum == bus and devnum == dev:
            matches.append(node.name)
    if len(matches) != 1:
        raise P0F1Error("P0 Download topology is absent or ambiguous")
    node = matches[0]
    if (
        hashlib.sha256(f"usb:{node}".encode("ascii")).hexdigest()
        != endpoint.get("topology_sha256")
    ):
        raise P0F1Error("P0 Download topology hash differs")
    return node


def _baseline_value(
    binding_sha256: str,
    endpoint: dict[str, Any],
    node: str,
    observed: dict[str, Any],
) -> dict[str, Any]:
    observer.validate_baseline(observed, node)
    return {
        "schema": P0_BASELINE_SCHEMA,
        "version": VERSION,
        "binding_sha256": binding_sha256,
        "download_topology_sha256": endpoint["topology_sha256"],
        "observer_baseline": observed,
        "observer_baseline_sha256": observer.digest(observed),
        "candidate_absent": True,
        "mapping_proved_at_capture": True,
        "at": engine.utc_now(),
    }


def _validate_baseline_value(
    value: Any,
    binding_sha256: str,
    endpoint: dict[str, Any],
) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value)
        != {
            "schema",
            "version",
            "binding_sha256",
            "download_topology_sha256",
            "observer_baseline",
            "observer_baseline_sha256",
            "candidate_absent",
            "mapping_proved_at_capture",
            "at",
        }
        or value.get("schema") != P0_BASELINE_SCHEMA
        or value.get("version") != VERSION
        or value.get("binding_sha256") != binding_sha256
        or value.get("download_topology_sha256") != endpoint.get("topology_sha256")
        or value.get("observer_baseline_sha256")
        != observer.digest(value.get("observer_baseline"))
        or value.get("candidate_absent") is not True
        or value.get("mapping_proved_at_capture") is not True
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise P0F1Error("P0 USB baseline is malformed")
    baseline = value["observer_baseline"]
    if (
        type(baseline) is not dict
        or set(baseline)
        != {
            "schema",
            "observer_schema",
            "expected_topology_sha256",
            "candidate_absent",
            "exact_identity_sha256",
            "pending_identity_sha256",
            "conflicting_identity_sha256",
        }
        or baseline.get("schema") != observer.BASELINE_SCHEMA
        or baseline.get("observer_schema") != observer.SCHEMA
        or baseline.get("candidate_absent") is not True
        or HEX64_RE.fullmatch(str(baseline.get("expected_topology_sha256"))) is None
        or baseline.get("exact_identity_sha256") != []
        or baseline.get("pending_identity_sha256") != []
        or baseline.get("conflicting_identity_sha256") != []
    ):
        raise P0F1Error("P0 observer baseline is malformed")
    return value


def _capture_p0_baseline(
    run_dir: Path,
    binding_sha256: str,
    endpoint: dict[str, Any],
) -> dict[str, Any]:
    require_active()
    _require_live_transaction()
    path = run_dir / P0_BASELINE_NAME
    current = engine.identify_download()
    if not engine.same_download_session(current, endpoint):
        raise P0F1Error("P0 baseline Download session changed")
    node = _download_usb_node(current)
    observed = observer.capture_baseline(node)
    if os.path.lexists(path):
        value = _validate_baseline_value(
            engine.read_json(path, "P0 USB baseline"), binding_sha256, endpoint
        )
        if value["observer_baseline"] != observed:
            raise P0F1Error("P0 candidate identity reappeared before global claim")
        return value
    value = _baseline_value(binding_sha256, endpoint, node, observed)
    engine.durable_json(path, value)
    return value


def consume_candidate_globally(
    run_dir: Path, binding_sha256: str
) -> dict[str, Any]:
    require_active()
    _require_live_transaction()
    prepared = engine.read_json(run_dir / "prepared.json", "P0 prepared binding")
    if (
        prepared.get("binding_sha256") != binding_sha256
        or not isinstance(prepared.get("binding"), dict)
    ):
        raise P0F1Error("P0 prepared binding differs before candidate claim")
    endpoint = prepared["binding"].get("endpoint")
    _capture_p0_baseline(run_dir, binding_sha256, endpoint)
    _stage_candidate_transfer_preflight(run_dir, binding_sha256, endpoint)
    identity = _actual_registry_identity(run_dir, binding_sha256)
    _claim_global_registry(run_dir, binding_sha256, identity)
    local = _ENGINE_CONSUME_CANDIDATE(run_dir, binding_sha256)
    _ENGINE_REQUIRE_CANDIDATE_CLAIM(run_dir, binding_sha256)
    return local


def require_candidate_claim(run_dir: Path, binding_sha256: str) -> dict[str, Any]:
    require_active()
    _require_live_transaction()
    identity = _actual_registry_identity(run_dir, binding_sha256)
    _registry_intent(run_dir, binding_sha256, identity)
    local_parse = _local_parse_result(run_dir, binding_sha256)
    if local_parse is not None:
        released = _release_global_claim_after_local_parse(
            run_dir, binding_sha256, identity
        )
        if released:
            return _local_claim_value(run_dir, binding_sha256)
    receipt_present = os.path.lexists(run_dir / P0_REGISTRY_RECEIPT_NAME)
    uncertain_present = os.path.lexists(run_dir / P0_REGISTRY_UNCERTAIN_NAME)
    if receipt_present and uncertain_present:
        raise P0F1Error("P0 global claim has contradictory receipt states")
    if receipt_present:
        _validate_local_registry_receipt(run_dir, binding_sha256, identity)
    elif uncertain_present:
        _registry_uncertain(run_dir, binding_sha256, identity)
    else:
        try:
            _registry_receipt(run_dir, binding_sha256, identity)
        except P0F1Error:
            try:
                _registry_authority()
            except P0F1Error:
                _registry_uncertain(run_dir, binding_sha256, identity)
            else:
                raise
    if not os.path.lexists(engine.claim_path()):
        _ENGINE_CONSUME_CANDIDATE(run_dir, binding_sha256)
    return _ENGINE_REQUIRE_CANDIDATE_CLAIM(run_dir, binding_sha256)


def _expected_node_from_hashes(baseline: dict[str, Any]) -> str | None:
    require_active()
    _require_live_transaction()
    observer_hash = baseline["observer_baseline"]["expected_topology_sha256"]
    download_hash = baseline["download_topology_sha256"]
    matches = [
        name
        for name, _path in observer.usb_device_nodes(observer.USB_ROOT)
        if observer.hash_text(name) == observer_hash
        and hashlib.sha256(f"usb:{name}".encode("ascii")).hexdigest() == download_hash
    ]
    if len(matches) > 1:
        raise P0F1Error("P0 topology hash mapping became ambiguous")
    return matches[0] if matches else None


def _read_raw_banner(run_dir: Path) -> tuple[bytes, dict[str, Any]]:
    parent_fd = _ENGINE_OPEN_DIRECT_DIRECTORY(run_dir)
    try:
        descriptor = os.open(
            P0_RAW_BANNER_NAME,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
        try:
            metadata = os.fstat(descriptor)
            payload = os.read(descriptor, len(observer.BANNER) + 1)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
                or stat.S_IMODE(metadata.st_mode) != 0o400
                or metadata.st_size != len(observer.BANNER)
                or len(payload) != metadata.st_size
                or os.read(descriptor, 1)
            ):
                raise P0F1Error("P0 raw ACM banner evidence is indirect or changed")
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise P0F1Error("P0 raw ACM banner evidence is unavailable") from exc
    finally:
        os.close(parent_fd)
    value = bytes(payload)
    return value, {
        "name": P0_RAW_BANNER_NAME,
        "size": len(value),
        "sha256": hashlib.sha256(value).hexdigest(),
        "mode": "0400",
    }


def _publish_raw_banner(run_dir: Path, payload: bytes) -> dict[str, Any]:
    require_active()
    _require_live_transaction()
    if payload != observer.BANNER or os.path.lexists(run_dir / P0_RAW_BANNER_NAME):
        raise P0F1Error("P0 raw ACM banner publication is not fresh and exact")
    parent_fd = _ENGINE_OPEN_DIRECT_DIRECTORY(run_dir)
    try:
        engine._atomic_publish_at(
            parent_fd,
            P0_RAW_BANNER_NAME,
            payload,
            0o400,
            "P0 raw ACM banner",
        )
    finally:
        os.close(parent_fd)
    reopened, receipt = _read_raw_banner(run_dir)
    if reopened != payload:
        raise P0F1Error("P0 raw ACM banner changed after publication")
    return receipt


def _observe_p0(run_dir: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    require_active()
    _require_live_transaction()
    baseline = _validate_baseline_value(
        engine.read_json(run_dir / P0_BASELINE_NAME, "P0 USB baseline"),
        prepared["binding_sha256"],
        prepared["binding"]["endpoint"],
    )
    deadline = time.monotonic() + P0_ARRIVAL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            inventory = observer.scan_inventory()
            if inventory.conflicting_identity_sha256:
                raise P0F1Error("P0 candidate USB identity is conflicting")
            if len(inventory.exact) > 1:
                raise P0F1Error("P0 candidate USB endpoint is ambiguous")
            node = _expected_node_from_hashes(baseline)
            if node is None or inventory.pending_identity_sha256 or not inventory.exact:
                time.sleep(P0_POLL_SECONDS)
                continue
            candidate = inventory.exact[0]
            if candidate.usb_node != node:
                raise P0F1Error("P0 candidate arrived on a foreign topology")
            selected = observer.select_arrival(
                baseline["observer_baseline"], node
            )
            descriptor = observer.open_live(selected)
            try:
                observer.verify_descriptor(selected, descriptor)
                payload = observer.read_exact_banner(descriptor)
                observer.verify_descriptor(selected, descriptor)
                repeated = observer.select_arrival(
                    baseline["observer_baseline"],
                    node,
                    usb_root=observer.USB_ROOT,
                    tty_root=observer.TTY_ROOT,
                )
            finally:
                os.close(descriptor)
            if repeated.identity_sha256 != selected.identity_sha256:
                raise P0F1Error("P0 endpoint changed after raw banner")
            rdev_sha256 = observer.digest(
                {"major": selected.major, "minor": selected.minor}
            )
            raw_receipt = _publish_raw_banner(run_dir, payload)
            receipt = {
                "schema": P0_RECEIPT_SCHEMA,
                "observer_schema": observer.SCHEMA,
                "baseline_sha256": observer.digest(baseline["observer_baseline"]),
                "expected_topology_sha256": baseline["observer_baseline"][
                    "expected_topology_sha256"
                ],
                "endpoint_identity_sha256": selected.identity_sha256,
                "descriptor_rdev_sha256": rdev_sha256,
                "endpoint_binding_sha256": observer.digest(
                    {
                        "endpoint_identity_sha256": selected.identity_sha256,
                        "descriptor_rdev_sha256": rdev_sha256,
                    }
                ),
                "raw_banner": raw_receipt,
                "pid1_exact": True,
                "tty_number_stable": False,
                "exact": True,
                "accepted": True,
            }
            return {
                "environment": P0_SUCCESS_ENVIRONMENT,
                "transport_authorized": True,
                "claim_verdict": "PROVED",
                "p0_receipt": receipt,
                "at": engine.utc_now(),
            }
        except (observer.ObserverError, P0F1Error) as exc:
            return {
                "environment": P0_NO_PROOF_ENVIRONMENT,
                "transport_authorized": False,
                "claim_verdict": "NO_PROOF",
                "reason_sha256": hashlib.sha256(str(exc).encode()).hexdigest(),
                "at": engine.utc_now(),
            }
    return {
        "environment": P0_NO_PROOF_ENVIRONMENT,
        "transport_authorized": False,
        "claim_verdict": "NO_PROOF",
        "reason_sha256": hashlib.sha256(b"bounded-p0-observer-timeout").hexdigest(),
        "at": engine.utc_now(),
    }


def observe_candidate(
    run_dir: Path, prepared: dict[str, Any]
) -> tuple[dict[str, Any], None]:
    require_active()
    _require_live_transaction()
    no_backend = False
    if os.path.lexists(run_dir / "candidate-transfer-cut.json"):
        cut = engine.read_json(run_dir / "candidate-transfer-cut.json", "candidate cut")
        no_backend = cut.get("possible_partition_effect") is False
    elif os.path.lexists(run_dir / "candidate-result.json"):
        result = engine.read_json(run_dir / "candidate-result.json", "candidate result")
        no_backend = result.get("classification") == "odin_local_parse_failure"
    if no_backend:
        observation, _serial = _ENGINE_OBSERVE_CANDIDATE(run_dir, prepared)
        return observation, None
    return _observe_p0(run_dir, prepared), None


def _validate_p0_receipt(
    value: Any,
    baseline: dict[str, Any],
    run_dir: Path,
) -> dict[str, Any]:
    expected_keys = {
        "schema",
        "observer_schema",
        "baseline_sha256",
        "expected_topology_sha256",
        "endpoint_identity_sha256",
        "descriptor_rdev_sha256",
        "endpoint_binding_sha256",
        "raw_banner",
        "pid1_exact",
        "tty_number_stable",
        "exact",
        "accepted",
    }
    if (
        type(value) is not dict
        or set(value) != expected_keys
        or value.get("schema") != P0_RECEIPT_SCHEMA
        or value.get("observer_schema") != observer.SCHEMA
        or value.get("baseline_sha256")
        != observer.digest(baseline["observer_baseline"])
        or value.get("expected_topology_sha256")
        != baseline["observer_baseline"]["expected_topology_sha256"]
        or HEX64_RE.fullmatch(str(value.get("endpoint_identity_sha256"))) is None
        or HEX64_RE.fullmatch(str(value.get("descriptor_rdev_sha256"))) is None
        or value.get("endpoint_binding_sha256")
        != observer.digest(
            {
                "endpoint_identity_sha256": value.get("endpoint_identity_sha256"),
                "descriptor_rdev_sha256": value.get("descriptor_rdev_sha256"),
            }
        )
        or value.get("pid1_exact") is not True
        or value.get("tty_number_stable") is not False
        or value.get("exact") is not True
        or value.get("accepted") is not True
    ):
        raise P0F1Error("P0 PID1 ACM receipt is malformed")
    raw, raw_receipt = _read_raw_banner(run_dir)
    if raw != observer.BANNER or value.get("raw_banner") != raw_receipt:
        raise P0F1Error("P0 PID1 claim is not rederived from raw ACM bytes")
    return value


def validate_candidate_observation(
    run_dir: Path,
    value: dict[str, Any],
    binding_sha256: str,
    initial_boot_id_sha256: str,
) -> None:
    environment = value.get("environment") if isinstance(value, dict) else None
    if environment not in {P0_SUCCESS_ENVIRONMENT, P0_NO_PROOF_ENVIRONMENT}:
        _ENGINE_VALIDATE_CANDIDATE_OBSERVATION(
            run_dir, value, binding_sha256, initial_boot_id_sha256
        )
        if value.get("claim_verdict") != "NO_PROOF":
            raise P0F1Error("only exact P0 raw ACM evidence may prove PID1")
        return
    common = {
        "schema",
        "version",
        "binding_sha256",
        "environment",
        "transport_authorized",
        "claim_verdict",
        "at",
        "candidate_replay_permitted",
    }
    success_keys = common | {"p0_receipt"}
    no_proof_keys = common | {"reason_sha256"}
    if (
        value.get("schema") != "s20plus_g986n_b0_candidate_observation_v1"
        or value.get("version") != VERSION
        or value.get("binding_sha256") != binding_sha256
        or value.get("candidate_replay_permitted") is not False
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise P0F1Error("P0 candidate observation is malformed")
    prepared = engine.read_json(run_dir / "prepared.json", "P0 prepared binding")
    baseline = _validate_baseline_value(
        engine.read_json(run_dir / P0_BASELINE_NAME, "P0 USB baseline"),
        binding_sha256,
        prepared["binding"]["endpoint"],
    )
    if environment == P0_SUCCESS_ENVIRONMENT:
        if (
            set(value) != success_keys
            or value.get("transport_authorized") is not True
            or value.get("claim_verdict") != "PROVED"
        ):
            raise P0F1Error("P0 positive observation is malformed")
        _validate_p0_receipt(value.get("p0_receipt"), baseline, run_dir)
    elif (
        set(value) != no_proof_keys
        or value.get("transport_authorized") is not False
        or value.get("claim_verdict") != "NO_PROOF"
        or HEX64_RE.fullmatch(str(value.get("reason_sha256"))) is None
    ):
        raise P0F1Error("P0 no-proof observation is malformed")


def _physical_rebind_continuity(
    prior: dict[str, Any], current: dict[str, Any]
) -> bool:
    try:
        engine._validate_endpoint(prior, "P0 prior physical Download endpoint")
        engine._validate_endpoint(current, "P0 rebound physical Download endpoint")
    except engine.B0F1Error:
        return False
    prior_match = USBFS_RE.fullmatch(str(prior.get("device", "")))
    current_match = USBFS_RE.fullmatch(str(current.get("device", "")))
    return bool(
        prior_match is not None
        and current_match is not None
        and prior_match.group(1) == current_match.group(1)
        and prior["device"] != current["device"]
        and prior["endpoint_sha256"] != current["endpoint_sha256"]
        and prior["topology_sha256"] == current["topology_sha256"]
        and prior["usb"] == current["usb"]
        and prior["usb"] == {**engine.DOWNLOAD_USB, "serial_absent": True}
    )


def _validate_physical_rebind_arm(
    run_dir: Path, prepared: dict[str, Any]
) -> dict[str, Any]:
    value = engine.read_json(
        run_dir / P0_PHYSICAL_REBIND_ARM_NAME,
        "P0 physical rollback rebind arm",
    )
    source_arrival = engine.read_json(
        run_dir / "physical-rollback-arrival.json",
        "P0 physical rollback source arrival",
    )
    source_confirmation = engine.read_json(
        run_dir / "physical-confirmation-intent.json",
        "P0 physical rollback source confirmation",
    )
    expected_keys = {
        "schema",
        "version",
        "binding_sha256",
        "source_arrival_sha256",
        "source_confirmation_sha256",
        "prior_endpoint",
        "endpoint",
        "reason",
        "expires_unix",
        "confirmation_token",
        "no_replay",
        "at",
    }
    core = {key: item for key, item in value.items() if key != "confirmation_token"}
    if (
        type(value) is not dict
        or set(value) != expected_keys
        or value.get("schema") != P0_PHYSICAL_REBIND_ARM_SCHEMA
        or value.get("version") != VERSION
        or value.get("binding_sha256") != prepared.get("binding_sha256")
        or value.get("source_arrival_sha256") != engine.digest(source_arrival)
        or value.get("source_confirmation_sha256")
        != engine.digest(source_confirmation)
        or value.get("prior_endpoint") != source_arrival.get("endpoint")
        or not isinstance(value.get("endpoint"), dict)
        or not _physical_rebind_continuity(
            value.get("prior_endpoint"), value["endpoint"]
        )
        or value.get("reason") != "usbfs-address-reenumerated-same-physical-topology"
        or type(value.get("expires_unix")) is not int
        or value.get("confirmation_token")
        != PHYSICAL_REBIND_CONFIRM_PREFIX + engine.digest(core)
        or value.get("no_replay") is not True
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise P0F1Error("P0 physical rollback rebind arm is malformed")
    return value


def _validate_physical_rebind_confirmation(
    run_dir: Path, prepared: dict[str, Any], arm: dict[str, Any]
) -> dict[str, Any]:
    value = engine.read_json(
        run_dir / P0_PHYSICAL_REBIND_CONFIRM_NAME,
        "P0 physical rollback rebind confirmation",
    )
    if (
        type(value) is not dict
        or set(value)
        != {
            "schema",
            "version",
            "binding_sha256",
            "arm_sha256",
            "confirmation_token_sha256",
            "confirmed_unix",
            "no_replay",
            "at",
        }
        or value.get("schema") != P0_PHYSICAL_REBIND_CONFIRM_SCHEMA
        or value.get("version") != VERSION
        or value.get("binding_sha256") != prepared.get("binding_sha256")
        or value.get("arm_sha256") != engine.digest(arm)
        or value.get("confirmation_token_sha256")
        != hashlib.sha256(arm["confirmation_token"].encode()).hexdigest()
        or type(value.get("confirmed_unix")) is not int
        or value.get("confirmed_unix") > arm.get("expires_unix", -1)
        or value.get("no_replay") is not True
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise P0F1Error("P0 physical rollback rebind confirmation is malformed")
    return value


def _validate_physical_rebind_arrival(
    run_dir: Path,
    prepared: dict[str, Any],
    arm: dict[str, Any],
    confirmation: dict[str, Any],
) -> dict[str, Any]:
    value = engine.read_json(
        run_dir / P0_PHYSICAL_REBIND_ARRIVAL_NAME,
        "P0 physical rollback rebound arrival",
    )
    if (
        type(value) is not dict
        or set(value)
        != {
            "schema",
            "version",
            "binding_sha256",
            "arm_sha256",
            "confirmation_sha256",
            "endpoint",
            "at",
        }
        or value.get("schema") != P0_PHYSICAL_REBIND_ARRIVAL_SCHEMA
        or value.get("version") != VERSION
        or value.get("binding_sha256") != prepared.get("binding_sha256")
        or value.get("arm_sha256") != engine.digest(arm)
        or value.get("confirmation_sha256") != engine.digest(confirmation)
        or value.get("endpoint") != arm.get("endpoint")
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise P0F1Error("P0 physical rollback rebound arrival is malformed")
    return value


def _validate_physical_rebind_miss(
    run_dir: Path,
    prepared: dict[str, Any],
    arm: dict[str, Any],
    confirmation: dict[str, Any],
) -> dict[str, Any]:
    value = engine.read_json(
        run_dir / P0_PHYSICAL_REBIND_MISS_NAME,
        "P0 physical rollback rebind miss",
    )
    current_endpoint = value.get("current_endpoint") if isinstance(value, dict) else None
    if current_endpoint is not None:
        try:
            engine._validate_endpoint(
                current_endpoint, "P0 physical rollback rebind miss endpoint"
            )
        except engine.B0F1Error as exc:
            raise P0F1Error("P0 physical rollback rebind miss is malformed") from exc
    if (
        type(value) is not dict
        or set(value)
        != {
            "schema",
            "version",
            "binding_sha256",
            "arm_sha256",
            "confirmation_sha256",
            "reason",
            "current_endpoint",
            "no_replay",
            "at",
        }
        or value.get("schema") != P0_PHYSICAL_REBIND_MISS_SCHEMA
        or value.get("version") != VERSION
        or value.get("binding_sha256") != prepared.get("binding_sha256")
        or value.get("arm_sha256") != engine.digest(arm)
        or value.get("confirmation_sha256") != engine.digest(confirmation)
        or value.get("reason")
        not in {
            "identity-unproved-after-confirmation",
            "identity-unproved-before-rollback-intent",
            "endpoint-changed-after-confirmation",
            "endpoint-changed-before-rollback-intent",
        }
        or value.get("no_replay") is not True
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise P0F1Error("P0 physical rollback rebind miss is malformed")
    return value


def validate_namespace(run_dir: Path) -> None:
    _ENGINE_VALIDATE_NAMESPACE(run_dir)
    names = {entry.name for entry in os.scandir(run_dir)}
    prepared = None
    identity = None
    if "prepared.json" in names:
        prepared = engine.read_json(run_dir / "prepared.json", "P0 prepared binding")
        identity = _registry_identity(run_dir.name, prepared["binding_sha256"])
    baseline_present = P0_BASELINE_NAME in names
    if baseline_present:
        if not {"prepared.json", "approval.json", "candidate-adb-baseline.json"} <= names:
            raise P0F1Error("P0 USB baseline lacks its pre-candidate chain")
        assert prepared is not None
        _validate_baseline_value(
            engine.read_json(run_dir / P0_BASELINE_NAME, "P0 USB baseline"),
            prepared["binding_sha256"],
            prepared["binding"]["endpoint"],
        )
    if "candidate-claim-intent.json" in names and not baseline_present:
        raise P0F1Error("P0 candidate claim lacks the USB baseline")
    if P0_CANDIDATE_PREFLIGHT_NAME in names:
        if not baseline_present or prepared is None:
            raise P0F1Error("P0 candidate preflight lacks its prepared baseline")
        _validate_candidate_transfer_preflight(
            run_dir,
            prepared["binding_sha256"],
            prepared["binding"]["endpoint"],
        )
    if (
        "candidate-claim-intent.json" in names
        and P0_CANDIDATE_PREFLIGHT_NAME not in names
    ):
        raise P0F1Error("P0 candidate claim precedes complete transfer preflight")
    if P0_REGISTRY_INTENT_NAME in names:
        if not baseline_present or P0_CANDIDATE_PREFLIGHT_NAME not in names:
            raise P0F1Error("P0 global candidate claim lacks complete preflight")
        assert prepared is not None and identity is not None
        _registry_intent(run_dir, prepared["binding_sha256"], identity)
    if P0_REGISTRY_RECEIPT_NAME in names:
        if P0_REGISTRY_INTENT_NAME not in names:
            raise P0F1Error("P0 global candidate receipt lacks its intent")
        assert prepared is not None and identity is not None
        _validate_local_registry_receipt(
            run_dir, prepared["binding_sha256"], identity
        )
    if P0_REGISTRY_UNCERTAIN_NAME in names:
        if P0_REGISTRY_INTENT_NAME not in names:
            raise P0F1Error("P0 uncertain global claim lacks its intent")
        assert prepared is not None and identity is not None
        _registry_uncertain(run_dir, prepared["binding_sha256"], identity)
    if (
        P0_REGISTRY_RECEIPT_NAME in names
        and P0_REGISTRY_UNCERTAIN_NAME in names
    ):
        raise P0F1Error("P0 global claim has contradictory receipt states")
    if (
        "candidate-claim-intent.json" in names
        and P0_REGISTRY_RECEIPT_NAME not in names
        and P0_REGISTRY_UNCERTAIN_NAME not in names
    ):
        raise P0F1Error("P0 local candidate claim lacks global consumed evidence")
    if P0_REGISTRY_RELEASE_INTENT_NAME in names:
        if P0_REGISTRY_RECEIPT_NAME not in names or "candidate-result.json" not in names:
            raise P0F1Error("P0 global release intent lacks claim or result")
        assert prepared is not None and identity is not None
        local_receipt = _validate_local_registry_receipt(
            run_dir, prepared["binding_sha256"], identity
        )
        if _local_parse_result(run_dir, prepared["binding_sha256"]) is None:
            raise P0F1Error("P0 global release lacks local-parse proof")
        _registry_release_intent(
            run_dir,
            prepared["binding_sha256"],
            identity,
            local_receipt["active_record"],
        )
    if P0_REGISTRY_RELEASE_RECEIPT_NAME in names:
        if P0_REGISTRY_RELEASE_INTENT_NAME not in names:
            raise P0F1Error("P0 global release receipt lacks its intent")
        assert prepared is not None and identity is not None
        local_receipt = _validate_local_registry_receipt(
            run_dir, prepared["binding_sha256"], identity
        )
        release_receipt = _validate_registry_release_receipt(
            run_dir,
            prepared["binding_sha256"],
            identity,
            local_receipt["active_record"],
        )
        if P0_LOCAL_PROJECTION_RELEASE_NAME not in names:
            raise P0F1Error("P0 released global claim retains a local projection")
        _remove_local_recovery_projection(
            run_dir, prepared["binding_sha256"], release_receipt
        )
    elif P0_LOCAL_PROJECTION_RELEASE_NAME in names:
        raise P0F1Error("P0 local projection release lacks global release proof")
    if P0_RAW_BANNER_NAME in names:
        if "candidate-observation-intent.json" not in names:
            raise P0F1Error("P0 raw ACM evidence lacks its observation intent")
        raw, _receipt = _read_raw_banner(run_dir)
        if raw != observer.BANNER:
            raise P0F1Error("P0 raw ACM evidence differs")
    if "candidate-observation.json" in names and not baseline_present:
        raise P0F1Error("P0 observation lacks the USB baseline")
    rebind_arm = None
    rebind_confirmation = None
    if P0_PHYSICAL_REBIND_ARM_NAME in names:
        if not {
            "prepared.json",
            "physical-rollback-arrival.json",
            "physical-confirmation-intent.json",
        } <= names:
            raise P0F1Error("P0 physical rollback rebind lacks its source chain")
        assert prepared is not None
        rebind_arm = _validate_physical_rebind_arm(run_dir, prepared)
    if P0_PHYSICAL_REBIND_CONFIRM_NAME in names:
        if rebind_arm is None:
            raise P0F1Error("P0 physical rollback rebind confirmation lacks its arm")
        assert prepared is not None
        rebind_confirmation = _validate_physical_rebind_confirmation(
            run_dir, prepared, rebind_arm
        )
    if P0_PHYSICAL_REBIND_ARRIVAL_NAME in names:
        if rebind_arm is None or rebind_confirmation is None:
            raise P0F1Error("P0 rebound arrival lacks its confirmation chain")
        assert prepared is not None
        _validate_physical_rebind_arrival(
            run_dir, prepared, rebind_arm, rebind_confirmation
        )
    if P0_PHYSICAL_REBIND_MISS_NAME in names:
        if rebind_arm is None or rebind_confirmation is None:
            raise P0F1Error("P0 rebind miss lacks its confirmation chain")
        assert prepared is not None
        _validate_physical_rebind_miss(
            run_dir, prepared, rebind_arm, rebind_confirmation
        )
    if "rollback-intent.json" in names and rebind_arm is not None:
        if (
            rebind_confirmation is None
            or P0_PHYSICAL_REBIND_ARRIVAL_NAME not in names
            or P0_PHYSICAL_REBIND_MISS_NAME in names
        ):
            raise P0F1Error("P0 rebound rollback lacks its complete arrival chain")
        rollback_intent = engine.read_json(
            run_dir / "rollback-intent.json", "P0 rollback intent"
        )
        rebound_arrival = engine.read_json(
            run_dir / P0_PHYSICAL_REBIND_ARRIVAL_NAME,
            "P0 physical rollback rebound arrival",
        )
        if rollback_intent.get("endpoint") != rebound_arrival.get("endpoint"):
            raise P0F1Error("P0 rollback endpoint differs from rebound arrival")
    binding_sha256 = None if prepared is None else prepared["binding_sha256"]
    for kind in CAGE_KINDS:
        effect_name = _effect_intent_name(kind)
        effect = (
            engine.read_json(run_dir / effect_name, f"P0 {kind} effect intent")
            if effect_name is not None and effect_name in names
            else None
        )
        claim_cut = (
            kind == "candidate"
            and isinstance(effect, dict)
            and effect.get("global_claim_cut") is True
            and effect.get("backend_invoked") is False
        )
        matched_effect_cages = 0
        for generation, suffixes in _cage_generations(run_dir, kind).items():
            generation_effect = effect
            if kind == "odin-listing":
                listing_name = _effect_intent_name(kind, generation)
                generation_effect = (
                    engine.read_json(
                        run_dir / listing_name, "P0 Odin-listing effect intent"
                    )
                    if listing_name is not None and listing_name in names
                    else None
                )
            expected_binding = (
                binding_sha256 if kind in {"candidate", "rollback"} else None
            )
            cage_prepare = _validate_cage_prepare(
                run_dir, kind, generation, expected_binding
            )
            cage_bound = None
            if "bound" in suffixes:
                cage_bound = _validate_cage_bound(
                    run_dir, kind, generation, cage_prepare
                )["process_cage"]
            effect_match = _effect_matches_cage(
                kind, generation_effect, cage_prepare, cage_bound
            )
            if effect_match:
                matched_effect_cages += 1
            if "reconciled" in suffixes:
                _validate_cage_reconciled(
                    run_dir, kind, generation, cage_prepare
                )
                if kind == "odin-listing":
                    intent_name = _effect_intent_name(kind, generation)
                    result_name = f"p0-odin-listing-{generation:04d}-result.json"
                    if isinstance(generation_effect, dict):
                        if cage_bound is None or not effect_match:
                            raise P0F1Error(
                                "P0 reconciled Odin-listing intent differs from its cage"
                            )
                        listing_intent = _validate_odin_listing_intent(
                            run_dir, generation, cage_prepare, cage_bound
                        )
                        if result_name in names:
                            _validate_odin_listing_result(
                                run_dir, generation, cage_prepare, listing_intent
                            )
                    elif result_name in names or (
                        intent_name is not None and intent_name in names
                    ):
                        raise P0F1Error(
                            "P0 Odin-listing result lacks its intent and bound cage"
                        )
                continue
            if not isinstance(generation_effect, dict) or claim_cut:
                raise P0F1Error("P0 process-cage prepare cut is unreconciled")
            if not effect_match:
                raise P0F1Error("P0 effect process-cage receipt differs")
        if isinstance(effect, dict) and not claim_cut and matched_effect_cages != 1:
            raise P0F1Error("P0 effect lacks one exact active process cage")


def derive_terminal_verdict(
    candidate_classification: str,
    claim_verdict: str,
    rollback_completed: bool,
) -> tuple[str, bool]:
    proved = (
        candidate_classification == "odin_transfer_completed"
        and claim_verdict == "PROVED"
        and rollback_completed is True
    )
    if proved:
        return "PROVED_P0_PID1_ACM_RETURNED_RESIDENT_HEALTHY", True
    return "NO_PROOF_P0_RETURNED_RESIDENT_HEALTHY", False


def render_plan() -> dict[str, Any]:
    activation_record_valid = False
    activation_record_failure = None
    if P0_F1_ACTIVE is True and observer.OBSERVER_ACTIVE is True:
        try:
            _validate_live_activation()
            activation_record_valid = True
        except P0F1Error as exc:
            activation_record_failure = type(exc).__name__
    activation_complete = (
        P0_F1_ACTIVE is True
        and observer.OBSERVER_ACTIVE is True
        and activation_record_valid
    )
    activation_mismatch = P0_F1_ACTIVE is not observer.OBSERVER_ACTIVE
    return {
        "schema": PLAN_SCHEMA,
        "version": VERSION,
        "status": (
            "BINDING_ATTENDED_P0_PID1_BOOT_ONLY_F1_ACTIVE"
            if activation_complete
            else (
                "ACTIVATION_MISMATCH_NOT_ACTIVE"
                if activation_mismatch
                else (
                    "ACTIVATION_RECORD_INVALID_NOT_ACTIVE"
                    if P0_F1_ACTIVE is True
                    else "H0_IMPLEMENTED_REVIEW_PENDING_NOT_ACTIVE"
                )
            )
        ),
        "active": activation_complete,
        "live_authority": activation_complete,
        "activation_mismatch": activation_mismatch,
        "activation_record": {
            "path": str(P0_LIVE_ACTIVATION),
            "required": True,
            "valid": activation_record_valid,
            "failure_class": activation_record_failure,
        },
        "target": dict(engine.TARGET),
        "engine": {
            "path": str(ENGINE_PATH),
            "size": ENGINE_SIZE,
            "sha256": ENGINE_SHA256,
            "isolated_module_instance": True,
            "closed_b0_journals_untouched": True,
        },
        "candidate": {
            "partition": "boot",
            "ap_size": CANDIDATE_AP_SIZE,
            "ap_sha256": CANDIDATE_AP_SHA256,
            "member": "boot.img.lz4",
            "decoded_boot_sha256": CANDIDATE_BOOT_SHA256,
            "first_runtime_syscall": "getpid",
            "accepted_pid": 1,
        },
        "observation": {
            "transport": "usb-cdc-acm",
            "observer_sha256": OBSERVER_SHA256,
            "usb": {
                "vendor": observer.USB_VENDOR,
                "product": observer.USB_PRODUCT,
                "manufacturer": observer.USB_MANUFACTURER,
                "product_string": observer.USB_PRODUCT_STRING,
                "serial_absent": True,
            },
            "banner_sha256": hashlib.sha256(observer.BANNER).hexdigest(),
            "banner_size": len(observer.BANNER),
            "timeout_seconds": P0_ARRIVAL_TIMEOUT_SECONDS,
        },
        "rollback": {
            "partition": "boot",
            "mandatory_after_candidate_intent": True,
            "ap_size": ROLLBACK_AP_SIZE,
            "ap_sha256": ROLLBACK_AP_SHA256,
            "member": "boot.img.lz4",
            "physical_download_fallback": True,
        },
        "forbidden": {
            "candidate_replay": True,
            "rollback_replay": True,
            "recovery_partition_read": True,
            "recovery_partition_write": True,
            "recovery_partition_transfer": True,
            "caller_selected_artifact": True,
            "caller_selected_command": True,
            "other_target_command": True,
        },
        "approval_after_fresh_android_prepare": True,
        "shared_guard": str(SHARED_GUARD),
        "local_recovery_projection": str(engine.claim_path()),
        "authoritative_global_registry": registry.REGISTRY_DIR_NAME,
        "target_session_lease": registry.SESSION_LOCK_NAME,
        "modes": [
            "render-plan",
            "validate-host",
            "prepare",
            "execute",
            "resume",
            "arm-physical-rollback",
            "confirm-physical-rollback",
            "finalize-resident",
            "abort-pre-candidate",
        ],
    }


def _candidate_preflight_bound(
    run_dir: Path, process_cage: dict[str, Any]
) -> tuple[int, dict[str, Any]]:
    matches: list[tuple[int, dict[str, Any]]] = []
    for generation, suffixes in _cage_generations(run_dir, "candidate").items():
        if "bound" not in suffixes:
            continue
        prepare = _validate_cage_prepare(
            run_dir,
            "candidate",
            generation,
            process_cage.get("binding_sha256"),
        )
        bound = _validate_cage_bound(
            run_dir, "candidate", generation, prepare
        )["process_cage"]
        if bound == process_cage:
            matches.append((generation, prepare))
    if len(matches) != 1:
        raise P0F1Error("P0 candidate preflight lacks one exact cage receipt")
    return matches[0]


def _validate_candidate_transfer_preflight(
    run_dir: Path, binding_sha256: str, endpoint: dict[str, Any]
) -> dict[str, Any]:
    value = engine.read_json(
        run_dir / P0_CANDIDATE_PREFLIGHT_NAME,
        "P0 candidate transfer preflight",
    )
    prepared = engine.read_json(run_dir / "prepared.json", "P0 prepared binding")
    prepared_binding = prepared.get("binding") if isinstance(prepared, dict) else None
    prepared_endpoint = (
        prepared_binding.get("endpoint")
        if isinstance(prepared_binding, dict)
        else None
    )
    process_cage = value.get("process_cage") if isinstance(value, dict) else None
    if (
        type(value) is not dict
        or set(value)
        != {
            "schema",
            "version",
            "binding_sha256",
            "candidate_ap",
            "prepared_endpoint_sha256",
            "current_endpoint",
            "process_cage",
            "complete_before_global_claim",
            "backend_invoked",
            "at",
        }
        or value.get("schema") != P0_CANDIDATE_PREFLIGHT_SCHEMA
        or value.get("version") != VERSION
        or value.get("binding_sha256") != binding_sha256
        or prepared.get("binding_sha256") != binding_sha256
        or not isinstance(prepared_endpoint, dict)
        or value.get("candidate_ap")
        != {
            "path": str(CANDIDATE_AP),
            "size": CANDIDATE_AP_SIZE,
            "sha256": CANDIDATE_AP_SHA256,
            "member_name": "boot.img.lz4",
            "member_size": CANDIDATE_MEMBER_SIZE,
            "member_sha256": CANDIDATE_MEMBER_SHA256,
        }
        or value.get("prepared_endpoint_sha256")
        != engine.digest(prepared_endpoint)
        or not isinstance(value.get("current_endpoint"), dict)
        or not engine.same_download_session(endpoint, prepared_endpoint)
        or not engine.same_download_session(value["current_endpoint"], endpoint)
        or not isinstance(process_cage, dict)
        or process_cage.get("binding_sha256") != binding_sha256
        or process_cage.get("kind") != "candidate"
        or value.get("complete_before_global_claim") is not True
        or value.get("backend_invoked") is not False
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise P0F1Error("P0 candidate transfer preflight differs")
    _candidate_preflight_bound(run_dir, process_cage)
    return value


def _make_candidate_preflight_pair(original):
    def stage(
        run_dir: Path, binding_sha256: str, endpoint: dict[str, Any]
    ) -> dict[str, Any]:
        require_active()
        transaction = _require_live_transaction()
        if transaction.get("run_dir") != str(run_dir):
            raise P0F1Error("P0 candidate preflight escaped its leased run")
        path = run_dir / P0_CANDIDATE_PREFLIGHT_NAME
        if os.path.lexists(path):
            raise P0F1Error("P0 candidate preflight was already consumed")
        current, process_cage = original(
            run_dir,
            "candidate",
            CANDIDATE_AP,
            CANDIDATE_AP_SIZE,
            CANDIDATE_AP_SHA256,
            endpoint,
            binding_sha256,
        )
        value = {
            "schema": P0_CANDIDATE_PREFLIGHT_SCHEMA,
            "version": VERSION,
            "binding_sha256": binding_sha256,
            "candidate_ap": {
                "path": str(CANDIDATE_AP),
                "size": CANDIDATE_AP_SIZE,
                "sha256": CANDIDATE_AP_SHA256,
                "member_name": "boot.img.lz4",
                "member_size": CANDIDATE_MEMBER_SIZE,
                "member_sha256": CANDIDATE_MEMBER_SHA256,
            },
            "prepared_endpoint_sha256": engine.digest(endpoint),
            "current_endpoint": current,
            "process_cage": process_cage,
            "complete_before_global_claim": True,
            "backend_invoked": False,
            "at": engine.utc_now(),
        }
        engine.durable_json(path, value)
        return _validate_candidate_transfer_preflight(
            run_dir, binding_sha256, endpoint
        )

    def replacement(
        run_dir: Path,
        kind: str,
        path: Path,
        size: int,
        sha256: str,
        endpoint: dict[str, Any],
        binding_sha256: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        require_active()
        _require_live_transaction()
        if kind != "candidate":
            return original(
                run_dir, kind, path, size, sha256, endpoint, binding_sha256
            )
        if (
            path != CANDIDATE_AP
            or size != CANDIDATE_AP_SIZE
            or sha256 != CANDIDATE_AP_SHA256
            or not os.path.lexists(run_dir / "candidate-claim-intent.json")
        ):
            raise P0F1Error("P0 candidate dispatch lacks its completed preclaim closure")
        receipt_present = os.path.lexists(run_dir / P0_REGISTRY_RECEIPT_NAME)
        uncertain_present = os.path.lexists(run_dir / P0_REGISTRY_UNCERTAIN_NAME)
        if receipt_present is uncertain_present:
            raise P0F1Error("P0 candidate dispatch lacks one global claim state")
        value = _validate_candidate_transfer_preflight(
            run_dir, binding_sha256, endpoint
        )
        current = value["current_endpoint"]
        live = engine.identify_download()
        if not engine.same_download_session(live, current):
            raise P0F1Error("P0 candidate endpoint changed after preclaim closure")
        return live, value["process_cage"]

    stage.__name__ = "p0_stage_candidate_transfer_preflight"
    replacement.__name__ = "p0_preflight_odin_dispatch"
    return stage, replacement


_stage_candidate_transfer_preflight, _P0_PREFLIGHT_ODIN_DISPATCH = (
    _make_candidate_preflight_pair(engine.preflight_odin_dispatch)
)


def _make_transfer_replacement(original):
    def replacement(
        run_dir: Path,
        kind: str,
        endpoint: dict[str, Any],
        binding_sha256: str,
    ) -> dict[str, Any]:
        require_active()
        _require_live_transaction()
        result = original(run_dir, kind, endpoint, binding_sha256)
        if kind == "candidate" and result.get("classification") == "odin_local_parse_failure":
            identity = _actual_registry_identity(run_dir, binding_sha256)
            _release_global_claim_after_local_parse(
                run_dir, binding_sha256, identity
            )
        return result

    replacement.__name__ = "p0_transfer_boot"
    return replacement


_P0_TRANSFER_BOOT = _make_transfer_replacement(engine.transfer_boot)


_ENGINE_ARM_PHYSICAL_ROLLBACK = engine.arm_physical_rollback
_ENGINE_CONFIRM_PHYSICAL_ROLLBACK = engine.confirm_physical_rollback


def _arm_physical_rollback_rebind(
    run_dir: Path, prepared: dict[str, Any]
) -> dict[str, Any]:
    if os.path.lexists(run_dir / "rollback-intent.json"):
        raise P0F1Error("P0 rollback was already attempted; replay forbidden")
    if os.path.lexists(run_dir / P0_PHYSICAL_REBIND_MISS_NAME):
        raise P0F1Error("P0 physical rollback rebind was invalidated")
    path = run_dir / P0_PHYSICAL_REBIND_ARM_NAME
    if os.path.lexists(path):
        arm = _validate_physical_rebind_arm(run_dir, prepared)
        if (
            not os.path.lexists(run_dir / P0_PHYSICAL_REBIND_CONFIRM_NAME)
            and int(time.time()) > arm["expires_unix"]
        ):
            raise P0F1Error("P0 physical rollback rebind arm expired")
    else:
        source_arrival = engine.read_json(
            run_dir / "physical-rollback-arrival.json",
            "P0 physical rollback source arrival",
        )
        source_confirmation = engine.read_json(
            run_dir / "physical-confirmation-intent.json",
            "P0 physical rollback source confirmation",
        )
        current = engine.identify_download()
        prior = source_arrival.get("endpoint")
        if not isinstance(prior, dict) or not _physical_rebind_continuity(
            prior, current
        ):
            raise P0F1Error(
                "P0 physical rollback changed beyond one USBFS address re-enumeration"
            )
        core = {
            "schema": P0_PHYSICAL_REBIND_ARM_SCHEMA,
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "source_arrival_sha256": engine.digest(source_arrival),
            "source_confirmation_sha256": engine.digest(source_confirmation),
            "prior_endpoint": prior,
            "endpoint": current,
            "reason": "usbfs-address-reenumerated-same-physical-topology",
            "expires_unix": int(time.time())
            + engine.PHYSICAL_ARRIVAL_LIFETIME_SECONDS,
            "no_replay": True,
            "at": engine.utc_now(),
        }
        arm = {
            **core,
            "confirmation_token": PHYSICAL_REBIND_CONFIRM_PREFIX
            + engine.digest(core),
        }
        engine.durable_json(path, arm)
        arm = _validate_physical_rebind_arm(run_dir, prepared)
    confirmed = os.path.lexists(run_dir / P0_PHYSICAL_REBIND_CONFIRM_NAME)
    return {
        "schema": "s20plus_g986n_p0_recovery_pending_v1",
        "run_dir": str(run_dir),
        "binding_sha256": prepared["binding_sha256"],
        "verdict": (
            "PHYSICAL_DOWNLOAD_REENUM_CONFIRMED_RECOVERY_PENDING"
            if confirmed
            else "PHYSICAL_DOWNLOAD_REENUM_BOUND_AWAITING_CONFIRMATION"
        ),
        "confirmation": arm["confirmation_token"],
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
    }


def _arm_physical_rollback_with_rebind(run_dir: Path) -> dict[str, Any]:
    require_active()
    prepared = engine.read_prepared(run_dir, phase="rollback")
    engine.require_all_transfer_processes_quiescent(
        run_dir, prepared["binding_sha256"]
    )
    if os.path.lexists(run_dir / P0_PHYSICAL_REBIND_ARM_NAME) or os.path.lexists(
        run_dir / "physical-confirmation-intent.json"
    ):
        return _arm_physical_rollback_rebind(run_dir, prepared)
    return _ENGINE_ARM_PHYSICAL_ROLLBACK(run_dir)


def _publish_physical_rebind_miss(
    run_dir: Path,
    prepared: dict[str, Any],
    arm: dict[str, Any],
    confirmation: dict[str, Any],
    reason: str,
    current_endpoint: dict[str, Any] | None,
) -> dict[str, Any]:
    path = run_dir / P0_PHYSICAL_REBIND_MISS_NAME
    if not os.path.lexists(path):
        engine.durable_json(
            path,
            {
                "schema": P0_PHYSICAL_REBIND_MISS_SCHEMA,
                "version": VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "arm_sha256": engine.digest(arm),
                "confirmation_sha256": engine.digest(confirmation),
                "reason": reason,
                "current_endpoint": current_endpoint,
                "no_replay": True,
                "at": engine.utc_now(),
            },
        )
    return _validate_physical_rebind_miss(
        run_dir, prepared, arm, confirmation
    )


def _rollback_preintent_identity_miss_reason(exc: BaseException) -> str | None:
    message = str(exc)
    if message in ROLLBACK_PREINTENT_IDENTITY_ERRORS:
        return "identity-unproved-before-rollback-intent"
    if message in ROLLBACK_PREINTENT_ENDPOINT_CHANGE_ERRORS:
        return "endpoint-changed-before-rollback-intent"
    return None


def _confirm_rebound_physical_rollback(
    run_dir: Path, prepared: dict[str, Any], confirmation: str
) -> dict[str, Any]:
    arm = _validate_physical_rebind_arm(run_dir, prepared)
    if confirmation != arm["confirmation_token"]:
        raise P0F1Error("P0 physical rollback rebind confirmation differs")
    if os.path.lexists(run_dir / "rollback-intent.json"):
        raise P0F1Error("P0 rollback was already attempted; replay forbidden")
    if os.path.lexists(run_dir / P0_PHYSICAL_REBIND_MISS_NAME):
        raise P0F1Error("P0 physical rollback rebind was invalidated")
    confirmation_path = run_dir / P0_PHYSICAL_REBIND_CONFIRM_NAME
    if not os.path.lexists(confirmation_path):
        confirmed_unix = int(time.time())
        if confirmed_unix > arm["expires_unix"]:
            raise P0F1Error("P0 physical rollback rebind confirmation expired")
        current = engine.identify_download()
        if not engine.same_download_session(current, arm["endpoint"]):
            raise P0F1Error("P0 confirmed rebound Download endpoint changed")
        engine.durable_json(
            confirmation_path,
            {
                "schema": P0_PHYSICAL_REBIND_CONFIRM_SCHEMA,
                "version": VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "arm_sha256": engine.digest(arm),
                "confirmation_token_sha256": hashlib.sha256(
                    confirmation.encode()
                ).hexdigest(),
                "confirmed_unix": confirmed_unix,
                "no_replay": True,
                "at": engine.utc_now(),
            },
        )
    rebound_confirmation = _validate_physical_rebind_confirmation(
        run_dir, prepared, arm
    )
    try:
        current = engine.identify_download()
    except engine.B0F1Error as exc:
        _publish_physical_rebind_miss(
            run_dir,
            prepared,
            arm,
            rebound_confirmation,
            "identity-unproved-after-confirmation",
            None,
        )
        raise P0F1Error(
            "P0 rebound Download identity is unproved after confirmation"
        ) from exc
    if not engine.same_download_session(current, arm["endpoint"]):
        _publish_physical_rebind_miss(
            run_dir,
            prepared,
            arm,
            rebound_confirmation,
            "endpoint-changed-after-confirmation",
            current,
        )
        raise P0F1Error("P0 rebound Download endpoint changed after confirmation")
    arrival_path = run_dir / P0_PHYSICAL_REBIND_ARRIVAL_NAME
    if not os.path.lexists(arrival_path):
        engine.durable_json(
            arrival_path,
            {
                "schema": P0_PHYSICAL_REBIND_ARRIVAL_SCHEMA,
                "version": VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "arm_sha256": engine.digest(arm),
                "confirmation_sha256": engine.digest(rebound_confirmation),
                "endpoint": current,
                "at": engine.utc_now(),
            },
        )
    rebound_arrival = _validate_physical_rebind_arrival(
        run_dir, prepared, arm, rebound_confirmation
    )
    try:
        dispatch_current = engine.identify_download()
    except (engine.B0F1Error, OSError) as exc:
        _publish_physical_rebind_miss(
            run_dir,
            prepared,
            arm,
            rebound_confirmation,
            "identity-unproved-before-rollback-intent",
            None,
        )
        raise P0F1Error(
            "P0 rebound Download identity is unproved before rollback intent"
        ) from exc
    if not engine.same_download_session(
        dispatch_current, rebound_arrival["endpoint"]
    ):
        _publish_physical_rebind_miss(
            run_dir,
            prepared,
            arm,
            rebound_confirmation,
            "endpoint-changed-before-rollback-intent",
            dispatch_current,
        )
        raise P0F1Error(
            "P0 rebound Download endpoint changed before rollback intent"
        )
    try:
        return engine.rollback_from_arrival(
            run_dir, prepared, dispatch_current
        )
    except engine.B0F1Error as exc:
        reason = _rollback_preintent_identity_miss_reason(exc)
        if not os.path.lexists(run_dir / "rollback-intent.json") and reason:
            _publish_physical_rebind_miss(
                run_dir,
                prepared,
                arm,
                rebound_confirmation,
                reason,
                None,
            )
        raise


def _confirm_physical_rollback_with_rebind(
    run_dir: Path, confirmation: str
) -> dict[str, Any]:
    require_active()
    prepared = engine.read_prepared(run_dir, phase="rollback")
    engine.require_all_transfer_processes_quiescent(
        run_dir, prepared["binding_sha256"]
    )
    if os.path.lexists(run_dir / P0_PHYSICAL_REBIND_ARM_NAME):
        return _confirm_rebound_physical_rollback(
            run_dir, prepared, confirmation
        )
    if os.path.lexists(run_dir / "physical-confirmation-intent.json"):
        raise P0F1Error(
            "P0 physical rollback rebind must be armed before confirmation"
        )
    try:
        return _ENGINE_CONFIRM_PHYSICAL_ROLLBACK(run_dir, confirmation)
    except engine.B0F1Error as exc:
        if str(exc) != "physical rollback endpoint changed":
            raise
        if not os.path.lexists(run_dir / "physical-confirmation-intent.json"):
            raise P0F1Error(
                "P0 physical endpoint changed without consumed confirmation"
            ) from exc
        return {
            "schema": "s20plus_g986n_p0_recovery_pending_v1",
            "run_dir": str(run_dir),
            "binding_sha256": prepared["binding_sha256"],
            "verdict": "PHYSICAL_DOWNLOAD_REENUM_REQUIRES_ARM",
            "next_mode": "--arm-physical-rollback",
            "candidate_replay_permitted": False,
            "rollback_replay_permitted": False,
        }


def _make_execution_dependency_replacements() -> dict[str, tuple[Any, str, Any]]:
    def live_only(original, label: str):
        def guarded(*args, **kwargs):
            require_active()
            _require_live_transaction()
            return original(*args, **kwargs)

        guarded.__name__ = f"p0_dependency_{label}"
        return guarded

    def deny_unused(label: str):
        def denied(*_args, **_kwargs):
            raise P0F1Error(f"P0 lease forbids direct unused helper: {label}")

        denied.__name__ = f"p0_denied_{label}"
        return denied

    replacements = {
        "base.bounded_command": (
            engine.base,
            "bounded_command",
            _build_base_command_capability(engine.base.bounded_command),
        ),
        "base.collect": (
            engine.base,
            "collect",
            deny_unused("base_collect"),
        ),
        "base.allocate_run_dir": (
            engine.base,
            "allocate_run_dir",
            deny_unused("base_allocate_run_dir"),
        ),
        "base.durable_write": (
            engine.base,
            "durable_write",
            deny_unused("base_durable_write"),
        ),
        "base.arm_intent": (
            engine.base,
            "arm_intent",
            deny_unused("base_arm_intent"),
        ),
        "base._fsync_dir": (
            engine.base,
            "_fsync_dir",
            deny_unused("base_fsync_dir"),
        ),
        "base.main": (
            engine.base,
            "main",
            deny_unused("base_main"),
        ),
        "raw_capture.acquire_command": (
            engine.raw_capture,
            "acquire_command",
            _RAW_CAPABILITY_REPLACEMENTS["acquire_command"],
        ),
        "raw_capture.RawCaptureWriter": (
            engine.raw_capture,
            "RawCaptureWriter",
            _RAW_CAPABILITY_REPLACEMENTS["RawCaptureWriter"],
        ),
        "raw_capture.publish_captured_bytes": (
            engine.raw_capture,
            "publish_captured_bytes",
            _RAW_CAPABILITY_REPLACEMENTS["publish_captured_bytes"],
        ),
        "raw_capture.prepare_capture_dir": (
            engine.raw_capture,
            "prepare_capture_dir",
            _RAW_CAPABILITY_REPLACEMENTS["prepare_capture_dir"],
        ),
        "raw_capture._direct_directory": (
            engine.raw_capture,
            "_direct_directory",
            _RAW_CAPABILITY_REPLACEMENTS["_direct_directory"],
        ),
        "raw_capture._open_stream": (
            engine.raw_capture,
            "_open_stream",
            _RAW_CAPABILITY_REPLACEMENTS["_open_stream"],
        ),
        "raw_capture._write_all": (
            engine.raw_capture,
            "_write_all",
            _RAW_CAPABILITY_REPLACEMENTS["_write_all"],
        ),
        "raw_capture._durable_create": (
            engine.raw_capture,
            "_durable_create",
            _RAW_CAPABILITY_REPLACEMENTS["_durable_create"],
        ),
        "raw_capture._fsync_dir": (
            engine.raw_capture,
            "_fsync_dir",
            _RAW_CAPABILITY_REPLACEMENTS["_fsync_dir"],
        ),
        "engine.durable_json": (
            engine,
            "durable_json",
            live_only(engine.durable_json, "engine_durable_json"),
        ),
        "engine._atomic_publish_at": (
            engine,
            "_atomic_publish_at",
            live_only(engine._atomic_publish_at, "engine_atomic_publish_at"),
        ),
        "transport.execute_odin_boot_only": (
            engine.transport,
            "execute_odin_boot_only",
            deny_unused("transport_execute_odin_boot_only"),
        ),
        "boot_verify.decompress_lz4": (
            engine.transport.boot_verify,
            "decompress_lz4",
            _guarded_host_or_live_alias(
                engine.transport.boot_verify.decompress_lz4,
                "boot_verify_decompress_lz4",
            ),
        ),
        "boot_verify.run_avbtool": (
            engine.transport.boot_verify,
            "run_avbtool",
            _guarded_host_or_live_alias(
                engine.transport.boot_verify.run_avbtool,
                "boot_verify_run_avbtool",
            ),
        ),
        "registry._append": (
            registry,
            "_append",
            _REGISTRY_INTERNAL_REPLACEMENTS["_append"],
        ),
        "registry._write_no_replace": (
            registry,
            "_write_no_replace",
            _REGISTRY_INTERNAL_REPLACEMENTS["_write_no_replace"],
        ),
        "registry._write_head": (
            registry,
            "_write_head",
            _REGISTRY_INTERNAL_REPLACEMENTS["_write_head"],
        ),
        "registry._writer": (
            registry,
            "_writer",
            _REGISTRY_INTERNAL_REPLACEMENTS["_writer"],
        ),
        "observer.read_attr": (
            observer,
            "read_attr",
            live_only(observer.read_attr, "observer_read_attr"),
        ),
        "observer.optional_attr": (
            observer,
            "optional_attr",
            live_only(observer.optional_attr, "observer_optional_attr"),
        ),
    }
    return replacements


_EXECUTION_DEPENDENCY_REPLACEMENTS = _make_execution_dependency_replacements()
del _build_base_command_capability
del _RAW_CAPABILITY_REPLACEMENTS
del _REGISTRY_INTERNAL_REPLACEMENTS


_ENGINE_LIVE_NAMES = (
    "allocate_run_dir",
    "validate_run_dir",
    "read_prepared",
    "adb_inventory",
    "adb_devpath",
    "resident_health_once",
    "enumerate_download",
    "download_baseline",
    "endpoint_stat",
    "identify_download",
    "wait_download",
    "adb_reboot_download_capture",
    "preflight_odin_dispatch",
    "execute_odin_exact",
    "quiesce_process_cage",
    "require_transfer_process_quiescence",
    "require_all_transfer_processes_quiescent",
    "recovery_probe",
    "revalidate_rollback_source",
    "enter_rollback_download",
    "bind_existing_download",
    "publish_physical_observation_miss",
    "publish_terminal_from_final",
    "publish_abort_terminal",
    "derive_abort_return_result",
    "final_health_and_terminal",
    "rollback_from_arrival",
    "payload_free_return",
    "acquire_guard",
    "guard_present",
    "require_guard",
    "_read_guard_at",
    "release_guard",
    "_bounded_odin_listing",
    "_write_host_control",
    "_quiesce_transient_cgroup",
    "_remove_stale_bounded_cgroup",
    "validate_process_cage_capability",
    "_read_small",
    "_read_bounded_host_file",
    "_host_boot_id",
    "_current_cgroup_parent",
    "_cgroup_identity",
    "_cgroup_populated",
)
_ENGINE_LIVE_REPLACEMENTS = {
    name: _guarded_live_alias(getattr(engine, name), f"engine_{name}")
    for name in _ENGINE_LIVE_NAMES
}


def _guarded_identify_download(original):
    def guarded():
        require_active()
        _require_live_transaction()
        try:
            return original()
        except OSError as exc:
            raise engine.B0F1Error("P0 Download identity is unproved") from exc

    guarded.__name__ = "p0_guarded_engine_identify_download"
    guarded.__qualname__ = guarded.__name__
    return guarded


def _guarded_endpoint_stat(original):
    def guarded(path: str):
        require_active()
        _require_live_transaction()
        try:
            return original(path)
        except OSError as exc:
            raise engine.B0F1Error("P0 Download identity is unproved") from exc

    guarded.__name__ = "p0_guarded_engine_endpoint_stat"
    guarded.__qualname__ = guarded.__name__
    return guarded


_ENGINE_LIVE_REPLACEMENTS["identify_download"] = _guarded_identify_download(
    engine.identify_download
)
_ENGINE_LIVE_REPLACEMENTS["endpoint_stat"] = _guarded_endpoint_stat(
    engine.endpoint_stat
)
_ENGINE_LIVE_REPLACEMENTS["adb_inventory"] = _build_adb_inventory_capability(
    engine.adb_inventory
)
del _build_adb_inventory_capability


def _make_allocate_run_dir_replacement(original, bind_run_dir):
    def replacement(*args, **kwargs):
        require_active()
        transaction = _require_live_transaction()
        if transaction.get("run_dir") is not None:
            raise P0F1Error("P0 live transaction already owns a run")
        run_dir = original(*args, **kwargs)
        if run_dir.parent != RUN_ROOT:
            raise P0F1Error("P0 allocated run escaped its fixed root")
        bind_run_dir(run_dir)
        return run_dir

    replacement.__name__ = "p0_allocate_run_dir"
    return replacement


_ENGINE_LIVE_REPLACEMENTS["allocate_run_dir"] = _make_allocate_run_dir_replacement(
    engine.allocate_run_dir, _bind_live_run_dir
)
del _bind_live_run_dir
_ENGINE_LIVE_REPLACEMENTS["preflight_odin_dispatch"] = (
    _P0_PREFLIGHT_ODIN_DISPATCH
)
_ENGINE_LIVE_REPLACEMENTS["_bounded_odin_listing"] = _p0_bounded_odin_listing
for _host_or_live_name in (
    "_write_host_control",
    "_quiesce_transient_cgroup",
    "_remove_stale_bounded_cgroup",
    "validate_process_cage_capability",
    "_read_bounded_host_file",
    "_host_boot_id",
    "_current_cgroup_parent",
    "_cgroup_identity",
    "_cgroup_populated",
):
    _ENGINE_LIVE_REPLACEMENTS[_host_or_live_name] = _guarded_host_or_live_alias(
        getattr(engine, _host_or_live_name), f"engine_{_host_or_live_name}"
    )


def _entrypoint_run(name: str, args: tuple[Any, ...]) -> Path | None:
    if name == "prepare":
        return None
    if not args:
        raise P0F1Error(f"P0 {name} lacks its run directory")
    run_dir = Path(args[0]).absolute()
    if run_dir.parent != RUN_ROOT:
        raise P0F1Error(f"P0 {name} run escaped its fixed root")
    return run_dir


_ENGINE_ENTRYPOINT_ORIGINALS = {
    name: getattr(engine, name)
    for name in (
        "prepare",
        "execute",
        "resume_run",
        "arm_physical_rollback",
        "confirm_physical_rollback",
        "finalize_resident",
        "abort_pre_candidate",
    )
}
_ENGINE_ENTRYPOINT_ORIGINALS["arm_physical_rollback"] = (
    _arm_physical_rollback_with_rebind
)
_ENGINE_ENTRYPOINT_ORIGINALS["confirm_physical_rollback"] = (
    _confirm_physical_rollback_with_rebind
)
_ENGINE_ENTRYPOINT_REPLACEMENTS = {
    name: _build_entrypoint_capability(
        name,
        original,
        require_active,
        _entrypoint_run,
        _reconcile_orphan_process_cages,
    )
    for name, original in _ENGINE_ENTRYPOINT_ORIGINALS.items()
}
_read_prepared_for_output = _build_prepare_output_capability(
    engine.read_prepared,
    require_active,
    _reconcile_orphan_process_cages,
)
del _build_entrypoint_capability
del _build_prepare_output_capability


def _profile_function_replacements() -> dict[str, Any]:
    return {
        **_ENGINE_LIVE_REPLACEMENTS,
        **_ENGINE_ENTRYPOINT_REPLACEMENTS,
        "require_active": require_active,
        "validate_manifest": validate_manifest,
        "validate_host_closure": validate_host_closure,
        "validate_rollback_closure": validate_rollback_closure,
        "validate_health_closure": validate_health_closure,
        "ensure_private_roots": ensure_private_roots,
        "candidate_claim_present": candidate_claim_present,
        "consume_candidate_globally": consume_candidate_globally,
        "require_candidate_claim": require_candidate_claim,
        "_candidate_claim_intent": _ENGINE_CANDIDATE_CLAIM_INTENT,
        "prepare_process_cage": _P0_PREPARE_PROCESS_CAGE,
        "_validate_process_cage_binding": _validate_p0_engine_cage_binding,
        "_validate_process_cage_quiescence": _validate_p0_engine_cage_quiescence,
        "transfer_boot": _P0_TRANSFER_BOOT,
        "observe_candidate": observe_candidate,
        "_validate_candidate_observation": validate_candidate_observation,
        "validate_namespace": validate_namespace,
        "derive_terminal_verdict": derive_terminal_verdict,
        "render_plan": render_plan,
    }


def _install_profile() -> None:
    for module, attribute, replacement in _EXECUTION_DEPENDENCY_REPLACEMENTS.values():
        setattr(module, attribute, replacement)
    engine._BOUND_APIS["inventory.bounded_command"] = (
        _EXECUTION_DEPENDENCY_REPLACEMENTS["base.bounded_command"][2]
    )
    engine._BOUND_APIS["raw_capture.acquire_command"] = (
        _EXECUTION_DEPENDENCY_REPLACEMENTS["raw_capture.acquire_command"][2]
    )
    for name, value in _OBSERVER_LIVE_REPLACEMENTS.items():
        setattr(observer, name, value)
    for name, value in _REGISTRY_MUTATION_REPLACEMENTS.items():
        setattr(registry, name, value)
    for name, value in _profile_value_replacements().items():
        setattr(engine, name, value)
    for name, value in _profile_function_replacements().items():
        setattr(engine, name, value)


_install_profile()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--render-plan", action="store_true")
    modes.add_argument("--validate-host", action="store_true")
    modes.add_argument("--prepare", action="store_true")
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--resume", action="store_true")
    modes.add_argument("--arm-physical-rollback", action="store_true")
    modes.add_argument("--confirm-physical-rollback", action="store_true")
    modes.add_argument("--finalize-resident", action="store_true")
    modes.add_argument("--abort-pre-candidate", action="store_true")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--approval")
    parser.add_argument("--confirmation")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.render_plan:
        print(json.dumps(render_plan(), sort_keys=True))
        return 0
    if args.validate_host:
        try:
            closure = validate_host_closure()
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "schema": PLAN_SCHEMA,
                        "verdict": "STOP_P0_HOST_CLOSURE",
                        "failure_class": type(exc).__name__,
                        "live_authority": False,
                    },
                    sort_keys=True,
                )
            )
            return 2
        print(
            json.dumps(
                {
                    "schema": PLAN_SCHEMA,
                    "verdict": "PASS_P0_HOST_CLOSURE_ONLY",
                    "closure_sha256": engine.digest(closure),
                    "live_authority": False,
                },
                sort_keys=True,
            )
        )
        return 0
    if P0_F1_ACTIVE is not True or observer.OBSERVER_ACTIVE is not True:
        print("STOP_S20PLUS_G986N_P0_PID1_ODIN_F1_NOT_ACTIVE")
        return 3
    try:
        if args.prepare:
            run_dir = engine.prepare(args.run_dir)
            prepared = _read_prepared_for_output(run_dir)
            print(f"run_dir={run_dir}")
            print(f"approval={prepared['approval_token']}")
            return 0
        if args.run_dir is None:
            raise P0F1Error("--run-dir is required")
        run_dir = args.run_dir.absolute()
        if args.execute:
            result = engine.execute(run_dir, args.approval or "")
        elif args.resume:
            result = engine.resume_run(run_dir)
        elif args.arm_physical_rollback:
            result = engine.arm_physical_rollback(run_dir)
        elif args.confirm_physical_rollback:
            result = engine.confirm_physical_rollback(
                run_dir, args.confirmation or ""
            )
        elif args.finalize_resident:
            result = engine.finalize_resident(run_dir)
        else:
            result = engine.abort_pre_candidate(run_dir)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"STOP_P0_F1:{type(exc).__name__}:{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

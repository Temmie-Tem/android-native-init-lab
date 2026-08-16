#!/usr/bin/env python3
"""Exact boot-only A90 H24 resident installer for the existing read-only UFS root.

This runner deliberately has no SD-rootfs staging mode.  It binds one H24 boot
candidate, the exact V2321 boot rollback, the H14 incident's proved V2321
recovery terminal, and the exact read-only userdata inventory.  Live mode
records durable candidate
intent before invoking the reviewed native boot flash helper once.  A candidate
is never replayed; an uncertain post-start result permits only the bound
rollback or a recovery-required park.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import select
import signal
import stat
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
FLAT_BUILDER_DIR = REVAL_DIR / "a90_flat_builder"
for _path in (SCRIPT_DIR, REVAL_DIR, FLAT_BUILDER_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_v3403_absent_only_staging as staging  # noqa: E402
import a90_v3403_f1_orchestrator as base  # noqa: E402
import buildlib as flat_buildlib  # noqa: E402


# Every schema, approval prefix, capability name, and run-id shape below is
# H27's own. Sharing H24's namespace would let two runners write into one
# journal and approval space, and no-replay accounting depends on those being
# disjoint.
SCHEMA = "a90-h27-ufs-f1-manifest-v1"
RESULT_SCHEMA = "a90-h27-ufs-f1-result-v1"
JOURNAL_SCHEMA = "a90-h27-ufs-f1-journal-v1"
QUALIFICATION_SCHEMA = "a90-h27-ufs-execution-qualification-v1"
EXECUTION_REVIEW_SCHEMA = (
    "a90-h27-ufs-f1-execution-independent-review-v1"
)
INVENTORY_SCHEMA = "a90-h27-ufs-readonly-inventory-v1"
APPROVAL_SCHEMA = "a90-h27-ufs-f1-approval-prepared-v1"
APPROVAL_BINDING_SCHEMA = "a90-h27-ufs-f1-approval-binding-v1"
APPROVAL_PREFIX = "A90-H27-F1-APPROVE:"
APPROVAL_TTL_SEC = 1800
D0_MAX_AGE_SEC = 900
CAPABILITY = "A90_H27_SELFBUILT_KERNEL_NOCFP_V1"
RUN_ID_RE = re.compile(r"^a90-h27-ufs-f1-[0-9]{8}-[0-9]{2}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
H24_AUTO_STATUS_RE = re.compile(
    r"^A90AUTO_STATUS binding=(?P<binding>[01]) "
    r"enable=(?P<enable>[01]) latch=(?P<latch>[01]) "
    r"build=(?P<build>[a-z0-9._-]+)$"
)

# NOT YET BOUND. These describe the resident this runner may install over, and
# they were inherited from the H24 runner, where the predecessor was H18. That
# is wrong for H27: GOAL_A90.md names H24 `0.11.192` as the exact installed
# resident. Flashing while the runner validates a predecessor that is not the
# one present is precisely the failure the check exists to prevent.
#
# Rebinding is not a constant swap. The H24 predecessor differs in kind: its D1
# closed `REFUTED_H24_POST_ROOT_FAILURE_ATTRIBUTED_NATIVE_FALLBACK_HEALTHY`,
# whereas the inherited check requires a D1 HEALTHY predecessor. Whether a
# refuted-but-healthy D1 satisfies this precondition is a contract reading --
# A90_TARGET_CONTRACT.md:1276-1279 says a later refutation does not retroactively
# fail an installation -- and it is left to the independent review rather than
# decided here.
#
# The measured H24 values are recorded in the handoff so the reviewer does not
# have to rediscover them; they are deliberately not installed as bindings.
CURRENT_VERSION = "UNSET_PENDING_H27_PREDECESSOR_REBIND"
CURRENT_BUILD = "UNSET_PENDING_H27_PREDECESSOR_REBIND"
CURRENT_BOOT_SIZE = 0
CURRENT_BOOT_SHA256 = "UNSET_PENDING_H27_PREDECESSOR_REBIND"
CURRENT_INSTALL_EXECUTION_CLOSURE_SHA256 = "UNSET_PENDING_H27_PREDECESSOR_REBIND"
# The independent review settled that H24 is an acceptable predecessor: a D1
# refutation does not retroactively fail an installation
# (A90_TARGET_CONTRACT.md:1276-1279). It also required the two terminals be
# combined rather than one substituted for the other, so this binds both.
#
# The F1 terminal proves the resident was installed and is healthy. The D1
# terminal proves the later experiment was refuted, consumed, and left the
# device healthy with no replay and no userdata write.
H24_PREDECESSOR_RUN_REL = (
    "workspace/private/runs/server-distro/a90-h24-ufs-f1-20260812-01"
)
H24_F1_CLOSED_REL = "h24-f1-live/journal/0006-closed.json"
H24_F1_CLOSED_SIZE = 56968
H24_F1_CLOSED_SHA256 = (
    "b35bf31954d523462b073191bdb167d51bb65d9772e7f140ec101366044341f5"
)
H24_F1_CLOSED_STATUS = "PASS_A90_H24_UFS_RESIDENT_INSTALLED"
H24_D1_CLOSED_REL = "h24-d1/run01/0006-closed.json"
H24_D1_CLOSED_SIZE = 83023
H24_D1_CLOSED_SHA256 = (
    "325b3d22c07a1d4d597e43e1f7be590352c5391d6dc7138ce93ba7da0b421c45"
)
H24_D1_CLOSED_STATUS = (
    "REFUTED_H24_POST_ROOT_FAILURE_ATTRIBUTED_NATIVE_FALLBACK_HEALTHY"
)
H24_D1_RECORDS = (
    (
        "0000-open.json",
        115212,
        "d7ece305f1a485649bbdb35b92116a02236deac28524155647314446a1153a6d",
    ),
    (
        "0001-arm-reboot-intent.json",
        1581,
        "ad7926ee5f718d7e1b2f48ca6b0da5e16fd554b51f13f82202d1c3f35a612fdf",
    ),
    (
        "0002-dispatch-result.json",
        4898,
        "f44a21f25917706cd35ac2a44db3748dc3858bf384210e4e22c8c90ecf0477a8",
    ),
    (
        "0003-persistent-observation.json",
        6162,
        "45412849deeb7482e7bb9c4e31945ed348ec3d7473c2716a3246440aaf9da048",
    ),
    (
        "0004-current-state.json",
        7041,
        "6c4ae04eeccc8eb2f4da3f3a7b8fe042d7478422ede5da8c9cf3167206545a47",
    ),
    (
        "0005-final-health.json",
        83029,
        "3e045b9ec203abc29e1113f07ddfe40e79d391177dda0f4657da03ef1298047c",
    ),
    (
        "0006-closed.json",
        83023,
        "325b3d22c07a1d4d597e43e1f7be590352c5391d6dc7138ce93ba7da0b421c45",
    ),
)
CANDIDATE_VERSION = "0.11.194"
CANDIDATE_BUILD = "phase3-minimal-h27-selfbuilt-kernel-nocfp"
CANDIDATE_BOOT_SIZE = 58368000
CANDIDATE_BOOT_SHA256 = (
    "fa7ab8af8cec027c433653da92eb6cb4ca6f3a02d7624a4f292f61906e8ce500"
)
CANDIDATE_INIT_SIZE = 1723376
CANDIDATE_INIT_SHA256 = (
    "7dd00ee2d02e9dfce3ccf9fe5d42e1fb3b0821bcde65978f987d8e1aed62c199"
)
CANDIDATE_RAMDISK_SIZE = 8537600
CANDIDATE_RAMDISK_SHA256 = (
    "3782548f01f19f54ca45e6e23f7673cb7b31160d22f828e9c15e55382dd05c4c"
)
CANDIDATE_HELPER_SIZE = 1649904
CANDIDATE_HELPER_SHA256 = (
    "fcb005b0454aceb08aa6f8f81d83aa303e37199a56e018eb2501e4225f08e00e"
)
CANDIDATE_AB_RECEIPT_SHA256 = (
    "3a3f12534543f9481f8a30571cab067714ec45fd12099c4ee1e6111311f24045"
)
CANDIDATE_AB_RECEIPT_SIZE = 5426
CANDIDATE_MANIFEST_SHA256 = (
    "b4cfa428da868724450f1db617143626417c2880452f3f8d0485839bb5b8fd3c"
)
CANDIDATE_EFFECTIVE_MANIFEST_SHA256 = (
    "6516f3ea3fd09878695c9ca957840afe30ac3e570095d891692acea9e86848c7"
)
# The self-built kernel is what this candidate exists to test. It is pinned
# here so the runner refuses any boot image that does not carry it, and so the
# reduced RKP CFP posture is visible at the binding rather than only in prose.
CANDIDATE_KERNEL_IMAGE_SHA256 = (
    "6cab67938d2d235ad5ad965abaefe7e3ebda6d13b57251705c91f5f333ab1b6d"
)
CANDIDATE_KERNEL_RKP_CFP_DISABLED = True
ROLLBACK_VERSION = "0.9.285"
ROLLBACK_BUILD = "v2321-usb-clean-identity-rodata"
ROLLBACK_SIZE = 60882944
ROLLBACK_SHA256 = (
    "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
)
UFS_IDENTITY = {
    "devname": "sda33",
    "devt_policy": "runtime-resolved-same-session",
    "sectors": "231577432",
    "partname": "userdata",
    "filesystem": "ext4",
    "uuid": "300aaf21-412c-4238-9106-56414eaab105",
    "label": "A90D4ROOT",
    "marker": "userdata=appliance-root",
    "mount_policy": "ro,noload,nosuid,nodev",
}
ENABLE_PATH = "/cache/a90-auto-handoff-phase3-minimal-h27.enable"
LATCH_PATH = "/cache/a90-auto-handoff-phase3-minimal-h27.done"
# A90_TARGET_CONTRACT.md:320-324,394-396 -- a replacement candidate never reuses
# a prior enable/latch pair. The H24 pair must stay absent for this candidate,
# and is listed so the runner can prove absence rather than assume it.
FORBIDDEN_PRIOR_STATE_PATHS = (
    "/cache/a90-auto-handoff-phase3-minimal-h24.enable",
    "/cache/a90-auto-handoff-phase3-minimal-h24.done",
)
CONTENT_REL = (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "phase3-minimal-h14/userdata-content-manifest.json"
)
VERSION_MANIFEST_REL = (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "phase3-minimal-h27/manifest.toml"
)
TARGET_CONTRACT_REL = "docs/operations/targets/A90_TARGET_CONTRACT.md"
NATIVE_FLASH = (REVAL_DIR / "native_init_flash.py").resolve()
PRIVATE_RUN_BASE = (REPO_ROOT / "workspace/private/runs/server-distro").resolve()
INPUT_MODE = "slow"
INPUT_CHAR_DELAY_SEC = 0.02
EXACT_BRIDGE_DEVICE = (
    "/dev/serial/by-id/usb-A90-LNX_A90_Linux_ARM64_A90NATIVE001-if00"
)
NATIVE_CLOSURE_SHA256 = (
    "3d1514e3f266e5b77886bf4511a396c9328b487b0c614c3c79fd3df16d26ca52"
)
# NOT YET PRODUCED. The four constants below bind an independent capability
# review that does not exist for H27. They are declared so this runner fails
# closed at `resolve(strict=True)` rather than silently inheriting H24's review.
#
# H24's review does not transfer. AGENTS.md:187-191 requires an independent
# review when the runner, hazard, or closure changes, and H27 changes the
# kernel, the builder manifest, the candidate hash, and -- through the disabled
# RKP CFP -- the device's exploit-mitigation posture.
#
# The closure digest, reviewer, and invariant list must come from that review's
# own report. They are deliberately left unfilled: writing plausible values here
# would forge the gate that exists to catch authoring errors.
H27_REVIEW_DATE = "UNSET_PENDING_H27_CAPABILITY_REVIEW"
HOST_CAPABILITY_CLOSURE_SHA256 = "UNSET_PENDING_H27_CAPABILITY_REVIEW"
HOST_QUALIFICATION_REL = (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "phase3-minimal-h27/capability-qualification.json"
)
HOST_REVIEW_REPORT_REL = (
    "docs/reports/A90_H27_SELFBUILT_KERNEL_CAPABILITY_INDEPENDENT_REVIEW.json"
)
HOST_CAPABILITY_REVIEWER = "UNSET_PENDING_H27_CAPABILITY_REVIEW"
HOST_CAPABILITY_SCOPE = "h27-selfbuilt-kernel-nocfp-capability"
HOST_CAPABILITY_INCIDENT = "UNSET_PENDING_H27_CAPABILITY_REVIEW"
# Each string here is a finding an independent reviewer signed, which this
# runner then cross-checks against the review report. They are the reviewer's
# words, not the author's, so the tuple stays empty until that review exists.
# An empty tuple is not a permissive default: validate_host_capability_
# qualification() rejects it, so the runner cannot start.
HOST_CAPABILITY_REQUIRED_INVARIANTS: tuple[str, ...] = ()
# NOT YET PRODUCED, for the same reason as the capability review above. The
# H24 execution review is scoped to the H24 runner and cannot cover this one.
EXECUTION_REVIEW_REPORT_REL = (
    "docs/reports/A90_H27_SELFBUILT_KERNEL_EXECUTION_INDEPENDENT_REVIEW.json"
)
EXECUTION_REVIEWER = "UNSET_PENDING_H27_EXECUTION_REVIEW"
EXECUTION_REVIEW_SCOPE = (
    "h27-selfbuilt-kernel-nocfp-boot-only-f1-execution-critical-closure"
)
EXECUTION_REVIEW_INCIDENT = "UNSET_PENDING_H27_EXECUTION_REVIEW"
EXECUTION_REVIEW_REQUIRED_INVARIANTS: tuple[str, ...] = ()
FIRSTBOOT_REL = "workspace/public/src/scripts/server-distro/a90_dpublic_firstboot.sh"

EXECUTION_SOURCE_RELS = (
    "AGENTS.md",
    "workspace/public/src/scripts/server-distro/a90_h27_ufs_f1_runner_v1.py",
    FIRSTBOOT_REL,
    "workspace/public/src/scripts/server-distro/a90_auto_handoff_benchmark_runner_v1.py",
    "workspace/public/src/scripts/server-distro/a90_boot_benchmark_v1.py",
    "workspace/public/src/scripts/server-distro/a90_ondevice_evidence_v1.py",
    "workspace/public/src/scripts/server-distro/a90_phase3_d1_observer_v1.py",
    "workspace/public/src/scripts/server-distro/a90_phase2d_connected_preflight.py",
    "workspace/public/src/scripts/server-distro/a90_phase2d_display_observer.py",
    "workspace/public/src/scripts/server-distro/a90_h5_existing_source_install_v1.py",
    "workspace/public/src/scripts/server-distro/a90_resident_existing_rootfs_install_v1.py",
    "workspace/public/src/scripts/server-distro/a90_resident_preserved_d1_prep_v1.py",
    "workspace/public/src/scripts/server-distro/a90_resident_promotion_v1.py",
    "workspace/public/src/scripts/server-distro/a90_transition_d1_session_v1.py",
    "workspace/public/src/scripts/server-distro/a90_transition_engine_v2.py",
    "workspace/public/src/scripts/server-distro/a90_v3403_f1_orchestrator.py",
    "workspace/public/src/scripts/server-distro/a90_v3403_absent_only_staging.py",
    "workspace/public/src/scripts/server-distro/a90_v3405_retained_work_cleanup.py",
    "workspace/public/src/scripts/server-distro/run_d1_chroot_mvp.py",
    "workspace/public/src/scripts/revalidation/a90ctl.py",
    "workspace/public/src/scripts/revalidation/a90_bridge.py",
    "workspace/public/src/scripts/revalidation/a90_observation_pipeline.py",
    "workspace/public/src/scripts/revalidation/a90_serial_lock.py",
    "workspace/public/src/scripts/revalidation/a90_transition_contract_v2.py",
    "workspace/public/src/scripts/revalidation/_workspace_bootstrap.py",
    "workspace/public/src/scripts/revalidation/serial_tcp_bridge.py",
    "workspace/public/src/scripts/revalidation/device_action_cdc_acm_observer_v1.py",
    "workspace/public/src/scripts/revalidation/native_init_flash.py",
    TARGET_CONTRACT_REL,
    VERSION_MANIFEST_REL,
    HOST_QUALIFICATION_REL,
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "v3404-effective/manifest.toml",
    CONTENT_REL,
    "workspace/public/src/native-init/a90_config.h",
    "workspace/public/src/native-init/a90_auto_handoff.c",
    "workspace/public/src/native-init/a90_server_distro.h",
    "workspace/public/src/native-init/a90_server_distro.c",
    "workspace/public/src/scripts/revalidation/a90_flat_builder/build.py",
    "workspace/public/src/scripts/revalidation/a90_flat_builder/buildlib.py",
)


class ContractError(RuntimeError):
    """Raised before widening, replaying, or misclassifying an H24 effect."""


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def parse_utc(value: Any, label: str) -> dt.datetime:
    if not isinstance(value, str):
        raise ContractError(f"{label} is not an exact UTC timestamp")
    try:
        parsed = dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=dt.UTC
        )
    except ValueError as exc:
        raise ContractError(f"{label} is not an exact UTC timestamp") from exc
    return parsed


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_sha256(value: Any) -> str:
    body = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_json_exclusive(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}-{time.time_ns()}")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        payload = _json_bytes(value)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise ContractError("short private JSON write")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.link(temporary, path, follow_symlinks=False)
        _fsync_dir(path.parent)
    except FileExistsError as exc:
        raise ContractError(f"refusing to replace durable file: {path}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def require_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise ContractError(f"{label} is not one lowercase SHA256")
    return value


def require_regular(path: Path, *, size: int, sha256: str) -> None:
    lexical = path.absolute()
    if lexical.is_symlink():
        raise ContractError(f"bound path is a symlink: {path}")
    resolved = lexical.resolve(strict=True)
    info = resolved.stat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_size != size
        or sha256_file(resolved) != sha256
    ):
        raise ContractError(f"bound regular file changed: {path}")


def bound_file(path: Path) -> dict[str, Any]:
    lexical = path.absolute()
    if lexical.is_symlink():
        raise ContractError(f"bound path is a symlink: {path}")
    resolved = lexical.resolve(strict=True)
    info = resolved.stat()
    if not stat.S_ISREG(info.st_mode):
        raise ContractError(f"bound path is not regular: {path}")
    return {
        "path": str(resolved),
        "size": info.st_size,
        "sha256": sha256_file(resolved),
    }


def resolve_regular_input(path: Path, label: str) -> Path:
    lexical = path.absolute()
    if lexical.is_symlink():
        raise ContractError(f"{label} is a symlink")
    resolved = lexical.resolve(strict=True)
    if not stat.S_ISREG(resolved.stat().st_mode):
        raise ContractError(f"{label} is not one regular file")
    return resolved


def load_reviewed_ab_receipt(path: Path) -> tuple[Path, dict[str, Any]]:
    resolved = resolve_regular_input(path, "AB receipt")
    if (
        resolved.stat().st_size != CANDIDATE_AB_RECEIPT_SIZE
        or sha256_file(resolved) != CANDIDATE_AB_RECEIPT_SHA256
    ):
        raise ContractError("H24 reviewed AB receipt changed")
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("H24 AB receipt is not exact JSON") from exc
    if not isinstance(value, dict):
        raise ContractError("H24 AB receipt is not an object")
    return resolved, value


def require_reviewed_ab_receipt_binding(value: Any) -> None:
    if (
        not isinstance(value, dict)
        or set(value) != {"path", "size", "sha256"}
        or value.get("size") != CANDIDATE_AB_RECEIPT_SIZE
        or value.get("sha256") != CANDIDATE_AB_RECEIPT_SHA256
    ):
        raise ContractError("H24 live AB receipt is not the reviewed artifact")


def reopen_bound(value: Any, label: str) -> Path:
    if not isinstance(value, dict) or set(value) != {"path", "size", "sha256"}:
        raise ContractError(f"{label} binding shape changed")
    path_value = value.get("path")
    size = value.get("size")
    sha = require_sha(value.get("sha256"), f"{label}.sha256")
    if not isinstance(path_value, str) or type(size) is not int or size <= 0:
        raise ContractError(f"{label} binding is not exact")
    path = Path(path_value)
    require_regular(path, size=size, sha256=sha)
    return path.resolve(strict=True)


def revalidate_post_flash_inputs(
    manifest: dict[str, Any], *, rollback: bool
) -> None:
    kind = "rollback_boot" if rollback else "candidate_boot"
    artifact = manifest.get(kind)
    if not isinstance(artifact, dict):
        raise ContractError(f"post-flash {kind} binding is absent")
    reopen_bound(
        {key: artifact.get(key) for key in ("path", "size", "sha256")},
        f"post-flash {kind}",
    )
    reopen_bound(manifest.get("flash_runner"), "post-flash flash_runner")


def load_json_bound(value: Any, label: str) -> tuple[Path, dict[str, Any]]:
    path = reopen_bound(value, label)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label} is not exact JSON") from exc
    if not isinstance(data, dict):
        raise ContractError(f"{label} JSON root is not an object")
    return path, data


def execution_closure() -> dict[str, Any]:
    version_manifest = (REPO_ROOT / VERSION_MANIFEST_REL).resolve(strict=True)
    resolution = flat_buildlib.resolve_manifest(version_manifest)
    init = resolution.data.get("init")
    if not isinstance(init, dict):
        raise ContractError("H24 native manifest init binding is absent")
    source_root = (REPO_ROOT / str(init.get("source_root") or "")).resolve(
        strict=True
    )
    native_files = flat_buildlib.expanded_closure(
        source_root,
        init.get("sources"),
        init.get("closure_globs"),
    )
    actual_native_closure = flat_buildlib.closure_sha256(
        source_root,
        native_files,
    )
    if (
        init.get("closure_sha256") != NATIVE_CLOSURE_SHA256
        or actual_native_closure != NATIVE_CLOSURE_SHA256
    ):
        raise ContractError("H24 native transitive closure changed")
    files: dict[str, dict[str, Any]] = {}
    digest = hashlib.sha256()
    for relative in sorted(EXECUTION_SOURCE_RELS):
        path = (REPO_ROOT / relative).resolve(strict=True)
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise ContractError(f"execution source is not regular: {relative}")
        sha = sha256_file(path)
        files[relative] = {"size": info.st_size, "sha256": sha}
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(info.st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(sha.encode("ascii"))
        digest.update(b"\0")
    return {"sha256": digest.hexdigest(), "files": files}


def validate_qualification(
    binding: Any,
    closure: dict[str, Any],
) -> dict[str, Any]:
    _, value = load_json_bound(binding, "execution_qualification")
    report_lexical = REPO_ROOT / EXECUTION_REVIEW_REPORT_REL
    if report_lexical.is_symlink():
        raise ContractError("independent execution review is not one regular file")
    report_path = report_lexical.resolve(strict=True)
    if not stat.S_ISREG(report_path.stat().st_mode):
        raise ContractError("independent execution review is not one regular file")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("independent execution review is not exact JSON") from exc
    expected_contacts = {
        "device": 0,
        "dev": 0,
        "usb": 0,
        "network": 0,
        "workspace_private": 0,
        "s22plus_paths": 0,
        "s20plus_paths": 0,
        "file_modifications": 0,
    }
    if (
        not isinstance(report, dict)
        or report.get("schema") != EXECUTION_REVIEW_SCHEMA
        or report.get("capability") != CAPABILITY
        or report.get("verdict") != "PASS_GO"
        or report.get("review_date") != H27_REVIEW_DATE
        or report.get("reviewer") != EXECUTION_REVIEWER
        or report.get("execution_closure_sha256") != closure["sha256"]
        or report.get("execution_file_count") != len(closure["files"])
        or report.get("review_scope") != EXECUTION_REVIEW_SCOPE
        or report.get("incident") != EXECUTION_REVIEW_INCIDENT
        or report.get("new_hazard_or_incident") is not True
        or report.get("findings") != {"high": [], "medium": [], "low": []}
        or report.get("validated_invariants")
        != list(EXECUTION_REVIEW_REQUIRED_INVARIANTS)
        or report.get("review_contacts") != expected_contacts
        or report.get("live_authority") is not False
    ):
        raise ContractError("independent execution review is not current")
    if (
        value.get("schema") != QUALIFICATION_SCHEMA
        or value.get("capability") != CAPABILITY
        or value.get("verdict") != "PASS_GO"
        or value.get("predecessor_capability_closure_sha256")
        != HOST_CAPABILITY_CLOSURE_SHA256
        or value.get("execution_closure_sha256") != closure["sha256"]
        or value.get("execution_hashes") != closure["files"]
        or value.get("review_scope") != EXECUTION_REVIEW_SCOPE
        or value.get("incident") != EXECUTION_REVIEW_INCIDENT
        or value.get("new_hazard_or_incident") is not True
        or value.get("ordinal_requalification_required") is not False
        or value.get("f1_runner_qualified") is not True
        or value.get("d1_runner_qualified") is not False
        or value.get("review_report") != EXECUTION_REVIEW_REPORT_REL
        or value.get("review_report_sha256") != sha256_file(report_path)
        or value.get("live_authority") is not False
    ):
        raise ContractError("independent execution qualification is not current")
    return value


# A90_TARGET_CONTRACT.md:62-71 keeps device safety and experiment proof on
# separate axes, and :102-121 governs which failures may occupy the proof axis:
# only device-attributable evidence may burn an ordinal, a missing, late, or
# malformed observation is NO_PROOF_OBSERVER, and when attribution remains
# unresolved NO_PROOF_OBSERVER is the answer.
#
# A previous version of this file derived the axis from the terminal status
# alone, mapping FAILED_* to REFUTED. That was wrong. Both failure terminals are
# emitted from `except Exception` handlers that also catch host-side parse,
# timeout, and transfer-uncertainty defects, so a status lookup cannot tell a
# device contradiction from an observer defect and would have burned ordinals on
# instrument failures.
#
# Attribution is therefore an input, not an inference. REFUTED requires a caller
# that positively proved a well-formed device response contradicting the health
# predicate. No site in this runner can do that yet -- the handlers discard the
# distinction -- so REFUTED is currently unreachable by construction, and that
# is stated rather than hidden.
PROOF_PROVED = "PROVED"
PROOF_REFUTED = "REFUTED"
PROOF_NO_PROOF_OBSERVER = "NO_PROOF_OBSERVER"
PASS_STATUS = "PASS_A90_H27_UFS_RESIDENT_INSTALLED"


def experiment_proof(status: str, *, device_contradiction: bool = False) -> str:
    """Place a terminal on the experiment-proof axis.

    `device_contradiction` must be True only where the caller proved the device
    reported a well-formed state contradicting the health predicate. Anything
    unresolved stays NO_PROOF_OBSERVER, which freezes new non-recovery device
    effects and never permits candidate replay.
    """
    if status == PASS_STATUS:
        if device_contradiction:
            raise ContractError("a passing install cannot carry a device contradiction")
        return PROOF_PROVED
    if device_contradiction:
        return PROOF_REFUTED
    return PROOF_NO_PROOF_OBSERVER


def validate_experiment_proof(result: dict[str, Any]) -> str:
    """Reject a durable result whose proof axis disagrees with its terminal.

    The axis is only worth recording if a consumer refuses a tampered or
    mismatched pairing; a field nothing checks is decoration.

    A consumer must not trust the producer's discipline. `REFUTED` is the
    terminal that burns an ordinal and forces a no-replay conclusion
    (A90_TARGET_CONTRACT.md:102-121), so a tampered or corrupted result claiming
    it would consume an ordinal on evidence that was never attributed. The
    producer can only emit `REFUTED` with proved device attribution, and today
    no site can prove it, so the consumer rejects it outright rather than
    accepting it on the producer's word.

    When attribution is implemented, this must not simply relax: `REFUTED`
    becomes admissible only once an exact device-attribution receipt is
    persisted in the result and validated here.
    """
    status = result.get("status")
    proof = result.get("experiment_proof")
    if proof not in (PROOF_PROVED, PROOF_REFUTED, PROOF_NO_PROOF_OBSERVER):
        raise ContractError(f"result carries no valid experiment proof axis: {proof!r}")
    if status == PASS_STATUS:
        if proof != PROOF_PROVED:
            raise ContractError("a passing install must record PROVED")
        if result.get("device_safety_state") != "RESIDENT_HEALTHY":
            raise ContractError("a passing install must record RESIDENT_HEALTHY")
        return proof
    if proof == PROOF_PROVED:
        raise ContractError("only a passing install may record PROVED")
    if proof == PROOF_REFUTED:
        raise ContractError(
            "REFUTED requires an exact device-attribution receipt that this "
            "runner cannot yet produce or validate; a durable result may not "
            "claim it"
        )
    return proof


def require_h27_reviews_exist() -> None:
    """Refuse to run while the independent H27 reviews are unwritten.

    A missing qualification file already stops this runner, but absence of a
    file is a weak gate: it disappears the moment somebody creates one. These
    placeholders are the positive statement that no reviewer has signed H27,
    and an empty invariant tuple must never read as "no invariants required".
    """
    unset = [
        name
        for name, value in (
            ("CURRENT_VERSION", CURRENT_VERSION),
            ("CURRENT_BUILD", CURRENT_BUILD),
            ("CURRENT_BOOT_SHA256", CURRENT_BOOT_SHA256),
            ("CURRENT_INSTALL_EXECUTION_CLOSURE_SHA256", CURRENT_INSTALL_EXECUTION_CLOSURE_SHA256),
            ("H27_REVIEW_DATE", H27_REVIEW_DATE),
            ("HOST_CAPABILITY_CLOSURE_SHA256", HOST_CAPABILITY_CLOSURE_SHA256),
            ("HOST_CAPABILITY_REVIEWER", HOST_CAPABILITY_REVIEWER),
            ("HOST_CAPABILITY_INCIDENT", HOST_CAPABILITY_INCIDENT),
            ("EXECUTION_REVIEWER", EXECUTION_REVIEWER),
            ("EXECUTION_REVIEW_INCIDENT", EXECUTION_REVIEW_INCIDENT),
        )
        if str(value).startswith("UNSET_PENDING_")
    ]
    if not HOST_CAPABILITY_REQUIRED_INVARIANTS:
        unset.append("HOST_CAPABILITY_REQUIRED_INVARIANTS")
    if not EXECUTION_REVIEW_REQUIRED_INVARIANTS:
        unset.append("EXECUTION_REVIEW_REQUIRED_INVARIANTS")
    if not CURRENT_BOOT_SIZE:
        unset.append("CURRENT_BOOT_SIZE")
    if not H24_D1_RECORDS or len(H24_D1_RECORDS) != 7:
        unset.append("H24_D1_RECORDS")
    if unset:
        raise ContractError(
            "H27 is not qualified: its independent reviews are unwritten and its "
            "this runner is not qualified for any device effect. Unset bindings: "
            + ", ".join(sorted(unset))
        )


def validate_host_capability_qualification() -> dict[str, Any]:
    require_h27_reviews_exist()
    path = (REPO_ROOT / HOST_QUALIFICATION_REL).resolve(strict=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    execution_hashes = value.get("execution_hashes")
    digest = hashlib.sha256()
    if not isinstance(execution_hashes, dict) or len(execution_hashes) != 24:
        raise ContractError("H24 host capability closure member set changed")
    for relative, expected in sorted(execution_hashes.items()):
        if not isinstance(relative, str) or not isinstance(expected, dict):
            raise ContractError("H24 host capability closure shape changed")
        source = (REPO_ROOT / relative).resolve(strict=True)
        try:
            source.relative_to(REPO_ROOT)
        except ValueError as exc:
            raise ContractError("H24 host capability closure escapes repository") from exc
        info = source.stat()
        sha = sha256_file(source)
        if (
            not stat.S_ISREG(info.st_mode)
            or expected != {"size": info.st_size, "sha256": sha}
        ):
            raise ContractError("H24 host capability execution hash changed")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(info.st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(sha.encode("ascii"))
        digest.update(b"\0")
    review_report = (REPO_ROOT / HOST_REVIEW_REPORT_REL).resolve(strict=True)
    report = json.loads(review_report.read_text(encoding="utf-8"))
    frozen = report.get("frozen_scope") if isinstance(report, dict) else None
    findings = report.get("findings") if isinstance(report, dict) else None
    expected_contacts = {
        "device": 0,
        "dev": 0,
        "usb": 0,
        "network": 0,
        "workspace_private": 0,
        "s22plus_paths": 0,
        "s20plus_paths": 0,
        "file_modifications": 0,
    }
    if (
        not isinstance(value, dict)
        or value.get("schema")
        != "a90-h27-selfbuilt-kernel-capability-qualification-v1"
        or value.get("capability")
        != "A90_H27_SELFBUILT_KERNEL_NOCFP_V1"
        or value.get("verdict") != "PASS_GO"
        or value.get("execution_closure_sha256")
        != HOST_CAPABILITY_CLOSURE_SHA256
        or digest.hexdigest() != HOST_CAPABILITY_CLOSURE_SHA256
        or value.get("native_init_closure_sha256") != NATIVE_CLOSURE_SHA256
        or value.get("native_init_closure_members") != 142
        or value.get("review_scope")
        != HOST_CAPABILITY_SCOPE
        or value.get("incident_class")
        != HOST_CAPABILITY_INCIDENT
        or value.get("new_hazard_or_incident") is not True
        or value.get("ordinal_requalification_required") is not False
        or value.get("f1_runner_qualified") is not False
        or value.get("d1_runner_qualified") is not False
        or value.get("review_report") != HOST_REVIEW_REPORT_REL
        or value.get("review_report_sha256") != sha256_file(review_report)
        or value.get("live_authority") is not False
        or not isinstance(report, dict)
        or report.get("schema")
        != "a90-h27-selfbuilt-kernel-independent-review-v1"
        or report.get("status") != "PASS_GO"
        or report.get("review_date") != H27_REVIEW_DATE
        or report.get("reviewer") != HOST_CAPABILITY_REVIEWER
        or report.get("capability")
        != "A90_H27_SELFBUILT_KERNEL_NOCFP_V1"
        or report.get("incident_class") != HOST_CAPABILITY_INCIDENT
        or report.get("validated_invariants")
        != list(HOST_CAPABILITY_REQUIRED_INVARIANTS)
        or not isinstance(frozen, dict)
        or frozen.get("execution_closure_sha256") != HOST_CAPABILITY_CLOSURE_SHA256
        or frozen.get("execution_closure_members") != 24
        or frozen.get("native_init_closure_sha256") != NATIVE_CLOSURE_SHA256
        or frozen.get("native_init_closure_members") != 142
        or frozen.get("candidate_boot_sha256") != CANDIDATE_BOOT_SHA256
        or frozen.get("candidate_boot_bytes") != CANDIDATE_BOOT_SIZE
        or frozen.get("candidate_init_sha256") != CANDIDATE_INIT_SHA256
        or frozen.get("candidate_init_bytes") != CANDIDATE_INIT_SIZE
        or frozen.get("ramdisk_sha256") != CANDIDATE_RAMDISK_SHA256
        or frozen.get("ramdisk_bytes") != CANDIDATE_RAMDISK_SIZE
        or frozen.get("helper_sha256") != CANDIDATE_HELPER_SHA256
        or frozen.get("helper_bytes") != CANDIDATE_HELPER_SIZE
        or frozen.get("ab_receipt_sha256") != CANDIDATE_AB_RECEIPT_SHA256
        or frozen.get("ab_receipt_bytes") != CANDIDATE_AB_RECEIPT_SIZE
        or frozen.get("manifest_sha256") != CANDIDATE_MANIFEST_SHA256
        or frozen.get("effective_manifest_sha256")
        != CANDIDATE_EFFECTIVE_MANIFEST_SHA256
        or frozen.get("compiled_binding_sha256")
        != "02b9ffb16e16a4545520c01aa0010cf1a1ecb3419a98def962a0b3a4d7994582"
        or findings
        != {"final_high": 0, "final_medium": 0, "final_low": 0, "unresolved": []}
        or report.get("review_contacts") != expected_contacts
        or report.get("device_authority_granted") is not False
    ):
        raise ContractError("H24 host capability qualification changed")
    return value


def validate_ufs_inventory(
    value: dict[str, Any],
    *,
    expected_run_id: str,
    expected_bridge_realpath: str,
    enforce_fresh: bool,
    now: dt.datetime | None = None,
) -> None:
    observed_devt = value.get("observed_devt")
    observed_at = parse_utc(value.get("timestamp_utc"), "UFS inventory timestamp")
    current = now or dt.datetime.now(dt.UTC)
    provenance = value.get("provenance")
    expected_marker = (
        f"A90H24_D0 exact=1 devt={observed_devt} "
        "devt_policy=same-session-only ufs_mounted=0 "
        "enable_absent=1 latch_absent=1 userdata_write=0"
    )
    if (
        value.get("schema") != INVENTORY_SCHEMA
        or value.get("status") != "PASS"
        or value.get("run_id") != expected_run_id
        or (
            enforce_fresh
            and (
                current < observed_at
                or (current - observed_at).total_seconds() > D0_MAX_AGE_SEC
            )
        )
        or value.get("target") != "Samsung Galaxy A90 5G"
        or value.get("identity") != UFS_IDENTITY
        or not isinstance(observed_devt, str)
        or re.fullmatch(r"[0-9]+:[0-9]+", observed_devt) is None
        or value.get("devt_stability") != "same-session-only"
        or value.get("content_manifest_sha256")
        != "e1950058627446d6bbd487d6a17b80f5766be4956b54cb56659b541dab09f8f6"
        or value.get("content_file_count") != 19
        or value.get("secrets_hashed") is not False
        or value.get("public_tunnel") != "disabled"
        or value.get("mounted_read_only") is not True
        or value.get("mounted_norecovery") is not True
        or value.get("mounted_after") is not False
        or value.get("userdata_write_count") != 0
        or value.get("format_count") != 0
        or value.get("repair_count") != 0
        or value.get("s22plus_command_count") != 0
        or value.get("s20plus_command_count") != 0
        or not isinstance(provenance, dict)
        or provenance.get("fresh_d0_bridge") != EXACT_BRIDGE_DEVICE
        or provenance.get("fresh_d0_bridge_realpath")
        != expected_bridge_realpath
        or provenance.get("fresh_d0_version") != CURRENT_VERSION
        or provenance.get("fresh_d0_build") != CURRENT_BUILD
        or provenance.get("fresh_d0_selftest") != "pass=11 warn=1 fail=0"
        or provenance.get("fresh_d0_ufs_marker") != expected_marker
    ):
        raise ContractError("read-only UFS inventory is not exact")


def expected_compiled_binding() -> dict[str, Any]:
    expected_binding = {
        "candidate_version": CANDIDATE_VERSION,
        "candidate_build": CANDIDATE_BUILD,
        "enable_path": ENABLE_PATH,
        "latch_path": LATCH_PATH,
        "schema": "a90-compiled-auto-handoff-binding-v11",
        "observer_auth": "boot-private-tmpfs-v1",
        "display_owner": "native-handoff-hud-v1",
        "firstboot_overlay": "disabled",
        "firstboot_source": "ufs-existing-immutable-v1",
        "persistent_native_hud": "enabled",
        "hud_drm_acquisition": "deferred-until-ufs-intent-v3",
        "hud_drm_device_access": "private-pivot-root-card0-bind-v1",
        "hud_mount_namespace": "private-minimal-card-root-v1",
        "hud_device_exposure": "card0-only-no-userdata-v1",
        "debian_dev_tree_exposure": "minimal-core-char-no-drm-no-userdata-v1",
        "debian_proc_hud_root_exposure": (
            "card0-and-shared-public-run-no-block-no-userdata-v1"
        ),
        "ufs_firstboot_cleanup_compatibility": "zero-pre-intent-drm-fd-v3",
        "root_kind": "userdata-ext4-ro-noload",
        "userdata_devname": UFS_IDENTITY["devname"],
        "userdata_devt_policy": UFS_IDENTITY["devt_policy"],
        "userdata_sectors": UFS_IDENTITY["sectors"],
        "userdata_label": UFS_IDENTITY["label"],
        "userdata_marker": UFS_IDENTITY["marker"],
        "userdata_uuid": UFS_IDENTITY["uuid"],
        "userdata_content_manifest": CONTENT_REL,
        "userdata_content_manifest_file_sha256": (
            "a878f6dec82bf799c3d2cd43beeda3c5494a8882ce116327f497d822b707d5ce"
        ),
        "userdata_content_manifest_sha256": (
            "e1950058627446d6bbd487d6a17b80f5766be4956b54cb56659b541dab09f8f6"
        ),
    }
    return {
        **expected_binding,
        "binding_sha256": json_sha256(expected_binding),
    }


def validate_ab_receipt(
    value: dict[str, Any],
    candidate: Path,
    observer_public_key_sha256: str,
) -> dict[str, Any]:
    artifacts = value.get("artifacts")
    boot = artifacts.get("boot") if isinstance(artifacts, dict) else None
    binding = value.get("auto_handoff_binding")
    expected_binding = expected_compiled_binding()
    resolution = flat_buildlib.resolve_manifest(REPO_ROOT / VERSION_MANIFEST_REL)
    manifest_sha = sha256_file(REPO_ROOT / VERSION_MANIFEST_REL)
    expected_lineage = [
        {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "sha256": sha256_file(path),
        }
        for path in resolution.lineage
    ]
    input_pins = value.get("input_pins")
    source_keys = value.get("source_keys")
    expected_source_keys = {
        "flat_builder": {
            "path": "workspace/public/src/scripts/revalidation/a90_flat_builder/build.py",
            **{
                key: item
                for key, item in bound_file(
                    REPO_ROOT
                    / "workspace/public/src/scripts/revalidation/a90_flat_builder/build.py"
                ).items()
                if key != "path"
            },
        },
        "flat_builder_library": {
            "path": "workspace/public/src/scripts/revalidation/a90_flat_builder/buildlib.py",
            **{
                key: item
                for key, item in bound_file(
                    REPO_ROOT
                    / "workspace/public/src/scripts/revalidation/a90_flat_builder/buildlib.py"
                ).items()
                if key != "path"
            },
        },
    }
    expected_artifacts = {
        "boot": {
            "path": "boot.img",
            "bytes": CANDIDATE_BOOT_SIZE,
            "sha256": CANDIDATE_BOOT_SHA256,
        },
        "helper": {
            "path": "build/helper",
            "bytes": CANDIDATE_HELPER_SIZE,
            "sha256": CANDIDATE_HELPER_SHA256,
        },
        "init": {
            "path": "build/init",
            "bytes": CANDIDATE_INIT_SIZE,
            "sha256": CANDIDATE_INIT_SHA256,
        },
        "ramdisk": {
            "path": "build/ramdisk.cpio",
            "bytes": CANDIDATE_RAMDISK_SIZE,
            "sha256": CANDIDATE_RAMDISK_SHA256,
        },
    }
    lineage = value.get("manifest_lineage")
    if (
        value.get("schema") != "a90-flat-builder-v1-ab-receipt"
        or value.get("profile") != CANDIDATE_BUILD
        or value.get("byte_identical") is not True
        or value.get("candidate_authority") is not False
        or value.get("accepted_boot_unchanged") is not True
        or value.get("manifest_sha256") != manifest_sha
        or lineage != expected_lineage
        or not isinstance(input_pins, dict)
        or input_pins.get("init_closure_sha256") != NATIVE_CLOSURE_SHA256
        or input_pins.get("observer_authorized_key_sha256")
        != observer_public_key_sha256
        or set(input_pins)
        != {
            "accepted_boot_sha256",
            "base_boot_sha256",
            "helper_source_sha256",
            "init_closure_sha256",
            "mkbootimg_sha256",
            "observer_authorized_key_sha256",
            "unpack_bootimg_sha256",
        }
        or source_keys != expected_source_keys
        or artifacts != expected_artifacts
        or not isinstance(boot, dict)
        or candidate.stat().st_size != CANDIDATE_BOOT_SIZE
        or sha256_file(candidate) != CANDIDATE_BOOT_SHA256
        or not isinstance(binding, dict)
        or set(binding) != set(expected_binding)
        or any(binding.get(key) != item for key, item in expected_binding.items())
    ):
        raise ContractError("H24 deterministic build receipt is not exact")
    return binding


def _baseline_inputs(manifest: dict[str, Any], result: dict[str, Any]) -> None:
    candidate = manifest.get("candidate_boot")
    rollback = manifest.get("rollback_boot")
    execution_closure = manifest.get("execution_closure")
    final_health = result.get("final_health")
    native = final_health.get("native") if isinstance(final_health, dict) else None
    first_boot = (
        final_health.get("first_boot") if isinstance(final_health, dict) else None
    )
    version = native.get("version") if isinstance(native, dict) else None
    selftest = native.get("selftest") if isinstance(native, dict) else None
    first_status = (
        first_boot.get("status") if isinstance(first_boot, dict) else None
    )
    if (
        manifest.get("schema") != "a90-h18-ufs-f1-manifest-v1"
        or manifest.get("capability") != "A90_H24_PRIVATE_CARD_ROOT_PERSISTENT_UFS_SERVER_V1"
        or not isinstance(execution_closure, dict)
        or execution_closure.get("sha256")
        != CURRENT_INSTALL_EXECUTION_CLOSURE_SHA256
        or not isinstance(candidate, dict)
        or candidate.get("expected_version") != CURRENT_VERSION
        or candidate.get("expected_build")
        != CURRENT_BUILD
        or candidate.get("size") != CURRENT_BOOT_SIZE
        or candidate.get("sha256") != CURRENT_BOOT_SHA256
        or not isinstance(rollback, dict)
        or rollback.get("expected_version") != ROLLBACK_VERSION
        or rollback.get("expected_build") != ROLLBACK_BUILD
        or rollback.get("size") != ROLLBACK_SIZE
        or rollback.get("sha256") != ROLLBACK_SHA256
        or result.get("schema") != "a90-h18-ufs-f1-result-v1"
        or result.get("status") != H24_F1_CLOSED_STATUS
        or result.get("device_safety_state") != "RESIDENT_HEALTHY"
        or result.get("candidate_attempt_count") != 1
        or result.get("candidate_transfer_count") != 1
        or result.get("rollback_transfer_count") != 0
        or result.get("candidate_replay") is not False
        or result.get("rootfs_payload_count") != 0
        or result.get("sd_stage_count") != 0
        or result.get("userdata_write_count") != 0
        or not isinstance(native, dict)
        or native.get("exact_bridge") is not True
        or not isinstance(version, dict)
        or version.get("command") != ["version"]
        or version.get("rc") != 0
        or CURRENT_VERSION not in str(version.get("text") or "")
        or CURRENT_BUILD not in str(version.get("text") or "")
        or not isinstance(selftest, dict)
        or selftest.get("command") != ["selftest"]
        or selftest.get("rc") != 0
        or "fail=0" not in str(selftest.get("text") or "")
        or not isinstance(first_boot, dict)
        or first_boot.get("proof") is not True
        or first_boot.get("enable") != 0
        or first_boot.get("latch") != 0
        or not isinstance(first_status, dict)
        or first_status.get("command") != ["auto-handoff-status"]
        or first_status.get("rc") != 0
        or "binding=1 enable=0 latch=0" not in str(
            first_status.get("text") or ""
        )
    ):
        raise ContractError("H24 predecessor resident predecessor is not exact healthy 0,0")


def validate_h24_predecessor_terminal(
    value: Any,
    predecessor_manifest: Any,
    predecessor_result: Any,
) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != {"run", "records", "terminal_result_sha256"}
        or value.get("run") != "run01"
        or value.get("terminal_result_sha256")
        != H24_D1_CLOSED_SHA256
        or not isinstance(value.get("records"), list)
        or len(value["records"]) != len(H24_D1_RECORDS)
    ):
        raise ContractError("H24 predecessor D1 terminal binding is not exact")
    actions = (
        "open-native-healthy-unarmed",
        "arm-reboot-intent",
        "dispatch-result",
        "persistent-observation",
        "current-state",
        "final-health",
        "closed",
    )
    records: list[dict[str, Any]] = []
    parent: Path | None = None
    for sequence, (filename, size, sha) in enumerate(H24_D1_RECORDS):
        binding = value["records"][sequence]
        if (
            not isinstance(binding, dict)
            or binding.get("size") != size
            or binding.get("sha256") != sha
        ):
            raise ContractError("H24 predecessor D1 journal artifact changed")
        path, record = load_json_bound(binding, f"predecessor_d1.records[{sequence}]")
        if path.name != filename or (parent is not None and path.parent != parent):
            raise ContractError("H24 predecessor D1 journal path set changed")
        parent = path.parent
        if (
            record.get("schema") != "a90-h18-ufs-d1-journal-v1"
            or record.get("sequence") != sequence
            or record.get("action") != actions[sequence]
        ):
            raise ContractError("H24 predecessor D1 journal sequence changed")
        records.append(record)
    final = records[5]
    closed = records[6]
    result = final.get("result")
    opening = records[0]
    if (
        not isinstance(predecessor_manifest, dict)
        or not isinstance(predecessor_result, dict)
        or opening.get("manifest_sha256")
        != predecessor_manifest.get("sha256")
        or opening.get("install_result_sha256")
        != predecessor_result.get("sha256")
        or opening.get("execution_closure_sha256")
        != CURRENT_INSTALL_EXECUTION_CLOSURE_SHA256
        or not isinstance(result, dict)
        or final.get("result_sha256") != H24_D1_CLOSED_SHA256
        or json_sha256(result) != H24_D1_CLOSED_SHA256
        or closed.get("result_sha256") != H24_D1_CLOSED_SHA256
        or closed.get("result") != result
        or result.get("schema") != "a90-h18-ufs-d1-result-v1"
        or result.get("status")
        != H24_D1_CLOSED_STATUS
        or result.get("device_safety_state") != "RESIDENT_HEALTHY"
        or result.get("resident_healthy") is not True
        or result.get("ordinal_closed") is not True
        or result.get("inter_effect_health_barrier_satisfied") is not True
        or result.get("new_device_effect_authority") is not False
        or result.get("candidate_replay") is not False
        or result.get("arm_dispatch_count") != 1
        or result.get("reboot_dispatch_count") != 1
        or any(
            result.get(name) != 0
            for name in (
                "payload_transfer_count",
                "partition_write_count",
                "flash_count",
                "sd_rootfs_stage_count",
                "userdata_write_count",
                "physical_return_reboot_dispatch_count",
            )
        )
    ):
        raise ContractError("H24 predecessor D1 terminal HEALTHY barrier changed")
    return value


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    if RUN_ID_RE.fullmatch(args.run_id) is None:
        raise ContractError("H24 run id is not exact")
    run_dir = (PRIVATE_RUN_BASE / args.run_id).resolve()
    if run_dir.parent != PRIVATE_RUN_BASE:
        raise ContractError("H24 run directory escapes private run base")
    baseline_manifest_path = resolve_regular_input(
        Path(args.baseline_manifest), "baseline manifest"
    )
    baseline_result_path = resolve_regular_input(
        Path(args.baseline_result), "baseline result"
    )
    baseline_manifest = json.loads(baseline_manifest_path.read_text(encoding="utf-8"))
    baseline_result = json.loads(baseline_result_path.read_text(encoding="utf-8"))
    if not isinstance(baseline_manifest, dict) or not isinstance(baseline_result, dict):
        raise ContractError("H24 predecessor resident predecessor JSON shape changed")
    _baseline_inputs(baseline_manifest, baseline_result)
    if baseline_result.get("manifest_sha256") != sha256_file(
        baseline_manifest_path
    ):
        raise ContractError("H24 predecessor resident predecessor manifest binding changed")
    d1_dir_lexical = Path(args.baseline_d1_transaction).absolute()
    if d1_dir_lexical.is_symlink():
        raise ContractError("H24 predecessor D1 transaction directory is a symlink")
    d1_dir = d1_dir_lexical.resolve(strict=True)
    if not d1_dir.is_dir() or d1_dir.name != "run01":
        raise ContractError("H24 predecessor D1 transaction directory is not exact run01")
    predecessor = {
        "manifest": bound_file(baseline_manifest_path),
        "result": bound_file(baseline_result_path),
    }
    predecessor_d1 = {
        "run": "run01",
        "records": [
            bound_file(d1_dir / filename)
            for filename, _, _ in H24_D1_RECORDS
        ],
        "terminal_result_sha256": H24_D1_CLOSED_SHA256,
    }
    validate_h24_predecessor_terminal(
        predecessor_d1,
        predecessor["manifest"],
        predecessor["result"],
    )

    target = baseline_manifest.get("target")
    rollback_value = baseline_manifest.get("rollback_boot")
    if not isinstance(target, dict) or not isinstance(rollback_value, dict):
        raise ContractError("H24 predecessor target/rollback binding is absent")
    rollback_path = Path(str(rollback_value.get("path") or ""))
    require_regular(rollback_path, size=ROLLBACK_SIZE, sha256=ROLLBACK_SHA256)
    bridge_device = target.get("bridge_device")
    if bridge_device != EXACT_BRIDGE_DEVICE:
        raise ContractError("H24 predecessor exact A90 bridge path is absent")
    bridge_path = Path(bridge_device)
    bridge_realpath = str(bridge_path.resolve(strict=True))
    if re.fullmatch(r"/dev/ttyACM[0-9]+", bridge_realpath) is None:
        raise ContractError("current A90 bridge realpath is not exact")

    observer = baseline_manifest.get("observer")
    if not isinstance(observer, dict):
        raise ContractError("H24 predecessor observer binding is absent")
    observer_key = reopen_bound(observer.get("private_key"), "observer.private_key")
    observer_public_key = reopen_bound(
        observer.get("public_key"), "observer.public_key"
    )
    observer_public_key_sha256 = require_sha(
        observer.get("public_key_sha256"),
        "observer.public_key_sha256",
    )
    if (
        observer_public_key
        != observer_key.with_suffix(observer_key.suffix + ".pub")
        or sha256_file(observer_public_key) != observer_public_key_sha256
    ):
        raise ContractError("H24 predecessor observer keypair changed")

    candidate = resolve_regular_input(Path(args.candidate), "candidate boot")
    receipt_path, receipt = load_reviewed_ab_receipt(Path(args.ab_receipt))
    compiled_binding = validate_ab_receipt(
        receipt,
        candidate,
        observer_public_key_sha256,
    )

    inventory_path = resolve_regular_input(Path(args.ufs_inventory), "UFS inventory")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if not isinstance(inventory, dict):
        raise ContractError("UFS inventory is not an object")
    validate_ufs_inventory(
        inventory,
        expected_run_id=args.run_id,
        expected_bridge_realpath=bridge_realpath,
        enforce_fresh=True,
    )

    closure = execution_closure()
    validate_host_capability_qualification()
    qualification = bound_file(Path(args.qualification))
    validate_qualification(qualification, closure)
    recovery = target.get("recovery_adb_identity_evidence")
    if not isinstance(recovery, dict):
        raise ContractError("recovery identity evidence is not bound")
    for name in ("candidate_recovery_log", "rollback_recovery_log"):
        reopen_bound(recovery.get(name), f"recovery.{name}")
    return {
        "schema": SCHEMA,
        "status": "ready-for-attended-f1",
        "run_id": args.run_id,
        "capability": CAPABILITY,
        "created_utc": utc_now(),
        "authority": {
            "operator_attendance_required": True,
            "candidate_attempt_limit": 1,
            "rollback_attempt_limit": 1,
            "candidate_replay": False,
            "partition_allowlist": ["boot"],
            "rootfs_payload_count": 0,
            "sd_stage_count": 0,
            "userdata_write_count": 0,
            "manifest_grants_live_authority": False,
        },
        "target": {
            "profile": "galaxy-a90-5g-native-init",
            "bridge_device": bridge_device,
            "bridge_realpath": bridge_realpath,
            "current_version": CURRENT_VERSION,
            "current_build": CURRENT_BUILD,
            "recovery": target.get("recovery"),
            "recovery_adb_serial_sha256": target.get(
                "recovery_adb_serial_sha256"
            ),
            "recovery_adb_identity_evidence": recovery,
        },
        "candidate_boot": {
            **bound_file(candidate),
            "partition": "boot",
            "expected_version": CANDIDATE_VERSION,
            "expected_build": CANDIDATE_BUILD,
            "compiled_binding": compiled_binding,
            "ab_receipt": bound_file(receipt_path),
            "enable_path": ENABLE_PATH,
            "latch_path": LATCH_PATH,
        },
        "rollback_boot": {
            **bound_file(rollback_path),
            "partition": "boot",
            "expected_version": ROLLBACK_VERSION,
            "expected_build": ROLLBACK_BUILD,
        },
        "ufs_root": {
            **UFS_IDENTITY,
            "content_manifest": bound_file(REPO_ROOT / CONTENT_REL),
            "content_manifest_semantic_sha256": (
                "e1950058627446d6bbd487d6a17b80f5766be4956b54cb56659b541dab09f8f6"
            ),
            "inventory": bound_file(inventory_path),
            "whole_filesystem_sha256": None,
            "write_allowed": False,
        },
        "predecessor": predecessor,
        "predecessor_d1": predecessor_d1,
        "flash_runner": bound_file(NATIVE_FLASH),
        "observer": {
            "private_key": bound_file(observer_key),
            "public_key": bound_file(observer_public_key),
            "public_key_sha256": observer_public_key_sha256,
            "device_ip": observer.get("device_ip"),
            "device_port": observer.get("device_port"),
            "host_ncm_profile": observer.get("host_ncm_profile"),
            "transport_scope": "USB-local NCM only",
            "wifi_required": True,
            "public_tunnel_allowed": False,
        },
        "execution_qualification": qualification,
        "execution_closure": closure,
    }


def load_manifest(path: Path, expected_sha256: str) -> dict[str, Any]:
    require_sha(expected_sha256, "expected manifest SHA256")
    resolved = path.resolve(strict=True)
    if sha256_file(resolved) != expected_sha256:
        raise ContractError("manifest SHA256 changed")
    value = json.loads(resolved.read_text(encoding="utf-8"))
    if (
        not isinstance(value, dict)
        or value.get("schema") != SCHEMA
        or value.get("status") != "ready-for-attended-f1"
        or value.get("capability") != CAPABILITY
        or RUN_ID_RE.fullmatch(str(value.get("run_id") or "")) is None
    ):
        raise ContractError("H24 F1 manifest header changed")
    authority = value.get("authority")
    if (
        not isinstance(authority, dict)
        or authority.get("operator_attendance_required") is not True
        or authority.get("candidate_attempt_limit") != 1
        or authority.get("rollback_attempt_limit") != 1
        or authority.get("candidate_replay") is not False
        or authority.get("partition_allowlist") != ["boot"]
        or authority.get("rootfs_payload_count") != 0
        or authority.get("sd_stage_count") != 0
        or authority.get("userdata_write_count") != 0
        or authority.get("manifest_grants_live_authority") is not False
    ):
        raise ContractError("H24 authority widened")

    closure = execution_closure()
    if value.get("execution_closure") != closure:
        raise ContractError("H24 execution-critical closure changed")
    validate_host_capability_qualification()
    validate_qualification(value.get("execution_qualification"), closure)
    _, inventory = load_json_bound(
        value.get("ufs_root", {}).get("inventory"),
        "ufs_root.inventory",
    )
    validate_ufs_inventory(
        inventory,
        expected_run_id=value["run_id"],
        expected_bridge_realpath=str(
            value.get("target", {}).get("bridge_realpath") or ""
        ),
        enforce_fresh=False,
    )
    content = value.get("ufs_root", {}).get("content_manifest")
    content_path = reopen_bound(content, "ufs_root.content_manifest")
    if (
        content_path != (REPO_ROOT / CONTENT_REL).resolve(strict=True)
        or value.get("ufs_root", {}).get("content_manifest_semantic_sha256")
        != "e1950058627446d6bbd487d6a17b80f5766be4956b54cb56659b541dab09f8f6"
        or value.get("ufs_root", {}).get("whole_filesystem_sha256") is not None
        or value.get("ufs_root", {}).get("write_allowed") is not False
        or any(value.get("ufs_root", {}).get(key) != item for key, item in UFS_IDENTITY.items())
    ):
        raise ContractError("H24 UFS binding changed")

    predecessor = value.get("predecessor")
    if not isinstance(predecessor, dict):
        raise ContractError("H24 predecessor resident predecessor binding is absent")
    predecessor_manifest_path, predecessor_manifest = load_json_bound(
        predecessor.get("manifest"), "predecessor.manifest"
    )
    _, predecessor_result = load_json_bound(
        predecessor.get("result"), "predecessor.result"
    )
    _baseline_inputs(predecessor_manifest, predecessor_result)
    if predecessor_result.get("manifest_sha256") != sha256_file(
        predecessor_manifest_path
    ):
        raise ContractError("H24 predecessor resident predecessor manifest binding changed")
    validate_h24_predecessor_terminal(
        value.get("predecessor_d1"),
        predecessor.get("manifest"),
        predecessor.get("result"),
    )
    predecessor_target = predecessor_manifest.get("target")
    target = value.get("target")
    if not isinstance(predecessor_target, dict) or not isinstance(target, dict):
        raise ContractError("H24 exact target predecessor binding is absent")
    expected_target_keys = {
        "profile",
        "bridge_device",
        "bridge_realpath",
        "current_version",
        "current_build",
        "recovery",
        "recovery_adb_serial_sha256",
        "recovery_adb_identity_evidence",
    }
    bridge_realpath = target.get("bridge_realpath")
    if (
        set(target) != expected_target_keys
        or target.get("profile") != "galaxy-a90-5g-native-init"
        or target.get("profile") != predecessor_target.get("profile")
        or target.get("bridge_device") != EXACT_BRIDGE_DEVICE
        or target.get("bridge_device") != predecessor_target.get("bridge_device")
        or not isinstance(bridge_realpath, str)
        or re.fullmatch(r"/dev/ttyACM[0-9]+", bridge_realpath) is None
        or target.get("current_version") != CURRENT_VERSION
        or target.get("current_build") != CURRENT_BUILD
        or target.get("recovery") != predecessor_target.get("recovery")
        or target.get("recovery_adb_serial_sha256")
        != predecessor_target.get("recovery_adb_serial_sha256")
        or target.get("recovery_adb_identity_evidence")
        != predecessor_target.get("recovery_adb_identity_evidence")
    ):
        raise ContractError("H24 exact target or recovery binding changed")

    observer = value.get("observer")
    if not isinstance(observer, dict):
        raise ContractError("H24 observer binding is absent")
    observer_key = reopen_bound(observer.get("private_key"), "observer.private_key")
    public_key = reopen_bound(observer.get("public_key"), "observer.public_key")
    observer_public_key_sha256 = require_sha(
        observer.get("public_key_sha256"),
        "observer.public_key_sha256",
    )
    if (
        public_key != observer_key.with_suffix(observer_key.suffix + ".pub")
        or observer_public_key_sha256 != sha256_file(public_key)
        or observer.get("device_ip") != "192.168.7.2"
        or observer.get("device_port") != 2222
        or observer.get("host_ncm_profile") != "a90-v3406-ncm"
        or observer.get("transport_scope") != "USB-local NCM only"
        or observer.get("wifi_required") is not True
        or observer.get("public_tunnel_allowed") is not False
    ):
        raise ContractError("H24 observer or network scope changed")

    candidate = value.get("candidate_boot")
    rollback = value.get("rollback_boot")
    if not isinstance(candidate, dict) or not isinstance(rollback, dict):
        raise ContractError("candidate or rollback binding is absent")
    candidate_path = reopen_bound(
        {key: candidate.get(key) for key in ("path", "size", "sha256")},
        "candidate_boot",
    )
    ab_receipt_binding = candidate.get("ab_receipt")
    require_reviewed_ab_receipt_binding(ab_receipt_binding)
    _, ab_receipt = load_json_bound(
        ab_receipt_binding,
        "candidate_boot.ab_receipt",
    )
    compiled_binding = validate_ab_receipt(
        ab_receipt,
        candidate_path,
        observer_public_key_sha256,
    )
    reopen_bound(
        {key: rollback.get(key) for key in ("path", "size", "sha256")},
        "rollback_boot",
    )
    if (
        candidate.get("partition") != "boot"
        or candidate.get("expected_version") != CANDIDATE_VERSION
        or candidate.get("expected_build") != CANDIDATE_BUILD
        or candidate.get("compiled_binding") != compiled_binding
        or compiled_binding != expected_compiled_binding()
        or candidate.get("enable_path") != ENABLE_PATH
        or candidate.get("latch_path") != LATCH_PATH
        or rollback.get("partition") != "boot"
        or rollback.get("expected_version") != ROLLBACK_VERSION
        or rollback.get("expected_build") != ROLLBACK_BUILD
        or rollback.get("size") != ROLLBACK_SIZE
        or rollback.get("sha256") != ROLLBACK_SHA256
    ):
        raise ContractError("boot-only candidate or rollback binding changed")
    flash_path = reopen_bound(value.get("flash_runner"), "flash_runner")
    if flash_path != NATIVE_FLASH:
        raise ContractError("flash runner changed")
    return value


def _approval_path(manifest: dict[str, Any]) -> Path:
    run_dir = (PRIVATE_RUN_BASE / manifest["run_id"]).resolve()
    if run_dir.parent != PRIVATE_RUN_BASE:
        raise ContractError("H24 approval path escapes private run base")
    return run_dir / "h27-f1-approval-prepared.json"


def approval_binding(
    manifest: dict[str, Any],
    manifest_sha: str,
    *,
    created_utc: str,
    expires_utc: str,
) -> dict[str, Any]:
    target = manifest["target"]
    candidate = manifest["candidate_boot"]
    rollback = manifest["rollback_boot"]
    return {
        "schema": APPROVAL_BINDING_SCHEMA,
        "workflow": "A90_F1_RESIDENT_INSTALL_V1",
        "authority_mode": "trial-retired-fresh-approval-required",
        "run_id": manifest["run_id"],
        "manifest_sha256": manifest_sha,
        "execution_closure_sha256": manifest["execution_closure"]["sha256"],
        "agents_contract_sha256": sha256_file(REPO_ROOT / "AGENTS.md"),
        "target_profile": target["profile"],
        "bridge_device": target["bridge_device"],
        "bridge_realpath": target["bridge_realpath"],
        "recovery_binding_sha256": json_sha256(
            target["recovery_adb_identity_evidence"]
        ),
        "candidate_boot_sha256": candidate["sha256"],
        "candidate_boot_size": candidate["size"],
        "rollback_boot_sha256": rollback["sha256"],
        "rollback_boot_size": rollback["size"],
        "partition_allowlist": ["boot"],
        "candidate_attempt_limit": 1,
        "rollback_transfer_attempt_limit": 1,
        "candidate_replay": False,
        "rollback_on_candidate_ambiguity": True,
        "operator_attendance_required": True,
        "created_utc": created_utc,
        "expires_utc": expires_utc,
    }


def prepare_approval(manifest_path: Path, manifest_sha: str) -> dict[str, Any]:
    manifest = load_manifest(manifest_path, manifest_sha)
    created = dt.datetime.now(dt.UTC).replace(microsecond=0)
    expires = created + dt.timedelta(seconds=APPROVAL_TTL_SEC)
    binding = approval_binding(
        manifest,
        manifest_sha,
        created_utc=created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        expires_utc=expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    binding_sha = json_sha256(binding)
    value = {
        "schema": APPROVAL_SCHEMA,
        "run_id": manifest["run_id"],
        "manifest_sha256": manifest_sha,
        "approval_binding": binding,
        "approval_binding_sha256": binding_sha,
        "approval_token": APPROVAL_PREFIX + binding_sha,
        "device_contact": False,
        "device_write": False,
        "live_authority_from_preparation": False,
    }
    write_json_exclusive(_approval_path(manifest), value)
    return value


def validate_approval(
    manifest: dict[str, Any],
    manifest_sha: str,
    approval: str | None,
) -> dict[str, Any]:
    path = _approval_path(manifest)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink() or info.st_mode & 0o077:
        raise ContractError("H24 F1 approval is not a private regular file")
    value = json.loads(path.read_text(encoding="utf-8"))
    binding = value.get("approval_binding") if isinstance(value, dict) else None
    if not isinstance(binding, dict):
        raise ContractError("H24 F1 approval binding is absent")
    binding_sha = json_sha256(binding)
    expected = approval_binding(
        manifest,
        manifest_sha,
        created_utc=str(binding.get("created_utc") or ""),
        expires_utc=str(binding.get("expires_utc") or ""),
    )
    now = dt.datetime.now(dt.UTC)
    created = parse_utc(binding.get("created_utc"), "approval created_utc")
    expires = parse_utc(binding.get("expires_utc"), "approval expires_utc")
    if (
        set(value)
        != {
            "schema",
            "run_id",
            "manifest_sha256",
            "approval_binding",
            "approval_binding_sha256",
            "approval_token",
            "device_contact",
            "device_write",
            "live_authority_from_preparation",
        }
        or value.get("schema") != APPROVAL_SCHEMA
        or value.get("run_id") != manifest["run_id"]
        or value.get("manifest_sha256") != manifest_sha
        or binding != expected
        or value.get("approval_binding_sha256") != binding_sha
        or value.get("approval_token") != APPROVAL_PREFIX + binding_sha
        or approval != value.get("approval_token")
        or value.get("device_contact") is not False
        or value.get("device_write") is not False
        or value.get("live_authority_from_preparation") is not False
        or expires - created != dt.timedelta(seconds=APPROVAL_TTL_SEC)
        or now < created
        or now > expires
    ):
        raise ContractError("H24 F1 approval is not fresh and exact")
    return value


def require_consumed_approval(
    records: list[dict[str, Any]],
    manifest: dict[str, Any],
    manifest_sha: str,
) -> dict[str, Any]:
    matches = [item for item in records if item.get("action") == "approval-consumed"]
    if len(matches) != 1:
        raise ContractError("H24 F1 approval consumption is not durable and unique")
    record = matches[0]
    binding = record.get("approval_binding")
    if not isinstance(binding, dict):
        raise ContractError("H24 F1 consumed approval binding is absent")
    expected = approval_binding(
        manifest,
        manifest_sha,
        created_utc=str(binding.get("created_utc") or ""),
        expires_utc=str(binding.get("expires_utc") or ""),
    )
    if (
        binding != expected
        or record.get("approval_binding_sha256") != json_sha256(binding)
        or record.get("approval_consumed") is not True
        or record.get("approval_token_sha256")
        != hashlib.sha256(
            (APPROVAL_PREFIX + json_sha256(binding)).encode("utf-8")
        ).hexdigest()
    ):
        raise ContractError("H24 F1 consumed approval changed")
    return record


def _stage_view(manifest: dict[str, Any], manifest_path: Path, manifest_sha: str) -> Any:
    target = manifest["target"]
    candidate = manifest["candidate_boot"]
    return SimpleNamespace(
        run_id=manifest["run_id"],
        manifest_path=manifest_path.resolve(strict=True),
        manifest_sha256=manifest_sha,
        local_image=Path(candidate["path"]),
        local_size=candidate["size"],
        local_sha256=candidate["sha256"],
        remote_final="",
        remote_work="",
        remote_stage_dir="",
        remote_payload="",
        bridge_device=target["bridge_device"],
        bridge_realpath=target["bridge_realpath"],
        observer_device="192.168.7.2",
        starting_version=CURRENT_VERSION,
        starting_build=CURRENT_BUILD,
    )


def _spec(manifest: dict[str, Any], manifest_path: Path, manifest_sha: str) -> Any:
    candidate = manifest["candidate_boot"]
    rollback = manifest["rollback_boot"]
    recovery = manifest["target"]["recovery_adb_identity_evidence"]
    evidence = []
    for name in ("candidate_recovery_log", "rollback_recovery_log"):
        item = recovery[name]
        path = reopen_bound(item, f"recovery.{name}")
        evidence.append(
            staging.BoundFile(
                label=name,
                path=path,
                size=item["size"],
                sha256=item["sha256"],
            )
        )
    serial_sha = require_sha(
        manifest["target"].get("recovery_adb_serial_sha256"),
        "recovery_adb_serial_sha256",
    )
    recovery_serial = base.recovery_serial_from_evidence(
        tuple(evidence), serial_sha
    )
    observer = manifest["observer"]
    return SimpleNamespace(
        stage=_stage_view(manifest, manifest_path, manifest_sha),
        candidate=staging.BoundFile(
            label="candidate_boot",
            path=Path(candidate["path"]),
            size=candidate["size"],
            sha256=candidate["sha256"],
        ),
        rollback=staging.BoundFile(
            label="rollback_boot",
            path=Path(rollback["path"]),
            size=rollback["size"],
            sha256=rollback["sha256"],
        ),
        flash_runner=staging.BoundFile(
            label="flash_runner",
            path=NATIVE_FLASH,
            size=manifest["flash_runner"]["size"],
            sha256=manifest["flash_runner"]["sha256"],
        ),
        candidate_version=CANDIDATE_VERSION,
        candidate_build=CANDIDATE_BUILD,
        rollback_version=ROLLBACK_VERSION,
        rollback_build=ROLLBACK_BUILD,
        candidate_boot_timeout=300,
        rollback_boot_timeout=300,
        handoff_timeout=1,
        ssh_marker_timeout=1,
        candidate_return_timeout=300,
        observer_key=Path(observer["private_key"]["path"]),
        observer_public_key_sha256=observer["public_key_sha256"],
        observer_device=observer["device_ip"],
        observer_port=observer["device_port"],
        observer_host_ncm_profile=observer["host_ncm_profile"],
        display_required=True,
        display_profile="phase2-display-v1",
        display_uid=3904,
        display_gid=3904,
        display_max_attempts=3,
        display_visible_text=(
            "A90 DEBIAN",
            "DIRECT DRM SESSION",
            "PID 1: SYSVINIT / VT: NONE",
            "DISPLAY OWNER: DEBIAN",
        ),
        recovery_serial_sha256=serial_sha,
        recovery_serial=recovery_serial,
        candidate_first_boot={
            "enable_path": ENABLE_PATH,
            "latch_path": LATCH_PATH,
        },
    )


def _journal_dir(manifest: dict[str, Any]) -> Path:
    run_dir = (PRIVATE_RUN_BASE / manifest["run_id"]).resolve()
    if run_dir.parent != PRIVATE_RUN_BASE:
        raise ContractError("transaction directory escapes private run base")
    return run_dir / "h27-f1-live" / "journal"


def read_journal(path: Path, manifest: dict[str, Any], manifest_sha: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for index, item in enumerate(sorted(path.glob("*.json"))):
        value = json.loads(item.read_text(encoding="utf-8"))
        if (
            not isinstance(value, dict)
            or value.get("schema") != JOURNAL_SCHEMA
            or value.get("sequence") != index
            or value.get("run_id") != manifest["run_id"]
            or value.get("manifest_sha256") != manifest_sha
            or item.name != f"{index:04d}-{value.get('action')}.json"
        ):
            raise ContractError("durable H24 journal is inconsistent")
        records.append(value)
    _validate_f1_journal(records, manifest, manifest_sha)
    return records


def _definite_pre_session(record: dict[str, Any]) -> bool:
    try:
        return base.candidate_failure_is_definite_pre_session(record)
    except Exception:
        return False


def _validate_closed_result(
    result: Any,
    records: list[dict[str, Any]],
    manifest: dict[str, Any],
    manifest_sha: str,
) -> None:
    if (
        not isinstance(result, dict)
        or result.get("schema") != RESULT_SCHEMA
        or result.get("run_id") != manifest["run_id"]
        or result.get("manifest_sha256") != manifest_sha
        or result.get("candidate_attempt_count") != 1
        or result.get("candidate_replay") is not False
        or result.get("rootfs_payload_count") != 0
        or result.get("sd_stage_count") != 0
        or result.get("userdata_write_count") != 0
    ):
        raise ContractError("durable H27 closed result is invalid")
    # The proof axis is only a control if a consumer refuses a mismatched
    # pairing. Without this, a durable result claiming a passing install while
    # carrying REFUTED would be accepted.
    validate_experiment_proof(result)
    actions = [item["action"] for item in records]
    candidate = next(
        (item for item in records if item["action"] == "candidate-result"), None
    )
    candidate_count = (
        candidate.get("candidate_transfer_count")
        if isinstance(candidate, dict)
        else None
    )
    candidate_health = next(
        (item for item in records if item["action"] == "candidate-health"), None
    )
    rollback = next(
        (item for item in records if item["action"] == "rollback-result"), None
    )
    rollback_health = next(
        (item for item in records if item["action"] == "rollback-health"), None
    )
    if candidate_health is not None:
        health = validate_stored_candidate_health(
            candidate_health.get("health"), manifest
        )
        valid = (
            result.get("status") == "PASS_A90_H27_UFS_RESIDENT_INSTALLED"
            and result.get("device_safety_state") == "RESIDENT_HEALTHY"
            and result.get("candidate_transfer_count") == 1
            and result.get("rollback_transfer_count") == 0
            and result.get("final_health") == health
            and "rollback-intent" not in actions
        )
    elif rollback_health is not None:
        health = validate_stored_rollback_health(
            rollback_health.get("health"), manifest
        )
        valid = (
            result.get("status")
            in {
                "FAILED_CANDIDATE_ROLLED_BACK",
                "FAILED_INITIAL_HEALTH_ROLLED_BACK",
                "FAILED_CANDIDATE_RECOVERY_ROLLBACK_COMPLETE",
            }
            and result.get("device_safety_state") == "BASELINE_HEALTHY"
            and result.get("candidate_transfer_count") == candidate_count
            and result.get("rollback_transfer_count") == 1
            and isinstance(rollback, dict)
            and rollback.get("rollback_transfer_count") == 1
            and result.get("final_health") == health
        )
    else:
        health = result.get("final_health")
        try:
            staging.validate_native_health_receipts(
                health,
                expected_version=CURRENT_VERSION,
                expected_build=CURRENT_BUILD,
            )
            health_valid = True
        except Exception:
            health_valid = False
        valid = (
            result.get("status")
            in {"ABORTED_BEFORE_CANDIDATE_RELEASE", "ABORTED_BEFORE_CANDIDATE_SESSION"}
            and result.get("device_safety_state") == "RESIDENT_HEALTHY"
            and result.get("candidate_transfer_count") == 0
            and candidate_count == 0
            and result.get("rollback_transfer_count") == 0
            and health_valid
            and "rollback-intent" not in actions
        )
    if not valid:
        raise ContractError("durable H24 closed result contradicts journal state")


def _validate_f1_journal(
    records: list[dict[str, Any]],
    manifest: dict[str, Any],
    manifest_sha: str,
) -> None:
    if not records:
        return
    actions = [item["action"] for item in records]
    allowed = {
        "approval-consumed",
        "guard-armed",
        "candidate-intent",
        "candidate-launch",
        "candidate-result",
        "candidate-health",
        "rollback-intent",
        "rollback-launch",
        "rollback-result",
        "rollback-health",
        "recovery-required",
        "closed",
    }
    if any(action not in allowed or actions.count(action) != 1 for action in actions):
        raise ContractError("durable H24 journal action set changed")
    opening = ("approval-consumed", "guard-armed", "candidate-intent")
    if tuple(actions[: min(3, len(actions))]) != opening[: min(3, len(actions))]:
        raise ContractError("durable H24 journal opening order changed")
    if "closed" in actions and actions[-1] != "closed":
        raise ContractError("durable H24 closed record is not terminal")
    approval = records[0]
    if (
        approval.get("approval_consumed") is not True
        or approval.get("device_safety_state") != "RESIDENT_HEALTHY"
        or approval.get("candidate_transfer_count") != 0
        or approval.get("rollback_transfer_count") != 0
        or approval.get("rootfs_payload_count") != 0
        or approval.get("sd_stage_count") != 0
        or approval.get("userdata_write_count") != 0
        or not isinstance(approval.get("approval_binding"), dict)
        or approval.get("approval_binding_sha256")
        != json_sha256(approval.get("approval_binding"))
    ):
        raise ContractError("durable H24 consumed approval changed")
    if len(actions) >= 2 and (
        records[1].get("candidate_replay") is not False
        or not isinstance(records[1].get("guard"), dict)
    ):
        raise ContractError("durable H24 guard arm changed")
    if len(actions) >= 3:
        intent = records[2]
        if (
            intent.get("candidate_sha256") != CANDIDATE_BOOT_SHA256
            or intent.get("candidate_attempt_limit") != 1
            or intent.get("partition") != "boot"
            or intent.get("rollback_pre_authorized") is not True
            or intent.get("approval_binding_sha256")
            != approval.get("approval_binding_sha256")
            or intent.get("candidate_replay") is not False
            or intent.get("rootfs_payload_count") != 0
            or intent.get("sd_stage_count") != 0
            or intent.get("userdata_write_count") != 0
        ):
            raise ContractError("durable H24 candidate intent changed")
    if len(actions) <= 3:
        return
    candidate_launch = "candidate-launch" in actions
    if candidate_launch:
        launch_item = records[3]
        launch = launch_item.get("launch")
        if (
            launch_item.get("candidate_replay") is not False
            or launch_item.get("rollback_replay") is not False
            or not isinstance(launch, dict)
            or launch.get("schema") != "a90-h27-flash-process-group-v1"
            or launch.get("kind") != "candidate"
            or launch.get("manifest_sha256") != manifest_sha
            or launch.get("artifact_sha256")
            != manifest.get("candidate_boot", {}).get("sha256")
            or launch.get("artifact_size")
            != manifest.get("candidate_boot", {}).get("size")
            or launch.get("release_count_max") != 1
        ):
            raise ContractError("durable candidate launch changed")
        if len(actions) == 4:
            return
    result_index = 4 if candidate_launch else 3
    if actions[result_index] != "candidate-result":
        raise ContractError("durable H24 candidate launch/result order changed")
    candidate_result = records[result_index]
    candidate_record = candidate_result.get("record")
    candidate_count = candidate_result.get("candidate_transfer_count")
    if (
        candidate_result.get("candidate_attempt_count") != 1
        or candidate_result.get("candidate_replay") is not False
        or not isinstance(candidate_record, dict)
        or isinstance(candidate_count, bool)
        or candidate_count not in (0, 1, None)
    ):
        raise ContractError("durable H24 candidate result changed")
    completed = _reconstructed_candidate_transfer_is_proven(candidate_record)
    if candidate_count == 1 and (
        not candidate_launch
        or not (candidate_record.get("returncode") == 0 or completed)
    ):
        raise ContractError("candidate transfer count lacks exact launch/result proof")
    if candidate_count == 0:
        absent_launch = (
            not candidate_launch
            and candidate_result.get("inferred_from_absent_launch") is True
            and candidate_record.get("process_started") is False
            and candidate_record.get("release_count") == 0
        )
        if not absent_launch and not (
            candidate_launch and _definite_pre_session(candidate_record)
        ):
            raise ContractError("zero candidate transfer is not definite pre-session")
    if candidate_count is None and (
        not candidate_launch or completed or _definite_pre_session(candidate_record)
    ):
        raise ContractError("ambiguous candidate transfer classification changed")

    tail = actions[result_index + 1 :]
    recovery_count = tail.count("recovery-required")
    if recovery_count > 1:
        raise ContractError("recovery park is duplicated")
    core = [action for action in tail if action != "recovery-required"]
    valid_cores = {
        (),
        ("closed",),
        ("candidate-health",),
        ("candidate-health", "closed"),
        ("rollback-intent",),
        ("rollback-intent", "rollback-launch"),
        ("rollback-intent", "rollback-launch", "rollback-result"),
        (
            "rollback-intent",
            "rollback-launch",
            "rollback-result",
            "rollback-health",
        ),
        (
            "rollback-intent",
            "rollback-launch",
            "rollback-result",
            "rollback-health",
            "closed",
        ),
    }
    if tuple(core) not in valid_cores:
        raise ContractError("durable H24 journal state transition changed")
    if recovery_count and "closed" in core:
        if "rollback-health" not in core:
            raise ContractError("recovery park closed without exact rollback health")
    if "candidate-health" in core:
        if candidate_count != 1:
            raise ContractError("candidate health lacks one candidate transfer")
        item = next(item for item in records if item["action"] == "candidate-health")
        if item.get("device_safety_state") != "RESIDENT_HEALTHY":
            raise ContractError("candidate health state changed")
        validate_stored_candidate_health(item.get("health"), manifest)
    intent_item = None
    if "rollback-intent" in core:
        intent_item = next(
            item for item in records if item["action"] == "rollback-intent"
        )
        if (
            intent_item.get("rollback_sha256") != ROLLBACK_SHA256
            or intent_item.get("rollback_attempt_limit") != 1
            or intent_item.get("candidate_replay") is not False
            or intent_item.get("recovery_mode") not in {"from-native", "adb-recovery"}
        ):
            raise ContractError("durable rollback intent changed")
    if "rollback-launch" in core:
        assert intent_item is not None
        launch_item = next(
            item for item in records if item["action"] == "rollback-launch"
        )
        launch = launch_item.get("launch")
        if (
            launch_item.get("candidate_replay") is not False
            or launch_item.get("rollback_replay") is not False
            or not isinstance(launch, dict)
            or launch.get("schema") != "a90-h27-flash-process-group-v1"
            or launch.get("kind") != "rollback"
            or launch.get("manifest_sha256") != manifest_sha
            or launch.get("artifact_sha256")
            != manifest.get("rollback_boot", {}).get("sha256")
            or launch.get("artifact_size")
            != manifest.get("rollback_boot", {}).get("size")
            or launch.get("release_count_max") != 1
            or launch.get("from_native")
            is not (intent_item.get("recovery_mode") == "from-native")
        ):
            raise ContractError("durable rollback launch changed")
    if "rollback-result" in core:
        item = next(item for item in records if item["action"] == "rollback-result")
        rollback_record = item.get("record")
        rollback_count = item.get("rollback_transfer_count")
        if (
            not isinstance(rollback_record, dict)
            or isinstance(rollback_count, bool)
            or rollback_count not in (0, 1, None)
            or (
                rollback_count == 1
                and not (
                    rollback_record.get("returncode") == 0
                    or _reconstructed_candidate_transfer_is_proven(rollback_record)
                )
            )
        ):
            raise ContractError("durable rollback result changed")
        if "rollback-health" in core:
            health_item = next(
                item for item in records if item["action"] == "rollback-health"
            )
            if (
                rollback_count != 1
                or health_item.get("device_safety_state") != "BASELINE_HEALTHY"
            ):
                raise ContractError("rollback health lacks one exact transfer")
            validate_stored_rollback_health(health_item.get("health"), manifest)
    if "closed" in actions:
        _validate_closed_result(records[-1].get("result"), records, manifest, manifest_sha)


def append_journal(
    path: Path,
    manifest: dict[str, Any],
    manifest_sha: str,
    action: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if re.fullmatch(r"[a-z0-9-]+", action) is None:
        raise ContractError("journal action name is not exact")
    records = read_journal(path, manifest, manifest_sha)
    value = {
        "schema": JOURNAL_SCHEMA,
        "sequence": len(records),
        "timestamp_utc": utc_now(),
        "run_id": manifest["run_id"],
        "manifest_sha256": manifest_sha,
        "action": action,
        **payload,
    }
    write_json_exclusive(path / f"{len(records):04d}-{action}.json", value)
    validated = read_journal(path, manifest, manifest_sha)
    if not validated or validated[-1] != value:
        raise ContractError("durable H24 journal append did not revalidate")
    return value


def validate_live_args(args: argparse.Namespace) -> None:
    exact = {
        "bridge_host": "127.0.0.1",
        "bridge_port": 54321,
        "bridge_timeout": 180.0,
        "remote_timeout": 180.0,
        "flash_command_timeout": 900.0,
        "ssh_connect_timeout": 8.0,
        "poll_interval": 3.0,
        "transfer_timeout": 1200.0,
    }
    for name, expected in exact.items():
        value = getattr(args, name, None)
        if (
            value != expected
            or isinstance(value, bool)
            or (isinstance(value, float) and not math.isfinite(value))
        ):
            raise ContractError(f"H24 live argument {name} changed")


def require_current_native_health(args: argparse.Namespace) -> dict[str, Any]:
    """Read and validate the exact H24 predecessor without a legacy allowlist."""
    health = {
        command: base.run_f1_cmd(args, [command])
        for command in ("version", "status", "selftest")
    }
    staging.validate_native_health_receipts(
        health,
        expected_version=CURRENT_VERSION,
        expected_build=CURRENT_BUILD,
    )
    return health


def require_current_native_health_on_exact_bridge(
    spec: Any,
    args: argparse.Namespace,
) -> dict[str, Any]:
    staging.require_exact_bridge(spec.stage, args)
    return require_current_native_health(args)


def exact_preflight(
    manifest: dict[str, Any],
    spec: Any,
    args: argparse.Namespace,
) -> dict[str, Any]:
    bridge = staging.require_exact_bridge(spec.stage, args)
    health = require_current_native_health(args)
    script = "\n".join(
        (
            "set -eu",
            '[ "$(/bin/busybox cat /sys/class/block/sda33/size)" = "231577432" ]',
            '/bin/busybox grep -qx "DEVNAME=sda33" /sys/class/block/sda33/uevent',
            '/bin/busybox grep -qx "PARTNAME=userdata" /sys/class/block/sda33/uevent',
            'DEVT=$(/bin/busybox cat /sys/class/block/sda33/dev)',
            'printf "%s\\n" "$DEVT" | /bin/busybox grep -Eq "^[0-9]+:[0-9]+$"',
            'if /bin/busybox grep -Eq "^/dev/block/(a90-userdata|sda33|by-name/userdata) | /mnt/a90-userdata-root " /proc/mounts; then exit 41; fi',
            f'[ ! -e "{ENABLE_PATH}" ] && [ ! -L "{ENABLE_PATH}" ]',
            f'[ ! -e "{LATCH_PATH}" ] && [ ! -L "{LATCH_PATH}" ]',
            "echo A90H24_F1_PRE exact=1 devt=$DEVT devt_policy=same-session-only ufs_mounted=0 enable_absent=1 latch_absent=1 userdata_write=0",
        )
    )
    record = base.run_f1_shell(args, script)
    marker = re.compile(
        r"^A90H24_F1_PRE exact=1 devt=[0-9]+:[0-9]+ "
        r"devt_policy=same-session-only ufs_mounted=0 enable_absent=1 "
        r"latch_absent=1 userdata_write=0$"
    )
    candidates = [
        line.strip()
        for line in str(record.get("text") or "").replace("\r", "").splitlines()
        if line.strip().startswith("A90H24_F1_PRE ")
    ]
    if len(candidates) != 1 or marker.fullmatch(candidates[0]) is None:
        raise ContractError("fresh H24 connected preflight is not exact")
    return {"bridge": bridge, "health": health, "ufs": record}


def validate_candidate_native_health(
    native: Any,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    if (
        not isinstance(native, dict)
        or native.get("exact_bridge") is not True
        or native.get("selected_realpath")
        != manifest.get("target", {}).get("bridge_realpath")
    ):
        raise ContractError("H24 candidate native health identity changed")
    version = base.require_exact_f1_command_receipt(
        native.get("version"), ["version"], "H24 candidate version"
    )
    selftest = base.require_exact_f1_command_receipt(
        native.get("selftest"), ["selftest"], "H24 candidate selftest"
    )
    version_line = f"version: {CANDIDATE_VERSION} build={CANDIDATE_BUILD}"
    version_facts = [
        line for line in str(version.get("text") or "").splitlines()
        if line.startswith("version: ")
    ]
    selftest_facts = [
        line for line in str(selftest.get("text") or "").splitlines()
        if line.startswith("selftest: ")
    ]
    if (
        version_facts != [version_line]
        or len(selftest_facts) != 1
        or staging.SELFTEST_FACT_RE.fullmatch(selftest_facts[0]) is None
    ):
        raise ContractError("H24 candidate native health facts changed")
    return native


def validate_h24_auto_status_record(
    record: Any,
    *,
    enable: int,
    latch: int,
) -> dict[str, Any]:
    exact = base.require_exact_f1_command_receipt(
        record,
        ["auto-handoff-status"],
        "H24 auto-handoff status",
    )
    lines = [
        line.strip()
        for line in str(exact.get("text") or "").replace("\r", "").splitlines()
        if line.strip().startswith("A90AUTO_STATUS")
    ]
    if len(lines) != 1:
        raise ContractError("H24 auto-handoff status is not unique")
    match = H24_AUTO_STATUS_RE.fullmatch(lines[0])
    if match is None:
        raise ContractError("H24 auto-handoff status shape changed")
    facts = {
        "binding": int(match.group("binding"), 10),
        "enable": int(match.group("enable"), 10),
        "latch": int(match.group("latch"), 10),
        "build": match.group("build"),
    }
    if facts != {
        "binding": 1,
        "enable": enable,
        "latch": latch,
        "build": CANDIDATE_BUILD,
    }:
        raise ContractError("H24 auto-handoff status facts changed")
    return facts


def exact_candidate_health(
    spec: Any,
    args: argparse.Namespace,
    guard: Any,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    health = base.verify_candidate_health(spec, args, return_guard=guard)
    validate_candidate_native_health(health, manifest)
    first_boot = base.require_candidate_first_boot_unarmed(spec, args)
    if not isinstance(first_boot, dict) or first_boot.get("proof") is not True:
        raise ContractError("H24 first boot is not exact unarmed resident health")
    combined = {"native": health, "first_boot": first_boot}
    return validate_stored_candidate_health(combined, manifest)


def validate_stored_candidate_health(
    health: Any,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    native = health.get("native") if isinstance(health, dict) else None
    first_boot = health.get("first_boot") if isinstance(health, dict) else None
    if (
        not isinstance(native, dict)
        or not isinstance(first_boot, dict)
        or first_boot.get("proof") is not True
        or first_boot.get("enable") != 0
        or first_boot.get("latch") != 0
        or first_boot.get("unarmed_log_unique") is not True
    ):
        raise ContractError("durable H24 candidate health changed")
    validate_candidate_native_health(native, manifest)
    validate_h24_auto_status_record(first_boot.get("status"), enable=0, latch=0)
    log = base.require_exact_f1_command_receipt(
        first_boot.get("log"), ["logcat"], "durable H24 first-boot log"
    )
    base.require_auto_handoff_log_exclusively_unarmed(
        str(log.get("text") or ""),
        "durable H24 first-boot log",
    )
    return health


def validate_stored_rollback_health(
    health: Any,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    if (
        not isinstance(health, dict)
        or health.get("exact_bridge") is not True
        or health.get("selected_realpath")
        != manifest.get("target", {}).get("bridge_realpath")
        or health.get("version") != ROLLBACK_VERSION
        or health.get("build") != ROLLBACK_BUILD
        or health.get("selftest_fail_zero") is not True
        or health.get("pstore_entries_zero") is not True
        or not isinstance(health.get("channel"), dict)
        or not isinstance(health.get("baseline"), dict)
    ):
        raise ContractError("durable rollback health changed")
    staging.validate_native_health_receipts(
        health["baseline"],
        expected_version=ROLLBACK_VERSION,
        expected_build=ROLLBACK_BUILD,
    )
    return health


def _release_guard(guard: Any, transaction_dir: Path) -> dict[str, Any]:
    release = base.release_candidate_return_modemmanager_guard(
        guard,
        transaction_dir,
        corridor="resident-promotion",
    )
    if release.get("released") is not True:
        raise ContractError("resident-promotion ModemManager guard did not release")
    return release


def _proc_stat(pid: int) -> tuple[str, int, int]:
    text = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    end = text.rfind(")")
    if end < 0:
        raise ContractError("flash process stat is malformed")
    fields = text[end + 2 :].split()
    if len(fields) < 20:
        raise ContractError("flash process stat is truncated")
    return fields[0], int(fields[2], 10), int(fields[19], 10)


def _process_group_members(pgid: int) -> list[dict[str, int]]:
    members: list[dict[str, int]] = []
    for item in Path("/proc").iterdir():
        if not item.name.isdigit():
            continue
        try:
            state, observed_pgid, start_ticks = _proc_stat(int(item.name, 10))
        except (OSError, ValueError, ContractError):
            continue
        if observed_pgid == pgid and state != "Z":
            members.append({"pid": int(item.name, 10), "start_ticks": start_ticks})
    return sorted(members, key=lambda value: value["pid"])


def _launch_path(transaction_dir: Path, rollback: bool) -> Path:
    kind = "rollback" if rollback else "candidate"
    return transaction_dir / f"{kind}-flash-launch.json"


def _require_launch_quiesced(
    transaction_dir: Path,
    journal: Path,
    manifest: dict[str, Any],
    manifest_sha: str,
    spec: Any,
    args: argparse.Namespace,
    rollback: bool,
) -> dict[str, Any]:
    kind = "rollback" if rollback else "candidate"
    path = _launch_path(transaction_dir, rollback)
    _, value = load_json_bound(bound_file(path), f"{kind}_flash_launch")
    records = read_journal(journal, manifest, manifest_sha)
    matches = [
        item for item in records if item.get("action") == f"{kind}-launch"
    ]
    artifact = manifest["rollback_boot" if rollback else "candidate_boot"]
    if (
        len(matches) != 1
        or matches[0].get("launch") != value
        or set(value)
        != {
            "schema",
            "kind",
            "leader_pid",
            "pgid",
            "leader_start_ticks",
            "command_sha256",
            "manifest_sha256",
            "artifact_sha256",
            "artifact_size",
            "flash_runner_sha256",
            "from_native",
            "release_count_max",
            "descendant_quiescence_required_before_recovery",
        }
        or value.get("schema") != "a90-h27-flash-process-group-v1"
        or value.get("kind") != kind
        or type(value.get("leader_pid")) is not int
        or value.get("leader_pid") <= 0
        or value.get("pgid") != value.get("leader_pid")
        or type(value.get("leader_start_ticks")) is not int
        or value.get("leader_start_ticks") <= 0
        or require_sha(value.get("command_sha256"), "launch.command_sha256")
        != value.get("command_sha256")
        or value.get("manifest_sha256") != manifest_sha
        or value.get("artifact_sha256") != artifact.get("sha256")
        or value.get("artifact_size") != artifact.get("size")
        or value.get("flash_runner_sha256")
        != manifest.get("flash_runner", {}).get("sha256")
        or type(value.get("from_native")) is not bool
        or (not rollback and value.get("from_native") is not True)
        or value.get("command_sha256")
        != json_sha256(
            base.flash_command(
                spec,
                args,
                rollback=rollback,
                from_native=value.get("from_native"),
            )
        )
        or value.get("release_count_max") != 1
        or value.get("descendant_quiescence_required_before_recovery") is not True
    ):
        raise ContractError(f"{kind} flash launch evidence is invalid")
    members = _process_group_members(value["pgid"])
    if members:
        raise ContractError(
            f"{kind} flash process group is still active; observe only and do not rollback"
        )
    return {"proof": True, "members": [], "launch": value}


def _terminate_flash_group(pid: int, *, leader_reaped: bool) -> None:
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    term_deadline = time.monotonic() + 5.0
    while time.monotonic() < term_deadline:
        if not leader_reaped:
            try:
                waited, _ = os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                leader_reaped = True
            else:
                leader_reaped = waited == pid
        if leader_reaped and not _process_group_members(pid):
            return
        time.sleep(0.05)
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    if not leader_reaped:
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass
    kill_deadline = time.monotonic() + 5.0
    while _process_group_members(pid):
        if time.monotonic() >= kill_deadline:
            raise ContractError(
                "flash process cleanup left a live descendant; rollback forbidden"
            )
        time.sleep(0.05)


def _wait_flash_group(pid: int, timeout: float) -> tuple[int, bool]:
    deadline = time.monotonic() + timeout
    while True:
        waited, status_value = os.waitpid(pid, os.WNOHANG)
        if waited == pid:
            returncode = os.waitstatus_to_exitcode(status_value)
            if _process_group_members(pid):
                _terminate_flash_group(pid, leader_reaped=True)
                return 124, True
            return returncode, False
        if time.monotonic() >= deadline:
            break
        time.sleep(0.1)
    _terminate_flash_group(pid, leader_reaped=False)
    return 124, True


def _flash_record(
    manifest: dict[str, Any],
    manifest_sha: str,
    spec: Any,
    args: argparse.Namespace,
    journal: Path,
    transaction_dir: Path,
    *,
    rollback: bool,
    from_native: bool,
) -> dict[str, Any]:
    kind = "rollback" if rollback else "candidate"
    name = f"{kind}-flash.raw.log"
    log_path = transaction_dir / name
    descriptor = os.open(
        log_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    gate_read, gate_write = os.pipe()
    ready_read, ready_write = os.pipe()
    command = base.flash_command(
        spec, args, rollback=rollback, from_native=from_native
    )
    command_sha256 = json_sha256(command)
    pid = os.fork()
    if pid == 0:  # child waits for a durable parent release before any flash code
        try:
            os.close(gate_write)
            os.close(ready_read)
            os.setsid()
            os.write(ready_write, b"R")
            os.close(ready_write)
            if os.read(gate_read, 1) != b"G":
                os._exit(126)
            os.close(gate_read)
            os.dup2(descriptor, 1)
            os.dup2(descriptor, 2)
            if descriptor > 2:
                os.close(descriptor)
            os.chdir(REPO_ROOT)
            os.execv(command[0], command)
        except BaseException:
            os._exit(125)
    os.close(gate_read)
    os.close(ready_write)
    child_reaped = False
    try:
        readable, _, _ = select.select([ready_read], [], [], 10.0)
        if not readable or os.read(ready_read, 1) != b"R":
            os.close(gate_write)
            gate_write = -1
            _, status_value = os.waitpid(pid, 0)
            child_reaped = True
            raise ContractError(
                "flash child did not enter the no-effect launch gate "
                f"rc={os.waitstatus_to_exitcode(status_value)}"
            )
        _, pgid, start_ticks = _proc_stat(pid)
        if pgid != pid:
            raise ContractError("flash child process group is not isolated")
        launch = {
            "schema": "a90-h27-flash-process-group-v1",
            "kind": kind,
            "leader_pid": pid,
            "pgid": pgid,
            "leader_start_ticks": start_ticks,
            "command_sha256": command_sha256,
            "manifest_sha256": manifest_sha,
            "artifact_sha256": (
                manifest["rollback_boot" if rollback else "candidate_boot"]["sha256"]
            ),
            "artifact_size": (
                manifest["rollback_boot" if rollback else "candidate_boot"]["size"]
            ),
            "flash_runner_sha256": manifest["flash_runner"]["sha256"],
            "from_native": from_native,
            "release_count_max": 1,
            "descendant_quiescence_required_before_recovery": True,
        }
        write_json_exclusive(_launch_path(transaction_dir, rollback), launch)
        append_journal(
            journal,
            manifest,
            manifest_sha,
            f"{kind}-launch",
            {
                "launch": launch,
                "candidate_replay": False,
                "rollback_replay": False,
            },
        )
        if os.write(gate_write, b"G") != 1:
            raise ContractError("flash child release was not exactly one byte")
        os.close(gate_write)
        gate_write = -1
        returncode, timed_out = _wait_flash_group(pid, args.flash_command_timeout)
        child_reaped = True
    except BaseException:
        if gate_write >= 0:
            os.close(gate_write)
            gate_write = -1
        if not child_reaped:
            try:
                _wait_flash_group(pid, 5.0)
            except BaseException:
                _terminate_flash_group(pid, leader_reaped=False)
            child_reaped = True
        raise
    finally:
        os.close(ready_read)
        if gate_write >= 0:
            os.close(gate_write)
        os.fsync(descriptor)
        os.close(descriptor)
    record = base.command_record(log_path, returncode)
    record["process_started"] = True
    record["process_group"] = {
        "leader_pid": pid,
        "pgid": pid,
        "timed_out": timed_out,
        "quiesced": True,
    }
    if timed_out:
        record["execution_error"] = {
            "type": "TimeoutExpired",
            "stage": "process-group-wait",
            "timeout_sec": args.flash_command_timeout,
            "descendants_terminated": True,
        }
    record["process_group_quiescence"] = _require_launch_quiesced(
        transaction_dir,
        journal,
        manifest,
        manifest_sha,
        spec,
        args,
        rollback,
    )
    revalidate_post_flash_inputs(manifest, rollback=rollback)
    record["phase_classification"] = base.classify_flash_log(
        log_path
    )
    return record


def _rollback(
    manifest: dict[str, Any],
    manifest_sha: str,
    spec: Any,
    args: argparse.Namespace,
    journal: Path,
    transaction_dir: Path,
    guard: Any,
    *,
    from_native: bool,
) -> dict[str, Any]:
    records = read_journal(journal, manifest, manifest_sha)
    intents = [item for item in records if item.get("action") == "rollback-intent"]
    launches = [item for item in records if item.get("action") == "rollback-launch"]
    expected_mode = "from-native" if from_native else "adb-recovery"
    if launches:
        raise ContractError("rollback launch already exists; effect replay refused")
    if intents:
        if (
            len(intents) != 1
            or intents[0].get("rollback_sha256") != ROLLBACK_SHA256
            or intents[0].get("rollback_attempt_limit") != 1
            or intents[0].get("candidate_replay") is not False
            or intents[0].get("recovery_mode") != expected_mode
        ):
            raise ContractError("existing rollback intent is not exact")
    else:
        append_journal(
            journal,
            manifest,
            manifest_sha,
            "rollback-intent",
            {
                "rollback_sha256": ROLLBACK_SHA256,
                "rollback_attempt_limit": 1,
                "candidate_replay": False,
                "recovery_mode": expected_mode,
            },
        )
    record = _flash_record(
        manifest,
        manifest_sha,
        spec,
        args,
        journal,
        transaction_dir,
        rollback=True,
        from_native=from_native,
    )
    append_journal(
        journal,
        manifest,
        manifest_sha,
        "rollback-result",
        {
            "rollback_transfer_count": (
                1
                if record["returncode"] == 0
                else 0
                if base.candidate_failure_is_definite_pre_session(record)
                else None
            ),
            "candidate_replay": False,
            "record": record,
        },
    )
    if record["returncode"] != 0:
        pending = ContractError("rollback result is uncertain; do not invoke it again")
        _park_recovery(manifest, manifest_sha, journal, pending)
        raise pending
    health = base.verify_final_health(spec, args, return_guard=guard)
    append_journal(
        journal,
        manifest,
        manifest_sha,
        "rollback-health",
        {"device_safety_state": "BASELINE_HEALTHY", "health": health},
    )
    return health


def _park_recovery(
    manifest: dict[str, Any],
    manifest_sha: str,
    journal: Path,
    exc: BaseException,
) -> None:
    actions = [item["action"] for item in read_journal(journal, manifest, manifest_sha)]
    if "recovery-required" not in actions:
        append_journal(
            journal,
            manifest,
            manifest_sha,
            "recovery-required",
            {
                "candidate_replay": False,
                "rollback_only": True,
                "reason": type(exc).__name__,
            },
        )


def _candidate_transfer_count(records: list[dict[str, Any]]) -> int | None:
    matches = [item for item in records if item.get("action") == "candidate-result"]
    if not matches:
        return None
    if len(matches) != 1:
        raise ContractError("candidate transfer count has duplicate durable results")
    count = matches[0].get("candidate_transfer_count")
    if isinstance(count, bool) or count not in (0, 1, None):
        raise ContractError("candidate transfer count is not exact")
    record = matches[0].get("record")
    if not isinstance(record, dict):
        raise ContractError("candidate flash record is absent")
    if record.get("returncode") == 0 and count != 1:
        raise ContractError("successful candidate result lost its transfer count")
    return count


def _reconstructed_candidate_transfer_is_proven(record: Any) -> bool:
    classification = (
        record.get("phase_classification") if isinstance(record, dict) else None
    )
    return bool(
        isinstance(classification, dict)
        and classification.get("boot_write_completed") is True
        and classification.get("readback_completed") is True
    )


def _reconstructed_flash_record(
    transaction_dir: Path,
    journal: Path,
    manifest: dict[str, Any],
    manifest_sha: str,
    spec: Any,
    args: argparse.Namespace,
    *,
    rollback: bool,
) -> dict[str, Any]:
    quiescence = _require_launch_quiesced(
        transaction_dir,
        journal,
        manifest,
        manifest_sha,
        spec,
        args,
        rollback,
    )
    revalidate_post_flash_inputs(manifest, rollback=rollback)
    kind = "rollback" if rollback else "candidate"
    log_path = transaction_dir / f"{kind}-flash.raw.log"
    if not log_path.is_file() or log_path.is_symlink():
        raise ContractError(f"{kind} flash log is unavailable for reconciliation")
    record = base.command_record(log_path, -1)
    record.update(
        {
            "process_started": True,
            "execution_error": {
                "type": "ParentExitOutcomeUnknown",
                "stage": "durable-result-publication",
            },
            "process_group_quiescence": quiescence,
            "phase_classification": base.classify_flash_log(log_path),
            "reconstructed_without_effect_replay": True,
        }
    )
    return record


def _historical_guard_inputs(transaction_dir: Path) -> tuple[dict[str, str], str]:
    path = transaction_dir / "resident-promotion-modemmanager-guard-arm.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("prior candidate guard evidence is unavailable") from exc
    guard_spec = value.get("guard_spec") if isinstance(value, dict) else None
    topology = value.get("topology") if isinstance(value, dict) else None
    receipt = value.get("receipt") if isinstance(value, dict) else None
    base.require_exact_modemmanager_guard_receipt(receipt, guard_spec, topology)
    if not isinstance(guard_spec, dict) or not isinstance(topology, str):
        raise ContractError("prior candidate guard input shape changed")
    return dict(guard_spec), topology


def recover(
    manifest_path: Path,
    manifest_sha: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    if args.operator_attended is not True:
        raise ContractError("A90 H24 recovery is attended-only")
    validate_live_args(args)
    manifest = load_manifest(manifest_path, manifest_sha)
    spec = _spec(manifest, manifest_path, manifest_sha)
    journal = _journal_dir(manifest)
    transaction_dir = journal.parent
    records = read_journal(journal, manifest, manifest_sha)
    require_consumed_approval(records, manifest, manifest_sha)
    actions = [item["action"] for item in records]
    if (
        "candidate-intent" not in actions
        or (
            "recovery-required" not in actions
            and "rollback-intent" not in actions
        )
        or "closed" in actions
        or "rollback-result" in actions
        or "rollback-launch" in actions
        or actions.count("rollback-intent") > 1
    ):
        raise ContractError(
            "rollback recovery requires one parked candidate and no released rollback"
        )
    if actions.count("candidate-launch") != 1:
        raise ContractError(
            "rollback recovery requires one durable candidate launch; intent-only "
            "state has no released device effect"
        )
    _require_launch_quiesced(
        transaction_dir,
        journal,
        manifest,
        manifest_sha,
        spec,
        args,
        False,
    )
    candidate_transfer_count = _candidate_transfer_count(records)
    prior_recovery_guard = any(
        (transaction_dir / f"rollback-recovery-{index}-modemmanager-guard-arm.json").exists()
        for index in (1, 2)
    )
    if prior_recovery_guard and (
        transaction_dir / "rollback-recovery-2-modemmanager-guard-arm.json"
    ).exists():
        raise ContractError(
            "both bounded recovery guard slots were consumed; repair host guard state only"
        )
    corridor = "rollback-recovery-2" if prior_recovery_guard else "rollback-recovery-1"
    prepared_inputs = None
    if args.recovery_path == "adb-recovery":
        prepared_inputs = _historical_guard_inputs(transaction_dir)
        from_native = False
    else:
        staging.require_exact_bridge(spec.stage, args)
        from_native = True
    prior_intents = [
        item for item in records if item.get("action") == "rollback-intent"
    ]
    if prior_intents and prior_intents[0].get("recovery_mode") != (
        "from-native" if from_native else "adb-recovery"
    ):
        raise ContractError("rollback recovery path differs from durable intent")
    guard = base.arm_candidate_return_modemmanager_guard(
        spec,
        args,
        transaction_dir,
        corridor=corridor,
        prepared_inputs=prepared_inputs,
    )
    base.modemmanager_guard_arm_evidence(
        transaction_dir,
        corridor,
        guard,
    )
    try:
        health = _rollback(
            manifest,
            manifest_sha,
            spec,
            args,
            journal,
            transaction_dir,
            guard,
            from_native=from_native,
        )
        result = {
            "schema": RESULT_SCHEMA,
            "status": "FAILED_CANDIDATE_RECOVERY_ROLLBACK_COMPLETE",
            "experiment_proof": experiment_proof("FAILED_CANDIDATE_RECOVERY_ROLLBACK_COMPLETE"),
            "run_id": manifest["run_id"],
            "manifest_sha256": manifest_sha,
            "device_safety_state": "BASELINE_HEALTHY",
            "candidate_attempt_count": 1,
            "candidate_transfer_count": candidate_transfer_count,
            "rollback_transfer_count": 1,
            "candidate_replay": False,
            "rootfs_payload_count": 0,
            "sd_stage_count": 0,
            "userdata_write_count": 0,
            "final_health": health,
        }
        release = base.release_candidate_return_modemmanager_guard(
            guard,
            transaction_dir,
            corridor=corridor,
        )
        if release.get("released") is not True:
            raise ContractError("rollback recovery guard did not release")
        result["guard_release"] = release
        append_journal(journal, manifest, manifest_sha, "closed", {"result": result})
        write_json_exclusive(transaction_dir / "result.json", result)
        return result
    except Exception:
        if guard.process is not None and guard.process.poll() is None:
            try:
                base.release_candidate_return_modemmanager_guard(
                    guard,
                    transaction_dir,
                    corridor=corridor,
                )
            except Exception:
                pass
        raise


def _publish_reconciled_result(
    manifest: dict[str, Any],
    manifest_sha: str,
    journal: Path,
    transaction_dir: Path,
    result: dict[str, Any],
) -> dict[str, Any]:
    records = read_journal(journal, manifest, manifest_sha)
    actions = [item["action"] for item in records]
    if "closed" not in actions:
        append_journal(
            journal,
            manifest,
            manifest_sha,
            "closed",
            {"result": result, "reconciled_without_effect_replay": True},
        )
    result_path = transaction_dir / "result.json"
    if result_path.exists():
        existing = json.loads(result_path.read_text(encoding="utf-8"))
        if existing != result:
            raise ContractError("existing H24 result differs from durable closure")
    else:
        write_json_exclusive(result_path, result)
    return result


def reconcile_health(
    manifest_path: Path,
    manifest_sha: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    """Finish only host publication or exact live health; never flash again."""
    if args.operator_attended is not True:
        raise ContractError("A90 H24 F1 health reconciliation is attended-only")
    validate_live_args(args)
    manifest = load_manifest(manifest_path, manifest_sha)
    spec = _spec(manifest, manifest_path, manifest_sha)
    journal = _journal_dir(manifest)
    transaction_dir = journal.parent
    records = read_journal(journal, manifest, manifest_sha)
    require_consumed_approval(records, manifest, manifest_sha)
    actions = [item["action"] for item in records]
    if actions.count("candidate-intent") != 1:
        raise ContractError("health reconciliation lacks one candidate intent")
    if actions.count("closed") > 1 or ("closed" in actions and actions[-1] != "closed"):
        raise ContractError("H24 closed record is not terminal")
    if "closed" in actions:
        result = records[-1].get("result")
        if (
            not isinstance(result, dict)
            or result.get("schema") != RESULT_SCHEMA
            or result.get("manifest_sha256") != manifest_sha
            or result.get("candidate_replay") is not False
            or result.get("rootfs_payload_count") != 0
            or result.get("sd_stage_count") != 0
            or result.get("userdata_write_count") != 0
        ):
            raise ContractError("durable H24 closed result is invalid")
        return _publish_reconciled_result(
            manifest, manifest_sha, journal, transaction_dir, result
        )

    candidate_count = _candidate_transfer_count(records)

    if "rollback-intent" in actions and "rollback-result" not in actions:
        launch_count = actions.count("rollback-launch")
        if actions.count("rollback-intent") != 1 or launch_count not in (0, 1):
            raise ContractError("rollback result gap is not one bounded attempt")
        if launch_count == 0:
            pending = ContractError(
                "rollback intent is durable but has no released launch"
            )
            _park_recovery(manifest, manifest_sha, journal, pending)
            raise ContractError(
                "resume the same bound rollback intent; running health cannot "
                "replace the required boot rollback"
            ) from pending
        rollback_record = _reconstructed_flash_record(
            transaction_dir,
            journal,
            manifest,
            manifest_sha,
            spec,
            args,
            rollback=True,
        )
        classification = rollback_record["phase_classification"]
        rollback_count = (
            1
            if classification.get("boot_write_completed") is True
            and classification.get("readback_completed") is True
            else 0
            if not any(
                classification.get(name) is True
                for name in (
                    "native_recovery_requested",
                    "recovery_endpoint_selected",
                    "payload_transfer_started",
                    "boot_write_started",
                )
            )
            else None
        )
        append_journal(
            journal,
            manifest,
            manifest_sha,
            "rollback-result",
            {
                "rollback_transfer_count": rollback_count,
                "candidate_replay": False,
                "record": rollback_record,
                "inferred_from_quiescent_process_group_log": True,
            },
        )
        if rollback_count != 1:
            pending = ContractError(
                "rollback release did not prove exact boot write and readback"
            )
            _park_recovery(manifest, manifest_sha, journal, pending)
            raise ContractError(
                "rollback outcome is parked with no replay; running baseline "
                "health cannot prove the boot partition bytes"
            ) from pending
        records = read_journal(journal, manifest, manifest_sha)
        actions = [item["action"] for item in records]

    if "rollback-result" in actions:
        if (
            actions.count("rollback-intent") != 1
            or actions.count("rollback-result") != 1
            or "candidate-health" in actions
        ):
            raise ContractError("rollback reconciliation is not one exact attempt")
        rollback_result = next(
            item for item in records if item.get("action") == "rollback-result"
        )
        rollback_record = rollback_result.get("record")
        if not isinstance(rollback_record, dict):
            raise ContractError("rollback transfer record is invalid")
        rollback_count = rollback_result.get("rollback_transfer_count")
        if rollback_count != 1:
            if actions.count("rollback-launch") == 1:
                _require_launch_quiesced(
                    transaction_dir,
                    journal,
                    manifest,
                    manifest_sha,
                    spec,
                    args,
                    True,
                )
            pending = ContractError(
                "durable rollback result does not prove one exact transfer"
            )
            _park_recovery(manifest, manifest_sha, journal, pending)
            raise ContractError(
                "rollback remains recovery-pending with no replay"
            ) from pending
        if (
            rollback_record.get("returncode") != 0
            and not (
                rollback_record.get("phase_classification", {}).get(
                    "boot_write_completed"
                )
                is True
                and rollback_record.get("phase_classification", {}).get(
                    "readback_completed"
                )
                is True
            )
        ):
            raise ContractError("rollback transfer count contradicts its result")
        if actions.count("rollback-launch") == 1:
            _require_launch_quiesced(
                transaction_dir,
                journal,
                manifest,
                manifest_sha,
                spec,
                args,
                True,
            )
        if actions.count("rollback-health") > 1:
            raise ContractError("rollback health evidence is duplicated")
        if "rollback-health" in actions:
            prior_health = next(
                item for item in records if item.get("action") == "rollback-health"
            )
            if (
                prior_health.get("device_safety_state") != "BASELINE_HEALTHY"
                or not isinstance(prior_health.get("health"), dict)
            ):
                raise ContractError("rollback health evidence is contradictory")
            health = validate_stored_rollback_health(
                prior_health["health"], manifest
            )
        else:
            health = base.verify_final_health(spec, args)
            append_journal(
                journal,
                manifest,
                manifest_sha,
                "rollback-health",
                {
                    "device_safety_state": "BASELINE_HEALTHY",
                    "health": health,
                    "reconciled_without_effect_replay": True,
                },
            )
        result = {
            "schema": RESULT_SCHEMA,
            "status": "FAILED_CANDIDATE_RECOVERY_ROLLBACK_COMPLETE",
            "experiment_proof": experiment_proof("FAILED_CANDIDATE_RECOVERY_ROLLBACK_COMPLETE"),
            "run_id": manifest["run_id"],
            "manifest_sha256": manifest_sha,
            "device_safety_state": "BASELINE_HEALTHY",
            "candidate_attempt_count": 1,
            "candidate_transfer_count": candidate_count,
            "rollback_transfer_count": rollback_count,
            "candidate_replay": False,
            "rootfs_payload_count": 0,
            "sd_stage_count": 0,
            "userdata_write_count": 0,
            "final_health": health,
            "reconciled_without_effect_replay": True,
            "rollback_count_inferred_by_exact_health": False,
        }
        return _publish_reconciled_result(
            manifest, manifest_sha, journal, transaction_dir, result
        )

    candidate_results = [
        item for item in records if item.get("action") == "candidate-result"
    ]
    if not candidate_results:
        if actions.count("candidate-launch") == 0:
            health = require_current_native_health_on_exact_bridge(spec, args)
            record = {
                "process_started": False,
                "release_count": 0,
                "reconstructed_without_effect_replay": True,
            }
            append_journal(
                journal,
                manifest,
                manifest_sha,
                "candidate-result",
                {
                    "candidate_attempt_count": 1,
                    "candidate_transfer_count": 0,
                    "candidate_replay": False,
                    "record": record,
                    "inferred_from_absent_launch": True,
                },
            )
            result = {
                "schema": RESULT_SCHEMA,
                "status": "ABORTED_BEFORE_CANDIDATE_RELEASE",
                "experiment_proof": experiment_proof("ABORTED_BEFORE_CANDIDATE_RELEASE"),
                "run_id": manifest["run_id"],
                "manifest_sha256": manifest_sha,
                "device_safety_state": "RESIDENT_HEALTHY",
                "candidate_attempt_count": 1,
                "candidate_transfer_count": 0,
                "rollback_transfer_count": 0,
                "candidate_replay": False,
                "rootfs_payload_count": 0,
                "sd_stage_count": 0,
                "userdata_write_count": 0,
                "final_health": health,
                "reconciled_without_effect_replay": True,
            }
            return _publish_reconciled_result(
                manifest, manifest_sha, journal, transaction_dir, result
            )
        if actions.count("candidate-launch") != 1:
            raise ContractError("candidate launch evidence is duplicated")
        candidate_record = _reconstructed_flash_record(
            transaction_dir,
            journal,
            manifest,
            manifest_sha,
            spec,
            args,
            rollback=False,
        )
        try:
            candidate_health = exact_candidate_health(spec, args, None, manifest)
        except Exception as candidate_exc:  # read-only alternate health follows
            try:
                starting_health = require_current_native_health_on_exact_bridge(
                    spec, args
                )
            except Exception:
                append_journal(
                    journal,
                    manifest,
                    manifest_sha,
                    "candidate-result",
                    {
                        "candidate_attempt_count": 1,
                        "candidate_transfer_count": None,
                        "candidate_replay": False,
                        "record": candidate_record,
                        "outcome_unknown_after_quiescence": True,
                    },
                )
                _park_recovery(manifest, manifest_sha, journal, candidate_exc)
                raise ContractError(
                    "candidate process group is quiescent but boot health is unknown; "
                    "resume bound rollback only"
                ) from candidate_exc
            classification = candidate_record["phase_classification"]
            session_started = any(
                classification.get(name) is True
                for name in (
                    "native_recovery_requested",
                    "recovery_endpoint_selected",
                    "payload_transfer_started",
                    "boot_write_started",
                )
            )
            candidate_count = None if session_started else 0
            append_journal(
                journal,
                manifest,
                manifest_sha,
                "candidate-result",
                {
                    "candidate_attempt_count": 1,
                    "candidate_transfer_count": candidate_count,
                    "candidate_replay": False,
                    "record": candidate_record,
                    "inferred_by_exact_starting_health": True,
                },
            )
            if session_started:
                pending = ContractError(
                    "candidate session or write marker exists without a durable result"
                )
                _park_recovery(manifest, manifest_sha, journal, pending)
                raise ContractError(
                    "candidate boot bytes are ambiguous; running V2321 health cannot "
                    "replace the bound rollback"
                ) from pending
            result = {
                "schema": RESULT_SCHEMA,
                "status": "ABORTED_BEFORE_CANDIDATE_SESSION",
                "experiment_proof": experiment_proof("ABORTED_BEFORE_CANDIDATE_SESSION"),
                "run_id": manifest["run_id"],
                "manifest_sha256": manifest_sha,
                "device_safety_state": "RESIDENT_HEALTHY",
                "candidate_attempt_count": 1,
                "candidate_transfer_count": candidate_count,
                "rollback_transfer_count": 0,
                "candidate_replay": False,
                "rootfs_payload_count": 0,
                "sd_stage_count": 0,
                "userdata_write_count": 0,
                "final_health": starting_health,
                "reconciled_without_effect_replay": True,
            }
            return _publish_reconciled_result(
                manifest, manifest_sha, journal, transaction_dir, result
            )
        else:
            if not _reconstructed_candidate_transfer_is_proven(candidate_record):
                append_journal(
                    journal,
                    manifest,
                    manifest_sha,
                    "candidate-result",
                    {
                        "candidate_attempt_count": 1,
                        "candidate_transfer_count": None,
                        "candidate_replay": False,
                        "record": candidate_record,
                        "candidate_health_observed_without_exact_transfer_proof": True,
                    },
                )
                pending = ContractError(
                    "candidate health cannot replace exact boot write and readback proof"
                )
                _park_recovery(manifest, manifest_sha, journal, pending)
                raise ContractError(
                    "candidate boot bytes are ambiguous despite running H24 health; "
                    "resume bound rollback only"
                ) from pending
            candidate_record["inferred_candidate_health"] = candidate_health
            append_journal(
                journal,
                manifest,
                manifest_sha,
                "candidate-result",
                {
                    "candidate_attempt_count": 1,
                    "candidate_transfer_count": 1,
                    "candidate_replay": False,
                    "record": candidate_record,
                    "inferred_by_exact_candidate_health": True,
                },
            )
            candidate_count = 1
            records = read_journal(journal, manifest, manifest_sha)
            actions = [item["action"] for item in records]
    elif len(candidate_results) != 1:
        raise ContractError("candidate result evidence is duplicated")
    else:
        candidate_count = _candidate_transfer_count(records)
        candidate_record = candidate_results[0].get("record")
        if not isinstance(candidate_record, dict):
            raise ContractError("candidate result record is invalid")

    if candidate_count == 1:
        if "rollback-intent" in actions or "rollback-health" in actions:
            raise ContractError("rollback intent exists without a proven rollback result")
        if actions.count("candidate-health") > 1:
            raise ContractError("candidate health evidence is duplicated")
        if "candidate-health" in actions:
            prior_health = next(
                item for item in records if item.get("action") == "candidate-health"
            )
            if (
                prior_health.get("device_safety_state") != "RESIDENT_HEALTHY"
                or not isinstance(prior_health.get("health"), dict)
            ):
                raise ContractError("candidate health evidence is contradictory")
            health = validate_stored_candidate_health(
                prior_health["health"], manifest
            )
        else:
            try:
                health = exact_candidate_health(spec, args, None, manifest)
            except Exception as exc:
                _park_recovery(manifest, manifest_sha, journal, exc)
                raise ContractError(
                    "candidate result is durable but exact initial health is absent; "
                    "resume bound rollback only"
                ) from exc
            append_journal(
                journal,
                manifest,
                manifest_sha,
                "candidate-health",
                {
                    "device_safety_state": "RESIDENT_HEALTHY",
                    "health": health,
                    "reconciled_without_effect_replay": True,
                },
            )
        result = {
            "schema": RESULT_SCHEMA,
            "status": "PASS_A90_H27_UFS_RESIDENT_INSTALLED",
            "experiment_proof": experiment_proof("PASS_A90_H27_UFS_RESIDENT_INSTALLED"),
            "run_id": manifest["run_id"],
            "manifest_sha256": manifest_sha,
            "device_safety_state": "RESIDENT_HEALTHY",
            "candidate_attempt_count": 1,
            "candidate_transfer_count": 1,
            "rollback_transfer_count": 0,
            "candidate_replay": False,
            "rootfs_payload_count": 0,
            "sd_stage_count": 0,
            "userdata_write_count": 0,
            "final_health": health,
            "reconciled_without_effect_replay": True,
        }
    elif base.candidate_failure_is_definite_pre_session(candidate_record):
        if "rollback-intent" in actions or candidate_count != 0:
            raise ContractError("pre-session abort evidence is inconsistent")
        health = require_current_native_health_on_exact_bridge(spec, args)
        result = {
            "schema": RESULT_SCHEMA,
            "status": "ABORTED_BEFORE_CANDIDATE_SESSION",
            "experiment_proof": experiment_proof("ABORTED_BEFORE_CANDIDATE_SESSION"),
            "run_id": manifest["run_id"],
            "manifest_sha256": manifest_sha,
            "device_safety_state": "RESIDENT_HEALTHY",
            "candidate_attempt_count": 1,
            "candidate_transfer_count": 0,
            "rollback_transfer_count": 0,
            "candidate_replay": False,
            "rootfs_payload_count": 0,
            "sd_stage_count": 0,
            "userdata_write_count": 0,
            "final_health": health,
            "reconciled_without_effect_replay": True,
        }
    else:
        pending = ContractError(
            "candidate result is durable but its transfer count is ambiguous"
        )
        _park_recovery(manifest, manifest_sha, journal, pending)
        raise ContractError(
            "candidate outcome is recovery-pending; reconcile cannot close or replay"
        ) from pending
    return _publish_reconciled_result(
        manifest, manifest_sha, journal, transaction_dir, result
    )


def execute(manifest_path: Path, manifest_sha: str, args: argparse.Namespace) -> dict[str, Any]:
    if args.operator_attended is not True:
        raise ContractError("A90 H24 F1 is attended-only")
    validate_live_args(args)
    manifest = load_manifest(manifest_path, manifest_sha)
    _, inventory = load_json_bound(
        manifest.get("ufs_root", {}).get("inventory"),
        "ufs_root.inventory",
    )
    validate_ufs_inventory(
        inventory,
        expected_run_id=manifest["run_id"],
        expected_bridge_realpath=manifest["target"]["bridge_realpath"],
        enforce_fresh=True,
    )
    spec = _spec(manifest, manifest_path, manifest_sha)
    journal = _journal_dir(manifest)
    transaction_dir = journal.parent
    records = read_journal(journal, manifest, manifest_sha)
    if records:
        raise ContractError("fresh H24 execution requires an empty durable journal")
    preflight = exact_preflight(manifest, spec, args)
    approval = validate_approval(manifest, manifest_sha, args.approval)
    approval_binding_value = approval["approval_binding"]
    approval_binding_sha = approval["approval_binding_sha256"]
    append_journal(
        journal,
        manifest,
        manifest_sha,
        "approval-consumed",
        {
            "approval_binding": approval_binding_value,
            "approval_binding_sha256": approval_binding_sha,
            "approval_token_sha256": hashlib.sha256(
                str(approval["approval_token"]).encode("utf-8")
            ).hexdigest(),
            "approval_consumed": True,
            "device_safety_state": "RESIDENT_HEALTHY",
            "candidate_transfer_count": 0,
            "rollback_transfer_count": 0,
            "rootfs_payload_count": 0,
            "sd_stage_count": 0,
            "userdata_write_count": 0,
            "preflight": preflight,
        },
    )

    guard = base.arm_candidate_return_modemmanager_guard(
        spec,
        args,
        transaction_dir,
        corridor="resident-promotion",
    )
    guard_evidence = base.modemmanager_guard_arm_evidence(
        transaction_dir,
        "resident-promotion",
        guard,
    )
    append_journal(
        journal,
        manifest,
        manifest_sha,
        "guard-armed",
        {"guard": guard_evidence, "candidate_replay": False},
    )
    append_journal(
        journal,
        manifest,
        manifest_sha,
        "candidate-intent",
        {
            "candidate_sha256": spec.candidate.sha256,
            "candidate_attempt_limit": 1,
            "partition": "boot",
            "rollback_pre_authorized": True,
            "approval_binding_sha256": approval_binding_sha,
            "candidate_replay": False,
            "rootfs_payload_count": 0,
            "sd_stage_count": 0,
            "userdata_write_count": 0,
        },
    )
    try:
        record = _flash_record(
            manifest,
            manifest_sha,
            spec,
            args,
            journal,
            transaction_dir,
            rollback=False,
            from_native=True,
        )
        if record["returncode"] == 0:
            candidate_transfer_count = 1
        elif base.candidate_failure_is_definite_pre_session(record):
            candidate_transfer_count = 0
        else:
            candidate_transfer_count = None
        append_journal(
            journal,
            manifest,
            manifest_sha,
            "candidate-result",
            {
                "candidate_attempt_count": 1,
                "candidate_transfer_count": candidate_transfer_count,
                "candidate_replay": False,
                "record": record,
            },
        )
        if record["returncode"] != 0:
            if base.candidate_failure_is_definite_pre_session(record):
                starting_health = require_current_native_health_on_exact_bridge(
                    spec, args
                )
                result = {
                    "schema": RESULT_SCHEMA,
                    "status": "ABORTED_BEFORE_CANDIDATE_SESSION",
                    "experiment_proof": experiment_proof("ABORTED_BEFORE_CANDIDATE_SESSION"),
                    "run_id": manifest["run_id"],
                    "manifest_sha256": manifest_sha,
                    "device_safety_state": "RESIDENT_HEALTHY",
                    "candidate_attempt_count": 1,
                    "candidate_transfer_count": 0,
                    "rollback_transfer_count": 0,
                    "candidate_replay": False,
                    "rootfs_payload_count": 0,
                    "sd_stage_count": 0,
                    "userdata_write_count": 0,
                    "final_health": starting_health,
                }
            else:
                try:
                    base.require_rollback_source_native(
                        spec, args, return_guard=guard
                    )
                except Exception as exc:  # noqa: BLE001 - exact recovery park
                    _park_recovery(manifest, manifest_sha, journal, exc)
                    raise ContractError(
                        "candidate result uncertain; enter bound TWRP/Download path "
                        "and resume rollback only"
                    ) from exc
                health = _rollback(
                    manifest,
                    manifest_sha,
                    spec,
                    args,
                    journal,
                    transaction_dir,
                    guard,
                    from_native=True,
                )
                result = {
                    "schema": RESULT_SCHEMA,
                    "status": "FAILED_CANDIDATE_ROLLED_BACK",
                    "experiment_proof": experiment_proof("FAILED_CANDIDATE_ROLLED_BACK"),
                    "run_id": manifest["run_id"],
                    "manifest_sha256": manifest_sha,
                    "device_safety_state": "BASELINE_HEALTHY",
                    "candidate_attempt_count": 1,
                    "candidate_transfer_count": candidate_transfer_count,
                    "rollback_transfer_count": 1,
                    "candidate_replay": False,
                    "rootfs_payload_count": 0,
                    "sd_stage_count": 0,
                    "userdata_write_count": 0,
                    "final_health": health,
                }
        else:
            try:
                health = exact_candidate_health(spec, args, guard, manifest)
            except Exception as health_exc:  # noqa: BLE001 - rollback is mandatory
                try:
                    base.require_rollback_source_native(
                        spec, args, return_guard=guard
                    )
                except Exception as recovery_exc:  # noqa: BLE001 - park rollback only
                    _park_recovery(
                        manifest,
                        manifest_sha,
                        journal,
                        recovery_exc,
                    )
                    raise ContractError(
                        "candidate initial health is not proven and native rollback "
                        "source is unavailable; enter bound recovery and resume "
                        "rollback only"
                    ) from health_exc
                rollback_health = _rollback(
                    manifest,
                    manifest_sha,
                    spec,
                    args,
                    journal,
                    transaction_dir,
                    guard,
                    from_native=True,
                )
                result = {
                    "schema": RESULT_SCHEMA,
                    "status": "FAILED_INITIAL_HEALTH_ROLLED_BACK",
                    "experiment_proof": experiment_proof("FAILED_INITIAL_HEALTH_ROLLED_BACK"),
                    "run_id": manifest["run_id"],
                    "manifest_sha256": manifest_sha,
                    "device_safety_state": "BASELINE_HEALTHY",
                    "candidate_attempt_count": 1,
                    "candidate_transfer_count": 1,
                    "rollback_transfer_count": 1,
                    "candidate_replay": False,
                    "rootfs_payload_count": 0,
                    "sd_stage_count": 0,
                    "userdata_write_count": 0,
                    "final_health": rollback_health,
                }
            else:
                append_journal(
                    journal,
                    manifest,
                    manifest_sha,
                    "candidate-health",
                    {
                        "device_safety_state": "RESIDENT_HEALTHY",
                        "health": health,
                    },
                )
                result = {
                    "schema": RESULT_SCHEMA,
                    "status": "PASS_A90_H27_UFS_RESIDENT_INSTALLED",
                    "experiment_proof": experiment_proof("PASS_A90_H27_UFS_RESIDENT_INSTALLED"),
                    "run_id": manifest["run_id"],
                    "manifest_sha256": manifest_sha,
                    "device_safety_state": "RESIDENT_HEALTHY",
                    "candidate_attempt_count": 1,
                    "candidate_transfer_count": 1,
                    "rollback_transfer_count": 0,
                    "candidate_replay": False,
                    "rootfs_payload_count": 0,
                    "sd_stage_count": 0,
                    "userdata_write_count": 0,
                    "final_health": health,
                }
        release = _release_guard(guard, transaction_dir)
        result["guard_release"] = release
        append_journal(journal, manifest, manifest_sha, "closed", {"result": result})
        write_json_exclusive(transaction_dir / "result.json", result)
        return result
    except Exception:
        if guard.process is not None and guard.process.poll() is None:
            try:
                _release_guard(guard, transaction_dir)
            except Exception:
                pass
        raise


def audit(manifest_path: Path, manifest_sha: str) -> dict[str, Any]:
    manifest = load_manifest(manifest_path, manifest_sha)
    return {
        "schema": "a90-h27-ufs-f1-audit-v1",
        "status": "PASS_HOST_CLOSURE",
        "run_id": manifest["run_id"],
        "manifest_sha256": manifest_sha,
        "execution_closure_sha256": manifest["execution_closure"]["sha256"],
        "candidate_sha256": manifest["candidate_boot"]["sha256"],
        "rollback_sha256": manifest["rollback_boot"]["sha256"],
        "rootfs_payload_count": 0,
        "sd_stage_count": 0,
        "userdata_write_count": 0,
        "s22plus_command_count": 0,
        "s20plus_command_count": 0,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="mode", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--run-id", required=True)
    prepare.add_argument("--candidate", type=Path, required=True)
    prepare.add_argument("--ab-receipt", type=Path, required=True)
    prepare.add_argument("--baseline-manifest", type=Path, required=True)
    prepare.add_argument("--baseline-result", type=Path, required=True)
    prepare.add_argument("--baseline-d1-transaction", type=Path, required=True)
    prepare.add_argument("--ufs-inventory", type=Path, required=True)
    prepare.add_argument("--qualification", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)

    for name in (
        "audit",
        "prepare-approval",
        "execute",
        "recover",
        "reconcile-health",
    ):
        item = sub.add_parser(name)
        item.add_argument("--manifest", type=Path, required=True)
        item.add_argument("--expect-manifest-sha256", required=True)
        if name in {"execute", "recover", "reconcile-health"}:
            item.add_argument("--operator-attended", action="store_true")
            item.add_argument("--bridge-host", default="127.0.0.1")
            item.add_argument("--bridge-port", type=int, default=54321)
            item.add_argument("--bridge-timeout", type=float, default=180.0)
            item.add_argument("--remote-timeout", type=float, default=180.0)
            item.add_argument("--flash-command-timeout", type=float, default=900.0)
            item.add_argument("--ssh-connect-timeout", type=float, default=8.0)
            item.add_argument("--poll-interval", type=float, default=3.0)
            item.add_argument("--transfer-timeout", type=float, default=1200.0)
        if name == "execute":
            item.add_argument("--approval", required=True)
        if name == "recover":
            item.add_argument(
                "--recovery-path",
                choices=("from-native", "adb-recovery"),
                required=True,
            )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.mode == "prepare":
            value = build_manifest(args)
            write_json_exclusive(args.output, value)
        elif args.mode == "audit":
            value = audit(args.manifest, args.expect_manifest_sha256)
        elif args.mode == "prepare-approval":
            value = prepare_approval(
                args.manifest,
                args.expect_manifest_sha256,
            )
        elif args.mode == "execute":
            value = execute(
                args.manifest,
                args.expect_manifest_sha256,
                args,
            )
        elif args.mode == "recover":
            value = recover(
                args.manifest,
                args.expect_manifest_sha256,
                args,
            )
        else:
            value = reconcile_health(
                args.manifest,
                args.expect_manifest_sha256,
                args,
            )
    except (ContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"H24_UFS_F1_ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

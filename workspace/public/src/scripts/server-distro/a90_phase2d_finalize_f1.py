#!/usr/bin/env python3
"""Finalize one host-prepared A90 V3406 display F1 manifest.

The default mode is host-only audit.  Finalization reopens the reviewed
keyed-rootfs, connected D0/path evidence, Phase 2 candidate, exact V2321
rollback, and current execution sources.  It creates private boot copies,
host-preparation evidence, and one immutable final manifest.  It cannot
contact a device, stage the rootfs, flash, reboot, or grant F1 authority.
"""

from __future__ import annotations

import argparse
import ast
import copy
import datetime as dt
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_phase2d_connected_preflight as connected  # noqa: E402
import a90_v3403_absent_only_staging as staging  # noqa: E402
import a90_v3403_f1_orchestrator as orchestrator  # noqa: E402


SCHEMA = "a90_phase2d_f1_finalizer_v1"
PASS_DECISION = "A90_PHASE2D_V3406_FINAL_MANIFEST_HOST_PASS"
REVIEW_DECISION = "GO_A90_RETURN_EPOCH_PRESENTER_DIAGNOSTICS_H0"
RUN_ID_RE = connected.RUN_ID_RE
PRIVATE_RUN_BASE = staging.PRIVATE_RUN_BASE
KEYED_SUMMARY_NAME = "keyed-rootfs-summary.json"
FINAL_MANIFEST_NAME = "prepared-manifest.json"
HOST_PREPARATION_NAME = "host-preparation.json"
ROLLBACK_COPY_NAME = "rollback-boot-v2321.img"
ROLLBACK_SOURCE = (
    staging.PRIVATE_ROOT
    / "inputs"
    / "boot_images"
    / "boot_linux_v2321_usb_clean_identity_rodata.img"
)
ROLLBACK_SHA256 = (
    "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
)
ROLLBACK_SIZE = 60882944
TEMPLATE_SCHEMA = staging.FINAL_MANIFEST_SCHEMA
TEMPLATE_RUN_ID_RE = re.compile(
    r"^a90-v3405-debian-f1-[0-9]{8}-[0-9]{2}$"
)


@dataclass(frozen=True)
class CandidateSpec:
    profile: str
    copy_name: str
    source: Path
    size: int
    sha256: str
    version: str
    build: str
    build_receipt: Path | None = None
    build_receipt_sha256: str | None = None
    compiled_auto_handoff: dict[str, str] | None = None


LEGACY_CANDIDATE_PROFILE = "phase2-display-v1"
MINIMAL_F_CANDIDATE_PROFILE = "phase3-minimal-f-power-recovery-ui"
MINIMAL_G_CANDIDATE_PROFILE = "phase3-minimal-g-server-core"
MINIMAL_H2_CANDIDATE_PROFILE = "phase3-minimal-h2-two-phase-auto-benchmark"
MINIMAL_H3_CANDIDATE_PROFILE = "phase3-minimal-h3-exact-binding-auto-benchmark"
MINIMAL_H4_CANDIDATE_PROFILE = (
    "phase3-minimal-h4-observer-complete-auto-benchmark"
)
MINIMAL_H5_CANDIDATE_PROFILE = (
    "phase3-minimal-h5-fresh-campaign-auto-benchmark"
)
MINIMAL_H6_CANDIDATE_PROFILE = (
    "phase3-minimal-h6-observer-complete-baseline-auto-benchmark"
)
LEGACY_CANDIDATE = CandidateSpec(
    profile=LEGACY_CANDIDATE_PROFILE,
    copy_name="candidate-boot-phase2-display-v1.img",
    source=(
        staging.PRIVATE_ROOT
        / "outputs"
        / "a90-phase2-display-v1-native-ab-02"
        / "A"
        / "boot.img"
    ),
    size=66379776,
    sha256="3d3e66535654a62f83c5772caba27624acc160911307190de458154acaefdabb",
    version="0.11.161",
    build="phase2-display-v1-native-handoff",
)
MINIMAL_F_CANDIDATE = CandidateSpec(
    profile=MINIMAL_F_CANDIDATE_PROFILE,
    copy_name="candidate-boot-phase3-minimal-f.img",
    source=(
        staging.PRIVATE_ROOT
        / "outputs"
        / "a90-phase3-minimal-f-ab-20260804-02"
        / "A"
        / "boot.img"
    ),
    size=61440000,
    sha256="93ac207f6008959f663ec3df60e9bfd43ee855f72e57a4967c93bd0aa49d2d6f",
    version="0.11.167",
    build="phase3-minimal-f-power-recovery-ui",
)
MINIMAL_G_CANDIDATE = CandidateSpec(
    profile=MINIMAL_G_CANDIDATE_PROFILE,
    copy_name="candidate-boot-phase3-minimal-g.img",
    source=(
        staging.PRIVATE_ROOT
        / "outputs"
        / "a90-phase3-minimal-g-ab-20260805-06"
        / "A"
        / "boot.img"
    ),
    size=58306560,
    sha256="f6eccc8e8b372e957d67e64e088acea4f7fddf351873d7c297e1fa4393f4169a",
    version="0.11.168",
    build="phase3-minimal-g-server-core",
)
MINIMAL_H2_CANDIDATE = CandidateSpec(
    profile=MINIMAL_H2_CANDIDATE_PROFILE,
    copy_name="candidate-boot-phase3-minimal-h2.img",
    source=(
        staging.PRIVATE_ROOT
        / "outputs"
        / "a90-phase3-minimal-h2-auto-benchmark-h0-20260805-08"
        / "A"
        / "boot.img"
    ),
    size=58372096,
    sha256="97cfbb149361773e895a2a1cff0f13961c06f0a4710119159d6d2a104bc69802",
    version="0.11.170",
    build="phase3-minimal-h2-two-phase-auto-benchmark",
)
MINIMAL_H3_CANDIDATE = CandidateSpec(
    profile=MINIMAL_H3_CANDIDATE_PROFILE,
    copy_name="candidate-boot-phase3-minimal-h3.img",
    source=(
        staging.PRIVATE_ROOT
        / "outputs"
        / "a90-phase3-minimal-h3-exact-binding-h0-20260805-01"
        / "A"
        / "boot.img"
    ),
    size=58372096,
    sha256="7962bf74707f8d038300795bd6918d6608eaff9ee491ed99230c95151f9f52ff",
    version="0.11.171",
    build="phase3-minimal-h3-exact-binding-auto-benchmark",
    build_receipt=(
        staging.PRIVATE_ROOT
        / "outputs"
        / "a90-phase3-minimal-h3-exact-binding-h0-20260805-01"
        / "ab-receipt.json"
    ),
    build_receipt_sha256=(
        "cdb352f98d95e9838d153071670df3a753a6074dd35e9914ccf2324160314101"
    ),
    compiled_auto_handoff={
        "schema": "a90-compiled-auto-handoff-binding-v1",
        "candidate_version": "0.11.171",
        "candidate_build": "phase3-minimal-h3-exact-binding-auto-benchmark",
        "image_path": "/mnt/sdext/a90/runtime/debian-bookworm-arm64-phase2-display-v3406-keyed-20260805-10.img",
        "image_sha256": "34de408d868ff0651d0f6efb1d1d9cc810e3dfe23acaac178e73e2840b2979a4",
        "enable_path": "/cache/a90-auto-handoff-phase3-minimal-h3.enable",
        "latch_path": "/cache/a90-auto-handoff-phase3-minimal-h3.done",
        "binding_sha256": "73ee6b413f2c3710c7582260cfd4fd52980dd819530beff579e8556ac0fefcfd",
    },
)
MINIMAL_H4_CANDIDATE = CandidateSpec(
    profile=MINIMAL_H4_CANDIDATE_PROFILE,
    copy_name="candidate-boot-phase3-minimal-h4.img",
    source=(
        staging.PRIVATE_ROOT
        / "outputs"
        / "a90-phase3-minimal-h4-observer-complete-h0-20260805-02"
        / "A"
        / "boot.img"
    ),
    size=58372096,
    sha256="6bc133937f19482739037b67a44b1f2b5da6da9a178a3edf8a9f2e74bd097935",
    version="0.11.172",
    build="phase3-minimal-h4-observer-complete-auto-benchmark",
    build_receipt=(
        staging.PRIVATE_ROOT
        / "outputs"
        / "a90-phase3-minimal-h4-observer-complete-h0-20260805-02"
        / "ab-receipt.json"
    ),
    build_receipt_sha256=(
        "01831ac20c55da7bc588fffef9ca3ed4922b556d2d1aef079fc8c89b021f4924"
    ),
    compiled_auto_handoff={
        "schema": "a90-compiled-auto-handoff-binding-v1",
        "candidate_version": "0.11.172",
        "candidate_build": "phase3-minimal-h4-observer-complete-auto-benchmark",
        "image_path": "/mnt/sdext/a90/runtime/debian-bookworm-arm64-phase2-display-v3406-keyed-20260805-11.img",
        "image_sha256": "8b4bfd99a9324c0a32e76c837e33282afa79739fa32645e3303861e8928a33fa",
        "enable_path": "/cache/a90-auto-handoff-phase3-minimal-h4.enable",
        "latch_path": "/cache/a90-auto-handoff-phase3-minimal-h4.done",
        "binding_sha256": "783a528a541e3a8edf82543d7352ed2e47f5d3393245d413ee8507df6e797e09",
    },
)
MINIMAL_H5_CANDIDATE = CandidateSpec(
    profile=MINIMAL_H5_CANDIDATE_PROFILE,
    copy_name="candidate-boot-phase3-minimal-h5.img",
    source=(
        staging.PRIVATE_ROOT
        / "outputs"
        / "server-distro"
        / "a90-phase3-minimal-h5-fresh-campaign-h0-20260805-01"
        / "A"
        / "boot.img"
    ),
    size=58372096,
    sha256="8ceda5ac0924c0fc1f8526bbd3632fd5e6f1a8cdd59b03c978efb09bbb1acd9b",
    version="0.11.173",
    build="phase3-minimal-h5-fresh-campaign-auto-benchmark",
    build_receipt=(
        staging.PRIVATE_ROOT
        / "outputs"
        / "server-distro"
        / "a90-phase3-minimal-h5-fresh-campaign-h0-20260805-01"
        / "ab-receipt.json"
    ),
    build_receipt_sha256=(
        "8d5423f9d109bf2ef1ac6f2aaeb5c4876885ad8a2beb4fc19fb0f01b2e105157"
    ),
    compiled_auto_handoff={
        "schema": "a90-compiled-auto-handoff-binding-v1",
        "candidate_version": "0.11.173",
        "candidate_build": "phase3-minimal-h5-fresh-campaign-auto-benchmark",
        "image_path": "/mnt/sdext/a90/runtime/debian-bookworm-arm64-phase2-display-v3406-keyed-20260805-12.img",
        "image_sha256": "874291801573d96bf7731b2cdc27deca066221450534365eddfa2acf41ab681e",
        "enable_path": "/cache/a90-auto-handoff-phase3-minimal-h5.enable",
        "latch_path": "/cache/a90-auto-handoff-phase3-minimal-h5.done",
        "binding_sha256": "243c65b770393e31c34048a4ec5ffea3032022b4de1d437e4e3ef1e7637d14f0",
    },
)
MINIMAL_H6_CANDIDATE = CandidateSpec(
    profile=MINIMAL_H6_CANDIDATE_PROFILE,
    copy_name="candidate-boot-phase3-minimal-h6.img",
    source=(
        staging.PRIVATE_ROOT
        / "outputs"
        / "server-distro"
        / "a90-phase3-minimal-h6-observer-complete-baseline-h0-20260807-03"
        / "A"
        / "boot.img"
    ),
    size=58372096,
    sha256="aa7cba7f730e12b08f6498a3307493eed033674d51c968b4ea4d2d3280ea98bb",
    version="0.11.174",
    build="phase3-minimal-h6-observer-complete-baseline-auto-benchmark",
    build_receipt=(
        staging.PRIVATE_ROOT
        / "outputs"
        / "server-distro"
        / "a90-phase3-minimal-h6-observer-complete-baseline-h0-20260807-03"
        / "ab-receipt.json"
    ),
    build_receipt_sha256=(
        "e0e2544770d1538ddc566d41e1a878db687a4da61a1926d994544f657d43cfd3"
    ),
    compiled_auto_handoff={
        "schema": "a90-compiled-auto-handoff-binding-v1",
        "candidate_version": "0.11.174",
        "candidate_build": "phase3-minimal-h6-observer-complete-baseline-auto-benchmark",
        "image_path": "/mnt/sdext/a90/runtime/debian-bookworm-arm64-phase2-display-v3406-keyed-20260807-03.img",
        "image_sha256": "feea09dd81fc342032c94629f47d06e743788efc9dc7bba9ca0067f346d4d490",
        "enable_path": "/cache/a90-auto-handoff-phase3-minimal-h6.enable",
        "latch_path": "/cache/a90-auto-handoff-phase3-minimal-h6.done",
        "binding_sha256": "238a1ae3aa1f4a2a1a8c46d8368fa4e025d0a0be7fb4ed77e7ccd80b410d1483",
    },
)
CANDIDATE_PROFILES = {
    item.profile: item
    for item in (
        LEGACY_CANDIDATE,
        MINIMAL_F_CANDIDATE,
        MINIMAL_G_CANDIDATE,
        MINIMAL_H2_CANDIDATE,
        MINIMAL_H3_CANDIDATE,
        MINIMAL_H4_CANDIDATE,
        MINIMAL_H5_CANDIDATE,
        MINIMAL_H6_CANDIDATE,
    )
}

# Backward-compatible aliases for the original single-candidate API.
CANDIDATE_COPY_NAME = LEGACY_CANDIDATE.copy_name
CANDIDATE_SOURCE = LEGACY_CANDIDATE.source
CANDIDATE_SIZE = LEGACY_CANDIDATE.size
CANDIDATE_SHA256 = LEGACY_CANDIDATE.sha256
CANDIDATE_VERSION = LEGACY_CANDIDATE.version
CANDIDATE_BUILD = LEGACY_CANDIDATE.build


def select_candidate_profile(profile: str) -> CandidateSpec:
    try:
        candidate = CANDIDATE_PROFILES[profile]
    except KeyError as exc:
        raise ContractError("candidate profile is not exact") from exc
    validate_candidate_build_receipt(candidate)
    return candidate


def validate_candidate_build_receipt(candidate: CandidateSpec) -> None:
    fields = (
        candidate.build_receipt,
        candidate.build_receipt_sha256,
        candidate.compiled_auto_handoff,
    )
    if fields == (None, None, None):
        return
    if any(value is None for value in fields):
        raise ContractError("candidate build receipt binding is incomplete")
    assert candidate.build_receipt is not None
    assert candidate.build_receipt_sha256 is not None
    assert candidate.compiled_auto_handoff is not None
    if candidate.build_receipt.is_symlink():
        raise ContractError("candidate build receipt must not be a symbolic link")
    receipt_path = candidate.build_receipt.resolve(strict=True)
    staging.require_below(receipt_path, staging.PRIVATE_ROOT, "candidate build receipt")
    receipt_info = receipt_path.lstat()
    if (
        not stat.S_ISREG(receipt_info.st_mode)
        or receipt_info.st_mode & 0o077
        or receipt_info.st_mode & 0o022
    ):
        raise ContractError("candidate build receipt is not exact private input")
    if sha256_file(receipt_path) != candidate.build_receipt_sha256:
        raise ContractError("candidate build receipt SHA256 changed")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    artifacts = receipt.get("artifacts")
    boot = artifacts.get("boot") if isinstance(artifacts, dict) else None
    init = artifacts.get("init") if isinstance(artifacts, dict) else None
    if (
        receipt.get("schema") != "a90-flat-builder-v1-ab-receipt"
        or receipt.get("profile") != candidate.profile
        or receipt.get("candidate_authority") is not False
        or receipt.get("byte_identical") is not True
        or receipt.get("accepted_boot_unchanged") is not True
        or receipt.get("auto_handoff_binding") != candidate.compiled_auto_handoff
        or not isinstance(boot, dict)
        or boot.get("path") != "boot.img"
        or boot.get("bytes") != candidate.size
        or boot.get("sha256") != candidate.sha256
        or not isinstance(init, dict)
    ):
        raise ContractError("candidate build receipt is not exact")
    if candidate.source.resolve(strict=True) != receipt_path.parent / "A" / "boot.img":
        raise ContractError("candidate source does not belong to the bound build receipt")
    init_path = receipt_path.parent / "A" / str(init.get("path"))
    init_info = init_path.lstat()
    if (
        not stat.S_ISREG(init_info.st_mode)
        or init_path.is_symlink()
        or init_info.st_mode & 0o077
        or init_info.st_size != init.get("bytes")
        or sha256_file(init_path) != init.get("sha256")
    ):
        raise ContractError("candidate init artifact does not match the build receipt")
    init_bytes = init_path.read_bytes()
    expected_init_counts = {
        "candidate_version": 2,
        "candidate_build": 2,
        "image_path": 1,
        "image_sha256": 1,
        "enable_path": 1,
        "latch_path": 1,
    }
    for name, expected_count in expected_init_counts.items():
        value = candidate.compiled_auto_handoff[name].encode("utf-8")
        if init_bytes.count(value) != expected_count:
            raise ContractError(f"compiled auto-handoff value count changed: {name}")


def candidate_first_boot_contract(candidate: CandidateSpec) -> dict[str, Any] | None:
    if candidate.profile == MINIMAL_H2_CANDIDATE_PROFILE:
        return {
            "schema": "a90-auto-handoff-first-boot-v1",
            "enable_path": "/cache/a90-auto-handoff-phase3-minimal-h2.enable",
            "latch_path": "/cache/a90-auto-handoff-phase3-minimal-h2.done",
            "pre_transfer_state": "both-absent",
            "post_boot_status": "binding=1-enable=0-latch=0",
            "post_boot_log": "A90AUTO state=unarmed-stay-native",
        }
    if candidate.profile in {
        MINIMAL_H3_CANDIDATE_PROFILE,
        MINIMAL_H4_CANDIDATE_PROFILE,
        MINIMAL_H5_CANDIDATE_PROFILE,
        MINIMAL_H6_CANDIDATE_PROFILE,
    }:
        assert candidate.compiled_auto_handoff is not None
        return {
            "schema": "a90-auto-handoff-first-boot-v2",
            "enable_path": candidate.compiled_auto_handoff["enable_path"],
            "latch_path": candidate.compiled_auto_handoff["latch_path"],
            "compiled_binding": dict(candidate.compiled_auto_handoff),
            "pre_transfer_state": "both-absent",
            "post_boot_status": "binding=1-enable=0-latch=0",
            "post_boot_log": "A90AUTO state=unarmed-stay-native",
        }
    return None


EXECUTION_REVIEW_SOURCES = (
    REVAL_DIR / "a90_observation_pipeline.py",
    REVAL_DIR / "a90ctl.py",
    SCRIPT_DIR / "run_d1_chroot_mvp.py",
    REVAL_DIR / "a90_transition_contract_v2.py",
    SCRIPT_DIR / "a90_phase2c_display_packet.py",
    SCRIPT_DIR / "a90_phase2d_display_observer.py",
    SCRIPT_DIR / "a90_v3403_absent_only_staging.py",
    SCRIPT_DIR / "a90_phase2d_keyed_rootfs.py",
    SCRIPT_DIR / "a90_v3403_f1_orchestrator.py",
    SCRIPT_DIR / "prepare_phase2_display_v1_rootfs.py",
    SCRIPT_DIR / "phase2_display_v1" / "a90_debian_display_v1.c",
    SCRIPT_DIR / "phase2_display_v1" / "manifest.toml",
    SCRIPT_DIR / "phase2c_display_packet_v1" / "contract.toml",
    Path(__file__).resolve(),
)
PHASE3_REVIEW_SCHEMA = "a90-phase3-resident-refresh-f1-independent-review-v1"
PHASE3_EXECUTION_REVIEW_SOURCES = tuple(
    dict.fromkeys(
        (
            *staging.required_support_files(staging.PHASE3_PROFILE),
            REVAL_DIR / "native_init_flash.py",
            REVAL_DIR / "tcpctl_host.py",
            SCRIPT_DIR / "a90_phase2d_connected_preflight.py",
            SCRIPT_DIR / "a90_v3403_absent_only_staging.py",
            SCRIPT_DIR / "a90_v3403_f1_orchestrator.py",
            SCRIPT_DIR / "a90_resident_manifest_builder_v1.py",
            SCRIPT_DIR / "a90_resident_promotion_v1.py",
            SCRIPT_DIR / "a90_resident_fast_handoff_v1.py",
            SCRIPT_DIR / "a90_phase3_network_ssh_keyed_rootfs_v1.py",
            SCRIPT_DIR / "prepare_phase3_network_ssh_v1_rootfs.py",
            SCRIPT_DIR / "prepare_phase2_display_v1_rootfs.py",
            REVAL_DIR / "a90_flat_builder/build.py",
            REVAL_DIR / "a90_flat_builder/buildlib.py",
            REVAL_DIR
            / "a90_flat_builder/versions/phase3-minimal-h/manifest.toml",
            SCRIPT_DIR / "phase3_network_ssh_v1/manifest.toml",
            SCRIPT_DIR
            / "phase3_network_ssh_v1/a90_debian_network_ssh_v1.sh",
            SCRIPT_DIR
            / "phase3_network_ssh_v1/a90_debian_return_arm_v1.sh",
            Path(__file__).resolve(),
        )
    )
)


class ContractError(RuntimeError):
    """Raised when final host preparation is not exact."""


def utc_now() -> str:
    return (
        dt.datetime.now(dt.UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sha256_file(path: Path) -> str:
    return staging.sha256_file(path)


def regular_record(
    path: Path,
    *,
    private: bool,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    lexical = path.lstat()
    if stat.S_ISLNK(lexical.st_mode):
        raise ContractError(f"input path must not be a symbolic link: {path}")
    resolved = path.resolve(strict=True)
    info = resolved.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_mode & 0o022
        or (private and info.st_mode & 0o077)
    ):
        raise ContractError(f"input is not an exact regular file: {resolved}")
    if private:
        staging.require_below(resolved, staging.PRIVATE_ROOT, "private input")
    actual = sha256_file(resolved)
    if expected_sha256 is not None and actual != expected_sha256:
        raise ContractError(f"input sha256 mismatch: {resolved}")
    return {
        "path": str(resolved),
        "size": info.st_size,
        "sha256": actual,
    }


def load_exact_json(
    path: Path,
    *,
    private: bool,
    expected_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    record = regular_record(
        path,
        private=private,
        expected_sha256=expected_sha256,
    )
    try:
        value = json.loads(Path(record["path"]).read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"input is not valid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"JSON input is not an object: {path}")
    return value, record


def copy_absent_private(
    source: Path,
    destination: Path,
    *,
    expected_size: int,
    expected_sha256: str,
) -> dict[str, Any]:
    source_record = regular_record(
        source,
        private=True,
        expected_sha256=expected_sha256,
    )
    if source_record["size"] != expected_size:
        raise ContractError("boot source size mismatch")
    if destination.exists() or destination.is_symlink():
        raise ContractError(f"boot destination must be absent: {destination}")
    result = subprocess.run(
        [
            "cp",
            "--reflink=never",
            "--sparse=always",
            "--preserve=mode",
            str(source.resolve()),
            str(destination),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=300.0,
        check=False,
        env={**os.environ, "LC_ALL": "C", "LANG": "C", "TZ": "UTC"},
    )
    if result.returncode != 0:
        raise ContractError("boot artifact copy failed")
    destination.chmod(0o600)
    copied = regular_record(
        destination,
        private=True,
        expected_sha256=expected_sha256,
    )
    source_info = source.resolve().stat()
    destination_info = destination.stat()
    if (
        copied["size"] != expected_size
        or (
            source_info.st_dev == destination_info.st_dev
            and source_info.st_ino == destination_info.st_ino
        )
    ):
        raise ContractError("boot copy is not an exact new inode")
    return copied


def current_source_record(path: Path) -> dict[str, Any]:
    return regular_record(path, private=False)


def required_review_source_records() -> tuple[dict[str, Any], ...]:
    return tuple(current_source_record(path.resolve()) for path in EXECUTION_REVIEW_SOURCES)


def required_phase3_review_source_records() -> tuple[dict[str, Any], ...]:
    return tuple(
        current_source_record(path.resolve())
        for path in PHASE3_EXECUTION_REVIEW_SOURCES
    )


def validate_independent_review_report(review_text: str) -> None:
    lines = review_text.splitlines()
    required = {
        "Independent verdict:": "Independent verdict: GO",
        "Unresolved HIGH:": "Unresolved HIGH: 0",
        "Unresolved MEDIUM:": "Unresolved MEDIUM: 0",
        "Device actions:": "Device actions: none",
        "Review decision:": f"Review decision: `{REVIEW_DECISION}`",
    }
    for prefix, exact in required.items():
        matching = [line for line in lines if line.startswith(prefix)]
        if matching != [exact]:
            raise ContractError("independent review report is not an exact GO")
    for record in required_review_source_records():
        path = Path(record["path"])
        relative = path.relative_to(REPO_ROOT.resolve(strict=True))
        token = f"- `{relative}`: `{record['sha256']}`"
        source_prefix = f"- `{relative}`:"
        matching = [line for line in lines if line.startswith(source_prefix)]
        if matching != [token]:
            raise ContractError(
                f"independent review does not bind current source: {relative}"
            )


def validate_phase3_independent_review_report(review_text: str) -> None:
    try:
        value = json.loads(review_text)
    except json.JSONDecodeError as exc:
        raise ContractError("Phase 3 F1 review is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ContractError("Phase 3 F1 review is not an object")
    expected_closure = {}
    for record in required_phase3_review_source_records():
        relative = str(
            Path(record["path"]).relative_to(REPO_ROOT.resolve(strict=True))
        )
        expected_closure[relative] = {
            "bytes": record["size"],
            "sha256": record["sha256"],
        }
    if (
        value.get("schema") != PHASE3_REVIEW_SCHEMA
        or value.get("status") != "PASS_GO"
        or value.get("unresolved_findings") != []
        or value.get("permanent_boundaries_unchanged") is not True
        or value.get("device_authority_granted") is not False
        or value.get("named_execution_critical_closure") != expected_closure
    ):
        raise ContractError("Phase 3 F1 independent review is not exact PASS_GO")


def allowed_starting_identities(*, phase3: bool) -> frozenset[tuple[str, str]]:
    if phase3:
        return staging.PHASE3_ALLOWED_STARTING_IDENTITIES
    return staging.PHASE2_ALLOWED_STARTING_IDENTITIES


def validate_template_rollback(template: dict[str, Any]) -> None:
    value = template.get("rollback_boot")
    if not isinstance(value, dict):
        raise ContractError("template rollback_boot is missing")
    source = ROLLBACK_SOURCE.resolve(strict=True)
    if (
        value.get("path") != str(source)
        or value.get("size") != ROLLBACK_SIZE
        or value.get("sha256") != ROLLBACK_SHA256
        or value.get("partition") != "boot"
        or value.get("expected_version") != staging.EXPECTED_BASELINE_VERSION
        or value.get("expected_build") != staging.EXPECTED_BASELINE_BUILD
    ):
        raise ContractError("template does not bind the exact canonical V2321 rollback")
    record = regular_record(
        ROLLBACK_SOURCE,
        private=True,
        expected_sha256=ROLLBACK_SHA256,
    )
    if record["size"] != ROLLBACK_SIZE:
        raise ContractError("canonical V2321 rollback size mismatch")


def validate_connected_preflight_source(value: dict[str, Any]) -> None:
    repository = value.get("repository")
    if not isinstance(repository, dict):
        raise ContractError("connected D0 repository binding is missing")
    source = current_source_record(Path(connected.__file__).resolve())
    if (
        repository.get("connected_preflight") != source["path"]
        or repository.get("connected_preflight_size") != source["size"]
        or repository.get("connected_preflight_sha256") != source["sha256"]
    ):
        raise ContractError(
            "connected D0 evidence does not bind the current preflight helper"
        )


def display_observation() -> dict[str, Any]:
    return {
        "profile": orchestrator.PHASE2_DISPLAY_PROFILE,
        "native_release_schema": "a90-native-display-release-v1",
        "native_release_marker_path": "/run/a90-native-display-release",
        "ready_schema": "a90-debian-display-v1",
        "ready_marker_path": "/run/a90-display/ready",
        "failure_schema": "a90-debian-display-v1-failure",
        "failure_marker_path": "/run/a90-display/failure",
        "display_uid": orchestrator.PHASE2_DISPLAY_UID,
        "display_gid": orchestrator.PHASE2_DISPLAY_GID,
        "max_attempts": orchestrator.PHASE2_DISPLAY_MAX_ATTEMPTS,
        "visible_text": list(orchestrator.PHASE2_DISPLAY_VISIBLE_TEXT),
        "operator_visible_confirmation_required": True,
    }


def require_compiled_rootfs_binding(manifest: dict[str, Any]) -> None:
    candidate = manifest.get("candidate_boot")
    rootfs = manifest.get("debian_rootfs")
    if not isinstance(candidate, dict) or not isinstance(rootfs, dict):
        raise ContractError("candidate/rootfs manifest binding is absent")
    first_boot = candidate.get("first_boot_contract")
    if not isinstance(first_boot, dict) or first_boot.get("schema") != (
        "a90-auto-handoff-first-boot-v2"
    ):
        return
    binding = first_boot.get("compiled_binding")
    keyed = rootfs.get("keyed_source")
    handoff = rootfs.get("handoff_command")
    if (
        not isinstance(binding, dict)
        or not isinstance(keyed, dict)
        or not isinstance(handoff, list)
        or binding.get("candidate_version") != candidate.get("expected_version")
        or binding.get("candidate_build") != candidate.get("expected_build")
        or binding.get("image_path") != keyed.get("device_path")
        or binding.get("image_sha256") != keyed.get("sha256")
        or handoff[2:4] != [binding.get("image_path"), binding.get("image_sha256")]
    ):
        raise ContractError("compiled candidate/rootfs binding mismatch")


def prepare_manifest(
    *,
    template: dict[str, Any],
    run_id: str,
    run_dir: Path,
    summary: dict[str, Any],
    summary_record: dict[str, Any],
    candidate_record: dict[str, Any],
    rollback_record: dict[str, Any],
    connected_value: dict[str, Any],
    connected_record: dict[str, Any],
    paths_record: dict[str, Any],
    host_preparation_record: dict[str, Any],
    repository_commit: str,
    candidate_spec: CandidateSpec = LEGACY_CANDIDATE,
) -> dict[str, Any]:
    manifest = copy.deepcopy(template)
    phase3 = (
        summary.get("schema")
        == "a90-phase3-network-ssh-keyed-rootfs-v1"
    )
    rootfs_profile = (
        staging.PHASE3_PROFILE if phase3 else staging.PHASE2_PROFILE
    )
    filesystem_label = (
        staging.PHASE3_FILESYSTEM_LABEL
        if phase3
        else staging.PHASE2_FILESYSTEM_LABEL
    )
    keyed = summary["keyed_image"]
    observer_summary = summary["observer"]
    bridge = connected_value["target"]
    remote_final = str(staging.derive_remote_final(run_id))
    manifest["schema"] = staging.PHASE2_DISPLAY_MANIFEST_SCHEMA
    manifest["status"] = staging.FINAL_MANIFEST_STATUS
    manifest["run_id"] = run_id
    manifest["candidate_boot"] = {
        **candidate_record,
        "partition": "boot",
        "expected_version": candidate_spec.version,
        "expected_build": candidate_spec.build,
    }
    first_boot = candidate_first_boot_contract(candidate_spec)
    if first_boot is not None:
        manifest["candidate_boot"]["first_boot_contract"] = first_boot
    manifest["rollback_boot"] = {
        **rollback_record,
        "partition": "boot",
        "expected_version": staging.EXPECTED_BASELINE_VERSION,
        "expected_build": staging.EXPECTED_BASELINE_BUILD,
    }
    target = manifest["target"]
    target.update(
        {
            "profile": staging.TARGET_PROFILE,
            "bridge_device": bridge["bridge_device"],
            "bridge_selected_realpath": bridge["bridge_selected_realpath"],
            "bridge_selected_exact": True,
            "current_version": connected_value["health"]["version"],
            "current_build": connected_value["health"]["version_build"],
            "connected_d0_result": {
                **connected_record,
                "outcome": staging.D0_RESULT_OUTCOME,
            },
            "connected_path_preflight": {
                **paths_record,
                "keyed_source_path_absent": True,
                "handoff_work_path_absent": True,
                "run_stage_path_absent": True,
            },
        }
    )
    rootfs = manifest["debian_rootfs"]
    old_observer = rootfs["observer"]
    rootfs.update(
        {
            "kind": (
                "bookworm-arm64-phase3-network-ssh-v1-per-run-keyed"
                if phase3
                else "bookworm-arm64-phase2-display-v1-per-run-keyed"
            ),
            "mount_mode": "read-write-on-work-copy-only",
            "keyed_source": {
                "local_path": keyed["path"],
                "size": keyed["size"],
                "sha256": keyed["sha256"],
                "profile": rootfs_profile,
                "device_path": remote_final,
                "filesystem": "ext4",
                "filesystem_label": filesystem_label,
                "authorized_keys_root_owned_mode_0600": True,
                "e2fsck_read_only_pass": True,
                "materialization": summary_record,
            },
            "pristine_provenance": {
                "path": summary["source"]["path"],
                "size": summary["source"]["size"],
                "sha256": summary["source"]["sha256"],
                "receipt_path": summary["source"]["receipt_path"],
                "receipt_sha256": summary["source"]["receipt_sha256"],
            },
            "observer": {
                "private_key_path": observer_summary["private_key_path"],
                "public_key_sha256": observer_summary["public_key_sha256"],
                "device_ip": old_observer["device_ip"],
                "device_port": old_observer["device_port"],
                "transport_scope": orchestrator.OBSERVER_TRANSPORT_SCOPE,
                "wifi_or_external_network": False,
                "host_ncm_profile": old_observer["host_ncm_profile"],
                "ncm_rebind_identity": orchestrator.NCM_REBIND_IDENTITY,
                "retained_pmsg_marker": orchestrator.RETAINED_PMSG_MARKER,
                "retained_pmsg_required_phase": (
                    orchestrator.RETAINED_PMSG_REQUIRED_PHASE
                ),
                "retained_pmsg_observer_contract": (
                    orchestrator.RETAINED_PMSG_OBSERVER_CONTRACT
                ),
                "retained_pmsg_cleanup_after_private_fsync": True,
            },
            "handoff_command": [
                orchestrator.HANDOFF_COMMAND,
                orchestrator.HANDOFF_TOKEN,
                remote_final,
                keyed["sha256"],
            ],
            "work_copy": {
                "device_path": str(staging.REMOTE_WORK),
                "created_and_mounted_only_by_v3406": True,
                "must_be_absent_before_handoff": True,
                "source_must_remain_byte_identical_on_every_pre_switch_failure": True,
            },
            "internal_userdata_touched": False,
            "expected_auto_reboot_sec": 120,
        }
    )
    adapter = current_source_record(Path(staging.__file__).resolve())
    tcpctl = current_source_record(
        staging.REVAL_DIR / "tcpctl_host.py"
    )
    support = [
        current_source_record(path.resolve())
        for path in staging.required_support_files(rootfs_profile)
    ]
    manifest["rootfs_staging"] = {
        "adapter": {**adapter, "status": "reviewed-ready"},
        "transport": {**tcpctl, "scope": "exclusive-payload-only"},
        "support_files": support,
        "independent_review_passed": True,
        "review_verdict": "PASS_GO" if phase3 else REVIEW_DECISION,
        "implementation_ready_for_review": True,
        "part_of_future_f1_transaction": True,
        "must_follow_fresh_exact_approval": True,
        "existing_tcpctl_install_selected_for_exclusive_payload_only": True,
        "existing_tcpctl_install_selected_for_final_publication": False,
        "final_publication": "absent-only-hardlink",
        "timeout_sec": 1800,
        "required_contract": [
            "exact keyed materialization receipt and image content",
            "exclusive stage directory and absent-only final hardlink",
            "fixed work image absent before handoff",
        ],
    }
    orchestrator_record = current_source_record(
        Path(orchestrator.__file__).resolve()
    )
    manifest["f1_orchestrator"] = {
        **orchestrator_record,
        "status": "reviewed-ready",
        "independent_review_passed": True,
        "candidate_attempt_limit": 1,
        "rollback_attempt_limit": 1,
        "candidate_route_in_recovery": False,
    }
    runner = current_source_record(
        staging.REVAL_DIR / "native_init_flash.py"
    )
    manifest["transport"].update(
        {
            "repository_commit": repository_commit,
            "candidate_and_rollback_runner": runner["path"],
            "runner_size": runner["size"],
            "runner_sha256": runner["sha256"],
            "only_partition_payload": "boot",
            "candidate_expected_arguments": [
                "--from-native",
                "--image",
                candidate_record["path"],
                "--expect-sha256",
                candidate_record["sha256"],
            ],
            "rollback_expected_arguments": [
                "--from-native|adb-recovery",
                "--image",
                rollback_record["path"],
                "--expect-sha256",
                rollback_record["sha256"],
            ],
            "forbidden_partition_writes": True,
        }
    )
    observation = manifest["observation"]
    observation.update(
        {
            "mode": orchestrator.ATTENDED_OBSERVATION_MODE,
            "attended_window_sec": orchestrator.ATTENDED_WINDOW_SEC,
            "pre_handoff_attempt_limit": (
                orchestrator.ATTENDED_PRE_HANDOFF_ATTEMPT_LIMIT
            ),
            "handoff_attempt_limit": (
                orchestrator.ATTENDED_HANDOFF_ATTEMPT_LIMIT
            ),
            "handoff_timeout_sec": orchestrator.F1_HANDOFF_MIN_TIMEOUT_SEC,
            "display": display_observation(),
            "pass_semantics": (
                "exact visible confirmation plus mandatory V2321 rollback"
            ),
        }
    )
    manifest["host_preparation"] = host_preparation_record
    manifest["readiness_blockers"] = []
    manifest["authority"] = {
        "candidate_transfer_authorized": False,
        "live_authority": False,
        "rootfs_staging_authorized": False,
        "manifest_grants_live_authority": False,
        "fresh_operator_approval_required": True,
        "rollback_authority_activates_after_candidate_start": True,
        "approval_must_reference_exact_final_manifest": True,
    }
    approval_path = run_dir / "approval-prepared.json"
    manifest["approval_preparation"] = {
        "schema": orchestrator.APPROVAL_PREPARED_SCHEMA,
        "path": str(approval_path),
        "must_not_exist_before_final_manifest": True,
        "created_by_host_only_prepare_mode": True,
        "fresh_exact_token_must_be_acknowledged_by_operator": True,
        "transaction_directory_consumes_token_once": True,
        "rollback_recovery_requires_no_second_token": True,
        "device_contact": False,
        "device_write": False,
        "f1_authorized": False,
        "live_authorized": False,
    }
    approval_scope = manifest["approval_scope_template"]
    approval_scope.pop("bind_v3405_observer_contract", None)
    approval_scope.pop("bind_phase2_materialization_receipt", None)
    approval_scope.update(
        {
            (
                "bind_phase3_materialization_receipt"
                if phase3
                else "bind_phase2_materialization_receipt"
            ): True,
            "bind_display_visible_confirmation_contract": True,
            "bind_keyed_rootfs_sha256": True,
            "bind_v3406_observer_contract": True,
            "one_candidate_attempt": True,
            "no_candidate_replay": True,
            "mandatory_exact_rollback_authorized_after_candidate_start": True,
        }
    )
    require_compiled_rootfs_binding(manifest)
    return manifest


def execute(args: argparse.Namespace) -> dict[str, Any]:
    if RUN_ID_RE.fullmatch(args.run_id) is None:
        raise ContractError("run ID is not the exact V3406 display form")
    run_dir = (PRIVATE_RUN_BASE / args.run_id).resolve(strict=True)
    staging.require_below(run_dir, PRIVATE_RUN_BASE, "run directory")
    if (run_dir / FINAL_MANIFEST_NAME).exists():
        raise ContractError("final manifest already exists and is never overwritten")
    if (run_dir / "approval-prepared.json").exists():
        raise ContractError("approval receipt must be absent before finalization")
    summary, summary_record = load_exact_json(
        run_dir / KEYED_SUMMARY_NAME,
        private=True,
        expected_sha256=args.expect_keyed_summary_sha256,
    )
    phase3 = (
        summary.get("schema")
        == "a90-phase3-network-ssh-keyed-rootfs-v1"
    )
    expected_summary_decision = (
        "A90_PHASE3_NETWORK_SSH_KEYED_ROOTFS_HOST_PASS"
        if phase3
        else "A90_PHASE2D_KEYED_ROOTFS_HOST_PASS"
    )
    if (
        summary.get("run_id") != args.run_id
        or summary.get("decision") != expected_summary_decision
    ):
        raise ContractError("keyed summary does not select this run")
    template, template_record = load_exact_json(
        args.template_manifest,
        private=True,
        expected_sha256=args.expect_template_sha256,
    )
    if (
        template.get("schema") != TEMPLATE_SCHEMA
        or TEMPLATE_RUN_ID_RE.fullmatch(str(template.get("run_id"))) is None
        or template.get("status") != staging.FINAL_MANIFEST_STATUS
    ):
        raise ContractError("template is not an exact closed V3405 manifest")
    validate_template_rollback(template)
    connected_value, connected_record = load_exact_json(
        args.connected_d0,
        private=True,
        expected_sha256=args.expect_connected_d0_sha256,
    )
    validate_connected_preflight_source(connected_value)
    paths_value, paths_record = load_exact_json(
        args.path_preflight,
        private=True,
        expected_sha256=args.expect_path_preflight_sha256,
    )
    review_record = regular_record(
        args.review_report,
        private=False,
        expected_sha256=args.expect_review_report_sha256,
    )
    try:
        Path(review_record["path"]).relative_to(
            (REPO_ROOT / "docs" / "reports").resolve(strict=True)
        )
    except ValueError as exc:
        raise ContractError(
            "independent review report must be under docs/reports"
        ) from exc
    review_text = Path(review_record["path"]).read_text(encoding="utf-8")
    if phase3:
        validate_phase3_independent_review_report(review_text)
    else:
        validate_independent_review_report(review_text)

    health = connected_value.get("health")
    starting_identity = (
        health.get("version") if isinstance(health, dict) else None,
        health.get("version_build") if isinstance(health, dict) else None,
    )
    if (
        not isinstance(health, dict)
        or starting_identity not in allowed_starting_identities(phase3=phase3)
    ):
        raise ContractError("connected D0 starting native identity is not exact")
    expected_starting_version, expected_starting_build = starting_identity

    candidate_spec = select_candidate_profile(args.candidate_profile)
    candidate_source = candidate_spec.source.resolve(strict=True)
    candidate_copy = copy_absent_private(
        candidate_source,
        run_dir / candidate_spec.copy_name,
        expected_size=candidate_spec.size,
        expected_sha256=candidate_spec.sha256,
    )
    rollback_copy = copy_absent_private(
        ROLLBACK_SOURCE,
        run_dir / ROLLBACK_COPY_NAME,
        expected_size=ROLLBACK_SIZE,
        expected_sha256=ROLLBACK_SHA256,
    )
    runner = current_source_record(
        staging.REVAL_DIR / "native_init_flash.py"
    )
    staging.validate_connected_d0_evidence(
        connected_value,
        expected_realpath=connected_value["target"][
            "bridge_selected_realpath"
        ],
        candidate=staging.BoundFile(
            "candidate_boot",
            Path(candidate_copy["path"]),
            candidate_copy["size"],
            candidate_copy["sha256"],
        ),
        rollback=staging.BoundFile(
            "rollback_boot",
            Path(rollback_copy["path"]),
            rollback_copy["size"],
            rollback_copy["sha256"],
        ),
        flash_runner=staging.BoundFile(
            "transport",
            Path(runner["path"]),
            runner["size"],
            runner["sha256"],
        ),
        expected_version=expected_starting_version,
        expected_build=expected_starting_build,
        require_phase2_preflight=True,
    )
    staging.validate_path_preflight_evidence(
        paths_value,
        run_id=args.run_id,
        connected_d0=staging.BoundFile(
            "connected_d0",
            Path(connected_record["path"]),
            connected_record["size"],
            connected_record["sha256"],
        ),
        remote_final=str(staging.derive_remote_final(args.run_id)),
        remote_work=str(staging.REMOTE_WORK),
        remote_stage_dir=str(staging.derive_stage_dir(args.run_id)),
    )
    repository_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30.0,
        check=True,
    ).stdout.strip()
    host_preparation = {
        "schema": (
            "a90_phase3_v3406_resident_refresh_host_preparation_v1"
            if phase3
            else "a90_phase2d_v3406_host_preparation_v1"
        ),
        "timestamp_utc": utc_now(),
        "run_id": args.run_id,
        "status": PASS_DECISION,
        "keyed_rootfs": summary_record,
        "candidate_boot": candidate_copy,
        "candidate_profile": candidate_spec.profile,
        "rollback_boot": rollback_copy,
        "connected_d0": connected_record,
        "connected_path_preflight": paths_record,
        "independent_review": review_record,
        "template_manifest": template_record,
        "repository": {
            "commit": repository_commit,
            "finalizer": current_source_record(Path(__file__).resolve()),
            "connected_preflight": current_source_record(
                Path(connected.__file__).resolve()
            ),
            "staging_adapter": current_source_record(Path(staging.__file__).resolve()),
            "orchestrator": current_source_record(
                Path(orchestrator.__file__).resolve()
            ),
        },
        "next_gate": "host-only approval receipt preparation",
        "safety": {
            "device_contact": False,
            "device_write": False,
            "rootfs_staged": False,
            "flash": False,
            "reboot": False,
            "f1_authorized": False,
            "live_authority": False,
        },
    }
    host_path = run_dir / HOST_PREPARATION_NAME
    staging.write_private_json_exclusive(host_path, host_preparation)
    host_record = regular_record(host_path, private=True)
    manifest = prepare_manifest(
        template=template,
        run_id=args.run_id,
        run_dir=run_dir,
        summary=summary,
        summary_record=summary_record,
        candidate_record=candidate_copy,
        rollback_record=rollback_copy,
        connected_value=connected_value,
        connected_record=connected_record,
        paths_record=paths_record,
        host_preparation_record=host_record,
        repository_commit=repository_commit,
        candidate_spec=candidate_spec,
    )
    manifest_path = run_dir / FINAL_MANIFEST_NAME
    staging.write_private_json_exclusive(manifest_path, manifest)
    manifest_sha256 = sha256_file(manifest_path)
    spec, issues = orchestrator.load_spec(
        manifest_path,
        manifest_sha256,
        allow_draft=False,
    )
    orchestrator.verify_local_closure(spec)
    if issues:
        raise ContractError(f"final manifest retained issues: {issues}")
    return {
        "schema": SCHEMA,
        "decision": PASS_DECISION,
        "run_id": args.run_id,
        "manifest": {
            "path": str(manifest_path),
            "size": manifest_path.stat().st_size,
            "sha256": manifest_sha256,
        },
        "host_preparation": host_record,
        "candidate_profile": candidate_spec.profile,
        "candidate_authority": False,
        "f1_authorized": False,
        "live_authority": False,
        "device_contact": False,
        "device_write": False,
        "rootfs_staged": False,
        "flash": False,
        "reboot": False,
        "fresh_exact_f1_approval_required": True,
    }


def source_contract_issues(source: str) -> tuple[str, ...]:
    issues: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ("finalizer source is not valid Python",)
    validator_node = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "source_contract_issues"
        ),
        None,
    )
    if validator_node is None:
        return ("finalizer source validator boundary is missing",)
    lines = source.splitlines(keepends=True)
    subject = "".join(
        lines[: validator_node.lineno - 1]
        + lines[validator_node.end_lineno :]
    )
    allowed_start = subject.find("def allowed_starting_identities(")
    allowed_end = subject.find("\ndef validate_template_rollback(", allowed_start + 1)
    expected_allowed = (
        "def allowed_starting_identities(*, phase3: bool) "
        "-> frozenset[tuple[str, str]]:\n"
        "    if phase3:\n"
        "        return staging.PHASE3_ALLOWED_STARTING_IDENTITIES\n"
        "    return staging.PHASE2_ALLOWED_STARTING_IDENTITIES\n\n"
    )
    if (
        allowed_start < 0
        or allowed_end < 0
        or subject[allowed_start:allowed_end] != expected_allowed
    ):
        issues.append("finalizer starting identity helper is not exact")
    exact_connected_start_gate = (
        "        or starting_identity not in "
        "allowed_starting_identities(phase3=phase3)\n"
    )
    if exact_connected_start_gate not in subject:
        issues.append("finalizer connected starting identity gate is not exact")
    for token in (
        '"cp",\n            "--reflink=never",',
        "destination.exists() or destination.is_symlink()",
        "staging.validate_connected_d0_evidence(",
        "candidate_spec = select_candidate_profile(args.candidate_profile)",
        "run_dir / candidate_spec.copy_name",
        "expected_size=candidate_spec.size",
        "expected_sha256=candidate_spec.sha256",
        "validate_template_rollback(template)",
        "validate_connected_preflight_source(connected_value)",
        "validate_independent_review_report(review_text)",
        "validate_phase3_independent_review_report(review_text)",
        "allowed_starting_identities(phase3=phase3)",
        "staging.PHASE3_ALLOWED_STARTING_IDENTITIES",
        "ROLLBACK_SOURCE,",
        "expected_size=ROLLBACK_SIZE",
        "expected_sha256=ROLLBACK_SHA256",
        "staging.validate_path_preflight_evidence(",
        "orchestrator.load_spec(",
        "orchestrator.verify_local_closure(spec)",
        '"candidate_transfer_authorized": False',
        '"live_authority": False',
        '"rootfs_staged": False',
        '"flash": False',
        '"reboot": False',
        '"fresh_exact_f1_approval_required": True',
    ):
        if token not in subject:
            issues.append(f"finalizer source contract missing: {token!r}")
    for forbidden in (
        "--execute-approved-f1",
        "--execute-approved-stage",
        "flash_command(",
        "invoke_rollback(",
        "run_remote(",
        "run_f1_cmd(",
        "/bin/busybox reboot",
        "/bin/busybox dd",
    ):
        if forbidden in subject:
            issues.append(f"finalizer contains forbidden action: {forbidden!r}")
    return tuple(issues)


def audit_payload(
    candidate_profile: str = LEGACY_CANDIDATE_PROFILE,
) -> dict[str, Any]:
    source = Path(__file__).read_text(encoding="utf-8")
    issues = source_contract_issues(source)
    candidate_spec = select_candidate_profile(candidate_profile)
    candidate = regular_record(
        candidate_spec.source,
        private=True,
        expected_sha256=candidate_spec.sha256,
    )
    if candidate["size"] != candidate_spec.size:
        issues = (*issues, "selected candidate size mismatch")
    rollback = regular_record(
        ROLLBACK_SOURCE,
        private=True,
        expected_sha256=ROLLBACK_SHA256,
    )
    if rollback["size"] != ROLLBACK_SIZE:
        issues = (*issues, "canonical V2321 rollback size mismatch")
    return {
        "schema": SCHEMA,
        "mode": "host-only-audit",
        "source_sha256": sha256_file(Path(__file__).resolve()),
        "candidate_profile": candidate_spec.profile,
        "candidate_sha256": candidate["sha256"],
        "candidate_size": candidate["size"],
        "candidate_version": candidate_spec.version,
        "candidate_build": candidate_spec.build,
        "rollback_sha256": rollback["sha256"],
        "rollback_size": rollback["size"],
        "contract_issues": list(issues),
        "ready_for_finalization_inputs": not issues,
        "device_contact": False,
        "device_write": False,
        "rootfs_staged": False,
        "flash": False,
        "reboot": False,
        "f1_authorized": False,
        "live_authority": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--audit-only", action="store_true")
    mode.add_argument("--finalize", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--expect-keyed-summary-sha256")
    parser.add_argument("--template-manifest", type=Path)
    parser.add_argument("--expect-template-sha256")
    parser.add_argument("--connected-d0", type=Path)
    parser.add_argument("--expect-connected-d0-sha256")
    parser.add_argument("--path-preflight", type=Path)
    parser.add_argument("--expect-path-preflight-sha256")
    parser.add_argument("--review-report", type=Path)
    parser.add_argument("--expect-review-report-sha256")
    parser.add_argument(
        "--candidate-profile",
        choices=tuple(CANDIDATE_PROFILES),
        default=LEGACY_CANDIDATE_PROFILE,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.audit_only:
        connected_names = (
            "run_id",
            "expect_keyed_summary_sha256",
            "template_manifest",
            "expect_template_sha256",
            "connected_d0",
            "expect_connected_d0_sha256",
            "path_preflight",
            "expect_path_preflight_sha256",
            "review_report",
            "expect_review_report_sha256",
        )
        if any(getattr(args, name) is not None for name in connected_names):
            raise ContractError("audit mode accepts no finalization inputs")
        result = audit_payload(args.candidate_profile)
    else:
        required = (
            "run_id",
            "expect_keyed_summary_sha256",
            "template_manifest",
            "expect_template_sha256",
            "connected_d0",
            "expect_connected_d0_sha256",
            "path_preflight",
            "expect_path_preflight_sha256",
            "review_report",
            "expect_review_report_sha256",
        )
        missing = [name for name in required if getattr(args, name) is None]
        if missing:
            raise ContractError(f"finalization inputs are missing: {missing}")
        result = execute(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:  # noqa: BLE001 - concise fail-closed CLI
        print(
            f"a90-phase2d-finalize-f1: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)

#!/usr/bin/env python3
"""Build one validated A90 resident-promotion manifest without device access.

The builder reuses an exact resident manifest only as a structural template.
Every run-dependent path, hash, size, and execution-source binding is reopened
from the selected private run.  It validates a temporary manifest through the
production resident loader and local closure before publishing one absent-only
final file.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_resident_fast_handoff_v1 as qualification  # noqa: E402
import a90_resident_promotion_v1 as promotion  # noqa: E402
import a90_v3403_absent_only_staging as staging  # noqa: E402
import a90_v3403_f1_orchestrator as base  # noqa: E402


SCHEMA = "a90_resident_manifest_builder_v1"
PASS_DECISION = "A90_RESIDENT_MANIFEST_VALIDATED_HOST_PASS"
RUN_ID_RE = re.compile(
    r"^a90-v3406-debian-display-f1-[0-9]{8}-[0-9]{2}$"
)
OUTPUT_NAME_RE = re.compile(r"^resident-prepared-manifest(?:-[a-z0-9-]+)?\.json$")
KEYED_SUMMARY_NAME = "keyed-rootfs-summary.json"
ROLLBACK_NAME = "rollback-boot-v2321.img"
HOST_PREPARATION_NAME = "host-preparation.json"
ROLLBACK_SIZE = 60882944
ROLLBACK_SHA256 = (
    "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
)
ROLLBACK_VERSION = "0.9.285"
ROLLBACK_BUILD = "v2321-usb-clean-identity-rodata"
JOURNAL_NAME_RE = re.compile(r"^(?P<sequence>[0-9]{4})-(?P<action>[a-z0-9-]+)\.json$")


@dataclass(frozen=True)
class CandidateSpec:
    profile: str
    name: str
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
MINIMAL_H7_CANDIDATE_PROFILE = (
    "phase3-minimal-h7-readonly-source-ondevice-evidence-auto-benchmark"
)
MINIMAL_H8_CANDIDATE_PROFILE = (
    "phase3-minimal-h8-dev-tmpfs-handoff-repair-auto-benchmark"
)
MINIMAL_H9_CANDIDATE_PROFILE = (
    "phase3-minimal-h9-fast-source-receipt-auto-benchmark"
)
MINIMAL_H10_CANDIDATE_PROFILE = (
    "phase3-minimal-h10-fast-source-receipt-auto-benchmark"
)
MINIMAL_H11_CANDIDATE_PROFILE = (
    "phase3-minimal-h11-direct-debian-boot-auto-benchmark"
)
LEGACY_CANDIDATE = CandidateSpec(
    profile=LEGACY_CANDIDATE_PROFILE,
    name="candidate-boot-phase2-display-v1.img",
    size=66379776,
    sha256="3d3e66535654a62f83c5772caba27624acc160911307190de458154acaefdabb",
    version="0.11.161",
    build="phase2-display-v1-native-handoff",
)
MINIMAL_F_CANDIDATE = CandidateSpec(
    profile=MINIMAL_F_CANDIDATE_PROFILE,
    name="candidate-boot-phase3-minimal-f.img",
    size=61440000,
    sha256="93ac207f6008959f663ec3df60e9bfd43ee855f72e57a4967c93bd0aa49d2d6f",
    version="0.11.167",
    build="phase3-minimal-f-power-recovery-ui",
)
MINIMAL_G_CANDIDATE = CandidateSpec(
    profile=MINIMAL_G_CANDIDATE_PROFILE,
    name="candidate-boot-phase3-minimal-g.img",
    size=58306560,
    sha256="f6eccc8e8b372e957d67e64e088acea4f7fddf351873d7c297e1fa4393f4169a",
    version="0.11.168",
    build="phase3-minimal-g-server-core",
)
MINIMAL_H2_CANDIDATE = CandidateSpec(
    profile=MINIMAL_H2_CANDIDATE_PROFILE,
    name="candidate-boot-phase3-minimal-h2.img",
    size=58372096,
    sha256="97cfbb149361773e895a2a1cff0f13961c06f0a4710119159d6d2a104bc69802",
    version="0.11.170",
    build="phase3-minimal-h2-two-phase-auto-benchmark",
)
MINIMAL_H3_CANDIDATE = CandidateSpec(
    profile=MINIMAL_H3_CANDIDATE_PROFILE,
    name="candidate-boot-phase3-minimal-h3.img",
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
    name="candidate-boot-phase3-minimal-h4.img",
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
    name="candidate-boot-phase3-minimal-h5.img",
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
    name="candidate-boot-phase3-minimal-h6.img",
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
MINIMAL_H7_CANDIDATE = CandidateSpec(
    profile=MINIMAL_H7_CANDIDATE_PROFILE,
    name="candidate-boot-phase3-minimal-h7.img",
    size=58306560,
    sha256="9edcbf8821c5fb5069576ca403ed04e873e9dfcf79dedb59e2d976d6981af4a2",
    version="0.11.175",
    build="phase3-minimal-h7-readonly-source-ondevice-evidence-auto-benchmark",
    build_receipt=(
        staging.PRIVATE_ROOT
        / "outputs"
        / "a90-h7-final-ab-20260809-01"
        / "ab-receipt.json"
    ),
    build_receipt_sha256=(
        "5786bc0a5a9999a158647203afe5d51d60569d42c6fc76bb3a063e7bdd483773"
    ),
    compiled_auto_handoff={
        "schema": "a90-compiled-auto-handoff-binding-v1",
        "candidate_version": "0.11.175",
        "candidate_build": (
            "phase3-minimal-h7-readonly-source-ondevice-evidence-auto-benchmark"
        ),
        "image_path": (
            "/mnt/sdext/a90/runtime/"
            "debian-bookworm-arm64-phase2-display-v3406-keyed-20260807-05.img"
        ),
        "image_sha256": (
            "b92a5437d3854b0f01e4b2acc4a241ad9c8ad8f0b17d7cc36e246d2fbb01d10a"
        ),
        "enable_path": "/cache/a90-auto-handoff-phase3-minimal-h7.enable",
        "latch_path": "/cache/a90-auto-handoff-phase3-minimal-h7.done",
        "binding_sha256": (
            "12fd4ad71f9e976455737d2671006cab77c8da916fad87d6e09eaae8f6253f7c"
        ),
    },
)
MINIMAL_H8_CANDIDATE = CandidateSpec(
    profile=MINIMAL_H8_CANDIDATE_PROFILE,
    name="candidate-boot-phase3-minimal-h8.img",
    size=58372096,
    sha256="cfffb68a4d47f8ae1a76cee7faef8085e1681f1c53155cd6d03d7d87c15f7409",
    version="0.11.176",
    build="phase3-minimal-h8-dev-tmpfs-handoff-repair-auto-benchmark",
    build_receipt=(
        staging.PRIVATE_ROOT
        / "outputs"
        / "a90-h8-dev-tmpfs-ab-20260809-01"
        / "ab-receipt.json"
    ),
    build_receipt_sha256=(
        "5285e0e6c1119151aa98d7cd5ee27b320939901a68408aa4a3c45defe5408ac6"
    ),
    compiled_auto_handoff={
        "schema": "a90-compiled-auto-handoff-binding-v1",
        "candidate_version": "0.11.176",
        "candidate_build": (
            "phase3-minimal-h8-dev-tmpfs-handoff-repair-auto-benchmark"
        ),
        "image_path": (
            "/mnt/sdext/a90/runtime/"
            "debian-bookworm-arm64-phase2-display-v3406-keyed-20260809-01.img"
        ),
        "image_sha256": (
            "e2028b021cd67ebf16ad3cb917e9b548e1fcc434d5e42f10117854f202d01b24"
        ),
        "enable_path": "/cache/a90-auto-handoff-phase3-minimal-h8.enable",
        "latch_path": "/cache/a90-auto-handoff-phase3-minimal-h8.done",
        "binding_sha256": (
            "4221d365c10a86a85c2ebaeb64cdbe1d1ea8c240226ce5868b6c20afeb6b51a3"
        ),
    },
)
MINIMAL_H9_CANDIDATE = CandidateSpec(
    profile=MINIMAL_H9_CANDIDATE_PROFILE,
    name="candidate-boot-phase3-minimal-h9.img",
    size=58372096,
    sha256="c78cd6b4eee5b44c6249ad20729f0379a97cd83db67cab2287271813cd91439f",
    version="0.11.177",
    build="phase3-minimal-h9-fast-source-receipt-auto-benchmark",
    build_receipt=(
        staging.PRIVATE_ROOT
        / "outputs"
        / "a90-h9-fast-source-receipt-ab-20260809-04"
        / "ab-receipt.json"
    ),
    build_receipt_sha256=(
        "2c8e45edcb9a1604c5b905b6dc956446d38ef94504ab44a2bb3dc5a16b06bd1e"
    ),
    compiled_auto_handoff={
        "schema": "a90-compiled-auto-handoff-binding-v2",
        "candidate_version": "0.11.177",
        "candidate_build": "phase3-minimal-h9-fast-source-receipt-auto-benchmark",
        "image_path": (
            "/mnt/sdext/a90/runtime/"
            "debian-bookworm-arm64-phase2-display-v3406-keyed-20260809-02.img"
        ),
        "image_sha256": (
            "e2028b021cd67ebf16ad3cb917e9b548e1fcc434d5e42f10117854f202d01b24"
        ),
        "enable_path": "/cache/a90-auto-handoff-phase3-minimal-h9.enable",
        "latch_path": "/cache/a90-auto-handoff-phase3-minimal-h9.done",
        "receipt_path": "/cache/a90-source-receipt-phase3-minimal-h9",
        "binding_sha256": (
            "02f441da4ccb982e52ce8b75438df38a68eb6b3f3e4de0cd6f7616e250876a88"
        ),
    },
)
MINIMAL_H10_CANDIDATE = CandidateSpec(
    profile=MINIMAL_H10_CANDIDATE_PROFILE,
    name="candidate-boot-phase3-minimal-h10.img",
    size=58372096,
    sha256="145ab5d0d2eff02e20d75149e62bd929084a9a1014a13f9b79e9dbd3269655f1",
    version="0.11.178",
    build="phase3-minimal-h10-fast-source-receipt-auto-benchmark",
    build_receipt=(
        staging.PRIVATE_ROOT
        / "outputs"
        / "a90-h10-fast-source-receipt-ab-20260809-02"
        / "ab-receipt.json"
    ),
    build_receipt_sha256=(
        "a8323448364a3bfbc4edc0661b61493574bd7302c92699c07a5aa53d0465653a"
    ),
    compiled_auto_handoff={
        "schema": "a90-compiled-auto-handoff-binding-v2",
        "candidate_version": "0.11.178",
        "candidate_build": "phase3-minimal-h10-fast-source-receipt-auto-benchmark",
        "image_path": (
            "/mnt/sdext/a90/runtime/"
            "debian-bookworm-arm64-phase2-display-v3406-keyed-20260809-03.img"
        ),
        "image_sha256": (
            "38d9ce41503483996d14a18fb51275fbbe47e898ce51aee37f9f88b61295018e"
        ),
        "enable_path": "/cache/a90-auto-handoff-phase3-minimal-h10.enable",
        "latch_path": "/cache/a90-auto-handoff-phase3-minimal-h10.done",
        "receipt_path": "/cache/a90-source-receipt-phase3-minimal-h10",
        "binding_sha256": (
            "decc69954c2f57067d56062b1a1dd61a394b0587ab86d17905eae070e5b71d2d"
        ),
    },
)
MINIMAL_H11_CANDIDATE = CandidateSpec(
    profile=MINIMAL_H11_CANDIDATE_PROFILE,
    name="candidate-boot-phase3-minimal-h11.img",
    size=58372096,
    sha256="b5b3391af4d0842150fcce38ef22e3f7c9b15cc771b14589571d56c1de72f637",
    version="0.11.179",
    build="phase3-minimal-h11-direct-debian-boot-auto-benchmark",
    build_receipt=(
        staging.PRIVATE_ROOT
        / "outputs"
        / "a90-h11-direct-debian-boot-ab-20260810-04"
        / "ab-receipt.json"
    ),
    build_receipt_sha256=(
        "6aafa2598587885e0e9e1b6cd229ef89055e9687c0cbe330988ef82ddf5b2eae"
    ),
    compiled_auto_handoff={
        "schema": "a90-compiled-auto-handoff-binding-v2",
        "candidate_version": "0.11.179",
        "candidate_build": "phase3-minimal-h11-direct-debian-boot-auto-benchmark",
        "image_path": (
            "/mnt/sdext/a90/runtime/"
            "debian-bookworm-arm64-phase2-display-v3406-keyed-20260810-03.img"
        ),
        "image_sha256": (
            "9e9b11aa80e2c83f54990e9b286dcdd89535438d6f0a248fe89557c75a763931"
        ),
        "enable_path": "/cache/a90-auto-handoff-phase3-minimal-h11.enable",
        "latch_path": "/cache/a90-auto-handoff-phase3-minimal-h11.done",
        "receipt_path": "/cache/a90-source-receipt-phase3-minimal-h11",
        "binding_sha256": (
            "801773b373a10380387603aa0a91f8a1b1456f4fb5eedfb5257debc1812c259a"
        ),
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
        MINIMAL_H7_CANDIDATE,
        MINIMAL_H8_CANDIDATE,
        MINIMAL_H9_CANDIDATE,
        MINIMAL_H10_CANDIDATE,
        MINIMAL_H11_CANDIDATE,
    )
}

# Backward-compatible aliases for the original single-candidate API.
CANDIDATE_NAME = LEGACY_CANDIDATE.name
CANDIDATE_SIZE = LEGACY_CANDIDATE.size
CANDIDATE_SHA256 = LEGACY_CANDIDATE.sha256
CANDIDATE_VERSION = LEGACY_CANDIDATE.version
CANDIDATE_BUILD = LEGACY_CANDIDATE.build


class ContractError(RuntimeError):
    """Raised when resident manifest preparation is not exact."""


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
    if "receipt_path" in candidate.compiled_auto_handoff:
        expected_init_counts["receipt_path"] = 1
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
        MINIMAL_H7_CANDIDATE_PROFILE,
        MINIMAL_H8_CANDIDATE_PROFILE,
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
    if candidate.profile in {
        MINIMAL_H9_CANDIDATE_PROFILE,
        MINIMAL_H10_CANDIDATE_PROFILE,
        MINIMAL_H11_CANDIDATE_PROFILE,
    }:
        assert candidate.compiled_auto_handoff is not None
        return {
            "schema": "a90-auto-handoff-first-boot-v3",
            "enable_path": candidate.compiled_auto_handoff["enable_path"],
            "latch_path": candidate.compiled_auto_handoff["latch_path"],
            "receipt_path": candidate.compiled_auto_handoff["receipt_path"],
            "compiled_binding": dict(candidate.compiled_auto_handoff),
            "pre_transfer_state": "enable-latch-receipt-absent",
            "post_boot_status": "binding=1-enable=0-latch=0",
            "post_boot_log": "A90AUTO state=unarmed-stay-native",
        }
    return None


def require_compiled_rootfs_binding(manifest: dict[str, Any]) -> None:
    candidate = manifest.get("candidate_boot")
    rootfs = manifest.get("debian_rootfs")
    if not isinstance(candidate, dict) or not isinstance(rootfs, dict):
        raise ContractError("candidate/rootfs manifest binding is absent")
    first_boot = candidate.get("first_boot_contract")
    if (
        not isinstance(first_boot, dict)
        or first_boot.get("schema")
        not in {
            "a90-auto-handoff-first-boot-v2",
            "a90-auto-handoff-first-boot-v3",
        }
    ):
        return
    binding = first_boot.get("compiled_binding")
    keyed = rootfs.get("keyed_source")
    handoff = rootfs.get("handoff_command")
    first_boot_schema = first_boot.get("schema")
    if (
        not isinstance(binding, dict)
        or not isinstance(keyed, dict)
        or not isinstance(handoff, list)
        or binding.get("candidate_version") != candidate.get("expected_version")
        or binding.get("candidate_build") != candidate.get("expected_build")
        or binding.get("image_path") != keyed.get("device_path")
        or binding.get("image_sha256") != keyed.get("sha256")
        or handoff[2:4] != [binding.get("image_path"), binding.get("image_sha256")]
        or (
            first_boot_schema == "a90-auto-handoff-first-boot-v3"
            and (
                binding.get("schema")
                != "a90-compiled-auto-handoff-binding-v2"
                or first_boot.get("receipt_path")
                != binding.get("receipt_path")
                or not str(binding.get("receipt_path") or "").startswith(
                    "/cache/a90-source-receipt-"
                )
                or first_boot.get("pre_transfer_state")
                != "enable-latch-receipt-absent"
            )
        )
    ):
        raise ContractError("compiled candidate/rootfs binding mismatch")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def validate_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or staging.HEX64_RE.fullmatch(value) is None:
        raise ContractError(f"{label} is not an exact sha256")
    return value


def validate_canonical_boot_template(
    candidate: dict[str, Any],
    rollback: dict[str, Any],
) -> None:
    for label, value, name, size, digest, version, build in (
        (
            "candidate",
            candidate,
            CANDIDATE_NAME,
            CANDIDATE_SIZE,
            CANDIDATE_SHA256,
            CANDIDATE_VERSION,
            CANDIDATE_BUILD,
        ),
        (
            "rollback",
            rollback,
            ROLLBACK_NAME,
            ROLLBACK_SIZE,
            ROLLBACK_SHA256,
            ROLLBACK_VERSION,
            ROLLBACK_BUILD,
        ),
    ):
        path = value.get("path")
        if (
            not isinstance(path, str)
            or Path(path).name != name
            or value.get("partition") != "boot"
            or value.get("size") != size
            or value.get("sha256") != digest
            or value.get("expected_version") != version
            or value.get("expected_build") != build
        ):
            raise ContractError(f"template {label} boot binding is not canonical")


def regular_record(
    path: Path,
    *,
    private: bool,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    if path.is_symlink():
        raise ContractError(f"input must not be a symbolic link: {path}")
    resolved = path.resolve(strict=True)
    info = resolved.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022:
        raise ContractError(f"input is not an exact regular file: {resolved}")
    if private:
        staging.require_below(resolved, staging.PRIVATE_ROOT, "private input")
        if info.st_mode & 0o077:
            raise ContractError(f"private input permissions are excessive: {resolved}")
    actual_sha256 = sha256_file(resolved)
    if expected_size is not None and info.st_size != expected_size:
        raise ContractError(f"input size mismatch: {resolved}")
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise ContractError(f"input sha256 mismatch: {resolved}")
    return {
        "path": str(resolved),
        "size": info.st_size,
        "sha256": actual_sha256,
    }


def load_exact_json(
    path: Path,
    *,
    expected_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    record = regular_record(
        path,
        private=True,
        expected_sha256=validate_sha256(expected_sha256, "JSON sha256"),
    )
    try:
        value = json.loads(Path(record["path"]).read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"input is not valid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"JSON input is not an object: {path}")
    return value, record


def bound_json_record(path: Path, label: str) -> dict[str, Any]:
    record = regular_record(path, private=True)
    try:
        value = json.loads(Path(record["path"]).read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{label} is not a JSON object")
    return record


def bind_prior_closed_run(prior_run_id: str) -> dict[str, Any]:
    if RUN_ID_RE.fullmatch(prior_run_id) is None:
        raise ContractError("prior closed-run id is not exact")
    prior_dir = (staging.PRIVATE_RUN_BASE / prior_run_id).resolve(strict=True)
    staging.require_below(prior_dir, staging.PRIVATE_RUN_BASE, "prior run directory")
    live_dir = prior_dir / "f1-live"
    journal_dir = live_dir / "journal"
    if journal_dir.is_symlink() or not journal_dir.is_dir():
        raise ContractError("prior journal directory is not exact")
    entries = sorted(journal_dir.iterdir())
    if not entries or len(entries) > promotion.MAX_PRIOR_JOURNAL_RECORDS:
        raise ContractError("prior journal record count is not bounded")
    journal: list[dict[str, Any]] = []
    for sequence, path in enumerate(entries):
        match = JOURNAL_NAME_RE.fullmatch(path.name)
        if (
            match is None
            or int(match.group("sequence")) != sequence
            or path.is_symlink()
            or not path.is_file()
        ):
            raise ContractError("prior journal filenames are not contiguous")
        record = bound_json_record(path, f"prior journal[{sequence}]")
        value = json.loads(Path(record["path"]).read_text(encoding="utf-8"))
        if (
            value.get("sequence") != sequence
            or value.get("action") != match.group("action")
            or value.get("run_id") != prior_run_id
        ):
            raise ContractError("prior journal filename and record differ")
        journal.append(record)
    return {
        "run_id": prior_run_id,
        "manifest": bound_json_record(
            prior_dir / "prepared-manifest.json",
            "prior manifest",
        ),
        "approval_prepared": bound_json_record(
            prior_dir / "approval-prepared.json",
            "prior approval",
        ),
        "result": bound_json_record(live_dir / "result.json", "prior result"),
        "timeline": bound_json_record(
            live_dir / "timeline.json",
            "prior timeline",
        ),
        "journal": journal,
    }


def current_record(path: Path) -> dict[str, Any]:
    return regular_record(path.resolve(), private=False)


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return value


def update_execution_sources(manifest: dict[str, Any]) -> None:
    orchestrator = require_dict(manifest.get("f1_orchestrator"), "f1_orchestrator")
    orchestrator.update(current_record(Path(base.__file__).resolve()))

    rootfs_staging = require_dict(manifest.get("rootfs_staging"), "rootfs_staging")
    rootfs = require_dict(manifest.get("debian_rootfs"), "debian_rootfs")
    keyed_source = require_dict(
        rootfs.get("keyed_source"),
        "debian_rootfs.keyed_source",
    )
    rootfs_profile = keyed_source.get("profile", staging.PHASE2_PROFILE)
    adapter = require_dict(rootfs_staging.get("adapter"), "rootfs_staging.adapter")
    adapter.update(current_record(Path(staging.__file__).resolve()))
    transport = require_dict(
        rootfs_staging.get("transport"),
        "rootfs_staging.transport",
    )
    transport.update(current_record(REVAL_DIR / "tcpctl_host.py"))
    rootfs_staging["support_files"] = [
        current_record(path.resolve())
        for path in staging.required_support_files(rootfs_profile)
    ]

    resident = require_dict(manifest.get("resident_promotion"), "resident_promotion")
    runner = require_dict(resident.get("runner"), "resident_promotion.runner")
    runner.update(current_record(Path(promotion.__file__).resolve()))
    helper = require_dict(
        resident.get("qualification_helper"),
        "resident_promotion.qualification_helper",
    )
    helper.update(current_record(Path(qualification.__file__).resolve()))

    flash_runner = current_record(REVAL_DIR / "native_init_flash.py")
    manifest_transport = require_dict(manifest.get("transport"), "transport")
    manifest_transport.update(
        {
            "candidate_and_rollback_runner": flash_runner["path"],
            "runner_size": flash_runner["size"],
            "runner_sha256": flash_runner["sha256"],
        }
    )


def prepare_manifest(
    *,
    template: dict[str, Any],
    run_id: str,
    run_dir: Path,
    evidence_sequence: str,
    summary: dict[str, Any],
    summary_record: dict[str, Any],
    candidate_record: dict[str, Any],
    rollback_record: dict[str, Any],
    connected_value: dict[str, Any],
    connected_record: dict[str, Any],
    paths_value: dict[str, Any],
    paths_record: dict[str, Any],
    host_preparation_record: dict[str, Any],
    repository_commit: str,
    resident_install_v2: bool = False,
    candidate_spec: CandidateSpec = LEGACY_CANDIDATE,
    prior_closed_run: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if template.get("schema") != staging.RESIDENT_PROMOTION_MANIFEST_SCHEMA:
        raise ContractError("template is not a resident-promotion manifest")
    if template.get("status") != staging.FINAL_MANIFEST_STATUS:
        raise ContractError("template status is not final")
    template_run_id = template.get("run_id")
    if not isinstance(template_run_id, str) or RUN_ID_RE.fullmatch(template_run_id) is None:
        raise ContractError("template run_id is not exact")

    keyed = require_dict(summary.get("keyed_image"), "keyed summary image")
    observer = require_dict(summary.get("observer"), "keyed summary observer")
    source = require_dict(summary.get("source"), "keyed summary source")
    phase3 = (
        summary.get("schema")
        == "a90-phase3-network-ssh-keyed-rootfs-v1"
    )
    expected_decision = (
        "A90_PHASE3_NETWORK_SSH_KEYED_ROOTFS_HOST_PASS"
        if phase3
        else "A90_PHASE2D_KEYED_ROOTFS_HOST_PASS"
    )
    expected_image = run_dir / (
        "phase3-network-ssh-v1-keyed.img"
        if phase3
        else "phase2-display-v1-keyed.img"
    )
    if (
        summary.get("run_id") != run_id
        or summary.get("decision") != expected_decision
        or keyed.get("path") != str(expected_image)
    ):
        raise ContractError("keyed summary does not select the exact run")

    manifest = copy.deepcopy(template)
    resident = require_dict(
        manifest.get("resident_promotion"),
        "resident_promotion",
    )
    if resident_install_v2:
        if resident.get("mode") != promotion.MODE:
            raise ContractError("template resident mode is not legacy promotion v1")
        manifest["schema"] = staging.RESIDENT_INSTALL_MANIFEST_SCHEMA
        resident["mode"] = promotion.INSTALL_MODE
        resident.pop("resident_reboot_command", None)
        resident.pop("resident_reboot_timeout_sec", None)
        resident["candidate_health_checks"] = 1
        resident["success_terminal"] = promotion.INSTALL_STATUS
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
        "expected_version": ROLLBACK_VERSION,
        "expected_build": ROLLBACK_BUILD,
    }
    if prior_closed_run is not None:
        resident["prior_closed_run"] = copy.deepcopy(prior_closed_run)

    target = require_dict(manifest.get("target"), "target")
    connected_target = require_dict(connected_value.get("target"), "connected D0 target")
    target.update(
        {
            "bridge_device": connected_target.get("bridge_device"),
            "bridge_selected_realpath": connected_target.get("bridge_selected_realpath"),
            "bridge_selected_exact": True,
            "current_version": require_dict(
                connected_value.get("health"),
                "connected D0 health",
            ).get("version"),
            "current_build": require_dict(
                connected_value.get("health"),
                "connected D0 health",
            ).get("version_build"),
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

    remote_final = str(staging.derive_remote_final(run_id))
    rootfs = require_dict(manifest.get("debian_rootfs"), "debian_rootfs")
    keyed_source = require_dict(rootfs.get("keyed_source"), "debian_rootfs.keyed_source")
    rootfs["kind"] = (
        "bookworm-arm64-phase3-network-ssh-v1-per-run-keyed"
        if phase3
        else "bookworm-arm64-phase2-display-v1-per-run-keyed"
    )
    keyed_source.update(
        {
            "local_path": keyed["path"],
            "size": keyed["size"],
            "sha256": keyed["sha256"],
            "profile": (
                staging.PHASE3_PROFILE if phase3 else staging.PHASE2_PROFILE
            ),
            "device_path": remote_final,
            "filesystem_label": (
                staging.PHASE3_FILESYSTEM_LABEL
                if phase3
                else staging.PHASE2_FILESYSTEM_LABEL
            ),
            "materialization": summary_record,
        }
    )
    rootfs["pristine_provenance"] = {
        "path": source.get("path"),
        "size": source.get("size"),
        "sha256": source.get("sha256"),
        "receipt_path": source.get("receipt_path"),
        "receipt_sha256": source.get("receipt_sha256"),
    }
    rootfs["handoff_command"] = [
        base.HANDOFF_COMMAND,
        base.HANDOFF_TOKEN,
        remote_final,
        keyed["sha256"],
    ]
    rootfs_observer = require_dict(rootfs.get("observer"), "debian_rootfs.observer")
    rootfs_observer.update(
        {
            "private_key_path": observer["private_key_path"],
            "public_key_sha256": observer["public_key_sha256"],
        }
    )

    manifest["host_preparation"] = host_preparation_record
    rootfs_staging = require_dict(
        manifest.get("rootfs_staging"),
        "rootfs_staging",
    )
    if phase3:
        rootfs_staging["review_verdict"] = "PASS_GO"
        approval_scope = manifest.get("approval_scope_template")
        if isinstance(approval_scope, dict):
            approval_scope.pop("bind_phase2_materialization_receipt", None)
            approval_scope["bind_phase3_materialization_receipt"] = True
    approval = require_dict(manifest.get("approval_preparation"), "approval_preparation")
    approval["path"] = str(run_dir / "approval-prepared.json")

    update_execution_sources(manifest)
    transport = require_dict(manifest.get("transport"), "transport")
    transport.update(
        {
            "repository_commit": repository_commit,
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
        }
    )

    if connected_value.get("run_id") != f"{run_id}-connected-d0-{evidence_sequence}":
        raise ContractError("connected D0 run_id does not match the selected sequence")
    if paths_value.get("run_id") != run_id:
        raise ContractError("path preflight run_id does not match the selected run")

    serialized = json.dumps(manifest, sort_keys=True)
    template_remote = require_dict(
        require_dict(template.get("debian_rootfs"), "template debian_rootfs").get(
            "keyed_source"
        ),
        "template keyed_source",
    ).get("device_path")
    for stale in (template_run_id, template_remote):
        if isinstance(stale, str) and stale in serialized:
            raise ContractError(f"template run-specific value survived rebinding: {stale}")
    require_compiled_rootfs_binding(manifest)
    return manifest


def validate_local_paths(manifest: dict[str, Any], run_dir: Path) -> None:
    approval_path = str(run_dir / "approval-prepared.json")
    seen: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str) and value.startswith(str(REPO_ROOT)):
            seen.append(value)

    walk(manifest)
    if approval_path not in seen:
        raise ContractError("approval receipt path is not bound")
    if Path(approval_path).exists() or Path(approval_path).is_symlink():
        raise ContractError("approval receipt must remain absent before preparation")
    for value in sorted(set(seen) - {approval_path}):
        path = Path(value)
        if path.is_symlink() or not path.is_file():
            raise ContractError(f"manifest local path is absent or not regular: {path}")


def write_validate_publish(
    manifest: dict[str, Any],
    *,
    run_dir: Path,
    output_name: str,
) -> tuple[Path, str, dict[str, Any]]:
    if OUTPUT_NAME_RE.fullmatch(output_name) is None:
        raise ContractError("output name is not an exact resident manifest name")
    output = run_dir / output_name
    if output.exists() or output.is_symlink():
        raise ContractError("final manifest output must be absent")
    validate_local_paths(manifest, run_dir)

    fd, temporary_name = tempfile.mkstemp(
        dir=run_dir,
        prefix=".resident-manifest-",
        suffix=".json",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        manifest_sha256 = sha256_file(temporary)
        spec, promotion_value, issues = promotion.load_spec(
            temporary,
            manifest_sha256,
            allow_draft=False,
        )
        base.verify_local_closure(spec)
        if issues or not promotion_value:
            raise ContractError(f"resident manifest retained issues: {issues}")
        os.link(temporary, output, follow_symlinks=False)
        directory_fd = os.open(run_dir, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        if sha256_file(output) != manifest_sha256:
            raise ContractError("published manifest hash changed")
        return output, manifest_sha256, promotion_value
    finally:
        temporary.unlink(missing_ok=True)


def build(args: argparse.Namespace) -> dict[str, Any]:
    if RUN_ID_RE.fullmatch(args.run_id) is None:
        raise ContractError("run_id is not the exact V3406 resident form")
    if re.fullmatch(r"[0-9]{2}", args.evidence_sequence) is None:
        raise ContractError("evidence sequence must be exactly two digits")
    run_dir = (staging.PRIVATE_RUN_BASE / args.run_id).resolve(strict=True)
    staging.require_below(run_dir, staging.PRIVATE_RUN_BASE, "run directory")

    template, _ = load_exact_json(
        args.template_manifest,
        expected_sha256=args.expect_template_sha256,
    )
    summary, summary_record = load_exact_json(
        run_dir / KEYED_SUMMARY_NAME,
        expected_sha256=args.expect_keyed_summary_sha256,
    )
    connected_path = run_dir / f"connected-d0-{args.evidence_sequence}.json"
    connected_value, connected_record = load_exact_json(
        connected_path,
        expected_sha256=args.expect_connected_d0_sha256,
    )
    paths_path = run_dir / f"connected-path-preflight-{args.evidence_sequence}.json"
    paths_value, paths_record = load_exact_json(
        paths_path,
        expected_sha256=args.expect_path_preflight_sha256,
    )

    template_candidate = require_dict(template.get("candidate_boot"), "candidate_boot")
    template_rollback = require_dict(template.get("rollback_boot"), "rollback_boot")
    validate_canonical_boot_template(template_candidate, template_rollback)
    candidate_spec = select_candidate_profile(args.candidate_profile)
    candidate_record = regular_record(
        run_dir / candidate_spec.name,
        private=True,
        expected_size=candidate_spec.size,
        expected_sha256=candidate_spec.sha256,
    )
    rollback_record = regular_record(
        run_dir / ROLLBACK_NAME,
        private=True,
        expected_size=ROLLBACK_SIZE,
        expected_sha256=ROLLBACK_SHA256,
    )
    host_preparation_record = regular_record(
        run_dir / HOST_PREPARATION_NAME,
        private=True,
        expected_sha256=args.expect_host_preparation_sha256,
    )
    repository_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30.0,
        check=True,
    ).stdout.strip()
    prior_closed_run = (
        bind_prior_closed_run(args.prior_closed_run_id)
        if args.prior_closed_run_id is not None
        else None
    )

    manifest = prepare_manifest(
        template=template,
        run_id=args.run_id,
        run_dir=run_dir,
        evidence_sequence=args.evidence_sequence,
        summary=summary,
        summary_record=summary_record,
        candidate_record=candidate_record,
        rollback_record=rollback_record,
        connected_value=connected_value,
        connected_record=connected_record,
        paths_value=paths_value,
        paths_record=paths_record,
        host_preparation_record=host_preparation_record,
        repository_commit=repository_commit,
        resident_install_v2=args.resident_install_v2,
        candidate_spec=candidate_spec,
        prior_closed_run=prior_closed_run,
    )
    output, manifest_sha256, promotion_value = write_validate_publish(
        manifest,
        run_dir=run_dir,
        output_name=args.output_name,
    )
    return {
        "schema": SCHEMA,
        "decision": PASS_DECISION,
        "run_id": args.run_id,
        "candidate_profile": candidate_spec.profile,
        "prior_closed_run_id": args.prior_closed_run_id,
        "manifest": {
            "path": str(output),
            "size": output.stat().st_size,
            "sha256": manifest_sha256,
        },
        "promotion_mode": promotion_value.get("mode"),
        "device_contact": False,
        "device_write": False,
        "rootfs_staged": False,
        "flash": False,
        "reboot": False,
        "f1_authorized": False,
        "live_authority": False,
        "fresh_exact_f1_approval_required": True,
    }


def audit_payload() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "mode": "host-only-audit",
        "source_sha256": sha256_file(Path(__file__).resolve()),
        "contract": {
            "temporary_production_loader_validation": True,
            "absent_only_final_publication": True,
            "manual_string_replacement": False,
            "device_actions": False,
        },
        "device_contact": False,
        "device_write": False,
        "f1_authorized": False,
        "live_authority": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--audit-only", action="store_true")
    mode.add_argument("--build", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--evidence-sequence", default="01")
    parser.add_argument("--template-manifest", type=Path)
    parser.add_argument("--expect-template-sha256")
    parser.add_argument("--expect-keyed-summary-sha256")
    parser.add_argument("--expect-connected-d0-sha256")
    parser.add_argument("--expect-path-preflight-sha256")
    parser.add_argument("--expect-host-preparation-sha256")
    parser.add_argument("--output-name", default="resident-prepared-manifest.json")
    parser.add_argument("--resident-install-v2", action="store_true")
    parser.add_argument(
        "--candidate-profile",
        choices=tuple(CANDIDATE_PROFILES),
        default=LEGACY_CANDIDATE_PROFILE,
    )
    parser.add_argument("--prior-closed-run-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.audit_only:
        if args.resident_install_v2 or args.prior_closed_run_id is not None:
            raise ContractError("audit mode accepts no build profile")
        connected = (
            "run_id",
            "template_manifest",
            "expect_template_sha256",
            "expect_keyed_summary_sha256",
            "expect_connected_d0_sha256",
            "expect_path_preflight_sha256",
            "expect_host_preparation_sha256",
        )
        if any(getattr(args, name) is not None for name in connected):
            raise ContractError("audit mode accepts no build inputs")
        result = audit_payload()
    else:
        required = (
            "run_id",
            "template_manifest",
            "expect_template_sha256",
            "expect_keyed_summary_sha256",
            "expect_connected_d0_sha256",
            "expect_path_preflight_sha256",
            "expect_host_preparation_sha256",
        )
        missing = [name for name in required if getattr(args, name) is None]
        if missing:
            raise ContractError(f"builder inputs are missing: {missing}")
        result = build(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:  # noqa: BLE001 - concise fail-closed CLI
        print(
            f"a90-resident-manifest-builder-v1: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)

#!/usr/bin/env python3
"""Qualify the Phase 2 display host profiles and emit a non-live H0 packet.

This tool never contacts a device, stages a rootfs, creates a candidate
identity, or grants live authority.  It binds the exact Phase 2B A/B receipts,
reopens their artifacts, audits the currently coupled A90 boot/staging route,
and records the observation contract that a later reviewed runner must
implement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import tomllib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
PRIVATE_OUTPUTS = REPO_ROOT / "workspace" / "private" / "outputs"
CONTRACT = (
    Path(__file__).resolve().parent
    / "phase2c_display_packet_v1"
    / "contract.toml"
)
PACKET_SCHEMA = "a90-phase2c-display-qualification-packet-v1"
DECISION = "A90_PHASE2C_HOST_PROFILES_BOUND_NOT_LIVE_READY"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
ANDROID_BOOT_MAGIC = b"ANDROID!"
EXT4_MAGIC_OFFSET = 1024 + 0x38
EXT4_LABEL_OFFSET = 1024 + 0x78
EXT4_LABEL_SIZE = 16

NATIVE_RELEASE_LOG_RE = re.compile(
    r"^A90D3DISPLAY native_kms_release rc=0 fd_before=[0-9]+ "
    r"disable_plane_rc=0 disable_crtc_rc=0 "
    r"munmap_failures=0 rmfb_failures=0 destroy_dumb_failures=0 "
    r"drop_master_rc=0 close_rc=0 release_complete=1$",
    re.MULTILINE,
)
MODE_RE = re.compile(r"^[1-9][0-9]*x[1-9][0-9]*@[1-9][0-9]*$")
DEVNO_RE = re.compile(r"^[1-9][0-9]*:[0-9]+$")


class ContractError(RuntimeError):
    """Raised when a host input or observation contract is not exact."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_file(value: Any, *, label: str) -> Path:
    if not isinstance(value, str) or value.startswith("/"):
        raise ContractError(f"{label} must be a repository-relative path")
    path = (REPO_ROOT / value).resolve(strict=True)
    try:
        path.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ContractError(f"{label} escapes the repository") from exc
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ContractError(f"{label} must be a regular non-symlink file")
    return path


def exact_hash(path: Path, expected: Any, *, label: str) -> str:
    if not isinstance(expected, str) or HEX64_RE.fullmatch(expected) is None:
        raise ContractError(f"{label} expected sha256 is invalid")
    actual = sha256_file(path)
    if actual != expected:
        raise ContractError(
            f"{label} sha256 mismatch: expected={expected} actual={actual}"
        )
    return actual


def load_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label} is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be a JSON object")
    return value


def load_contract(path: Path = CONTRACT) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    if resolved != CONTRACT.resolve(strict=True):
        raise ContractError("only the canonical Phase 2C contract is accepted")
    with resolved.open("rb") as stream:
        value = tomllib.load(stream)
    if (
        value.get("schema") != "a90-phase2c-display-qualification-v1"
        or value.get("profile") != "phase2-display-v1"
        or value.get("candidate_authority") is not False
        or value.get("device_action") is not False
        or value.get("live_authority") is not False
    ):
        raise ContractError("Phase 2C contract authority fields are not exact")
    return value


def require_artifact(
    path: Path,
    *,
    expected_size: int,
    expected_sha256: str,
    label: str,
) -> dict[str, Any]:
    if path.stat().st_size != expected_size:
        raise ContractError(f"{label} size mismatch")
    actual = exact_hash(path, expected_sha256, label=label)
    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "bytes": expected_size,
        "sha256": actual,
    }


def validate_native(contract: dict[str, Any]) -> dict[str, Any]:
    native = contract["native"]
    receipt_path = repo_file(native["receipt"], label="native receipt")
    exact_hash(
        receipt_path,
        native["receipt_sha256"],
        label="native receipt",
    )
    manifest_path = repo_file(native["manifest"], label="native manifest")
    exact_hash(
        manifest_path,
        native["manifest_sha256"],
        label="native manifest",
    )
    receipt = load_json(receipt_path, label="native receipt")
    expected_artifacts = {
        "boot": native["boot_sha256"],
        "ramdisk": native["ramdisk_sha256"],
        "init": native["init_sha256"],
        "helper": native["helper_sha256"],
        "engine": native["engine_sha256"],
    }
    if (
        receipt.get("schema") != "a90-flat-builder-v1-ab-receipt"
        or receipt.get("profile") != "phase2-display-v1-native-handoff"
        or receipt.get("byte_identical") is not True
        or receipt.get("accepted_boot_unchanged") is not True
        or receipt.get("candidate_authority") is not False
        or receipt.get("manifest_sha256") != native["manifest_sha256"]
    ):
        raise ContractError("native A/B receipt semantics are not exact")
    artifacts = receipt.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(expected_artifacts):
        raise ContractError("native A/B receipt artifact set is not exact")
    for name, expected in expected_artifacts.items():
        entry = artifacts.get(name)
        if (
            not isinstance(entry, dict)
            or entry.get("sha256") != expected
            or not isinstance(entry.get("bytes"), int)
            or entry["bytes"] <= 0
            or not isinstance(entry.get("path"), str)
        ):
            raise ContractError(f"native receipt {name} identity mismatch")

    boot_a = repo_file(native["boot_a"], label="native boot A")
    boot_b = repo_file(native["boot_b"], label="native boot B")
    verified_pairs: dict[str, dict[str, dict[str, Any]]] = {}
    for name, expected_sha256 in expected_artifacts.items():
        entry = artifacts[name]
        expected_relative = Path(entry["path"])
        if (
            expected_relative.is_absolute()
            or ".." in expected_relative.parts
            or expected_relative
            != (Path("boot.img") if name == "boot" else Path("build") / (
                "ramdisk.cpio" if name == "ramdisk" else name
            ))
        ):
            raise ContractError(f"native receipt {name} path is not exact")
        pair: dict[str, dict[str, Any]] = {}
        for side, boot in (("A", boot_a), ("B", boot_b)):
            artifact = repo_file(
                str((boot.parent / expected_relative).relative_to(REPO_ROOT)),
                label=f"native {name} {side}",
            )
            pair[side] = require_artifact(
                artifact,
                expected_size=entry["bytes"],
                expected_sha256=expected_sha256,
                label=f"native {name} {side}",
            )
        verified_pairs[name] = pair
    boot_a_record = verified_pairs["boot"]["A"]
    boot_b_record = verified_pairs["boot"]["B"]
    with boot_a.open("rb") as stream:
        if stream.read(len(ANDROID_BOOT_MAGIC)) != ANDROID_BOOT_MAGIC:
            raise ContractError("native boot A lacks Android boot magic")
    return {
        "profile": receipt["profile"],
        "manifest_sha256": native["manifest_sha256"],
        "receipt_sha256": native["receipt_sha256"],
        "artifacts": expected_artifacts,
        "verified_pairs": verified_pairs,
        "boot_a": boot_a_record,
        "boot_b": boot_b_record,
        "byte_identical": True,
        "candidate_authority": False,
    }


def debugfs_path_absent(image: Path, target: str) -> bool:
    result = subprocess.run(
        ["debugfs", "-R", f"stat {target}", str(image)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60.0,
    )
    text = result.stdout + result.stderr
    return result.returncode == 0 and "File not found by ext2_lookup" in text


def read_ext4_identity(path: Path) -> tuple[bytes, str]:
    with path.open("rb") as stream:
        stream.seek(EXT4_MAGIC_OFFSET)
        magic = stream.read(2)
        stream.seek(EXT4_LABEL_OFFSET)
        raw_label = stream.read(EXT4_LABEL_SIZE)
    label = raw_label.split(b"\0", 1)[0].decode("ascii")
    return magic, label


def validate_debian(contract: dict[str, Any]) -> dict[str, Any]:
    debian = contract["debian"]
    receipt_path = repo_file(debian["receipt"], label="Debian receipt")
    exact_hash(
        receipt_path,
        debian["receipt_sha256"],
        label="Debian receipt",
    )
    manifest_path = repo_file(debian["manifest"], label="Debian manifest")
    exact_hash(
        manifest_path,
        debian["manifest_sha256"],
        label="Debian manifest",
    )
    receipt = load_json(receipt_path, label="Debian receipt")
    if (
        receipt.get("schema") != "a90-phase2-display-v1-ab-receipt"
        or receipt.get("profile") != "phase2-display-v1"
        or receipt.get("candidate_authority") is not False
        or receipt.get("device_action") is not False
        or receipt.get("flash") is not False
        or receipt.get("host_only") is not True
        or receipt.get("image_byte_identical") is not True
        or receipt.get("presenter_byte_identical") is not True
        or receipt.get("source_unchanged") is not True
        or receipt.get("manifest_sha256") != debian["manifest_sha256"]
    ):
        raise ContractError("Debian A/B receipt semantics are not exact")
    for side in ("A", "B"):
        side_value = receipt.get(side)
        image_value = side_value.get("image") if isinstance(side_value, dict) else None
        presenter = (
            side_value.get("presenter") if isinstance(side_value, dict) else None
        )
        if (
            not isinstance(image_value, dict)
            or image_value.get("bytes") != debian["image_bytes"]
            or image_value.get("sha256") != debian["image_sha256"]
            or not isinstance(presenter, dict)
            or presenter.get("sha256") != debian["presenter_sha256"]
            or side_value.get("e2fsck_read_only_rc") != 0
        ):
            raise ContractError(f"Debian receipt side {side} is not exact")

    image_a = repo_file(debian["image_a"], label="Debian image A")
    image_b = repo_file(debian["image_b"], label="Debian image B")
    records = {}
    presenters = {}
    for side, image in (("A", image_a), ("B", image_b)):
        side_value = receipt[side]
        records[side] = require_artifact(
            image,
            expected_size=debian["image_bytes"],
            expected_sha256=debian["image_sha256"],
            label=f"Debian image {side}",
        )
        magic, label = read_ext4_identity(image)
        if magic != b"\x53\xef" or label != debian["filesystem_label"]:
            raise ContractError(f"Debian image {side} ext4 identity mismatch")
        presenter = repo_file(
            str(
                (image.parent / "a90-debian-display-v1").relative_to(
                    REPO_ROOT
                )
            ),
            label=f"Debian presenter {side}",
        )
        presenters[side] = require_artifact(
            presenter,
            expected_size=side_value["presenter"]["bytes"],
            expected_sha256=debian["presenter_sha256"],
            label=f"Debian presenter {side}",
        )

    absent_paths = debian["clean_absent_paths"]
    if not isinstance(absent_paths, list) or not absent_paths:
        raise ContractError("Debian clean-absence path set is empty")
    for target in absent_paths:
        if not isinstance(target, str) or not target.startswith("/"):
            raise ContractError("Debian clean-absence target is invalid")
        if not debugfs_path_absent(image_a, target):
            raise ContractError(f"Debian clean image unexpectedly contains {target}")
    return {
        "profile": receipt["profile"],
        "manifest_sha256": debian["manifest_sha256"],
        "receipt_sha256": debian["receipt_sha256"],
        "image_sha256": debian["image_sha256"],
        "image_bytes": debian["image_bytes"],
        "presenter_sha256": debian["presenter_sha256"],
        "presenters": presenters,
        "images": records,
        "clean_absent_paths": absent_paths,
        "observer_key_materialized": False,
        "role": "clean-deterministic-base-not-final-keyed-rootfs",
        "candidate_authority": False,
    }


def function_slice(source: str, start: str, end: str) -> str:
    begin = source.find(start)
    finish = source.find(end, begin + len(start))
    if begin < 0 or finish < 0:
        raise ContractError(f"source boundary missing: {start} .. {end}")
    return source[begin:finish]


def validate_machinery(contract: dict[str, Any]) -> dict[str, Any]:
    machinery = contract["machinery"]
    paths: dict[str, Path] = {}
    for name in ("flash_runner", "staging_adapter", "orchestrator"):
        path = repo_file(machinery[name], label=name)
        exact_hash(path, machinery[f"{name}_sha256"], label=name)
        paths[name] = path
    flash = paths["flash_runner"].read_text(encoding="utf-8")
    stage = paths["staging_adapter"].read_text(encoding="utf-8")
    orchestrator = paths["orchestrator"].read_text(encoding="utf-8")

    flash_command = function_slice(
        orchestrator,
        "def flash_command(",
        "\ndef validate_stage_result(",
    )
    required_flash_tokens = (
        "str(bound.path)",
        '"--expect-sha256"',
        "bound.sha256",
        '"--expect-version"',
        "version",
        '"--serial"',
        "spec.recovery_serial",
        'command.append("--from-native")',
    )
    if any(token not in flash_command for token in required_flash_tokens):
        raise ContractError("coupled A90 flash command lost an exact binding")
    for forbidden in (
        "--allow-unpinned-image",
        "--boot-block",
        "--experimental-self-write",
        "--self-write-live-authorized",
    ):
        if forbidden in flash_command:
            raise ContractError(f"coupled A90 flash command adds {forbidden}")
    if (
        'default="/dev/block/by-name/boot"' not in flash
        or 'raise SystemExit("refusing to flash without --expect-sha256")' not in flash
        or "remote_hash != local_hash" not in flash
        or "boot_prefix_hash != expected_readback_hash" not in flash
        or "with sealed_local_image_copy(" not in flash
    ):
        raise ContractError("A90 flash runner boot/hash/readback closure drifted")

    publish = function_slice(
        stage,
        "def remote_publish_script(",
        "\ndef remote_cleanup_script(",
    )
    if (
        '[ ! -e "$WORK" ]' not in publish
        or '/bin/busybox ln "$PAYLOAD" "$FINAL"' not in publish
        or "no_clobber=hardlink" not in publish
        or '/bin/busybox rm "$FINAL"' in publish
    ):
        raise ContractError("absent-only rootfs publication closure drifted")
    if (
        'REMOTE_WORK = REMOTE_ROOT / "d3-handoff-work.img"' not in stage
        or machinery["fixed_work_image"]
        != "/mnt/sdext/a90/runtime/d3-handoff-work.img"
    ):
        raise ContractError("fixed work-image identity drifted")
    cycles = set(machinery["supported_live_cycles"])
    if cycles != {"v3403", "v3404", "v3405"}:
        raise ContractError("current staging cycle inventory is not exact")

    ssh_observer = function_slice(
        orchestrator,
        "def ssh_command(",
        "\ndef observe_ssh(",
    )
    current_display_observation = (
        "/run/a90-display/ready" in ssh_observer
        and "/run/a90-display/failure" in ssh_observer
        and "A90D3DISPLAY native_kms_release" in orchestrator
    )
    if current_display_observation:
        raise ContractError(
            "orchestrator gained display observation without a Phase 2C contract update"
        )
    return {
        "hashes": {
            name: machinery[f"{name}_sha256"]
            for name in ("flash_runner", "staging_adapter", "orchestrator")
        },
        "checked_boot_only_coupled_route": True,
        "direct_runner_general_interface_is_not_the_coupled_proof": True,
        "candidate_and_rollback_hash_version_serial_bound": True,
        "boot_prefix_readback_required": True,
        "absent_only_hardlink_publication": True,
        "fixed_work_image": machinery["fixed_work_image"],
        "work_must_be_absent": True,
        "automatic_work_cleanup_allowed": False,
        "supported_live_cycles": sorted(cycles),
        "phase2_profile_supported_for_live_staging": False,
        "display_observation_integrated": False,
    }


def parse_exact_marker(text: str) -> dict[str, str]:
    if not isinstance(text, str) or not text.endswith("\n"):
        raise ContractError("marker must be newline terminated")
    result: dict[str, str] = {}
    for line in text.splitlines():
        if not line or "=" not in line:
            raise ContractError("marker contains an invalid line")
        key, value = line.split("=", 1)
        if not key or key in result or not value:
            raise ContractError("marker keys must be unique and nonempty")
        result[key] = value
    return result


def validate_native_release_evidence(log_text: str, marker_text: str) -> None:
    if NATIVE_RELEASE_LOG_RE.search(log_text) is None:
        raise ContractError("native KMS release success line is absent")
    for line in (
        "A90D3DISPLAY native_pid1_drm_fd_count=0 observed=0",
        "A90D3DISPLAY other_drm_fd_count=0 observed=0",
        "A90D3DISPLAY native_kms_initialized=0 observed=0",
        "A90D3DISPLAY display_services_restart_blocked=1 "
        "corridor=synchronous-handoff",
    ):
        if log_text.count(line) != 1:
            raise ContractError(f"native release evidence is not exact: {line}")
    marker = parse_exact_marker(marker_text)
    if marker != {
        "schema": "a90-native-display-release-v1",
        "native_pid1_drm_fd_count": "0",
        "other_drm_fd_count": "0",
        "native_kms_initialized": "0",
        "display_services_restart_blocked": "1",
        "release_complete": "1",
    }:
        raise ContractError("native release marker is not exact")


def positive_int(value: str, *, label: str) -> int:
    if not value.isdigit() or int(value) <= 0:
        raise ContractError(f"{label} must be a positive integer")
    return int(value)


def validate_debian_ready_marker(
    marker_text: str,
    *,
    display_uid: int = 3904,
    display_gid: int = 3904,
) -> dict[str, str]:
    marker = parse_exact_marker(marker_text)
    expected_keys = {
        "schema",
        "pid1_exe",
        "presenter_pid",
        "presenter_uid",
        "presenter_gid",
        "presenter_cap_eff",
        "no_new_privs",
        "controlling_vt",
        "drm_node",
        "drm_node_major_minor",
        "drm_master",
        "connector_id",
        "crtc_id",
        "mode",
        "setcrtc_rc",
        "native_pid1_drm_fd_count",
        "other_native_drm_fd_count",
        "presenter_self_drm_fd_count",
        "other_process_drm_fd_count",
        "native_init_process_count",
    }
    if set(marker) != expected_keys:
        raise ContractError("Debian display-ready marker key set is not exact")
    fixed = {
        "schema": "a90-debian-display-v1",
        "pid1_exe": "/usr/sbin/init",
        "presenter_uid": str(display_uid),
        "presenter_gid": str(display_gid),
        "presenter_cap_eff": "0000000000000000",
        "no_new_privs": "1",
        "controlling_vt": "none",
        "drm_node": "/dev/dri/card0",
        "drm_master": "1",
        "setcrtc_rc": "0",
        "native_pid1_drm_fd_count": "0",
        "other_native_drm_fd_count": "0",
        "presenter_self_drm_fd_count": "1",
        "other_process_drm_fd_count": "0",
        "native_init_process_count": "0",
    }
    for key, value in fixed.items():
        if marker.get(key) != value:
            raise ContractError(f"Debian display-ready {key} is not exact")
    positive_int(marker["presenter_pid"], label="presenter_pid")
    positive_int(marker["connector_id"], label="connector_id")
    positive_int(marker["crtc_id"], label="crtc_id")
    if DEVNO_RE.fullmatch(marker["drm_node_major_minor"]) is None:
        raise ContractError("DRM major/minor is not exact")
    if MODE_RE.fullmatch(marker["mode"]) is None:
        raise ContractError("display mode is not exact")
    return marker


def validate_bounded_failure_marker(
    marker_text: str,
    *,
    max_attempts: int = 3,
    ready_absent: bool,
) -> dict[str, str]:
    marker = parse_exact_marker(marker_text)
    if set(marker) != {"schema", "attempt", "rc"}:
        raise ContractError("display failure marker key set is not exact")
    if (
        marker["schema"] != "a90-debian-display-v1-failure"
        or marker["attempt"] != str(max_attempts)
        or not marker["rc"].isdigit()
        or int(marker["rc"]) == 0
        or ready_absent is not True
    ):
        raise ContractError("bounded display failure evidence is not terminal")
    return marker


def observation_contract(contract: dict[str, Any]) -> dict[str, Any]:
    observation = contract["observation"]
    return {
        "one_run_atomic_requirements": [
            "exact candidate health before handoff",
            "fresh exact final rootfs and absent fixed work image",
            "one native release log and exact release marker",
            "Debian sysvinit PID1 and exact display-ready marker",
            "operator sees all four fixed Phase 2 display strings",
            "healthy no-sync candidate return with retained armed pmsg",
            "one exact rollback and final baseline health",
        ],
        "native_release": {
            "schema": observation["native_release_schema"],
            "requires_ioctl_success": True,
            "requires_zero_all_drm_owners": True,
            "requires_synchronous_restart_block": True,
        },
        "debian_acquisition": {
            "schema": observation["debian_ready_schema"],
            "uid": observation["display_uid"],
            "gid": observation["display_gid"],
            "sole_drm_master": True,
            "cap_eff": "0000000000000000",
            "no_new_privs": True,
            "controlling_vt": "none",
        },
        "visible_acquisition": {
            "expected_text": observation["visible_text"],
            "future_attended_receipt_must_bind": [
                "manifest_sha256",
                "candidate_boot_sha256",
                "final_keyed_rootfs_sha256",
                "display_ready_marker_sha256",
                "observation_deadline_utc",
            ],
            "freeform_acknowledgement_is_proof": False,
        },
        "bounded_failure": {
            "schema": observation["debian_failure_schema"],
            "terminal_attempt": observation["max_display_attempts"],
            "ready_marker_must_be_absent": True,
            "candidate_replay": False,
            "rollback_remains_mandatory": True,
            "formal_result_if_health_restored": (
                "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
            ),
        },
        "return": {
            "no_global_sync": True,
            "retained_pmsg_marker": observation["return_marker"],
            "required_phase": observation["required_return_phase"],
            "candidate_return_required_before_rollback": True,
        },
    }


def build_packet(contract_path: Path = CONTRACT) -> dict[str, Any]:
    contract = load_contract(contract_path)
    native = validate_native(contract)
    debian = validate_debian(contract)
    machinery = validate_machinery(contract)
    blockers = [
        {
            "code": "FINAL_KEYED_ROOTFS_NOT_MATERIALIZED",
            "detail": (
                "Phase 2B ext4 is a clean deterministic base; a future run must "
                "create a new-inode single-run keyed image and bind its new hash."
            ),
        },
        {
            "code": "PHASE2_LIVE_STAGING_IDENTITY_NOT_DEFINED",
            "detail": (
                "The current absent-only adapter accepts only V3403-V3405 run "
                "identities; Phase 2C deliberately assigns no candidate cycle."
            ),
        },
        {
            "code": "DISPLAY_OBSERVATION_NOT_IN_EXECUTION_RUNNER",
            "detail": (
                "The current orchestrator proves Debian PID1/Dropbear/return but "
                "does not parse native release, display ready/failure, or a "
                "manifest-bound visible-acquisition receipt."
            ),
        },
        {
            "code": "FRESH_D0_MANIFEST_APPROVAL_ABSENT",
            "detail": (
                "No target-bound D0, final manifest, rollback binding, or fresh "
                "F1 approval exists for this host profile."
            ),
        },
    ]
    return {
        "schema": PACKET_SCHEMA,
        "decision": DECISION,
        "profile": contract["profile"],
        "contract_sha256": sha256_file(CONTRACT),
        "packet_generator_sha256": sha256_file(Path(__file__).resolve()),
        "native": native,
        "debian": debian,
        "machinery": machinery,
        "observation_contract": observation_contract(contract),
        "host_profiles_bound": True,
        "ready_for_live_candidate": False,
        "blockers": blockers,
        "next_change_unit": (
            "reviewed per-run keying plus Phase 2 display observation integration"
        ),
        "independent_review_required_before_live_use": True,
        "safety": {
            "host_only": True,
            "candidate_identity_created": False,
            "candidate_authority": False,
            "live_authority": False,
            "device_contact": False,
            "device_write": False,
            "rootfs_staged": False,
            "flash": False,
            "reboot": False,
        },
    }


def write_packet(output_dir: Path, packet: dict[str, Any]) -> Path:
    try:
        resolved_parent = output_dir.parent.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ContractError("output directory parent must already exist") from exc
    if resolved_parent != PRIVATE_OUTPUTS.resolve(strict=True):
        raise ContractError(
            "output directory must be a new direct child of workspace/private/outputs"
        )
    output_dir = resolved_parent / output_dir.name
    if output_dir.exists() or output_dir.is_symlink():
        raise ContractError("output directory must be absent")
    output_dir.mkdir(mode=0o700)
    path = output_dir / "packet.json"
    body = (
        json.dumps(packet, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
        0o600,
    )
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)
    directory_fd = os.open(output_dir, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    packet = build_packet(args.contract)
    if args.output_dir is not None:
        path = write_packet(args.output_dir, packet)
        packet = {**packet, "private_packet_path": str(path.relative_to(REPO_ROOT))}
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:  # noqa: BLE001 - concise fail-closed CLI
        print(
            f"a90-phase2c-display-packet: {type(exc).__name__}: {exc}",
            file=os.sys.stderr,
        )
        raise SystemExit(1)

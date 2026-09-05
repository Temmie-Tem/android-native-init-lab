#!/usr/bin/env python3
"""Prepare the P341 Process-v2 promotion projection on the host only.

The P341 static receipt, boot-only candidate AP, and exact stock rollback are
reopened by identity.  This module emits in-memory candidate-static,
run-manifest, and static-check payloads and asks common evidence to verify
their closure.  Publication is explicit and is never performed by ``build``.
No device, ADB, USB, Odin, approval, or later-action lease is created here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = Path(__file__).resolve().parent
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for _directory in (ANALYSIS, REVALIDATION):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as core  # noqa: E402
import s22plus_fyg8_p341_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p341_open_read_branch_acm_observer as framed_observer  # noqa: E402
import s22plus_fyg8_p341_open_read_branch_runtime as framed_runtime  # noqa: E402
import s22plus_fyg8_p341_process_v2_candidate_static as candidate_static  # noqa: E402
import s22plus_fyg8_p341_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p341_stock_process_v2_adapter as adapter  # noqa: E402


SCHEMA = "s22plus_fyg8_p341_process_v2_promotion_v1"
VERDICT = "PASS_P341_PROCESS_V2_PROMOTION_HOST_ONLY"
READY_SCHEMA = "s22plus_fyg8_p341_ready_manifest_builder_v1"
READY_VERDICT = "PASS_P341_PROCESS_V2_READY_MANIFEST_HOST_ONLY"
REHEARSAL_VERDICT = "PASS_P341_PROCESS_V2_READY_MANIFEST_REHEARSAL_HOST_ONLY"
RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p341_process_v2_run_manifest_v1"
STATIC_RESULT_SCHEMA = "s22plus_fyg8_p341_process_v2_static_result_v1"
STATIC_RESULT_VERDICT = "PASS_P341_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
DEFAULT_BUILDER_OUTPUT = Path(candidate_build.DEFAULT_OUTPUT_ROOT).absolute()
DEFAULT_STATIC_OUTPUT = candidate_static.DEFAULT_OUTPUT
DEFAULT_CANDIDATE_AP = DEFAULT_BUILDER_OUTPUT / "candidate-a/odin4/AP.tar.md5"
DEFAULT_ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
DEFAULT_PROMOTION = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p341/"
    "process-v2-promotion-20260905-01"
)
DEFAULT_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p341_process_v2_ready_1.json"
)
DEFAULT_TARGET_PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
DEFAULT_MANIFEST_ID = "s22plus-fyg8-p341-process-v2-ready-1"
DEFAULT_LIVE_RUN_ID = "s22plus-fyg8-p341-live-1"
DEFAULT_TIMEOUT_SEC = 300
TARGET = dict(candidate_static.TARGET)
RUN_ID = candidate_static.RUN_ID
PREDECESSOR_RUN_ID = candidate_static.PREDECESSOR_RUN_ID
ROLLBACK_IDENTITY = dict(candidate_static.ROLLBACK_IDENTITY)
AUTH_KEY_IDENTITY = dict(candidate_static.AUTH_KEY_IDENTITY)
TARGET_STRING = f"{TARGET['model']}/{TARGET['codename']}/{TARGET['build']}"


class PromotionError(ValueError):
    """The exact P341 promotion closure or manifest is invalid."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise PromotionError("P341 promotion value is not canonical JSON") from exc


def manifest_bytes(value: dict[str, Any]) -> bytes:
    try:
        return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(
            "ascii"
        )
    except (TypeError, ValueError, UnicodeError) as exc:
        raise PromotionError("P341 ready manifest is not canonical JSON") from exc


def relative(path: Path) -> str:
    direct = path.absolute()
    try:
        return direct.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise PromotionError("P341 path escaped the repository") from exc


def _inode(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def stable_bytes(
    path: Path,
    label: str,
    maximum: int,
    *,
    expected: dict[str, Any] | None = None,
    mode: int | None = None,
    nlink: int = 1,
) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise PromotionError(f"{label} is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != nlink
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or len(payload) > maximum
        or (expected is not None and identity(payload) != dict(expected))
        or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
    ):
        raise PromotionError(f"{label} identity differs")
    return payload


def _decode(payload: bytes, label: str) -> dict[str, Any]:
    def unique(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise PromotionError(f"{label} has duplicate key {key}")
            result[key] = value
        return result

    try:
        value = json.loads(payload.decode("ascii"), object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PromotionError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise PromotionError(f"{label} is not an object")
    return value


def _candidate_inputs(
    static_path: Path,
    candidate_ap_path: Path,
) -> tuple[dict[str, Any], bytes, dict[str, Any], bytes, dict[str, Any]]:
    static_path = static_path.absolute()
    try:
        static_lstat = static_path.lstat()
    except FileNotFoundError:
        static_lstat = None
    except OSError as exc:
        raise PromotionError("P341 candidate-static path is unavailable") from exc
    if static_lstat is None:
        static_value = candidate_static.build_result()
        static_payload = candidate_static.canonical(static_value)
    else:
        static_payload = stable_bytes(
            static_path, "P341 candidate-static", 2 * 1024 * 1024, mode=0o400
        )
        static_value = _decode(static_payload, "P341 candidate-static")
        if static_payload != candidate_static.canonical(static_value):
            raise PromotionError("P341 candidate-static bytes are not canonical")
        try:
            candidate_static.validate_result(static_value)
        except Exception as exc:
            raise PromotionError("P341 candidate-static did not reopen") from exc

    builder_path = DEFAULT_BUILDER_OUTPUT / "result.json"
    builder_expected = static_value.get("builder_result")
    if not isinstance(builder_expected, dict):
        raise PromotionError("P341 static receipt does not bind builder result")
    builder_payload = stable_bytes(
        builder_path,
        "P341 builder result",
        4 * 1024 * 1024,
        expected={key: builder_expected[key] for key in ("size", "sha256")},
        mode=0o400,
    )
    builder_value = _decode(builder_payload, "P341 builder result")
    try:
        audited = candidate_build.audit_existing(DEFAULT_BUILDER_OUTPUT)
    except Exception as exc:
        raise PromotionError("P341 builder result did not reopen") from exc
    if audited != builder_value:
        raise PromotionError("P341 builder result changed")

    candidate = static_value.get("candidate")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("a"), dict):
        raise PromotionError("P341 candidate-static package is incomplete")
    image = stable_bytes(
        DEFAULT_BUILDER_OUTPUT / "inputs/fixed-Image",
        "P341 candidate Image",
        64 * 1024 * 1024,
        expected=candidate.get("image"),
        mode=0o400,
    )
    init = stable_bytes(
        DEFAULT_BUILDER_OUTPUT / "userspace-a/init",
        "P341 candidate init",
        2 * 1024 * 1024,
        expected=candidate.get("init"),
        mode=0o400,
    )
    child = stable_bytes(
        DEFAULT_BUILDER_OUTPUT / "userspace-a/s22-e1-child",
        "P341 candidate child",
        2 * 1024 * 1024,
        expected=candidate.get("child"),
        mode=0o400,
    )
    ap_payload = stable_bytes(candidate_ap_path, "P341 candidate AP", 64 * 1024 * 1024)
    try:
        ap_info = artifact.inspect_ap(
            candidate_ap_path,
            expected_run_id=artifact.P341_RUN_ID,
            expected_image=image,
            expected_init=init,
            expected_child=child,
            expected_ap=identity(ap_payload),
            label="P341 candidate AP",
        )
    except Exception as exc:
        raise PromotionError("P341 candidate AP is invalid") from exc
    if ap_info["ap_structure"]["member"]["name"] != "boot.img.lz4":
        raise PromotionError("P341 candidate AP is not boot-only")
    ap_receipt = {
        **identity(ap_payload),
        "member": dict(ap_info["ap_structure"]["member"]),
    }
    if candidate["a"].get("ap_tar_md5") != {
        key: ap_receipt[key] for key in ("size", "sha256")
    }:
        raise PromotionError("P341 candidate-static AP identity differs")
    return static_value, static_payload, builder_value, builder_payload, ap_receipt


def _acceptance(payloads: dict[str, bytes], output: Path) -> dict[str, Any]:
    value = adapter.acceptance_fixture()
    value["auth_key"] = dict(AUTH_KEY_IDENTITY)
    value["contract"] = {
        name: {"path": relative(output / filename), **identity(payloads[name])}
        for name, filename in {
            "candidate_static": "candidate-static.json",
            "run_manifest": "run-manifest.json",
            "static_check": "static-check-result.json",
        }.items()
    }
    try:
        adapter.validate_acceptance_item(value)
    except Exception as exc:
        raise PromotionError(f"P341 acceptance identity differs: {exc}") from exc
    return value


def _promotion_payloads(
    static_value: dict[str, Any],
    static_payload: bytes,
    ap_receipt: dict[str, Any],
) -> dict[str, bytes]:
    candidate = static_value.get("candidate")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("a"), dict):
        raise PromotionError("P341 candidate package is incomplete")
    expected_authentication = {
        "required": True,
        "scheme": "auth-key-v1",
        "key": AUTH_KEY_IDENTITY,
        "path_published": False,
        "candidate_possession_implies_key_possession": True,
        "hardware_backed": False,
    }
    if static_value.get("authentication") != expected_authentication:
        raise PromotionError("P341 authentication receipt differs")
    acceptance_template = adapter.audit()["acceptance"]
    run_manifest = {
        "schema": RUN_MANIFEST_SCHEMA,
        "target": TARGET_STRING,
        "profile": adapter.PROFILE,
        "run_id": RUN_ID,
        "decoder": adapter.DECODER_ID,
        "policy_id": adapter.POLICY_ID,
        "records": {
            "long_family_hex": acceptance_template["long_family_hex"],
            "unsat_family_hex": acceptance_template["unsat_family_hex"],
            "terminal_stage": acceptance_template["terminal_stage"],
        },
        "observation_contract": {
            "accepted_identity": "P341_STOCK_OBSERVER_V4_OPEN_HEADER_CAPTURE",
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "runtime_values_preflighted": False,
            "complete_is_noncausal": True,
            "incomplete_result": "NO_PROOF_EXPERIMENT_PRECONDITION",
            "receipt_result": "NO_PROOF_OBSERVER",
            "host_first_open": True,
            "host_open_before_banner": True,
            "device_banner_after_open": True,
            "stage_zero_after_banner": True,
            "open_parsed_after_stage_zero": True,
            "no_unsolicited_device_tx": True,
            "silent_no_peer_no_proof": True,
            "consumed_partial_open_no_replay": True,
            "successful_wire_exchange_unchanged": False,
            "runtime_order_changed": True,
        },
        "candidate_ap": {key: ap_receipt[key] for key in ("size", "sha256")},
        "candidate_static": identity(static_payload),
        "source_contract_id": adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": adapter.OVERLAY_CONTRACT_ID,
    }
    run_payload = canonical(run_manifest)
    static_check = {
        "schema": STATIC_RESULT_SCHEMA,
        "target": TARGET_STRING,
        "verdict": STATIC_RESULT_VERDICT,
        "profile": adapter.PROFILE,
        "run_id": RUN_ID,
        "decoder": adapter.DECODER_ID,
        "policy_id": adapter.POLICY_ID,
        "source_contract_id": adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": adapter.OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
        "candidate": {
            "artifacts": {
                "ap": {key: ap_receipt[key] for key in ("size", "sha256")},
                "candidate_static": identity(static_payload),
                "boot_image": candidate["a"]["boot_img"],
                "boot_img_lz4": candidate["a"]["boot_img_lz4"],
                "image": candidate["image"],
                "init": candidate["init"],
                "child": candidate["child"],
                "busybox": candidate["busybox"],
                "latch": {
                    key: static_value["source_closure"]["latch"][key]
                    for key in ("size", "sha256")
                },
            },
            "boot_only_ap": True,
            "independent_static_contract": True,
            "complete_is_noncausal": True,
            "runtime_values_observed": False,
            "verified": True,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
        },
    }
    return {
        "candidate_static": static_payload,
        "run_manifest": run_payload,
        "static_check": canonical(static_check),
    }


def _observer_spec() -> dict[str, Any]:
    return dict(evidence.p341_authenticated_open_read_branch_observer_spec())


def _common_support() -> bool:
    return (
        getattr(evidence, "P341_STOCK_OVERLAY_CONTRACT_ID", None)
        == adapter.OVERLAY_CONTRACT_ID
        and getattr(evidence, "P341_RUN_MANIFEST_SCHEMA", None) == RUN_MANIFEST_SCHEMA
        and getattr(evidence, "P341_STATIC_RESULT_SCHEMA", None) == STATIC_RESULT_SCHEMA
    )


def _offline_verification(
    acceptance: dict[str, Any],
    payloads: dict[str, bytes],
    ap_receipt: dict[str, Any],
) -> dict[str, Any]:
    if not _common_support():
        return {
            "schema": "device_action_f1_p341_stock_offline_contract_pending_v1",
            "run_id": RUN_ID,
            "verified": False,
            "common_offline_verified": False,
            "common_registration_pending": True,
            "device_contact": False,
            "live_authorized": False,
            "candidate_success": False,
            "causal_result_allowed": False,
        }
    try:
        value = evidence.verify_offline_contract(
            acceptance,
            payloads=payloads,
            receipts={name: identity(data) for name, data in payloads.items()},
            candidate_ap=ap_receipt,
        )
    except Exception as exc:
        raise PromotionError(f"P341 common offline verification failed: {exc}") from exc
    value["common_offline_verified"] = True
    return value


def _manifest(
    *,
    promotion_root: Path,
    payloads: dict[str, bytes],
    candidate_ap: dict[str, Any],
    rollback_ap: dict[str, Any],
    target_profile: Path,
    manifest_id: str,
    live_run_id: str,
    timeout_sec: int,
    common_verified: bool,
) -> dict[str, Any]:
    run_manifest = _decode(payloads["run_manifest"], "P341 run manifest")
    expected = {
        "source_contract_id": adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": adapter.OVERLAY_CONTRACT_ID,
        "profile": adapter.PROFILE,
        "run_id": RUN_ID,
        "candidate_ap": {key: candidate_ap[key] for key in ("size", "sha256")},
        "candidate_static": identity(payloads["candidate_static"]),
    }
    if any(run_manifest.get(key) != value for key, value in expected.items()):
        raise PromotionError("P341 promotion run manifest differs")
    if type(timeout_sec) is not int or not 1 <= timeout_sec <= 600:
        raise PromotionError("P341 observation timeout is invalid")
    acceptance = _acceptance(payloads, promotion_root)
    return {
        "schema": core.MANIFEST_SCHEMA,
        "manifest_id": manifest_id,
        "run_id": live_run_id,
        "status": "ready-for-f1-approval" if common_verified else "host-only-review-pending",
        "target_profile": relative(target_profile),
        "candidate_ap": {
            key: candidate_ap[key] for key in ("path", "size", "sha256")
        },
        "rollback_ap": rollback_ap,
        "allowed_member": "boot.img.lz4",
        "observation": {
            "timeout_sec": timeout_sec,
            "acceptance": acceptance,
            "candidate_observer": _observer_spec(),
            evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY: getattr(
                evidence,
                "CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE",
                "p332_authenticated_logical_resident_same_fd_session_v1",
            ),
        },
        "final_health_profile": "s22plus-fyg8-magisk",
        "runner_version": core.RUNNER_VERSION,
    }


def verify_manifest(
    value: dict[str, Any],
    payload: bytes,
    *,
    promotion_payloads: dict[str, bytes] | None = None,
) -> None:
    if payload != manifest_bytes(value):
        raise PromotionError("P341 ready manifest bytes differ")
    if not _common_support():
        return
    private_root = ROOT / "workspace/private"
    try:
        private_root.lstat()
    except OSError as exc:
        raise PromotionError("P341 private workspace is unavailable") from exc
    import tempfile

    with tempfile.TemporaryDirectory(prefix=".p341-ready-", dir=private_root) as name:
        temporary = Path(name)
        staged_value = json.loads(json.dumps(value))
        if promotion_payloads is not None:
            staged_root = temporary / "promotion"
            publish_promotion(staged_root, promotion_payloads)
            for key, filename in {
                "candidate_static": "candidate-static.json",
                "run_manifest": "run-manifest.json",
                "static_check": "static-check-result.json",
            }.items():
                staged_value["observation"]["acceptance"]["contract"][key]["path"] = relative(
                    staged_root / filename
                )
        path = temporary / "manifest.json"
        path.write_bytes(manifest_bytes(staged_value))
        try:
            core.verify_bundle(ROOT, path)
        except (core.F1V2Error, core.F1TransportError, OSError) as exc:
            raise PromotionError(str(exc)) from exc


def _write_exclusive(path: Path, payload: bytes, mode: int) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        mode,
    )
    try:
        offset = 0
        while offset < len(payload):
            count = os.write(descriptor, payload[offset:])
            if count <= 0:
                raise PromotionError("P341 publication was short")
            offset += count
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_promotion(output: Path, payloads: dict[str, bytes]) -> None:
    direct = output.absolute()
    if direct.exists() or direct.is_symlink():
        raise PromotionError("P341 promotion output already exists")
    direct.mkdir(mode=0o700, parents=True)
    direct.chmod(0o700)
    for name, filename in {
        "candidate_static": "candidate-static.json",
        "run_manifest": "run-manifest.json",
        "static_check": "static-check-result.json",
    }.items():
        _write_exclusive(direct / filename, payloads[name], 0o400)
    descriptor = os.open(direct, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_manifest(path: Path, payload: bytes) -> None:
    direct = path.absolute()
    if direct.exists() or direct.is_symlink():
        raise PromotionError("P341 ready manifest already exists")
    direct.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _write_exclusive(direct, payload, 0o640)
    descriptor = os.open(direct.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def build(
    *,
    static_path: Path = DEFAULT_STATIC_OUTPUT,
    candidate_ap_path: Path = DEFAULT_CANDIDATE_AP,
    rollback_path: Path = DEFAULT_ROLLBACK_AP,
    promotion_root: Path = DEFAULT_PROMOTION,
    target_profile: Path = DEFAULT_TARGET_PROFILE,
    manifest_id: str = DEFAULT_MANIFEST_ID,
    live_run_id: str = DEFAULT_LIVE_RUN_ID,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
) -> tuple[dict[str, Any], dict[str, bytes], dict[str, Any]]:
    static_value, static_payload, _builder, _builder_payload, ap_receipt = _candidate_inputs(
        static_path, candidate_ap_path
    )
    payloads = _promotion_payloads(static_value, static_payload, ap_receipt)
    candidate_ap = {
        "path": relative(candidate_ap_path),
        **{key: ap_receipt[key] for key in ("size", "sha256", "member")},
    }
    rollback_payload = stable_bytes(rollback_path, "P341 exact rollback AP", 64 * 1024 * 1024)
    rollback_ap = {"path": relative(rollback_path), **identity(rollback_payload)}
    if {key: rollback_ap[key] for key in ("size", "sha256")} != ROLLBACK_IDENTITY:
        raise PromotionError("P341 rollback identity differs")
    acceptance = _acceptance(payloads, promotion_root)
    verification = _offline_verification(acceptance, payloads, ap_receipt)
    common_verified = verification.get("common_offline_verified") is True
    manifest = _manifest(
        promotion_root=promotion_root,
        payloads=payloads,
        candidate_ap=candidate_ap,
        rollback_ap=rollback_ap,
        target_profile=target_profile,
        manifest_id=manifest_id,
        live_run_id=live_run_id,
        timeout_sec=timeout_sec,
        common_verified=common_verified,
    )
    verify_manifest(
        manifest,
        manifest_bytes(manifest),
        promotion_payloads=payloads if common_verified else None,
    )
    return manifest, payloads, verification


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static", type=Path, default=DEFAULT_STATIC_OUTPUT)
    parser.add_argument("--candidate-ap", type=Path, default=DEFAULT_CANDIDATE_AP)
    parser.add_argument("--rollback-ap", type=Path, default=DEFAULT_ROLLBACK_AP)
    parser.add_argument("--promotion", type=Path, default=DEFAULT_PROMOTION)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="publish private P341 promotion/manifest only after common verification",
    )
    args = parser.parse_args(argv)
    paths = {
        name: value if value.is_absolute() else ROOT / value
        for name, value in {
            "static": args.static,
            "candidate": args.candidate_ap,
            "rollback": args.rollback_ap,
            "promotion": args.promotion,
            "manifest": args.manifest,
        }.items()
    }
    try:
        manifest, payloads, verification = build(
            static_path=paths["static"],
            candidate_ap_path=paths["candidate"],
            rollback_path=paths["rollback"],
            promotion_root=paths["promotion"],
            target_profile=DEFAULT_TARGET_PROFILE,
            manifest_id=DEFAULT_MANIFEST_ID,
            live_run_id=DEFAULT_LIVE_RUN_ID,
            timeout_sec=DEFAULT_TIMEOUT_SEC,
        )
        if args.publish:
            if verification.get("common_offline_verified") is not True:
                raise PromotionError("P341 common verification is pending; publication refused")
            publish_promotion(paths["promotion"], payloads)
            publish_manifest(paths["manifest"], manifest_bytes(manifest))
        elif args.audit_only and (paths["promotion"].exists() or paths["manifest"].exists()):
            raise PromotionError("P341 audit-only refuses existing publication paths")
    except (OSError, RuntimeError, PromotionError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "verdict": VERDICT
                if verification.get("common_offline_verified")
                else REHEARSAL_VERDICT,
                "manifest": identity(manifest_bytes(manifest)),
                "payloads": {name: identity(value) for name, value in payloads.items()},
                "common_offline_verified": verification.get("common_offline_verified", False),
                "published": bool(args.publish),
                "device_contact": False,
                "live_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


__all__ = [name for name in globals() if not name.startswith("_")]


if __name__ == "__main__":
    raise SystemExit(main())

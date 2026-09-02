#!/usr/bin/env python3
"""Prepare the P3.28 authenticated-exec F1 bundle (host-only).

This is the P3.28-specific promotion seam.  It reopens the already-built
boot-only AP, the P3.28 candidate-static closure, and the exact stock
rollback, then verifies the three immutable Process-v2 contract artifacts in
a temporary private directory.  It does not contact a device, invoke Odin,
create an F1 journal, or publish approval authority during rehearsal.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for _directory in (ANALYSIS, REVALIDATION):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as core  # noqa: E402
import s22plus_boot_verify as boot_verify  # noqa: E402
import s22plus_fyg8_p328_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p328_auth_acm_observer as framed_observer  # noqa: E402
import s22plus_fyg8_p328_auth_exec_runtime as framed_runtime  # noqa: E402
import s22plus_fyg8_p328_process_v2_candidate_static as candidate_static  # noqa: E402
import s22plus_fyg8_p328_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p328_stock_process_v2_adapter as adapter  # noqa: E402


SCHEMA = "s22plus_fyg8_p328_process_v2_promotion_v1"
VERDICT = "PASS_P328_PROCESS_V2_PROMOTION_HOST_ONLY"
READY_SCHEMA = "s22plus_fyg8_p328_ready_manifest_builder_v1"
READY_VERDICT = "PASS_P328_PROCESS_V2_READY_MANIFEST_HOST_ONLY"
REHEARSAL_VERDICT = "PASS_P328_PROCESS_V2_READY_MANIFEST_REHEARSAL_HOST_ONLY"
DEFAULT_BUILDER_OUTPUT = candidate_build.DEFAULT_OUTPUT_ROOT
DEFAULT_STATIC_OUTPUT = candidate_static.DEFAULT_OUTPUT
DEFAULT_CANDIDATE_AP = DEFAULT_BUILDER_OUTPUT / "candidate-a/odin4/AP.tar.md5"
DEFAULT_ROLLBACK_AP = ROOT / (
    "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
)
DEFAULT_PROMOTION = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p328/"
    "process-v2-promotion-20260902-01"
)
DEFAULT_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p328_process_v2_ready_1.json"
)
DEFAULT_TARGET_PROFILE = ROOT / (
    "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
)
DEFAULT_MANIFEST_ID = "s22plus-fyg8-p328-process-v2-ready-1"
DEFAULT_LIVE_RUN_ID = "s22plus-fyg8-p328-live-1"
DEFAULT_TIMEOUT_SEC = 300
ROLLBACK_IDENTITY = dict(candidate_static.ROLLBACK_IDENTITY)
TARGET = dict(candidate_static.TARGET)
PRIVATE_PARENT = ROOT / "workspace/private/outputs/s22plus_fyg8_p328"
AUTH_KEY_IDENTITY = dict(candidate_static.P328_KEY_IDENTITY)


class PromotionError(ValueError):
    """The P3.28 promotion closure or manifest is not valid."""


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
        raise PromotionError("P3.28 promotion value is not canonical JSON") from exc


def manifest_bytes(value: dict[str, Any]) -> bytes:
    try:
        return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(
            "ascii"
        )
    except (TypeError, ValueError, UnicodeError) as exc:
        raise PromotionError("P3.28 ready manifest is not canonical JSON") from exc


def relative(path: Path) -> str:
    direct = path.resolve(strict=False)
    try:
        return direct.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise PromotionError("P3.28 path escaped the repository") from exc


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
    nlink: int | None = None,
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
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or len(payload) > maximum
        or (expected is not None and identity(payload) != expected)
        or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
        or (nlink is not None and before.st_nlink != nlink)
    ):
        raise PromotionError(f"{label} identity differs")
    return payload


def decode(payload: bytes, label: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise PromotionError(f"{label} has a duplicate key")
            value[key] = item
        return value

    try:
        value = json.loads(payload.decode("ascii"), object_pairs_hook=pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PromotionError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise PromotionError(f"{label} is not an object")
    return value


def _candidate_inputs(
    static_path: Path,
    candidate_ap_path: Path,
) -> tuple[dict[str, Any], bytes, dict[str, Any], bytes, dict[str, Any]]:
    """Load a published static receipt, or derive one in memory for rehearsal.

    The fallback is deliberately not a publication path: candidate-static
    itself performs the same exact reopen of the final builder, AP, runtime,
    source closure, and key identity.  This keeps an audit-only rehearsal
    useful before a static receipt has been selected for promotion.
    """
    try:
        static_lstat = static_path.absolute().lstat()
    except FileNotFoundError:
        static_lstat = None
    except OSError as exc:
        raise PromotionError("P3.28 candidate-static path is unavailable") from exc
    if static_lstat is None:
        static_value = candidate_static.build_result()
        static_payload = candidate_static.canonical(static_value)
    else:
        static_payload = stable_bytes(
            static_path,
            "P3.28 candidate-static",
            2 * 1024 * 1024,
            mode=0o400,
            nlink=1,
        )
        static_value = decode(static_payload, "P3.28 candidate-static")
        if static_payload != candidate_static.canonical(static_value):
            raise PromotionError("P3.28 candidate-static bytes are not canonical")
        try:
            candidate_static.validate_result(static_value)
        except Exception as exc:
            raise PromotionError("P3.28 candidate-static did not reopen") from exc

    builder_path = DEFAULT_BUILDER_OUTPUT / "result.json"
    builder_payload = stable_bytes(
        builder_path,
        "P3.28 builder result",
        4 * 1024 * 1024,
        mode=0o400,
        nlink=1,
    )
    builder_value = decode(builder_payload, "P3.28 builder result")
    try:
        audited = candidate_build.audit_existing(
            DEFAULT_BUILDER_OUTPUT,
            auth_key=artifact.DEFAULT_AUTH_KEY_PATH,
        )
    except Exception as exc:
        raise PromotionError("P3.28 builder result did not reopen") from exc
    if audited != builder_value:
        raise PromotionError("P3.28 builder result changed")
    builder_identity = identity(builder_payload)
    if (
        not isinstance(static_value.get("builder_result"), dict)
        or {
            key: static_value["builder_result"].get(key)
            for key in ("size", "sha256")
        }
        != builder_identity
    ):
        raise PromotionError("P3.28 static receipt does not bind builder result")

    ap_payload = stable_bytes(
        candidate_ap_path, "P3.28 candidate AP", 64 * 1024 * 1024
    )
    try:
        ap_info, frame = boot_verify.parse_ap_tar_md5(ap_payload)
    except boot_verify.BootVerifyError as exc:
        raise PromotionError("P3.28 candidate AP is invalid") from exc
    if ap_info["member"]["name"] != "boot.img.lz4":
        raise PromotionError("P3.28 candidate AP is not boot-only")
    ap_receipt = {
        **identity(ap_payload),
        "member": {"name": "boot.img.lz4", **identity(frame)},
    }
    candidate = static_value.get("candidate")
    if (
        not isinstance(candidate, dict)
        or not isinstance(candidate.get("a"), dict)
        or candidate["a"].get("ap_tar_md5")
        != {key: ap_receipt[key] for key in ("size", "sha256")}
    ):
        raise PromotionError("P3.28 candidate-static AP identity differs")
    return static_value, static_payload, builder_value, builder_payload, ap_receipt


def _promotion_payloads(
    static_value: dict[str, Any],
    static_payload: bytes,
    ap_receipt: dict[str, Any],
) -> dict[str, bytes]:
    candidate = static_value.get("candidate")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("a"), dict):
        raise PromotionError("P3.28 candidate package is incomplete")
    authentication = static_value.get("authentication")
    if authentication != {
        "required": True,
        "scheme": "auth-key-v1",
        "key": AUTH_KEY_IDENTITY,
        "embedded_key_occurrences_in_init": 1,
        "hardware_backed": False,
        "candidate_possession_implies_key_possession": True,
        "path_published": False,
    }:
        raise PromotionError("P3.28 authentication receipt differs")

    static_identity = identity(static_payload)
    records = {
        "long_family_hex": adapter.LONG_FAMILY.hex(),
        "unsat_family_hex": adapter.UNSAT_FAMILY.hex(),
        "terminal_stage": adapter.TERMINAL_STAGE,
    }
    observation = {
        "accepted_identity": "P328_STOCK_OBSERVER_V4_RETAINED",
        "minimum_success_count": 1,
        "clean_baseline_required": True,
        "runtime_values_preflighted": False,
        "complete_is_noncausal": True,
        "incomplete_result": "NO_PROOF_EXPERIMENT_PRECONDITION",
        "receipt_result": "NO_PROOF_OBSERVER",
    }
    run_manifest = {
        "schema": evidence.P328_RUN_MANIFEST_SCHEMA,
        "target": evidence.PID1_USERSPACE_TARGET,
        "profile": adapter.PROFILE,
        "run_id": adapter.P328_RUN_ID_HEX,
        "decoder": adapter.DECODER_ID,
        "policy_id": adapter.POLICY_ID,
        "records": records,
        "observation_contract": observation,
        "candidate_ap": {
            key: ap_receipt[key] for key in ("size", "sha256")
        },
        "candidate_static": static_identity,
        "source_contract_id": adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": adapter.OVERLAY_CONTRACT_ID,
    }
    run_payload = canonical(run_manifest)
    static_result = {
        "schema": evidence.P328_STATIC_RESULT_SCHEMA,
        "target": evidence.PID1_USERSPACE_TARGET,
        "verdict": evidence.P328_STATIC_RESULT_VERDICT,
        "profile": adapter.PROFILE,
        "run_id": adapter.P328_RUN_ID_HEX,
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
                "candidate_static": static_identity,
                "boot_image": candidate["a"]["boot_img"],
                "boot_img_lz4": candidate["a"]["boot_img_lz4"],
                "image": candidate["image"],
                "init": candidate["init"],
                "child": candidate["child"],
                "busybox": candidate["busybox"],
                "latch": evidence.P319_EXACT_ARTIFACTS["latch"],
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
        "static_check": canonical(static_result),
    }


def _acceptance(output: Path, payloads: dict[str, bytes]) -> dict[str, Any]:
    names = {
        "candidate_static": "candidate-static.json",
        "run_manifest": "run-manifest.json",
        "static_check": "static-check-result.json",
    }
    item = adapter.acceptance_fixture()
    item["contract"] = {
        name: {"path": relative(output / filename), **identity(payloads[name])}
        for name, filename in names.items()
    }
    # Bind the fixed key by public identity only.  The private key bytes and
    # its path remain available solely to the live P3.28 implementation.
    item["auth_key"] = dict(AUTH_KEY_IDENTITY)
    try:
        evidence.validate_acceptance(item)
    except evidence.EvidenceError as exc:
        raise PromotionError(str(exc)) from exc
    return item


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
                raise PromotionError("P3.28 publication was short")
            offset += count
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_promotion(output: Path, payloads: dict[str, bytes]) -> None:
    direct = output.absolute()
    if direct.exists() or direct.is_symlink():
        raise PromotionError("P3.28 promotion output already exists")
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


def _observer_spec() -> dict[str, Any]:
    try:
        value = evidence.p328_authenticated_framed_observer_spec()
    except AttributeError:
        value = {
            "kind": "exact_cdc_acm_authenticated_framed_commands_v1",
            "usb_vendor_id": "04e8",
            "usb_product_id": "6861",
            "usb_serial": "S22E3" + adapter.P328_RUN_ID_HEX,
            "usb_driver": "cdc_acm",
            "usb_interface_number": "00",
            "banner_hex": (
                "S22PLUS-FYG8-E3:" + adapter.P328_RUN_ID_HEX + "\n"
            ).encode("ascii").hex(),
            "protocol_contract": framed_observer.CONTRACT_ID,
            "wire_magic": framed_runtime.FRAME_MAGIC.decode("ascii"),
            "frame_header_size": framed_runtime.FRAME_HEADER_SIZE,
            "max_frame_payload": framed_runtime.MAX_FRAME_PAYLOAD,
            "max_commands": framed_runtime.MAX_COMMANDS,
            "command_timeout_sec": framed_runtime.COMMAND_TIMEOUT_SEC,
            "max_output_bytes": framed_runtime.MAX_OUTPUT_BYTES,
            "auth_algorithm": "hmac-sha256",
            "auth_tag_size": framed_runtime.AUTH_TAG_SIZE,
            "auth_key_schema": artifact.AUTH_KEY_SCHEMA,
            "auth_key_size": artifact.AUTH_KEY_SIZE,
            "auth_key": AUTH_KEY_IDENTITY,
            "auth_key_path_published": False,
            "authentication_required": True,
            "per_session_random_nonce": True,
            "proof_command_count": len(framed_observer.DEFAULT_COMMANDS),
            "commands": [
                {"size": len(command), "sha256": hashlib.sha256(command).hexdigest()}
                for command in framed_observer.DEFAULT_COMMANDS
            ],
            "caller_selected_command": True,
            "interactive_pty": False,
            "raw_rx_forwarded_before_classification": True,
            "host_only": True,
            "device_contact": False,
        }
    if value.get("auth_key") != AUTH_KEY_IDENTITY:
        raise PromotionError("P3.28 observer key identity differs")
    encoded = json.dumps(value, sort_keys=True)
    if "auth-key-v1.bin" in encoded or "workspace/private/inputs" in encoded:
        raise PromotionError("P3.28 observer spec exposes a key path")
    return value


def derive_manifest(
    *,
    promotion_root: Path,
    payloads: dict[str, bytes],
    candidate_ap: dict[str, Any],
    rollback_ap: dict[str, Any],
    target_profile: Path,
    manifest_id: str,
    live_run_id: str,
    timeout_sec: int,
) -> dict[str, Any]:
    run_manifest = decode(payloads["run_manifest"], "P3.28 run manifest")
    expected = {
        "source_contract_id": adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": adapter.OVERLAY_CONTRACT_ID,
        "profile": adapter.PROFILE,
        "run_id": adapter.P328_RUN_ID_HEX,
        "candidate_ap": {
            key: candidate_ap[key] for key in ("size", "sha256")
        },
        "candidate_static": identity(payloads["candidate_static"]),
    }
    if any(run_manifest.get(key) != value for key, value in expected.items()):
        raise PromotionError("P3.28 promotion run manifest differs")
    if type(timeout_sec) is not int or not 1 <= timeout_sec <= 600:
        raise PromotionError("P3.28 observation timeout is invalid")
    acceptance = _acceptance(promotion_root, payloads)
    observer = _observer_spec()
    return {
        "schema": core.MANIFEST_SCHEMA,
        "manifest_id": manifest_id,
        "run_id": live_run_id,
        "status": "ready-for-f1-approval",
        "target_profile": relative(target_profile),
        "candidate_ap": {
            key: candidate_ap[key] for key in ("path", "size", "sha256")
        },
        "rollback_ap": rollback_ap,
        "allowed_member": "boot.img.lz4",
        "observation": {
            "timeout_sec": timeout_sec,
            "acceptance": acceptance,
            "candidate_observer": observer,
            evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY: (
                evidence.CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE
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
        raise PromotionError("P3.28 ready manifest bytes differ")
    private_root = ROOT / "workspace/private"
    try:
        private_root.lstat()
    except OSError as exc:
        raise PromotionError("P3.28 private workspace is unavailable") from exc
    with tempfile.TemporaryDirectory(prefix=".p328-ready-", dir=private_root) as name:
        temporary = Path(name)
        staged_value = value
        if promotion_payloads is not None:
            staged_root = temporary / "promotion"
            publish_promotion(staged_root, promotion_payloads)
            staged_value = json.loads(json.dumps(value))
            for key, filename in {
                "candidate_static": "candidate-static.json",
                "run_manifest": "run-manifest.json",
                "static_check": "static-check-result.json",
            }.items():
                staged_value["observation"]["acceptance"]["contract"][key][
                    "path"
                ] = relative(staged_root / filename)
        path = temporary / "manifest.json"
        path.write_bytes(manifest_bytes(staged_value))
        try:
            core.verify_bundle(ROOT, path)
        except (core.F1V2Error, core.F1TransportError, OSError) as exc:
            raise PromotionError(str(exc)) from exc


def publish_manifest(path: Path, payload: bytes) -> None:
    direct = path.absolute()
    if direct.exists() or direct.is_symlink():
        raise PromotionError("P3.28 ready manifest already exists")
    direct.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    _write_exclusive(direct, payload, 0o644)
    descriptor = os.open(
        direct.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    )
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
    (
        static_value,
        static_payload,
        _builder_value,
        _builder_payload,
        ap_receipt,
    ) = _candidate_inputs(static_path, candidate_ap_path)
    payloads = _promotion_payloads(static_value, static_payload, ap_receipt)
    candidate_ap = {
        "path": relative(candidate_ap_path),
        **{key: ap_receipt[key] for key in ("size", "sha256", "member")},
    }
    rollback_payload = stable_bytes(
        rollback_path, "P3.28 exact rollback AP", 64 * 1024 * 1024
    )
    rollback_ap = {"path": relative(rollback_path), **identity(rollback_payload)}
    if {key: rollback_ap[key] for key in ("size", "sha256")} != ROLLBACK_IDENTITY:
        raise PromotionError("P3.28 rollback identity differs")
    acceptance = _acceptance(promotion_root, payloads)
    try:
        verification = evidence.verify_offline_contract(
            acceptance,
            payloads=payloads,
            receipts={name: identity(value) for name, value in payloads.items()},
            candidate_ap=ap_receipt,
        )
        frame = boot_verify.parse_ap_tar_md5(
            stable_bytes(
                candidate_ap_path,
                "P3.28 candidate AP recheck",
                64 * 1024 * 1024,
            )
        )[1]
        evidence.validate_e2_ap_payload(frame, verification["ap_payload_closure"])
    except (evidence.EvidenceError, boot_verify.BootVerifyError) as exc:
        raise PromotionError(str(exc)) from exc
    manifest = derive_manifest(
        promotion_root=promotion_root,
        payloads=payloads,
        candidate_ap=candidate_ap,
        rollback_ap=rollback_ap,
        target_profile=target_profile,
        manifest_id=manifest_id,
        live_run_id=live_run_id,
        timeout_sec=timeout_sec,
    )
    payload = manifest_bytes(manifest)
    verify_manifest(manifest, payload, promotion_payloads=payloads)
    return manifest, payloads, verification


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static", type=Path, default=DEFAULT_STATIC_OUTPUT)
    parser.add_argument("--candidate-ap", type=Path, default=DEFAULT_CANDIDATE_AP)
    parser.add_argument("--rollback-ap", type=Path, default=DEFAULT_ROLLBACK_AP)
    parser.add_argument("--promotion", type=Path, default=DEFAULT_PROMOTION)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--audit-only", action="store_true")
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
        )
        if not args.audit_only:
            publish_promotion(paths["promotion"], payloads)
            verify_manifest(manifest, manifest_bytes(manifest))
            publish_manifest(paths["manifest"], manifest_bytes(manifest))
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "verdict": VERDICT,
                    "ready_schema": READY_SCHEMA,
                    "ready_verdict": (
                        REHEARSAL_VERDICT if args.audit_only else READY_VERDICT
                    ),
                    "promotion": str(paths["promotion"]),
                    "manifest": str(paths["manifest"]),
                    "manifest_id": manifest["manifest_id"],
                    "run_id": adapter.P328_RUN_ID_HEX,
                    "verification": verification.get("verified") is True,
                    "created": not args.audit_only,
                    "run_directory_created": False,
                    "device_contact": False,
                    "odin_invoked": False,
                    "live_authorized": False,
                },
                sort_keys=True,
            )
        )
        return 0
    except (OSError, PromotionError, RuntimeError) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)},
                sort_keys=True,
            )
        )
        return 1


__all__ = [
    "AUTH_KEY_IDENTITY",
    "DEFAULT_BUILDER_OUTPUT",
    "DEFAULT_CANDIDATE_AP",
    "DEFAULT_MANIFEST",
    "DEFAULT_MANIFEST_ID",
    "DEFAULT_PROMOTION",
    "DEFAULT_ROLLBACK_AP",
    "DEFAULT_STATIC_OUTPUT",
    "DEFAULT_TARGET_PROFILE",
    "DEFAULT_TIMEOUT_SEC",
    "DEFAULT_LIVE_RUN_ID",
    "PRIVATE_PARENT",
    "PromotionError",
    "READY_SCHEMA",
    "READY_VERDICT",
    "REHEARSAL_VERDICT",
    "ROLLBACK_IDENTITY",
    "SCHEMA",
    "TARGET",
    "adapter",
    "build",
    "canonical",
    "decode",
    "derive_manifest",
    "evidence",
    "identity",
    "main",
    "manifest_bytes",
    "publish_manifest",
    "publish_promotion",
    "relative",
    "stable_bytes",
    "verify_manifest",
]


if __name__ == "__main__":
    raise SystemExit(main())

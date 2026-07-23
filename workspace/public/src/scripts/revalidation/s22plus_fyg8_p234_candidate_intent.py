#!/usr/bin/env python3
"""Create one candidate-bound FYG8 E1 identity and exact kernel patch."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p233_e1_decoder as decoder  # noqa: E402
import s22plus_fyg8_p233_e1_static_checker as p233  # noqa: E402
import s22plus_fyg8_p241_e2_static_checker as p241  # noqa: E402
import s22plus_fyg8_p245_source_contract as p245  # noqa: E402
import s22plus_fyg8_r4w1b_patch_check as source_base  # noqa: E402


SCHEMA = "s22plus_fyg8_p234_candidate_intent_v1"
PREIMAGE_SCHEMA = "s22plus_fyg8_p234_candidate_identity_preimage_v1"
VERDICT = "PASS_P234_CANDIDATE_INTENT_HOST_ONLY"
TARGET = p233.TARGET
PROFILE = "E1A"
PROFILE_NUMBER = decoder.model.PROFILE_NUMBERS[PROFILE]
RUN_ID_DOMAIN = b"S22PLUS-FYG8-P234-E1A-RUN-ID-V1\0"
SUPPORTED_PROFILES = ("E1A", "E1B", "E2")
RUN_ID_DOMAINS = {
    "E1A": RUN_ID_DOMAIN,
    "E1B": b"S22PLUS-FYG8-P239-E1B-RUN-ID-V1\0",
    "E2": b"S22PLUS-FYG8-P242-E2-RUN-ID-V1\0",
}
DEFAULT_SOURCE = p233.DEFAULT_SOURCE
DEFAULT_BASE_PATCH = p233.DEFAULT_PATCH
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p234/intent")
DEFCONFIG = "kernel_platform/common/arch/arm64/configs/gki_defconfig"
BASE_FILES = dict(source_base.BASE_FILES)

SOURCE_PATHS = {
    "base_patch": p233.DEFAULT_PATCH,
    "checkpoint_client": p233.DEFAULT_CLIENT,
    "runtime_wrapper": p233.DEFAULT_RUNTIME,
    "legacy_runtime": p233.DEFAULT_LEGACY_RUNTIME,
    "legacy_header": p233.DEFAULT_HEADER,
    "child": p233.DEFAULT_CHILD,
    "decoder": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p233_e1_decoder.py"
    ),
    "design_model": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p232_e1_latest_stage_design.py"
    ),
    "source_checker": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p233_e1_static_checker.py"
    ),
}
E2_SOURCE_PATHS = {
    "base_patch": p241.DEFAULT_PATCH,
    "checkpoint_client": p241.DEFAULT_CLIENT,
    "runtime_wrapper": p241.DEFAULT_RUNTIME,
    "plan_header": p241.DEFAULT_PLAN_HEADER,
    "loader_core": Path(
        "workspace/public/src/native-init/s22plus_o2_loader_core.h"
    ),
    "legacy_runtime": p233.DEFAULT_LEGACY_RUNTIME,
    "legacy_header": p233.DEFAULT_HEADER,
    "child": p241.DEFAULT_CHILD,
    "decoder": SOURCE_PATHS["decoder"],
    "design_model": SOURCE_PATHS["design_model"],
    "source_checker": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p241_e2_static_checker.py"
    ),
    "planner": Path(
        "workspace/public/src/scripts/revalidation/s22plus_o2_module_plan.py"
    ),
    "dtbo_contract": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p241_dtbo_role_contract.py"
    ),
    "stock_closure": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p242_e2_stock_closure.py"
    ),
}


class IntentError(ValueError):
    pass


def repo_root() -> Path:
    return p233.repo_root()


def resolve(root: Path, path: Path) -> Path:
    return p233.resolve(root, path)


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def parse_nonce(value: str | None) -> bytes:
    if value is None:
        return secrets.token_bytes(16)
    if re.fullmatch(r"[0-9a-f]{32}", value) is None:
        raise IntentError("--nonce-hex must be exactly 32 lowercase hex digits")
    nonce = bytes.fromhex(value)
    if not any(nonce):
        raise IntentError("candidate nonce must be nonzero")
    return nonce


def source_paths_for_profile(profile: str) -> dict[str, Path]:
    profile_number(profile)
    return E2_SOURCE_PATHS if profile == "E2" else SOURCE_PATHS


def source_receipts(
    root: Path,
    profile: str = PROFILE,
    source_contract_id: str | None = None,
) -> tuple[dict[str, bytes], dict[str, Any]]:
    if source_contract_id is not None:
        p245.require(source_contract_id, profile)
        return p245.source_receipts(root)
    data: dict[str, bytes] = {}
    rows: dict[str, Any] = {}
    for name, relative in source_paths_for_profile(profile).items():
        value = p233.read_direct(resolve(root, relative), name)
        data[name] = value
        rows[name] = receipt(value)
    return data, rows


def profile_number(profile: str) -> int:
    if profile not in SUPPORTED_PROFILES:
        raise IntentError(f"unsupported candidate profile: {profile}")
    return decoder.model.PROFILE_NUMBERS[profile]


def decoder_for(profile: str, source_contract_id: str | None = None):
    profile_number(profile)
    if source_contract_id is None:
        return decoder
    p245.require(source_contract_id, profile)
    return p245.decoder


def source_check_run_id(
    profile: str, source_contract_id: str | None = None
) -> bytes:
    profile_number(profile)
    if source_contract_id is not None:
        p245.require(source_contract_id, profile)
        return p245.p244_checker.RUN_ID
    if profile == "E2":
        return p241.RUN_ID
    return p233.SOURCE_CHECK_RUN_IDS[profile]


def identity_preimage(
    nonce: bytes,
    sources: dict[str, Any],
    profile: str = PROFILE,
    source_contract_id: str | None = None,
) -> dict[str, Any]:
    selected_decoder = decoder_for(profile, source_contract_id)
    result = {
        "schema": PREIMAGE_SCHEMA,
        "target": TARGET,
        "profile": profile,
        "profile_number": profile_number(profile),
        "nonce": nonce.hex(),
        "decoder_id": selected_decoder.DECODER_ID,
        "decoder_policy_id": selected_decoder.POLICY_ID,
        "record_layout": "S22E1L1-45-ab-crc32",
        "sources": sources,
    }
    if source_contract_id is not None:
        p245.require(source_contract_id, profile)
        result["schema"] = p245.PREIMAGE_SCHEMA
        result["source_contract_id"] = source_contract_id
    return result


def derive_run_id(preimage: dict[str, Any]) -> bytes:
    profile = preimage.get("profile")
    if not isinstance(profile, str) or preimage.get("profile_number") != profile_number(
        profile
    ):
        raise IntentError("candidate preimage profile binding is invalid")
    source_contract_id = preimage.get("source_contract_id")
    domain = RUN_ID_DOMAINS[profile]
    if source_contract_id is not None:
        domain = p245.require(source_contract_id, profile).run_id_domain
    run_id = hashlib.sha256(domain + canonical(preimage)).digest()[:16]
    rejected = {
        bytes(16),
        *(decoder.model.model_run_id(name) for name in SUPPORTED_PROFILES),
        *p233.SOURCE_CHECK_RUN_IDS.values(),
        p241.RUN_ID,
    }
    if run_id in rejected:
        raise IntentError("derived run ID collides with a forbidden identity")
    return run_id


def defconfig_patch(
    run_id: bytes, unsat_tag: bytes, profile: str = PROFILE
) -> bytes:
    lines = (
        "CONFIG_S22PLUS_FYG8_E1_LATEST_STAGE=y",
        f"CONFIG_S22PLUS_FYG8_E1_PROFILE={profile_number(profile)}",
        f'CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="{run_id.hex()}"',
        f'CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX="{unsat_tag.hex()}"',
    )
    body = "\n".join(f"+{line}" for line in lines)
    return (
        "diff --git a/kernel_platform/common/arch/arm64/configs/gki_defconfig "
        "b/kernel_platform/common/arch/arm64/configs/gki_defconfig\n"
        "--- a/kernel_platform/common/arch/arm64/configs/gki_defconfig\n"
        "+++ b/kernel_platform/common/arch/arm64/configs/gki_defconfig\n"
        "@@ -737,6 +737,10 @@ CONFIG_CRYPTO_FIPS=y\n"
        " \n"
        " \n"
        " # CONFIG_RKP_TEST is not set\n"
        f"{body}\n"
        " \n"
        " \n"
        " \n"
    ).encode("ascii")


def build_patch(
    base_patch: bytes, run_id: bytes, unsat_tag: bytes, profile: str = PROFILE
) -> bytes:
    if not base_patch.endswith(b"\n"):
        raise IntentError("P2.33 base patch lacks final newline")
    return defconfig_patch(run_id, unsat_tag, profile) + b"\n" + base_patch


def audit_patch(
    source: Path,
    patch: bytes,
    run_id: bytes,
    unsat_tag: bytes,
    profile: str = PROFILE,
) -> dict[str, Any]:
    if source.is_symlink() or not source.is_dir():
        raise IntentError("FYG8 source tree is missing or indirect")
    targets = re.findall(
        rb"^diff --git a/(\S+) b/\1$", patch, flags=re.MULTILINE
    )
    decoded_targets = [value.decode("ascii") for value in targets]
    if set(decoded_targets) != set(BASE_FILES) or len(decoded_targets) != 3:
        raise IntentError(f"candidate patch targets changed: {decoded_targets}")
    config_lines = [
        "CONFIG_S22PLUS_FYG8_E1_LATEST_STAGE=y",
        f"CONFIG_S22PLUS_FYG8_E1_PROFILE={profile_number(profile)}",
        f'CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="{run_id.hex()}"',
        f'CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX="{unsat_tag.hex()}"',
    ]
    text = patch.decode("ascii")
    if any(text.count(f"+{line}") != 1 for line in config_lines):
        raise IntentError("candidate config binding cardinality changed")

    with tempfile.TemporaryDirectory(prefix="s22-p234-intent-") as temporary:
        tree = Path(temporary)
        for relative, expected in BASE_FILES.items():
            source_path = source / relative
            data = p233.read_direct(source_path, f"base {relative}")
            if hashlib.sha256(data).hexdigest() != expected:
                raise IntentError(f"base source identity mismatch: {relative}")
            target = tree / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        completed = subprocess.run(
            ["patch", "--batch", "--forward", "-p1"],
            cwd=tree,
            input=patch,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=30,
        )
        if completed.returncode != 0:
            detail = completed.stdout.decode("utf-8", "replace")[-2000:]
            raise IntentError(f"candidate patch does not apply cleanly: {detail}")
        patched_files = {
            relative: hashlib.sha256((tree / relative).read_bytes()).hexdigest()
            for relative in sorted(BASE_FILES)
        }
    return {
        "targets": sorted(decoded_targets),
        "base_files": dict(sorted(BASE_FILES.items())),
        "patched_files": patched_files,
        "config_lines": config_lines,
        "clean_apply": True,
        "verified": True,
    }


def durable_write(path: Path, data: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o400,
    )
    try:
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                raise IntentError(f"short write: {path}")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def create(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    output = resolve(root, args.out)
    if output.exists() or output.is_symlink():
        raise IntentError(f"output already exists: {output}")
    source = resolve(root, args.source)
    profile = getattr(args, "profile", PROFILE)
    source_contract_id = getattr(args, "source_contract_id", None)
    source_data, source_rows = source_receipts(
        root, profile, source_contract_id
    )
    nonce = parse_nonce(args.nonce_hex)
    number = profile_number(profile)
    preimage = identity_preimage(
        nonce, source_rows, profile, source_contract_id
    )
    run_id = derive_run_id(preimage)
    selected_decoder = decoder_for(profile, source_contract_id)
    unsat = selected_decoder.model.unsat_record(profile, run_id)
    unsat_tag = unsat[len(selected_decoder.model.UNSAT_FAMILY) :]
    reachable = (
        p245.validate_reachable_records(run_id)
        if source_contract_id is not None
        else p233.validate_reachable_records({profile: run_id})
    )
    patch = build_patch(source_data["base_patch"], run_id, unsat_tag, profile)
    patch_audit = audit_patch(source, patch, run_id, unsat_tag, profile)
    result: dict[str, Any] = {
        "schema": p245.INTENT_SCHEMA if source_contract_id else SCHEMA,
        "target": TARGET,
        "verdict": p245.INTENT_VERDICT if source_contract_id else VERDICT,
        "profile": profile,
        "profile_number": number,
        "identity_preimage": preimage,
        "identity_preimage_sha256": hashlib.sha256(canonical(preimage)).hexdigest(),
        "run_id": run_id.hex(),
        "run_id_derivation": "sha256(domain || canonical(identity_preimage))[:16]",
        "unsat_record_hex": unsat.hex(),
        "unsat_tag_hex": unsat_tag.hex(),
        "patch": {**receipt(patch), **patch_audit},
        "reachable_record_contract": reachable,
        "safety": {
            "host_only": True,
            "kernel_built": False,
            "image_built": False,
            "candidate_created": False,
            "manifest_created": False,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        },
    }
    if source_contract_id is not None:
        result["source_contract_id"] = source_contract_id
        result["materialized_sources"] = {
            name: {
                "path": f"materialized-sources/{filename}",
                **receipt(source_data[name]),
            }
            for name, filename in sorted(p245.MATERIALIZED_FILENAMES.items())
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{output.name}.", dir=output.parent
    ) as temporary:
        staging = Path(temporary)
        durable_write(staging / "candidate.patch", patch)
        if source_contract_id is not None:
            materialized = staging / "materialized-sources"
            materialized.mkdir()
            for name, filename in p245.MATERIALIZED_FILENAMES.items():
                durable_write(materialized / filename, source_data[name])
        durable_write(
            staging / "candidate-intent.json",
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode(
                "ascii"
            )
            + b"\n",
        )
        os.replace(staging, output)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--base-patch", type=Path)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--nonce-hex")
    parser.add_argument("--profile", choices=SUPPORTED_PROFILES, default=PROFILE)
    parser.add_argument(
        "--source-contract-id",
        choices=(p245.CONTRACT_ID,),
    )
    args = parser.parse_args(argv)
    if args.source_contract_id is not None:
        p245.require(args.source_contract_id, args.profile)
    expected_patch = (
        source_paths_for_profile(args.profile)["base_patch"]
        if args.source_contract_id is None
        else None
    )
    if args.base_patch is not None and args.base_patch != expected_patch:
        raise IntentError("alternate base patch is not supported for this profile")
    return args


def main(argv: list[str] | None = None) -> int:
    try:
        result = create(parse_args(argv))
    except (
        IntentError,
        p245.SourceContractError,
        p233.CheckError,
        decoder.model.DesignError,
        OSError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    summary = {
        "schema": result["schema"],
        "verdict": result["verdict"],
        "run_id": result["run_id"],
        "patch_sha256": result["patch"]["sha256"],
    }
    if result.get("source_contract_id") is not None:
        summary["source_contract_id"] = result["source_contract_id"]
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

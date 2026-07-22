#!/usr/bin/env python3
"""Create one candidate-bound P2.34 E1A identity and exact kernel patch."""

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
import s22plus_fyg8_r4w1b_patch_check as source_base  # noqa: E402


SCHEMA = "s22plus_fyg8_p234_candidate_intent_v1"
PREIMAGE_SCHEMA = "s22plus_fyg8_p234_candidate_identity_preimage_v1"
VERDICT = "PASS_P234_CANDIDATE_INTENT_HOST_ONLY"
TARGET = p233.TARGET
PROFILE = "E1A"
PROFILE_NUMBER = decoder.model.PROFILE_NUMBERS[PROFILE]
RUN_ID_DOMAIN = b"S22PLUS-FYG8-P234-E1A-RUN-ID-V1\0"
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


def source_receipts(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    data: dict[str, bytes] = {}
    rows: dict[str, Any] = {}
    for name, relative in SOURCE_PATHS.items():
        value = p233.read_direct(resolve(root, relative), name)
        data[name] = value
        rows[name] = receipt(value)
    return data, rows


def identity_preimage(nonce: bytes, sources: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": PREIMAGE_SCHEMA,
        "target": TARGET,
        "profile": PROFILE,
        "profile_number": PROFILE_NUMBER,
        "nonce": nonce.hex(),
        "decoder_id": decoder.DECODER_ID,
        "decoder_policy_id": decoder.POLICY_ID,
        "record_layout": "S22E1L1-45-ab-crc32",
        "sources": sources,
    }


def derive_run_id(preimage: dict[str, Any]) -> bytes:
    run_id = hashlib.sha256(RUN_ID_DOMAIN + canonical(preimage)).digest()[:16]
    rejected = {
        bytes(16),
        decoder.model.model_run_id(PROFILE),
        *p233.SOURCE_CHECK_RUN_IDS.values(),
    }
    if run_id in rejected:
        raise IntentError("derived run ID collides with a forbidden identity")
    return run_id


def defconfig_patch(run_id: bytes, unsat_tag: bytes) -> bytes:
    lines = (
        "CONFIG_S22PLUS_FYG8_E1_LATEST_STAGE=y",
        f"CONFIG_S22PLUS_FYG8_E1_PROFILE={PROFILE_NUMBER}",
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


def build_patch(base_patch: bytes, run_id: bytes, unsat_tag: bytes) -> bytes:
    if not base_patch.endswith(b"\n"):
        raise IntentError("P2.33 base patch lacks final newline")
    return defconfig_patch(run_id, unsat_tag) + b"\n" + base_patch


def audit_patch(
    source: Path, patch: bytes, run_id: bytes, unsat_tag: bytes
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
        f"CONFIG_S22PLUS_FYG8_E1_PROFILE={PROFILE_NUMBER}",
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
    source_data, source_rows = source_receipts(root)
    nonce = parse_nonce(args.nonce_hex)
    preimage = identity_preimage(nonce, source_rows)
    run_id = derive_run_id(preimage)
    unsat = decoder.model.unsat_record(PROFILE, run_id)
    unsat_tag = unsat[len(decoder.model.UNSAT_FAMILY) :]
    reachable = p233.validate_reachable_records({PROFILE: run_id})
    patch = build_patch(source_data["base_patch"], run_id, unsat_tag)
    patch_audit = audit_patch(source, patch, run_id, unsat_tag)
    result = {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": VERDICT,
        "profile": PROFILE,
        "profile_number": PROFILE_NUMBER,
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
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{output.name}.", dir=output.parent
    ) as temporary:
        staging = Path(temporary)
        durable_write(staging / "candidate.patch", patch)
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
    parser.add_argument("--base-patch", type=Path, default=DEFAULT_BASE_PATCH)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--nonce-hex")
    args = parser.parse_args(argv)
    if args.base_patch != DEFAULT_BASE_PATCH:
        raise IntentError("alternate base patch is not supported")
    return args


def main(argv: list[str] | None = None) -> int:
    try:
        result = create(parse_args(argv))
    except (IntentError, p233.CheckError, decoder.model.DesignError, OSError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "verdict": result["verdict"],
                "run_id": result["run_id"],
                "patch_sha256": result["patch"]["sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

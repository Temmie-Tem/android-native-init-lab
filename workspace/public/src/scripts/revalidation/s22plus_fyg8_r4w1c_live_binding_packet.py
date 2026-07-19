#!/usr/bin/env python3
"""Build the host-only R4W1-C connected-to-live binding packet.

This helper never contacts a device and never edits AGENTS.md.  Before the
connected run it checks source readiness.  After the canonical connected PASS
exists it reopens that evidence and emits the one exact rendered live clause
for independent review and a separate policy commit.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import s22plus_boot_only_live_core as core
import s22plus_fyg8_r4w1c_connected_gate as connected
import s22plus_fyg8_r4w1c_live_gate as live


SCHEMA = "s22plus_fyg8_r4w1c_live_binding_packet_v1"
SCRIPT_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1c_live_binding_packet.py"
)
TEST_RELATIVE = Path("tests/test_s22plus_fyg8_r4w1c_live_binding_packet.py")
OUTPUT_ROOT = Path("workspace/private/outputs")

# Updated only after the live source packet receives SOURCE GO.
EXPECTED_LIVE_HELPER_SIZE = 90_950
EXPECTED_LIVE_HELPER_SHA256 = (
    "65c137586b2decf160800f841b7243f3332108332043dbcaa548d7698e080c99"
)
EXPECTED_LIVE_TEST_SIZE = 64_948
EXPECTED_LIVE_TEST_SHA256 = (
    "c5966fb411983bed5b72e39400e8c8d15304ec0257e34e435ad5aae075ca1fbb"
)
EXPECTED_POLICY_TEMPLATE_SIZE = live.EXPECTED_POLICY_TEMPLATE_SIZE
EXPECTED_POLICY_TEMPLATE_SHA256 = live.EXPECTED_POLICY_TEMPLATE_SHA256
EXPECTED_CONNECTED_HELPER_SIZE = 54_734
EXPECTED_CONNECTED_TEST_SIZE = 32_764


class GateError(RuntimeError):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def require_identity(
    root: Path, relative: Path, *, size: int, digest: str, label: str
) -> dict[str, Any]:
    path = connected.require_direct_path(root, root / relative, label)
    identity = core.hash_stable_file(path)
    if identity != {"size": size, "sha256": digest}:
        raise GateError(f"{label} identity mismatch: {identity}")
    return {"path": str(relative), **identity}


def source_gate(root: Path) -> dict[str, Any]:
    identities = {
        "live_helper": require_identity(
            root,
            live.SCRIPT_RELATIVE,
            size=EXPECTED_LIVE_HELPER_SIZE,
            digest=EXPECTED_LIVE_HELPER_SHA256,
            label="R4W1-C live helper",
        ),
        "live_test": require_identity(
            root,
            live.TEST_RELATIVE,
            size=EXPECTED_LIVE_TEST_SIZE,
            digest=EXPECTED_LIVE_TEST_SHA256,
            label="R4W1-C live test",
        ),
        "policy_template": require_identity(
            root,
            live.POLICY_DRAFT,
            size=EXPECTED_POLICY_TEMPLATE_SIZE,
            digest=EXPECTED_POLICY_TEMPLATE_SHA256,
            label="R4W1-C live policy template",
        ),
        "connected_helper": require_identity(
            root,
            connected.SCRIPT_RELATIVE,
            size=EXPECTED_CONNECTED_HELPER_SIZE,
            digest=live.CONNECTED_HELPER_SHA256,
            label="R4W1-C connected helper",
        ),
        "connected_test": require_identity(
            root,
            connected.TEST_RELATIVE,
            size=EXPECTED_CONNECTED_TEST_SIZE,
            digest=live.CONNECTED_TEST_SHA256,
            label="R4W1-C connected test",
        ),
    }
    if not connected.policy_active(root):
        raise GateError("R4W1-C connected policy is not ACTIVE")
    if live.policy_active(root):
        raise GateError("R4W1-C live policy is already active")
    state_parent = connected.require_direct_path(
        root,
        root / live.CONSUMED_STATE.parent,
        "R4W1-C state directory",
        directory=True,
    )
    if state_parent != (root / live.CONSUMED_STATE.parent).resolve():
        raise GateError("R4W1-C state directory identity mismatch")
    if (root / live.CONSUMED_STATE).exists() or (root / live.CONSUMED_STATE).is_symlink():
        raise GateError("R4W1-C candidate exception is already consumed")
    return identities


def connected_binding(root: Path, artifacts: dict[str, Any]) -> dict[str, Any]:
    record = connected.validate_connected_pass(root, expected_artifacts=artifacts)
    pass_path = connected.require_direct_path(
        root, root / connected.PASS_STATE, "R4W1-C connected PASS"
    )
    result_path = connected.require_direct_path(
        root,
        root / Path(str(record["result_path"])),
        "R4W1-C connected result",
    )
    pass_identity = core.hash_stable_file(pass_path)
    result_identity = core.hash_stable_file(result_path)
    binding = {
        "pass_path": str(connected.PASS_STATE),
        "created_at_utc": record["created_at_utc"],
        "pass_size": pass_identity["size"],
        "pass_sha256": pass_identity["sha256"],
        "result_path": record["result_path"],
        "result_size": result_identity["size"],
        "result_sha256": result_identity["sha256"],
    }
    if (
        record.get("helper_sha256") != live.CONNECTED_HELPER_SHA256
        or record.get("test_sha256") != live.CONNECTED_TEST_SHA256
        or record.get("policy_clause_sha256") != live.CONNECTED_CLAUSE_SHA256
    ):
        raise GateError("R4W1-C connected PASS source binding mismatch")
    if (
        core.hash_stable_file(pass_path) != pass_identity
        or core.hash_stable_file(result_path) != result_identity
    ):
        raise GateError("R4W1-C connected evidence changed while binding")
    return binding


def durable_create_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise GateError(f"short write while creating {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def allocate_output(root: Path, requested: Path | None) -> Path:
    base = connected.require_direct_path(
        root, root / OUTPUT_ROOT, "R4W1-C output root", directory=True
    )
    relative = requested or OUTPUT_ROOT / f"s22plus-r4w1c-live-binding-{core.utc_stamp()}"
    candidate = relative if relative.is_absolute() else root / relative
    if candidate.is_symlink() or candidate.exists():
        raise GateError("R4W1-C binding output already exists or is indirect")
    resolved_parent = candidate.parent.resolve()
    if resolved_parent != base and base not in resolved_parent.parents:
        raise GateError("R4W1-C binding output escaped the private output root")
    candidate.mkdir(mode=0o700)
    return candidate.resolve()


def emit_packet(
    root: Path,
    output: Path,
    *,
    identities: dict[str, Any],
    artifacts: dict[str, Any],
    binding: dict[str, Any],
) -> dict[str, Any]:
    clause, template_identity = live.render_policy_clause(root, binding)
    if live.parse_connected_binding(clause) != binding:
        raise GateError("rendered live clause does not reproduce connected binding")
    clause_path = output / "AGENTS_R4W1C_LIVE_CLAUSE.md"
    durable_create_bytes(clause_path, (clause + "\n").encode("utf-8"))
    clause_identity = core.hash_stable_file(clause_path)
    packet = {
        "schema": SCHEMA,
        "created_at_utc": core.utc_now(),
        "target": live.TARGET,
        "source_identities": identities,
        "policy_template": template_identity,
        "connected_binding": binding,
        "rendered_clause": {
            "path": str(clause_path.relative_to(root)),
            **clause_identity,
        },
        "artifacts": artifacts,
        "device_contact": False,
        "device_writes": False,
        "reboot": False,
        "download_transition": False,
        "odin_transfer": False,
        "flash": False,
        "policy_edited": False,
        "verdict": "PASS_R4W1C_LIVE_BINDING_PACKET_EMITTED_HOST_ONLY",
    }
    packet_path = output / "packet.json"
    core.durable_create_json(packet_path, packet)
    packet["packet"] = {
        "path": str(packet_path.relative_to(root)),
        **core.hash_stable_file(packet_path),
    }
    return packet


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preconnected-check", action="store_true")
    modes.add_argument("--emit-after-connected", action="store_true")
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--candidate-boot", type=Path, default=connected.DEFAULT_CANDIDATE_BOOT)
    parser.add_argument("--candidate-lz4", type=Path, default=connected.DEFAULT_CANDIDATE_LZ4)
    parser.add_argument("--candidate-ap", type=Path, default=connected.DEFAULT_CANDIDATE_AP)
    parser.add_argument("--manifest", type=Path, default=connected.DEFAULT_MANIFEST)
    parser.add_argument("--static-result", type=Path, default=connected.DEFAULT_STATIC_RESULT)
    parser.add_argument("--magisk-ap", type=Path, default=connected.DEFAULT_MAGISK_AP)
    parser.add_argument("--stock-ap", type=Path, default=connected.DEFAULT_STOCK_AP)
    parser.add_argument("--full-firmware", type=Path, default=connected.DEFAULT_FULL_FIRMWARE)
    parser.add_argument("--odin", type=Path, default=connected.DEFAULT_ODIN)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    try:
        identities = source_gate(root)
        artifacts = live.verify_artifacts(root, args)
        if args.preconnected_check:
            if (root / connected.PASS_STATE).exists() or (
                root / connected.PASS_STATE
            ).is_symlink():
                raise GateError("R4W1-C connected PASS already exists")
            result = {
                "schema": SCHEMA,
                "mode": "preconnected-check",
                "target": live.TARGET,
                "source_identities": identities,
                "artifacts": artifacts,
                "connected_policy_active": True,
                "live_policy_active": False,
                "connected_pass_present": False,
                "candidate_consumed": False,
                "device_contact": False,
                "device_writes": False,
                "reboot": False,
                "download_transition": False,
                "odin_transfer": False,
                "flash": False,
                "verdict": "PASS_R4W1C_PRECONNECTED_SOURCE_PACKET_HOST_ONLY",
            }
        else:
            binding = connected_binding(root, artifacts)
            output = allocate_output(root, args.out_dir)
            result = emit_packet(
                root,
                output,
                identities=identities,
                artifacts=artifacts,
                binding=binding,
            )
        print(json.dumps(result, indent=2))
        return 0
    except (
        GateError,
        live.GateError,
        connected.GateError,
        core.LiveCoreError,
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

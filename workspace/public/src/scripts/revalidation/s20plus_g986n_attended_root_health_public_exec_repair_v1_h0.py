#!/usr/bin/env python3
"""Inactive H0 qualification model for the S20+ public exec-out repair.

The active attended root-health runner pre-quotes its public snapshot script
before passing it as the final argv element of ``adb exec-out sh -c``.  ADB
34.0.5 itself applies ``escape_arg`` to every exec-out argv element after the
first command, so that construction sends the already-quoted text as the
remote ``sh -c`` argument.  The root read uses the different ``adb shell``
join path and must retain its existing runner-owned ``shlex.quote`` literal.

This module performs no replacement and has no connected mode.  It validates
an exact two-fragment candidate transformation in memory, models the two ADB
command constructors, and renders a review plan.  Activation, runner/test/
contract rotation, a new direct request, and all live authority remain false.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import shlex
from types import MappingProxyType
from typing import Any, Final, Mapping, Sequence


STATUS = "H0_ATTENDED_ROOT_HEALTH_PUBLIC_EXEC_REPAIR_V1_PASS_GO_NOT_ACTIVE"
SCHEMA = "s20plus_g986n_attended_root_health_public_exec_repair_v1_h0"
EXPECTED_SELF_NORMALIZED_SHA256 = (
    "b507ec66a7ab3223fc8dbc38e083895b44ff553cc65517a438b03a5c3de4084e"
)

REPAIR_REVIEWED = False
ACTIVE_RUNNER_EXACT_BOUND = False
ADB_SOURCE_CORRESPONDENCE_REVIEWED = False
FOCUSED_TEST_ROTATION_REVIEWED = False
TARGET_CONTRACT_ROTATED = False
DOCUMENT_ASSERTIONS_ROTATED = False
ACTIVE_RUNNER_ROTATED = False
MECHANICAL_ACTIVATION_COMPLETE = False
FRESH_DIRECT_REQUEST_PRESENT = False
LIVE_AUTHORITY = False

NORMALIZED_GATE_NAMES = (
    "REPAIR_REVIEWED",
    "ACTIVE_RUNNER_EXACT_BOUND",
    "ADB_SOURCE_CORRESPONDENCE_REVIEWED",
    "FOCUSED_TEST_ROTATION_REVIEWED",
    "TARGET_CONTRACT_ROTATED",
    "DOCUMENT_ASSERTIONS_ROTATED",
    "ACTIVE_RUNNER_ROTATED",
    "MECHANICAL_ACTIVATION_COMPLETE",
    "FRESH_DIRECT_REQUEST_PRESENT",
    "LIVE_AUTHORITY",
)

TARGET = MappingProxyType(
    {
        "model": "SM-G986N",
        "device": "y2q",
        "product": "y2qksx",
        "build": "G986NKSS8IYC2",
    }
)

REPO_ROOT = Path(__file__).resolve().parents[5]
ACTIVE_RUNNER_PATH = REPO_ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_attended_root_health_d0.py"
)
ACTIVE_RUNNER_IDENTITY = MappingProxyType(
    {
        "path": str(ACTIVE_RUNNER_PATH),
        "size": 39_820,
        "sha256": (
            "7967f85dc1418473c66b418cedfc2c15063a141fed2550d040eb122fec04584a"
        ),
    }
)
CANDIDATE_RUNNER_IDENTITY = MappingProxyType(
    {
        "size": 39_819,
        "sha256": (
            "24f69cc5aa43c70558e3594534ee684db0a038e972d1b0db2f1b8d8446af2d44"
        ),
    }
)
ADB_IDENTITY = MappingProxyType(
    {
        "path": "/usr/lib/android-sdk/platform-tools/adb",
        "size": 716_968,
        "sha256": (
            "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
        ),
        "platform_tools_tag": "platform-tools-34.0.5",
        "ubuntu_source_version": "34.0.5-12build1",
    }
)

AOSP_COMMANDLINE_URL = (
    "https://android.googlesource.com/platform/packages/modules/adb/+/"
    "refs/tags/platform-tools-34.0.5/client/commandline.cpp"
)
AOSP_ESCAPE_ARG_URL = (
    "https://android.googlesource.com/platform/packages/modules/adb/+/"
    "refs/tags/platform-tools-34.0.5/adb_utils.cpp"
)

INCIDENT = MappingProxyType(
    {
        "verdict": "FAIL_S20PLUS_G986N_ATTENDED_ROOT_HEALTH_D0_READ_CLOSED",
        "failure_class": "RootHealthD0Error",
        "failure_message": "selected target public snapshot has the wrong field count",
        "failure_signature_sha256": (
            "a796e18647a44a3cbf815f57dc6e2539c7ab8d6852ae83397affafaa04f007e7"
        ),
        "failure_receipt_sha256": (
            "ddbab45528249b7c6c65e61d53e2a036ce5a4c67834ec78f7483038c5ebc1296"
        ),
        "host_commands": 3,
        "public_snapshots": 1,
        "root_commands": 0,
        "device_effects": 0,
    }
)

OLD_ARGUMENT_LINE = (
    b"PUBLIC_SHELL_ARGUMENT = shlex.quote(PUBLIC_SNAPSHOT_SCRIPT)\n"
)
NEW_ARGUMENT_LINE = b"PUBLIC_SHELL_ARGUMENT = PUBLIC_SNAPSHOT_SCRIPT\n"
OLD_PLAN_BLOCK = (
    b'        "public_snapshot_transport": [\n'
    b'            "exec-out",\n'
    b'            "sh",\n'
    b'            "-c",\n'
    b'            "<single-shlex-quoted-fixed-literal>",\n'
    b"        ],\n"
)
NEW_PLAN_BLOCK = (
    b'        "public_snapshot_transport": [\n'
    b'            "exec-out",\n'
    b'            "sh",\n'
    b'            "-c",\n'
    b'            "<single-raw-fixed-script-argv-ADB-escaped-once>",\n'
    b"        ],\n"
)
EXACT_REPLACEMENTS: Final[tuple[tuple[bytes, bytes], ...]] = (
    (OLD_ARGUMENT_LINE, NEW_ARGUMENT_LINE),
    (OLD_PLAN_BLOCK, NEW_PLAN_BLOCK),
)

PUBLIC_SCRIPT_SIZE = 423
PUBLIC_SCRIPT_SHA256 = (
    "f17aac6c9c946968b18ac91a05c6d8f006fef1857533518495a97d5e71d9813b"
)
ACTIVE_PUBLIC_ARGUMENT_SIZE = 449
ACTIVE_PUBLIC_ARGUMENT_SHA256 = (
    "0fa4c7d3b01941f467f5ad2da51059f5b7ae5d054267a39fdca2cac878f8e4f9"
)
ACTIVE_EXEC_SERVICE_SIZE = 524
ACTIVE_EXEC_SERVICE_SHA256 = (
    "206586836f8f8bc43a0f6b1d414c9d2df9b3fa7d41e1c9629b4d1ce460a0771f"
)
CANDIDATE_EXEC_SERVICE_SIZE = 456
CANDIDATE_EXEC_SERVICE_SHA256 = (
    "8ff45512fd92c37671396cf1d0abeb5b591dd1cdf37a5ee7bbc489d9f3acdbbf"
)
ROOT_SCRIPT_SIZE = 584
ROOT_SCRIPT_SHA256 = (
    "128ba6294378442b9e2a580086c2a8f6fc2f06afe30e642066f9bca4af314da1"
)
ROOT_ARGUMENT_SIZE = 594
ROOT_ARGUMENT_SHA256 = (
    "e5db5a7bb0fb78553e033649bc16496c008b9e5882b88f0c84234c1dede657aa"
)


class PublicExecRepairV1Error(RuntimeError):
    """Any source drift, ambiguous transform, or attempted activation stops."""


def sha256_bytes(value: bytes) -> str:
    if type(value) is not bytes:
        raise PublicExecRepairV1Error("hash input must be exact bytes")
    return hashlib.sha256(value).hexdigest()


def _read_self_bytes() -> bytes:
    return Path(__file__).resolve(strict=True).read_bytes()


def normalized_source_sha256(source: bytes) -> str:
    if type(source) is not bytes:
        raise PublicExecRepairV1Error("source normalization requires exact bytes")
    normalized, identity_count = re.subn(
        rb'^EXPECTED_SELF_NORMALIZED_SHA256 = \(\n    "[0-9a-f]{64}"\n\)$',
        b'EXPECTED_SELF_NORMALIZED_SHA256 = (\n    "<NORMALIZED-SELF-SHA256>"\n)',
        source,
        flags=re.MULTILINE,
    )
    if identity_count != 1:
        raise PublicExecRepairV1Error("self identity normalization is ambiguous")
    for name in NORMALIZED_GATE_NAMES:
        normalized, count = re.subn(
            rb"^" + name.encode("ascii") + rb" = (?:False|True)$",
            name.encode("ascii") + b" = <REVIEWED-GATE>",
            normalized,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise PublicExecRepairV1Error("source gate normalization is ambiguous")
    return sha256_bytes(normalized)


def _literal_assignments(source: bytes) -> dict[str, Any]:
    try:
        tree = ast.parse(source.decode("utf-8"))
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise PublicExecRepairV1Error("runner source is not exact parseable UTF-8") from exc
    values: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        if target.id in {"PUBLIC_SNAPSHOT_SCRIPT", "ROOT_READ_SCRIPT"}:
            try:
                values[target.id] = ast.literal_eval(node.value)
            except (ValueError, TypeError) as exc:
                raise PublicExecRepairV1Error("runner script literal is indirect") from exc
    if set(values) != {"PUBLIC_SNAPSHOT_SCRIPT", "ROOT_READ_SCRIPT"}:
        raise PublicExecRepairV1Error("runner fixed script closure differs")
    if any(type(value) is not str for value in values.values()):
        raise PublicExecRepairV1Error("runner fixed script is not text")
    return values


def _assignment_shape(source: bytes, name: str) -> ast.AST:
    tree = ast.parse(source.decode("utf-8"))
    matches = [
        node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == name
    ]
    if len(matches) != 1:
        raise PublicExecRepairV1Error(f"{name} assignment is ambiguous")
    return matches[0]


def _assert_name_assignment(source: bytes, name: str, referenced: str) -> None:
    value = _assignment_shape(source, name)
    if not isinstance(value, ast.Name) or value.id != referenced:
        raise PublicExecRepairV1Error(f"{name} is not the exact direct script reference")


def _assert_shlex_quote_assignment(source: bytes, name: str, referenced: str) -> None:
    value = _assignment_shape(source, name)
    if (
        not isinstance(value, ast.Call)
        or len(value.args) != 1
        or value.keywords
        or not isinstance(value.func, ast.Attribute)
        or not isinstance(value.func.value, ast.Name)
        or value.func.value.id != "shlex"
        or value.func.attr != "quote"
        or not isinstance(value.args[0], ast.Name)
        or value.args[0].id != referenced
    ):
        raise PublicExecRepairV1Error(f"{name} no longer has the exact shell quote shape")


def adb_escape_arg(value: str) -> str:
    """Exact ADB 34.0.5 ``escape_arg`` text transformation."""

    if type(value) is not str or "\x00" in value:
        raise PublicExecRepairV1Error("ADB argument is not exact NUL-free text")
    return "'" + value.replace("'", "'\\''") + "'"


def exec_out_service(command: str, *arguments: str) -> str:
    """Model commandline.cpp: argv[1] raw, each later argv escaped once."""

    if type(command) is not str or not command or "\x00" in command:
        raise PublicExecRepairV1Error("exec-out command differs")
    if any(type(value) is not str for value in arguments):
        raise PublicExecRepairV1Error("exec-out argument type differs")
    return "exec:" + command + "".join(" " + adb_escape_arg(v) for v in arguments)


def shell_join(command: str, *arguments: str) -> str:
    """Model adb_shell: non-option argv elements are joined without escaping."""

    values = (command, *arguments)
    if any(type(value) is not str or "\x00" in value for value in values):
        raise PublicExecRepairV1Error("shell join argument differs")
    return " ".join(values)


def apply_candidate_transform(active: bytes) -> bytes:
    if type(active) is not bytes:
        raise PublicExecRepairV1Error("active runner input must be exact bytes")
    if (
        len(active) != ACTIVE_RUNNER_IDENTITY["size"]
        or sha256_bytes(active) != ACTIVE_RUNNER_IDENTITY["sha256"]
    ):
        raise PublicExecRepairV1Error("active runner identity differs")
    candidate = active
    for old, new in EXACT_REPLACEMENTS:
        if candidate.count(old) != 1 or new in candidate:
            raise PublicExecRepairV1Error("candidate replacement is ambiguous")
        candidate = candidate.replace(old, new, 1)
    if (
        len(candidate) != CANDIDATE_RUNNER_IDENTITY["size"]
        or sha256_bytes(candidate) != CANDIDATE_RUNNER_IDENTITY["sha256"]
    ):
        raise PublicExecRepairV1Error("candidate runner identity differs")
    return candidate


def validate_candidate(active: bytes) -> dict[str, Any]:
    candidate = apply_candidate_transform(active)
    active_literals = _literal_assignments(active)
    candidate_literals = _literal_assignments(candidate)
    if candidate_literals != active_literals:
        raise PublicExecRepairV1Error("fixed remote scripts changed")

    public_script = candidate_literals["PUBLIC_SNAPSHOT_SCRIPT"]
    root_script = candidate_literals["ROOT_READ_SCRIPT"]
    _assert_shlex_quote_assignment(
        active, "PUBLIC_SHELL_ARGUMENT", "PUBLIC_SNAPSHOT_SCRIPT"
    )
    _assert_name_assignment(
        candidate, "PUBLIC_SHELL_ARGUMENT", "PUBLIC_SNAPSHOT_SCRIPT"
    )
    _assert_shlex_quote_assignment(candidate, "ROOT_SHELL_ARGUMENT", "ROOT_READ_SCRIPT")

    active_argument = shlex.quote(public_script)
    root_argument = shlex.quote(root_script)
    if (
        len(public_script.encode()) != PUBLIC_SCRIPT_SIZE
        or sha256_bytes(public_script.encode()) != PUBLIC_SCRIPT_SHA256
        or len(active_argument.encode()) != ACTIVE_PUBLIC_ARGUMENT_SIZE
        or sha256_bytes(active_argument.encode()) != ACTIVE_PUBLIC_ARGUMENT_SHA256
        or len(root_script.encode()) != ROOT_SCRIPT_SIZE
        or sha256_bytes(root_script.encode()) != ROOT_SCRIPT_SHA256
        or len(root_argument.encode()) != ROOT_ARGUMENT_SIZE
        or sha256_bytes(root_argument.encode()) != ROOT_ARGUMENT_SHA256
    ):
        raise PublicExecRepairV1Error("fixed script or argument identity differs")

    active_service = exec_out_service("sh", "-c", active_argument)
    candidate_service = exec_out_service("sh", "-c", public_script)
    if (
        len(active_service.encode()) != ACTIVE_EXEC_SERVICE_SIZE
        or sha256_bytes(active_service.encode()) != ACTIVE_EXEC_SERVICE_SHA256
        or len(candidate_service.encode()) != CANDIDATE_EXEC_SERVICE_SIZE
        or sha256_bytes(candidate_service.encode()) != CANDIDATE_EXEC_SERVICE_SHA256
    ):
        raise PublicExecRepairV1Error("modeled exec-out service identity differs")

    active_remote_argv = shlex.split(active_service.removeprefix("exec:"))
    candidate_remote_argv = shlex.split(candidate_service.removeprefix("exec:"))
    root_remote_argv = shlex.split(shell_join("su", "-c", root_argument))
    if active_remote_argv != ["sh", "-c", active_argument]:
        raise PublicExecRepairV1Error("active double-quote model differs")
    if candidate_remote_argv != ["sh", "-c", public_script]:
        raise PublicExecRepairV1Error("candidate single-escape model differs")
    if root_remote_argv != ["su", "-c", root_script]:
        raise PublicExecRepairV1Error("root shell join model differs")

    failure_material = (
        INCIDENT["failure_class"] + ":" + INCIDENT["failure_message"]
    ).encode("utf-8")
    if sha256_bytes(failure_material) != INCIDENT["failure_signature_sha256"]:
        raise PublicExecRepairV1Error("incident failure signature differs")

    return {
        "active_runner": dict(ACTIVE_RUNNER_IDENTITY),
        "candidate_runner": dict(CANDIDATE_RUNNER_IDENTITY),
        "changed_fragments": len(EXACT_REPLACEMENTS),
        "remote_scripts_byte_identical": True,
        "active_public_argument_equals_raw_script": active_argument == public_script,
        "candidate_public_argument_equals_raw_script": True,
        "active_exec_service": {
            "size": len(active_service.encode()),
            "sha256": sha256_bytes(active_service.encode()),
            "remote_final_argv_equals_raw_script": active_remote_argv[-1] == public_script,
            "remote_final_argv_equals_prequoted_script": active_remote_argv[-1]
            == active_argument,
        },
        "candidate_exec_service": {
            "size": len(candidate_service.encode()),
            "sha256": sha256_bytes(candidate_service.encode()),
            "remote_final_argv_equals_raw_script": candidate_remote_argv[-1]
            == public_script,
        },
        "root_transport_unchanged": root_remote_argv == ["su", "-c", root_script],
    }


def _gates() -> dict[str, bool]:
    return {
        "repair_reviewed": REPAIR_REVIEWED,
        "active_runner_exact_bound": ACTIVE_RUNNER_EXACT_BOUND,
        "adb_source_correspondence_reviewed": ADB_SOURCE_CORRESPONDENCE_REVIEWED,
        "focused_test_rotation_reviewed": FOCUSED_TEST_ROTATION_REVIEWED,
        "target_contract_rotated": TARGET_CONTRACT_ROTATED,
        "document_assertions_rotated": DOCUMENT_ASSERTIONS_ROTATED,
        "active_runner_rotated": ACTIVE_RUNNER_ROTATED,
        "mechanical_activation_complete": MECHANICAL_ACTIVATION_COMPLETE,
        "fresh_direct_request_present": FRESH_DIRECT_REQUEST_PRESENT,
        "live_authority": LIVE_AUTHORITY,
    }


def _require_live_gates() -> None:
    if not all(value is True for value in _gates().values()):
        raise PublicExecRepairV1Error("repair is H0-only and not active")
    raise PublicExecRepairV1Error("live repair/invocation is deliberately unimplemented")


def render_plan() -> dict[str, Any]:
    self_source = _read_self_bytes()
    normalized = normalized_source_sha256(self_source)
    if normalized != EXPECTED_SELF_NORMALIZED_SHA256:
        raise PublicExecRepairV1Error("repair model normalized source identity differs")
    gates = _gates()
    if any(gates.values()):
        raise PublicExecRepairV1Error("H0 render found an active gate")
    active_source = ACTIVE_RUNNER_PATH.read_bytes()
    qualification = validate_candidate(active_source)
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "self": {
            "size": len(self_source),
            "sha256": sha256_bytes(self_source),
            "normalized_sha256": normalized,
            "normalized_sha256_expected": EXPECTED_SELF_NORMALIZED_SHA256,
        },
        "target": dict(TARGET),
        "authority": {
            "tier": "H0",
            "device_contact": False,
            "adb_executed": False,
            "su_executed": False,
            "device_effects": 0,
            "writes": False,
            "reboots": False,
            "mode_transitions": False,
            "transfers": False,
            "partition_access": False,
            "live_authority": False,
        },
        "gates": gates,
        "incident": dict(INCIDENT),
        "pinned_adb": dict(ADB_IDENTITY),
        "source_provenance": {
            "commandline": AOSP_COMMANDLINE_URL,
            "escape_arg": AOSP_ESCAPE_ARG_URL,
            "binary_to_source_correspondence": "SUPPORTED_NOT_REPRODUCIBLY_PROVED",
        },
        "qualification": qualification,
        "claims": {
            "proved": [
                "active-runner-prequotes-public-script",
                "ADB-34-exec-out-escapes-each-argv-after-command",
                "active-modeled-service-delivers-prequoted-not-raw-script",
                "two-fragment-candidate-delivers-exact-raw-public-script",
                "root-shell-join-remains-byte-identical-and-correctly-prequoted",
                "candidate-performs-no-device-action",
            ],
            "supported": [
                "double-escaping-coherently-explains-read-closed-field-count-incident"
            ],
            "unknown": [
                "unretained-failed-public-snapshot-stdout",
                "double-escaping-was-the-only-runtime-cause",
                "candidate-live-result",
                "current-root-health",
            ],
        },
        "candidate_application": {
            "performed": False,
            "exact_replacement_count": len(EXACT_REPLACEMENTS),
            "root_script_changed": False,
            "root_argument_changed": False,
            "device_retry_authorized": False,
        },
        "caller_inputs": [],
        "connected_modes": [],
        "device_commands": [],
        "root_commands": [],
        "private_writes": [],
        "unresolved_gates": [
            "independent-hostile-review-of-model-and-two-fragment-candidate",
            "focused-active-runner-test-rotation",
            "target-contract-and-document-assertion-rotation",
            "post-rotation-independent-review",
            "mechanical-active-identity-rotation",
            "fresh-direct-attended-request-after-activation",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--render-plan", action="store_true")
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.render_plan:
        raise PublicExecRepairV1Error("only the H0 render mode exists")
    print(json.dumps(render_plan(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

#!/usr/bin/env python3
"""Prepare an inert R4W1-B live-policy review packet after connected PASS.

This helper never enumerates or contacts a device.  It only reopens the exact
connected PASS and result, fills a hash-pinned clause template, and writes a
private host-side review packet.  The rendered clause is not authorization and
must still pass independent review plus a separate AGENTS.md commit.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

import s22plus_boot_only_live_core as core
import s22plus_fyg8_r4w1b_live_gate as gate


SCHEMA = "s22plus_fyg8_r4w1b_live_binding_packet_v1"
TEMPLATE_RELATIVE = Path(
    "docs/operations/"
    "S22PLUS_FYG8_R4W1B_LIVE_BINDING_CLAUSE_TEMPLATE_2026-07-19.md"
)
EXPECTED_TEMPLATE_SHA256 = (
    "66b14fc1c87497346c4c6583f93d3e2c3bd4505c3a688837f91c540b2a7eb68f"
)
EXPECTED_HELPER_SHA256 = (
    "734693c456d482e6a09360129ba74e9123017b5c42829518a23870d07465a95d"
)
EXPECTED_TEST_SHA256 = (
    "87de80150d1962c5804471a8037657144a4c394cd8cba5c596947c0723be42c1"
)
EXPECTED_CORE_SHA256 = (
    "9bcade2532e77d538112836ebe9903bab832c1f2250151d3635260b6fd013725"
)
EXPECTED_CORE_TEST_SHA256 = (
    "b55db8579115ec437e7fe63b6a3b6ecef0d8cbcac54110599e85f310f3b2fd9d"
)
RUN_ROOT = Path("workspace/private/runs")
PLACEHOLDERS = (
    "CONNECTED_PASS_CREATED_AT_UTC",
    "CONNECTED_PASS_RECORD_SIZE",
    "CONNECTED_PASS_RECORD_SHA256",
    "CONNECTED_RESULT_PATH",
    "CONNECTED_RESULT_SIZE",
    "CONNECTED_RESULT_SHA256",
)


class PacketError(RuntimeError):
    pass


def source_pins(root: Path) -> dict[str, str]:
    pins = {
        "helper_sha256": gate.helper_sha256(root),
        "test_sha256": gate.test_sha256(root),
        "core_sha256": gate.core_sha256(root),
        "core_test_sha256": gate.core_test_sha256(root),
    }
    expected = {
        "helper_sha256": EXPECTED_HELPER_SHA256,
        "test_sha256": EXPECTED_TEST_SHA256,
        "core_sha256": EXPECTED_CORE_SHA256,
        "core_test_sha256": EXPECTED_CORE_TEST_SHA256,
    }
    if pins != expected:
        raise PacketError(f"R4W1-B source pins changed: {pins}")
    return pins


def read_template(root: Path) -> tuple[str, dict[str, Any]]:
    path = root / TEMPLATE_RELATIVE
    identity = core.hash_stable_file(path)
    if identity["sha256"] != EXPECTED_TEMPLATE_SHA256:
        raise PacketError("R4W1-B live binding template identity changed")
    payload = core.read_stable_file(path, maximum=1024 * 1024)
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PacketError("R4W1-B live binding template is not UTF-8") from exc
    for name in PLACEHOLDERS:
        token = "{{" + name + "}}"
        if text.count(token) != 1:
            raise PacketError(f"template placeholder count is not one: {token}")
    unknown = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", text)) - {
        "{{" + name + "}}" for name in PLACEHOLDERS
    })
    if unknown:
        raise PacketError(f"template has unknown placeholders: {unknown}")
    return text, identity


def validate_render_values(values: dict[str, str]) -> None:
    if set(values) != set(PLACEHOLDERS):
        raise PacketError("render values do not match the exact placeholder set")
    for name, value in values.items():
        if (
            not value
            or "{{" in value
            or "}}" in value
            or "`" in value
            or any(ord(character) < 0x20 for character in value)
        ):
            raise PacketError(f"unsafe render value: {name}")
    if not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z",
        values["CONNECTED_PASS_CREATED_AT_UTC"],
    ):
        raise PacketError("connected PASS timestamp is not canonical UTC")
    for name in ("CONNECTED_PASS_RECORD_SIZE", "CONNECTED_RESULT_SIZE"):
        if not re.fullmatch(r"[1-9][0-9]*", values[name]):
            raise PacketError(f"connected evidence size is not positive decimal: {name}")
    for name in ("CONNECTED_PASS_RECORD_SHA256", "CONNECTED_RESULT_SHA256"):
        if not re.fullmatch(r"[0-9a-f]{64}", values[name]):
            raise PacketError(f"connected evidence SHA256 is malformed: {name}")
    result_path = values["CONNECTED_RESULT_PATH"]
    parsed = Path(result_path)
    if (
        not re.fullmatch(r"[A-Za-z0-9._/-]+", result_path)
        or parsed.is_absolute()
        or str(parsed) != result_path
        or ".." in parsed.parts
        or parsed.name != "result.json"
        or tuple(parsed.parts[:3]) != ("workspace", "private", "runs")
    ):
        raise PacketError("connected result path is not canonical private-run evidence")


def render_template(template: str, values: dict[str, str]) -> str:
    validate_render_values(values)
    rendered = template
    for name in PLACEHOLDERS:
        token = "{{" + name + "}}"
        if rendered.count(token) != 1:
            raise PacketError(f"render placeholder count is not one: {token}")
        rendered = rendered.replace(token, values[name])
    if re.search(r"\{\{[A-Z0-9_]+\}\}", rendered):
        raise PacketError("rendered template retains a placeholder")
    return rendered


def extract_exact_clause(rendered: str) -> str:
    match = re.search(r"(?ms)^```text\n(.*?)^```\s*$", rendered)
    if match is None:
        raise PacketError("rendered template has no unique text fence")
    if len(re.findall(r"(?m)^```text$", rendered)) != 1:
        raise PacketError("rendered template has multiple text fences")
    clause = match.group(1)
    if gate.LIVE_ACTIVE_SENTINEL not in clause:
        raise PacketError("rendered clause lacks the live ACTIVE sentinel")
    if clause.count(gate.LIVE_ACTIVE_SENTINEL) != 1:
        raise PacketError("rendered clause live ACTIVE sentinel count is not one")
    return clause


def stable_json(path: Path, *, maximum: int) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    payload = core.read_stable_file(path, maximum=maximum)
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PacketError(f"invalid stable JSON evidence: {path}") from exc
    if not isinstance(value, dict):
        raise PacketError(f"stable JSON evidence is not an object: {path}")
    return value, payload, {"size": len(payload), "sha256": core.sha256_bytes(payload)}


def reopen_connected_evidence(
    root: Path, pins: dict[str, str]
) -> tuple[dict[str, Any], dict[str, Any], Path, dict[str, Any]]:
    pass_path = root / gate.CONNECTED_PASS_STATE
    record, pass_before, pass_identity = stable_json(pass_path, maximum=1024 * 1024)
    expected = {
        "schema": "s22plus_fyg8_r4w1b_connected_pass_v1",
        "target": gate.TARGET,
        **pins,
        "verdict": "PASS_R4W1B_CONNECTED_BASELINE_READ_ONLY",
        "device_writes": False,
    }
    if any(record.get(key) != value for key, value in expected.items()):
        raise PacketError("stable connected PASS contract mismatch")
    result_text = str(record.get("result_path", ""))
    provisional = {
        "CONNECTED_PASS_CREATED_AT_UTC": str(record.get("created_at_utc", "")),
        "CONNECTED_PASS_RECORD_SIZE": str(pass_identity["size"]),
        "CONNECTED_PASS_RECORD_SHA256": str(pass_identity["sha256"]),
        "CONNECTED_RESULT_PATH": result_text,
        "CONNECTED_RESULT_SIZE": "1",
        "CONNECTED_RESULT_SHA256": "0" * 64,
    }
    validate_render_values(provisional)
    result_relative = Path(result_text)
    result_path = gate.resolve(root, result_relative)
    run_root = gate.resolve(root, gate.RUN_ROOT)
    if not result_path.is_relative_to(run_root):
        raise PacketError("connected result escaped private runs")
    result, result_before, result_identity = stable_json(
        result_path, maximum=8 * 1024 * 1024
    )
    if result_identity["sha256"] != record.get("result_sha256"):
        raise PacketError("connected result SHA differs from PASS record")
    gate.validate_connected_result_contract(result)
    canonical = gate.validate_connected_pass(root)
    if canonical != record:
        raise PacketError("canonical and stable connected PASS records differ")
    _, pass_after, pass_after_identity = stable_json(pass_path, maximum=1024 * 1024)
    _, result_after, result_after_identity = stable_json(
        result_path, maximum=8 * 1024 * 1024
    )
    if (
        pass_before != pass_after
        or pass_identity != pass_after_identity
        or result_before != result_after
        or result_identity != result_after_identity
    ):
        raise PacketError("connected evidence changed while reopening it")
    return record, pass_identity, result_relative, result_identity


def ensure_promotion_state(root: Path, *, require_connected_pass: bool) -> dict[str, Any]:
    if not gate.policy_active(root, connected=True):
        raise PacketError("R4W1-B connected policy is inactive")
    if gate.policy_active(root, connected=False):
        raise PacketError("R4W1-B live policy is already active")
    consumed = root / gate.CONSUMED_STATE
    if consumed.exists() or consumed.is_symlink():
        raise PacketError("R4W1-B candidate state is already consumed")
    pass_path = root / gate.CONNECTED_PASS_STATE
    pass_present = pass_path.is_file() and not pass_path.is_symlink()
    if require_connected_pass and not pass_present:
        raise PacketError("R4W1-B connected PASS is absent")
    if not require_connected_pass and (pass_path.exists() or pass_path.is_symlink()):
        raise PacketError("preconnected check requires connected PASS to be absent")
    return {
        "connected_policy_active": True,
        "live_policy_active": False,
        "connected_pass_present": pass_present,
        "candidate_consumed": False,
    }


def durable_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        core._fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def preconnected_check(root: Path) -> dict[str, Any]:
    pins = source_pins(root)
    _, template_identity = read_template(root)
    policy_draft = gate.verify_policy_draft(root)
    state = ensure_promotion_state(root, require_connected_pass=False)
    return {
        "schema": SCHEMA,
        "mode": "preconnected-check",
        "target": gate.TARGET,
        "source_pins": pins,
        "template": {
            "path": str(TEMPLATE_RELATIVE),
            **template_identity,
        },
        "inactive_full_policy_draft": policy_draft,
        "state": state,
        "device_contact": False,
        "device_writes": False,
        "flash": False,
        "verdict": "PASS_R4W1B_LIVE_BINDING_PACKET_PRECONNECTED_READY",
    }


def emit_after_connected(root: Path, requested: Path | None) -> dict[str, Any]:
    pins = source_pins(root)
    template, template_identity = read_template(root)
    state = ensure_promotion_state(root, require_connected_pass=True)
    record, pass_identity, result_relative, result_identity = reopen_connected_evidence(
        root, pins
    )
    values = {
        "CONNECTED_PASS_CREATED_AT_UTC": str(record["created_at_utc"]),
        "CONNECTED_PASS_RECORD_SIZE": str(pass_identity["size"]),
        "CONNECTED_PASS_RECORD_SHA256": str(pass_identity["sha256"]),
        "CONNECTED_RESULT_PATH": str(result_relative),
        "CONNECTED_RESULT_SIZE": str(result_identity["size"]),
        "CONNECTED_RESULT_SHA256": str(result_identity["sha256"]),
    }
    rendered = render_template(template, values)
    clause = extract_exact_clause(rendered)
    run_dir = core.allocate_run_dir(
        root, RUN_ROOT, "s22plus-r4w1b-live-binding", requested
    )
    rendered_path = run_dir / "rendered_live_binding_clause.md"
    clause_path = run_dir / "exact_agents_clause.txt"
    durable_write_text(rendered_path, rendered)
    durable_write_text(clause_path, clause)
    final_record, final_pass_identity, final_result_relative, final_result_identity = (
        reopen_connected_evidence(root, pins)
    )
    if (
        final_record != record
        or final_pass_identity != pass_identity
        or final_result_relative != result_relative
        or final_result_identity != result_identity
    ):
        raise PacketError("connected evidence changed during packet emission")
    packet = {
        "schema": SCHEMA,
        "mode": "emit-after-connected",
        "target": gate.TARGET,
        "created_at_utc": core.utc_now(),
        "source_pins": pins,
        "template": {"path": str(TEMPLATE_RELATIVE), **template_identity},
        "connected_pass": {
            "path": str(gate.CONNECTED_PASS_STATE),
            **pass_identity,
            "record": record,
        },
        "connected_result": {"path": str(result_relative), **result_identity},
        "render_values": values,
        "rendered_clause": {
            "path": str(rendered_path.relative_to(root)),
            **core.hash_stable_file(rendered_path),
        },
        "exact_agents_clause": {
            "path": str(clause_path.relative_to(root)),
            **core.hash_stable_file(clause_path),
            "live_active_sentinel_count": clause.count(gate.LIVE_ACTIVE_SENTINEL),
        },
        "state": state,
        "device_contact": False,
        "device_writes": False,
        "flash": False,
        "verdict": "PASS_R4W1B_LIVE_BINDING_REVIEW_PACKET_EMITTED_HOST_ONLY",
    }
    core.durable_write_json(run_dir / "packet.json", packet)
    return {"run_dir": str(run_dir), **packet}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preconnected-check", action="store_true")
    modes.add_argument("--emit-after-connected", action="store_true")
    parser.add_argument("--run-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = gate.repo_root()
    try:
        if args.preconnected_check:
            if args.run_dir is not None:
                raise PacketError("preconnected check does not accept --run-dir")
            result = preconnected_check(root)
        else:
            result = emit_after_connected(root, args.run_dir)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (PacketError, gate.GateError, core.LiveCoreError, OSError, KeyError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

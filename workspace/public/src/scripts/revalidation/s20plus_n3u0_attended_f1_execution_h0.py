#!/usr/bin/env python3
"""Dormant evidence-backed execution join for S20+ N3-U0 attended F1."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import types
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
SCHEMA = "s20plus_g986n_n3u0_attended_f1_execution_h0_v1"
STATUS = "H0_EVIDENCE_EXECUTION_INTEGRATION_PASS_GO_NOT_ACTIVE"
EXECUTION_ACTIVE = False
EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256 = "a73e44d0241b904948eaeeb80a5a4cc9c4387fe2f55bba5120013f7fcdd806e7"
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_CAPTURE_ITEMS = 64
SUMMARY_ORDINAL = 90

TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "build": "G986NKSS8IYC2",
}

SOURCES = {
    "journal": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/s20plus_n3u0_attended_f1.py",
        "size": 55_803,
        "sha256": "2c4d7335211ade6c25540782148f44c309da6373d8ad495a5904d43714a01e86",
    },
    "integration": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_n3u0_attended_f1_integration_h0.py",
        "size": 18_516,
        "sha256": "4b5234f818306ffc8d361ee8b14b15c74702b23b05f752c5acef5171071bc3a0",
    },
    "backend": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_n3u0_attended_f1_backend_h0.py",
        "size": 30_896,
        "sha256": "0d8a752e94ea34f5130a53fe2747c7e949561db54ba661d55c4af2db0a19e27b",
    },
    "evidence": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_n3u0_attended_f1_evidence_h0.py",
        "size": 23_833,
        "sha256": "730e5e78368894ef30e22d9e1f7d8356f6dfc00a536fc36b322ac0424cb84f09",
    },
}

EXPECTED_BINDINGS = {
    "journal": "4695acca5c8d618eee7e16aaf665cbf66235a5a76aadc0a4322f490113cc2945",
    "integration": "2a037eb3cab5f068b0d534d034fcadce51b26c3ee9f5874ec583b90905a6d6a6",
    "backend": "5561aabc35f20752702b8ef12ec6f8d4669bbef8b022ff5557c7925c34b9704b",
    "evidence": "c59992f48361429812475b6535c4ad927ee63cad81f61a1d4e2ac59567402f47",
}

OPERATIONS = frozenset(
    {
        "initial-download-reboot",
        "initial-download-observation",
        "candidate-transfer",
        "candidate-observation",
        "rollback-download-reboot",
        "rollback-download-observation",
        "rollback-transfer",
        "final-resident-health",
    }
)
HEX64_RE = re.compile(r"[0-9a-f]{64}")


class ExecutionError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ExecutionError("execution value is not canonical JSON") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _reject_constant(value: str) -> Any:
    raise ValueError(f"non-finite JSON constant {value}")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _read_exact(expected: dict[str, Any], label: str) -> bytes:
    path = expected["path"]
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as exc:
        raise ExecutionError(f"{label} is unavailable") from exc
    try:
        metadata = os.fstat(descriptor)
        size = expected["size"]
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or type(size) is not int
            or not 0 < size <= MAX_SOURCE_BYTES
            or metadata.st_size != size
        ):
            raise ExecutionError(f"{label} identity differs")
        payload = bytearray()
        while len(payload) < size:
            chunk = os.read(descriptor, min(1024 * 1024, size - len(payload)))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) != size or os.read(descriptor, 1):
            raise ExecutionError(f"{label} length differs")
    finally:
        os.close(descriptor)
    result = bytes(payload)
    if hashlib.sha256(result).hexdigest() != expected["sha256"]:
        raise ExecutionError(f"{label} hash differs")
    return result


def _load_exact(expected: dict[str, Any], name: str) -> Any:
    payload = _read_exact(expected, name)
    module = types.ModuleType(name)
    module.__file__ = str(expected["path"])
    exec(compile(payload, str(expected["path"]), "exec"), module.__dict__)
    return module


def source_receipts() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name, expected in SOURCES.items():
        _read_exact(expected, f"N3-U0 execution {name}")
        result[name] = {
            "path": str(expected["path"]),
            "size": expected["size"],
            "sha256": expected["sha256"],
        }
    return result


def self_receipt() -> dict[str, Any]:
    path = Path(__file__).resolve()
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as exc:
        raise ExecutionError("execution runner is unavailable") from exc
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or not 0 < metadata.st_size <= MAX_SOURCE_BYTES
        ):
            raise ExecutionError("execution runner identity differs")
        data = bytearray()
        while len(data) < metadata.st_size:
            chunk = os.read(
                descriptor, min(1024 * 1024, metadata.st_size - len(data))
            )
            if not chunk:
                break
            data.extend(chunk)
        if len(data) != metadata.st_size or os.read(descriptor, 1):
            raise ExecutionError("execution runner length differs")
    finally:
        os.close(descriptor)
    payload = bytes(data)
    normalized = re.sub(
        rb'EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256 = "[0-9a-f]{64}"',
        b'EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256 = "' + b"0" * 64 + b'"',
        payload,
        count=1,
    )
    normalized_sha256 = hashlib.sha256(normalized).hexdigest()
    if normalized_sha256 != EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256:
        raise ExecutionError("execution runner normalized identity differs")
    return {
        "path": str(path),
        "size": len(payload),
        "normalized_sha256": normalized_sha256,
    }


def load_sources() -> dict[str, Any]:
    modules = {
        name: _load_exact(expected, f"n3u0_execution_{name}_bound")
        for name, expected in SOURCES.items()
    }
    for name, expected_binding in EXPECTED_BINDINGS.items():
        if modules[name].binding_sha256() != expected_binding:
            raise ExecutionError(f"{name} binding differs")
    if (
        modules["journal"].F1_ACTIVE is not False
        or modules["integration"].INTEGRATION_ACTIVE is not False
        or modules["backend"].BACKEND_ACTIVE is not False
        or modules["evidence"].EVIDENCE_ACTIVE is not False
    ):
        raise ExecutionError("an execution dependency unexpectedly exposes authority")
    return modules


def current_binding() -> dict[str, Any]:
    modules = load_sources()
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "target": dict(TARGET),
        "runner": self_receipt(),
        "bindings": dict(EXPECTED_BINDINGS),
        "dependency_status": {name: modules[name].STATUS for name in modules},
        "sources": source_receipts(),
        "operations": sorted(OPERATIONS),
        "summary_ordinal": SUMMARY_ORDINAL,
        "no_replay_after_intent": True,
    }


def binding_sha256() -> str:
    return digest(current_binding())


def require_active() -> None:
    if EXECUTION_ACTIVE is not True:
        raise ExecutionError("N3-U0 evidence execution integration is not active")


def _parse_canonical(payload: bytes, label: str) -> Any:
    try:
        value = json.loads(
            payload.decode("utf-8", "strict"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
        if payload != canonical_bytes(value):
            raise ValueError("noncanonical bytes")
        return value
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise ExecutionError(f"{label} is malformed") from exc


class ExecutionSession:
    """Exact in-process H0 join. No caller backend, command, path, or callback."""

    def __init__(self) -> None:
        require_active()
        self._modules = load_sources()
        self._backend = self._modules["backend"].FixedBackend()
        self._fresh: set[tuple[str, str]] = set()

    def _capture_fresh(self, run_dir: Path, operation: str) -> Any:
        require_active()
        key = (run_dir.name, operation)
        if key not in self._fresh:
            raise ExecutionError("operation intent was not created by this invocation")
        self._fresh.remove(key)
        journal = self._modules["journal"]
        evidence = self._modules["evidence"]
        journal.validate_legal_prefix(run_dir)
        self._backend.begin_operation_capture(operation)
        try:
            if operation == "initial-download-reboot":
                intent = journal.read_exact_json(
                    run_dir / "initial-download-intent.json",
                    "initial Download intent",
                )
                semantic = self._backend.reboot_download(
                    "initial", intent["source_identity"]
                )
            elif operation == "initial-download-observation":
                semantic = self._backend.observe_download("initial")
            elif operation == "candidate-transfer":
                intent = journal.read_exact_json(
                    run_dir / "candidate-intent.json", "candidate intent"
                )
                semantic = self._backend.transfer_boot(
                    "candidate", intent["endpoint"]
                )
            elif operation == "candidate-observation":
                semantic = self._backend.observe_candidate()
            elif operation == "rollback-download-reboot":
                intent = journal.read_exact_json(
                    run_dir / "rollback-mode-intent.json", "rollback mode intent"
                )
                semantic = self._backend.reboot_download(
                    "rollback", intent["source_identity"]
                )
            elif operation == "rollback-download-observation":
                semantic = self._backend.observe_download("rollback")
            elif operation == "rollback-transfer":
                intent = journal.read_exact_json(
                    run_dir / "rollback-intent.json", "rollback intent"
                )
                semantic = self._backend.transfer_boot(
                    "rollback", intent["endpoint"]
                )
            elif operation == "final-resident-health":
                semantic = self._backend.final_resident_health()
            else:
                raise ExecutionError("unknown fixed backend operation")
        except BaseException as exc:
            captured = self._backend.consume_operation_capture(operation)
            semantic = None
            error_class: str | None = type(exc).__name__
            original: BaseException | None = exc
        else:
            captured = self._backend.consume_operation_capture(operation)
            error_class = None
            original = None

        captures = captured["commands"]
        full_receipt = captured["full_receipt"]
        if not isinstance(captures, list) or len(captures) > MAX_CAPTURE_ITEMS:
            raise ExecutionError("operation capture count is malformed")
        result_digests: list[str] = []
        for ordinal, capture in enumerate(captures, start=1):
            if not isinstance(capture, dict) or set(capture) != {
                "argv",
                "timeout_seconds",
                "output_limit",
                "returncode",
                "stdout",
                "stderr",
            }:
                raise ExecutionError("captured command shape differs")
            result = evidence.publish_command_result(
                run_dir,
                operation,
                ordinal,
                capture["argv"],
                capture["timeout_seconds"],
                capture["output_limit"],
                capture["returncode"],
                capture["stdout"],
                capture["stderr"],
            )
            result_digests.append(evidence.digest(result))
        if (error_class is None) == (semantic is None):
            raise ExecutionError("operation outcome is ambiguous")
        if error_class is None and not isinstance(full_receipt, dict):
            raise ExecutionError("complete backend return lacks its full receipt")
        if error_class is not None and full_receipt is not None:
            raise ExecutionError("failed backend return unexpectedly has a receipt")
        summary = {
            "schema": "s20plus_g986n_n3u0_backend_return_v1",
            "operation": operation,
            "capture_count": len(captures),
            "capture_result_sha256": result_digests,
            "outcome": "complete" if error_class is None else "producer-error",
            "semantic": semantic,
            "full_receipt": full_receipt,
            "error_class": error_class,
            "replay_permitted": False,
        }
        payload = canonical_bytes(summary)
        evidence.publish_command_result(
            run_dir,
            operation,
            SUMMARY_ORDINAL,
            ["n3u0-fixed-backend-return", operation],
            1,
            max(1, len(payload)),
            0,
            payload,
            b"",
        )
        if original is not None:
            raise original
        return semantic

    def enter_initial_download(self, run_dir: Path) -> str:
        require_active()
        journal = self._modules["journal"]
        journal.begin_initial_download(run_dir)
        self._fresh.add((run_dir.name, "initial-download-reboot"))
        self._capture_fresh(run_dir, "initial-download-reboot")
        reboot = derive_initial_download_result(run_dir)
        if reboot.get("state") != "complete" or reboot["semantic"]["outcome"] != "dispatched":
            raise ExecutionError("initial Download dispatch is not complete")
        self._fresh.add((run_dir.name, "initial-download-observation"))
        self._capture_fresh(run_dir, "initial-download-observation")
        observed = derive_initial_download_observation(run_dir)
        if observed.get("state") != "complete":
            raise ExecutionError("initial Download observation is incomplete")
        return journal.approval_token(run_dir)

    def transfer_candidate(self, run_dir: Path, approval: str) -> dict[str, Any]:
        require_active()
        journal = self._modules["journal"]
        arrival = journal.read_exact_json(
            run_dir / "initial-download-observation.json",
            "initial Download observation",
        )
        journal.begin_candidate(run_dir, approval, arrival["endpoint"])
        self._fresh.add((run_dir.name, "candidate-transfer"))
        self._capture_fresh(run_dir, "candidate-transfer")
        transfer = derive_transfer_result(run_dir, "candidate")
        if transfer.get("state") != "complete":
            raise ExecutionError("candidate transfer evidence is incomplete")
        self._fresh.add((run_dir.name, "candidate-observation"))
        self._capture_fresh(run_dir, "candidate-observation")
        observed = derive_candidate_observation(run_dir)
        if observed.get("state") != "complete":
            raise ExecutionError("candidate observation evidence is incomplete")
        return observed["semantic"]

    def automatic_rollback(self, run_dir: Path) -> dict[str, Any]:
        require_active()
        journal = self._modules["journal"]
        candidate = journal.read_exact_json(
            run_dir / "candidate-observation.json", "candidate observation"
        )
        source = candidate.get("android_identity")
        if source is None:
            raise ExecutionError("automatic rollback lacks Android source identity")
        journal.begin_rollback_mode(run_dir)
        self._fresh.add((run_dir.name, "rollback-download-reboot"))
        self._capture_fresh(run_dir, "rollback-download-reboot")
        reboot = derive_rollback_download_result(run_dir)
        if reboot.get("state") != "complete" or reboot["semantic"]["outcome"] != "dispatched":
            raise ExecutionError("rollback Download dispatch is not complete")
        self._fresh.add((run_dir.name, "rollback-download-observation"))
        self._capture_fresh(run_dir, "rollback-download-observation")
        observed = derive_rollback_download_observation(run_dir)
        if observed.get("state") != "complete":
            raise ExecutionError("rollback Download observation is incomplete")
        journal.begin_rollback(run_dir)
        self._fresh.add((run_dir.name, "rollback-transfer"))
        self._capture_fresh(run_dir, "rollback-transfer")
        transfer = derive_transfer_result(run_dir, "rollback")
        if transfer.get("state") != "complete":
            raise ExecutionError("rollback transfer evidence is incomplete")
        return transfer["semantic"]

    def finalize_resident(self, run_dir: Path) -> dict[str, Any]:
        require_active()
        journal = self._modules["journal"]
        if os.path.lexists(run_dir / "terminal-result.json"):
            return journal.finalize(run_dir)
        if not os.path.lexists(run_dir / "final-health.json"):
            existing = derive_backend_return(run_dir, "final-resident-health")
            if existing.get("state") == "complete":
                derive_final_health(run_dir)
            elif existing.get("state") == "intent-consumed-evidence-absent":
                self._fresh.add((run_dir.name, "final-resident-health"))
                self._capture_fresh(run_dir, "final-resident-health")
                derive_final_health(run_dir)
            else:
                raise ExecutionError("final health evidence is consumed or incomplete")
        return journal.finalize(run_dir)


def derive_backend_return(run_dir: Path, operation: str) -> dict[str, Any]:
    require_active()
    modules = load_sources()
    if operation not in OPERATIONS:
        raise ExecutionError("unknown execution operation")
    evidence = modules["evidence"]
    inspection = evidence.inspect_operation(run_dir, operation, SUMMARY_ORDINAL)
    if inspection.get("state") != "complete":
        prepared = modules["journal"].read_prepared(run_dir)
        names = evidence._evidence_names(prepared["run_id"])
        prefix = f"{operation}-"
        state = (
            "uncertain-consumed"
            if any(name.startswith(prefix) for name in names)
            else inspection.get("state")
        )
        return {
            "state": state,
            "operation": operation,
            "replay_permitted": False,
        }
    complete = evidence.read_complete_operation(
        run_dir, operation, SUMMARY_ORDINAL
    )
    if complete["stderr"] != b"":
        raise ExecutionError("backend return summary emitted stderr")
    result = complete["inspection"]["result"]
    if result.get("command_sha256") != evidence.digest(
        ["n3u0-fixed-backend-return", operation]
    ):
        raise ExecutionError("backend return command binding differs")
    summary = _parse_canonical(complete["stdout"], "backend return summary")
    keys = {
        "schema",
        "operation",
        "capture_count",
        "capture_result_sha256",
        "outcome",
        "semantic",
        "full_receipt",
        "error_class",
        "replay_permitted",
    }
    if (
        not isinstance(summary, dict)
        or set(summary) != keys
        or summary.get("schema") != "s20plus_g986n_n3u0_backend_return_v1"
        or summary.get("operation") != operation
        or type(summary.get("capture_count")) is not int
        or not 0 <= summary["capture_count"] <= MAX_CAPTURE_ITEMS
        or not isinstance(summary.get("capture_result_sha256"), list)
        or len(summary["capture_result_sha256"]) != summary["capture_count"]
        or any(
            not isinstance(item, str) or HEX64_RE.fullmatch(item) is None
            for item in summary["capture_result_sha256"]
        )
        or summary.get("outcome") not in {"complete", "producer-error"}
        or summary.get("replay_permitted") is not False
    ):
        raise ExecutionError("backend return summary shape differs")
    command_results: list[dict[str, Any]] = []
    for ordinal, expected_sha256 in enumerate(
        summary["capture_result_sha256"], start=1
    ):
        command = evidence.inspect_operation(run_dir, operation, ordinal)
        if command.get("state") != "complete" or evidence.digest(
            command["result"]
        ) != expected_sha256:
            raise ExecutionError("backend command evidence differs from summary")
        command_results.append(command["result"])
    if summary["outcome"] == "producer-error":
        if (
            summary.get("semantic") is not None
            or summary.get("full_receipt") is not None
            or not isinstance(summary.get("error_class"), str)
            or not summary["error_class"]
        ):
            raise ExecutionError("backend producer failure is malformed")
        return {
            "state": "producer-error-consumed",
            "operation": operation,
            "error_class": summary["error_class"],
            "replay_permitted": False,
        }
    if (
        summary.get("error_class") is not None
        or summary.get("semantic") is None
        or not isinstance(summary.get("full_receipt"), dict)
    ):
        raise ExecutionError("backend complete return is malformed")
    return {
        "state": "complete",
        "operation": operation,
        "semantic": summary["semantic"],
        "full_receipt": summary["full_receipt"],
        "command_results": command_results,
        "replay_permitted": False,
    }


def _require_effect_receipt_binding(
    modules: dict[str, Any], operation: str, derived: dict[str, Any]
) -> None:
    require_active()
    semantic = derived["semantic"]
    full = derived["full_receipt"]
    commands = derived["command_results"]
    if operation in {"initial-download-reboot", "rollback-download-reboot"}:
        phase = "initial" if operation.startswith("initial") else "rollback"
        if (
            not commands
            or full.get("operation") != f"{phase}-reboot-download"
            or full.get("outcome") != semantic.get("outcome")
            or not modules["journal"].exact_typed_equal(
                full.get("raw_receipt"), semantic.get("raw_receipt")
            )
            or not modules["journal"].exact_typed_equal(
                commands[-1].get("raw_receipt"), semantic.get("raw_receipt")
            )
        ):
            raise ExecutionError("reboot return differs from captured command")
        return
    if operation in {"candidate-transfer", "rollback-transfer"}:
        kind = "candidate" if operation.startswith("candidate") else "rollback"
        if (
            not commands
            or full.get("operation") != f"{kind}-boot-transfer"
            or full.get("classification") != semantic.get("classification")
            or not modules["journal"].exact_typed_equal(
                full.get("raw_receipt"), semantic.get("raw_receipt")
            )
            or not modules["journal"].exact_typed_equal(
                commands[-1].get("raw_receipt"), semantic.get("raw_receipt")
            )
        ):
            raise ExecutionError("transfer return differs from captured command")


def _require_read_receipt_binding(
    modules: dict[str, Any], operation: str, derived: dict[str, Any]
) -> None:
    require_active()
    semantic = derived["semantic"]
    full = derived["full_receipt"]
    if operation in {
        "initial-download-observation",
        "rollback-download-observation",
    }:
        if not modules["journal"].exact_typed_equal(full, semantic):
            raise ExecutionError("Download observation full receipt differs")
        return
    if operation == "candidate-observation":
        usb = full.get("usb_receipt")
        if (
            semantic.get("banner_accepted") is not True
            or not isinstance(semantic.get("android_identity"), dict)
            or not isinstance(usb, dict)
            or usb.get("accepted") is not True
            or usb.get("exact") is not True
            or not modules["journal"].exact_typed_equal(
                full.get("android_identity"), semantic.get("android_identity")
            )
            or not isinstance(full.get("android_health_sha256"), str)
            or HEX64_RE.fullmatch(full["android_health_sha256"]) is None
        ):
            raise ExecutionError("candidate observation full receipt differs")
        return
    if operation == "final-resident-health":
        root = full.get("root")
        if (
            not isinstance(root, dict)
            or not modules["journal"].exact_typed_equal(
                full.get("identity"), semantic.get("identity")
            )
            or full.get("android_health_sha256")
            != semantic.get("android_health_sha256")
            or root.get("output_sha256") != semantic.get("root_output_sha256")
            or root.get("attempts") != semantic.get("root_attempts")
            or root.get("root_verified") is not True
        ):
            raise ExecutionError("final health full receipt differs")


def _require_existing_result(
    journal: Any, path: Path, fields: dict[str, Any], label: str
) -> None:
    require_active()
    existing = journal.read_exact_json(path, label)
    for key, expected in fields.items():
        if key not in existing or not journal.exact_typed_equal(existing[key], expected):
            raise ExecutionError(f"{label} differs from durable backend evidence")


def derive_initial_download_result(run_dir: Path) -> dict[str, Any]:
    require_active()
    modules = load_sources()
    derived = derive_backend_return(run_dir, "initial-download-reboot")
    if derived["state"] != "complete":
        return derived
    value = modules["integration"]._reboot_result(
        modules["journal"], derived["semantic"], "initial"
    )
    _require_effect_receipt_binding(
        modules, "initial-download-reboot", derived
    )
    if not os.path.lexists(run_dir / "initial-download-result.json"):
        modules["journal"].record_initial_download_result(
            run_dir, value["outcome"], value["raw_receipt"]
        )
    else:
        _require_existing_result(
            modules["journal"],
            run_dir / "initial-download-result.json",
            {"outcome": value["outcome"], "raw_receipt": value["raw_receipt"]},
            "initial Download result",
        )
    return derived


def derive_initial_download_observation(run_dir: Path) -> dict[str, Any]:
    require_active()
    modules = load_sources()
    derived = derive_backend_return(run_dir, "initial-download-observation")
    if derived["state"] != "complete":
        return derived
    value = modules["integration"]._download(
        modules["journal"], derived["semantic"], "initial"
    )
    _require_read_receipt_binding(
        modules, "initial-download-observation", derived
    )
    if not os.path.lexists(run_dir / "initial-download-observation.json"):
        modules["journal"].record_initial_download_observation(
            run_dir, value["endpoint"], value["arrival_listing_sha256"]
        )
    else:
        _require_existing_result(
            modules["journal"],
            run_dir / "initial-download-observation.json",
            {
                "endpoint": value["endpoint"],
                "arrival_listing_sha256": value["arrival_listing_sha256"],
            },
            "initial Download observation",
        )
    return derived


def derive_transfer_result(run_dir: Path, kind: str) -> dict[str, Any]:
    require_active()
    if kind not in {"candidate", "rollback"}:
        raise ExecutionError("unknown transfer kind")
    operation = f"{kind}-transfer"
    modules = load_sources()
    derived = derive_backend_return(run_dir, operation)
    if derived["state"] != "complete":
        return derived
    value = modules["integration"]._transfer_result(
        modules["journal"], derived["semantic"], kind
    )
    _require_effect_receipt_binding(modules, operation, derived)
    result_path = run_dir / f"{kind}-result.json"
    if not os.path.lexists(result_path):
        modules["journal"].record_transfer_result(
            run_dir, kind, value["classification"], value["raw_receipt"]
        )
    else:
        _require_existing_result(
            modules["journal"],
            result_path,
            {
                "classification": value["classification"],
                "raw_receipt": value["raw_receipt"],
            },
            f"{kind} result",
        )
    return derived


def derive_candidate_observation(run_dir: Path) -> dict[str, Any]:
    require_active()
    modules = load_sources()
    derived = derive_backend_return(run_dir, "candidate-observation")
    if derived["state"] != "complete":
        return derived
    value = modules["integration"]._candidate_observation(
        modules["journal"], derived["semantic"]
    )
    _require_read_receipt_binding(modules, "candidate-observation", derived)
    if not os.path.lexists(run_dir / "candidate-observation.json"):
        modules["journal"].record_candidate_observation(run_dir, **value)
    else:
        _require_existing_result(
            modules["journal"],
            run_dir / "candidate-observation.json",
            value,
            "candidate observation",
        )
    return derived


def derive_rollback_download_result(run_dir: Path) -> dict[str, Any]:
    require_active()
    modules = load_sources()
    derived = derive_backend_return(run_dir, "rollback-download-reboot")
    if derived["state"] != "complete":
        return derived
    value = modules["integration"]._reboot_result(
        modules["journal"], derived["semantic"], "rollback"
    )
    _require_effect_receipt_binding(
        modules, "rollback-download-reboot", derived
    )
    if not os.path.lexists(run_dir / "rollback-mode-result.json"):
        modules["journal"].record_rollback_mode_result(
            run_dir, value["outcome"], value["raw_receipt"]
        )
    else:
        _require_existing_result(
            modules["journal"],
            run_dir / "rollback-mode-result.json",
            {"outcome": value["outcome"], "raw_receipt": value["raw_receipt"]},
            "rollback mode result",
        )
    return derived


def derive_rollback_download_observation(run_dir: Path) -> dict[str, Any]:
    require_active()
    modules = load_sources()
    derived = derive_backend_return(run_dir, "rollback-download-observation")
    if derived["state"] != "complete":
        return derived
    value = modules["integration"]._download(
        modules["journal"], derived["semantic"], "rollback"
    )
    _require_read_receipt_binding(
        modules, "rollback-download-observation", derived
    )
    if not os.path.lexists(run_dir / "rollback-mode-observation.json"):
        modules["journal"].record_rollback_mode_observation(
            run_dir, value["endpoint"]
        )
    else:
        _require_existing_result(
            modules["journal"],
            run_dir / "rollback-mode-observation.json",
            {"endpoint": value["endpoint"]},
            "rollback mode observation",
        )
    return derived


def derive_final_health(run_dir: Path) -> dict[str, Any]:
    require_active()
    modules = load_sources()
    derived = derive_backend_return(run_dir, "final-resident-health")
    if derived["state"] != "complete":
        return derived
    value = modules["integration"]._health(
        modules["journal"], derived["semantic"]
    )
    _require_read_receipt_binding(modules, "final-resident-health", derived)
    if not os.path.lexists(run_dir / "final-health.json"):
        modules["journal"].record_final_health(run_dir, value)
    else:
        _require_existing_result(
            modules["journal"],
            run_dir / "final-health.json",
            {"health_receipt": value},
            "final health",
        )
    return derived


def render_plan() -> dict[str, Any]:
    binding = current_binding()
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "active": EXECUTION_ACTIVE,
        "live_authority": False,
        "binding_sha256": digest(binding),
        "binding": binding,
        "cli": ["--render-plan"],
        "device_commands": [],
        "partition_transfers": [],
        "backend_exposed": False,
        "integrated_live_consumer": False,
        "physical_entry_bridge": False,
        "result_derivation_without_replay": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-plan", action="store_true")
    arguments = parser.parse_args()
    if not arguments.render_plan:
        parser.error("only --render-plan is available")
    print(json.dumps(render_plan(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

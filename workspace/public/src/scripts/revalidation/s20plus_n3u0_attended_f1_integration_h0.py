#!/usr/bin/env python3
"""Dormant H0 consumer-integration harness for S20+ N3-U0 attended F1."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import types
from pathlib import Path
from typing import Any, Protocol


ROOT = Path(__file__).resolve().parents[5]
SCHEMA = "s20plus_g986n_n3u0_attended_f1_integration_h0_v1"
STATUS = "H0_CONSUMER_INTEGRATION_PASS_GO_NOT_ACTIVE"
INTEGRATION_ACTIVE = False
EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256 = "efbbc9c0640ffa531ed4c9416c46683904212bde094c1cfbe535a7eebc2560ab"
MAX_SOURCE_BYTES = 2 * 1024 * 1024

TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "build": "G986NKSS8IYC2",
}

JOURNAL_BINDING_SHA256 = (
    "4695acca5c8d618eee7e16aaf665cbf66235a5a76aadc0a4322f490113cc2945"
)
CLOSURE = {
    "journal": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_n3u0_attended_f1.py",
        "size": 55_803,
        "sha256": "2c4d7335211ade6c25540782148f44c309da6373d8ad495a5904d43714a01e86",
    },
    "android_download_odin_root": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_g986n_magisk_bootstrap_f1.py",
        "size": 161_259,
        "sha256": "11ca8aaef183e76c6eeec1a43e75b00bbc14e4b51650e3122c8f4bbdfdc8799f",
    },
    "n3u0_usb_observer": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_n3u0_usb_observer.py",
        "size": 16_713,
        "sha256": "f1c6af4123684be1122950442472de7803995345e125955322a8fd262b25e44f",
    },
    "odin_classifier": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/device_action_f1_v2.py",
        "size": 80_851,
        "sha256": "4e61a7511cc2ed103d1cac4d1afdd2c91d6edc41e30d9bc2832229286d9ee290",
    },
}

HEX64_RE = re.compile(r"[0-9a-f]{64}")


class IntegrationError(RuntimeError):
    pass


class ConsumerBackend(Protocol):
    """Fixed reviewed consumer surface; callers supply no command or path."""

    def preflight(self) -> dict[str, Any]: ...

    def download_baseline(self, phase: str) -> str: ...

    def reboot_download(
        self, phase: str, source_identity: dict[str, str]
    ) -> dict[str, Any]: ...

    def observe_download(self, phase: str) -> dict[str, Any]: ...

    def transfer_boot(
        self, kind: str, endpoint: dict[str, str]
    ) -> dict[str, Any]: ...

    def observe_candidate(self) -> dict[str, Any]: ...

    def physical_download_entry(self) -> None: ...

    def final_resident_health(self) -> dict[str, Any]: ...


def canonical_bytes(value: Any) -> bytes:
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


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_exact_source(path: Path, expected: dict[str, Any], label: str) -> bytes:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as exc:
        raise IntegrationError(f"{label} is unavailable") from exc
    try:
        info = os.fstat(descriptor)
        size = expected["size"]
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or type(size) is not int
            or not 0 <= size <= MAX_SOURCE_BYTES
            or info.st_size != size
        ):
            raise IntegrationError(f"{label} identity differs")
        payload = bytearray()
        while len(payload) < size:
            block = os.read(descriptor, min(1024 * 1024, size - len(payload)))
            if not block:
                break
            payload.extend(block)
        if len(payload) != size or os.read(descriptor, 1):
            raise IntegrationError(f"{label} length differs")
    finally:
        os.close(descriptor)
    result = bytes(payload)
    if hashlib.sha256(result).hexdigest() != expected["sha256"]:
        raise IntegrationError(f"{label} hash differs")
    return result


def source_receipts() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name, expected in CLOSURE.items():
        read_exact_source(expected["path"], expected, f"N3-U0 {name}")
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
        raise IntegrationError("integration runner is unavailable") from exc
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or not 0 < info.st_size <= MAX_SOURCE_BYTES
        ):
            raise IntegrationError("integration runner identity differs")
        data = bytearray()
        while len(data) < info.st_size:
            block = os.read(descriptor, min(1024 * 1024, info.st_size - len(data)))
            if not block:
                break
            data.extend(block)
        if len(data) != info.st_size or os.read(descriptor, 1):
            raise IntegrationError("integration runner length differs")
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
        raise IntegrationError("integration runner normalized identity differs")
    return {
        "path": str(path),
        "size": len(payload),
        "normalized_sha256": normalized_sha256,
    }


def _load_exact(expected: dict[str, Any], name: str) -> Any:
    path = expected["path"]
    payload = read_exact_source(path, expected, name)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(payload, str(path), "exec"), module.__dict__)
    return module


def load_journal() -> Any:
    expected = CLOSURE["journal"]
    journal = _load_exact(expected, "s20plus_n3u0_attended_f1_bound")
    if journal.binding_sha256() != JOURNAL_BINDING_SHA256:
        raise IntegrationError("journal binding differs")
    if journal.F1_ACTIVE is not False:
        raise IntegrationError("journal unexpectedly exposes live authority")
    return journal


def current_binding() -> dict[str, Any]:
    journal = load_journal()
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "target": dict(TARGET),
        "runner": self_receipt(),
        "journal_binding_sha256": JOURNAL_BINDING_SHA256,
        "journal_status": journal.STATUS,
        "closure": source_receipts(),
        "consumer_map": {
            "android_health_and_root": "android_download_odin_root",
            "download_enumeration_and_reboot": "android_download_odin_root",
            "boot_only_odin": "android_download_odin_root+odin_classifier",
            "candidate_banner": "n3u0_usb_observer",
        },
        "effect_budget": {
            "initial_download_reboots": 1,
            "candidate_boot_transfers": 1,
            "automatic_rollback_reboots": 1,
            "physical_rollback_entries": 1,
            "resident_rollback_boot_transfers": 1,
        },
    }


def binding_sha256() -> str:
    return digest(current_binding())


def require_active() -> None:
    if INTEGRATION_ACTIVE is not True:
        raise IntegrationError("N3-U0 consumer integration is not active")


def _hex(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise IntegrationError(f"{label} is malformed")
    return value


def _identity(journal: Any, value: Any, label: str) -> dict[str, str]:
    try:
        return journal.validate_identity(value, label)
    except Exception as exc:
        raise IntegrationError(f"{label} is malformed") from exc


def _endpoint(journal: Any, value: Any, label: str) -> dict[str, str]:
    try:
        return journal.validate_endpoint(value, label)
    except Exception as exc:
        raise IntegrationError(f"{label} is malformed") from exc


def _raw(journal: Any, value: Any, label: str) -> dict[str, Any]:
    try:
        return journal.validate_raw_receipt(value, label)
    except Exception as exc:
        raise IntegrationError(f"{label} is malformed") from exc


def _preflight(journal: Any, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "identity",
        "empty_download_baseline_sha256",
    }:
        raise IntegrationError("preflight receipt is malformed")
    return {
        "identity": _identity(journal, value["identity"], "preflight identity"),
        "empty_download_baseline_sha256": _hex(
            value["empty_download_baseline_sha256"], "preflight baseline"
        ),
    }


def _reboot_result(journal: Any, value: Any, phase: str) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != {"phase", "outcome", "raw_receipt"}
        or value.get("phase") != phase
        or value.get("outcome") not in ("dispatched", "uncertain")
    ):
        raise IntegrationError(f"{phase} reboot receipt is malformed")
    return {
        "phase": phase,
        "outcome": value["outcome"],
        "raw_receipt": _raw(journal, value["raw_receipt"], f"{phase} reboot raw"),
    }


def _download(journal: Any, value: Any, phase: str) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != {"phase", "endpoint", "arrival_listing_sha256"}
        or value.get("phase") != phase
    ):
        raise IntegrationError(f"{phase} Download observation is malformed")
    return {
        "phase": phase,
        "endpoint": _endpoint(journal, value["endpoint"], f"{phase} endpoint"),
        "arrival_listing_sha256": _hex(
            value["arrival_listing_sha256"], f"{phase} arrival listing"
        ),
    }


def _transfer_result(journal: Any, value: Any, kind: str) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != {"kind", "classification", "raw_receipt"}
        or value.get("kind") != kind
        or value.get("classification")
        not in (
            "odin_transfer_completed",
            "odin_device_session_failure_or_unknown",
            "local_parse_failure",
        )
    ):
        raise IntegrationError(f"{kind} transfer receipt is malformed")
    return {
        "kind": kind,
        "classification": value["classification"],
        "raw_receipt": _raw(journal, value["raw_receipt"], f"{kind} raw"),
    }


def _candidate_observation(journal: Any, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "banner_accepted",
        "android_identity",
    }:
        raise IntegrationError("candidate observation is malformed")
    if type(value["banner_accepted"]) is not bool:
        raise IntegrationError("candidate banner state is malformed")
    identity = value["android_identity"]
    return {
        "banner_accepted": value["banner_accepted"],
        "android_identity": (
            None
            if identity is None
            else _identity(journal, identity, "candidate Android identity")
        ),
    }


def _health(journal: Any, value: Any) -> dict[str, Any]:
    try:
        return journal.validate_final_health_receipt(value)
    except Exception as exc:
        raise IntegrationError("final resident health is malformed") from exc


def prepare(runs_root: Path, backend: ConsumerBackend) -> Path:
    require_active()
    if os.path.lexists(runs_root / "active.json"):
        raise IntegrationError("an unresolved N3-U0 guard already exists")
    journal = load_journal()
    receipt = _preflight(journal, backend.preflight())
    return journal.create_prepared(
        runs_root,
        receipt["identity"],
        receipt["empty_download_baseline_sha256"],
    )


def enter_initial_download(run_dir: Path, backend: ConsumerBackend) -> str:
    require_active()
    journal = load_journal()
    prepared = journal.read_prepared(run_dir)
    journal.begin_initial_download(run_dir)
    result = _reboot_result(
        journal,
        backend.reboot_download("initial", prepared["prepared_identity"]),
        "initial",
    )
    journal.record_initial_download_result(
        run_dir, result["outcome"], result["raw_receipt"]
    )
    if result["outcome"] != "dispatched":
        raise IntegrationError("initial Download dispatch is uncertain; no replay")
    observed = _download(journal, backend.observe_download("initial"), "initial")
    journal.record_initial_download_observation(
        run_dir, observed["endpoint"], observed["arrival_listing_sha256"]
    )
    return journal.approval_token(run_dir)


def transfer_candidate(
    run_dir: Path, approval: str, backend: ConsumerBackend
) -> dict[str, Any]:
    require_active()
    journal = load_journal()
    journal.validate_legal_prefix(run_dir)
    if os.path.lexists(run_dir / "candidate-intent.json"):
        raise IntegrationError("candidate-transfer intent already exists; replay forbidden")
    current = _download(journal, backend.observe_download("candidate"), "candidate")
    journal.begin_candidate(run_dir, approval, current["endpoint"])
    result = _transfer_result(
        journal,
        backend.transfer_boot("candidate", current["endpoint"]),
        "candidate",
    )
    journal.record_transfer_result(
        run_dir,
        "candidate",
        result["classification"],
        result["raw_receipt"],
    )
    observed = _candidate_observation(journal, backend.observe_candidate())
    journal.record_candidate_observation(run_dir, **observed)
    return observed


def _transfer_rollback(run_dir: Path, backend: ConsumerBackend) -> dict[str, Any]:
    require_active()
    journal = load_journal()
    intent = journal.begin_rollback(run_dir)
    result = _transfer_result(
        journal, backend.transfer_boot("rollback", intent["endpoint"]), "rollback"
    )
    journal.record_transfer_result(
        run_dir,
        "rollback",
        result["classification"],
        result["raw_receipt"],
    )
    return result


def automatic_rollback(run_dir: Path, backend: ConsumerBackend) -> dict[str, Any]:
    require_active()
    journal = load_journal()
    journal.validate_legal_prefix(run_dir)
    observation = journal.read_exact_json(
        run_dir / "candidate-observation.json", "candidate observation"
    )
    source_identity = _identity(
        journal, observation.get("android_identity"), "automatic rollback source"
    )
    journal.begin_rollback_mode(run_dir)
    reboot = _reboot_result(
        journal,
        backend.reboot_download("rollback", source_identity),
        "rollback",
    )
    journal.record_rollback_mode_result(
        run_dir, reboot["outcome"], reboot["raw_receipt"]
    )
    if reboot["outcome"] != "dispatched":
        raise IntegrationError("rollback-mode dispatch is uncertain; no replay")
    observed = _download(journal, backend.observe_download("rollback"), "rollback")
    journal.record_rollback_mode_observation(run_dir, observed["endpoint"])
    return _transfer_rollback(run_dir, backend)


def physical_rollback(run_dir: Path, backend: ConsumerBackend) -> dict[str, Any]:
    require_active()
    journal = load_journal()
    journal.validate_legal_prefix(run_dir)
    if os.path.lexists(run_dir / "physical-rollback-intent.json"):
        raise IntegrationError("physical rollback intent already exists; replay forbidden")
    if os.path.lexists(run_dir / "rollback-mode-intent.json"):
        raise IntegrationError("automatic rollback branch already owns recovery")
    if not os.path.lexists(run_dir / "candidate-intent.json"):
        raise IntegrationError("physical rollback requires consumed candidate intent")
    baseline = _hex(backend.download_baseline("physical"), "physical baseline")
    journal.begin_physical_rollback(run_dir, baseline)
    backend.physical_download_entry()
    observed = _download(journal, backend.observe_download("physical"), "physical")
    journal.record_physical_arrival(
        run_dir, observed["endpoint"], observed["arrival_listing_sha256"]
    )
    return _transfer_rollback(run_dir, backend)


def finalize_resident(run_dir: Path, backend: ConsumerBackend) -> dict[str, Any]:
    require_active()
    journal = load_journal()
    if os.path.lexists(run_dir / "terminal-result.json"):
        journal.validate_legal_prefix(run_dir, require_active_guard=False)
        return journal.finalize(run_dir)
    journal.validate_legal_prefix(run_dir)
    if os.path.lexists(run_dir / "final-health.json"):
        return journal.finalize(run_dir)
    if not os.path.lexists(run_dir / "rollback-result.json"):
        raise IntegrationError("final health lacks rollback result")
    rollback = journal.read_exact_json(
        run_dir / "rollback-result.json", "rollback result"
    )
    if rollback.get("classification") != "odin_transfer_completed":
        raise IntegrationError("final health requires completed resident rollback")
    health = _health(journal, backend.final_resident_health())
    journal.record_final_health(run_dir, health)
    return journal.finalize(run_dir)


def render_plan() -> dict[str, Any]:
    binding = current_binding()
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "active": INTEGRATION_ACTIVE,
        "live_authority": False,
        "binding_sha256": digest(binding),
        "binding": binding,
        "cli": ["--render-plan"],
        "device_commands": [],
        "partition_transfers": [],
        "backend_exposed": False,
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

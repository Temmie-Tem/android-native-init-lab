#!/usr/bin/env python3
"""Host-only P3.19 Process-v2 integration qualification.

This orchestrator consumes the current result-contract arming output, the
independent experiment-executability closure, and the prerequisite audit.  It
does not create a ready/run/approval manifest and never contacts a device.
Missing prerequisites, a stale candidate pin, a missing fresh baseline, or a
missing global consumed-candidate registry remain explicit H0 blockers.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
PRIVATE = ROOT / "workspace/private"
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
ADAPTER = SCRIPT_DIR / "s22plus_fyg8_p319_stock_process_v2_adapter.py"
EXECUTABILITY = SCRIPT_DIR / "s22plus_fyg8_p319_experiment_executability_closure.py"
PREREQUISITE = SCRIPT_DIR / "s22plus_fyg8_p319_process_v2_prerequisite_audit.py"
CANDIDATE_QUALIFICATION = SCRIPT_DIR / "s22plus_fyg8_p319_candidate_qualification.py"
INTENT = PRIVATE / (
    "outputs/s22plus_fyg8_p319/candidate-qualification-v1-20260821-08/intent.json"
)
FRESH_BASELINE = PRIVATE / (
    "outputs/s22plus_fyg8_p319/fresh-baseline-v1/result.json"
)
CONSUMED_CANDIDATE_REGISTRY = PRIVATE / "consumed-run-registry.json"
PROCESS_CONTRACT = ROOT / "docs/operations/DEVICE_ACTION_PROCESS_V2.md"

SCHEMA = "s22plus_fyg8_p319_process_v2_integration_qualification_v1"
BLOCKED_VERDICT = "BLOCKED_P319_PROCESS_V2_INTEGRATION_H0"
NOT_READY_VERDICT = "NOT_READY_P319_RUNTIME_CLASSIFICATION_PENDING_H0"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
PROOF_CLASSES = {
    "NONCAUSAL_SUCCESS_PATH",
    "NO_PROOF_EXPERIMENT_PRECONDITION",
    "NO_PROOF_OBSERVER",
}


class IntegrationAuditError(ValueError):
    """The H0 integration receipt cannot be trusted."""


def _canonical(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("ascii")
            + b"\n"
        )
    except (TypeError, ValueError) as exc:
        raise IntegrationAuditError("integration value is not canonical JSON") from exc


def _identity(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _stable_bytes(
    path: Path,
    label: str,
    *,
    maximum: int = 2 * 1024 * 1024,
    mode: int | None = None,
    nlink: int | None = None,
) -> bytes:
    try:
        before = path.lstat()
    except OSError as exc:
        raise IntegrationAuditError(f"{label} is unavailable") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise IntegrationAuditError(f"{label} is not a direct regular file")
    if mode is not None and stat.S_IMODE(before.st_mode) != mode:
        raise IntegrationAuditError(f"{label} mode differs")
    if nlink is not None and before.st_nlink != nlink:
        raise IntegrationAuditError(f"{label} link count differs")
    if before.st_size > maximum:
        raise IntegrationAuditError(f"{label} exceeds the bounded read")
    try:
        with path.open("rb") as stream:
            data = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
    except OSError as exc:
        raise IntegrationAuditError(f"{label} cannot be read") from exc
    after = path.lstat()
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_inside = (inside.st_dev, inside.st_ino, inside.st_size, inside.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if len(data) != before.st_size or len(data) > maximum:
        raise IntegrationAuditError(f"{label} size changed while reading")
    if identity_before != identity_inside or identity_before != identity_after:
        raise IntegrationAuditError(f"{label} changed while reading")
    return data


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise IntegrationAuditError("duplicate JSON key in integration input")
        result[key] = value
    return result


def _json_receipt(path: Path, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    data = _stable_bytes(path, label, mode=0o400, nlink=1)
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                IntegrationAuditError(f"{label} contains non-finite JSON")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntegrationAuditError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict) or data != _canonical(value):
        raise IntegrationAuditError(f"{label} is not canonical JSON")
    return value, {"path": _relative(path), **_identity(data)}


def _load_local(path: Path, name: str) -> Any:
    if not path.is_file() or path.is_symlink():
        raise IntegrationAuditError(f"{name} source is unavailable")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise IntegrationAuditError(f"{name} source cannot be loaded")
    old_path = list(sys.path)
    sys.path.insert(0, str(path.parent))
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as exc:
        raise IntegrationAuditError(f"{name} source failed to load: {type(exc).__name__}") from exc
    finally:
        sys.path[:] = old_path


def _summary(name: str, value: Mapping[str, Any]) -> dict[str, Any]:
    encoded = _canonical(dict(value))
    return {
        "name": name,
        "schema": value.get("schema"),
        "verdict": value.get("verdict"),
        "status": value.get("status"),
        "identity": _identity(encoded),
    }


def _projection_view(value: Mapping[str, Any]) -> dict[str, Any]:
    """Preserve prerequisite-owned projection/census policy without guessing fields."""
    found: dict[str, Any] = {}

    def visit(current: Any, prefix: str) -> None:
        if isinstance(current, dict):
            for key in sorted(current):
                child = f"{prefix}.{key}" if prefix else str(key)
                if "projection" in str(key).lower() or "census" in str(key).lower():
                    found[child] = current[key]
                visit(current[key], child)
        elif isinstance(current, list):
            for index, child_value in enumerate(current):
                visit(child_value, f"{prefix}[{index}]")

    visit(dict(value), "")
    return found


def _validate_arming(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise IntegrationAuditError("result-contract arming did not return an object")
    admitted = value.get("admitted_terminals")
    if not isinstance(admitted, list) or value.get("admitted_terminal_count") != len(admitted):
        raise IntegrationAuditError("result-contract admitted terminal output is malformed")
    rows: list[dict[str, Any]] = []
    details: set[int] = set()
    states: set[str] = set()
    classes: set[str] = set()
    for item in admitted:
        if not isinstance(item, dict):
            raise IntegrationAuditError("result-contract admitted row is not an object")
        detail, state, proof = item.get("terminal_detail"), item.get("state"), item.get("proof_class")
        if not isinstance(detail, int) or not isinstance(state, str) or not isinstance(proof, str):
            raise IntegrationAuditError("result-contract admitted row is not typed")
        if detail in details or state in states:
            raise IntegrationAuditError("result-contract admitted row is duplicated")
        details.add(detail)
        states.add(state)
        classes.add(proof)
        rows.append(dict(item))
    if classes != PROOF_CLASSES:
        raise IntegrationAuditError("result-contract proof classes are not three distinct classes")
    if value.get("causal_result_allowed") is not False or value.get("candidate_success") is not False:
        raise IntegrationAuditError("result-contract arming exposed causal authority")
    if value.get("device_contact") is not False:
        raise IntegrationAuditError("result-contract arming contacted a device")
    return {
        **_summary("result_contract_arming", value),
        "admitted_terminals": rows,
        "admitted_terminal_count": len(rows),
        "admitted_digest": _identity(_canonical(rows))["sha256"],
        "proof_classes": sorted(classes),
        "device_contact": False,
        "causal_result_allowed": False,
        "candidate_success": False,
    }


def _run_arming() -> dict[str, Any]:
    module = _load_local(ADAPTER, "P3.19 adapter")
    fn = getattr(module, "audit_result_contract_arming", None)
    if not callable(fn):
        raise IntegrationAuditError("P3.19 adapter lacks result-contract arming API")
    try:
        value = fn()
    except Exception as exc:
        raise IntegrationAuditError(
            f"P3.19 result-contract arming raised {type(exc).__name__}"
        ) from exc
    return _validate_arming(value)


def _run_executability() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    module = _load_local(EXECUTABILITY, "P3.19 executability closure")
    fn = getattr(module, "build_result", None)
    if not callable(fn):
        raise IntegrationAuditError("P3.19 executability closure lacks build_result API")
    try:
        value = fn()
    except Exception as exc:
        raise IntegrationAuditError(
            f"P3.19 executability closure raised {type(exc).__name__}"
        ) from exc
    if not isinstance(value, dict):
        raise IntegrationAuditError("P3.19 executability closure returned a non-object")
    source_pass = (
        value.get("verdict") == "PASS_P319_EXPERIMENT_EXECUTABILITY_CLOSURE_H0"
        and value.get("status") == "PASS_SOURCE_CLOSURE_RUNTIME_GATES_PENDING"
    )
    witnesses = value.get("runtime_evaluability_witnesses") or {}
    if not isinstance(witnesses, dict):
        raise IntegrationAuditError("P3.19 executability runtime witness shape differs")
    pending = any(
        isinstance(item, dict) and item.get("status") == "PENDING_FRESH_CANDIDATE_RUN"
        for item in witnesses.values()
    )
    blockers: list[dict[str, Any]] = []
    if not source_pass:
        blockers.append({"code": "EXECUTABILITY_SOURCE_CLOSURE_BLOCKED", "detail": "source closure did not pass"})
    scope = value.get("scope") or {}
    if not isinstance(scope, dict):
        raise IntegrationAuditError("P3.19 executability scope shape differs")
    if value.get("device_contact") is not False or scope.get("device_contact") is not False:
        blockers.append({"code": "EXECUTABILITY_DEVICE_CONTACT", "detail": "executability closure scope is not host-only"})
    return {
        **_summary("experiment_executability", value),
        "source_closure_pass": source_pass,
        "runtime_classification_gate_pending": pending,
        "runtime_evaluability_witnesses": witnesses,
        "device_contact": False,
        "causal_result_allowed": False,
        "candidate_success": False,
    }, blockers


def _run_prerequisite() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not PREREQUISITE.is_file() or PREREQUISITE.is_symlink():
        return (
            {"name": "prerequisite_audit", "status": "BLOCKED_MISSING_SOURCE", "path": _relative(PREREQUISITE)},
            [{"code": "PREREQUISITE_AUDIT_MISSING", "detail": "prerequisite audit source is not present"}],
        )
    module = _load_local(PREREQUISITE, "P3.19 prerequisite audit")
    api_name = "build_result"
    fn = getattr(module, api_name, None)
    if not callable(fn):
        for candidate in ("build_receipt", "audit", "audit_prerequisites", "run_audit"):
            if callable(getattr(module, candidate, None)):
                api_name, fn = candidate, getattr(module, candidate)
                break
    if not callable(fn):
        return (
            {"name": "prerequisite_audit", "status": "BLOCKED_API_MISSING", "api": api_name},
            [{"code": "PREREQUISITE_API_BLOCKED", "detail": "no clear prerequisite audit API"}],
        )
    try:
        value = fn()
    except Exception as exc:
        return (
            {"name": "prerequisite_audit", "status": "BLOCKED_EXECUTION", "api": api_name},
            [{"code": "PREREQUISITE_BLOCKED", "detail": f"audit raised {type(exc).__name__}"}],
        )
    if not isinstance(value, dict):
        return (
            {"name": "prerequisite_audit", "status": "BLOCKED_SCHEMA", "api": api_name},
            [{"code": "PREREQUISITE_BLOCKED", "detail": "audit returned a non-object"}],
        )
    blocked = "BLOCKED" in str(value.get("verdict", "")) or "BLOCKED" in str(value.get("status", ""))
    owned_blockers: list[dict[str, Any]] = []
    declared_blockers = value.get("blockers")
    if isinstance(declared_blockers, list):
        owned_blockers = [
            {"code": item["code"], "detail": item.get("detail", "prerequisite audit blocker")}
            for item in declared_blockers
            if isinstance(item, dict) and isinstance(item.get("code"), str)
        ]
    global_blocker = value.get("global_registry_blocker")
    if isinstance(global_blocker, str):
        owned_blockers.append({"code": global_blocker, "detail": "prerequisite audit global registry result"})
    no_replay = value.get("no_replay")
    global_registry = no_replay.get("global_consumed_run_registry", {}) if isinstance(no_replay, dict) else {}
    component = {
        **_summary("prerequisite_audit", value),
        "api": api_name,
        "projection_policy": _projection_view(value),
        "recovery_usability_provenance": value.get("recovery_usability_provenance"),
        "no_replay": no_replay,
        "restart_durability": value.get("restart_durability"),
        "raw_first_execution_closure": value.get("raw_first_execution_closure"),
        "global_registry_proof": global_registry,
        "global_registry_authoritative": (
            global_registry.get("present") is True
            and global_registry.get("runner_consumes_it") is True
            and global_registry.get("authoritative") is True
        ),
    }
    if blocked:
        return (
            component,
            owned_blockers or [{"code": "PREREQUISITE_BLOCKED", "detail": "prerequisite audit is blocked"}],
        )
    scope = value.get("scope") or {}
    if not isinstance(scope, dict):
        return component, [{"code": "PREREQUISITE_BLOCKED", "detail": "prerequisite scope shape differs"}]
    if value.get("device_contact") is True or scope.get("device_contact") is True:
        return (
            component,
            [{"code": "PREREQUISITE_DEVICE_CONTACT", "detail": "prerequisite audit is not host-only"}],
        )
    return component, []


REQUIRED_ARMING_SOURCE_KEY = "adapter_closure:s22plus_fyg8_p319_result_contract_arming.py"


def _source_key_summary(source_keys: Mapping[str, Any]) -> dict[str, Any]:
    """Digest the complete candidate qualifier SOURCE_KEYS authority."""
    keys = sorted(str(key) for key in source_keys)
    return {
        "count": len(keys),
        "digest": _identity(_canonical(dict(source_keys)))["sha256"],
        "keys": keys,
    }


def _source_key_comparison(
    pinned: Mapping[str, Any], current: Mapping[str, Any]
) -> dict[str, Any]:
    pinned_summary = _source_key_summary(pinned)
    current_summary = _source_key_summary(current)
    mismatch_keys = sorted(
        key for key in set(pinned) | set(current)
        if pinned.get(key) != current.get(key)
    )
    return {
        "pinned": pinned_summary,
        "current": current_summary,
        "pinned_digest": pinned_summary["digest"],
        "current_digest": current_summary["digest"],
        "mismatch_count": len(mismatch_keys),
        "mismatch_keys": mismatch_keys,
        "exact_match": not mismatch_keys,
        "required_arming_source_key": REQUIRED_ARMING_SOURCE_KEY,
        "required_arming_key_present_pinned": REQUIRED_ARMING_SOURCE_KEY in pinned,
        "required_arming_key_present_current": REQUIRED_ARMING_SOURCE_KEY in current,
    }


def _adapter_pin() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        intent, intent_identity = _json_receipt(INTENT, "candidate qualification intent")
        pinned_source_keys = intent["source_keys"]
        if not isinstance(pinned_source_keys, dict):
            raise IntegrationAuditError("candidate intent SOURCE_KEYS is not an object")
        pin = pinned_source_keys["adapter"]
        if not isinstance(pin, dict):
            raise IntegrationAuditError("candidate intent adapter pin is not an object")
        if pin.get("logical_path") != _relative(ADAPTER):
            raise IntegrationAuditError("candidate intent adapter logical path differs")
        current_data = _stable_bytes(ADAPTER, "current P3.19 adapter", maximum=512 * 1024)
        current = _identity(current_data)
        pinned = {"size": pin.get("size"), "sha256": pin.get("sha256")}

        qualifier = _load_local(CANDIDATE_QUALIFICATION, "P3.19 candidate qualification")
        source_keys_fn = getattr(qualifier, "_source_keys", None)
        if not callable(source_keys_fn):
            raise IntegrationAuditError("candidate qualification lacks _source_keys authority")
        current_source_keys = source_keys_fn()
        if not isinstance(current_source_keys, dict):
            raise IntegrationAuditError("candidate qualification _source_keys returned a non-object")
        source_keys = _source_key_comparison(pinned_source_keys, current_source_keys)

        blockers: list[dict[str, Any]] = []
        if current != pinned:
            blockers.append({
                "code": "REQUALIFICATION_REQUIRED",
                "detail": "current adapter bytes differ from pinned qualification intent",
            })
        if source_keys["mismatch_count"]:
            blockers.append({
                "code": "REQUALIFICATION_REQUIRED",
                "detail": (
                    "candidate qualifier SOURCE_KEYS differ from pinned intent: "
                    f"{source_keys['mismatch_count']} mismatches"
                ),
            })
        if not source_keys["required_arming_key_present_current"]:
            blockers.append({
                "code": "CANDIDATE_SOURCE_CLOSURE_MISSING_ARMING",
                "detail": f"current candidate SOURCE_KEYS omit {REQUIRED_ARMING_SOURCE_KEY}",
            })
        return {
            "intent": intent_identity,
            "pinned": pinned,
            "current": current,
            "source_keys": source_keys,
        }, blockers
    except (IntegrationAuditError, KeyError, TypeError, AttributeError) as exc:
        return {"status": "BLOCKED_PIN_UNAVAILABLE"}, [{"code": "ADAPTER_PIN_BLOCKED", "detail": str(exc)}]
    except Exception as exc:
        # The candidate qualifier is an execution-critical source authority.
        # Any unexpected failure while loading or invoking it is a blocker,
        # never permission to continue with the adapter-only pin.
        return {"status": "BLOCKED_PIN_UNAVAILABLE"}, [{"code": "ADAPTER_PIN_BLOCKED", "detail": str(exc)}]


def _required_private_receipt(path: Path, label: str, schema: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        value, identity = _json_receipt(path, label)
    except IntegrationAuditError:
        return {"status": "BLOCKED_MISSING", "path": _relative(path)}, [
            {"code": "FRESH_BASELINE_MISSING" if path == FRESH_BASELINE else "CONSUMED_CANDIDATE_REGISTRY_MISSING", "detail": f"{label} is unavailable"}
        ]
    if value.get("schema") != schema:
        code = "FRESH_BASELINE_INVALID" if path == FRESH_BASELINE else "CONSUMED_CANDIDATE_REGISTRY_INVALID"
        return {"status": "BLOCKED_SCHEMA", "identity": identity}, [{"code": code, "detail": f"{label} schema differs"}]
    if path == FRESH_BASELINE:
        valid = value.get("fresh") is True and value.get("clean") is True and value.get("candidate_absent") is True and value.get("target") == TARGET and value.get("device_contact") is False
        code, detail = "FRESH_BASELINE_INVALID", "fresh baseline predicates are incomplete"
    else:
        valid = value.get("scope") == "global" and isinstance(value.get("entries"), list) and value.get("replay_forbidden") is True
        code, detail = "CONSUMED_CANDIDATE_REGISTRY_INVALID", "global consumed-candidate registry predicates are incomplete"
    return ({"status": "PRESENT" if valid else "BLOCKED_INVALID", "identity": identity}, [] if valid else [{"code": code, "detail": detail}])


def _contract_provenance() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    requirements = {
        "result_contract_arming": ("### Result-Contract Arming Precondition", ("real encoder", "real carrier representation", "real host decoder")),
        "experiment_executability": ("### Experiment Executability Closure", ("EXPERIMENT_EXECUTABILITY_CLOSURE", "must-bind consumer set")),
        "recovery": ("## Recovery", ("Rollback is a normal state-machine transition", "Do not launch a second candidate")),
    }
    try:
        data = _stable_bytes(PROCESS_CONTRACT, "Process-v2 contract", maximum=1024 * 1024)
        text = data.decode("utf-8")
    except (IntegrationAuditError, UnicodeDecodeError) as exc:
        return {}, [{"code": "CONTRACT_PROVENANCE_BLOCKED", "detail": str(exc)}]
    provenance = {"path": _relative(PROCESS_CONTRACT), **_identity(data), "sections": {}}
    normalized = " ".join(text.split())
    blockers: list[dict[str, Any]] = []
    for name, (heading, tokens) in requirements.items():
        matched = (
            " ".join(heading.split()) in normalized
            and all(" ".join(token.split()) in normalized for token in tokens)
        )
        provenance["sections"][name] = {"heading": heading, "tokens": list(tokens), "matched": matched}
        if not matched:
            blockers.append({"code": "CONTRACT_PROVENANCE_BLOCKED", "detail": f"{name} wording is incomplete"})
    return provenance, blockers


def _blocker_key(item: Mapping[str, Any]) -> tuple[str, str]:
    return str(item.get("code", "")), str(item.get("detail", ""))


def validate_result(value: Mapping[str, Any]) -> None:
    if value.get("ready") is not False or value.get("ready_manifest_created") is not False or value.get("run_manifest_created") is not False or value.get("approval_created") is not False:
        raise IntegrationAuditError("integration receipt contains a ready/run/approval claim")
    if value.get("causal_result_allowed") is not False or value.get("candidate_success") is not False or value.get("device_contact") is not False:
        raise IntegrationAuditError("integration receipt exposes forbidden authority")
    if any(value.get(key) is not False for key in ("live_authorized", "d0_authorized", "d1_authorized", "f1_authorized", "replay_authorized")):
        raise IntegrationAuditError("integration receipt exposes a live/action authority")
    scope = value.get("scope")
    if not isinstance(scope, dict) or any(scope.get(key) is not False for key in ("live_authorized", "d0_authorized", "d1_authorized", "f1_authorized", "replay_authorized")):
        raise IntegrationAuditError("integration scope is not H0-only")
    blockers = value.get("blockers")
    if not isinstance(blockers, list) or any(not isinstance(item, dict) or not item.get("code") for item in blockers):
        raise IntegrationAuditError("integration blocker list is malformed")
    if value.get("blocker_count") != len(blockers) or value.get("blocker_digest") != _identity(_canonical(blockers))["sha256"]:
        raise IntegrationAuditError("integration blocker list was changed")
    codes = {str(item["code"]) for item in blockers}
    if blockers and value.get("verdict") != BLOCKED_VERDICT:
        raise IntegrationAuditError("blocked integration verdict differs")
    if not blockers and value.get("verdict") != NOT_READY_VERDICT:
        raise IntegrationAuditError("unblocked integration verdict differs")
    components = value.get("components", {})
    if not isinstance(components, dict):
        raise IntegrationAuditError("integration components are malformed")
    if components.get("executability", {}).get("source_closure_pass") is not True and "EXECUTABILITY_SOURCE_CLOSURE_BLOCKED" not in codes:
        raise IntegrationAuditError("executability blocker was removed")
    if components.get("fresh_baseline", {}).get("status") != "PRESENT" and not ({"FRESH_BASELINE_MISSING", "FRESH_BASELINE_INVALID"} & codes):
        raise IntegrationAuditError("fresh-baseline blocker was removed")
    adapter_pin = components.get("adapter_pin", {})
    if isinstance(adapter_pin.get("pinned"), dict) and isinstance(adapter_pin.get("current"), dict) and adapter_pin["pinned"] != adapter_pin["current"] and "REQUALIFICATION_REQUIRED" not in codes:
        raise IntegrationAuditError("adapter requalification blocker was removed")
    source_keys = adapter_pin.get("source_keys")
    if not isinstance(source_keys, dict):
        if "ADAPTER_PIN_BLOCKED" not in codes:
            raise IntegrationAuditError("integration adapter SOURCE_KEYS comparison is missing")
    else:
        mismatch_keys = source_keys.get("mismatch_keys")
        mismatch_count = source_keys.get("mismatch_count")
        if not isinstance(mismatch_keys, list) or any(not isinstance(key, str) for key in mismatch_keys):
            raise IntegrationAuditError("integration adapter SOURCE_KEYS mismatch keys are malformed")
        if mismatch_count != len(mismatch_keys):
            raise IntegrationAuditError("integration adapter SOURCE_KEYS mismatch count differs")
        pinned_summary = source_keys.get("pinned")
        current_summary = source_keys.get("current")
        if not isinstance(pinned_summary, dict) or not isinstance(current_summary, dict):
            raise IntegrationAuditError("integration adapter SOURCE_KEYS summaries are malformed")
        for summary in (pinned_summary, current_summary):
            summary_keys = summary.get("keys")
            if (
                not isinstance(summary_keys, list)
                or any(not isinstance(key, str) for key in summary_keys)
            ):
                raise IntegrationAuditError("integration adapter SOURCE_KEYS summary keys are malformed")
            if summary_keys != sorted(set(summary_keys)) or summary.get("count") != len(summary_keys):
                raise IntegrationAuditError("integration adapter SOURCE_KEYS summary keys are malformed")
        if source_keys.get("pinned_digest") != pinned_summary.get("digest"):
            raise IntegrationAuditError("integration adapter pinned SOURCE_KEYS digest differs")
        if source_keys.get("current_digest") != current_summary.get("digest"):
            raise IntegrationAuditError("integration adapter current SOURCE_KEYS digest differs")
        if source_keys.get("exact_match") is not (mismatch_count == 0):
            raise IntegrationAuditError("integration adapter SOURCE_KEYS exact-match flag differs")
        if mismatch_count and "REQUALIFICATION_REQUIRED" not in codes:
            raise IntegrationAuditError("adapter SOURCE_KEYS requalification blocker was removed")
        required_arming_key = source_keys.get("required_arming_source_key")
        if required_arming_key != REQUIRED_ARMING_SOURCE_KEY:
            raise IntegrationAuditError("integration adapter SOURCE_KEYS arming key differs")
        if source_keys.get("required_arming_key_present_current") is not True and "CANDIDATE_SOURCE_CLOSURE_MISSING_ARMING" not in codes:
            raise IntegrationAuditError("candidate source-closure arming blocker was removed")
    arming = value.get("components", {}).get("arming", {})
    admitted = arming.get("admitted_terminals")
    if isinstance(admitted, list) and arming.get("admitted_digest") != _identity(_canonical(admitted))["sha256"]:
        raise IntegrationAuditError("integration admitted terminal list was changed")
    registry = components.get("consumed_candidate_registry", {})
    prerequisite = components.get("prerequisite", {})
    if registry.get("status") == "PRESENT" and prerequisite.get("global_registry_authoritative") is not True:
        raise IntegrationAuditError("registry presence lacks prerequisite runner-consumption authority")
    if prerequisite.get("global_registry_authoritative") is not True and "BLOCKED_MISSING_GLOBAL_CONSUMED_REGISTRY" not in codes:
        raise IntegrationAuditError("global registry blocker was removed")
    for key in ("ready_manifest", "run_manifest", "approval_manifest", "approval"):
        if key in value:
            raise IntegrationAuditError("integration receipt contains a forbidden manifest field")


def build_result() -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    components: dict[str, Any] = {}
    try:
        components["arming"] = _run_arming()
    except IntegrationAuditError as exc:
        components["arming"] = {"name": "result_contract_arming", "status": "BLOCKED", "error": str(exc)}
        blockers.append({"code": "RESULT_CONTRACT_ARMING_BLOCKED", "detail": str(exc)})
    try:
        components["executability"], closure_blockers = _run_executability()
        blockers.extend(closure_blockers)
    except IntegrationAuditError as exc:
        components["executability"] = {"name": "experiment_executability", "status": "BLOCKED", "error": str(exc)}
        blockers.append({"code": "EXECUTABILITY_SOURCE_CLOSURE_BLOCKED", "detail": str(exc)})
    components["prerequisite"], prerequisite_blockers = _run_prerequisite()
    blockers.extend(prerequisite_blockers)
    if components["prerequisite"].get("global_registry_authoritative") is not True:
        blockers.append({
            "code": "BLOCKED_MISSING_GLOBAL_CONSUMED_REGISTRY",
            "detail": "prerequisite runner-consumption and authoritative registry proof is absent",
        })
    components["adapter_pin"], adapter_blockers = _adapter_pin()
    blockers.extend(adapter_blockers)
    components["fresh_baseline"], baseline_blockers = _required_private_receipt(
        FRESH_BASELINE, "fresh baseline", "s22plus_fyg8_p319_fresh_baseline_v1"
    )
    blockers.extend(baseline_blockers)
    components["consumed_candidate_registry"], registry_blockers = _required_private_receipt(
        CONSUMED_CANDIDATE_REGISTRY, "global consumed-candidate registry", "s22plus_fyg8_p319_consumed_candidate_registry_v1"
    )
    blockers.extend(registry_blockers)
    if components["prerequisite"].get("global_registry_authoritative") is not True:
        if components["consumed_candidate_registry"].get("status") == "PRESENT":
            components["consumed_candidate_registry"] = {
                **components["consumed_candidate_registry"],
                "status": "BLOCKED_UNAUTHORIZED",
            }
    provenance, provenance_blockers = _contract_provenance()
    blockers.extend(provenance_blockers)
    by_code: dict[str, dict[str, Any]] = {}
    for item in sorted(blockers, key=_blocker_key):
        by_code.setdefault(str(item.get("code", "")), dict(item))
    unique_blockers = [by_code[key] for key in sorted(by_code)]
    runtime_pending = components.get("executability", {}).get("runtime_classification_gate_pending") is True
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "verdict": BLOCKED_VERDICT if unique_blockers else NOT_READY_VERDICT,
        "status": "BLOCKED_H0" if unique_blockers else "SOURCE_CLOSURE_PASS_RUNTIME_CLASSIFICATION_PENDING",
        "decision": "BLOCKED_H0" if unique_blockers else "NOT_READY_RUNTIME_CLASSIFICATION_PENDING",
        "target": TARGET,
        "blockers": unique_blockers,
        "blocker_count": len(unique_blockers),
        "blocker_digest": _identity(_canonical(unique_blockers))["sha256"],
        "components": components,
        "provenance": provenance,
        "source_closure_pass": components.get("executability", {}).get("source_closure_pass") is True,
        "runtime_classification_gate_pending": runtime_pending,
        "fresh_baseline_present": components.get("fresh_baseline", {}).get("status") == "PRESENT",
        "global_consumed_candidate_registry_present": (
            components.get("consumed_candidate_registry", {}).get("status") == "PRESENT"
            and components.get("prerequisite", {}).get("global_registry_authoritative") is True
        ),
        "ready": False,
        "ready_manifest_created": False,
        "run_manifest_created": False,
        "approval_created": False,
        "live_authorized": False,
        "d0_authorized": False,
        "d1_authorized": False,
        "f1_authorized": False,
        "replay_authorized": False,
        "causal_result_allowed": False,
        "candidate_success": False,
        "device_contact": False,
        "scope": {"tier": "H0", "host_only": True, "live_authorized": False, "d0_authorized": False, "d1_authorized": False, "f1_authorized": False, "replay_authorized": False, "approval_created": False, "device_contact": False},
    }
    validate_result(result)
    return result


def encode(value: Mapping[str, Any]) -> bytes:
    return _canonical(dict(value))


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_exclusive(path: Path, payload: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise IntegrationAuditError("refusing to clobber integration receipt")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    parent = path.parent.lstat()
    if not stat.S_ISDIR(parent.st_mode) or stat.S_IMODE(parent.st_mode) != 0o700:
        raise IntegrationAuditError("integration receipt parent is not private 0700")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o400)
    try:
        os.fchmod(descriptor, 0o400)
        offset = 0
        while offset < len(payload):
            try:
                count = os.write(descriptor, payload[offset:])
            except InterruptedError:
                continue
            if count <= 0:
                raise IntegrationAuditError("integration receipt write did not progress")
            offset += count
        os.fsync(descriptor)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o400 or info.st_nlink != 1 or info.st_size != len(payload):
            raise IntegrationAuditError("integration receipt metadata differs")
    finally:
        os.close(descriptor)
    _fsync_directory(path.parent)
    reopened = _stable_bytes(path, "published integration receipt", maximum=max(len(payload), 1), mode=0o400, nlink=1)
    if reopened != payload:
        raise IntegrationAuditError("published integration receipt changed after reopen")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=PRIVATE / "outputs/s22plus_fyg8_p319/process-v2-integration-qualification-v1-20260821-02/result.json")
    args = parser.parse_args(argv)
    result = build_result()
    publish_exclusive(args.out, encode(result))
    return 3 if result["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

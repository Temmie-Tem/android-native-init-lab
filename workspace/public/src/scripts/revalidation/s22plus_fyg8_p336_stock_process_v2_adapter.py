#!/usr/bin/env python3
"""P3.36 Process-v2 adapter over the exact P3.35 stock ABI.

P3.36 changes the host-side later-session boundary only.  The candidate keeps
the P3.35 authenticated, fixed three-command device behavior, while the new
observer performs one bounded OPEN-before-resynchronization on a freshly
rebound descriptor.  This file is deliberately a thin, isolated load of the
reviewed P3.35 adapter; it does not mutate an imported predecessor module.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import sys
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = Path(__file__).resolve().parent
SOURCE = REVALIDATION / "s22plus_fyg8_p335_stock_process_v2_adapter.py"
SOURCE_IDENTITY = {
    "size": 23_646,
    "sha256": "422a2e226892715c8af0084b3695487c360834d8f260a822305e9e25be5f3f57",
}
P335_PREDECESSOR_RUN_ID_HEX = "c335f1e0a90b5e6d7c8a9b0c1d2e3f5b"
P335_PREDECESSOR_RUN_ID = bytes.fromhex(P335_PREDECESSOR_RUN_ID_HEX)
P336_RUN_ID_HEX = "c336f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P336_RUN_ID = bytes.fromhex(P336_RUN_ID_HEX)

P336_OVERLAY_CONTRACT_ID = "s22plus-fyg8-p336-long-idle-v1"
P336_DECODER_ID = "s22plus_fyg8_p336_long_idle_v1"
P336_OBSERVER_CONTRACT_ID = (
    "s22plus-fyg8-p336-long-idle-acm-observer-v1"
)
P336_POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P336_STOCK_OBSERVER_V1|"
    "protocol=p336-long-idle-v1|"
    "initial-proof=sessions-3,same-fd,host-close-reopen-1|"
    "later-action=one-open-before-bounded-resync|"
    "commands=fixed-p335-three-commands|"
    "transport=one-open-fd-per-session|"
    "per-boot-identity=unchanged-nonzero|retry=none|"
    "usb=bidirectional-primary|run="
    + P336_RUN_ID_HEX
    + "|causal=false"
)
P336_POLICY_ID = hashlib.sha256(P336_POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]
# Compatibility labels consumed by the exact-loaded P3.35 static seam.
P335_OVERLAY_CONTRACT_ID = P336_OVERLAY_CONTRACT_ID
P335_DECODER_ID = P336_DECODER_ID
P335_OBSERVER_CONTRACT_ID = P336_OBSERVER_CONTRACT_ID
P335_POLICY_PREIMAGE = P336_POLICY_PREIMAGE
P335_POLICY_ID = P336_POLICY_ID
P334_OVERLAY_CONTRACT_ID = P336_OVERLAY_CONTRACT_ID
P333_OVERLAY_CONTRACT_ID = P336_OVERLAY_CONTRACT_ID
P332_OVERLAY_CONTRACT_ID = P336_OVERLAY_CONTRACT_ID

INITIAL_SESSION_COUNT = 3
INITIAL_RECONNECT_COUNT = 1
LEASE_DURATION_SEC = 3_600
LEASE_ACTION_CAP = 16
LEASE_SCHEMA = "s22plus_fyg8_p336_long_idle_lease_v1"


class AdapterIdentityError(ValueError):
    """The exact P3.35 adapter or fresh P3.36 binding differs."""


class ContractError(ValueError):
    """The public P3.36 contract projection is incomplete or changed."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


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


def _stable_source() -> bytes:
    direct = SOURCE.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(SOURCE_IDENTITY["size"] + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AdapterIdentityError("P3.35 adapter source is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or identity(payload) != SOURCE_IDENTITY
    ):
        raise AdapterIdentityError("P3.35 adapter source identity differs")
    return payload


def _stable(path: Path, label: str, maximum: int = 2 << 20) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AdapterIdentityError(f"{label} is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or len(payload) > maximum
    ):
        raise AdapterIdentityError(f"{label} identity differs")
    return payload


def _legacy_runtime_alias(runtime: types.ModuleType) -> types.ModuleType:
    """Provide only names needed by the exact P3.35/P3.34 parser load."""
    alias = types.ModuleType("s22plus_fyg8_p334_first_read_rc_runtime_for_p336")
    alias.__dict__.update(vars(runtime))
    alias.P334_DETAIL_PREFIX = getattr(runtime, "P334_DETAIL_PREFIX", 0xB000)
    alias.P334_DETAIL_SENTINEL = getattr(runtime, "P334_DETAIL_SENTINEL", 0xBFFF)
    if not hasattr(alias, "decode_first_read_detail"):

        def decode_first_read_detail(detail: int) -> dict[str, Any]:
            if detail == alias.P334_DETAIL_SENTINEL:
                return {"valid": False, "console_called": None, "return_code": None}
            if (
                detail & 0xF000 != alias.P334_DETAIL_PREFIX
                or detail & 0x0FFF > 4094
            ):
                raise ValueError("legacy P3.34 terminal detail differs")
            return {
                "valid": True,
                "console_called": True,
                "return_code": -(detail & 0x0FFF),
            }

        alias.decode_first_read_detail = decode_first_read_detail
    return alias


def _load_p336_inputs() -> tuple[types.ModuleType, types.ModuleType]:
    try:
        import s22plus_fyg8_p336_long_idle_runtime as runtime  # type: ignore
        import s22plus_fyg8_p336_long_idle_acm_observer as observer  # type: ignore
    except ModuleNotFoundError as exc:
        raise AdapterIdentityError("P3.36 runtime/observer sources are unavailable") from exc
    return runtime, observer


def _load_p335(runtime: types.ModuleType, observer: types.ModuleType) -> types.ModuleType:
    payload = _stable_source()
    module = types.ModuleType("s22plus_fyg8_p335_adapter_bound_for_p336")
    module.__file__ = str(SOURCE)
    module.__package__ = ""
    legacy_runtime = _legacy_runtime_alias(runtime)
    aliases = {
        "s22plus_fyg8_p335_retained_listener_runtime": runtime,
        "s22plus_fyg8_p335_retained_listener_acm_observer": observer,
        "s22plus_fyg8_p334_first_read_rc_runtime": legacy_runtime,
    }
    missing = object()
    previous = {name: sys.modules.get(name, missing) for name in aliases}
    try:
        # The aliases exist only during compilation.  Restoring sys.modules is
        # important when the five P336 modules are tested in one interpreter.
        sys.modules.update(aliases)
        exec(compile(payload, str(SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AdapterIdentityError("P3.35 adapter source failed to load") from exc
    finally:
        for name, old in previous.items():
            if old is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
    if getattr(module, "P335_RUN_ID_HEX", None) != P335_PREDECESSOR_RUN_ID_HEX:
        raise AdapterIdentityError("P3.35 adapter binding differs")
    return module


def _modules(root: types.ModuleType) -> list[types.ModuleType]:
    result: list[types.ModuleType] = []
    pending = [root]
    while pending:
        module = pending.pop()
        if module in result:
            continue
        result.append(module)
        for name, value in vars(module).items():
            if name.startswith("_P") and isinstance(value, types.ModuleType):
                pending.append(value)
    return result


runtime, observer = _load_p336_inputs()
_P335 = _load_p335(runtime, observer)


def _rebind_module_graph() -> None:
    # Only the exact-loaded P3.35 module graph is rebound.  runtime and
    # observer are imported P336 modules and are intentionally not traversed.
    modules = [_P335, *_modules(_P335)]
    legacy_runtime = _legacy_runtime_alias(runtime)
    seen: set[int] = set()
    for module in modules:
        if id(module) in seen:
            continue
        seen.add(id(module))
        for name, value in tuple(vars(module).items()):
            if value == P335_PREDECESSOR_RUN_ID:
                setattr(module, name, P336_RUN_ID)
            elif value == P335_PREDECESSOR_RUN_ID_HEX:
                setattr(module, name, P336_RUN_ID_HEX)
            elif callable(value) and getattr(value, "__kwdefaults__", None):
                defaults = dict(value.__kwdefaults__)
                changed = False
                for key, current in tuple(defaults.items()):
                    if current == P335_PREDECESSOR_RUN_ID:
                        defaults[key] = P336_RUN_ID
                        changed = True
                    elif current == P335_PREDECESSOR_RUN_ID_HEX:
                        defaults[key] = P336_RUN_ID_HEX
                        changed = True
                if changed:
                    value.__kwdefaults__ = defaults
        for name, value in {
            # The root P335 adapter consumes the P336 runtime directly.  Its
            # exact-loaded P334 parser still needs the compatibility alias
            # carrying the historical detail decoder names.
            "return_runtime": runtime if module is _P335 else legacy_runtime,
            "resident_observer": observer,
            "DEFAULT_COMMANDS": tuple(runtime.DEFAULT_COMMANDS),
            "P335_RUN_ID": P336_RUN_ID,
            "P335_RUN_ID_HEX": P336_RUN_ID_HEX,
            "P334_RUN_ID": P336_RUN_ID,
            "P334_RUN_ID_HEX": P336_RUN_ID_HEX,
        }.items():
            if hasattr(module, name):
                setattr(module, name, value)


_rebind_module_graph()

# Public P336 identity.  The P335 names below are compatibility labels only;
# all authority-bearing functions require P336_RUN_ID exactly.
SCHEMA = "s22plus_fyg8_p336_stock_process_v2_adapter_v1"
OVERLAY_CONTRACT_ID = P336_OVERLAY_CONTRACT_ID
DECODER_ID = P336_DECODER_ID
OBSERVER_CONTRACT_ID = P336_OBSERVER_CONTRACT_ID
POLICY_PREIMAGE = P336_POLICY_PREIMAGE
POLICY_ID = P336_POLICY_ID
RUN_ID = P336_RUN_ID
STOCK_RUN_ID = P336_RUN_ID
P335_RUN_ID_HEX = P336_RUN_ID_HEX
P335_RUN_ID = P336_RUN_ID
P334_RUN_ID_HEX = P336_RUN_ID_HEX
P334_RUN_ID = P336_RUN_ID
P336_ADAPTER_SOURCE = Path(__file__).resolve()
P335_ADAPTER_SOURCE = P336_ADAPTER_SOURCE
P334_ADAPTER_SOURCE = P336_ADAPTER_SOURCE
PARENT_SOURCE_CONTRACT_ID = getattr(
    _P335, "PARENT_SOURCE_CONTRACT_ID", "s22plus-fyg8-p310-carrier-v2-hsphy-attribution-v1"
)
PROFILE = getattr(_P335, "PROFILE", "E2")
DEFAULT_COMMANDS = tuple(runtime.DEFAULT_COMMANDS)
P320_PAYLOAD_ABI = getattr(_P335, "P320_PAYLOAD_ABI", 4)
OBSERVER_RECEIPT_SIZE = getattr(_P335, "OBSERVER_RECEIPT_SIZE", 15)
P336_DETAIL_BOOT_ID = getattr(runtime, "P335_DETAIL_BOOT_ID", 0xC350)
P336_DETAIL_INITIAL_SESSION = getattr(runtime, "P335_DETAIL_INITIAL_SESSION", 0xC351)
P336_DETAIL_LISTENER_BANNER = getattr(runtime, "P335_DETAIL_LISTENER_BANNER", 0xC352)
P336_DETAIL_LISTENER_PROTOCOL = getattr(runtime, "P335_DETAIL_LISTENER_PROTOCOL", 0xC353)


def _public(value: Any) -> Any:
    original = getattr(_P335, "_ORIGINAL_PUBLIC", None)
    try:
        result = original(value) if callable(original) else value
    except Exception as exc:
        raise AdapterIdentityError(str(exc)) from exc
    if not isinstance(result, dict):
        return result
    item = dict(result)
    item.update(
        {
            "schema": SCHEMA,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "policy_id": POLICY_ID,
            "run_id": P336_RUN_ID_HEX,
            "authenticated_exec": True,
            "authentication_required": True,
            "caller_selected_command": False,
            "same_tty_fd_required": True,
            "host_tty_close_reopen": True,
            "transport_reconnect": True,
            "fixed_heartbeat_only": False,
            "fixed_p330_commands": True,
            "command_count_per_session": len(DEFAULT_COMMANDS),
            "resident_sessions": INITIAL_SESSION_COUNT,
            "resident_reconnects": INITIAL_RECONNECT_COUNT,
            "initial_session_count": INITIAL_SESSION_COUNT,
            "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
            "per_boot_identity_required": True,
            "long_idle_host_resync": True,
            "later_action_open_before_resync": True,
            "later_action_max_preamble_pairs": observer.MAX_PREAMBLE_PAIRS,
            "later_action_max_resync_bytes": observer.MAX_RESYNC_BYTES,
            "resident_lease_schema": LEASE_SCHEMA,
            "resident_lease_duration_sec": LEASE_DURATION_SEC,
            "resident_lease_action_cap": LEASE_ACTION_CAP,
            "listener_wait_after_proof": True,
            "action_retry": False,
            "device_contact": False,
            "live_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
        }
    )
    for key in (
        "first_console_return_checkpoint_only",
        "first_console_return_detail_prefix",
        "first_console_return_detail_sentinel",
        "first_read_attribution_requires_stage0_without_stage1",
        "first_read_interpretation_requires_stage0_without_stage1",
    ):
        item.pop(key, None)
    return item


def acceptance_fixture() -> dict[str, Any]:
    try:
        value = dict(_P335.acceptance_fixture())
    except Exception as exc:
        raise AdapterIdentityError(str(exc)) from exc
    predecessors = list(value.get("predecessor_run_ids_rejected", []))
    if P335_PREDECESSOR_RUN_ID_HEX not in predecessors:
        predecessors.append(P335_PREDECESSOR_RUN_ID_HEX)
    value.update(
        {
            "schema": SCHEMA,
            "run_id": P336_RUN_ID_HEX,
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "policy_id": POLICY_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "predecessor_run_id_rejected": P335_PREDECESSOR_RUN_ID_HEX,
            "predecessor_run_ids_rejected": predecessors,
            "resident_sessions": INITIAL_SESSION_COUNT,
            "resident_reconnects": INITIAL_RECONNECT_COUNT,
            "logical_same_tty": True,
            "same_tty_fd": True,
            "host_tty_close_reopen": True,
            "transport_reconnect": True,
            "fixed_heartbeat_only": False,
            "fixed_p330_commands": True,
            "command_count_per_session": len(DEFAULT_COMMANDS),
            "initial_session_count": INITIAL_SESSION_COUNT,
            "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
            "per_boot_identity_required": True,
            "long_idle_host_resync": True,
            "later_action_open_before_resync": True,
            "later_action_max_preamble_pairs": observer.MAX_PREAMBLE_PAIRS,
            "later_action_max_resync_bytes": observer.MAX_RESYNC_BYTES,
            "resident_lease_schema": LEASE_SCHEMA,
            "resident_lease_duration_sec": LEASE_DURATION_SEC,
            "resident_lease_action_cap": LEASE_ACTION_CAP,
            "listener_wait_after_proof": True,
            "action_retry": False,
            "causal_result_allowed": False,
            "candidate_success": False,
        }
    )
    contract = value.get("contract")
    if isinstance(contract, dict):
        # The inherited ABI contract contains only the three promotion
        # receipts.  P336 identity belongs in the surrounding acceptance
        # projection, not as an extra unreviewed contract key.
        value["contract"] = dict(contract)
    observer_contract = value.get("observer_contract")
    if isinstance(observer_contract, dict):
        observer_contract = dict(observer_contract)
        observer_contract.update(
            {
                "id": OBSERVER_CONTRACT_ID,
                "initial_session_count": INITIAL_SESSION_COUNT,
                "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
                "per_boot_identity_required": True,
                "long_idle_host_resync": True,
                "open_before_resync": True,
                "max_preamble_pairs": observer.MAX_PREAMBLE_PAIRS,
                "max_resync_bytes": observer.MAX_RESYNC_BYTES,
                "resident_lease_schema": LEASE_SCHEMA,
                "listener_wait_after_proof": True,
                "action_retry": False,
            }
        )
        value["observer_contract"] = observer_contract
    for key in (
        "first_console_return_checkpoint_only",
        "first_console_return_detail_prefix",
        "first_console_return_detail_sentinel",
        "first_read_attribution_requires_stage0_without_stage1",
        "first_read_interpretation_requires_stage0_without_stage1",
    ):
        value.pop(key, None)
    return value


def bind_exact_sources(auth_key: Path | str | bytes | None = None) -> dict[str, Any]:
    try:
        value = dict(_P335.bind_exact_sources(auth_key))
    except Exception as exc:
        raise AdapterIdentityError(str(exc)) from exc
    value.update(
        {
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "run_id": P336_RUN_ID_HEX,
            "predecessor_run_id_rejected": P335_PREDECESSOR_RUN_ID_HEX,
            "resident_sessions": INITIAL_SESSION_COUNT,
            "resident_reconnects": INITIAL_RECONNECT_COUNT,
            "host_tty_close_reopen": True,
            "transport_reconnect": True,
            "fixed_heartbeat_only": False,
            "fixed_p330_commands": True,
            "command_count_per_session": len(DEFAULT_COMMANDS),
            "initial_session_count": INITIAL_SESSION_COUNT,
            "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
            "per_boot_identity_required": True,
            "long_idle_host_resync": True,
            "later_action_open_before_resync": True,
            "later_action_max_preamble_pairs": observer.MAX_PREAMBLE_PAIRS,
            "later_action_max_resync_bytes": observer.MAX_RESYNC_BYTES,
            "resident_lease_schema": LEASE_SCHEMA,
            "resident_lease_duration_sec": LEASE_DURATION_SEC,
            "resident_lease_action_cap": LEASE_ACTION_CAP,
        }
    )
    for key in (
        "first_console_return_checkpoint_only",
        "first_console_return_detail_prefix",
        "first_console_return_detail_sentinel",
        "first_read_attribution_requires_stage0_without_stage1",
        "first_read_interpretation_requires_stage0_without_stage1",
    ):
        value.pop(key, None)
    return value


def audit() -> dict[str, Any]:
    try:
        value = dict(_P335.audit())
    except Exception as exc:
        raise AdapterIdentityError(str(exc)) from exc
    value.update(
        {
            "schema": SCHEMA,
            "verdict": "PASS_P336_STOCK_PROCESS_V2_ADAPTER_H0_LONG_IDLE",
            "overlay_contract_id": OVERLAY_CONTRACT_ID,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "run_id": P336_RUN_ID_HEX,
            "predecessor_run_id": P335_PREDECESSOR_RUN_ID_HEX,
            "predecessor_run_id_rejected": P335_PREDECESSOR_RUN_ID_HEX,
            "encoder_failure_class": "P336_STOCK_ENCODER_FAILURE",
            "resident_sessions": INITIAL_SESSION_COUNT,
            "resident_reconnects": INITIAL_RECONNECT_COUNT,
            "initial_session_count": INITIAL_SESSION_COUNT,
            "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
            "host_tty_close_reopen": True,
            "transport_reconnect": True,
            "fixed_heartbeat_only": False,
            "fixed_p330_commands": True,
            "command_count_per_session": len(DEFAULT_COMMANDS),
            "per_boot_identity_required": True,
            "long_idle_host_resync": True,
            "later_action_open_before_resync": True,
            "later_action_max_preamble_pairs": observer.MAX_PREAMBLE_PAIRS,
            "later_action_max_resync_bytes": observer.MAX_RESYNC_BYTES,
            "resident_lease_schema": LEASE_SCHEMA,
            "resident_lease_duration_sec": LEASE_DURATION_SEC,
            "resident_lease_action_cap": LEASE_ACTION_CAP,
            "listener_wait_after_proof": True,
            "action_retry": False,
            "device_contact": False,
            "live_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
            "lineage": bind_exact_sources(),
        }
    )
    value["acceptance"] = acceptance_fixture()
    contract = value.get("contract")
    if isinstance(contract, dict):
        value["contract"] = {
            **contract,
            "decoder": DECODER_ID,
            "observer_contract_id": OBSERVER_CONTRACT_ID,
            "policy_id": POLICY_ID,
            "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
            "causal_result_allowed": False,
            "candidate_success": False,
        }
    for key in (
        "first_console_return_checkpoint_only",
        "first_console_return_detail_prefix",
        "first_console_return_detail_sentinel",
        "first_read_attribution_requires_stage0_without_stage1",
        "first_read_interpretation_requires_stage0_without_stage1",
    ):
        value.pop(key, None)
    return value


def validate_contract(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise ContractError("P336 overlay contract is not an object")
    expected = {
        "userspace_overlay_contract_id": OVERLAY_CONTRACT_ID,
        "decoder": DECODER_ID,
        "policy_id": POLICY_ID,
        "profile": PROFILE,
        "source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "observer_contract_id": OBSERVER_CONTRACT_ID,
        "payload_abi": P320_PAYLOAD_ABI,
        "observer_receipt_size": OBSERVER_RECEIPT_SIZE,
        "causal_result_allowed": False,
        "candidate_success": False,
    }
    if any(value.get(key) != expected_value for key, expected_value in expected.items()):
        raise ContractError("P336 overlay contract identity differs")
    return value


def validate_acceptance_item(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise ContractError("P336 acceptance item is not an object")
    expected = acceptance_fixture()
    for key, expected_value in expected.items():
        if key == "contract":
            continue
        if value.get(key) != expected_value or type(value.get(key)) is not type(expected_value):
            raise ContractError(f"P336 acceptance field differs: {key}")
    contract = value.get("contract")
    if type(contract) is not dict or set(contract) != {"candidate_static", "run_manifest", "static_check"}:
        raise ContractError("P336 acceptance contract differs")
    for name, item in contract.items():
        if (
            type(item) is not dict
            or set(item) != {"path", "size", "sha256"}
            or type(item["path"]) is not str
            or not item["path"]
            or type(item["size"]) is not int
            or item["size"] <= 0
            or type(item["sha256"]) is not str
            or len(item["sha256"]) != 64
            or any(char not in "0123456789abcdef" for char in item["sha256"])
        ):
            raise ContractError(f"P336 acceptance contract {name} differs")
    return value


def classify_observation(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P336_RUN_ID,
) -> dict[str, Any]:
    if expected_profile != PROFILE or expected_run_id != P336_RUN_ID:
        raise AdapterIdentityError("P336 observation binding differs")
    original = getattr(_P335, "_ORIGINAL_CLASSIFY_OBSERVATION", None)
    if not callable(original):
        raise AdapterIdentityError("P3.35 observation parser is unavailable")
    try:
        value = original(
            payload,
            expected_profile=PROFILE,
            expected_run_id=P336_RUN_ID,
        )
    except Exception as exc:
        raise AdapterIdentityError(str(exc)) from exc
    return _public(value)


def classify_clean_baseline(
    payload: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes = P336_RUN_ID,
) -> dict[str, Any]:
    if expected_profile != PROFILE or expected_run_id != P336_RUN_ID:
        raise AdapterIdentityError("P336 baseline binding differs")
    original = getattr(_P335, "_ORIGINAL_CLASSIFY_CLEAN_BASELINE", None)
    if not callable(original):
        raise AdapterIdentityError("P3.35 baseline parser is unavailable")
    try:
        value = original(
            payload,
            expected_profile=PROFILE,
            expected_run_id=P336_RUN_ID,
        )
    except Exception as exc:
        raise AdapterIdentityError(str(exc)) from exc
    return _public(value)


bind_lineage = bind_exact_sources

__all__ = sorted(
    {
        "AdapterIdentityError",
        "ContractError",
        "DEFAULT_COMMANDS",
        "INITIAL_RECONNECT_COUNT",
        "INITIAL_SESSION_COUNT",
        "LEASE_ACTION_CAP",
        "LEASE_DURATION_SEC",
        "OBSERVER_CONTRACT_ID",
        "OVERLAY_CONTRACT_ID",
        "P334_ADAPTER_SOURCE",
        "P334_PREDECESSOR_RUN_ID",
        "P334_PREDECESSOR_RUN_ID_HEX",
        "P334_RUN_ID",
        "P334_RUN_ID_HEX",
        "P335_ADAPTER_SOURCE",
        "P335_PREDECESSOR_RUN_ID",
        "P335_PREDECESSOR_RUN_ID_HEX",
        "P335_RUN_ID",
        "P335_RUN_ID_HEX",
        "P336_ADAPTER_SOURCE",
        "P336_POLICY_ID",
        "P336_POLICY_PREIMAGE",
        "P336_RUN_ID",
        "P336_RUN_ID_HEX",
        "POLICY_ID",
        "POLICY_PREIMAGE",
        "PARENT_SOURCE_CONTRACT_ID",
        "PROFILE",
        "RUN_ID",
        "SCHEMA",
        "SOURCE",
        "SOURCE_IDENTITY",
        "STOCK_RUN_ID",
        "acceptance_fixture",
        "audit",
        "bind_exact_sources",
        "bind_lineage",
        "classify_clean_baseline",
        "classify_observation",
        "identity",
        "validate_acceptance_item",
        "validate_contract",
    }
)

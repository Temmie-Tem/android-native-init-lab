#!/usr/bin/env python3
"""Reviewed attended S20+ N1 exact privileged root-data transaction.

This capability is active but creates no run or standing device authority.  It
owns only one deterministic Magisk module, one fixed device namespace, bounded
ordinary reboots, exact staged-byte cleanup, and a durable handoff to its
separately reviewed stock-boot recovery runner.  It never accepts a caller
supplied device path, shell fragment, module ID, package, artifact, or root
command.
"""

from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import time
from typing import Any, Callable

import s20plus_g986n_magisk_bootstrap_f1 as bootstrap
import s22plus_boot_only_f1_transport as transport


VERSION = "s20plus-g986n-native-canary-r1-v1"
NATIVE_CANARY_R1_ACTIVE = True
EXPECTED_REVIEWED_NORMALIZED_SHA256 = "39cdf9eda1eb4fa8240bab49c1a45fdf54b63431908fd6721cdde2453e77544c"

ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve()
RUN_ROOT = ROOT / "workspace/private/runs/s20plus-g986n-native-canary-r1"
RECOVERY_SCRIPT = SCRIPT.with_name("s20plus_g986n_native_canary_stock_recovery_r1.py")

POST_INSTALL_PREDECESSOR_ROOT_RUNNER = {
    "path": str(SCRIPT),
    "size": 213_403,
    "sha256": "35dfc7557c5c9e9b3e62d4865e81122572c57d0464997f4e2a35904a0b15432f",
    "normalized_sha256": "6c64c8763fd0ab68fe2b88721f6d6d1f0f9c28f96b4595f028c0af7c143194ad",
}
POST_INSTALL_PREDECESSOR_BINDING_SHA256 = (
    "89098a4190d3ab2a85ddf0efd8b12ffdd800f79cf4146b8302f8e23832cf1845"
)

APPROVAL_PREFIX = "S20PLUS-G986N-NATIVE-CANARY-R1-APPROVE:"
STOCK_HANDOFF_CONFIRM = (
    "S20PLUS-G986N-NATIVE-CANARY-R1-"
    "ROOTED-RECOVERY-UNAVAILABLE-STOCK-HANDOFF"
)

MODULE_ID = "s20plus_native_canary"
MODULE_ZIP = (
    ROOT
    / "workspace/private/outputs/s20plus_g986n/native_canary_n1_v1"
    / f"{MODULE_ID}.zip"
)
MODULE_ZIP_SIZE = 598_551
MODULE_ZIP_SHA256 = "e06c88c3a1c029658160b974bc5938acc1f89ab68ea9a7d7d7169d5bd51525a2"
BINARY = MODULE_ZIP.parent / "s20plus_native_canary"
BINARY_SIZE = 597_720
BINARY_SHA256 = "38e14e6f54374fc98604bdd61e50922ce9bff1c96feae7572221be548902066c"

BUILDER_SOURCE = {
    "path": str(SCRIPT.with_name("build_s20plus_g986n_native_canary_n1.py")),
    "size": 21_773,
    "sha256": "bcbbc60052631d810ffa3f866e7077fdbc394f161c701d00f17d9c1a3166c0cc",
}
CANARY_SOURCE = {
    "path": str(ROOT / "workspace/public/src/native-init/s20plus_native_canary.c"),
    "size": 34_802,
    "sha256": "31a4413f5d1d320d81ddb8720ff2f0303fb5198cd14a746af4c6cbe47bed3f2e",
}
BOOTSTRAP_SOURCE = {
    "path": str(Path(bootstrap.__file__).resolve()),
    "size": 161_259,
    "sha256": "11ca8aaef183e76c6eeec1a43e75b00bbc14e4b51650e3122c8f4bbdfdc8799f",
    "normalized_sha256": "457c6c9c06a70b431a0c352d7707c1d421bbe89f190667eb2eab608cab49c57e",
}
STOCK_RECOVERY_SOURCE = {
    "path": str(RECOVERY_SCRIPT),
    "size": 61_312,
    "sha256": "b029afc3d4a899e4d83304773f8405519bacdb02de742de015a52c97689cc2a6",
    "normalized_sha256": "0bb7eab8a87d11758dac20103ede5ac16c5acbdf3cbc3b511cb30842c4f29f2d",
}

STATE_PARENT = "/data/adb/s20plus-native-init"
STATE_DIR = f"{STATE_PARENT}/n1"
ACTIVE_MODULE_DIR = f"/data/adb/modules/{MODULE_ID}"
UPDATE_MODULE_DIR = f"/data/adb/modules_update/{MODULE_ID}"
STAGE_NAME = f"Codex-S20Plus-N1-{MODULE_ZIP_SHA256[:12]}"
STAGE_PARENT = "/data/local/tmp"
STAGE_DIR = f"{STAGE_PARENT}/{STAGE_NAME}"
STAGE_ZIP = f"{STAGE_DIR}/{MODULE_ID}.zip"
STAGE_BINDING = f"{STAGE_DIR}/binding.txt"

MAGISK_VERSION = "30.7:MAGISK:R"
MAGISK_VERSION_CODE = "30700"
MAGISK_BINARY = "/data/adb/magisk/magisk"
MAGISK_BUSYBOX = "/data/adb/magisk/busybox"
MAGISK_UTIL_FUNCTIONS = "/data/adb/magisk/util_functions.sh"
MAX_OUTPUT = 64 * 1024
MAX_STATE_FILE = 8 * 1024
ANDROID_WAIT = 420

MODULE_PROP_SHA256 = "542c4502a9183ba37d8428f81c311a979ff2e642a7320d540342a717db1e78dc"
SERVICE_SHA256 = "e343071024cc982e2860736bbedfb141b0149dfb5050ba74a47624023a8353df"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
MODULE_PROP_SIZE = 178
SERVICE_SIZE = 215
DEVICE_BINDING_SIZE = 469
CANARY_INTENT_SIZE = len(
    (
        '{"schema":"s20plus_native_canary_n1_intent_v1",'
        f'"binding_sha256":"{"0" * 64}",'
        f'"run_nonce":"{"0" * 32}",'
        '"replay_permitted":false}\n'
    ).encode("ascii")
)

Command = Callable[[list[str], float, int], tuple[int, bytes, bytes]]


class RootDataError(RuntimeError):
    pass


AT_EMPTY_PATH = 0x1000
_LIBC = ctypes.CDLL(None, use_errno=True)
_LINKAT = _LIBC.linkat
_LINKAT.argtypes = (
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_int,
)
_LINKAT.restype = ctypes.c_int


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_bytes(value: Any) -> bytes:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise RootDataError("N1 canonical JSON value is not finite") from exc
    return (encoded + "\n").encode()


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def exact_typed_equal(actual: Any, expected: Any) -> bool:
    """Compare journal values without Python's bool/int equivalence."""
    if isinstance(expected, dict):
        return (
            isinstance(actual, dict)
            and set(actual) == set(expected)
            and all(exact_typed_equal(actual[key], expected[key]) for key in expected)
        )
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(exact_typed_equal(left, right) for left, right in zip(actual, expected))
        )
    if expected is None:
        return actual is None
    return type(actual) is type(expected) and actual == expected


def require_active() -> None:
    if not NATIVE_CANARY_R1_ACTIVE:
        raise RootDataError("S20+ N1 privileged root-data R1 is not active")


def exact_regular_receipt(
    path: Path,
    label: str,
    *,
    expected_mode: int | None = None,
) -> dict[str, Any]:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise RootDataError(f"{label} is missing") from exc
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise RootDataError(f"{label} is not an exact regular file")
    mode = stat.S_IMODE(metadata.st_mode)
    if expected_mode is not None and mode != expected_mode:
        raise RootDataError(f"{label} mode changed")
    receipt = {
        "path": str(path.resolve(strict=True)),
        "size": metadata.st_size,
        "sha256": bootstrap.sha256_file(path),
    }
    if expected_mode is not None:
        receipt["mode"] = f"{mode:04o}"
    return receipt


def require_receipt(path: Path, expected: dict[str, Any], label: str) -> dict[str, Any]:
    mode_value = expected.get("mode")
    if mode_value is not None and (
        not isinstance(mode_value, str)
        or re.fullmatch(r"0[0-7]{3}", mode_value) is None
    ):
        raise RootDataError(f"{label} expected mode is malformed")
    expected_mode = int(mode_value, 8) if mode_value is not None else None
    actual = exact_regular_receipt(path, label, expected_mode=expected_mode)
    if not exact_typed_equal(actual, expected):
        raise RootDataError(f"{label} changed")
    return actual


def bootstrap_runner_receipt() -> dict[str, Any]:
    path = Path(BOOTSTRAP_SOURCE["path"])
    receipt = exact_regular_receipt(
        path,
        "N1 bootstrap parser runner",
    )
    normalized, count = re.subn(
        rb'EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256 = "[0-9a-f]{64}"',
        b'EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256 = "' + b"0" * 64 + b'"',
        path.read_bytes(),
    )
    value = {
        **receipt,
        "normalized_sha256": hashlib.sha256(normalized).hexdigest(),
    }
    if count != 1 or not exact_typed_equal(value, BOOTSTRAP_SOURCE):
        raise RootDataError("N1 bootstrap parser runner changed")
    return value


def bootstrap_f1_core_receipt() -> dict[str, Any]:
    path, size, digest = bootstrap.CLOSURE_FILES["f1_core"]
    expected = {
        "path": str(path),
        "size": size,
        "sha256": digest,
    }
    return require_receipt(
        path,
        expected,
        "N1 persisted-transfer classifier",
    )


def load_candidate_builder() -> Any:
    """Load candidate-only build code only on a fresh prepare path.

    Recovery entrypoints must remain importable when the disposable builder and
    candidate source have legitimately been removed after install intent.
    """
    require_receipt(Path(BUILDER_SOURCE["path"]), BUILDER_SOURCE, "N1 builder")
    try:
        module = importlib.import_module("build_s20plus_g986n_native_canary_n1")
    except (ImportError, OSError) as exc:
        raise RootDataError("N1 candidate builder is unavailable") from exc
    module_path = Path(getattr(module, "__file__", "")).resolve(strict=True)
    source_path = Path(getattr(module, "SOURCE", "")).resolve(strict=True)
    if (
        str(module_path) != BUILDER_SOURCE["path"]
        or str(source_path) != CANARY_SOURCE["path"]
    ):
        raise RootDataError("N1 candidate builder resolved outside its frozen closure")
    return module


def normalized_self_sha256() -> str:
    payload = SCRIPT.read_bytes()
    pattern = rb'EXPECTED_REVIEWED_NORMALIZED_SHA256 = "[0-9a-f]{64}"'
    normalized, count = re.subn(
        pattern,
        b'EXPECTED_REVIEWED_NORMALIZED_SHA256 = "' + b"0" * 64 + b'"',
        payload,
    )
    if count != 1:
        raise RootDataError("N1 runner normalized identity is ambiguous")
    return hashlib.sha256(normalized).hexdigest()


def self_receipt() -> dict[str, Any]:
    receipt = exact_regular_receipt(SCRIPT, "N1 runner")
    normalized = normalized_self_sha256()
    if normalized != EXPECTED_REVIEWED_NORMALIZED_SHA256:
        raise RootDataError("N1 runner does not match its reviewed identity")
    return {**receipt, "normalized_sha256": normalized}


def recovery_runner_receipt() -> dict[str, Any]:
    receipt = exact_regular_receipt(RECOVERY_SCRIPT, "N1 stock-recovery runner")
    source = RECOVERY_SCRIPT.read_bytes()
    pattern = rb'EXPECTED_REVIEWED_NORMALIZED_SHA256 = "[0-9a-f]{64}"'
    normalized, count = re.subn(
        pattern,
        b'EXPECTED_REVIEWED_NORMALIZED_SHA256 = "' + b"0" * 64 + b'"',
        source,
    )
    normalized_sha256 = hashlib.sha256(normalized).hexdigest()
    actual = {**receipt, "normalized_sha256": normalized_sha256}
    if count != 1 or not exact_typed_equal(actual, STOCK_RECOVERY_SOURCE):
        raise RootDataError("N1 stock-recovery runner changed from its reviewed identity")
    return actual


def validate_artifacts(builder_module: Any | None = None) -> dict[str, Any]:
    if builder_module is None:
        builder_module = load_candidate_builder()
    require_receipt(Path(CANARY_SOURCE["path"]), CANARY_SOURCE, "N1 canary source")
    binary = require_receipt(BINARY, {
        "path": str(BINARY.resolve(strict=True)),
        "size": BINARY_SIZE,
        "sha256": BINARY_SHA256,
    }, "N1 binary")
    module_zip = require_receipt(MODULE_ZIP, {
        "path": str(MODULE_ZIP.resolve(strict=True)),
        "size": MODULE_ZIP_SIZE,
        "sha256": MODULE_ZIP_SHA256,
        "mode": "0600",
    }, "N1 module ZIP")
    audit = builder_module.audit_module_zip(MODULE_ZIP, BINARY.read_bytes())
    if audit.get("size") != MODULE_ZIP_SIZE or audit.get("sha256") != MODULE_ZIP_SHA256:
        raise RootDataError("N1 module ZIP audit changed")
    stock_boot = validate_stock_artifact()
    return {
        "module_zip": module_zip,
        "binary": binary,
        "stock_boot": stock_boot,
    }


def validate_stock_artifact() -> dict[str, Any]:
    require_receipt(bootstrap.ROLLBACK, {
        "path": str(bootstrap.ROLLBACK.resolve(strict=True)),
        "size": bootstrap.ROLLBACK_SIZE,
        "sha256": bootstrap.ROLLBACK_SHA256,
    }, "N1 stock rollback")
    with transport.pin_boot_only_ap(
        bootstrap.ROLLBACK,
        label="N1 stock rollback",
        expected_size=bootstrap.ROLLBACK_SIZE,
        expected_sha256=bootstrap.ROLLBACK_SHA256,
    ) as pinned:
        stock_member = transport.boot_only_member_receipt(pinned, label="N1 stock rollback")
    return {
        "path": str(bootstrap.ROLLBACK),
        "size": bootstrap.ROLLBACK_SIZE,
        "sha256": bootstrap.ROLLBACK_SHA256,
        "member": stock_member,
    }


def closure_receipts() -> dict[str, Any]:
    base = bootstrap.closure_receipts()
    if not exact_typed_equal(base["runner"], BOOTSTRAP_SOURCE):
        raise RootDataError("S20+ bootstrap helper closure changed")
    return {
        "root_data_runner": self_receipt(),
        "stock_recovery_runner": recovery_runner_receipt(),
        "bootstrap": base,
        "builder": require_receipt(Path(BUILDER_SOURCE["path"]), BUILDER_SOURCE, "N1 builder"),
        "canary_source": require_receipt(Path(CANARY_SOURCE["path"]), CANARY_SOURCE, "N1 canary source"),
    }


def validate_recovery_inputs(
    prepared: dict[str, Any],
    scope: str,
    run_dir: Path | None = None,
) -> None:
    if scope not in {
        "root-recovery", "stock-recovery", "stock-finalize",
        "root-terminal-release", "stock-terminal-release",
        "post-install-resume",
    }:
        raise RootDataError("N1 recovery input scope is invalid")
    binding = prepared.get("binding") if isinstance(prepared, dict) else None
    closure = binding.get("closure") if isinstance(binding, dict) else None
    artifacts = binding.get("artifacts") if isinstance(binding, dict) else None
    root_runner = closure.get("root_data_runner") if isinstance(closure, dict) else None
    if scope == "post-install-resume":
        if (
            not isinstance(closure, dict)
            or set(closure) != {
                "root_data_runner", "stock_recovery_runner", "bootstrap",
                "builder", "canary_source",
            }
            or not exact_typed_equal(
                closure.get("root_data_runner"),
                POST_INSTALL_PREDECESSOR_ROOT_RUNNER,
            )
            or prepared.get("binding_sha256")
            != POST_INSTALL_PREDECESSOR_BINDING_SHA256
            or not exact_typed_equal(
                closure.get("bootstrap"), bootstrap.closure_receipts()
            )
        ):
            raise RootDataError("N1 post-install predecessor closure changed")
        self_receipt()
        return
    continued_predecessor = False
    if (
        run_dir is not None
        and exact_typed_equal(root_runner, POST_INSTALL_PREDECESSOR_ROOT_RUNNER)
        and os.path.lexists(run_dir / "post-install-continuation.json")
    ):
        validate_post_install_continuation(run_dir, prepared)
        continued_predecessor = True
    current_root_runner = self_receipt()
    root_runner_valid = (
        exact_typed_equal(root_runner, current_root_runner)
        or continued_predecessor
    )
    if scope in {"root-terminal-release", "stock-terminal-release"}:
        bootstrap_closure = (
            closure.get("bootstrap") if isinstance(closure, dict) else None
        )
        if (
            not isinstance(closure, dict)
            or set(closure) != {
                "root_data_runner", "stock_recovery_runner", "bootstrap",
                "builder", "canary_source",
            }
            or not root_runner_valid
            or (
                scope == "stock-terminal-release"
                and not exact_typed_equal(
                    closure.get("stock_recovery_runner"), recovery_runner_receipt()
                )
            )
            or not exact_typed_equal(
                bootstrap_closure.get("runner")
                if isinstance(bootstrap_closure, dict) else None,
                bootstrap_runner_receipt(),
            )
            or (
                scope == "stock-terminal-release"
                and not exact_typed_equal(
                    bootstrap_closure.get("f1_core")
                    if isinstance(bootstrap_closure, dict) else None,
                    bootstrap_f1_core_receipt(),
                )
            )
        ):
            raise RootDataError("N1 terminal-release parser closure changed")
        return
    if (
        not isinstance(closure, dict)
        or set(closure) != {
            "root_data_runner", "stock_recovery_runner", "bootstrap",
            "builder", "canary_source",
        }
        or not root_runner_valid
        or not exact_typed_equal(closure.get("bootstrap"), bootstrap.closure_receipts())
    ):
        raise RootDataError("N1 recovery-critical helper closure changed")
    if scope in {"stock-recovery", "stock-finalize"}:
        if (
            not exact_typed_equal(
                closure.get("stock_recovery_runner"), recovery_runner_receipt()
            )
            or not isinstance(artifacts, dict)
            or set(artifacts) != {"module_zip", "binary", "stock_boot"}
        ):
            raise RootDataError("N1 stock-recovery inputs changed")
        if scope == "stock-recovery" and not exact_typed_equal(
            artifacts.get("stock_boot"), validate_stock_artifact()
        ):
            raise RootDataError("N1 stock-recovery artifact changed before dispatch")


def guard_path() -> Path:
    return bootstrap.guard_path()


def guard_value(run_dir: Path) -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_native_canary_r1_guard_v1",
        "version": VERSION,
        "run_dir": str(run_dir),
        "unresolved": True,
    }


def read_guard(run_dir: Path) -> dict[str, Any]:
    value = read_exact_json(guard_path(), "N1 shared guard")
    if not exact_typed_equal(value, guard_value(run_dir)):
        raise RootDataError("N1 shared guard does not match this run")
    return value


def release_guard(run_dir: Path) -> None:
    read_guard(run_dir)
    guard_path().unlink()
    bootstrap.fsync_dir(guard_path().parent)


RUN_ID_RE = re.compile(r"run-[0-9]{18,20}")


def allocate_run_dir() -> Path:
    parent = RUN_ROOT.parent.resolve(strict=True)
    if RUN_ROOT.exists():
        if RUN_ROOT.is_symlink() or RUN_ROOT.resolve(strict=True) != RUN_ROOT.absolute():
            raise RootDataError("N1 run root is indirect")
    else:
        if RUN_ROOT.parent.absolute() != parent:
            raise RootDataError("N1 run parent is indirect")
        RUN_ROOT.mkdir(mode=0o700)
        bootstrap.fsync_dir(RUN_ROOT.parent)
    run_dir = RUN_ROOT / f"run-{time.time_ns()}"
    if RUN_ID_RE.fullmatch(run_dir.name) is None:
        raise RootDataError("N1 generated run ID is malformed")
    if run_dir.parent != RUN_ROOT or os.path.lexists(run_dir):
        raise RootDataError("N1 run directory is not a fresh direct child")
    run_dir.mkdir(mode=0o700)
    bootstrap.fsync_dir(RUN_ROOT)
    return run_dir


def resolve_run_id(run_id: str) -> Path:
    if not isinstance(run_id, str) or RUN_ID_RE.fullmatch(run_id) is None:
        raise RootDataError("N1 run ID is malformed")
    return validate_run_dir(RUN_ROOT / run_id)


def validate_run_dir(run_dir: Path) -> Path:
    if RUN_ROOT.is_symlink() or RUN_ROOT.resolve(strict=True) != RUN_ROOT.absolute():
        raise RootDataError("N1 run root is indirect")
    if run_dir.parent != RUN_ROOT or run_dir.is_symlink() or not run_dir.is_dir():
        raise RootDataError("N1 run directory is indirect")
    if run_dir.resolve(strict=True) != run_dir.absolute():
        raise RootDataError("N1 run directory escaped its root")
    return run_dir


def require_exact_nodes(run_dir: Path, regular_names: set[str]) -> None:
    expected = {Path(name): "regular" for name in regular_names}
    expected[Path("events")] = "directory"
    actual: dict[Path, str] = {}
    pending = [run_dir]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                relative = path.relative_to(run_dir)
                metadata = entry.stat(follow_symlinks=False)
                if stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1:
                    actual[relative] = "regular"
                elif stat.S_ISDIR(metadata.st_mode) and not entry.is_symlink():
                    actual[relative] = "directory"
                    pending.append(path)
                else:
                    actual[relative] = "unexpected"
    if actual != expected:
        raise RootDataError("N1 journal contains missing, extra, or indirect nodes")


def event(run_dir: Path, ordinal: int, name: str, payload: dict[str, Any]) -> None:
    events = run_dir / "events"
    if not os.path.lexists(events):
        events.mkdir(mode=0o700)
        bootstrap.fsync_dir(run_dir)
    metadata = events.lstat()
    if (
        events.is_symlink()
        or not stat.S_ISDIR(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or events.resolve(strict=True) != events.absolute()
    ):
        raise RootDataError("N1 event directory is not exact")
    event_name = f"native-canary-{name}"
    durable_create(
        events / f"{ordinal:02d}-{event_name}.json",
        {
            "schema": "s20plus_g986n_f1_event_v1",
            "version": bootstrap.VERSION,
            "ordinal": ordinal,
            "name": event_name,
            "at": utc_now(),
            **payload,
        },
    )


PREFLIGHT_SCRIPT = f"""set -eu
for item in \
  active:{ACTIVE_MODULE_DIR} \
  update:{UPDATE_MODULE_DIR} \
  parent:{STATE_PARENT} \
  state:{STATE_DIR} \
  stage:{STAGE_DIR}; do
  key=${{item%%:*}}; path=${{item#*:}}
  if [ -e "$path" ] || [ -L "$path" ]; then printf '%s=present\\n' "$key"; else printf '%s=absent\\n' "$key"; fi
done
[ -d /data/adb/modules ] && [ ! -L /data/adb/modules ]
[ "$(/data/adb/magisk/busybox stat -c %a /data/adb/modules)" = "755" ]
[ "$(/data/adb/magisk/busybox stat -c %u:%g /data/adb/modules)" = "0:0" ]
[ ! -e /data/adb/modules_update ] && [ ! -L /data/adb/modules_update ]
printf 'active_count=%s\\n' "$(/data/adb/magisk/busybox find /data/adb/modules -mindepth 1 -maxdepth 1 -print | /data/adb/magisk/busybox wc -l)"
printf 'update_count=0\\n'
"""

MAGISK_CLOSURE_ROOT_CONTEXT_RC = 97

MAGISK_CLOSURE_SCRIPT = f"""set -u
[ "$(/system/bin/toybox id -u 2>/dev/null)" = "0" ] || exit {MAGISK_CLOSURE_ROOT_CONTEXT_RC}
probe() {{
  label="$1"; path="$2"
  if [ -L "$path" ]; then printf '%s|error|symlink\\n' "$label"; return 0; fi
  if [ ! -e "$path" ]; then printf '%s|error|absent\\n' "$label"; return 0; fi
  if [ ! -f "$path" ]; then printf '%s|error|not-regular\\n' "$label"; return 0; fi
  mode=$(/system/bin/toybox stat -c %a "$path" 2>/dev/null) || {{ printf '%s|error|mode-read-failed\\n' "$label"; return 0; }}
  uid=$(/system/bin/toybox stat -c %u "$path" 2>/dev/null) || {{ printf '%s|error|uid-read-failed\\n' "$label"; return 0; }}
  gid=$(/system/bin/toybox stat -c %g "$path" 2>/dev/null) || {{ printf '%s|error|gid-read-failed\\n' "$label"; return 0; }}
  links=$(/system/bin/toybox stat -c %h "$path" 2>/dev/null) || {{ printf '%s|error|nlink-read-failed\\n' "$label"; return 0; }}
  size=$(/system/bin/toybox stat -c %s "$path" 2>/dev/null) || {{ printf '%s|error|size-read-failed\\n' "$label"; return 0; }}
  hash_line=$(/system/bin/toybox sha256sum "$path" 2>/dev/null) || {{ printf '%s|error|hash-read-failed\\n' "$label"; return 0; }}
  digest=${{hash_line%% *}}
  printf '%s|%s|%s|%s|%s|%s|%s\\n' "$label" "$mode" "$uid" "$gid" "$links" "$size" "$digest"
}}
probe magisk {MAGISK_BINARY}
probe busybox {MAGISK_BUSYBOX}
probe util_functions {MAGISK_UTIL_FUNCTIONS}
"""

MAGISK_CLOSURE_ERROR_TOKENS = frozenset({
    "symlink",
    "absent",
    "not-regular",
    "mode-read-failed",
    "uid-read-failed",
    "gid-read-failed",
    "nlink-read-failed",
    "size-read-failed",
    "hash-read-failed",
})

MAGISK_CLOSURE_EXPECTED = (
    ("magisk", MAGISK_BINARY, frozenset({"700", "750", "755"}), 128 * 1024 * 1024),
    ("busybox", MAGISK_BUSYBOX, frozenset({"700", "750", "755"}), 32 * 1024 * 1024),
    (
        "util_functions",
        MAGISK_UTIL_FUNCTIONS,
        # Magisk v30.7 installs the persistent MAGISKBIN tree with
        # chmod -R 755 in both flash_script.sh and app fix_env().
        frozenset({"755"}),
        2 * 1024 * 1024,
    ),
)

INVENTORY_SCRIPT = """set -eu
[ -d /data/adb/modules ] && [ ! -L /data/adb/modules ]
[ "$(/data/adb/magisk/busybox stat -c %a /data/adb/modules)" = "755" ]
[ "$(/data/adb/magisk/busybox stat -c %u:%g /data/adb/modules)" = "0:0" ]
[ ! -e /data/adb/modules_update ] && [ ! -L /data/adb/modules_update ]
printf 'active_count=%s\\n' "$(/data/adb/magisk/busybox find /data/adb/modules -mindepth 1 -maxdepth 1 -print | /data/adb/magisk/busybox wc -l)"
printf 'update_count=0\\n'
"""


def _file_test(path: str, digest: str, size: int, mode: str) -> str:
    return (
        f'[ -f "{path}" ] && [ ! -L "{path}" ] && '
        f'[ "$(/data/adb/magisk/busybox sha256sum "{path}" | /data/adb/magisk/busybox cut -d" " -f1)" = "{digest}" ] && '
        f'[ "$(/data/adb/magisk/busybox stat -c %s "{path}")" = "{size}" ] && '
        f'[ "$(/data/adb/magisk/busybox stat -c %a "{path}")" = "{mode}" ] && '
        f'[ "$(/data/adb/magisk/busybox stat -c %u:%g:%h "{path}")" = "0:0:1" ]'
    )


def _dir_test(path: str, mode: str) -> str:
    return (
        f'[ -d "{path}" ] && [ ! -L "{path}" ] && '
        f'[ "$(/data/adb/magisk/busybox stat -c %a "{path}")" = "{mode}" ] && '
        f'[ "$(/data/adb/magisk/busybox stat -c %u:%g "{path}")" = "0:0" ]'
    )


POST_INSTALL_TESTS = " && ".join((
    _dir_test("/data/adb/modules", "755"),
    # The exact v30.7 native entrypoint sets umask(0).  install_module then
    # creates the transient parent and active stub with mkdir -p; only the
    # update module tree receives set_default_perm before the first reboot.
    _dir_test("/data/adb/modules_update", "777"),
    '[ "$(/data/adb/magisk/busybox find /data/adb/modules -mindepth 1 -maxdepth 1 -print | /data/adb/magisk/busybox wc -l)" = "1" ]',
    '[ "$(/data/adb/magisk/busybox find /data/adb/modules_update -mindepth 1 -maxdepth 1 -print | /data/adb/magisk/busybox wc -l)" = "1" ]',
    f'[ "$(/data/adb/magisk/busybox find "{UPDATE_MODULE_DIR}" -mindepth 1 | /data/adb/magisk/busybox wc -l)" = "5" ]',
    _dir_test(UPDATE_MODULE_DIR, "755"),
    _dir_test(f"{UPDATE_MODULE_DIR}/bin", "755"),
    _file_test(f"{UPDATE_MODULE_DIR}/module.prop", MODULE_PROP_SHA256, MODULE_PROP_SIZE, "644"),
    _file_test(f"{UPDATE_MODULE_DIR}/skip_mount", EMPTY_SHA256, 0, "644"),
    _file_test(f"{UPDATE_MODULE_DIR}/service.sh", SERVICE_SHA256, SERVICE_SIZE, "644"),
    _file_test(f"{UPDATE_MODULE_DIR}/bin/s20plus_native_canary", BINARY_SHA256, BINARY_SIZE, "750"),
    f'[ "$(/data/adb/magisk/busybox find "{ACTIVE_MODULE_DIR}" -mindepth 1 | /data/adb/magisk/busybox wc -l)" = "2" ]',
    _dir_test(ACTIVE_MODULE_DIR, "777"),
    _file_test(f"{ACTIVE_MODULE_DIR}/module.prop", MODULE_PROP_SHA256, MODULE_PROP_SIZE, "644"),
    _file_test(f"{ACTIVE_MODULE_DIR}/update", EMPTY_SHA256, 0, "644"),
    _dir_test(STATE_PARENT, "700"),
    f'[ "$(/data/adb/magisk/busybox find "{STATE_PARENT}" -mindepth 1 -maxdepth 1 | /data/adb/magisk/busybox wc -l)" = "1" ]',
    _dir_test(STATE_DIR, "700"),
    f'[ "$(/data/adb/magisk/busybox find "{STATE_DIR}" -mindepth 1 -maxdepth 1 | /data/adb/magisk/busybox wc -l)" = "1" ]',
    _file_test(f"{STATE_DIR}/binding.txt", "__BINDING_SHA256__", DEVICE_BINDING_SIZE, "600"),
))


ACTIVE_MODULE_TREE_TESTS = " && ".join((
    _dir_test("/data/adb/modules", "755"),
    f'[ "$(/data/adb/magisk/busybox find "{ACTIVE_MODULE_DIR}" -mindepth 1 | /data/adb/magisk/busybox wc -l)" = "5" ]',
    _dir_test(ACTIVE_MODULE_DIR, "755"),
    _dir_test(f"{ACTIVE_MODULE_DIR}/bin", "755"),
    _file_test(f"{ACTIVE_MODULE_DIR}/module.prop", MODULE_PROP_SHA256, MODULE_PROP_SIZE, "644"),
    _file_test(f"{ACTIVE_MODULE_DIR}/skip_mount", EMPTY_SHA256, 0, "644"),
    _file_test(f"{ACTIVE_MODULE_DIR}/service.sh", SERVICE_SHA256, SERVICE_SIZE, "644"),
    _file_test(f"{ACTIVE_MODULE_DIR}/bin/s20plus_native_canary", BINARY_SHA256, BINARY_SIZE, "750"),
    f'[ ! -e "{ACTIVE_MODULE_DIR}/update" ] && [ ! -L "{ACTIVE_MODULE_DIR}/update" ]',
    f'[ ! -e "{ACTIVE_MODULE_DIR}/disable" ] && [ ! -L "{ACTIVE_MODULE_DIR}/disable" ]',
))


DISABLED_MODULE_TREE_TESTS = ACTIVE_MODULE_TREE_TESTS.replace(
    f'[ ! -e "{ACTIVE_MODULE_DIR}/disable" ] && [ ! -L "{ACTIVE_MODULE_DIR}/disable" ]',
    _file_test(f"{ACTIVE_MODULE_DIR}/disable", EMPTY_SHA256, 0, "644"),
).replace('= "5" ]', '= "6" ]', 1)

def expected_canary_intent(binding_sha256: str, run_nonce: str) -> bytes:
    if (
        re.fullmatch(r"[0-9a-f]{64}", binding_sha256) is None
        or re.fullmatch(r"[0-9a-f]{32}", run_nonce) is None
    ):
        raise RootDataError("N1 canary state binding is malformed")
    return (
        '{"schema":"s20plus_native_canary_n1_intent_v1",'
        f'"binding_sha256":"{binding_sha256}",'
        f'"run_nonce":"{run_nonce}",'
        '"replay_permitted":false}\n'
    ).encode("ascii")


def completed_state_tests(binding_sha256: str, run_nonce: str) -> str:
    intent_sha256 = hashlib.sha256(
        expected_canary_intent(binding_sha256, run_nonce)
    ).hexdigest()
    return " && ".join((
        _dir_test(STATE_PARENT, "700"),
        f'[ "$(/data/adb/magisk/busybox find "{STATE_PARENT}" -mindepth 1 -maxdepth 1 | /data/adb/magisk/busybox wc -l)" = "1" ]',
        _dir_test(STATE_DIR, "700"),
        f'[ "$(/data/adb/magisk/busybox find "{STATE_DIR}" -mindepth 1 -maxdepth 1 | /data/adb/magisk/busybox wc -l)" = "3" ]',
        _file_test(f"{STATE_DIR}/binding.txt", binding_sha256, DEVICE_BINDING_SIZE, "600"),
        _file_test(f"{STATE_DIR}/intent.json", intent_sha256, CANARY_INTENT_SIZE, "600"),
        f'[ -f "{STATE_DIR}/result.json" ] && [ ! -L "{STATE_DIR}/result.json" ]',
        f'[ "$(/data/adb/magisk/busybox stat -c %a "{STATE_DIR}/result.json")" = "600" ]',
        f'[ "$(/data/adb/magisk/busybox stat -c %u:%g:%h "{STATE_DIR}/result.json")" = "0:0:1" ]',
    ))


def active_audit_script(binding_sha256: str, run_nonce: str) -> str:
    return f"""set -eu
{ACTIVE_MODULE_TREE_TESTS}
{completed_state_tests(binding_sha256, run_nonce)}
printf 'PASS_N1_ACTIVE_AUDIT\\n'
"""


def disabled_audit_script(binding_sha256: str, run_nonce: str) -> str:
    return f"""set -eu
{DISABLED_MODULE_TREE_TESTS}
{completed_state_tests(binding_sha256, run_nonce)}
printf 'PASS_N1_DISABLED_AUDIT\\n'
"""


def disable_script(binding_sha256: str, run_nonce: str) -> str:
    return f"""set -eu
{ACTIVE_MODULE_TREE_TESTS}
{completed_state_tests(binding_sha256, run_nonce)}
: > {ACTIVE_MODULE_DIR}/disable
/data/adb/magisk/busybox chown 0:0 {ACTIVE_MODULE_DIR}/disable
/data/adb/magisk/busybox chmod 0644 {ACTIVE_MODULE_DIR}/disable
/data/adb/magisk/busybox sync
{DISABLED_MODULE_TREE_TESTS}
{completed_state_tests(binding_sha256, run_nonce)}
printf 'PASS_N1_DISABLE_EXACT\\n'
"""


def recovery_state_shell(binding_sha256: str, run_nonce: str) -> str:
    intent_sha256 = hashlib.sha256(
        expected_canary_intent(binding_sha256, run_nonce)
    ).hexdigest()
    return f"""
{_dir_test(STATE_PARENT, "700")}
state_parent_count=$(/data/adb/magisk/busybox find "{STATE_PARENT}" -mindepth 1 -maxdepth 1 | /data/adb/magisk/busybox wc -l)
[ "$state_parent_count" = "1" ]
{_dir_test(STATE_DIR, "700")}
{_file_test(f"{STATE_DIR}/binding.txt", binding_sha256, DEVICE_BINDING_SIZE, "600")}
state_count=$(/data/adb/magisk/busybox find "{STATE_DIR}" -mindepth 1 -maxdepth 1 | /data/adb/magisk/busybox wc -l)
case "$state_count" in
  1)
    [ ! -e "{STATE_DIR}/intent.json" ] && [ ! -L "{STATE_DIR}/intent.json" ]
    [ ! -e "{STATE_DIR}/result.json" ] && [ ! -L "{STATE_DIR}/result.json" ]
    state_class=binding-only
    ;;
  2)
    {_file_test(f"{STATE_DIR}/intent.json", intent_sha256, CANARY_INTENT_SIZE, "600")}
    [ ! -e "{STATE_DIR}/result.json" ] && [ ! -L "{STATE_DIR}/result.json" ]
    state_class=intent-only
    ;;
  3)
    {_file_test(f"{STATE_DIR}/intent.json", intent_sha256, CANARY_INTENT_SIZE, "600")}
    [ -f "{STATE_DIR}/result.json" ] && [ ! -L "{STATE_DIR}/result.json" ]
    [ "$(/data/adb/magisk/busybox stat -c %a "{STATE_DIR}/result.json")" = "600" ]
    [ "$(/data/adb/magisk/busybox stat -c %u:%g:%h "{STATE_DIR}/result.json")" = "0:0:1" ]
    state_class=completed
    ;;
  *) exit 91 ;;
esac
"""


def recovery_disable_script(binding_sha256: str, run_nonce: str) -> str:
    return f"""set -eu
{ACTIVE_MODULE_TREE_TESTS}
{recovery_state_shell(binding_sha256, run_nonce)}
: > {ACTIVE_MODULE_DIR}/disable
/data/adb/magisk/busybox chown 0:0 {ACTIVE_MODULE_DIR}/disable
/data/adb/magisk/busybox chmod 0644 {ACTIVE_MODULE_DIR}/disable
/data/adb/magisk/busybox sync
{DISABLED_MODULE_TREE_TESTS}
printf 'PASS_N1_RECOVERY_DISABLE_%s\\n' "$state_class"
"""


def recovery_source_audit_script(binding_sha256: str, run_nonce: str) -> str:
    return f"""set -eu
{ACTIVE_MODULE_TREE_TESTS}
{recovery_state_shell(binding_sha256, run_nonce)}
printf 'PASS_N1_RECOVERY_SOURCE_%s\n' "$state_class"
"""


def recovery_disabled_audit_script(
    binding_sha256: str,
    run_nonce: str,
) -> str:
    return f"""set -eu
{DISABLED_MODULE_TREE_TESTS}
{recovery_state_shell(binding_sha256, run_nonce)}
printf 'PASS_N1_RECOVERY_DISABLED_%s\\n' "$state_class"
"""


RECOVERY_STATE_OUTPUTS = {
    b"PASS_N1_RECOVERY_DISABLE_binding-only\n": "binding-only",
    b"PASS_N1_RECOVERY_DISABLE_intent-only\n": "intent-only",
    b"PASS_N1_RECOVERY_DISABLE_completed\n": "completed",
}
RECOVERY_SOURCE_OUTPUTS = {
    b"PASS_N1_RECOVERY_SOURCE_binding-only\n": "binding-only",
    b"PASS_N1_RECOVERY_SOURCE_intent-only\n": "intent-only",
    b"PASS_N1_RECOVERY_SOURCE_completed\n": "completed",
}
RECOVERY_AUDIT_OUTPUTS = {
    b"PASS_N1_RECOVERY_DISABLED_binding-only\n": "binding-only",
    b"PASS_N1_RECOVERY_DISABLED_intent-only\n": "intent-only",
    b"PASS_N1_RECOVERY_DISABLED_completed\n": "completed",
}
RECOVERY_STATE_ORDER = {
    "binding-only": 0,
    "intent-only": 1,
    "completed": 2,
}
COMPLETED_SOURCE_UNOBSERVED = "completed-source-unobserved"


def decode_recovery_state(
    result: tuple[int, bytes, bytes],
    label: str,
    expected: dict[bytes, str],
) -> str:
    rc, stdout, stderr = result
    if rc != 0 or stderr or stdout not in expected:
        raise RootDataError(f"{label} failed or returned an invalid state class")
    return expected[stdout]


def require_monotonic_recovery_state(before: str, after: str, label: str) -> None:
    if before not in RECOVERY_STATE_ORDER or after not in RECOVERY_STATE_ORDER:
        raise RootDataError(f"{label} contains an invalid recovery state")
    if RECOVERY_STATE_ORDER[after] < RECOVERY_STATE_ORDER[before]:
        raise RootDataError(f"{label} regressed during recovery")


def terminal_audit_state(state_class: str) -> str:
    if state_class == COMPLETED_SOURCE_UNOBSERVED:
        return "completed"
    return state_class


def install_script(binding_sha256: str) -> str:
    if re.fullmatch(r"[0-9a-f]{64}", binding_sha256) is None:
        raise RootDataError("N1 device binding hash is malformed")
    tests = POST_INSTALL_TESTS.replace("__BINDING_SHA256__", binding_sha256)
    return f"""set -eu
BB=/data/adb/magisk/busybox
[ -d {STAGE_DIR} ] && [ ! -L {STAGE_DIR} ]
[ "$($BB stat -c %a {STAGE_DIR})" = "700" ]
[ "$($BB stat -c %u:%g {STAGE_DIR})" = "2000:2000" ]
[ "$($BB find {STAGE_DIR} -mindepth 1 -maxdepth 1 | $BB wc -l)" = "2" ]
[ -f {STAGE_ZIP} ] && [ ! -L {STAGE_ZIP} ]
[ "$($BB stat -c %a {STAGE_ZIP})" = "600" ]
[ "$($BB stat -c %u:%g:%h {STAGE_ZIP})" = "2000:2000:1" ]
[ "$($BB sha256sum {STAGE_ZIP} | $BB cut -d' ' -f1)" = "{MODULE_ZIP_SHA256}" ]
[ "$($BB stat -c %s {STAGE_ZIP})" = "{MODULE_ZIP_SIZE}" ]
[ -f {STAGE_BINDING} ] && [ ! -L {STAGE_BINDING} ]
[ "$($BB stat -c %a {STAGE_BINDING})" = "600" ]
[ "$($BB stat -c %u:%g:%h {STAGE_BINDING})" = "2000:2000:1" ]
[ "$($BB stat -c %s {STAGE_BINDING})" = "{DEVICE_BINDING_SIZE}" ]
[ "$($BB sha256sum {STAGE_BINDING} | $BB cut -d' ' -f1)" = "{binding_sha256}" ]
[ ! -e {STATE_PARENT} ] && [ ! -L {STATE_PARENT} ]
$BB mkdir -m 0700 {STATE_PARENT}
$BB mkdir -m 0700 {STATE_DIR}
$BB cp {STAGE_BINDING} {STATE_DIR}/binding.txt
$BB chown 0:0 {STATE_DIR}/binding.txt
$BB chmod 0600 {STATE_DIR}/binding.txt
$BB sync
{MAGISK_BINARY} --install-module {STAGE_ZIP}
$BB chmod 0750 {UPDATE_MODULE_DIR}/bin/s20plus_native_canary
$BB sync
{tests}
printf 'PASS_N1_INSTALL_EXACT\\n'
"""


INSTALL_AUDIT_TEMPLATE = f"""set -eu
{POST_INSTALL_TESTS}
printf 'PASS_N1_POST_INSTALL_AUDIT\\n'
"""

CAT_INTENT_SCRIPT = f"exec /data/adb/magisk/busybox cat {STATE_DIR}/intent.json"
CAT_RESULT_SCRIPT = f"exec /data/adb/magisk/busybox cat {STATE_DIR}/result.json"

def cleanup_script(binding_sha256: str) -> str:
    if re.fullmatch(r"[0-9a-f]{64}", binding_sha256) is None:
        raise RootDataError("N1 cleanup binding hash is malformed")
    return f"""set -eu
BB=/system/bin/toybox
if [ -e {STAGE_DIR} ] || [ -L {STAGE_DIR} ]; then
  [ -d {STAGE_DIR} ] && [ ! -L {STAGE_DIR} ]
  [ "$($BB stat -c %a {STAGE_DIR})" = "700" ]
  [ "$($BB stat -c %u:%g {STAGE_DIR})" = "2000:2000" ]
  unexpected=$($BB find {STAGE_DIR} -mindepth 1 -maxdepth 1 ! -name '{MODULE_ID}.zip' ! -name 'binding.txt' -print | $BB wc -l)
  [ "$unexpected" = "0" ]
  if [ -e {STAGE_ZIP} ] || [ -L {STAGE_ZIP} ]; then
    [ -f {STAGE_ZIP} ] && [ ! -L {STAGE_ZIP} ]
    [ "$($BB stat -c %u:%g:%h {STAGE_ZIP})" = "2000:2000:1" ]
    case "$($BB stat -c %a {STAGE_ZIP})" in 600|666) ;; *) exit 92 ;; esac
    zip_size=$($BB stat -c %s {STAGE_ZIP})
    [ "$zip_size" -ge 0 ] && [ "$zip_size" -le "{MODULE_ZIP_SIZE}" ]
  fi
  if [ -e {STAGE_BINDING} ] || [ -L {STAGE_BINDING} ]; then
    [ -f {STAGE_BINDING} ] && [ ! -L {STAGE_BINDING} ]
    [ "$($BB stat -c %u:%g:%h {STAGE_BINDING})" = "2000:2000:1" ]
    case "$($BB stat -c %a {STAGE_BINDING})" in 444|600) ;; *) exit 93 ;; esac
    binding_size=$($BB stat -c %s {STAGE_BINDING})
    [ "$binding_size" -ge 0 ] && [ "$binding_size" -le "{DEVICE_BINDING_SIZE}" ]
  fi
  [ ! -e {STAGE_ZIP} ] || $BB rm -f {STAGE_ZIP}
  [ ! -e {STAGE_BINDING} ] || $BB rm -f {STAGE_BINDING}
  $BB rmdir {STAGE_DIR}
fi
$BB sync
[ ! -e {STAGE_DIR} ] && [ ! -L {STAGE_DIR} ]
printf 'PASS_N1_STAGE_CLEANUP\\n'
"""


CLEANUP_SCRIPT_TEMPLATE = cleanup_script("0" * 64)

STAGE_ABSENCE_SCRIPT = f"""set -eu
[ ! -e {STAGE_DIR} ] && [ ! -L {STAGE_DIR} ]
printf 'PASS_N1_STAGE_ABSENT\\n'
"""


def decode_exact(result: tuple[int, bytes, bytes], label: str, expected: bytes) -> bytes:
    rc, stdout, stderr = result
    if rc != 0 or stderr or stdout != expected:
        raise RootDataError(f"{label} failed or returned unexpected output")
    return stdout


INSTALL_SUCCESS_STDOUT = (
    b"- Device is system-as-root\n"
    b"****************************\n"
    b" S20+ Native Canary \n"
    b" by android-native-init-lab \n"
    b"****************************\n"
    b"*******************\n"
    b" Powered by Magisk \n"
    b"*******************\n"
    b"- Extracting module files\n"
    b"- Done\n"
    b"PASS_N1_INSTALL_EXACT\n"
)


def validate_install_output(result: tuple[int, bytes, bytes]) -> str:
    rc, stdout, stderr = result
    if rc != 0 or stderr or len(stdout) > MAX_OUTPUT:
        raise RootDataError("N1 exact Magisk install failed")
    if stdout != INSTALL_SUCCESS_STDOUT:
        raise RootDataError("N1 install output does not match the closed Magisk grammar")
    return hashlib.sha256(stdout).hexdigest()


def root_argv(adb: str, serial: str, script: str) -> list[str]:
    # ADB joins all arguments following `shell` with spaces and does not quote
    # them. Quote the complete fixed script for the remote shell so `su -c`
    # receives exactly one command argument rather than only its first token.
    return [adb, "-s", serial, "shell", "su", "-c", shlex.quote(script)]


def run_root_exact(
    command: Command,
    adb: str,
    serial: str,
    script: str,
    label: str,
    expected: bytes,
) -> str:
    output = decode_exact(command(root_argv(adb, serial, script), 180, MAX_OUTPUT), label, expected)
    return hashlib.sha256(output).hexdigest()


def durable_root_exact(
    run_dir: Path,
    evidence_label: str,
    command: Command,
    adb: str,
    serial: str,
    script: str,
    label: str,
    expected: bytes,
) -> str:
    result = durable_command_result(
        run_dir,
        evidence_label,
        root_argv(adb, serial, script),
        command,
        180,
        MAX_OUTPUT,
    )
    output = decode_exact(result, label, expected)
    return hashlib.sha256(output).hexdigest()


def parse_preflight(payload: bytes) -> dict[str, Any]:
    try:
        lines = payload.decode("utf-8", "strict").splitlines()
    except UnicodeError as exc:
        raise RootDataError("N1 preflight output is not UTF-8") from exc
    if lines != [
        "active=absent", "update=absent", "parent=absent", "state=absent", "stage=absent"
        , "active_count=0", "update_count=0"
    ]:
        raise RootDataError("N1 preflight state is not clean")
    inventory = b"active_count=0\nupdate_count=0\n"
    return {
        "active_count": 0,
        "update_count": 0,
        "inventory_sha256": hashlib.sha256(inventory).hexdigest(),
        "_module_inventory": inventory,
    }


def parse_magisk_install_closure(payload: bytes) -> dict[str, Any]:
    try:
        lines = payload.decode("ascii", "strict").splitlines()
    except UnicodeError as exc:
        raise RootDataError("N1 Magisk install closure is not ASCII") from exc
    expected = MAGISK_CLOSURE_EXPECTED
    if len(lines) != len(expected):
        raise RootDataError("N1 Magisk install closure has the wrong cardinality")
    receipts: dict[str, Any] = {}
    issues: list[str] = []
    for line, (label, path, modes, maximum) in zip(lines, expected, strict=True):
        fields = line.split("|")
        if (
            len(fields) == 3
            and fields[0] == label
            and fields[1] == "error"
            and fields[2] in MAGISK_CLOSURE_ERROR_TOKENS
        ):
            issues.append(f"{label}={fields[2]}")
            continue
        if len(fields) != 7 or fields[0] != label:
            raise RootDataError("N1 Magisk install closure is malformed")
        _label, mode, uid, gid, links, size_text, digest = fields
        if (
            mode not in modes
            or uid != "0"
            or gid != "0"
            or links != "1"
            or re.fullmatch(r"[1-9][0-9]{0,8}", size_text) is None
            or not 1 <= int(size_text) <= maximum
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
        ):
            issues.append(f"{label}=unsafe-metadata")
            continue
        receipts[label] = {
            "path": path,
            "mode": mode,
            "uid": 0,
            "gid": 0,
            "nlink": 1,
            "size": int(size_text),
            "sha256": digest,
        }
    if issues:
        raise RootDataError(
            "N1 Magisk install closure incompatible: " + ",".join(issues)
        )
    return receipts


def validate_magisk_install_closure(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "magisk", "busybox", "util_functions"
    }:
        raise RootDataError("N1 prepared Magisk install closure is malformed")
    for label, path, modes, maximum in MAGISK_CLOSURE_EXPECTED:
        receipt = value.get(label)
        if (
            not isinstance(receipt, dict)
            or set(receipt) != {
                "path", "mode", "uid", "gid", "nlink", "size", "sha256"
            }
            or receipt.get("path") != path
            or receipt.get("mode") not in modes
            or type(receipt.get("uid")) is not int
            or receipt.get("uid") != 0
            or type(receipt.get("gid")) is not int
            or receipt.get("gid") != 0
            or type(receipt.get("nlink")) is not int
            or receipt.get("nlink") != 1
            or type(receipt.get("size")) is not int
            or not 1 <= receipt.get("size", 0) <= maximum
            or not isinstance(receipt.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", receipt.get("sha256")) is None
        ):
            raise RootDataError("N1 prepared Magisk install closure changed")
    return value


def root_preflight(
    command: Command,
    adb: str,
    selected: dict[str, Any],
    identity: dict[str, str],
) -> dict[str, Any]:
    root = bootstrap.root_observation(command, adb, identity, timeout=30)
    if root.get("root_verified") is not True:
        raise RootDataError("N1 requires exact working Magisk root")
    serial = selected["serial"]
    closure_rc, closure_stdout, closure_stderr = command(
        root_argv(adb, serial, MAGISK_CLOSURE_SCRIPT), 30, MAX_OUTPUT
    )
    if closure_rc == MAGISK_CLOSURE_ROOT_CONTEXT_RC and not closure_stderr:
        raise RootDataError("N1 Magisk install closure root context is not exact")
    if closure_rc != 0 or closure_stderr:
        raise RootDataError("N1 Magisk install closure read failed")
    install_closure = parse_magisk_install_closure(closure_stdout)
    version_out, version_err = bootstrap.decode(
        command(root_argv(adb, serial, f"{MAGISK_BINARY} -v"), 20, MAX_OUTPUT),
        "Magisk version",
    )
    code_out, code_err = bootstrap.decode(
        command(root_argv(adb, serial, f"{MAGISK_BINARY} -V"), 20, MAX_OUTPUT),
        "Magisk version code",
    )
    if version_err or code_err or version_out != MAGISK_VERSION or code_out != MAGISK_VERSION_CODE:
        raise RootDataError("N1 Magisk version is not exact")
    rc, stdout, stderr = command(root_argv(adb, serial, PREFLIGHT_SCRIPT), 30, MAX_OUTPUT)
    if rc != 0 or stderr:
        raise RootDataError("N1 root-data preflight failed")
    state = parse_preflight(stdout)
    return {
        "root_observation_sha256": canonical_sha(root),
        "magisk_version": version_out,
        "magisk_version_code": code_out,
        "install_closure": install_closure,
        **state,
    }


def recovery_magisk_preflight(
    command: Command,
    adb: str,
    selected: dict[str, Any],
    identity: dict[str, str],
    prepared: dict[str, Any],
) -> dict[str, Any]:
    """Rebind exact read-only Magisk helper bytes before recovery use."""
    root = bootstrap.root_observation(command, adb, identity, timeout=60)
    if root.get("root_verified") is not True:
        raise RootDataError("N1 recovery requires exact working Magisk root")
    serial = selected["serial"]
    closure_rc, closure_stdout, closure_stderr = command(
        root_argv(adb, serial, MAGISK_CLOSURE_SCRIPT), 30, MAX_OUTPUT
    )
    if closure_rc == MAGISK_CLOSURE_ROOT_CONTEXT_RC and not closure_stderr:
        raise RootDataError("N1 recovery Magisk helper root context is not exact")
    if closure_rc != 0 or closure_stderr:
        raise RootDataError("N1 recovery Magisk helper closure read failed")
    current_closure = parse_magisk_install_closure(closure_stdout)
    version_out, version_err = bootstrap.decode(
        command(root_argv(adb, serial, f"{MAGISK_BINARY} -v"), 20, MAX_OUTPUT),
        "recovery Magisk version",
    )
    code_out, code_err = bootstrap.decode(
        command(root_argv(adb, serial, f"{MAGISK_BINARY} -V"), 20, MAX_OUTPUT),
        "recovery Magisk version code",
    )
    expected = prepared["binding"]["magisk"]
    if (
        version_err
        or code_err
        or version_out != MAGISK_VERSION
        or code_out != MAGISK_VERSION_CODE
        or version_out != expected.get("magisk_version")
        or code_out != expected.get("magisk_version_code")
        or not exact_typed_equal(
            current_closure,
            validate_magisk_install_closure(expected.get("install_closure")),
        )
    ):
        raise RootDataError("N1 recovery Magisk helper closure changed")
    return root


def post_stage_preflight(
    command: Command,
    adb: str,
    selected: dict[str, Any],
    identity: dict[str, str],
    prepared: dict[str, Any],
) -> None:
    """Rebind the target and exact helpers immediately before install intent."""
    recovery_magisk_preflight(command, adb, selected, identity, prepared)
    rc, stdout, stderr = command(
        root_argv(adb, selected["serial"], PREFLIGHT_SCRIPT),
        30,
        MAX_OUTPUT,
    )
    expected = (
        b"active=absent\nupdate=absent\nparent=absent\nstate=absent\n"
        b"stage=present\nactive_count=0\nupdate_count=0\n"
    )
    if type(rc) is not int or rc != 0 or stdout != expected or stderr != b"":
        raise RootDataError("N1 post-stage module baseline or stage presence changed")


def require_module_inventory(
    run_dir: Path,
    command: Command,
    adb: str,
    serial: str,
) -> str:
    initial = read_exact_blob(run_dir / "module-inventory.txt", "N1 initial module inventory", MAX_OUTPUT)
    if initial != b"active_count=0\nupdate_count=0\n":
        raise RootDataError("N1 initial module inventory is malformed")
    rc, stdout, stderr = command(root_argv(adb, serial, INVENTORY_SCRIPT), 30, MAX_OUTPUT)
    if rc != 0 or stderr:
        raise RootDataError("N1 current module inventory read failed")
    if stdout != b"active_count=1\nupdate_count=0\n":
        raise RootDataError("N1 module inventory drifted")
    return hashlib.sha256(stdout).hexdigest()


def durable_blob(path: Path, payload: bytes, mode: int = 0o400) -> None:
    """Publish only a complete fsynced inode under the final no-clobber name."""
    parent_descriptor = os.open(
        path.parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    descriptor = -1
    try:
        descriptor = os.open(
            ".",
            os.O_WRONLY | os.O_TMPFILE | os.O_CLOEXEC,
            mode,
            dir_fd=parent_descriptor,
        )
        os.fchmod(descriptor, mode)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise RootDataError("short N1 evidence write")
            offset += written
        os.fsync(descriptor)
        if _LINKAT(
            descriptor,
            b"",
            parent_descriptor,
            os.fsencode(path.name),
            AT_EMPTY_PATH,
        ) != 0:
            error_number = ctypes.get_errno()
            raise OSError(error_number, os.strerror(error_number), path)
        os.fsync(parent_descriptor)
    finally:
        try:
            if descriptor >= 0:
                os.close(descriptor)
        finally:
            os.close(parent_descriptor)


def durable_create(path: Path, value: Any) -> None:
    try:
        payload = json.dumps(
            value,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8") + b"\n"
    except (TypeError, ValueError) as exc:
        raise RootDataError("N1 durable JSON value is not serializable") from exc
    durable_blob(path, payload)


def read_exact_blob(path: Path, label: str, maximum: int) -> bytes:
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        metadata = os.fstat(descriptor)
    except (FileNotFoundError, OSError) as exc:
        raise RootDataError(f"{label} is missing or indirect") from exc
    try:
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_size > maximum:
            raise RootDataError(f"{label} is not an exact bounded regular file")
        payload = bytearray()
        while True:
            chunk = os.read(descriptor, min(64 * 1024, maximum + 1 - len(payload)))
            if not chunk:
                break
            payload.extend(chunk)
            if len(payload) > maximum:
                raise RootDataError(f"{label} is oversized")
        return bytes(payload)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise RootDataError("N1 JSON contains a duplicate key")
        value[key] = item
    return value


def reject_nonfinite_json_constant(value: str) -> Any:
    raise RootDataError(f"N1 JSON contains a non-finite constant: {value}")


def read_exact_json(path: Path, label: str) -> Any:
    payload = read_exact_blob(path, label, 1024 * 1024)
    try:
        return json.loads(
            payload.decode("utf-8", "strict"),
            object_pairs_hook=reject_duplicate_json_keys,
            parse_constant=reject_nonfinite_json_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RootDataError(f"{label} is malformed") from exc


def prepared_binding(
    run_dir: Path,
    artifacts: dict[str, Any],
    closure: dict[str, Any],
    identity: dict[str, str],
    preflight: dict[str, Any],
    binding_sha256: str,
    run_nonce: str,
) -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_native_canary_r1_binding_v1",
        "version": VERSION,
        "run_dir": str(run_dir),
        "target": {
            "model": bootstrap.EXPECTED_MODEL,
            "device": bootstrap.EXPECTED_DEVICE,
            "product": bootstrap.EXPECTED_PRODUCT,
            "incremental": bootstrap.EXPECTED_INCREMENTAL,
            **identity,
        },
        "magisk": preflight,
        "artifacts": artifacts,
        "closure": closure,
        "module_id": MODULE_ID,
        "state_dir": STATE_DIR,
        "stage_dir": STAGE_DIR,
        "device_binding_sha256": binding_sha256,
        "run_nonce": run_nonce,
        "normal_reboot_budget": 3,
        "install_attempts": 1,
        "disable_attempts": 1,
        "stock_recovery_attempts": 1,
        "install_replay": False,
        "reboot_replay": False,
        "stock_recovery_preapproved": True,
    }


def prepare(command: Command = bootstrap.bounded_command) -> Path:
    require_active()
    if os.path.lexists(guard_path()):
        raise RootDataError("another S20+ action remains unresolved")
    builder_module = load_candidate_builder()
    artifacts = validate_artifacts(builder_module)
    closure = closure_receipts()
    run_dir = allocate_run_dir()
    guard_claimed = False
    try:
        adb = closure["bootstrap"]["adb"]["path"]
        selected, _values, identity = bootstrap.android_health_once(command, adb)
        preflight = root_preflight(command, adb, selected, identity)
        inventory_bytes = preflight.pop("_module_inventory")
        if hashlib.sha256(inventory_bytes).hexdigest() != preflight["inventory_sha256"]:
            raise RootDataError("N1 private module inventory hash is inconsistent")
        durable_blob(run_dir / "module-inventory.txt", inventory_bytes)
        run_nonce = os.urandom(16).hex()
        device_binding = builder_module.render_binding(
            {"binary": artifacts["binary"], "module_zip": artifacts["module_zip"]},
            run_nonce=run_nonce,
            pre_boot_id_sha256=identity["boot_id_sha256"],
        )
        binding_path = run_dir / "device-binding.txt"
        durable_blob(binding_path, device_binding)
        device_binding_sha256 = hashlib.sha256(device_binding).hexdigest()
        binding = prepared_binding(
            run_dir,
            artifacts,
            closure,
            identity,
            preflight,
            device_binding_sha256,
            run_nonce,
        )
        binding_sha256 = canonical_sha(binding)
        prepared = {
            "schema": "s20plus_g986n_native_canary_r1_prepared_v1",
            "version": VERSION,
            "binding": binding,
            "binding_sha256": binding_sha256,
            "approval_token": APPROVAL_PREFIX + binding_sha256,
            "prepared_at": utc_now(),
        }
        durable_create(run_dir / "prepared.json", prepared)
        event(run_dir, 0, "prepared", {"binding_sha256": binding_sha256})
        try:
            durable_create(guard_path(), guard_value(run_dir))
            guard_claimed = True
        except Exception:
            if os.path.lexists(guard_path()):
                try:
                    read_guard(run_dir)
                    release_guard(run_dir)
                except RootDataError:
                    pass
            raise
        return run_dir
    except Exception:
        if guard_claimed:
            release_guard(run_dir)
        raise


PREPARED_FILES = {
    "device-binding.txt",
    "module-inventory.txt",
    "prepared.json",
    "events/00-native-canary-prepared.json",
}


def read_prepared(
    run_dir: Path,
    *,
    input_scope: str = "all",
    allow_released_terminal: bool = False,
) -> dict[str, Any]:
    validate_run_dir(run_dir)
    if os.path.lexists(guard_path()):
        read_guard(run_dir)
    elif not allow_released_terminal:
        raise RootDataError("N1 shared guard is missing")
    value = read_exact_json(run_dir / "prepared.json", "N1 prepared binding")
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "version", "binding", "binding_sha256", "approval_token", "prepared_at"}
        or value.get("schema") != "s20plus_g986n_native_canary_r1_prepared_v1"
        or value.get("version") != VERSION
        or value.get("binding_sha256") != canonical_sha(value.get("binding"))
        or value.get("approval_token") != APPROVAL_PREFIX + value["binding_sha256"]
        or not isinstance(value.get("prepared_at"), str)
    ):
        raise RootDataError("N1 prepared binding is malformed")
    binding = value["binding"]
    expected_keys = {
        "schema", "version", "run_dir", "target", "magisk", "artifacts", "closure",
        "module_id", "state_dir", "stage_dir",
        "device_binding_sha256", "run_nonce",
        "normal_reboot_budget", "install_attempts", "disable_attempts",
        "stock_recovery_attempts", "install_replay", "reboot_replay",
        "stock_recovery_preapproved",
    }
    target = binding.get("target", {}) if isinstance(binding, dict) else {}
    magisk = binding.get("magisk", {}) if isinstance(binding, dict) else {}
    if (
        not isinstance(binding, dict)
        or set(binding) != expected_keys
        or binding.get("schema") != "s20plus_g986n_native_canary_r1_binding_v1"
        or binding.get("version") != VERSION
        or binding.get("run_dir") != str(run_dir)
        or not isinstance(target, dict)
        or set(target) != {
            "model", "device", "product", "incremental",
            "serial_sha256", "topology_sha256", "boot_id_sha256",
        }
        or target.get("model") != bootstrap.EXPECTED_MODEL
        or target.get("device") != bootstrap.EXPECTED_DEVICE
        or target.get("product") != bootstrap.EXPECTED_PRODUCT
        or target.get("incremental") != bootstrap.EXPECTED_INCREMENTAL
        or target.get("topology_sha256") != bootstrap.EXPECTED_TOPOLOGY_SHA256
        or any(
            not isinstance(target.get(key), str)
            or re.fullmatch(r"[0-9a-f]{64}", target.get(key)) is None
            for key in ("serial_sha256", "topology_sha256", "boot_id_sha256")
        )
        or not isinstance(magisk, dict)
        or set(magisk) != {
            "root_observation_sha256", "magisk_version", "magisk_version_code",
            "install_closure", "active_count", "update_count", "inventory_sha256",
        }
        or not isinstance(magisk.get("root_observation_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", magisk.get("root_observation_sha256")) is None
        or magisk.get("magisk_version") != MAGISK_VERSION
        or magisk.get("magisk_version_code") != MAGISK_VERSION_CODE
        or validate_magisk_install_closure(magisk.get("install_closure"))
        != magisk.get("install_closure")
        or type(magisk.get("active_count")) is not int
        or magisk.get("active_count", -1) < 0
        or type(magisk.get("update_count")) is not int
        or magisk.get("update_count") != 0
        or not isinstance(magisk.get("inventory_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", magisk.get("inventory_sha256")) is None
        or binding.get("module_id") != MODULE_ID
        or binding.get("state_dir") != STATE_DIR
        or binding.get("stage_dir") != STAGE_DIR
        or not isinstance(binding.get("device_binding_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", binding.get("device_binding_sha256")) is None
        or not isinstance(binding.get("run_nonce"), str)
        or re.fullmatch(r"[0-9a-f]{32}", binding.get("run_nonce")) is None
        or type(binding.get("normal_reboot_budget")) is not int
        or binding.get("normal_reboot_budget") != 3
        or type(binding.get("install_attempts")) is not int
        or binding.get("install_attempts") != 1
        or type(binding.get("disable_attempts")) is not int
        or binding.get("disable_attempts") != 1
        or type(binding.get("stock_recovery_attempts")) is not int
        or binding.get("stock_recovery_attempts") != 1
        or binding.get("install_replay") is not False
        or binding.get("reboot_replay") is not False
        or binding.get("stock_recovery_preapproved") is not True
    ):
        raise RootDataError("N1 prepared binding changed")
    device_binding = read_exact_blob(run_dir / "device-binding.txt", "N1 device binding", MAX_STATE_FILE)
    if hashlib.sha256(device_binding).hexdigest() != binding["device_binding_sha256"]:
        raise RootDataError("N1 device binding changed")
    inventory = read_exact_blob(run_dir / "module-inventory.txt", "N1 module inventory", MAX_OUTPUT)
    if (
        inventory != b"active_count=0\nupdate_count=0\n"
        or magisk["active_count"] != 0
        or magisk["update_count"] != 0
    ):
        raise RootDataError("N1 module inventory evidence is inconsistent")
    inventory_sha = hashlib.sha256(inventory).hexdigest()
    if inventory_sha != binding.get("magisk", {}).get("inventory_sha256"):
        raise RootDataError("N1 module inventory evidence changed")
    if input_scope == "all":
        if (
            not exact_typed_equal(binding.get("artifacts"), validate_artifacts())
            or not exact_typed_equal(binding.get("closure"), closure_receipts())
        ):
            raise RootDataError("N1 execution-critical inputs changed")
    elif input_scope in {
        "root-recovery", "stock-recovery", "stock-finalize",
        "root-terminal-release", "stock-terminal-release",
        "post-install-resume",
    }:
        validate_recovery_inputs(value, input_scope, run_dir)
    else:
        raise RootDataError("N1 prepared input scope is invalid")
    return value


def prepared_cli_output(run_dir: Path) -> dict[str, str]:
    value = read_exact_json(run_dir / "prepared.json", "N1 prepared CLI result")
    if (
        not isinstance(value, dict)
        or set(value) != {
            "schema", "version", "binding", "binding_sha256", "approval_token", "prepared_at"
        }
        or value.get("schema") != "s20plus_g986n_native_canary_r1_prepared_v1"
        or value.get("version") != VERSION
        or not isinstance(value.get("binding"), dict)
        or not isinstance(value.get("binding_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", value["binding_sha256"]) is None
        or value["binding_sha256"] != canonical_sha(value["binding"])
        or value.get("approval_token") != APPROVAL_PREFIX + value["binding_sha256"]
        or not isinstance(value.get("prepared_at"), str)
        or RUN_ID_RE.fullmatch(run_dir.name) is None
    ):
        raise RootDataError("N1 prepared CLI approval binding is malformed")
    return {
        "schema": "s20plus_g986n_native_canary_r1_prepare_output_v1",
        "run_id": run_dir.name,
        "approval_token": value["approval_token"],
    }


def resume_prepared_cli_output() -> dict[str, str]:
    guard = read_exact_json(guard_path(), "N1 prepared-output shared guard")
    run_text = guard.get("run_dir") if isinstance(guard, dict) else None
    if not isinstance(run_text, str):
        raise RootDataError("N1 prepared-output guard is malformed")
    run_dir = Path(run_text)
    if (
        RUN_ID_RE.fullmatch(run_dir.name) is None
        or run_dir.parent != RUN_ROOT
        or not exact_typed_equal(guard, guard_value(run_dir))
    ):
        raise RootDataError("N1 prepared-output guard is not an exact R1 run")
    validate_run_dir(run_dir)
    read_guard(run_dir)
    require_exact_nodes(run_dir, PREPARED_FILES)
    prepared = read_exact_json(run_dir / "prepared.json", "N1 prepared output resume")
    validate_prepared_event(run_dir, prepared)
    return prepared_cli_output(run_dir)


def durable_command_result(
    run_dir: Path,
    label: str,
    argv: list[str],
    command: Command,
    timeout: float,
    maximum: int,
) -> tuple[int, bytes, bytes]:
    try:
        rc, stdout, stderr = command(argv, timeout, maximum)
        if (
            type(rc) is not int
            or not isinstance(stdout, bytes)
            or not isinstance(stderr, bytes)
            or len(stdout) + len(stderr) > maximum
        ):
            raise RootDataError("N1 command returned a malformed or oversized receipt")
        durable_blob(run_dir / f"{label}.stdout", stdout)
        durable_blob(run_dir / f"{label}.stderr", stderr)
        result = {
            "schema": "s20plus_g986n_native_canary_r1_command_result_v1",
            "version": VERSION,
            "label": label,
            "returncode": rc,
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "stdout_bytes": len(stdout),
            "stderr_bytes": len(stderr),
            "replay_permitted": False,
        }
    except Exception as exc:
        result = {
            "schema": "s20plus_g986n_native_canary_r1_command_failure_v1",
            "version": VERSION,
            "label": label,
            "failure_class": type(exc).__name__,
            "effect_outcome": "uncertain",
            "replay_permitted": False,
        }
        durable_create(run_dir / f"{label}-result.json", result)
        raise
    durable_create(run_dir / f"{label}-result.json", result)
    return rc, stdout, stderr


def validate_stage_host_inputs(run_dir: Path, prepared: dict[str, Any]) -> None:
    artifacts = prepared.get("binding", {}).get("artifacts", {})
    expected_zip = artifacts.get("module_zip") if isinstance(artifacts, dict) else None
    if (
        not isinstance(expected_zip, dict)
        or set(expected_zip) != {"path", "size", "sha256", "mode"}
        or expected_zip.get("mode") != "0600"
        or not exact_typed_equal(
            require_receipt(MODULE_ZIP, expected_zip, "N1 module ZIP stage source"),
            expected_zip,
        )
    ):
        raise RootDataError("N1 module ZIP stage source changed")
    binding = run_dir / "device-binding.txt"
    binding_receipt = exact_regular_receipt(
        binding,
        "N1 device binding",
        expected_mode=0o400,
    )
    if not exact_typed_equal(
        binding_receipt,
        {
            "path": str(binding.resolve(strict=True)),
            "size": DEVICE_BINDING_SIZE,
            "sha256": prepared["binding"]["device_binding_sha256"],
            "mode": "0400",
        },
    ):
        raise RootDataError("N1 device binding host receipt changed")


def stage_inputs(
    run_dir: Path,
    prepared: dict[str, Any],
    selected: dict[str, Any],
    command: Command,
) -> None:
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    serial = selected["serial"]
    binding = run_dir / "device-binding.txt"
    validate_stage_host_inputs(run_dir, prepared)
    claim = (
        f"set -eu; umask 077; [ ! -e {STAGE_DIR} ] && [ ! -L {STAGE_DIR} ]; "
        f"/system/bin/toybox mkdir -m 0700 {STAGE_DIR}; "
        f"[ -d {STAGE_DIR} ] && [ ! -L {STAGE_DIR} ]; "
        f"[ \"$(/system/bin/toybox stat -c %a {STAGE_DIR})\" = \"700\" ]; "
        f"[ \"$(/system/bin/toybox stat -c %u:%g {STAGE_DIR})\" = \"2000:2000\" ]; "
        f"[ \"$(/system/bin/toybox find {STAGE_DIR} -mindepth 1 -maxdepth 1 | /system/bin/toybox wc -l)\" = \"0\" ]; "
        "printf 'PASS_N1_STAGE_CLAIMED\\n'"
    )
    rc, stdout, stderr = durable_command_result(
        run_dir,
        "stage-claim",
        [adb, "-s", serial, "exec-out", "sh", "-c", claim],
        command,
        20,
        MAX_OUTPUT,
    )
    if rc != 0 or stderr or stdout != b"PASS_N1_STAGE_CLAIMED\n":
        raise RootDataError("N1 stage directory claim failed")
    for label, source, remote in (
        ("stage-zip", MODULE_ZIP, STAGE_ZIP),
        ("stage-binding", binding, STAGE_BINDING),
    ):
        rc, _stdout, _stderr = durable_command_result(
            run_dir, label, [adb, "-s", serial, "push", "-Z", str(source), remote], command, 300, MAX_OUTPUT
        )
        validate_stage_host_inputs(run_dir, prepared)
        if rc != 0:
            raise RootDataError(f"N1 {label} transfer failed")
    verify = (
        f"set -eu; /system/bin/toybox chmod 0600 {STAGE_ZIP} {STAGE_BINDING}; "
        f"[ -d {STAGE_DIR} ] && [ ! -L {STAGE_DIR} ]; "
        f"[ \"$(/system/bin/toybox stat -c %a {STAGE_DIR})\" = \"700\" ]; "
        f"[ \"$(/system/bin/toybox stat -c %u:%g {STAGE_DIR})\" = \"2000:2000\" ]; "
        f"[ \"$(/system/bin/toybox find {STAGE_DIR} -mindepth 1 -maxdepth 1 | /system/bin/toybox wc -l)\" = \"2\" ]; "
        f"[ -f {STAGE_ZIP} ] && [ ! -L {STAGE_ZIP} ]; "
        f"[ \"$(/system/bin/toybox stat -c %a {STAGE_ZIP})\" = \"600\" ]; "
        f"[ \"$(/system/bin/toybox stat -c %u:%g:%h {STAGE_ZIP})\" = \"2000:2000:1\" ]; "
        f"[ \"$(/system/bin/toybox stat -c %s {STAGE_ZIP})\" = \"{MODULE_ZIP_SIZE}\" ]; "
        f"[ \"$(/system/bin/toybox sha256sum {STAGE_ZIP} | /system/bin/toybox cut -d' ' -f1)\" = \"{MODULE_ZIP_SHA256}\" ]; "
        f"[ -f {STAGE_BINDING} ] && [ ! -L {STAGE_BINDING} ]; "
        f"[ \"$(/system/bin/toybox stat -c %a {STAGE_BINDING})\" = \"600\" ]; "
        f"[ \"$(/system/bin/toybox stat -c %u:%g:%h {STAGE_BINDING})\" = \"2000:2000:1\" ]; "
        f"[ \"$(/system/bin/toybox stat -c %s {STAGE_BINDING})\" = \"{DEVICE_BINDING_SIZE}\" ]; "
        f"[ \"$(/system/bin/toybox sha256sum {STAGE_BINDING} | /system/bin/toybox cut -d' ' -f1)\" = \"{prepared['binding']['device_binding_sha256']}\" ]; "
        "printf 'PASS_N1_STAGE_EXACT\\n'"
    )
    rc, stdout, stderr = durable_command_result(
        run_dir, "stage-verify", [adb, "-s", serial, "exec-out", "sh", "-c", verify], command, 30, MAX_OUTPUT
    )
    if rc != 0 or stderr or stdout != b"PASS_N1_STAGE_EXACT\n":
        raise RootDataError("N1 staged bytes are not exact")


def known_boot_ids_before_observation(
    run_dir: Path,
    prepared: dict[str, Any],
    phase: str,
) -> set[str]:
    observed_boot_ids = [prepared["binding"]["target"]["boot_id_sha256"]]
    for observed_phase in ("first", "replay", "disabled", "recovery-disabled"):
        if observed_phase == phase:
            continue
        path = run_dir / f"{observed_phase}-observation.json"
        if not os.path.lexists(path):
            continue
        observation = read_exact_json(
            path,
            f"N1 {observed_phase} prior reboot observation",
        )
        boot_id = observation.get("android_identity", {}).get("boot_id_sha256") \
            if isinstance(observation, dict) else None
        if not isinstance(boot_id, str) or re.fullmatch(r"[0-9a-f]{64}", boot_id) is None:
            raise RootDataError("N1 prior reboot observation boot ID is malformed")
        observed_boot_ids.append(boot_id)
    if len(set(observed_boot_ids)) != len(observed_boot_ids):
        raise RootDataError("N1 durable reboot history reuses an earlier boot ID")
    known = set(observed_boot_ids)
    for intent_name in (
        "first-reboot-intent.json",
        "replay-reboot-intent.json",
        "disabled-reboot-intent.json",
        "recovery-disabled-reboot-intent.json",
    ):
        path = run_dir / intent_name
        if not os.path.lexists(path):
            continue
        intent = read_exact_json(path, f"N1 {intent_name} boot history")
        boot_id = intent.get("prior_boot_id_sha256") \
            if isinstance(intent, dict) else None
        if not isinstance(boot_id, str) or re.fullmatch(r"[0-9a-f]{64}", boot_id) is None:
            raise RootDataError("N1 reboot-intent boot history is malformed")
        known.add(boot_id)
    for intent_name in ("disable-intent.json", "recovery-disable-intent.json"):
        path = run_dir / intent_name
        if not os.path.lexists(path):
            continue
        intent = read_exact_json(path, f"N1 {intent_name} source boot history")
        boot_id = intent.get("source_identity", {}).get("boot_id_sha256") \
            if isinstance(intent, dict) else None
        if not isinstance(boot_id, str) or re.fullmatch(r"[0-9a-f]{64}", boot_id) is None:
            raise RootDataError("N1 disable source boot history is malformed")
        known.add(boot_id)
    return known


def read_live_canary_pair(
    prepared: dict[str, Any],
    selected: dict[str, Any],
    command: Command,
) -> tuple[bytes, bytes, dict[str, Any]]:
    """Read and validate the current fixed canary pair without publishing it."""
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    values: list[bytes] = []
    for label, script in (
        ("intent", CAT_INTENT_SCRIPT),
        ("result", CAT_RESULT_SCRIPT),
    ):
        rc, stdout, stderr = command(
            root_argv(adb, selected["serial"], script),
            30,
            MAX_STATE_FILE,
        )
        if (
            type(rc) is not int
            or rc != 0
            or not isinstance(stdout, bytes)
            or not isinstance(stderr, bytes)
            or stderr
            or not 0 < len(stdout) <= MAX_STATE_FILE
        ):
            raise RootDataError(f"N1 live canary {label} read is not exact")
        values.append(stdout)
    intent, result = values
    return intent, result, validate_canary_files(intent, result, prepared)


def revalidate_reboot_source(
    run_dir: Path,
    phase: str,
    prepared: dict[str, Any],
    selected: dict[str, Any],
    prior_identity: dict[str, str],
    command: Command,
    minimum_recovery_state: str | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Rebind the exact source boot and branch state before a reboot effect."""
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    current_selected, _values, current_identity = bootstrap.android_health_once(
        command, adb
    )
    if (
        not exact_typed_equal(current_identity, prior_identity)
        or current_selected.get("serial") != selected.get("serial")
    ):
        raise RootDataError("N1 reboot source boot changed before dispatch")
    recovery_magisk_preflight(
        command,
        adb,
        current_selected,
        current_identity,
        prepared,
    )
    binding = prepared["binding"]
    if phase == "first":
        decode_exact(
            command(
                root_argv(
                    adb,
                    current_selected["serial"],
                    INSTALL_AUDIT_TEMPLATE.replace(
                        "__BINDING_SHA256__",
                        binding["device_binding_sha256"],
                    ),
                ),
                30,
                MAX_OUTPUT,
            ),
            "N1 first reboot source audit",
            b"PASS_N1_POST_INSTALL_AUDIT\n",
        )
    else:
        require_module_inventory(
            run_dir,
            command,
            adb,
            current_selected["serial"],
        )
        if phase == "replay":
            script = active_audit_script(
                binding["device_binding_sha256"], binding["run_nonce"]
            )
            expected = b"PASS_N1_ACTIVE_AUDIT\n"
            decode_exact(
                command(
                    root_argv(adb, current_selected["serial"], script),
                    30,
                    MAX_OUTPUT,
                ),
                "N1 replay reboot source audit",
                expected,
            )
            prior_intent, prior_result, _parsed = read_canary_pair(
                run_dir,
                prepared,
                "first",
            )
            live_intent, live_result, _live_parsed = read_live_canary_pair(
                prepared,
                current_selected,
                command,
            )
            if (live_intent, live_result) != (prior_intent, prior_result):
                raise RootDataError("N1 replay reboot source canary bytes changed")
        elif phase == "disabled":
            script = disabled_audit_script(
                binding["device_binding_sha256"], binding["run_nonce"]
            )
            decode_exact(
                command(
                    root_argv(adb, current_selected["serial"], script),
                    30,
                    MAX_OUTPUT,
                ),
                "N1 disabled reboot source audit",
                b"PASS_N1_DISABLED_AUDIT\n",
            )
            prior_intent, prior_result, _parsed = read_canary_pair(
                run_dir,
                prepared,
                "first",
            )
            live_intent, live_result, _live_parsed = read_live_canary_pair(
                prepared,
                current_selected,
                command,
            )
            if (live_intent, live_result) != (prior_intent, prior_result):
                raise RootDataError("N1 disabled reboot source canary bytes changed")
        elif phase == "recovery-disabled":
            if minimum_recovery_state not in RECOVERY_STATE_ORDER:
                raise RootDataError(
                    "N1 Android-recovery reboot source state is not bound"
                )
            script = recovery_disabled_audit_script(
                binding["device_binding_sha256"], binding["run_nonce"]
            )
            current_state = decode_recovery_state(
                command(
                    root_argv(adb, current_selected["serial"], script),
                    30,
                    MAX_OUTPUT,
                ),
                "N1 Android-recovery reboot source audit",
                RECOVERY_AUDIT_OUTPUTS,
            )
            require_monotonic_recovery_state(
                minimum_recovery_state,
                current_state,
                "N1 Android-recovery reboot source state",
            )
            if current_state == "completed":
                prior_intent, prior_result, _parsed = read_canary_pair(
                    run_dir,
                    prepared,
                    "recovery",
                )
                live_intent, live_result, _live_parsed = read_live_canary_pair(
                    prepared,
                    current_selected,
                    command,
                )
                if (live_intent, live_result) != (prior_intent, prior_result):
                    raise RootDataError(
                        "N1 Android-recovery reboot source canary bytes changed"
                    )
        else:
            raise RootDataError("N1 reboot source phase is not allowlisted")
    return current_selected, current_identity


def dispatch_reboot(
    run_dir: Path,
    phase: str,
    prepared: dict[str, Any],
    selected: dict[str, Any],
    prior_identity: dict[str, str],
    command: Command,
    *,
    minimum_recovery_state: str | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    if phase not in {"first", "replay", "disabled", "recovery-disabled"}:
        raise RootDataError("N1 reboot phase is not allowlisted")
    intent_path = run_dir / f"{phase}-reboot-intent.json"
    if os.path.lexists(intent_path):
        raise RootDataError("N1 reboot intent already exists; replay forbidden")
    selected, prior_identity = revalidate_reboot_source(
        run_dir,
        phase,
        prepared,
        selected,
        prior_identity,
        command,
        minimum_recovery_state,
    )
    intent = {
        "schema": "s20plus_g986n_native_canary_r1_reboot_intent_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "phase": phase,
        "prior_boot_id_sha256": prior_identity["boot_id_sha256"],
        "attempt": 1,
        "replay_permitted": False,
        "at": utc_now(),
    }
    durable_create(intent_path, intent)
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    rc, stdout, stderr = durable_command_result(
        run_dir,
        f"{phase}-reboot",
        [adb, "-s", selected["serial"], "reboot"],
        command,
        20,
        MAX_OUTPUT,
    )
    if rc != 0 or stdout or stderr:
        raise RootDataError("N1 reboot dispatch is uncertain; replay forbidden")
    returned = bootstrap.wait_android(command, adb, ANDROID_WAIT)
    if returned is None:
        raise RootDataError("N1 Android return was not observed; recovery required")
    current_selected, _values, identity = returned
    known_boot_ids = known_boot_ids_before_observation(run_dir, prepared, phase)
    if (
        identity.get("serial_sha256") != prior_identity.get("serial_sha256")
        or identity.get("topology_sha256") != prior_identity.get("topology_sha256")
        or identity.get("boot_id_sha256") == prior_identity.get("boot_id_sha256")
        or identity.get("boot_id_sha256") in known_boot_ids
    ):
        raise RootDataError("N1 reboot lost exact target or reused a boot identity")
    root = bootstrap.root_observation(command, adb, identity, timeout=60)
    if root.get("root_verified") is not True:
        raise RootDataError("N1 rooted Android health was not re-established")
    observation = {
        "schema": "s20plus_g986n_native_canary_r1_reboot_observation_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "phase": phase,
        "android_identity": identity,
        "root_observation": root,
        "dispatch_evidence": "complete-success",
        "replay_permitted": False,
        "at": utc_now(),
    }
    durable_create(run_dir / f"{phase}-observation.json", observation)
    return current_selected, identity


def reboot_dispatch_evidence_class(run_dir: Path, phase: str) -> str:
    evidence = validate_command_evidence(
        run_dir,
        f"{phase}-reboot",
        allow_uncertain_consumed=True,
    )
    if (
        isinstance(evidence, dict)
        and evidence.get("schema")
        == "s20plus_g986n_native_canary_r1_command_result_v1"
        and evidence.get("returncode") == 0
        and evidence.get("stdout_bytes") == 0
        and evidence.get("stderr_bytes") == 0
    ):
        return "complete-success"
    return "consumed-unproved"


def resume_reboot_observation(
    run_dir: Path,
    phase: str,
    prepared: dict[str, Any],
    command: Command,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Observe an already-consumed reboot intent without dispatching it again."""
    intent_path = run_dir / f"{phase}-reboot-intent.json"
    if not os.path.lexists(intent_path):
        raise RootDataError(f"N1 {phase} reboot resume has no durable intent")
    validate_reboot_evidence(run_dir, prepared, phase)
    intent = read_exact_json(intent_path, f"N1 {phase} reboot intent")
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    selected, _values, identity = bootstrap.android_health_once(command, adb)
    require_returned_target(prepared, identity, f"N1 {phase} reboot resume target")
    if identity.get("boot_id_sha256") == intent.get("prior_boot_id_sha256"):
        raise RootDataError(f"N1 {phase} reboot remains unproved; replay forbidden")
    if identity.get("boot_id_sha256") in known_boot_ids_before_observation(
        run_dir,
        prepared,
        phase,
    ):
        raise RootDataError(f"N1 {phase} reboot reused an earlier boot identity")
    root = bootstrap.root_observation(command, adb, identity, timeout=60)
    if root.get("root_verified") is not True:
        raise RootDataError(f"N1 {phase} reboot resume did not recover exact root")
    observation_path = run_dir / f"{phase}-observation.json"
    if os.path.lexists(observation_path):
        observation = read_exact_json(
            observation_path, f"N1 {phase} reboot observation"
        )
        if not exact_typed_equal(observation.get("android_identity"), identity):
            raise RootDataError(f"N1 {phase} reboot observation is no longer current")
        validate_reboot_evidence(run_dir, prepared, phase)
        return selected, identity
    durable_create(observation_path, {
        "schema": "s20plus_g986n_native_canary_r1_reboot_observation_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "phase": phase,
        "android_identity": identity,
        "root_observation": root,
        "dispatch_evidence": reboot_dispatch_evidence_class(run_dir, phase),
        "replay_permitted": False,
        "at": utc_now(),
    })
    validate_reboot_evidence(run_dir, prepared, phase)
    return selected, identity


RESULT_KEYS = [
    "schema", "binding_sha256", "run_nonce", "target_model", "target_device",
    "target_product", "target_incremental", "pid", "ppid", "uid", "gid",
    "selinux_context", "cap_eff", "cap_prm", "cap_bnd", "no_new_privs",
    "monotonic_sec", "monotonic_nsec", "self_sha256", "self_size",
    "boot_id_sha256", "pre_boot_id_changed", "mnt_ns", "pid_ns", "uts_ns",
    "net_ns", "replay_permitted",
]


def strict_json(payload: bytes, label: str) -> tuple[dict[str, Any], list[str]]:
    if len(payload) > MAX_STATE_FILE or not payload.endswith(b"\n") or b"\x00" in payload or b"\r" in payload:
        raise RootDataError(f"{label} bytes are malformed")
    pairs: list[tuple[str, Any]] = []

    def hook(items: list[tuple[str, Any]]) -> dict[str, Any]:
        pairs.extend(items)
        if len({key for key, _ in items}) != len(items):
            raise RootDataError(f"{label} contains duplicate keys")
        return dict(items)

    try:
        value = json.loads(payload.decode("utf-8", "strict"), object_pairs_hook=hook)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RootDataError(f"{label} JSON is malformed") from exc
    if not isinstance(value, dict):
        raise RootDataError(f"{label} is not an object")
    return value, [key for key, _ in pairs]


def validate_canary_files(
    intent_bytes: bytes,
    result_bytes: bytes,
    prepared: dict[str, Any],
) -> dict[str, Any]:
    binding = prepared["binding"]
    expected_intent = (
        '{"schema":"s20plus_native_canary_n1_intent_v1",'
        f'"binding_sha256":"{binding["device_binding_sha256"]}",'
        f'"run_nonce":"{binding["run_nonce"]}",'
        '"replay_permitted":false}\n'
    ).encode("ascii")
    if intent_bytes != expected_intent:
        raise RootDataError("N1 canary intent is malformed or mismatched")
    result, order = strict_json(result_bytes, "N1 canary result")
    integer_keys = ("pid", "ppid", "uid", "gid", "monotonic_sec", "monotonic_nsec", "self_size")
    namespace_values: dict[str, int] = {}
    for name in ("mnt", "pid", "uts", "net"):
        value = result.get(f"{name}_ns")
        match = (
            re.fullmatch(fr"{name}:\[([1-9][0-9]*)\]", value)
            if isinstance(value, str)
            else None
        )
        if match is None:
            raise RootDataError("N1 canary result is malformed or mismatched")
        digits = match.group(1)
        if len(digits) > 20:
            raise RootDataError("N1 canary namespace inode is out of range")
        namespace_values[name] = int(digits)
    try:
        canonical_result = (
            json.dumps(
                {key: result[key] for key in RESULT_KEYS},
                ensure_ascii=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("ascii")
    except (KeyError, UnicodeError) as exc:
        raise RootDataError("N1 canary result is not canonical ASCII") from exc
    if (
        result_bytes != canonical_result
        or order != RESULT_KEYS
        or set(result) != set(RESULT_KEYS)
        or result.get("schema") != "s20plus_native_canary_n1_result_v1"
        or result.get("binding_sha256") != binding["device_binding_sha256"]
        or result.get("run_nonce") != binding["run_nonce"]
        or result.get("target_model") != bootstrap.EXPECTED_MODEL
        or result.get("target_device") != bootstrap.EXPECTED_DEVICE
        or result.get("target_product") != bootstrap.EXPECTED_PRODUCT
        or result.get("target_incremental") != bootstrap.EXPECTED_INCREMENTAL
        or any(not isinstance(result.get(key), int) or isinstance(result.get(key), bool) for key in integer_keys)
        or not 1 <= result.get("pid", 0) <= 2_147_483_647
        or not 0 <= result.get("ppid", -1) <= 2_147_483_647
        or not 0 <= result.get("monotonic_sec", -1) <= 9_223_372_036_854_775_807
        or not 0 <= result.get("monotonic_nsec", -1) <= 999_999_999
        or result.get("uid") != 0
        or result.get("gid") != 0
        or result.get("self_sha256") != BINARY_SHA256
        or result.get("self_size") != BINARY_SIZE
        or not isinstance(result.get("boot_id_sha256"), str)
        or result.get("boot_id_sha256") == binding["target"]["boot_id_sha256"]
        or re.fullmatch(r"[0-9a-f]{64}", result.get("boot_id_sha256")) is None
        or result.get("pre_boot_id_changed") is not True
        or result.get("replay_permitted") is not False
        or result.get("no_new_privs") not in {"0", "1"}
        or any(
            not isinstance(result.get(key), str)
            or re.fullmatch(r"[0-9a-f]{16}", result.get(key)) is None
            for key in ("cap_eff", "cap_prm", "cap_bnd")
        )
        or any(value > 18_446_744_073_709_551_615 for value in namespace_values.values())
        or result.get("selinux_context") != "u:r:magisk:s0"
    ):
        raise RootDataError("N1 canary result is malformed or mismatched")
    return result


def read_state_files(
    run_dir: Path,
    label: str,
    prepared: dict[str, Any],
    selected: dict[str, Any],
    command: Command,
) -> tuple[bytes, bytes, dict[str, Any]]:
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    outputs: list[bytes] = []
    for kind, script in (("intent", CAT_INTENT_SCRIPT), ("result", CAT_RESULT_SCRIPT)):
        rc, stdout, stderr = command(root_argv(adb, selected["serial"], script), 20, MAX_STATE_FILE)
        if rc != 0 or stderr:
            raise RootDataError(f"N1 {kind} read failed")
        durable_blob(run_dir / f"{label}-{kind}.raw", stdout)
        outputs.append(stdout)
    result = validate_canary_files(outputs[0], outputs[1], prepared)
    return outputs[0], outputs[1], result


def read_or_collect_state_files(
    run_dir: Path,
    label: str,
    prepared: dict[str, Any],
    selected: dict[str, Any],
    command: Command,
) -> tuple[bytes, bytes, dict[str, Any]]:
    intent_path = run_dir / f"{label}-intent.raw"
    result_path = run_dir / f"{label}-result.raw"
    present = (os.path.lexists(intent_path), os.path.lexists(result_path))
    if present == (False, False):
        return read_state_files(run_dir, label, prepared, selected, command)
    if present == (False, True):
        raise RootDataError(
            f"N1 {label} canary result has no preceding intent observation"
        )
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    values: dict[str, bytes] = {}
    for kind, path, script in (
        ("intent", intent_path, CAT_INTENT_SCRIPT),
        ("result", result_path, CAT_RESULT_SCRIPT),
    ):
        if os.path.lexists(path):
            values[kind] = read_exact_blob(
                path,
                f"N1 {label} canary {kind}",
                MAX_STATE_FILE,
            )
            continue
        rc, stdout, stderr = command(
            root_argv(adb, selected["serial"], script),
            20,
            MAX_STATE_FILE,
        )
        if type(rc) is not int or rc != 0 or not isinstance(stdout, bytes) or stderr != b"":
            raise RootDataError(f"N1 {label} missing canary {kind} read failed")
        durable_blob(path, stdout)
        values[kind] = stdout
    intent = values["intent"]
    result = values["result"]
    return intent, result, validate_canary_files(intent, result, prepared)


def cleanup_stage(
    run_dir: Path,
    prepared: dict[str, Any],
    selected: dict[str, Any],
    command: Command,
) -> None:
    if os.path.lexists(run_dir / "cleanup-intent.json"):
        validate_optional_effect_intents(run_dir, prepared)
        receipt = validate_command_evidence(run_dir, "cleanup")
        if (
            receipt is None
            or receipt.get("schema")
            != "s20plus_g986n_native_canary_r1_command_result_v1"
            or receipt.get("returncode") != 0
        ):
            raise RootDataError("N1 cleanup remains uncertain; replay forbidden")
        stdout = read_exact_blob(run_dir / "cleanup.stdout", "N1 cleanup stdout", MAX_OUTPUT)
        stderr = read_exact_blob(run_dir / "cleanup.stderr", "N1 cleanup stderr", MAX_OUTPUT)
        decode_exact((receipt["returncode"], stdout, stderr), "N1 staged-input cleanup", b"PASS_N1_STAGE_CLEANUP\n")
        return
    durable_create(run_dir / "cleanup-intent.json", {
        "schema": "s20plus_g986n_native_canary_r1_cleanup_intent_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "stage_dir": STAGE_DIR,
        "attempt": 1,
        "replay_permitted": False,
        "at": utc_now(),
    })
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    result = durable_command_result(
        run_dir,
        "cleanup",
        [
            adb,
            "-s",
            selected["serial"],
            "exec-out",
            "sh",
            "-c",
            cleanup_script(prepared["binding"]["device_binding_sha256"]),
        ],
        command,
        30,
        MAX_OUTPUT,
    )
    decode_exact(result, "N1 staged-input cleanup", b"PASS_N1_STAGE_CLEANUP\n")


def stage_absence_evidence(
    command: Command,
    adb: str,
    selected: dict[str, Any],
) -> dict[str, Any]:
    script = (
        f"set -eu; /system/bin/toybox df -k {STAGE_PARENT} >/dev/null 2>&1; "
        f"[ -d {STAGE_PARENT} ] && [ ! -L {STAGE_PARENT} ] && "
        f"[ -w {STAGE_PARENT} ] && [ -x {STAGE_PARENT} ]; "
        f"[ ! -e {STAGE_DIR} ] && [ ! -L {STAGE_DIR} ]; "
        "printf 'PASS_N1_STAGE_ABSENT\\n'"
    )
    rc, stdout, stderr = command(
        [adb, "-s", selected["serial"], "exec-out", "sh", "-c", script],
        20,
        MAX_OUTPUT,
    )
    if (
        type(rc) is not int
        or not isinstance(stdout, bytes)
        or not isinstance(stderr, bytes)
        or rc != 0
        or stdout != b"PASS_N1_STAGE_ABSENT\n"
        or stderr != b""
    ):
        raise RootDataError("N1 final staged-input absence is not exact")
    return {
        "returncode": 0,
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "staged_input_absent": True,
    }


def terminal_input_value(
    prepared: dict[str, Any],
    verdict: str,
    identity: dict[str, str],
    result_sha256: str | None,
    recovery: str,
    canary_state_class: str,
    install_intent_count: int,
    require_boot_change: bool,
    at: str,
) -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_native_canary_r1_terminal_input_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "verdict": verdict,
        "target_identity": identity,
        "canary_result_sha256": result_sha256,
        "recovery": recovery,
        "canary_state_class": canary_state_class,
        "install_intent_count": install_intent_count,
        "require_boot_change": require_boot_change,
        "at": at,
    }


def stock_terminal_semantics(stock_transfer_state: str) -> dict[str, str]:
    if stock_transfer_state == "odin_transfer_completed":
        return {
            "verdict": "RECOVERED_S20PLUS_G986N_NATIVE_CANARY_N1_TO_STOCK_HEALTHY",
            "recovery": "stock",
            "canary_state_class": "unobserved-under-stock",
            "module_terminal": "inactive-under-stock-boot",
        }
    if stock_transfer_state in {
        "odin_device_session_failure_or_unknown",
        "odin_local_parse_failure",
        "odin_effect_outcome_unproved_after_intent",
    }:
        return {
            "verdict": (
                "RECOVERED_S20PLUS_G986N_NATIVE_CANARY_N1_"
                "ROOT_ABSENT_AFTER_CONSUMED_STOCK_ATTEMPT"
            ),
            "recovery": "stock-attempt-unproved",
            "canary_state_class": "unobserved-under-root-absent",
            "module_terminal": "inactive-under-root-absent-boot",
        }
    raise RootDataError("N1 stock terminal transfer state is invalid")


def stock_terminal_input_value(
    prepared: dict[str, Any],
    verdict: str,
    identity: dict[str, str],
    stock_transfer_state: str,
    stock_final_health_sha256: str,
    stock_root_absence_sha256: str,
    at: str,
) -> dict[str, Any]:
    semantics = stock_terminal_semantics(stock_transfer_state)
    if verdict != semantics["verdict"]:
        raise RootDataError("N1 stock terminal verdict overclaims transfer provenance")
    return {
        "schema": "s20plus_g986n_native_canary_r1_stock_terminal_input_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "verdict": verdict,
        "target_identity": identity,
        "recovery": semantics["recovery"],
        "canary_state_class": semantics["canary_state_class"],
        "install_intent_count": 1,
        "require_boot_change": True,
        "stock_transfer_state": stock_transfer_state,
        "stock_final_health_sha256": stock_final_health_sha256,
        "stock_root_absence_sha256": stock_root_absence_sha256,
        "at": at,
    }


def write_stock_terminal_input(
    run_dir: Path,
    prepared: dict[str, Any],
    verdict: str,
    identity: dict[str, str],
    *,
    stock_transfer_state: str,
    stock_final_health_sha256: str,
    stock_root_absence_sha256: str,
) -> dict[str, Any]:
    require_returned_target(prepared, identity, "N1 stock terminal-input target")
    if stock_transfer_state not in {
        "odin_transfer_completed",
        "odin_device_session_failure_or_unknown",
        "odin_local_parse_failure",
        "odin_effect_outcome_unproved_after_intent",
    }:
        raise RootDataError("N1 stock terminal-input transfer state is invalid")
    for label, digest in (
        ("health", stock_final_health_sha256),
        ("root absence", stock_root_absence_sha256),
    ):
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise RootDataError(f"N1 stock terminal-input {label} hash is invalid")
    path = run_dir / "terminal-input.json"
    existing = read_exact_json(path, "N1 stock terminal input") \
        if os.path.lexists(path) else None
    value = stock_terminal_input_value(
        prepared,
        verdict,
        identity,
        stock_transfer_state,
        stock_final_health_sha256,
        stock_root_absence_sha256,
        existing.get("at") if isinstance(existing, dict) else utc_now(),
    )
    if existing is None:
        durable_create(path, value)
    elif not exact_typed_equal(existing, value) or not isinstance(existing.get("at"), str):
        raise RootDataError("N1 existing stock terminal input is malformed or mismatched")
    return value


def read_stock_terminal_input(run_dir: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    value = read_exact_json(run_dir / "terminal-input.json", "N1 stock terminal input")
    if (
        not isinstance(value, dict)
        or set(value) != {
            "schema", "version", "binding_sha256", "verdict", "target_identity",
            "recovery", "canary_state_class", "install_intent_count",
            "require_boot_change", "stock_transfer_state",
            "stock_final_health_sha256", "stock_root_absence_sha256", "at",
        }
        or value.get("schema")
        != "s20plus_g986n_native_canary_r1_stock_terminal_input_v1"
        or value.get("version") != VERSION
        or value.get("binding_sha256") != prepared["binding_sha256"]
        or type(value.get("install_intent_count")) is not int
        or value.get("install_intent_count") != 1
        or value.get("require_boot_change") is not True
        or value.get("stock_transfer_state") not in {
            "odin_transfer_completed",
            "odin_device_session_failure_or_unknown",
            "odin_local_parse_failure",
            "odin_effect_outcome_unproved_after_intent",
        }
        or not isinstance(value.get("verdict"), str)
        or not isinstance(value.get("at"), str)
        or any(
            not isinstance(value.get(key), str)
            or re.fullmatch(r"[0-9a-f]{64}", value.get(key)) is None
            for key in ("stock_final_health_sha256", "stock_root_absence_sha256")
        )
    ):
        raise RootDataError("N1 stock terminal input is malformed")
    semantics = stock_terminal_semantics(value["stock_transfer_state"])
    if (
        value.get("verdict") != semantics["verdict"]
        or value.get("recovery") != semantics["recovery"]
        or value.get("canary_state_class") != semantics["canary_state_class"]
    ):
        raise RootDataError("N1 stock terminal input overclaims transfer provenance")
    require_returned_target(prepared, value["target_identity"], "N1 stock terminal-input target")
    return value


def write_terminal_input(
    run_dir: Path,
    prepared: dict[str, Any],
    verdict: str,
    identity: dict[str, str],
    result_sha256: str | None,
    *,
    recovery: str,
    canary_state_class: str,
    install_intent_count: int = 1,
    require_boot_change: bool = True,
) -> dict[str, Any]:
    require_returned_target(
        prepared,
        identity,
        "N1 terminal-input target",
        require_boot_change=require_boot_change,
    )
    path = run_dir / "terminal-input.json"
    existing = read_exact_json(path, "N1 terminal input") \
        if os.path.lexists(path) else None
    value = terminal_input_value(
        prepared,
        verdict,
        identity,
        result_sha256,
        recovery,
        canary_state_class,
        install_intent_count,
        require_boot_change,
        existing.get("at") if isinstance(existing, dict) else utc_now(),
    )
    if existing is None:
        durable_create(path, value)
    elif not exact_typed_equal(existing, value) or not isinstance(existing.get("at"), str):
        raise RootDataError("N1 existing terminal input is malformed or mismatched")
    return value


def read_terminal_input(run_dir: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    value = read_exact_json(run_dir / "terminal-input.json", "N1 terminal input")
    if (
        not isinstance(value, dict)
        or set(value) != {
            "schema", "version", "binding_sha256", "verdict", "target_identity",
            "canary_result_sha256", "recovery", "canary_state_class",
            "install_intent_count", "require_boot_change", "at",
        }
        or value.get("schema") != "s20plus_g986n_native_canary_r1_terminal_input_v1"
        or value.get("version") != VERSION
        or value.get("binding_sha256") != prepared["binding_sha256"]
        or value.get("recovery")
        not in {"normal", "pre-install-abort", "android-disable"}
        or value.get("canary_state_class")
        not in {
            "absent", "binding-only", "intent-only", "completed",
            COMPLETED_SOURCE_UNOBSERVED,
        }
        or type(value.get("install_intent_count")) is not int
        or value.get("install_intent_count") not in {0, 1}
        or type(value.get("require_boot_change")) is not bool
        or not isinstance(value.get("verdict"), str)
        or not isinstance(value.get("at"), str)
        or (
            value.get("canary_result_sha256") is not None
            and (
                not isinstance(value.get("canary_result_sha256"), str)
                or re.fullmatch(r"[0-9a-f]{64}", value.get("canary_result_sha256"))
                is None
            )
        )
    ):
        raise RootDataError("N1 terminal input is malformed")
    require_returned_target(
        prepared,
        value["target_identity"],
        "N1 terminal-input target",
        require_boot_change=value["require_boot_change"],
    )
    return value


def write_terminal(
    run_dir: Path,
    prepared: dict[str, Any],
    verdict: str,
    identity: dict[str, str],
    result_sha256: str | None,
    *,
    recovery: str,
    canary_state_class: str,
    stock_final_health_sha256: str | None = None,
    stock_transfer_state: str | None = None,
    stock_precleanup_root_absence_sha256: str | None = None,
    stock_root_absent: bool | None = None,
    stock_terminal_root_absence: dict[str, Any] | None = None,
    staged_input_absence: dict[str, Any] | None = None,
    install_intent_count: int = 1,
    require_boot_change: bool = True,
) -> dict[str, Any]:
    require_returned_target(
        prepared,
        identity,
        "N1 terminal target",
        require_boot_change=require_boot_change,
    )
    if canary_state_class not in {
        "absent", "binding-only", "intent-only", "completed",
        COMPLETED_SOURCE_UNOBSERVED,
        "unobserved-under-stock", "unobserved-under-root-absent",
    }:
        raise RootDataError("N1 terminal canary state class is invalid")
    if type(install_intent_count) is not int or install_intent_count not in {0, 1}:
        raise RootDataError("N1 terminal install-intent count is invalid")
    if recovery not in {
        "normal", "pre-install-abort", "android-disable",
        "stock", "stock-attempt-unproved",
    }:
        raise RootDataError("N1 terminal recovery class is invalid")
    stock_recovery = recovery in {"stock", "stock-attempt-unproved"}
    if not stock_recovery:
        terminal_input = read_terminal_input(run_dir, prepared)
        expected_input = terminal_input_value(
            prepared,
            verdict,
            identity,
            result_sha256,
            recovery,
            canary_state_class,
            install_intent_count,
            require_boot_change,
            terminal_input["at"],
        )
        if not exact_typed_equal(terminal_input, expected_input):
            raise RootDataError("N1 terminal input does not match terminal publication")
        if stock_transfer_state is not None or stock_precleanup_root_absence_sha256 is not None:
            raise RootDataError("N1 non-stock terminal contains stock input evidence")
    if not exact_typed_equal(staged_input_absence, {
        "returncode": 0,
        "stdout_sha256": hashlib.sha256(b"PASS_N1_STAGE_ABSENT\n").hexdigest(),
        "stderr_sha256": hashlib.sha256(b"").hexdigest(),
        "staged_input_absent": True,
    }):
        raise RootDataError("N1 terminal lacks exact staged-input absence evidence")
    if stock_recovery:
        terminal_input = read_stock_terminal_input(run_dir, prepared)
        expected_stock_input = stock_terminal_input_value(
            prepared,
            verdict,
            identity,
            stock_transfer_state,
            stock_final_health_sha256,
            stock_precleanup_root_absence_sha256,
            terminal_input["at"],
        )
        if (
            not exact_typed_equal(terminal_input, expected_stock_input)
            or recovery != stock_terminal_semantics(stock_transfer_state)["recovery"]
            or canary_state_class
            != stock_terminal_semantics(stock_transfer_state)["canary_state_class"]
            or not isinstance(stock_final_health_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", stock_final_health_sha256) is None
            or stock_root_absent is not True
            or not isinstance(stock_terminal_root_absence, dict)
            or stock_terminal_root_absence.get("root_absent") is not True
            or stock_terminal_root_absence.get("identity_confirmed") is not True
            or not isinstance(stock_terminal_root_absence.get("normalized_sha256"), str)
            or re.fullmatch(
                r"[0-9a-f]{64}",
                stock_terminal_root_absence.get("normalized_sha256"),
            )
            is None
        ):
            raise RootDataError("N1 stock terminal lacks durable final-health evidence")
    elif (
        stock_final_health_sha256 is not None
        or stock_transfer_state is not None
        or stock_precleanup_root_absence_sha256 is not None
        or stock_root_absent is not None
        or stock_terminal_root_absence is not None
    ):
        raise RootDataError("N1 non-stock terminal contains stock-only evidence")
    terminal_path = run_dir / "terminal-result.json"
    existing = read_exact_json(terminal_path, "N1 terminal result") \
        if os.path.lexists(terminal_path) else None
    value = {
        "schema": "s20plus_g986n_native_canary_r1_result_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "verdict": verdict,
        "target_identity": identity,
        "canary_result_sha256": result_sha256,
        "canary_state_class": canary_state_class,
        "module_terminal": (
            stock_terminal_semantics(stock_transfer_state)["module_terminal"]
            if stock_recovery
            else "absent"
            if recovery == "pre-install-abort"
            else "disabled"
        ),
        "stock_final_health_sha256": stock_final_health_sha256,
        "stock_transfer_state": stock_transfer_state,
        "stock_precleanup_root_absence_sha256": stock_precleanup_root_absence_sha256,
        "stock_root_absent": stock_root_absent,
        "stock_terminal_root_absence": stock_terminal_root_absence,
        "staged_input_absent": True,
        "staged_input_absence_evidence": staged_input_absence,
        "install_intent_count": install_intent_count,
        "stock_recovery_attempt_count": 1 if stock_recovery else 0,
        "install_replay_permitted": False,
        "reboot_replay_permitted": False,
        "stock_recovery_replay_permitted": False,
        "other_target_command_count": 0,
        "s22plus_command_count": 0,
        "a90_command_count": 0,
        "at": existing.get("at") if isinstance(existing, dict) else utc_now(),
    }
    if existing is None:
        durable_create(terminal_path, value)
    elif not exact_typed_equal(existing, value) or not isinstance(existing.get("at"), str):
        raise RootDataError("N1 existing terminal result is malformed or mismatched")
    if os.path.lexists(guard_path()):
        release_guard(run_dir)
    elif existing is None:
        raise RootDataError("N1 terminal cannot publish without its shared guard")
    return value


def require_returned_target(
    prepared: dict[str, Any],
    identity: dict[str, str],
    label: str,
    *,
    require_boot_change: bool | None = True,
) -> None:
    target = prepared["binding"]["target"]
    if (
        not isinstance(identity, dict)
        or set(identity) != {"serial_sha256", "topology_sha256", "boot_id_sha256"}
        or identity.get("serial_sha256") != target.get("serial_sha256")
        or identity.get("topology_sha256") != target.get("topology_sha256")
        or not isinstance(identity.get("boot_id_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", identity.get("boot_id_sha256")) is None
        or (
            require_boot_change is True
            and identity.get("boot_id_sha256") == target.get("boot_id_sha256")
        )
        or (
            require_boot_change is False
            and identity.get("boot_id_sha256") != target.get("boot_id_sha256")
        )
    ):
        raise RootDataError(f"{label} is not the prepared returned target")


def require_canary_boot(result: dict[str, Any], boot_id_sha256: Any, label: str) -> None:
    if (
        not isinstance(boot_id_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", boot_id_sha256) is None
        or result.get("boot_id_sha256") != boot_id_sha256
    ):
        raise RootDataError(f"{label} is not bound to the observed source boot")


def confirm_rooted_terminal_state(
    run_dir: Path,
    prepared: dict[str, Any],
    command: Command,
    expected_identity: dict[str, str],
    recovery: str,
    state_class: str,
) -> None:
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    selected, _values, identity = bootstrap.android_health_once(command, adb)
    if identity != expected_identity:
        raise RootDataError("N1 target changed after staged-input cleanup")
    if recovery == "pre-install-abort":
        current = root_preflight(command, adb, selected, identity)
        current.pop("_module_inventory")
        expected = dict(prepared["binding"]["magisk"])
        current.pop("root_observation_sha256", None)
        expected.pop("root_observation_sha256", None)
        if not exact_typed_equal(current, expected):
            raise RootDataError("N1 pre-install terminal state changed")
        return
    recovery_magisk_preflight(command, adb, selected, identity, prepared)
    require_module_inventory(run_dir, command, adb, selected["serial"])
    binding = prepared["binding"]
    audit = command(
        root_argv(
            adb,
            selected["serial"],
            recovery_disabled_audit_script(
                binding["device_binding_sha256"],
                binding["run_nonce"],
            ),
        ),
        30,
        MAX_OUTPUT,
    )
    live_state = decode_recovery_state(
        audit,
        "N1 post-cleanup terminal disabled audit",
        RECOVERY_AUDIT_OUTPUTS,
    )
    if live_state != terminal_audit_state(state_class):
        raise RootDataError("N1 module state changed after staged-input cleanup")


def continue_after_install(
    run_dir: Path,
    prepared: dict[str, Any],
    selected: dict[str, Any],
    identity: dict[str, str],
    command: Command,
) -> dict[str, Any]:
    """Continue after one durably proven install without invoking it again."""
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    audit_script = INSTALL_AUDIT_TEMPLATE.replace(
        "__BINDING_SHA256__", prepared["binding"]["device_binding_sha256"]
    )
    audit = complete_readonly_command(
        run_dir,
        "post-install-audit",
        root_argv(adb, selected["serial"], audit_script),
        command,
        180,
        MAX_OUTPUT,
    )
    decode_exact(
        audit,
        "N1 post-install audit",
        b"PASS_N1_POST_INSTALL_AUDIT\n",
    )
    selected, identity = dispatch_reboot(
        run_dir, "first", prepared, selected, identity, command
    )
    require_module_inventory(run_dir, command, adb, selected["serial"])
    device_binding_sha256 = prepared["binding"]["device_binding_sha256"]
    run_nonce = prepared["binding"]["run_nonce"]
    durable_root_exact(
        run_dir,
        "first-active-audit",
        command,
        adb,
        selected["serial"],
        active_audit_script(device_binding_sha256, run_nonce),
        "N1 active audit",
        b"PASS_N1_ACTIVE_AUDIT\n",
    )
    first_intent, first_result, first_parsed = read_state_files(
        run_dir, "first", prepared, selected, command
    )
    require_canary_boot(
        first_parsed, identity.get("boot_id_sha256"), "N1 canary result"
    )
    event(
        run_dir,
        3,
        "first-observed",
        {"result_sha256": hashlib.sha256(first_result).hexdigest()},
    )
    selected, identity = dispatch_reboot(
        run_dir, "replay", prepared, selected, identity, command
    )
    require_module_inventory(run_dir, command, adb, selected["serial"])
    durable_root_exact(
        run_dir,
        "replay-active-audit",
        command,
        adb,
        selected["serial"],
        active_audit_script(device_binding_sha256, run_nonce),
        "N1 replay audit",
        b"PASS_N1_ACTIVE_AUDIT\n",
    )
    replay_intent, replay_result, _ = read_state_files(
        run_dir, "replay", prepared, selected, command
    )
    if replay_intent != first_intent or replay_result != first_result:
        raise RootDataError("N1 canary journal changed on replay-proof boot")
    current_selected, _values, current_identity = bootstrap.android_health_once(
        command, adb
    )
    if current_identity != identity:
        raise RootDataError("N1 target changed before module disable")
    recovery_magisk_preflight(
        command,
        adb,
        current_selected,
        current_identity,
        prepared,
    )
    require_module_inventory(
        run_dir, command, adb, current_selected["serial"]
    )
    selected = current_selected
    identity = current_identity
    durable_create(run_dir / "disable-intent.json", {
        "schema": "s20plus_g986n_native_canary_r1_disable_intent_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "module_id": MODULE_ID,
        "source_identity": identity,
        "attempt": 1,
        "replay_permitted": False,
        "at": utc_now(),
    })
    disable = durable_command_result(
        run_dir,
        "disable",
        root_argv(
            adb,
            selected["serial"],
            disable_script(device_binding_sha256, run_nonce),
        ),
        command,
        30,
        MAX_OUTPUT,
    )
    decode_exact(disable, "N1 module disable", b"PASS_N1_DISABLE_EXACT\n")
    selected, identity = dispatch_reboot(
        run_dir, "disabled", prepared, selected, identity, command
    )
    require_module_inventory(run_dir, command, adb, selected["serial"])
    durable_root_exact(
        run_dir,
        "disabled-audit",
        command,
        adb,
        selected["serial"],
        disabled_audit_script(device_binding_sha256, run_nonce),
        "N1 disabled audit",
        b"PASS_N1_DISABLED_AUDIT\n",
    )
    disabled_intent, disabled_result, _ = read_state_files(
        run_dir, "disabled", prepared, selected, command
    )
    if disabled_intent != first_intent or disabled_result != first_result:
        raise RootDataError("N1 canary journal changed after disable")
    result_sha = hashlib.sha256(first_result).hexdigest()
    write_terminal_input(
        run_dir,
        prepared,
        "PASS_S20PLUS_G986N_NATIVE_CANARY_N1_DISABLED_ROOTED_HEALTHY",
        identity,
        result_sha,
        recovery="normal",
        canary_state_class="completed",
    )
    cleanup_stage(run_dir, prepared, selected, command)
    staged_absence = stage_absence_evidence(command, adb, selected)
    confirm_rooted_terminal_state(
        run_dir, prepared, command, identity, "normal", "completed"
    )
    return write_terminal(
        run_dir,
        prepared,
        "PASS_S20PLUS_G986N_NATIVE_CANARY_N1_DISABLED_ROOTED_HEALTHY",
        identity,
        result_sha,
        recovery="normal",
        canary_state_class="completed",
        staged_input_absence=staged_absence,
    )


def execute(
    run_dir: Path,
    approval: str,
    command: Command = bootstrap.bounded_command,
) -> dict[str, Any]:
    require_active()
    prepared = read_prepared(run_dir)
    require_exact_nodes(run_dir, PREPARED_FILES)
    if approval != prepared["approval_token"]:
        raise RootDataError("N1 approval token mismatch")
    if os.path.lexists(run_dir / "stage-intent.json"):
        raise RootDataError("N1 transaction attempt already exists; replay forbidden")
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    selected, _values, identity = bootstrap.android_health_once(command, adb)
    if identity != {
        key: prepared["binding"]["target"][key]
        for key in ("serial_sha256", "topology_sha256", "boot_id_sha256")
    }:
        raise RootDataError("N1 target changed after preparation")
    current = root_preflight(command, adb, selected, identity)
    current.pop("_module_inventory")
    if not exact_typed_equal(current, prepared["binding"]["magisk"]):
        raise RootDataError("N1 Magisk or module inventory changed after preparation")
    durable_create(run_dir / "stage-intent.json", {
        "schema": "s20plus_g986n_native_canary_r1_stage_intent_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "module_zip_sha256": MODULE_ZIP_SHA256,
        "device_binding_sha256": prepared["binding"]["device_binding_sha256"],
        "stage_dir": STAGE_DIR,
        "attempt": 1,
        "replay_permitted": False,
        "at": utc_now(),
    })
    event(run_dir, 1, "stage-intent", {"binding_sha256": prepared["binding_sha256"]})
    stage_inputs(run_dir, prepared, selected, command)
    selected, _values, identity = bootstrap.android_health_once(command, adb)
    if identity != {
        key: prepared["binding"]["target"][key]
        for key in ("serial_sha256", "topology_sha256", "boot_id_sha256")
    }:
        raise RootDataError("N1 target changed between staging and install")
    post_stage_preflight(command, adb, selected, identity, prepared)
    durable_create(run_dir / "install-intent.json", {
        "schema": "s20plus_g986n_native_canary_r1_install_intent_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "module_zip_sha256": MODULE_ZIP_SHA256,
        "module_id": MODULE_ID,
        "stage_dir": STAGE_DIR,
        "attempt": 1,
        "replay_permitted": False,
        "at": utc_now(),
    })
    event(run_dir, 2, "install-intent", {"binding_sha256": prepared["binding_sha256"]})
    script = install_script(prepared["binding"]["device_binding_sha256"])
    outcome = durable_command_result(
        run_dir,
        "install",
        root_argv(adb, selected["serial"], script),
        command,
        300,
        MAX_OUTPUT,
    )
    validate_install_output(outcome)
    return continue_after_install(run_dir, prepared, selected, identity, command)


def resume_after_install(
    run_dir: Path,
    command: Command = bootstrap.bounded_command,
) -> dict[str, Any]:
    """Resume one exact predecessor run after its proven install result.

    This entrypoint never stages or installs.  It first publishes a host-only
    predecessor-to-successor receipt, then rebinds the prepared Android boot
    before any privileged read and continues at the post-install audit.
    """
    require_active()
    prepared = read_prepared(run_dir, input_scope="post-install-resume")
    validate_post_install_resume_cut(run_dir, prepared)
    ensure_post_install_continuation(run_dir, prepared)
    continued_seen = validate_post_install_resume_cut(run_dir, prepared)
    if "post-install-continuation.json" not in continued_seen:
        raise RootDataError("N1 post-install continuation receipt disappeared")
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    selected, _values, identity = bootstrap.android_health_once(command, adb)
    require_returned_target(
        prepared,
        identity,
        "N1 post-install continuation source",
        require_boot_change=False,
    )
    recovery_magisk_preflight(
        command,
        adb,
        selected,
        identity,
        prepared,
    )
    return continue_after_install(run_dir, prepared, selected, identity, command)


PRE_INSTALL_ABORT_FILES = PREPARED_FILES | {
    "stage-intent.json",
    "events/01-native-canary-stage-intent.json",
    "stage-claim.stdout", "stage-claim.stderr", "stage-claim-result.json",
    "stage-zip.stdout", "stage-zip.stderr", "stage-zip-result.json",
    "stage-binding.stdout", "stage-binding.stderr", "stage-binding-result.json",
    "stage-verify.stdout", "stage-verify.stderr", "stage-verify-result.json",
    "cleanup-intent.json", "cleanup.stdout", "cleanup.stderr", "cleanup-result.json",
    "terminal-input.json",
    "terminal-result.json",
}


def validate_pre_install_cut(run_dir: Path, prepared: dict[str, Any]) -> set[str]:
    if os.path.lexists(run_dir / "install-intent.json"):
        raise RootDataError("N1 pre-install abort is unavailable after install intent")
    if not os.path.lexists(run_dir / "stage-intent.json"):
        expected = set(PREPARED_FILES)
        if os.path.lexists(run_dir / "terminal-input.json"):
            expected.add("terminal-input.json")
        if os.path.lexists(run_dir / "terminal-result.json"):
            expected.add("terminal-result.json")
        require_exact_nodes(run_dir, expected)
        validate_prepared_event(run_dir, prepared)
        return expected
    seen = validate_recovery_journal(
        run_dir,
        prepared,
        allow_uncertain_commands=True,
    )
    if not seen.issubset(PRE_INSTALL_ABORT_FILES):
        raise RootDataError("N1 pre-install abort journal contains post-install state")
    previous_complete = True
    for label in ("stage-claim", "stage-zip", "stage-binding", "stage-verify"):
        evidence = validate_command_evidence(
            run_dir,
            label,
            allow_uncertain_consumed=True,
        )
        if evidence is None:
            previous_complete = False
            continue
        if not previous_complete:
            raise RootDataError("N1 staged-input command journal is out of order")
        previous_complete = (
            evidence.get("schema")
            == "s20plus_g986n_native_canary_r1_command_result_v1"
            and evidence.get("returncode") == 0
        )
    return seen


def abort_pre_install(
    run_dir: Path,
    command: Command = bootstrap.bounded_command,
) -> dict[str, Any]:
    require_active()
    prepared = read_prepared(run_dir, input_scope="root-recovery")
    validate_pre_install_cut(run_dir, prepared)
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    selected, _values, identity = bootstrap.android_health_once(command, adb)
    require_returned_target(
        prepared,
        identity,
        "N1 pre-install abort target",
        require_boot_change=None,
    )
    boot_changed = (
        identity["boot_id_sha256"]
        != prepared["binding"]["target"]["boot_id_sha256"]
    )
    root = bootstrap.root_observation(command, adb, identity, timeout=30)
    if root.get("root_verified") is not True:
        raise RootDataError("N1 pre-install abort requires exact healthy root")
    write_terminal_input(
        run_dir,
        prepared,
        "ABORTED_S20PLUS_G986N_NATIVE_CANARY_N1_BEFORE_INSTALL_HEALTHY",
        identity,
        None,
        recovery="pre-install-abort",
        canary_state_class="absent",
        install_intent_count=0,
        require_boot_change=boot_changed,
    )
    if os.path.lexists(run_dir / "stage-intent.json"):
        settle_cleanup_without_replay(run_dir, prepared, selected, command)
    staged_absence = stage_absence_evidence(command, adb, selected)
    confirm_rooted_terminal_state(
        run_dir,
        prepared,
        command,
        identity,
        "pre-install-abort",
        "absent",
    )
    return write_terminal(
        run_dir,
        prepared,
        "ABORTED_S20PLUS_G986N_NATIVE_CANARY_N1_BEFORE_INSTALL_HEALTHY",
        identity,
        None,
        recovery="pre-install-abort",
        canary_state_class="absent",
        staged_input_absence=staged_absence,
        install_intent_count=0,
        require_boot_change=boot_changed,
    )


def validate_normal_disable_proof(
    run_dir: Path,
    prepared: dict[str, Any],
) -> dict[str, Any]:
    value = read_exact_json(
        run_dir / "normal-disable-proof.json",
        "N1 normal disable recovery proof",
    )
    identity = value.get("source_identity") if isinstance(value, dict) else None
    require_returned_target(prepared, identity, "N1 normal disable proof target")
    binding = prepared["binding"]
    script = disabled_audit_script(
        binding["device_binding_sha256"], binding["run_nonce"]
    )
    expected_output = b"PASS_N1_DISABLED_AUDIT\n"
    if not exact_typed_equal(value, {
        "schema": "s20plus_g986n_native_canary_r1_normal_disable_proof_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "source_identity": identity,
        "script_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
        "output_sha256": hashlib.sha256(expected_output).hexdigest(),
        "state_class": "completed",
        "read_only": True,
        "replay_permitted": False,
        "at": value.get("at") if isinstance(value, dict) else None,
    }) or not isinstance(value.get("at"), str):
        raise RootDataError("N1 normal disable recovery proof is malformed")
    return value


def resume_normal_disable(
    run_dir: Path,
    prepared: dict[str, Any],
    command: Command,
) -> dict[str, Any]:
    """Continue a consumed normal disable without replaying that write."""
    if any(os.path.lexists(run_dir / name) for name in (
        "stock-recovery-handoff.json", "rollback-intent.json",
        "recovery-disable-intent.json", "cleanup-intent.json",
        "terminal-result.json",
    )):
        raise RootDataError("N1 normal disable resume conflicts with another recovery branch")
    validate_recovery_journal(
        run_dir,
        prepared,
        allow_uncertain_commands=True,
    )
    evidence = validate_command_evidence(
        run_dir,
        "disable",
        allow_uncertain_consumed=True,
    )
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    selected, _values, identity = bootstrap.android_health_once(command, adb)
    require_returned_target(prepared, identity, "N1 normal disable resume target")
    recovery_magisk_preflight(command, adb, selected, identity, prepared)
    require_module_inventory(run_dir, command, adb, selected["serial"])
    complete_disable = False
    if (
        isinstance(evidence, dict)
        and evidence.get("schema")
        == "s20plus_g986n_native_canary_r1_command_result_v1"
    ):
        disable_tuple = complete_command_tuple(run_dir, "disable")
        decode_exact(disable_tuple, "N1 normal disable receipt", b"PASS_N1_DISABLE_EXACT\n")
        complete_disable = True
    proof_path = run_dir / "normal-disable-proof.json"
    disabled_reboot_intent = run_dir / "disabled-reboot-intent.json"
    disable_intent = read_exact_json(
        run_dir / "disable-intent.json",
        "N1 normal disable intent",
    )
    if (
        not os.path.lexists(disabled_reboot_intent)
        and not exact_typed_equal(disable_intent.get("source_identity"), identity)
    ):
        raise RootDataError("N1 normal disable source boot changed before reboot")
    if os.path.lexists(proof_path):
        proof = validate_normal_disable_proof(run_dir, prepared)
        if not os.path.lexists(disabled_reboot_intent) and not exact_typed_equal(
            proof["source_identity"], identity
        ):
            raise RootDataError("N1 normal disable proof source boot changed before reboot")
    elif not complete_disable:
        binding = prepared["binding"]
        script = disabled_audit_script(
            binding["device_binding_sha256"], binding["run_nonce"]
        )
        rc, stdout, stderr = command(
            root_argv(adb, selected["serial"], script),
            30,
            MAX_OUTPUT,
        )
        decode_exact(
            (rc, stdout, stderr),
            "N1 normal disable read-only recovery proof",
            b"PASS_N1_DISABLED_AUDIT\n",
        )
        durable_create(proof_path, {
            "schema": "s20plus_g986n_native_canary_r1_normal_disable_proof_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "source_identity": identity,
            "script_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
            "output_sha256": hashlib.sha256(stdout).hexdigest(),
            "state_class": "completed",
            "read_only": True,
            "replay_permitted": False,
            "at": utc_now(),
        })
    if os.path.lexists(disabled_reboot_intent):
        selected, identity = resume_reboot_observation(
            run_dir,
            "disabled",
            prepared,
            command,
        )
    else:
        selected, identity = dispatch_reboot(
            run_dir,
            "disabled",
            prepared,
            selected,
            identity,
            command,
        )
    require_module_inventory(run_dir, command, adb, selected["serial"])
    binding = prepared["binding"]
    audit = complete_readonly_command(
        run_dir,
        "disabled-audit",
        root_argv(
            adb,
            selected["serial"],
            disabled_audit_script(
                binding["device_binding_sha256"], binding["run_nonce"]
            ),
        ),
        command,
        30,
        MAX_OUTPUT,
    )
    decode_exact(audit, "N1 resumed disabled audit", b"PASS_N1_DISABLED_AUDIT\n")
    read_or_collect_state_files(run_dir, "disabled", prepared, selected, command)
    return finalize_terminal(run_dir, command)


def recover_android(
    run_dir: Path,
    command: Command = bootstrap.bounded_command,
) -> dict[str, Any]:
    require_active()
    prepared = read_prepared(run_dir, input_scope="root-recovery")
    if not os.path.lexists(run_dir / "install-intent.json"):
        raise RootDataError("N1 Android recovery requires a consumed install intent")
    if os.path.lexists(run_dir / "disable-intent.json"):
        return resume_normal_disable(run_dir, prepared, command)
    if any(os.path.lexists(run_dir / name) for name in (
        "stock-recovery-handoff.json", "rollback-intent.json", "terminal-result.json",
        "disabled-reboot-intent.json", "cleanup-intent.json",
    )):
        raise RootDataError("N1 Android recovery state conflicts with stock or terminal evidence")
    seen = validate_recovery_journal(
        run_dir,
        prepared,
        allow_uncertain_commands=True,
    )
    recovery_resume_files = {
        "recovery-disable-intent.json",
        "recovery-disable-result.json",
        "recovery-disable.stdout",
        "recovery-disable.stderr",
        "recovery-disabled-reboot-intent.json",
        "recovery-disabled-reboot-result.json",
        "recovery-disabled-reboot.stdout",
        "recovery-disabled-reboot.stderr",
        "recovery-disabled-observation.json",
        "recovery-disabled-audit-result.json",
        "recovery-disabled-audit.stdout",
        "recovery-disabled-audit.stderr",
        "recovery-disabled-audit-resume.json",
        "recovery-intent.raw",
        "recovery-result.raw",
        "terminal-input.json",
    }
    conflicting = {
        name
        for name in seen
        if name.startswith(("disable", "disabled-", "recovery-", "cleanup"))
        and name not in recovery_resume_files
    }
    if conflicting:
        raise RootDataError("N1 Android recovery journal is not at an eligible cut point")
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    selected, _values, identity = bootstrap.android_health_once(command, adb)
    if identity.get("boot_id_sha256") == prepared["binding"]["target"]["boot_id_sha256"]:
        raise RootDataError(
            "N1 Android recovery requires the promoted post-boot module tree; "
            "pre-promotion uncertainty requires stock recovery only"
        )
    require_returned_target(prepared, identity, "N1 Android recovery target")
    root = recovery_magisk_preflight(command, adb, selected, identity, prepared)
    require_module_inventory(run_dir, command, adb, selected["serial"])
    binding = prepared["binding"]
    source_completed_sha: str | None = None
    source_canary_boot_id: str | None = None
    source_completed_observed = False
    if os.path.lexists(run_dir / "recovery-disable-intent.json"):
        recovery_intent = read_exact_json(
            run_dir / "recovery-disable-intent.json",
            "N1 recovery-disable intent",
        )
        recovery_source_identity = recovery_intent["source_identity"]
        source_state_class = recovery_intent["source_state_class"]
        source_completed_sha = recovery_intent["source_canary_result_sha256"]
        source_canary_boot_id = recovery_intent[
            "source_canary_boot_id_sha256"
        ]
        source_completed_observed = recovery_intent["source_boot_observed"]
        if source_state_class == "completed":
            validate_recovery_source_canary_binding(
                run_dir,
                prepared,
                recovery_intent,
            )
        reboot_intent_present = os.path.lexists(
            run_dir / "recovery-disabled-reboot-intent.json"
        )
        if not reboot_intent_present and identity != recovery_source_identity:
            raise RootDataError("N1 recovery-disable source boot changed before reboot")
        disable = complete_command_tuple(run_dir, "recovery-disable")
    else:
        source_state_class = decode_recovery_state(
            command(
                root_argv(
                    adb,
                    selected["serial"],
                    recovery_source_audit_script(
                        binding["device_binding_sha256"], binding["run_nonce"]
                    ),
                ),
                30,
                MAX_OUTPUT,
            ),
            "N1 Android-recovery source audit",
            RECOVERY_SOURCE_OUTPUTS,
        )
        if source_state_class == "completed":
            _source_intent, source_result, source_parsed = read_or_collect_state_files(
                run_dir, "recovery", prepared, selected, command
            )
            source_completed_sha = hashlib.sha256(source_result).hexdigest()
            if os.path.lexists(run_dir / "first-observation.json"):
                first_observation = read_exact_json(
                    run_dir / "first-observation.json", "N1 first-boot observation"
                )
                source_canary_boot_id = first_observation.get(
                    "android_identity", {}
                ).get("boot_id_sha256")
                require_canary_boot(
                    source_parsed,
                    source_canary_boot_id,
                    "N1 Android-recovery pre-effect canary result",
                )
                source_completed_observed = True
            else:
                source_canary_boot_id = identity.get("boot_id_sha256")
                require_canary_boot(
                    source_parsed,
                    source_canary_boot_id,
                    "N1 Android-recovery pre-effect canary result",
                )
        recovery_source_identity = identity
        recovery_intent = {
            "schema": "s20plus_g986n_native_canary_r1_recovery_disable_intent_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "source_identity": recovery_source_identity,
            "root_observation": root,
            "source_state_class": source_state_class,
            "source_canary_result_sha256": source_completed_sha,
            "source_canary_boot_id_sha256": source_canary_boot_id,
            "source_boot_observed": source_completed_observed,
            "attempt": 1,
            "replay_permitted": False,
            "at": utc_now(),
        }
        validate_recovery_source_canary_binding(
            run_dir,
            prepared,
            recovery_intent,
        )
        durable_create(run_dir / "recovery-disable-intent.json", recovery_intent)
        disable = durable_command_result(
            run_dir,
            "recovery-disable",
            root_argv(
                adb,
                selected["serial"],
                recovery_disable_script(
                    binding["device_binding_sha256"], binding["run_nonce"]
                ),
            ),
            command,
            30,
            MAX_OUTPUT,
        )
    state_class = decode_recovery_state(
        disable, "N1 recovery disable", RECOVERY_STATE_OUTPUTS
    )
    require_monotonic_recovery_state(
        source_state_class,
        state_class,
        "N1 Android-recovery pre-disable state",
    )
    if state_class == "completed":
        completed_during_disable = source_completed_sha is None
        _current_intent, current_result, current_parsed = read_or_collect_state_files(
            run_dir,
            "recovery",
            prepared,
            selected,
            command,
        )
        current_result_sha = hashlib.sha256(current_result).hexdigest()
        if source_completed_sha is not None and current_result_sha != source_completed_sha:
            raise RootDataError("N1 recovery canary result changed before reboot")
        if completed_during_disable:
            source_canary_boot_id = recovery_source_identity.get(
                "boot_id_sha256"
            )
            require_canary_boot(
                current_parsed,
                source_canary_boot_id,
                "N1 recovery pre-reboot canary result",
            )
        else:
            require_canary_boot(
                current_parsed,
                source_canary_boot_id,
                "N1 recovery pre-reboot canary result",
            )
        source_completed_sha = current_result_sha
    if os.path.lexists(run_dir / "recovery-disabled-reboot-intent.json"):
        selected, identity = resume_reboot_observation(
            run_dir,
            "recovery-disabled",
            prepared,
            command,
        )
    else:
        selected, identity = dispatch_reboot(
            run_dir,
            "recovery-disabled",
            prepared,
            selected,
            identity,
            command,
            minimum_recovery_state=state_class,
        )
    require_module_inventory(run_dir, command, adb, selected["serial"])
    audit = complete_readonly_command(
        run_dir,
        "recovery-disabled-audit",
        root_argv(
            adb,
            selected["serial"],
            recovery_disabled_audit_script(
                binding["device_binding_sha256"], binding["run_nonce"]
            ),
        ),
        command,
        30,
        MAX_OUTPUT,
    )
    audited_state_class = decode_recovery_state(
        audit, "N1 recovery disabled audit", RECOVERY_AUDIT_OUTPUTS
    )
    require_monotonic_recovery_state(
        state_class,
        audited_state_class,
        "N1 canary state",
    )
    state_class = audited_state_class
    result_sha: str | None = None
    if state_class == "completed":
        durable_intent, durable_result, durable_parsed = (
            read_or_collect_state_files(
                run_dir, "recovery", prepared, selected, command
            )
        )
        live_intent, live_result, _live_parsed = read_live_canary_pair(
            prepared,
            selected,
            command,
        )
        if (live_intent, live_result) != (durable_intent, durable_result):
            raise RootDataError(
                "N1 recovery canary bytes changed after the disabled reboot"
            )
        require_canary_boot(
            durable_parsed,
            source_canary_boot_id,
            "N1 Android-recovery completed canary result",
        )
        result_sha = hashlib.sha256(durable_result).hexdigest()
        if source_completed_sha is not None and result_sha != source_completed_sha:
            raise RootDataError(
                "N1 recovery canary result changed after the disabled reboot"
            )
        if not source_completed_observed:
            state_class = COMPLETED_SOURCE_UNOBSERVED
    write_terminal_input(
        run_dir,
        prepared,
        "RECOVERED_S20PLUS_G986N_NATIVE_CANARY_N1_DISABLED_ROOTED_HEALTHY",
        identity,
        result_sha,
        recovery="android-disable",
        canary_state_class=state_class,
    )
    cleanup_stage(run_dir, prepared, selected, command)
    staged_absence = stage_absence_evidence(command, adb, selected)
    confirm_rooted_terminal_state(
        run_dir,
        prepared,
        command,
        identity,
        "android-disable",
        state_class,
    )
    return write_terminal(
        run_dir,
        prepared,
        "RECOVERED_S20PLUS_G986N_NATIVE_CANARY_N1_DISABLED_ROOTED_HEALTHY",
        identity,
        result_sha,
        recovery="android-disable",
        canary_state_class=state_class,
        staged_input_absence=staged_absence,
    )


HANDOFF_ALLOWED_FILES = PREPARED_FILES | {
    "stage-intent.json",
    "install-intent.json",
    "stage-claim.stdout", "stage-claim.stderr", "stage-claim-result.json",
    "stage-zip.stdout", "stage-zip.stderr", "stage-zip-result.json",
    "stage-binding.stdout", "stage-binding.stderr", "stage-binding-result.json",
    "stage-verify.stdout", "stage-verify.stderr", "stage-verify-result.json",
    "install.stdout", "install.stderr", "install-result.json",
    "post-install-audit.stdout", "post-install-audit.stderr", "post-install-audit-result.json",
    "post-install-audit-resume.json",
    "post-install-continuation.json",
    "first-reboot-intent.json", "first-reboot.stdout", "first-reboot.stderr",
    "first-reboot-result.json", "first-observation.json",
    "first-active-audit.stdout", "first-active-audit.stderr", "first-active-audit-result.json",
    "first-intent.raw", "first-result.raw",
    "replay-reboot-intent.json", "replay-reboot.stdout", "replay-reboot.stderr",
    "replay-reboot-result.json", "replay-observation.json",
    "replay-active-audit.stdout", "replay-active-audit.stderr", "replay-active-audit-result.json",
    "replay-intent.raw", "replay-result.raw",
    "disable-intent.json", "disable.stdout", "disable.stderr", "disable-result.json",
    "normal-disable-proof.json",
    "disabled-reboot-intent.json", "disabled-reboot.stdout", "disabled-reboot.stderr",
    "disabled-reboot-result.json", "disabled-observation.json",
    "disabled-audit.stdout", "disabled-audit.stderr", "disabled-audit-result.json",
    "disabled-audit-resume.json",
    "disabled-intent.raw", "disabled-result.raw",
    "recovery-disable-intent.json", "recovery-disable.stdout", "recovery-disable.stderr",
    "recovery-disable-result.json", "recovery-disabled-reboot-intent.json",
    "recovery-disabled-reboot.stdout", "recovery-disabled-reboot.stderr",
    "recovery-disabled-reboot-result.json", "recovery-disabled-observation.json",
    "recovery-disabled-audit.stdout", "recovery-disabled-audit.stderr",
    "recovery-disabled-audit-result.json", "recovery-disabled-audit-resume.json",
    "recovery-intent.raw", "recovery-result.raw",
    "cleanup-intent.json", "cleanup.stdout", "cleanup.stderr", "cleanup-result.json",
    "terminal-input.json",
    "terminal-result.json",
    "events/01-native-canary-stage-intent.json",
    "events/02-native-canary-install-intent.json",
    "events/03-native-canary-first-observed.json",
}

COMMAND_LABELS = (
    "stage-claim", "stage-zip", "stage-binding", "stage-verify", "install",
    "post-install-audit", "first-reboot", "first-active-audit",
    "replay-reboot", "replay-active-audit", "disable", "disabled-reboot",
    "disabled-audit", "recovery-disable", "recovery-disabled-reboot",
    "recovery-disabled-audit", "cleanup",
)

POST_INSTALL_RESUME_REQUIRED_FILES = PREPARED_FILES | {
    "stage-intent.json",
    "install-intent.json",
    "stage-claim.stdout", "stage-claim.stderr", "stage-claim-result.json",
    "stage-zip.stdout", "stage-zip.stderr", "stage-zip-result.json",
    "stage-binding.stdout", "stage-binding.stderr", "stage-binding-result.json",
    "stage-verify.stdout", "stage-verify.stderr", "stage-verify-result.json",
    "install.stdout", "install.stderr", "install-result.json",
    "events/01-native-canary-stage-intent.json",
    "events/02-native-canary-install-intent.json",
}

POST_INSTALL_RESUME_ALLOWED_FILES = POST_INSTALL_RESUME_REQUIRED_FILES | {
    "post-install-continuation.json",
    "post-install-audit.stdout",
    "post-install-audit.stderr",
    "post-install-audit-result.json",
    "post-install-audit-resume.json",
}


def uncertain_command_evidence(
    run_dir: Path,
    label: str,
    paths: dict[str, Path],
    present: set[str],
) -> dict[str, Any]:
    for stream in ("stdout", "stderr"):
        if stream in present:
            read_exact_blob(paths[stream], f"N1 {label} partial {stream}", MAX_OUTPUT)
    return {
        "schema": "s20plus_g986n_native_canary_r1_command_uncertain_consumed_v1",
        "version": VERSION,
        "label": label,
        "present": sorted(present),
        "replay_permitted": False,
    }


def validate_command_evidence(
    run_dir: Path,
    label: str,
    *,
    allow_uncertain_consumed: bool = False,
) -> dict[str, Any] | None:
    paths = {
        "result": run_dir / f"{label}-result.json",
        "stdout": run_dir / f"{label}.stdout",
        "stderr": run_dir / f"{label}.stderr",
    }
    present = {key for key, path in paths.items() if os.path.lexists(path)}
    if not present:
        return None
    if "stderr" in present and "stdout" not in present:
        raise RootDataError(
            f"N1 {label} command evidence violates publication order"
        )
    if "result" not in present:
        if present not in ({"stdout"}, {"stdout", "stderr"}):
            raise RootDataError(
                f"N1 {label} command evidence is not a reachable publication cut"
            )
        if allow_uncertain_consumed:
            return uncertain_command_evidence(run_dir, label, paths, present)
        raise RootDataError(f"N1 {label} command evidence is incomplete")
    value = read_exact_json(paths["result"], f"N1 {label} command result")
    if not isinstance(value, dict):
        raise RootDataError(f"N1 {label} command result is malformed")
    if value.get("schema") == "s20plus_g986n_native_canary_r1_command_failure_v1":
        if (
            set(value) != {
                "schema", "version", "label", "failure_class",
                "effect_outcome", "replay_permitted",
            }
            or value.get("version") != VERSION
            or value.get("label") != label
            or not isinstance(value.get("failure_class"), str)
            or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,127}", value.get("failure_class"))
            is None
            or value.get("effect_outcome") != "uncertain"
            or value.get("replay_permitted") is not False
        ):
            raise RootDataError(f"N1 {label} failure evidence is malformed")
        if present != {"result"}:
            if allow_uncertain_consumed:
                return uncertain_command_evidence(run_dir, label, paths, present)
            raise RootDataError(f"N1 {label} failure evidence is inconsistent")
        return value
    if (
        set(value) != {
            "schema", "version", "label", "returncode", "stdout_sha256",
            "stderr_sha256", "stdout_bytes", "stderr_bytes",
            "replay_permitted",
        }
        or value.get("schema") != "s20plus_g986n_native_canary_r1_command_result_v1"
        or value.get("version") != VERSION
        or value.get("label") != label
        or type(value.get("returncode")) is not int
        or type(value.get("stdout_bytes")) is not int
        or type(value.get("stderr_bytes")) is not int
        or value.get("stdout_bytes", -1) < 0
        or value.get("stderr_bytes", -1) < 0
        or value.get("stdout_bytes", 0) + value.get("stderr_bytes", 0) > MAX_OUTPUT
        or not isinstance(value.get("stdout_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", value.get("stdout_sha256")) is None
        or not isinstance(value.get("stderr_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", value.get("stderr_sha256")) is None
        or value.get("replay_permitted") is not False
    ):
        raise RootDataError(f"N1 {label} command result is malformed")
    if present != {"result", "stdout", "stderr"}:
        raise RootDataError(
            f"N1 {label} successful command evidence is not a reachable publication cut"
        )
    stdout = read_exact_blob(paths["stdout"], f"N1 {label} stdout", MAX_OUTPUT)
    stderr = read_exact_blob(paths["stderr"], f"N1 {label} stderr", MAX_OUTPUT)
    if (
        len(stdout) != value["stdout_bytes"]
        or len(stderr) != value["stderr_bytes"]
        or hashlib.sha256(stdout).hexdigest() != value["stdout_sha256"]
        or hashlib.sha256(stderr).hexdigest() != value["stderr_sha256"]
    ):
        raise RootDataError(f"N1 {label} raw command evidence changed")
    return value


def settle_cleanup_without_replay(
    run_dir: Path,
    prepared: dict[str, Any],
    selected: dict[str, Any],
    command: Command,
) -> None:
    if not os.path.lexists(run_dir / "cleanup-intent.json"):
        cleanup_stage(run_dir, prepared, selected, command)
        return
    evidence = validate_command_evidence(
        run_dir,
        "cleanup",
        allow_uncertain_consumed=True,
    )
    if evidence is None or evidence.get("schema") != (
        "s20plus_g986n_native_canary_r1_command_result_v1"
    ):
        return
    cleanup_stage(run_dir, prepared, selected, command)


def validate_reboot_evidence(
    run_dir: Path,
    prepared: dict[str, Any],
    phase: str,
) -> None:
    intent_path = run_dir / f"{phase}-reboot-intent.json"
    observation_path = run_dir / f"{phase}-observation.json"
    command_present = any(
        os.path.lexists(run_dir / name)
        for name in (
            f"{phase}-reboot-result.json",
            f"{phase}-reboot.stdout",
            f"{phase}-reboot.stderr",
        )
    )
    if not os.path.lexists(intent_path) and (
        command_present or os.path.lexists(observation_path)
    ):
        raise RootDataError(f"N1 {phase} reboot evidence has no intent")
    if os.path.lexists(intent_path):
        intent = read_exact_json(intent_path, f"N1 {phase} reboot intent")
        if (
            not isinstance(intent, dict)
            or set(intent) != {
                "schema", "version", "binding_sha256", "phase",
                "prior_boot_id_sha256", "attempt", "replay_permitted", "at",
            }
            or intent.get("schema") != "s20plus_g986n_native_canary_r1_reboot_intent_v1"
            or intent.get("version") != VERSION
            or intent.get("binding_sha256") != prepared["binding_sha256"]
            or intent.get("phase") != phase
            or not isinstance(intent.get("prior_boot_id_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", intent.get("prior_boot_id_sha256")) is None
            or type(intent.get("attempt")) is not int
            or intent.get("attempt") != 1
            or intent.get("replay_permitted") is not False
            or not isinstance(intent.get("at"), str)
        ):
            raise RootDataError(f"N1 {phase} reboot intent is malformed")
    if os.path.lexists(observation_path):
        if not os.path.lexists(intent_path):
            raise RootDataError(f"N1 {phase} observation has no reboot intent")
        command_result = validate_command_evidence(
            run_dir,
            f"{phase}-reboot",
            allow_uncertain_consumed=True,
        )
        dispatch_evidence = reboot_dispatch_evidence_class(run_dir, phase)
        observation = read_exact_json(
            observation_path, f"N1 {phase} reboot observation"
        )
        identity = observation.get("android_identity") if isinstance(observation, dict) else None
        root = observation.get("root_observation") if isinstance(observation, dict) else None
        if (
            not isinstance(observation, dict)
            or set(observation) != {
                "schema", "version", "binding_sha256", "phase",
                "android_identity", "root_observation", "dispatch_evidence",
                "replay_permitted", "at",
            }
            or observation.get("schema")
            != "s20plus_g986n_native_canary_r1_reboot_observation_v1"
            or observation.get("version") != VERSION
            or observation.get("binding_sha256") != prepared["binding_sha256"]
            or observation.get("phase") != phase
            or not isinstance(identity, dict)
            or set(identity) != {
                "serial_sha256", "topology_sha256", "boot_id_sha256",
            }
            or identity.get("serial_sha256")
            != prepared["binding"]["target"]["serial_sha256"]
            or identity.get("topology_sha256") != bootstrap.EXPECTED_TOPOLOGY_SHA256
            or not isinstance(identity.get("boot_id_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", identity.get("boot_id_sha256")) is None
            or not isinstance(root, dict)
            or set(root) != {"root_verified", "attempts", "output_sha256"}
            or root.get("root_verified") is not True
            or type(root.get("attempts")) is not int
            or root.get("attempts", 0) < 1
            or not isinstance(root.get("output_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", root.get("output_sha256")) is None
            or observation.get("dispatch_evidence") != dispatch_evidence
            or observation.get("replay_permitted") is not False
            or not isinstance(observation.get("at"), str)
            or (
                dispatch_evidence == "complete-success"
                and (
                    command_result is None
                    or command_result.get("schema")
                    != "s20plus_g986n_native_canary_r1_command_result_v1"
                    or command_result.get("returncode") != 0
                    or command_result.get("stdout_bytes") != 0
                    or command_result.get("stderr_bytes") != 0
                )
            )
        ):
            raise RootDataError(f"N1 {phase} reboot observation is malformed")
        intent = read_exact_json(intent_path, f"N1 {phase} reboot intent")
        if identity["boot_id_sha256"] == intent["prior_boot_id_sha256"]:
            raise RootDataError(f"N1 {phase} reboot did not change boot identity")


def validate_optional_canary_pair(
    run_dir: Path,
    prepared: dict[str, Any],
    label: str,
) -> None:
    intent_path = run_dir / f"{label}-intent.raw"
    result_path = run_dir / f"{label}-result.raw"
    present = (os.path.lexists(intent_path), os.path.lexists(result_path))
    if present == (False, False):
        return
    if present == (True, False):
        intent = read_exact_blob(
            intent_path,
            f"N1 {label} partial canary intent",
            MAX_STATE_FILE,
        )
        expected = (
            '{"schema":"s20plus_native_canary_n1_intent_v1",'
            f'"binding_sha256":"{prepared["binding"]["device_binding_sha256"]}",'
            f'"run_nonce":"{prepared["binding"]["run_nonce"]}",'
            '"replay_permitted":false}\n'
        ).encode("ascii")
        if intent != expected:
            raise RootDataError(f"N1 {label} partial canary intent is malformed")
        # This is a consumed read-only observation cut, not proof of a completed
        # result. Recovery may proceed, but no success branch may infer or
        # recreate the missing result from this file.
        return
    if present != (True, True):
        raise RootDataError(f"N1 {label} canary evidence is incomplete")
    validate_canary_files(
        read_exact_blob(intent_path, f"N1 {label} canary intent", MAX_STATE_FILE),
        read_exact_blob(result_path, f"N1 {label} canary result", MAX_STATE_FILE),
        prepared,
    )


def validate_optional_effect_intents(
    run_dir: Path,
    prepared: dict[str, Any],
) -> None:
    definitions = {
        "disable-intent.json": (
            "s20plus_g986n_native_canary_r1_disable_intent_v1",
            None,
            "disable",
        ),
        "recovery-disable-intent.json": (
            "s20plus_g986n_native_canary_r1_recovery_disable_intent_v1",
            None,
            "recovery-disable",
        ),
        "cleanup-intent.json": (
            "s20plus_g986n_native_canary_r1_cleanup_intent_v1",
            {"stage_dir": STAGE_DIR},
            "cleanup",
        ),
    }
    for filename, (schema, extra, command_label) in definitions.items():
        path = run_dir / filename
        command_present = any(
            os.path.lexists(run_dir / name)
            for name in (
                f"{command_label}-result.json",
                f"{command_label}.stdout",
                f"{command_label}.stderr",
            )
        )
        if not os.path.lexists(path):
            if command_present:
                raise RootDataError(f"N1 {command_label} evidence has no intent")
            continue
        value = read_exact_json(path, f"N1 {command_label} intent")
        dynamic_extra: dict[str, Any]
        if filename == "disable-intent.json":
            dynamic_extra = {
                "module_id": MODULE_ID,
                "source_identity": value.get("source_identity")
                if isinstance(value, dict) else None,
            }
        elif filename == "recovery-disable-intent.json":
            dynamic_extra = {
                "source_identity": value.get("source_identity")
                if isinstance(value, dict) else None,
                "root_observation": value.get("root_observation")
                if isinstance(value, dict) else None,
                "source_state_class": value.get("source_state_class")
                if isinstance(value, dict) else None,
                "source_canary_result_sha256": value.get("source_canary_result_sha256")
                if isinstance(value, dict) else None,
                "source_canary_boot_id_sha256": value.get(
                    "source_canary_boot_id_sha256"
                ) if isinstance(value, dict) else None,
                "source_boot_observed": value.get("source_boot_observed")
                if isinstance(value, dict) else None,
            }
        else:
            dynamic_extra = extra or {}
        expected = {
            "schema": schema,
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            **dynamic_extra,
            "attempt": 1,
            "replay_permitted": False,
            "at": value.get("at") if isinstance(value, dict) else None,
        }
        if (
            not exact_typed_equal(value, expected)
            or type(value.get("attempt")) is not int
            or not isinstance(value.get("at"), str)
        ):
            raise RootDataError(f"N1 {command_label} intent is malformed")
        if filename == "disable-intent.json":
            require_returned_target(
                prepared,
                value["source_identity"],
                "N1 normal disable source target",
            )
            replay_observation = read_exact_json(
                run_dir / "replay-observation.json",
                "N1 normal disable replay observation",
            )
            if not exact_typed_equal(
                value["source_identity"],
                replay_observation.get("android_identity"),
            ):
                raise RootDataError(
                    "N1 normal disable source is not the replay observation"
                )
        elif filename == "recovery-disable-intent.json":
            identity = value["source_identity"]
            root = value["root_observation"]
            source_state = value["source_state_class"]
            source_result_sha = value["source_canary_result_sha256"]
            source_canary_boot_id = value["source_canary_boot_id_sha256"]
            source_observed = value["source_boot_observed"]
            require_returned_target(prepared, identity, "N1 recovery source target")
            if (
                not isinstance(root, dict)
                or set(root) != {"root_verified", "attempts", "output_sha256"}
                or root.get("root_verified") is not True
                or type(root.get("attempts")) is not int
                or root.get("attempts", 0) < 1
                or not isinstance(root.get("output_sha256"), str)
                or re.fullmatch(r"[0-9a-f]{64}", root.get("output_sha256")) is None
                or source_state not in RECOVERY_STATE_ORDER
                or type(source_observed) is not bool
                or (
                    source_state == "completed"
                    and (
                        not isinstance(source_result_sha, str)
                        or re.fullmatch(r"[0-9a-f]{64}", source_result_sha) is None
                        or not isinstance(source_canary_boot_id, str)
                        or re.fullmatch(
                            r"[0-9a-f]{64}", source_canary_boot_id
                        ) is None
                    )
                )
                or (
                    source_state != "completed"
                    and (
                        source_result_sha is not None
                        or source_canary_boot_id is not None
                    )
                )
                or (source_observed and source_state != "completed")
                or (
                    source_state == "completed"
                    and source_observed
                    != os.path.lexists(run_dir / "first-observation.json")
                )
            ):
                raise RootDataError("N1 recovery source root observation is malformed")
            if source_observed:
                first_observation = read_exact_json(
                    run_dir / "first-observation.json",
                    "N1 recovery source first observation",
                )
                if (
                    first_observation.get("android_identity", {}).get(
                        "boot_id_sha256"
                    )
                    != source_canary_boot_id
                ):
                    raise RootDataError(
                        "N1 recovery source canary boot is not the observed first boot"
                    )
            elif (
                source_state == "completed"
                and source_canary_boot_id != identity.get("boot_id_sha256")
            ):
                raise RootDataError(
                    "N1 unobserved recovery canary boot is not the disable source boot"
                )
            validate_recovery_source_canary_binding(run_dir, prepared, value)


def scan_recovery_journal(run_dir: Path, allowed_extra: set[str] | None = None) -> set[str]:
    allowed = HANDOFF_ALLOWED_FILES | (allowed_extra or set())
    seen: set[str] = set()
    pending = [run_dir]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                relative = str(path.relative_to(run_dir))
                metadata = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(metadata.st_mode) and not entry.is_symlink():
                    if relative != "events":
                        raise RootDataError("N1 recovery journal contains an unexpected directory")
                    pending.append(path)
                    continue
                if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or relative not in allowed:
                    raise RootDataError("N1 recovery journal contains an extra or indirect node")
                seen.add(relative)
    if not PREPARED_FILES.issubset(seen) or "stage-intent.json" not in seen:
        raise RootDataError("N1 recovery journal is missing its prepared or stage intent")
    return seen


def validate_stage_intent(run_dir: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    value = read_exact_json(run_dir / "stage-intent.json", "N1 stage intent")
    if not exact_typed_equal(value, {
        "schema": "s20plus_g986n_native_canary_r1_stage_intent_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "module_zip_sha256": MODULE_ZIP_SHA256,
        "device_binding_sha256": prepared["binding"]["device_binding_sha256"],
        "stage_dir": STAGE_DIR,
        "attempt": 1,
        "replay_permitted": False,
        "at": value.get("at") if isinstance(value, dict) else None,
    }) or type(value.get("attempt")) is not int or not isinstance(value.get("at"), str):
        raise RootDataError("N1 stage intent is malformed or mismatched")
    return value


def validate_install_intent(run_dir: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    value = read_exact_json(run_dir / "install-intent.json", "N1 install intent")
    if not exact_typed_equal(value, {
        "schema": "s20plus_g986n_native_canary_r1_install_intent_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "module_zip_sha256": MODULE_ZIP_SHA256,
        "module_id": MODULE_ID,
        "stage_dir": STAGE_DIR,
        "attempt": 1,
        "replay_permitted": False,
        "at": value.get("at") if isinstance(value, dict) else None,
    }) or type(value.get("attempt")) is not int or not isinstance(value.get("at"), str):
        raise RootDataError("N1 install intent is malformed or mismatched")
    return value


def validate_action_event(
    run_dir: Path,
    prepared: dict[str, Any],
    ordinal: int,
    name: str,
    intent_name: str,
) -> None:
    path = run_dir / "events" / f"{ordinal:02d}-native-canary-{name}.json"
    present = os.path.lexists(path)
    intent_present = os.path.lexists(run_dir / intent_name)
    if present and not intent_present:
        raise RootDataError(f"N1 {name} event has no durable intent")
    if not present:
        return
    value = read_exact_json(path, f"N1 {name} event")
    if not exact_typed_equal(value, {
        "schema": "s20plus_g986n_f1_event_v1",
        "version": bootstrap.VERSION,
        "ordinal": ordinal,
        "name": f"native-canary-{name}",
        "at": value.get("at") if isinstance(value, dict) else None,
        "binding_sha256": prepared["binding_sha256"],
    }) or type(value.get("ordinal")) is not int or not isinstance(value.get("at"), str):
        raise RootDataError(f"N1 {name} event is malformed or mismatched")


def validate_first_observed_event(run_dir: Path) -> None:
    path = run_dir / "events/03-native-canary-first-observed.json"
    if not os.path.lexists(path):
        return
    result_path = run_dir / "first-result.raw"
    if not os.path.lexists(result_path):
        raise RootDataError("N1 first-observed event has no canary result")
    value = read_exact_json(path, "N1 first-observed event")
    result_bytes = read_exact_blob(
        result_path,
        "N1 first-observed canary result",
        MAX_STATE_FILE,
    )
    if not exact_typed_equal(value, {
        "schema": "s20plus_g986n_f1_event_v1",
        "version": bootstrap.VERSION,
        "ordinal": 3,
        "name": "native-canary-first-observed",
        "at": value.get("at") if isinstance(value, dict) else None,
        "result_sha256": hashlib.sha256(result_bytes).hexdigest(),
    }) or type(value.get("ordinal")) is not int or not isinstance(value.get("at"), str):
        raise RootDataError("N1 first-observed event is malformed or mismatched")


def validate_prepared_event(run_dir: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    value = read_exact_json(
        run_dir / "events/00-native-canary-prepared.json", "N1 prepared event"
    )
    if not exact_typed_equal(value, {
        "schema": "s20plus_g986n_f1_event_v1",
        "version": bootstrap.VERSION,
        "ordinal": 0,
        "name": "native-canary-prepared",
        "at": value.get("at") if isinstance(value, dict) else None,
        "binding_sha256": prepared["binding_sha256"],
    }) or type(value.get("ordinal")) is not int or not isinstance(value.get("at"), str):
        raise RootDataError("N1 prepared event is malformed or mismatched")
    return value


def require_complete_successful_command(
    run_dir: Path,
    label: str,
) -> tuple[int, bytes, bytes]:
    result = complete_command_tuple(run_dir, label)
    if result[0] != 0:
        raise RootDataError(f"N1 {label} predecessor did not succeed")
    return result


def validate_recovery_prefix_graph(
    run_dir: Path,
    prepared: dict[str, Any],
    seen: set[str],
) -> None:
    """Reject strict-looking node sets that no reviewed writer path can emit."""
    normal_branch = any(
        name == "normal-disable-proof.json"
        or name.startswith("disable")
        or name.startswith("disabled-")
        for name in seen
    )
    android_branch = any(name.startswith("recovery-") for name in seen)
    if normal_branch and android_branch:
        raise RootDataError("N1 recovery journal mixes normal and Android branches")

    stage_command_present = any(
        name.startswith(("stage-claim", "stage-zip", "stage-binding", "stage-verify"))
        for name in seen
    )
    if (
        stage_command_present
        and "events/01-native-canary-stage-intent.json" not in seen
    ):
        raise RootDataError("N1 stage command evidence lacks its intent event")

    install_present = "install-intent.json" in seen
    if install_present:
        required = {
            "events/01-native-canary-stage-intent.json",
            "stage-claim-result.json", "stage-claim.stdout", "stage-claim.stderr",
            "stage-zip-result.json", "stage-zip.stdout", "stage-zip.stderr",
            "stage-binding-result.json", "stage-binding.stdout", "stage-binding.stderr",
            "stage-verify-result.json", "stage-verify.stdout", "stage-verify.stderr",
        }
        if not required.issubset(seen):
            raise RootDataError("N1 install intent lacks its completed stage chain")
        decode_exact(
            require_complete_successful_command(run_dir, "stage-claim"),
            "N1 stage-claim predecessor",
            b"PASS_N1_STAGE_CLAIMED\n",
        )
        require_complete_successful_command(run_dir, "stage-zip")
        require_complete_successful_command(run_dir, "stage-binding")
        decode_exact(
            require_complete_successful_command(run_dir, "stage-verify"),
            "N1 stage-verify predecessor",
            b"PASS_N1_STAGE_EXACT\n",
        )

    install_command_present = any(
        name in seen
        for name in ("install-result.json", "install.stdout", "install.stderr")
    )
    if install_command_present and "events/02-native-canary-install-intent.json" not in seen:
        raise RootDataError("N1 install command evidence lacks its intent event")

    post_install_present = any(name.startswith("post-install-audit") for name in seen)
    if post_install_present:
        validate_install_output(require_complete_successful_command(run_dir, "install"))

    first_prefix = any(
        name.startswith("first-") or "first-observed" in name for name in seen
    )
    if first_prefix:
        decode_exact(
            require_complete_successful_command(run_dir, "post-install-audit"),
            "N1 first-reboot post-install predecessor",
            b"PASS_N1_POST_INSTALL_AUDIT\n",
        )
        if "first-reboot-intent.json" not in seen:
            raise RootDataError("N1 first-boot evidence lacks its reboot intent")
        first_reboot = read_exact_json(
            run_dir / "first-reboot-intent.json",
            "N1 first reboot prefix intent",
        )
        if (
            first_reboot.get("prior_boot_id_sha256")
            != prepared["binding"]["target"]["boot_id_sha256"]
        ):
            raise RootDataError("N1 first reboot prefix has the wrong source boot")
    if any(
        name.startswith("first-active-audit")
        or name in {"first-intent.raw", "first-result.raw"}
        or "first-observed" in name
        for name in seen
    ) and "first-observation.json" not in seen:
        raise RootDataError("N1 first-boot read evidence lacks its observation")
    if any(
        name in {"first-intent.raw", "first-result.raw"}
        or "first-observed" in name
        for name in seen
    ):
        decode_exact(
            require_complete_successful_command(run_dir, "first-active-audit"),
            "N1 first-state-read audit predecessor",
            b"PASS_N1_ACTIVE_AUDIT\n",
        )

    replay_prefix = any(name.startswith("replay-") for name in seen)
    if replay_prefix:
        required = {
            "events/03-native-canary-first-observed.json",
            "first-observation.json",
            "first-active-audit-result.json",
            "first-active-audit.stdout",
            "first-active-audit.stderr",
            "first-intent.raw",
            "first-result.raw",
            "replay-reboot-intent.json",
        }
        if not required.issubset(seen):
            raise RootDataError("N1 replay evidence lacks its completed first-boot chain")
        decode_exact(
            require_complete_successful_command(run_dir, "first-active-audit"),
            "N1 replay first-active predecessor",
            b"PASS_N1_ACTIVE_AUDIT\n",
        )
        read_canary_pair(run_dir, prepared, "first")
        replay_reboot = read_exact_json(
            run_dir / "replay-reboot-intent.json",
            "N1 replay reboot prefix intent",
        )
        first_observation = read_exact_json(
            run_dir / "first-observation.json",
            "N1 first reboot prefix observation",
        )
        if (
            replay_reboot.get("prior_boot_id_sha256")
            != first_observation.get("android_identity", {}).get("boot_id_sha256")
        ):
            raise RootDataError("N1 replay reboot prefix is not contiguous")
        if "replay-observation.json" in seen:
            replay_observation = read_exact_json(
                run_dir / "replay-observation.json",
                "N1 replay reboot prefix observation",
            )
            boot_ids = {
                prepared["binding"]["target"]["boot_id_sha256"],
                first_observation.get("android_identity", {}).get("boot_id_sha256"),
            }
            if replay_observation.get("android_identity", {}).get(
                "boot_id_sha256"
            ) in boot_ids:
                raise RootDataError("N1 replay reboot prefix reuses a boot identity")
    if any(
        name.startswith("replay-active-audit")
        or name in {"replay-intent.raw", "replay-result.raw"}
        for name in seen
    ) and "replay-observation.json" not in seen:
        raise RootDataError("N1 replay read evidence lacks its observation")
    if any(name in {"replay-intent.raw", "replay-result.raw"} for name in seen):
        decode_exact(
            require_complete_successful_command(run_dir, "replay-active-audit"),
            "N1 replay-state-read audit predecessor",
            b"PASS_N1_ACTIVE_AUDIT\n",
        )

    if "disable-intent.json" in seen:
        required = {
            "replay-observation.json",
            "replay-active-audit-result.json",
            "replay-active-audit.stdout",
            "replay-active-audit.stderr",
            "replay-intent.raw",
            "replay-result.raw",
        }
        if not required.issubset(seen):
            raise RootDataError("N1 disable intent lacks its completed replay chain")
        decode_exact(
            require_complete_successful_command(run_dir, "replay-active-audit"),
            "N1 disable replay-active predecessor",
            b"PASS_N1_ACTIVE_AUDIT\n",
        )
        first_intent, first_result, _ = read_canary_pair(run_dir, prepared, "first")
        replay_intent, replay_result, _ = read_canary_pair(run_dir, prepared, "replay")
        if (first_intent, first_result) != (replay_intent, replay_result):
            raise RootDataError("N1 disable intent follows changed replay evidence")
        disable_intent = read_exact_json(
            run_dir / "disable-intent.json",
            "N1 normal disable prefix intent",
        )
        replay_observation = read_exact_json(
            run_dir / "replay-observation.json",
            "N1 normal disable prefix observation",
        )
        if not exact_typed_equal(
            disable_intent.get("source_identity"),
            replay_observation.get("android_identity"),
        ):
            raise RootDataError("N1 normal disable prefix source is not contiguous")

    if "disabled-reboot-intent.json" in seen:
        if "disable-intent.json" not in seen:
            raise RootDataError("N1 disabled reboot prefix has no disable intent")
        disable_intent = read_exact_json(
            run_dir / "disable-intent.json",
            "N1 disabled reboot source intent",
        )
        disabled_reboot = read_exact_json(
            run_dir / "disabled-reboot-intent.json",
            "N1 disabled reboot prefix intent",
        )
        if (
            disabled_reboot.get("prior_boot_id_sha256")
            != disable_intent.get("source_identity", {}).get("boot_id_sha256")
        ):
            raise RootDataError("N1 disabled reboot prefix is not contiguous")
        proof_present = "normal-disable-proof.json" in seen
        if proof_present:
            proof = validate_normal_disable_proof(run_dir, prepared)
            if not exact_typed_equal(
                proof.get("source_identity"),
                disable_intent.get("source_identity"),
            ):
                raise RootDataError("N1 normal disable proof source is not contiguous")
        else:
            decode_exact(
                require_complete_successful_command(run_dir, "disable"),
                "N1 disabled reboot predecessor",
                b"PASS_N1_DISABLE_EXACT\n",
            )
    if any(
        name.startswith("disabled-audit")
        or name in {"disabled-intent.raw", "disabled-result.raw"}
        for name in seen
    ) and "disabled-observation.json" not in seen:
        raise RootDataError("N1 disabled read evidence lacks its observation")
    if any(name in {"disabled-intent.raw", "disabled-result.raw"} for name in seen):
        decode_exact(
            completed_readonly_command(run_dir, "disabled-audit"),
            "N1 disabled-state-read audit predecessor",
            b"PASS_N1_DISABLED_AUDIT\n",
        )
    if "disabled-observation.json" in seen:
        disabled_observation = read_exact_json(
            run_dir / "disabled-observation.json",
            "N1 disabled reboot prefix observation",
        )
        earlier = {
            prepared["binding"]["target"]["boot_id_sha256"],
            read_exact_json(
                run_dir / "first-observation.json",
                "N1 first reboot prefix observation",
            ).get("android_identity", {}).get("boot_id_sha256"),
            read_exact_json(
                run_dir / "replay-observation.json",
                "N1 replay reboot prefix observation",
            ).get("android_identity", {}).get("boot_id_sha256"),
        }
        if disabled_observation.get("android_identity", {}).get(
            "boot_id_sha256"
        ) in earlier:
            raise RootDataError("N1 disabled reboot prefix reuses a boot identity")

    if "recovery-disabled-reboot-intent.json" in seen:
        if "recovery-disable-intent.json" not in seen:
            raise RootDataError("N1 recovery reboot prefix has no disable intent")
        recovery_intent = read_exact_json(
            run_dir / "recovery-disable-intent.json",
            "N1 recovery reboot source intent",
        )
        recovery_reboot = read_exact_json(
            run_dir / "recovery-disabled-reboot-intent.json",
            "N1 recovery reboot prefix intent",
        )
        if (
            recovery_reboot.get("prior_boot_id_sha256")
            != recovery_intent.get("source_identity", {}).get("boot_id_sha256")
        ):
            raise RootDataError("N1 recovery reboot prefix is not contiguous")
        state = decode_recovery_state(
            require_complete_successful_command(run_dir, "recovery-disable"),
            "N1 recovery reboot predecessor",
            RECOVERY_STATE_OUTPUTS,
        )
        if state not in RECOVERY_STATE_ORDER:
            raise RootDataError("N1 recovery reboot predecessor state is invalid")
    if any(name.startswith("recovery-disabled-audit") for name in seen) and (
        "recovery-disabled-observation.json" not in seen
    ):
        raise RootDataError("N1 recovery audit lacks its reboot observation")
    if "recovery-disabled-observation.json" in seen:
        recovery_observation = read_exact_json(
            run_dir / "recovery-disabled-observation.json",
            "N1 recovery reboot prefix observation",
        )
        returned_boot_id = recovery_observation.get("android_identity", {}).get(
            "boot_id_sha256"
        )
        if returned_boot_id in known_boot_ids_before_observation(
            run_dir,
            prepared,
            "recovery-disabled",
        ):
            raise RootDataError("N1 recovery reboot prefix reuses a boot identity")

    if "cleanup-intent.json" in seen and "terminal-input.json" not in seen:
        raise RootDataError("N1 cleanup intent has no terminal input predecessor")
    terminal_predecessors = {"terminal-input.json"}
    if "stage-intent.json" in seen:
        terminal_predecessors.add("cleanup-intent.json")
    if (
        "terminal-result.json" in seen
        and not terminal_predecessors.issubset(seen)
    ):
        raise RootDataError("N1 terminal result lacks its cleanup prefix")


def validate_post_install_continuation(
    run_dir: Path,
    prepared: dict[str, Any],
) -> dict[str, Any]:
    if prepared.get("binding_sha256") != POST_INSTALL_PREDECESSOR_BINDING_SHA256:
        raise RootDataError("N1 post-install continuation binding is not authorized")
    value = read_exact_json(
        run_dir / "post-install-continuation.json",
        "N1 post-install continuation",
    )
    install_result = read_exact_blob(
        run_dir / "install-result.json",
        "N1 post-install continuation install result",
        MAX_OUTPUT,
    )
    install_stdout_sha256 = validate_install_output(
        require_complete_successful_command(run_dir, "install")
    )
    expected = {
        "schema": "s20plus_g986n_native_canary_r1_post_install_continuation_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "predecessor_root_data_runner": POST_INSTALL_PREDECESSOR_ROOT_RUNNER,
        "current_root_data_runner": self_receipt(),
        "install_result_sha256": hashlib.sha256(install_result).hexdigest(),
        "install_stdout_sha256": install_stdout_sha256,
        "attempt": 1,
        "device_effect_count": 0,
        "install_replay_permitted": False,
        "at": value.get("at") if isinstance(value, dict) else None,
    }
    if (
        not exact_typed_equal(value, expected)
        or type(value.get("attempt")) is not int
        or type(value.get("device_effect_count")) is not int
        or not isinstance(value.get("at"), str)
    ):
        raise RootDataError("N1 post-install continuation is malformed or mismatched")
    return value


def ensure_post_install_continuation(
    run_dir: Path,
    prepared: dict[str, Any],
) -> dict[str, Any]:
    if prepared.get("binding_sha256") != POST_INSTALL_PREDECESSOR_BINDING_SHA256:
        raise RootDataError("N1 post-install continuation binding is not authorized")
    path = run_dir / "post-install-continuation.json"
    if not os.path.lexists(path):
        install_result = read_exact_blob(
            run_dir / "install-result.json",
            "N1 post-install continuation install result",
            MAX_OUTPUT,
        )
        install_stdout_sha256 = validate_install_output(
            require_complete_successful_command(run_dir, "install")
        )
        durable_create(path, {
            "schema": "s20plus_g986n_native_canary_r1_post_install_continuation_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "predecessor_root_data_runner": POST_INSTALL_PREDECESSOR_ROOT_RUNNER,
            "current_root_data_runner": self_receipt(),
            "install_result_sha256": hashlib.sha256(install_result).hexdigest(),
            "install_stdout_sha256": install_stdout_sha256,
            "attempt": 1,
            "device_effect_count": 0,
            "install_replay_permitted": False,
            "at": utc_now(),
        })
    return validate_post_install_continuation(run_dir, prepared)


def validate_post_install_resume_cut(
    run_dir: Path,
    prepared: dict[str, Any],
) -> set[str]:
    if prepared.get("binding_sha256") != POST_INSTALL_PREDECESSOR_BINDING_SHA256:
        raise RootDataError("N1 post-install continuation binding is not authorized")
    seen = validate_recovery_journal(
        run_dir,
        prepared,
        allow_uncertain_commands=True,
    )
    if (
        not POST_INSTALL_RESUME_REQUIRED_FILES.issubset(seen)
        or not seen.issubset(POST_INSTALL_RESUME_ALLOWED_FILES)
    ):
        raise RootDataError("N1 post-install continuation journal is not at the exact cut")
    audit_present = any(name.startswith("post-install-audit") for name in seen)
    if audit_present and "post-install-continuation.json" not in seen:
        raise RootDataError("N1 post-install audit has no continuation predecessor")
    validate_install_output(require_complete_successful_command(run_dir, "install"))
    if "post-install-continuation.json" in seen:
        validate_post_install_continuation(run_dir, prepared)
    return seen


def validate_recovery_journal(
    run_dir: Path,
    prepared: dict[str, Any],
    allowed_extra: set[str] | None = None,
    *,
    allow_uncertain_commands: bool = False,
) -> set[str]:
    seen = scan_recovery_journal(run_dir, allowed_extra)
    validate_stage_intent(run_dir, prepared)
    if os.path.lexists(run_dir / "install-intent.json"):
        validate_install_intent(run_dir, prepared)
    elif any(
        os.path.lexists(run_dir / name)
        for name in ("install-result.json", "install.stdout", "install.stderr")
    ):
        raise RootDataError("N1 install evidence has no install intent")
    validate_prepared_event(run_dir, prepared)
    validate_action_event(run_dir, prepared, 1, "stage-intent", "stage-intent.json")
    validate_action_event(run_dir, prepared, 2, "install-intent", "install-intent.json")
    validate_first_observed_event(run_dir)
    for label in COMMAND_LABELS:
        validate_command_evidence(
            run_dir,
            label,
            allow_uncertain_consumed=allow_uncertain_commands,
        )
    for label in (
        "post-install-audit",
        "disabled-audit",
        "recovery-disabled-audit",
    ):
        if os.path.lexists(run_dir / f"{label}-resume.json"):
            read_readonly_resume(run_dir, label)
    if os.path.lexists(run_dir / "post-install-continuation.json"):
        validate_post_install_continuation(run_dir, prepared)
    validate_optional_effect_intents(run_dir, prepared)
    if os.path.lexists(run_dir / "normal-disable-proof.json"):
        if not os.path.lexists(run_dir / "disable-intent.json"):
            raise RootDataError("N1 normal disable proof has no disable intent")
        validate_normal_disable_proof(run_dir, prepared)
    for phase in ("first", "replay", "disabled", "recovery-disabled"):
        validate_reboot_evidence(run_dir, prepared, phase)
    for label in ("first", "replay", "disabled", "recovery"):
        validate_optional_canary_pair(run_dir, prepared, label)
    validate_recovery_prefix_graph(run_dir, prepared, seen)
    return seen


def complete_command_tuple(run_dir: Path, label: str) -> tuple[int, bytes, bytes]:
    receipt = validate_command_evidence(run_dir, label)
    if (
        receipt is None
        or receipt.get("schema")
        != "s20plus_g986n_native_canary_r1_command_result_v1"
    ):
        raise RootDataError(f"N1 {label} lacks a complete command receipt")
    return (
        receipt["returncode"],
        read_exact_blob(run_dir / f"{label}.stdout", f"N1 {label} stdout", MAX_OUTPUT),
        read_exact_blob(run_dir / f"{label}.stderr", f"N1 {label} stderr", MAX_OUTPUT),
    )


def read_readonly_resume(
    run_dir: Path,
    label: str,
    maximum: int = MAX_OUTPUT,
) -> tuple[int, bytes, bytes]:
    value = read_exact_json(
        run_dir / f"{label}-resume.json",
        f"N1 {label} read-only resume",
    )
    source_paths = {
        "result": run_dir / f"{label}-result.json",
        "stdout": run_dir / f"{label}.stdout",
        "stderr": run_dir / f"{label}.stderr",
    }
    actual_source = sorted(
        key for key, path in source_paths.items() if os.path.lexists(path)
    )
    if (
        not isinstance(value, dict)
        or set(value) != {
            "schema", "version", "label", "returncode", "stdout_hex",
            "stderr_hex", "source_evidence", "read_only", "device_effect_count",
        }
        or value.get("schema")
        != "s20plus_g986n_native_canary_r1_readonly_resume_v1"
        or value.get("version") != VERSION
        or value.get("label") != label
        or type(value.get("returncode")) is not int
        or value.get("read_only") is not True
        or type(value.get("device_effect_count")) is not int
        or value.get("device_effect_count") != 0
        or not isinstance(value.get("stdout_hex"), str)
        or re.fullmatch(r"(?:[0-9a-f]{2})*", value.get("stdout_hex")) is None
        or not isinstance(value.get("stderr_hex"), str)
        or re.fullmatch(r"(?:[0-9a-f]{2})*", value.get("stderr_hex")) is None
        or not isinstance(value.get("source_evidence"), list)
        or any(item not in {"result", "stdout", "stderr"} for item in value["source_evidence"])
        or value["source_evidence"] != sorted(set(value["source_evidence"]))
        or value["source_evidence"] != actual_source
    ):
        raise RootDataError(f"N1 {label} read-only resume evidence is malformed")
    source_receipt = validate_command_evidence(
        run_dir,
        label,
        allow_uncertain_consumed=True,
    )
    if (
        isinstance(source_receipt, dict)
        and source_receipt.get("schema")
        == "s20plus_g986n_native_canary_r1_command_result_v1"
    ):
        raise RootDataError(
            f"N1 {label} read-only resume duplicates complete command evidence"
        )
    try:
        stdout = bytes.fromhex(value["stdout_hex"])
        stderr = bytes.fromhex(value["stderr_hex"])
    except ValueError as exc:
        raise RootDataError(f"N1 {label} read-only resume bytes are malformed") from exc
    if len(stdout) + len(stderr) > maximum:
        raise RootDataError(f"N1 {label} read-only resume output is oversized")
    return value["returncode"], stdout, stderr


def complete_readonly_command(
    run_dir: Path,
    label: str,
    argv: list[str],
    command: Command,
    timeout: float,
    maximum: int = MAX_OUTPUT,
) -> tuple[int, bytes, bytes]:
    resume_path = run_dir / f"{label}-resume.json"
    if os.path.lexists(resume_path):
        return read_readonly_resume(run_dir, label, maximum)
    paths = {
        "result": run_dir / f"{label}-result.json",
        "stdout": run_dir / f"{label}.stdout",
        "stderr": run_dir / f"{label}.stderr",
    }
    present = {key for key, path in paths.items() if os.path.lexists(path)}
    if not present:
        return durable_command_result(run_dir, label, argv, command, timeout, maximum)
    source_receipt = validate_command_evidence(
        run_dir,
        label,
        allow_uncertain_consumed=True,
    )
    if (
        isinstance(source_receipt, dict)
        and source_receipt.get("schema")
        == "s20plus_g986n_native_canary_r1_command_result_v1"
    ):
        return complete_command_tuple(run_dir, label)
    rc, stdout, stderr = command(argv, timeout, maximum)
    if (
        type(rc) is not int
        or not isinstance(stdout, bytes)
        or not isinstance(stderr, bytes)
        or len(stdout) + len(stderr) > maximum
    ):
        raise RootDataError(f"N1 {label} read-only resume returned malformed evidence")
    durable_create(resume_path, {
        "schema": "s20plus_g986n_native_canary_r1_readonly_resume_v1",
        "version": VERSION,
        "label": label,
        "returncode": rc,
        "stdout_hex": stdout.hex(),
        "stderr_hex": stderr.hex(),
        "source_evidence": sorted(present),
        "read_only": True,
        "device_effect_count": 0,
    })
    return rc, stdout, stderr


def completed_readonly_command(
    run_dir: Path,
    label: str,
    maximum: int = MAX_OUTPUT,
) -> tuple[int, bytes, bytes]:
    if os.path.lexists(run_dir / f"{label}-resume.json"):
        return read_readonly_resume(run_dir, label, maximum)
    return complete_command_tuple(run_dir, label)


def read_canary_pair(
    run_dir: Path,
    prepared: dict[str, Any],
    label: str,
) -> tuple[bytes, bytes, dict[str, Any]]:
    intent = read_exact_blob(
        run_dir / f"{label}-intent.raw", f"N1 {label} canary intent", MAX_STATE_FILE
    )
    result = read_exact_blob(
        run_dir / f"{label}-result.raw", f"N1 {label} canary result", MAX_STATE_FILE
    )
    return intent, result, validate_canary_files(intent, result, prepared)


def validate_recovery_source_canary_binding(
    run_dir: Path,
    prepared: dict[str, Any],
    recovery_intent: dict[str, Any],
) -> tuple[bytes, bytes, dict[str, Any]] | None:
    """Bind a completed recovery source to the exact durable canary bytes."""
    if recovery_intent.get("source_state_class") != "completed":
        return None
    intent, result, parsed = read_canary_pair(run_dir, prepared, "recovery")
    result_sha256 = hashlib.sha256(result).hexdigest()
    if result_sha256 != recovery_intent.get("source_canary_result_sha256"):
        raise RootDataError("N1 recovery source canary result hash is mismatched")
    require_canary_boot(
        parsed,
        recovery_intent.get("source_canary_boot_id_sha256"),
        "N1 recovery source canary result",
    )
    if recovery_intent.get("source_boot_observed") is True:
        first_intent, first_result, first_parsed = read_canary_pair(
            run_dir,
            prepared,
            "first",
        )
        if (intent, result) != (first_intent, first_result):
            raise RootDataError(
                "N1 observed recovery source differs from the first canary evidence"
            )
        first_observation = read_exact_json(
            run_dir / "first-observation.json",
            "N1 recovery source first observation",
        )
        first_boot_id = first_observation.get("android_identity", {}).get(
            "boot_id_sha256"
        )
        require_canary_boot(
            first_parsed,
            first_boot_id,
            "N1 first canary evidence",
        )
        if (
            recovery_intent.get("source_canary_boot_id_sha256") != first_boot_id
            or recovery_intent.get("source_canary_result_sha256")
            != hashlib.sha256(first_result).hexdigest()
        ):
            raise RootDataError(
                "N1 observed recovery source is not bound to the first canary evidence"
            )
    elif os.path.lexists(run_dir / "first-observation.json"):
        raise RootDataError(
            "N1 unobserved recovery source conflicts with a first observation"
        )
    return intent, result, parsed


def validate_normal_reboot_chain(
    prepared: dict[str, Any],
    first_reboot: dict[str, Any],
    first_observation: dict[str, Any],
    replay_reboot: dict[str, Any],
    replay_observation: dict[str, Any],
    disabled_reboot: dict[str, Any],
    disabled_observation: dict[str, Any],
) -> None:
    if (
        first_reboot.get("prior_boot_id_sha256")
        != prepared["binding"]["target"]["boot_id_sha256"]
        or replay_reboot.get("prior_boot_id_sha256")
        != first_observation.get("android_identity", {}).get("boot_id_sha256")
        or disabled_reboot.get("prior_boot_id_sha256")
        != replay_observation.get("android_identity", {}).get("boot_id_sha256")
    ):
        raise RootDataError("N1 normal reboot chain is not contiguous")
    boot_ids = (
        prepared["binding"]["target"]["boot_id_sha256"],
        first_observation.get("android_identity", {}).get("boot_id_sha256"),
        replay_observation.get("android_identity", {}).get("boot_id_sha256"),
        disabled_observation.get("android_identity", {}).get("boot_id_sha256"),
    )
    if any(
        not isinstance(boot_id, str)
        or re.fullmatch(r"[0-9a-f]{64}", boot_id) is None
        for boot_id in boot_ids
    ) or len(set(boot_ids)) != len(boot_ids):
        raise RootDataError("N1 normal reboot chain reuses a boot identity")


def validate_recovery_reboot_chain(
    run_dir: Path,
    prepared: dict[str, Any],
    recovery_intent: dict[str, Any],
    recovery_reboot: dict[str, Any],
    recovery_observation: dict[str, Any],
) -> None:
    source_boot_id = recovery_intent.get("source_identity", {}).get(
        "boot_id_sha256"
    )
    returned_boot_id = recovery_observation.get("android_identity", {}).get(
        "boot_id_sha256"
    )
    if (
        not isinstance(source_boot_id, str)
        or re.fullmatch(r"[0-9a-f]{64}", source_boot_id) is None
        or not isinstance(returned_boot_id, str)
        or re.fullmatch(r"[0-9a-f]{64}", returned_boot_id) is None
        or recovery_reboot.get("prior_boot_id_sha256") != source_boot_id
    ):
        raise RootDataError("N1 Android-recovery reboot chain is not contiguous")
    if (
        returned_boot_id == source_boot_id
        or returned_boot_id
        in known_boot_ids_before_observation(
            run_dir,
            prepared,
            "recovery-disabled",
        )
    ):
        raise RootDataError("N1 Android-recovery reboot chain reuses a boot identity")


def derived_terminal_fields(
    run_dir: Path,
    prepared: dict[str, Any],
    live_identity: dict[str, str],
) -> dict[str, Any]:
    install_present = os.path.lexists(run_dir / "install-intent.json")
    if not install_present:
        validate_pre_install_cut(run_dir, prepared)
        boot_changed = (
            live_identity["boot_id_sha256"]
            != prepared["binding"]["target"]["boot_id_sha256"]
        )
        require_returned_target(
            prepared,
            live_identity,
            "N1 pre-install terminal target",
            require_boot_change=boot_changed,
        )
        return {
            "verdict": "ABORTED_S20PLUS_G986N_NATIVE_CANARY_N1_BEFORE_INSTALL_HEALTHY",
            "identity": live_identity,
            "result_sha256": None,
            "recovery": "pre-install-abort",
            "state_class": "absent",
            "install_intent_count": 0,
            "require_boot_change": boot_changed,
        }

    branch_markers = {
        "normal": any(
            os.path.lexists(run_dir / name)
            for name in ("disable-intent.json", "disabled-observation.json", "disabled-audit-result.json")
        ),
        "android-disable": any(
            os.path.lexists(run_dir / name)
            for name in (
                "recovery-disable-intent.json", "recovery-disabled-observation.json",
                "recovery-disabled-audit-result.json",
            )
        ),
    }
    selected_branches = [name for name, present in branch_markers.items() if present]
    if len(selected_branches) != 1:
        raise RootDataError("N1 terminal branch is absent or ambiguous")
    recovery = selected_branches[0]
    validate_recovery_journal(
        run_dir,
        prepared,
        allow_uncertain_commands=True,
    )
    for label in COMMAND_LABELS:
        if label != "cleanup" and any(
            os.path.lexists(run_dir / name)
            for name in (f"{label}-result.json", f"{label}.stdout", f"{label}.stderr")
        ):
            validate_command_evidence(
                run_dir,
                label,
                allow_uncertain_consumed=True,
            )

    result_sha: str | None = None
    state_class: str
    identity = live_identity
    if recovery == "normal":
        required = {
            "first-reboot-intent.json", "first-reboot-result.json",
            "first-observation.json", "first-active-audit-result.json",
            "replay-reboot-intent.json", "replay-reboot-result.json",
            "replay-observation.json", "replay-active-audit-result.json",
            "disable-intent.json", "disabled-reboot-intent.json",
            "disabled-observation.json",
            "first-intent.raw", "first-result.raw",
            "replay-intent.raw", "replay-result.raw", "disabled-intent.raw",
            "disabled-result.raw",
        }
        seen = scan_recovery_journal(run_dir)
        if not required.issubset(seen):
            raise RootDataError("N1 normal terminal journal is incomplete")
        decode_exact(
            complete_command_tuple(run_dir, "first-active-audit"),
            "N1 first active terminal audit",
            b"PASS_N1_ACTIVE_AUDIT\n",
        )
        decode_exact(
            complete_command_tuple(run_dir, "replay-active-audit"),
            "N1 replay active terminal audit",
            b"PASS_N1_ACTIVE_AUDIT\n",
        )
        decode_exact(
            completed_readonly_command(run_dir, "disabled-audit"),
            "N1 disabled terminal audit",
            b"PASS_N1_DISABLED_AUDIT\n",
        )
        first_intent, first_result, parsed = read_canary_pair(run_dir, prepared, "first")
        replay_intent, replay_result, _ = read_canary_pair(run_dir, prepared, "replay")
        disabled_intent, disabled_result, _ = read_canary_pair(run_dir, prepared, "disabled")
        if (first_intent, first_result) != (replay_intent, replay_result) or (
            first_intent,
            first_result,
        ) != (disabled_intent, disabled_result):
            raise RootDataError("N1 normal terminal canary evidence changed")
        first_observation = read_exact_json(
            run_dir / "first-observation.json", "N1 first observation"
        )
        replay_observation = read_exact_json(
            run_dir / "replay-observation.json", "N1 replay observation"
        )
        first_reboot = read_exact_json(
            run_dir / "first-reboot-intent.json", "N1 first reboot intent"
        )
        replay_reboot = read_exact_json(
            run_dir / "replay-reboot-intent.json", "N1 replay reboot intent"
        )
        disabled_reboot = read_exact_json(
            run_dir / "disabled-reboot-intent.json", "N1 disabled reboot intent"
        )
        disabled_observation = read_exact_json(
            run_dir / "disabled-observation.json", "N1 disabled observation"
        )
        validate_normal_reboot_chain(
            prepared,
            first_reboot,
            first_observation,
            replay_reboot,
            replay_observation,
            disabled_reboot,
            disabled_observation,
        )
        require_canary_boot(
            parsed,
            first_observation.get("android_identity", {}).get("boot_id_sha256"),
            "N1 normal terminal canary result",
        )
        identity = disabled_observation["android_identity"]
        if live_identity != identity:
            raise RootDataError("N1 normal terminal target changed after final observation")
        state_class = "completed"
        result_sha = hashlib.sha256(first_result).hexdigest()
        verdict = "PASS_S20PLUS_G986N_NATIVE_CANARY_N1_DISABLED_ROOTED_HEALTHY"
    elif recovery == "android-disable":
        required = {
            "recovery-disable-intent.json", "recovery-disable-result.json",
            "recovery-disabled-reboot-intent.json",
            "recovery-disabled-observation.json",
        }
        seen = scan_recovery_journal(run_dir)
        if not required.issubset(seen):
            raise RootDataError("N1 Android-recovery terminal journal is incomplete")
        disabled_state = decode_recovery_state(
            complete_command_tuple(run_dir, "recovery-disable"),
            "N1 Android-recovery disable receipt",
            RECOVERY_STATE_OUTPUTS,
        )
        audited_state_class = decode_recovery_state(
            completed_readonly_command(run_dir, "recovery-disabled-audit"),
            "N1 Android-recovery terminal audit",
            RECOVERY_AUDIT_OUTPUTS,
        )
        require_monotonic_recovery_state(
            disabled_state,
            audited_state_class,
            "N1 Android-recovery terminal state",
        )
        state_class = audited_state_class
        observation = read_exact_json(
            run_dir / "recovery-disabled-observation.json",
            "N1 recovery-disabled observation",
        )
        identity = observation["android_identity"]
        recovery_intent = read_exact_json(
            run_dir / "recovery-disable-intent.json", "N1 recovery-disable intent"
        )
        recovery_reboot = read_exact_json(
            run_dir / "recovery-disabled-reboot-intent.json",
            "N1 recovery-disabled reboot intent",
        )
        validate_recovery_reboot_chain(
            run_dir,
            prepared,
            recovery_intent,
            recovery_reboot,
            observation,
        )
        require_monotonic_recovery_state(
            recovery_intent["source_state_class"],
            disabled_state,
            "N1 Android-recovery source state",
        )
        if live_identity != identity:
            raise RootDataError("N1 Android-recovery terminal target changed")
        if state_class == "completed":
            _intent, result, parsed = read_canary_pair(run_dir, prepared, "recovery")
            result_sha = hashlib.sha256(result).hexdigest()
            if recovery_intent["source_state_class"] == "completed" and (
                result_sha != recovery_intent["source_canary_result_sha256"]
            ):
                raise RootDataError("N1 Android-recovery source result changed")
            require_canary_boot(
                parsed,
                recovery_intent["source_canary_boot_id_sha256"]
                if recovery_intent["source_canary_boot_id_sha256"] is not None
                else recovery_intent["source_identity"]["boot_id_sha256"],
                "N1 Android-recovery terminal canary result",
            )
            if recovery_intent["source_boot_observed"]:
                source = read_exact_json(
                    run_dir / "first-observation.json", "N1 first observation"
                )["android_identity"]["boot_id_sha256"]
                require_canary_boot(
                    parsed,
                    source,
                    "N1 Android-recovery terminal canary result",
                )
            else:
                state_class = COMPLETED_SOURCE_UNOBSERVED
        verdict = "RECOVERED_S20PLUS_G986N_NATIVE_CANARY_N1_DISABLED_ROOTED_HEALTHY"
    require_returned_target(prepared, identity, "N1 derived terminal target")
    return {
        "verdict": verdict,
        "identity": identity,
        "result_sha256": result_sha,
        "recovery": recovery,
        "state_class": state_class,
        "install_intent_count": 1,
        "require_boot_change": True,
    }


def finalize_terminal(
    run_dir: Path,
    command: Command = bootstrap.bounded_command,
) -> dict[str, Any]:
    require_active()
    terminal_present = os.path.lexists(run_dir / "terminal-result.json")
    prepared = read_prepared(
        run_dir,
        input_scope="root-terminal-release" if terminal_present else "root-recovery",
        allow_released_terminal=terminal_present,
    )
    input_present = os.path.lexists(run_dir / "terminal-input.json")
    if terminal_present:
        if not input_present:
            raise RootDataError("N1 terminal result has no terminal input")
        terminal_input = read_terminal_input(run_dir, prepared)
        derived = derived_terminal_fields(
            run_dir,
            prepared,
            terminal_input["target_identity"],
        )
        terminal = read_exact_json(run_dir / "terminal-result.json", "N1 terminal result")
        staged_absence = terminal.get("staged_input_absence_evidence")
    else:
        adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
        selected, _values, live_identity = bootstrap.android_health_once(command, adb)
        require_returned_target(
            prepared,
            live_identity,
            "N1 terminal finalizer target",
            require_boot_change=None,
        )
        recovery_magisk_preflight(command, adb, selected, live_identity, prepared)
        derived = derived_terminal_fields(run_dir, prepared, live_identity)
        if input_present:
            terminal_input = read_terminal_input(run_dir, prepared)
            expected = terminal_input_value(
                prepared,
                derived["verdict"],
                derived["identity"],
                derived["result_sha256"],
                derived["recovery"],
                derived["state_class"],
                derived["install_intent_count"],
                derived["require_boot_change"],
                terminal_input["at"],
            )
            if not exact_typed_equal(terminal_input, expected):
                raise RootDataError("N1 terminal input differs from its branch journal")
        else:
            terminal_input = write_terminal_input(
                run_dir,
                prepared,
                derived["verdict"],
                derived["identity"],
                derived["result_sha256"],
                recovery=derived["recovery"],
                canary_state_class=derived["state_class"],
                install_intent_count=derived["install_intent_count"],
                require_boot_change=derived["require_boot_change"],
            )
        if os.path.lexists(run_dir / "stage-intent.json"):
            settle_cleanup_without_replay(run_dir, prepared, selected, command)
        staged_absence = stage_absence_evidence(command, adb, selected)
        confirm_rooted_terminal_state(
            run_dir,
            prepared,
            command,
            derived["identity"],
            derived["recovery"],
            derived["state_class"],
        )
    return write_terminal(
        run_dir,
        prepared,
        derived["verdict"],
        derived["identity"],
        derived["result_sha256"],
        recovery=derived["recovery"],
        canary_state_class=derived["state_class"],
        install_intent_count=derived["install_intent_count"],
        require_boot_change=derived["require_boot_change"],
        staged_input_absence=staged_absence,
    )


def assert_stock_handoff_eligible_journal(
    run_dir: Path,
    seen: set[str],
) -> None:
    """Reject stock fallback after an exact completed rooted recovery proof."""
    for label in (
        "disabled-audit",
        "recovery-disabled-audit",
    ):
        if (
            {
                f"{label}.stdout", f"{label}.stderr", f"{label}-result.json"
            }.issubset(seen)
            or f"{label}-resume.json" in seen
        ):
            receipt = completed_readonly_command(run_dir, label)
            semantically_complete = False
            try:
                if label == "disabled-audit":
                    decode_exact(
                        receipt,
                        "N1 rooted recovery proof",
                        b"PASS_N1_DISABLED_AUDIT\n",
                    )
                else:
                    decode_recovery_state(
                        receipt,
                        "N1 rooted recovery proof",
                        RECOVERY_AUDIT_OUTPUTS,
                    )
                semantically_complete = True
            except RootDataError:
                semantically_complete = False
            if semantically_complete:
                raise RootDataError(
                    "N1 stock handoff cannot replace a completed rooted recovery proof"
                )


def create_stock_handoff(run_dir: Path, confirmation: str) -> Path:
    require_active()
    prepared = read_prepared(run_dir, input_scope="stock-recovery")
    if confirmation != STOCK_HANDOFF_CONFIRM:
        raise RootDataError("N1 stock-recovery handoff confirmation mismatch")
    if not os.path.lexists(run_dir / "install-intent.json"):
        raise RootDataError("N1 stock recovery requires a consumed install intent")
    if any(os.path.lexists(run_dir / name) for name in (
        "terminal-input.json", "terminal-result.json", "rollback-intent.json",
        "stock-recovery-handoff.json", "cleanup-intent.json",
    )):
        raise RootDataError("N1 stock-recovery handoff is duplicated or inconsistent")
    seen = validate_recovery_journal(
        run_dir,
        prepared,
        allow_uncertain_commands=True,
    )
    assert_stock_handoff_eligible_journal(run_dir, seen)
    value = {
        "schema": "s20plus_g986n_native_canary_r1_stock_handoff_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "run_dir": str(run_dir),
        "stock_boot": prepared["binding"]["artifacts"]["stock_boot"],
        "recovery_runner": prepared["binding"]["closure"]["stock_recovery_runner"],
        "operator_confirmed": True,
        "operator_asserted_rooted_recovery_unavailable": True,
        "confirmation": STOCK_HANDOFF_CONFIRM,
        "attempt": 1,
        "replay_permitted": False,
        "at": utc_now(),
    }
    path = run_dir / "stock-recovery-handoff.json"
    durable_create(path, value)
    return path


def render_plan() -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_native_canary_r1_plan_v1",
        "version": VERSION,
        "active": NATIVE_CANARY_R1_ACTIVE,
        "tier": "R1",
        "target": f"{bootstrap.EXPECTED_MODEL}/{bootstrap.EXPECTED_DEVICE}/{bootstrap.EXPECTED_INCREMENTAL}",
        "module_id": MODULE_ID,
        "module_zip": {
            "size": MODULE_ZIP_SIZE,
            "sha256": MODULE_ZIP_SHA256,
            "host_mode": "0600",
        },
        "binary": {"size": BINARY_SIZE, "sha256": BINARY_SHA256},
        "state_dir": STATE_DIR,
        "stage_dir": STAGE_DIR,
        "install_attempts": 1,
        "normal_reboot_budget": 3,
        "post_install_resume": {
            "predecessor_binding_sha256": (
                POST_INSTALL_PREDECESSOR_BINDING_SHA256
            ),
            "predecessor_root_data_runner_sha256": (
                POST_INSTALL_PREDECESSOR_ROOT_RUNNER["sha256"]
            ),
            "install_replay_permitted": False,
        },
        "stock_recovery_attempts": 1,
        "generic_root_command_surface": False,
        "partition_payloads": ["boot-only-stock-recovery"],
        "live_authority": NATIVE_CANARY_R1_ACTIVE,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-plan", action="store_true")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--resume-after-install", action="store_true")
    parser.add_argument("--abort-pre-install", action="store_true")
    parser.add_argument("--recover-android", action="store_true")
    parser.add_argument("--finalize-terminal", action="store_true")
    parser.add_argument("--create-stock-handoff", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--approval")
    parser.add_argument("--confirmation")
    args = parser.parse_args()
    modes = sum((
        args.render_plan,
        args.prepare,
        args.execute,
        args.resume_after_install,
        args.abort_pre_install,
        args.recover_android,
        args.finalize_terminal,
        args.create_stock_handoff,
    ))
    if modes != 1:
        parser.error("choose exactly one N1 mode")
    if args.render_plan:
        if args.run_id is not None or args.approval is not None or args.confirmation is not None:
            parser.error("--render-plan accepts no run or approval input")
        print(json.dumps(render_plan(), sort_keys=True))
        return 0
    require_active()
    if args.prepare:
        if args.run_id is not None or args.approval is not None or args.confirmation is not None:
            parser.error("--prepare accepts no caller-selected run or approval input")
        if os.path.lexists(guard_path()):
            output = resume_prepared_cli_output()
        else:
            output = prepared_cli_output(prepare())
        print(json.dumps(output, sort_keys=True))
        return 0
    if args.run_id is None:
        parser.error("--run-id is required")
    run_dir = resolve_run_id(args.run_id)
    if args.execute:
        if args.approval is None or args.confirmation is not None:
            parser.error("--approval is required")
        result = execute(run_dir, args.approval)
    elif args.resume_after_install:
        if args.approval is not None or args.confirmation is not None:
            parser.error("--resume-after-install accepts only --run-id")
        result = resume_after_install(run_dir)
    elif args.abort_pre_install:
        if args.approval is not None or args.confirmation is not None:
            parser.error("--abort-pre-install accepts only --run-id")
        result = abort_pre_install(run_dir)
    elif args.recover_android:
        if args.approval is not None or args.confirmation is not None:
            parser.error("--recover-android accepts only --run-id")
        result = recover_android(run_dir)
    elif args.finalize_terminal:
        if args.approval is not None or args.confirmation is not None:
            parser.error("--finalize-terminal accepts only --run-id")
        result = finalize_terminal(run_dir)
    else:
        if args.confirmation is None or args.approval is not None:
            parser.error("--create-stock-handoff accepts only --run-id and --confirmation")
        result = {"handoff_created": create_stock_handoff(run_dir, args.confirmation).name}
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

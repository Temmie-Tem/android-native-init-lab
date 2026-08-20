#!/usr/bin/env python3
"""Dormant fixed-consumer backend primitives for S20+ N3-U0 attended F1."""

from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
import hashlib
import json
import os
import re
import stat
import sys
import time
import types
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
SCHEMA = "s20plus_g986n_n3u0_attended_f1_backend_h0_v1"
STATUS = "H0_CONCRETE_BACKEND_PASS_GO_NOT_ACTIVE"
BACKEND_ACTIVE = False
EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256 = "8ac9dcac66196ec7a1585ae6e1e4ba9c2c3ed75f7d573aca0d90049bbb0bc8c6"
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_RAW_BYTES = 8 * 1024 * 1024
DOWNLOAD_TIMEOUT_SEC = 180
CAPTURE_OPERATIONS = frozenset(
    {
        "initial-download-reboot",
        "initial-download-observation",
        "candidate-transfer",
        "candidate-observation",
        "rollback-download-reboot",
        "rollback-download-observation",
        "physical-download-entry",
        "physical-download-observation",
        "rollback-transfer",
        "final-resident-health",
    }
)

TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "build": "G986NKSS8IYC2",
}

INTEGRATION_BINDING_SHA256 = (
    "2a037eb3cab5f068b0d534d034fcadce51b26c3ee9f5874ec583b90905a6d6a6"
)
SOURCES = {
    "integration": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_n3u0_attended_f1_integration_h0.py",
        "size": 18_516,
        "sha256": "4b5234f818306ffc8d361ee8b14b15c74702b23b05f752c5acef5171071bc3a0",
    },
    "bootstrap": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_g986n_magisk_bootstrap_f1.py",
        "size": 161_259,
        "sha256": "11ca8aaef183e76c6eeec1a43e75b00bbc14e4b51650e3122c8f4bbdfdc8799f",
    },
    "inventory": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_g986n_d0_inventory.py",
        "size": 21_474,
        "sha256": "3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81",
    },
    "routine": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_g986n_routine_d0.py",
        "size": 12_649,
        "sha256": "2377e463e1ec4869fd9ba7a5155aeb6c792bdb5b5b969c902a2b0e5a00fda77c",
    },
    "transport": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s22plus_boot_only_f1_transport.py",
        "size": 10_937,
        "sha256": "f18e2e453e33078a184653722d4579a184c59b1c3ac10f9eb54d4a4ba437ffea",
    },
    "raw_capture": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "device_action_raw_capture_v1.py",
        "size": 25_006,
        "sha256": "410e260129c0c50dca29b008dc7cf1051ee007816ab18bea76aeae62505ca0e4",
    },
    "boot_verify": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s22plus_boot_verify.py",
        "size": 37_806,
        "sha256": "e19d604039a744d14bcdbb495951e95f86666b6927061529e440aacb4b63381d",
    },
    "observer": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_n3u0_usb_observer.py",
        "size": 16_713,
        "sha256": "f1c6af4123684be1122950442472de7803995345e125955322a8fd262b25e44f",
    },
    "owner": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_n3u0_attended_owner_h0.py",
        "size": 14_125,
        "sha256": "db1b282e33218ea9f7a48b8b90b28b50a121dab3429b3f642ebf0e90ff940eca",
    },
    "classifier": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/device_action_f1_v2.py",
        "size": 80_851,
        "sha256": "4e61a7511cc2ed103d1cac4d1afdd2c91d6edc41e30d9bc2832229286d9ee290",
    },
}

USB_NODE_RE = re.compile(r"[0-9]+-[0-9]+(?:\.[0-9]+)*")
HEX64_RE = re.compile(r"[0-9a-f]{64}")


class BackendError(RuntimeError):
    pass


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


def _read_exact(path: Path, expected: dict[str, Any], label: str) -> bytes:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as exc:
        raise BackendError(f"{label} is unavailable") from exc
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
            raise BackendError(f"{label} identity differs")
        payload = bytearray()
        while len(payload) < size:
            block = os.read(descriptor, min(1024 * 1024, size - len(payload)))
            if not block:
                break
            payload.extend(block)
        if len(payload) != size or os.read(descriptor, 1):
            raise BackendError(f"{label} length differs")
    finally:
        os.close(descriptor)
    result = bytes(payload)
    if hashlib.sha256(result).hexdigest() != expected["sha256"]:
        raise BackendError(f"{label} hash differs")
    return result


def _load_exact(expected: dict[str, Any], name: str) -> Any:
    payload = _read_exact(expected["path"], expected, name)
    module = types.ModuleType(name)
    module.__file__ = str(expected["path"])
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        exec(compile(payload, str(expected["path"]), "exec"), module.__dict__)
    except Exception:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
        raise
    return module


@contextmanager
def _bound_imports(modules: dict[str, Any]):
    previous = {name: sys.modules.get(name) for name in modules}
    sys.modules.update(modules)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


def _load_classifier_exact() -> Any:
    expected = SOURCES["classifier"]
    payload = _read_exact(expected["path"], expected, "N3-U0 backend classifier")
    tree = ast.parse(payload, filename=str(expected["path"]))
    selected = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "classify_odin_output"
    ]
    if len(selected) != 1:
        raise BackendError("classifier entrypoint is not unique")
    module = types.ModuleType("device_action_f1_v2_bound")
    module.__file__ = str(expected["path"])
    isolated = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(isolated)
    exec(compile(isolated, str(expected["path"]), "exec"), module.__dict__)
    return module


def source_receipts() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name, expected in SOURCES.items():
        _read_exact(expected["path"], expected, f"N3-U0 backend {name}")
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
        raise BackendError("backend runner is unavailable") from exc
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or not 0 < info.st_size <= MAX_SOURCE_BYTES
        ):
            raise BackendError("backend runner identity differs")
        payload = bytearray()
        while len(payload) < info.st_size:
            block = os.read(descriptor, min(1024 * 1024, info.st_size - len(payload)))
            if not block:
                break
            payload.extend(block)
        if len(payload) != info.st_size or os.read(descriptor, 1):
            raise BackendError("backend runner length differs")
    finally:
        os.close(descriptor)
    normalized = re.sub(
        rb'EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256 = "[0-9a-f]{64}"',
        b'EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256 = "' + b"0" * 64 + b'"',
        bytes(payload),
        count=1,
    )
    normalized_sha256 = hashlib.sha256(normalized).hexdigest()
    if normalized_sha256 != EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256:
        raise BackendError("backend runner normalized identity differs")
    return {
        "path": str(path),
        "size": info.st_size,
        "normalized_sha256": normalized_sha256,
    }


def load_sources() -> dict[str, Any]:
    integration = _load_exact(SOURCES["integration"], "n3u0_integration_bound")
    if integration.binding_sha256() != INTEGRATION_BINDING_SHA256:
        raise BackendError("consumer integration binding differs")
    if integration.INTEGRATION_ACTIVE is not False:
        raise BackendError("consumer integration unexpectedly exposes authority")
    inventory = _load_exact(SOURCES["inventory"], "n3u0_inventory_bound")
    with _bound_imports({"s20plus_g986n_d0_inventory": inventory}):
        routine = _load_exact(SOURCES["routine"], "n3u0_routine_bound")
    boot_verify = _load_exact(SOURCES["boot_verify"], "n3u0_boot_verify_bound")
    raw_capture = _load_exact(SOURCES["raw_capture"], "n3u0_raw_capture_bound")
    with _bound_imports(
        {
            "s22plus_boot_verify": boot_verify,
            "device_action_raw_capture_v1": raw_capture,
        }
    ):
        transport = _load_exact(SOURCES["transport"], "n3u0_transport_bound")
    classifier = _load_classifier_exact()
    bound = {
        "device_action_f1_v2": classifier,
        "s20plus_g986n_d0_inventory": inventory,
        "s20plus_g986n_routine_d0": routine,
        "s22plus_boot_only_f1_transport": transport,
    }
    with _bound_imports(bound):
        bootstrap = _load_exact(SOURCES["bootstrap"], "n3u0_bootstrap_bound")
    if not (
        bootstrap.f1_core is classifier
        and bootstrap.base is inventory
        and bootstrap.routine is routine
        and bootstrap.transport is transport
        and transport.boot_verify is boot_verify
        and transport.raw_capture is raw_capture
    ):
        raise BackendError("bootstrap transitive source closure differs")
    return {
        "integration": integration,
        "bootstrap": bootstrap,
        "observer": _load_exact(SOURCES["observer"], "n3u0_observer_bound"),
        "owner": _load_exact(SOURCES["owner"], "n3u0_owner_bound"),
        "inventory": inventory,
        "routine": routine,
        "transport": transport,
        "boot_verify": boot_verify,
        "raw_capture": raw_capture,
        "classifier": classifier,
    }


def current_binding() -> dict[str, Any]:
    sources = load_sources()
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "target": dict(TARGET),
        "runner": self_receipt(),
        "integration_binding_sha256": INTEGRATION_BINDING_SHA256,
        "integration_status": sources["integration"].STATUS,
        "sources": source_receipts(),
        "fixed_operations": [
            "exact-rooted-android-preflight",
            "empty-download-baseline",
            "exact-source-adb-reboot-download",
            "exact-download-endpoint-observation",
            "candidate-or-resident-boot-only-odin",
            "bounded-n3u0-banner-observation",
            "exact-resident-rooted-health",
        ],
    }


def binding_sha256() -> str:
    return digest(current_binding())


def require_active() -> None:
    if BACKEND_ACTIVE is not True:
        raise BackendError("N3-U0 concrete backend is not active")


def _raw(stdout: bytes, stderr: bytes) -> dict[str, Any]:
    if len(stdout) + len(stderr) > MAX_RAW_BYTES:
        raise BackendError("backend raw output is oversized")
    return {
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "stdout_size": len(stdout),
        "stderr_size": len(stderr),
    }


def _require_root_receipt(value: Any, label: str) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or value.get("root_verified") is not True
        or type(value.get("attempts")) is not int
        or value["attempts"] < 1
        or not isinstance(value.get("output_sha256"), str)
        or HEX64_RE.fullmatch(value["output_sha256"]) is None
    ):
        raise BackendError(f"{label} is not exact")
    return value


def _public_endpoint(integration: Any, bootstrap: Any, value: Any) -> dict[str, str]:
    endpoint = bootstrap.validate_download_endpoint_record(value, "N3-U0 endpoint")
    return integration._endpoint(
        integration.load_journal(),
        {
            "path_sha256": endpoint["endpoint_sha256"],
            "identity_sha256": digest(endpoint["endpoint_identity"]),
            "topology_sha256": endpoint["topology_sha256"],
            "profile_sha256": digest(endpoint["usb"]),
        },
        "N3-U0 public endpoint",
    )


def _usb_node_from_devpath(devpath: str) -> str:
    if not isinstance(devpath, str) or not devpath.startswith("usb:"):
        raise BackendError("Android devpath is malformed")
    node = devpath[4:]
    if USB_NODE_RE.fullmatch(node) is None:
        raise BackendError("Android USB node is malformed")
    return node


def _observe_candidate_fixed(observer: Any, baseline: dict[str, Any], node: str) -> dict[str, Any]:
    require_active()
    observer.validate_baseline(baseline, node)
    deadline = time.monotonic() + observer.ARRIVAL_TIMEOUT_SEC
    candidate = None
    while time.monotonic() < deadline:
        try:
            candidate = observer.select_arrival(baseline, node)
            break
        except Exception as exc:
            if str(exc) not in {
                "N3-U0 candidate endpoint is absent",
                "N3-U0 candidate endpoint is pending",
            }:
                raise
        time.sleep(observer.POLL_INTERVAL_SEC)
    if candidate is None:
        raise BackendError("N3-U0 candidate arrival timed out")
    descriptor = observer._open_live(candidate)
    try:
        return observer.observe_selected(
            baseline,
            node,
            candidate,
            descriptor,
            usb_root=observer.USB_ROOT,
            tty_root=observer.TTY_ROOT,
        )
    finally:
        os.close(descriptor)


class FixedBackend:
    """No-input concrete primitive set. Not exposed while BACKEND_ACTIVE is false."""

    def __init__(self) -> None:
        sources = load_sources()
        self.integration = sources["integration"]
        self.bootstrap = sources["bootstrap"]
        self.observer = sources["observer"]
        self.owner = sources["owner"]
        self._command_impl = self.bootstrap.bounded_command
        self.command = self._captured_command
        self.adb = str(self.bootstrap.ADB)
        self.expected_usb_node: str | None = None
        self.candidate_baseline: dict[str, Any] | None = None
        self.last_full_receipt: dict[str, Any] | None = None
        self._capture_operation: str | None = None
        self._command_returns: list[dict[str, Any]] = []

    def begin_operation_capture(self, operation: str) -> None:
        require_active()
        if operation not in CAPTURE_OPERATIONS:
            raise BackendError("unknown evidence capture operation")
        if self._capture_operation is not None or self._command_returns:
            raise BackendError("another evidence capture is unresolved")
        self.last_full_receipt = None
        self._capture_operation = operation

    def consume_operation_capture(self, operation: str) -> dict[str, Any]:
        require_active()
        if operation != self._capture_operation or operation not in CAPTURE_OPERATIONS:
            raise BackendError("evidence capture operation differs")
        result = {
            "commands": list(self._command_returns),
            "full_receipt": self.last_full_receipt,
        }
        self._command_returns.clear()
        self._capture_operation = None
        self.last_full_receipt = None
        return result

    def _captured_command(
        self, argv: list[str], timeout: float, maximum: int
    ) -> tuple[int, bytes, bytes]:
        require_active()
        result = self._command_impl(argv, timeout, maximum)
        if self._capture_operation is not None:
            returncode, stdout, stderr = result
            if (
                not isinstance(argv, list)
                or any(not isinstance(item, str) for item in argv)
                or type(returncode) is not int
                or not isinstance(stdout, bytes)
                or not isinstance(stderr, bytes)
                or type(timeout) is not int
                or not 0 < timeout <= 900
                or type(maximum) is not int
                or not 0 < maximum <= MAX_RAW_BYTES
            ):
                raise BackendError("captured command return is malformed")
            self._command_returns.append(
                {
                    "argv": list(argv),
                    "timeout_seconds": timeout,
                    "output_limit": maximum,
                    "returncode": returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                }
            )
        return result

    @contextmanager
    def _capture_odin_stream(self):
        require_active()
        previous = self.bootstrap.streaming_command

        def capture_stream(
            argv: list[str], timeout: int, maximum: int
        ) -> tuple[int, bytes, bytes]:
            require_active()
            result = previous(argv, timeout, maximum)
            if self._capture_operation is not None:
                returncode, stdout, stderr = result
                if (
                    not isinstance(argv, list)
                    or any(not isinstance(item, str) for item in argv)
                    or type(timeout) is not int
                    or not 0 < timeout <= 900
                    or type(maximum) is not int
                    or not 0 < maximum <= MAX_RAW_BYTES
                    or type(returncode) is not int
                    or not isinstance(stdout, bytes)
                    or not isinstance(stderr, bytes)
                ):
                    raise BackendError("captured Odin return is malformed")
                self._command_returns.append(
                    {
                        "argv": list(argv),
                        "timeout_seconds": timeout,
                        "output_limit": maximum,
                        "returncode": returncode,
                        "stdout": stdout,
                        "stderr": stderr,
                    }
                )
            return result

        self.bootstrap.streaming_command = capture_stream
        try:
            yield
        finally:
            self.bootstrap.streaming_command = previous

    def preflight(self) -> dict[str, Any]:
        require_active()
        selected, _values, identity = self.bootstrap.android_health_once(
            self.command, self.adb
        )
        root = self.bootstrap.root_observation(
            self.command, self.adb, identity, timeout=90
        )
        _require_root_receipt(root, "resident root preflight")
        rc, stdout, stderr = self.command(
            [self.adb, "-s", selected["serial"], "get-devpath"], 10, 64 * 1024
        )
        if rc != 0 or stderr:
            raise BackendError("Android devpath read failed")
        try:
            devpath = stdout.decode("utf-8", "strict").strip()
        except UnicodeError as exc:
            raise BackendError("Android devpath is malformed") from exc
        if hashlib.sha256(devpath.encode()).hexdigest() != identity["topology_sha256"]:
            raise BackendError("Android devpath differs from health identity")
        self.expected_usb_node = _usb_node_from_devpath(devpath)
        baseline = self.bootstrap.download_baseline(self.command)
        return {
            "identity": identity,
            "empty_download_baseline_sha256": self.bootstrap.canonical_sha(baseline),
        }

    def download_baseline(self, phase: str) -> str:
        require_active()
        if phase != "physical":
            raise BackendError("unknown Download baseline phase")
        return self.bootstrap.canonical_sha(self.bootstrap.download_baseline(self.command))

    def reboot_download(
        self, phase: str, source_identity: dict[str, str]
    ) -> dict[str, Any]:
        require_active()
        if phase not in ("initial", "rollback"):
            raise BackendError("unknown Download reboot phase")
        selected, _values, current = self.bootstrap.android_health_once(
            self.command, self.adb
        )
        if current != source_identity:
            raise BackendError("Download reboot source identity differs")
        self.bootstrap.download_baseline(self.command)
        rc, stdout, stderr = self.command(
            [self.adb, "-s", selected["serial"], "reboot", "download"],
            20,
            64 * 1024,
        )
        outcome = "dispatched" if rc == 0 and not stderr else "uncertain"
        self.last_full_receipt = {
            "operation": f"{phase}-reboot-download",
            "returncode": rc,
            "source_identity": source_identity,
            "raw_receipt": _raw(stdout, stderr),
            "outcome": outcome,
        }
        return {"phase": phase, "outcome": outcome, "raw_receipt": _raw(stdout, stderr)}

    def observe_download(self, phase: str) -> dict[str, Any]:
        require_active()
        if phase not in ("initial", "candidate", "rollback", "physical"):
            raise BackendError("unknown Download observation phase")
        deadline = time.monotonic() + DOWNLOAD_TIMEOUT_SEC
        while True:
            devices, listing_sha256 = self.bootstrap.enumerate_download(self.command)
            if len(devices) == 1:
                break
            if len(devices) > 1:
                raise BackendError("Download endpoint is ambiguous")
            if time.monotonic() >= deadline:
                raise BackendError("Download endpoint arrival timed out")
            time.sleep(2)
        endpoint = self.bootstrap.identify_download(self.command)
        repeated, repeated_sha256 = self.bootstrap.enumerate_download(self.command)
        if repeated != devices or repeated_sha256 != listing_sha256:
            raise BackendError("Download listing changed during observation")
        if endpoint["device"] != devices[0]:
            raise BackendError("Download endpoint differs from listing")
        result = {
            "phase": phase,
            "endpoint": _public_endpoint(self.integration, self.bootstrap, endpoint),
            "arrival_listing_sha256": listing_sha256,
        }
        self.last_full_receipt = result
        return result

    def transfer_boot(self, kind: str, endpoint: dict[str, str]) -> dict[str, Any]:
        require_active()
        if kind == "candidate":
            path = self.owner.CANDIDATE_AP
            size = self.owner.CANDIDATE_AP_SIZE
            sha256 = self.owner.CANDIDATE_AP_SHA256
            if self.expected_usb_node is None:
                raise BackendError("candidate observer topology was not prepared")
        elif kind == "rollback":
            path = self.owner.ROLLBACK_AP
            size = self.owner.ROLLBACK_AP_SIZE
            sha256 = self.owner.ROLLBACK_AP_SHA256
        else:
            raise BackendError("unknown boot transfer kind")
        live = self.bootstrap.identify_download(self.command)
        if _public_endpoint(self.integration, self.bootstrap, live) != endpoint:
            raise BackendError("Odin endpoint differs from durable intent")
        if kind == "candidate":
            self.candidate_baseline = self.observer.capture_baseline(
                self.expected_usb_node
            )
            self.owner.audit_boot_only_ap(
                path,
                expected_size=size,
                expected_sha256=sha256,
                expected_member_size=self.owner.CANDIDATE_MEMBER_SIZE,
                expected_member_sha256=self.owner.CANDIDATE_MEMBER_SHA256,
                label="N3-U0 candidate AP",
            )
        else:
            self.owner.audit_boot_only_ap(
                path,
                expected_size=size,
                expected_sha256=sha256,
                expected_member_size=self.owner.ROLLBACK_MEMBER_SIZE,
                expected_member_sha256=self.owner.ROLLBACK_MEMBER_SHA256,
                label="N3-U0 resident rollback AP",
            )
        with self._capture_odin_stream():
            receipt, stdout, stderr = self.bootstrap.execute_odin_exact(
                path, size, sha256, kind, live
            )
        classification = self.bootstrap.persisted_transfer_classification(
            receipt, stdout, stderr
        )
        if classification == "odin_local_parse_failure":
            classification = "local_parse_failure"
        if classification not in {
            "odin_transfer_completed",
            "odin_device_session_failure_or_unknown",
            "local_parse_failure",
        }:
            raise BackendError("Odin classification is unknown")
        self.last_full_receipt = {
            "operation": f"{kind}-boot-transfer",
            "classification": classification,
            "receipt": receipt,
            "raw_receipt": _raw(stdout, stderr),
        }
        return {
            "kind": kind,
            "classification": classification,
            "raw_receipt": _raw(stdout, stderr),
        }

    def observe_candidate(self) -> dict[str, Any]:
        require_active()
        if self.expected_usb_node is None or self.candidate_baseline is None:
            raise BackendError("candidate observer baseline is absent")
        receipt = _observe_candidate_fixed(
            self.observer, self.candidate_baseline, self.expected_usb_node
        )
        if (
            not isinstance(receipt, dict)
            or set(receipt)
            != {
                "schema",
                "observer_schema",
                "baseline_sha256",
                "expected_topology_sha256",
                "endpoint_identity_sha256",
                "banner_sha256",
                "banner_size",
                "tty_number_stable",
                "exact",
                "accepted",
            }
            or receipt.get("schema") != self.observer.RECEIPT_SCHEMA
            or receipt.get("observer_schema") != self.observer.SCHEMA
            or receipt.get("baseline_sha256")
            != self.observer._digest(self.candidate_baseline)
            or receipt.get("expected_topology_sha256")
            != self.observer._hash_text(self.expected_usb_node)
            or not isinstance(receipt.get("endpoint_identity_sha256"), str)
            or HEX64_RE.fullmatch(receipt["endpoint_identity_sha256"]) is None
            or receipt.get("banner_sha256")
            != hashlib.sha256(self.observer.BANNER).hexdigest()
            or type(receipt.get("banner_size")) is not int
            or receipt["banner_size"] != len(self.observer.BANNER)
            or receipt.get("tty_number_stable") is not False
            or receipt.get("accepted") is not True
            or receipt.get("exact") is not True
        ):
            raise BackendError("N3-U0 banner receipt is not exact")
        android = self.bootstrap.wait_android(
            self.command, self.adb, self.bootstrap.ANDROID_TIMEOUT
        )
        if android is None:
            raise BackendError("candidate Android did not return after N3-U0 banner")
        _selected, values, identity = android
        self.last_full_receipt = {
            "usb_receipt": receipt,
            "android_identity": identity,
            "android_health_sha256": digest(
                {"target": TARGET, "values": values, "identity": identity}
            ),
        }
        return {"banner_accepted": True, "android_identity": identity}

    def physical_download_entry(self) -> None:
        require_active()
        raise BackendError("attended physical-entry bridge is not implemented")

    def final_resident_health(self) -> dict[str, Any]:
        require_active()
        android = self.bootstrap.wait_android(
            self.command, self.adb, self.bootstrap.ANDROID_TIMEOUT
        )
        if android is None:
            raise BackendError("resident Android did not return")
        _selected, values, identity = android
        root = self.bootstrap.root_observation(
            self.command, self.adb, identity, timeout=90
        )
        _require_root_receipt(root, "resident root health")
        health_sha256 = digest(
            {"target": TARGET, "values": values, "identity": identity}
        )
        self.last_full_receipt = {
            "operation": "resident-final-health",
            "identity": identity,
            "android_health_sha256": health_sha256,
            "root": root,
        }
        return {
            "identity": identity,
            "android_health_sha256": health_sha256,
            "root_output_sha256": root["output_sha256"],
            "root_attempts": root["attempts"],
            "exact_target_healthy": True,
            "root_verified": True,
        }


def render_plan() -> dict[str, Any]:
    binding = current_binding()
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "active": BACKEND_ACTIVE,
        "live_authority": False,
        "backend_exposed": False,
        "binding_sha256": digest(binding),
        "binding": binding,
        "cli": ["--render-plan"],
        "device_commands": [],
        "partition_transfers": [],
        "raw_evidence_durable": False,
        "physical_entry_bridge": False,
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

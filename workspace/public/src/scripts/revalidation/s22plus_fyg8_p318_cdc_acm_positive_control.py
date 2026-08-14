#!/usr/bin/env python3
"""Join the dummy_hcd and real Python CDC ACM positive-control seams.

The QEMU half proves that the exact 49-byte pre-bind banner survives the Linux
dummy_hcd/u_serial/cdc_acm path.  The PTY half executes the real Python
observer against an already queued 49-byte banner.  The two halves are joined
by the source-derived byte identity.  This is deliberately described as a
two-seam transitive control, not as the Python observer running inside QEMU.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import pty
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_p318_cdc_acm_positive_control_v1"
VERDICT = "PASS_P318_CDC_ACM_TWO_SEAM_POSITIVE_CONTROL_H0"
QEMU_VERDICT = "PASS_P260_E3_GENERIC_QEMU_HOST_ONLY"

DEFAULT_QEMU_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p260_qemu_final/result.json"
)
DEFAULT_QEMU_LOG = Path(
    "workspace/private/outputs/s22plus_fyg8_p260_qemu_final/qemu-console.log"
)
DEFAULT_RUNTIME = Path(
    "workspace/public/src/native-init/s22plus_fyg8_p260_e3_runtime.inc.c"
)
DEFAULT_HARNESS = Path(
    "workspace/public/src/native-init/s22plus_fyg8_p260_qemu_harness.c"
)
DEFAULT_OBSERVER = Path(
    "workspace/public/src/scripts/revalidation/"
    "device_action_cdc_acm_observer_v1.py"
)
DEFAULT_SELECTOR = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_cdc_acm_endpoint_transition.py"
)


class PositiveControlError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "AGENTS.md").is_file() and (parent / "GOAL.md").is_file():
            return parent
    raise PositiveControlError("repository root not found")


def _identity(stat_result: Any) -> tuple[int, int, int, int]:
    return (
        stat_result.st_dev,
        stat_result.st_ino,
        stat_result.st_size,
        stat_result.st_mtime_ns,
    )


def stable_read(path: Path, label: str, limit: int) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise PositiveControlError(f"{label} unavailable: {path}") from exc
    if path.is_symlink() or not path.is_file() or not 0 < before.st_size <= limit:
        raise PositiveControlError(f"{label} is indirect, empty, or outside bound")
    data = path.read_bytes()
    after = path.stat(follow_symlinks=False)
    if _identity(before) != _identity(after) or len(data) != before.st_size:
        raise PositiveControlError(f"{label} changed while reading")
    return data


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def load_json(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PositiveControlError(f"{label} is not JSON") from exc
    if not isinstance(value, dict):
        raise PositiveControlError(f"{label} is not an object")
    return value


def derive_banner(runtime_data: bytes, harness_data: bytes) -> tuple[bytes, str]:
    try:
        runtime = runtime_data.decode("utf-8", "strict")
        harness = harness_data.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise PositiveControlError("QEMU sources are not UTF-8") from exc
    prefixes = re.findall(
        r'static const char banner_prefix\[\] = "([^"]+)";', runtime
    )
    run_regions = re.findall(
        r"static const uint8_t k_run_id\[16\] = \{(?P<body>.*?)\};",
        harness,
        re.DOTALL,
    )
    if prefixes != ["S22PLUS-FYG8-E3:"] or len(run_regions) != 1:
        raise PositiveControlError("QEMU banner source authority drifted")
    octets = re.findall(r"0x([0-9a-fA-F]{2})", run_regions[0])
    if len(octets) != 16:
        raise PositiveControlError("QEMU run identity is not 16 bytes")
    run_id = bytes(int(value, 16) for value in octets)
    banner = prefixes[0].encode("ascii") + run_id.hex().encode("ascii") + b"\n"
    if len(banner) != 49:
        raise PositiveControlError("QEMU banner is not 49 bytes")
    serial = "S22E3" + run_id.hex()
    required = (
        'open(\n                "/dev/ttyACM0",',
        "used == sizeof(p260_banner) - 1U",
        "p260_bytes_equal(\n                observed, p260_banner",
        "write(output_fd, observed, used)",
        "p260_write_all(\n        tty_fd, p260_banner",
    )
    if any(harness.count(token) != 1 for token in required):
        raise PositiveControlError("QEMU observer/banner seam drifted")
    return banner, serial


def audit_qemu(
    *,
    result_data: bytes,
    log_data: bytes,
    runtime_data: bytes,
    harness_data: bytes,
) -> dict[str, Any]:
    result = load_json(result_data, "QEMU result")
    banner, serial = derive_banner(runtime_data, harness_data)
    validated = {
        "generic configfs mount and statfs",
        "generic ACM gadget construction",
        "ttyGS0 materialization and raw mode",
        "pre-bind banner queue",
        "dummy_hcd UDC bind and configured state",
        "exact banner arrival through ttyACM0",
    }
    try:
        scope = set(result["scope"]["validated"])
        build = result["build"]
    except (KeyError, TypeError) as exc:
        raise PositiveControlError("QEMU result shape differs") from exc
    if (
        result.get("schema") != "s22plus_fyg8_p260_generic_qemu_harness_v1"
        or result.get("verdict") != QEMU_VERDICT
        or scope != validated
        or result.get("qemu_output_sha256")
        != hashlib.sha256(log_data.decode("utf-8", "replace").encode("utf-8")).hexdigest()
        or build.get("runtime_sha256") != hashlib.sha256(runtime_data).hexdigest()
        or build.get("harness_sha256") != hashlib.sha256(harness_data).hexdigest()
    ):
        raise PositiveControlError("QEMU result authority differs")
    log = log_data.decode("utf-8", "strict")
    required = (
        "P260_QEMU stage=0x8c status=PASS name=pre-bind-banner",
        "P260_QEMU stage=0x8e status=PASS name=dummy-udc-bind",
        "P260_QEMU stage=0x8f status=PASS name=dummy-configured",
        "P260_QEMU result=PASS verdict=PASS_P260_E3_GENERIC_QEMU_HOST_ONLY banner_bytes=49",
    )
    if any(log.count(token) != 1 for token in required):
        raise PositiveControlError("QEMU console positive control differs")
    return {
        "result": receipt(result_data),
        "console": receipt(log_data),
        "runtime": receipt(runtime_data),
        "harness": receipt(harness_data),
        "banner_size": len(banner),
        "banner_sha256": hashlib.sha256(banner).hexdigest(),
        "serial_sha256": hashlib.sha256(serial.encode("ascii")).hexdigest(),
        "dummy_hcd_kernel_path_executed": True,
        "pre_bind_queue_executed": True,
        "exact_ttyacm_arrival_executed": True,
    }


def _load_observer(path: Path):
    spec = importlib.util.spec_from_file_location("p318_real_cdc_observer", path)
    if spec is None or spec.loader is None:
        raise PositiveControlError("real CDC ACM observer cannot be imported")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _HealthyFixtureGuard:
    def healthy(self, *, recheck: bool = False) -> bool:
        return True

    def matches_node(self, _node: Path) -> bool:
        return True


def run_real_observer_positive(
    *, observer_path: Path, banner: bytes, serial: str
) -> dict[str, Any]:
    observer = _load_observer(observer_path)
    temporary = tempfile.TemporaryDirectory()
    master = -1
    slave = -1
    try:
        root = Path(temporary.name)
        class_tty = root / "sys/class/tty"
        class_tty.mkdir(parents=True)
        drivers = root / "sys/drivers/cdc_acm"
        drivers.mkdir(parents=True)
        usb = (
            root
            / "sys/devices/pci0000:00/0000:00:14.0/usb3/3-1/3-1.3"
        )
        interface = usb / "3-1.3:1.0"
        tty_device = interface / "tty/ttyACM0"
        tty_device.mkdir(parents=True)
        (usb / "idVendor").write_text("04e8\n", encoding="ascii")
        (usb / "idProduct").write_text("6861\n", encoding="ascii")
        (usb / "serial").write_text(serial + "\n", encoding="ascii")
        (interface / "bInterfaceNumber").write_text("00\n", encoding="ascii")
        (interface / "driver").symlink_to(drivers)
        master, slave = pty.openpty()
        slave_path = Path(os.ttyname(slave))
        device_info = slave_path.stat()
        tty_class = class_tty / "ttyACM0"
        tty_class.mkdir()
        (tty_class / "device").symlink_to(tty_device)
        (tty_class / "dev").write_text(
            f"{os.major(device_info.st_rdev)}:{os.minor(device_info.st_rdev)}\n",
            encoding="ascii",
        )
        dev_root = root / "dev"
        dev_root.mkdir()
        (dev_root / "ttyACM0").symlink_to(slave_path)
        run_dir = root / "run"
        run_dir.mkdir()
        spec_value = {
            "kind": "exact_cdc_acm_banner_v1",
            "usb_vendor_id": "04e8",
            "usb_product_id": "6861",
            "usb_serial": serial,
            "usb_driver": "cdc_acm",
            "usb_interface_number": "00",
            "banner_hex": banner.hex(),
        }
        baseline = {
            "schema": observer.BASELINE_SCHEMA,
            "spec_sha256": observer.digest(spec_value),
            "topology_sha256": hashlib.sha256(b"3-1.3").hexdigest(),
            "identity_sha256": [],
            "exact_candidate_absent": True,
        }
        baseline_receipt = observer.persist_json(
            run_dir / "candidate-observer-baseline.json", baseline
        )
        guard_value = {
            "schema": observer.GUARD_SCHEMA,
            "status": "armed",
            "spec_sha256": observer.digest(spec_value),
            "topology_sha256": hashlib.sha256(b"3-1.3").hexdigest(),
            "rule_sha256": hashlib.sha256(
                observer._guard_rule(spec_value, "usb:3-1.3")
            ).hexdigest(),
            "instance_sha256": "5" * 64,
            "output_sha256": "4" * 64,
            "child_alive": True,
        }
        guard_receipt = observer.persist_json(
            run_dir / "candidate-observer-guard.json", guard_value
        )
        binding = {
            "approval_binding_sha256": "a" * 64,
            "bundle_sha256": "b" * 64,
            "manifest_id": "p318-positive-control",
            "candidate_ap_sha256": "c" * 64,
        }
        session = observer.ObserverSession(
            spec_value,
            "usb:3-1.3",
            run_dir,
            binding,
            baseline,
            baseline_receipt,
            _HealthyFixtureGuard(),
            guard_receipt,
            class_tty,
            dev_root,
        )
        os.write(master, banner)
        value = session.observe(
            timeout_sec=2,
            download_departure={
                "download_endpoint_absent": True,
                "absence_timed_out": False,
                "sequence": 1,
            },
        )
        reopened = observer.validate_receipt(
            run_dir / "candidate-observer.json",
            spec=spec_value,
            binding=binding,
            topology="usb:3-1.3",
        )
        raw = (run_dir / "candidate-observer.raw").read_bytes()
        if (
            value.get("classification") != "accepted"
            or reopened.get("accepted") is not True
            or raw != banner
        ):
            raise PositiveControlError("real CDC ACM observer positive control failed")
        return {
            "observer_source": receipt(observer_path.read_bytes()),
            "classification": "accepted",
            "accepted": True,
            "banner_queued_before_observer_open": True,
            "raw_size": len(raw),
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "real_python_selector_executed": True,
            "real_python_open_raw_read_and_receipt_executed": True,
            "kernel_transport": "pty",
            "modemmanager_guard": "fixture_healthy_not_root_udev_guard",
        }
    finally:
        if master >= 0:
            os.close(master)
        if slave >= 0:
            os.close(slave)
        temporary.cleanup()


def build_contract(
    *,
    qemu_result_data: bytes,
    qemu_log_data: bytes,
    runtime_data: bytes,
    harness_data: bytes,
    observer_path: Path,
    selector_data: bytes,
    extractor_data: bytes,
) -> dict[str, Any]:
    qemu = audit_qemu(
        result_data=qemu_result_data,
        log_data=qemu_log_data,
        runtime_data=runtime_data,
        harness_data=harness_data,
    )
    banner, serial = derive_banner(runtime_data, harness_data)
    observed = run_real_observer_positive(
        observer_path=observer_path, banner=banner, serial=serial
    )
    if (
        qemu["banner_sha256"] != observed["raw_sha256"]
        or qemu["banner_size"] != observed["raw_size"]
    ):
        raise PositiveControlError("positive-control byte join differs")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "inputs": {
            "extractor": receipt(extractor_data),
            "selector": receipt(selector_data),
        },
        "qemu_dummy_hcd": qemu,
        "real_observer": observed,
        "transitive_join": {
            "banner_size": len(banner),
            "banner_sha256": hashlib.sha256(banner).hexdigest(),
            "same_bytes_at_both_seams": True,
            "dummy_hcd_to_real_python_end_to_end": False,
            "claim": (
                "dummy_hcd delivers the exact prequeued bytes and the real "
                "Python observer accepts those exact bytes when prequeued"
            ),
        },
        "scope": {
            "device_actions": 0,
            "actual_s22_usb": False,
            "actual_root_udev_guard": False,
            "live_selector_wired": False,
            "full_dummy_hcd_python_pipeline_claimed": False,
        },
    }


def encode_contract(value: dict[str, Any]) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=repo_root())
    parser.add_argument("--qemu-result", type=Path, default=DEFAULT_QEMU_RESULT)
    parser.add_argument("--qemu-log", type=Path, default=DEFAULT_QEMU_LOG)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--harness", type=Path, default=DEFAULT_HARNESS)
    parser.add_argument("--observer", type=Path, default=DEFAULT_OBSERVER)
    parser.add_argument("--selector", type=Path, default=DEFAULT_SELECTOR)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.repo.resolve()

    def resolve(path: Path) -> Path:
        return path if path.is_absolute() else root / path

    extractor_path = Path(__file__).resolve()
    observer_path = resolve(args.observer)
    value = build_contract(
        qemu_result_data=stable_read(resolve(args.qemu_result), "QEMU result", 2**20),
        qemu_log_data=stable_read(resolve(args.qemu_log), "QEMU log", 2**24),
        runtime_data=stable_read(resolve(args.runtime), "P2.60 runtime", 2**20),
        harness_data=stable_read(resolve(args.harness), "P2.60 QEMU harness", 2**20),
        observer_path=observer_path,
        selector_data=stable_read(resolve(args.selector), "P3.18 selector", 2**20),
        extractor_data=stable_read(extractor_path, "positive-control audit", 2**20),
    )
    payload = encode_contract(value)
    if args.output is None:
        print(payload.decode(), end="")
    else:
        output = resolve(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

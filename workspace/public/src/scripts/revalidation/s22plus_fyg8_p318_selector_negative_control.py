#!/usr/bin/env python3
"""Execute the P3.18 endpoint and DWC3 exact-selector negative controls."""

from __future__ import annotations

import argparse
import errno
import hashlib
import importlib.util
import json
import os
import pty
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_p318_selector_negative_control_v1"
VERDICT = "PASS_P318_SELECTOR_NEGATIVE_CONTROL_H0"
DEFAULT_OBSERVER = Path(
    "workspace/public/src/scripts/revalidation/"
    "device_action_cdc_acm_observer_v1.py"
)
DEFAULT_LATCH = Path(
    "workspace/public/src/kernel-modules/s22plus_dwc3_event_latch/"
    "s22plus_dwc3_event_latch.c"
)
APPROVED_TOPOLOGY = "usb:2-1.3"
SYNTHETIC_SERIAL = "S22E3" + "1" * 32
FOREIGN_SERIAL = "S22E3" + "2" * 32
SYNTHETIC_BANNER = b"S22PLUS-FYG8-E3:" + b"1" * 32 + b"\n"


class NegativeControlError(RuntimeError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "AGENTS.md").is_file() and (parent / "GOAL.md").is_file():
            return parent
    raise NegativeControlError("repository root not found")


def _identity(stat_result: Any) -> tuple[int, int, int, int]:
    return (
        stat_result.st_dev,
        stat_result.st_ino,
        stat_result.st_size,
        stat_result.st_mtime_ns,
    )


def stable_read(path: Path, label: str, limit: int = 2**20) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise NegativeControlError(f"{label} unavailable: {path}") from exc
    if path.is_symlink() or not path.is_file() or not 0 < before.st_size <= limit:
        raise NegativeControlError(f"{label} is indirect, empty, or outside bound")
    data = path.read_bytes()
    after = path.stat(follow_symlinks=False)
    if _identity(before) != _identity(after) or len(data) != before.st_size:
        raise NegativeControlError(f"{label} changed while reading")
    return data


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _load_observer(path: Path):
    name = "p318_selector_negative_real_observer"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise NegativeControlError("real CDC ACM observer cannot be imported")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _HealthyFixtureGuard:
    def healthy(self, *, recheck: bool = False) -> bool:
        return True

    def matches_node(self, _node: Path) -> bool:
        return True


class _OneScanClock:
    """Run one real selector scan without spending a wall-clock timeout."""

    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, _seconds: float) -> None:
        self.now = 1.0


class _SelectorFixture:
    def __init__(self, observer: Any, case_name: str) -> None:
        self.observer = observer
        self.temporary = tempfile.TemporaryDirectory(prefix=f"p318-{case_name}-")
        self.root = Path(self.temporary.name)
        self.class_tty = self.root / "sys/class/tty"
        self.class_tty.mkdir(parents=True)
        self.drivers = self.root / "sys/drivers/cdc_acm"
        self.drivers.mkdir(parents=True)
        self.dev_root = self.root / "dev"
        self.dev_root.mkdir()
        self.run_dir = self.root / "run"
        self.run_dir.mkdir()
        self.descriptors: list[int] = []
        self.device_paths: set[Path] = set()

    def close(self) -> None:
        for descriptor in self.descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass
        self.temporary.cleanup()

    @staticmethod
    def _write_exact(path: Path, value: str) -> None:
        if path.exists():
            if path.read_text(encoding="ascii") != value:
                raise NegativeControlError("synthetic USB node identity conflicts")
            return
        path.write_text(value, encoding="ascii")

    def add_endpoint(
        self,
        *,
        tty_name: str,
        controller: str,
        topology: str,
        product: str = "6861",
        serial: str = SYNTHETIC_SERIAL,
    ) -> None:
        bus = topology.split("-", 1)[0]
        parent = topology.rsplit(".", 1)[0]
        usb = (
            self.root
            / "sys/devices/pci0000:00"
            / controller
            / f"usb{bus}"
            / parent
            / topology
        )
        interface = usb / f"{topology}:1.0"
        tty_device = interface / "tty" / tty_name
        tty_device.mkdir(parents=True, exist_ok=True)
        self._write_exact(usb / "idVendor", "04e8\n")
        self._write_exact(usb / "idProduct", product + "\n")
        self._write_exact(usb / "serial", serial + "\n")
        self._write_exact(interface / "bInterfaceNumber", "00\n")
        driver_link = interface / "driver"
        if not driver_link.exists():
            driver_link.symlink_to(self.drivers)

        master, slave = pty.openpty()
        self.descriptors.extend((master, slave))
        slave_path = Path(os.ttyname(slave))
        device_info = slave_path.stat()
        tty_class = self.class_tty / tty_name
        tty_class.mkdir()
        (tty_class / "device").symlink_to(tty_device)
        (tty_class / "dev").write_text(
            f"{os.major(device_info.st_rdev)}:{os.minor(device_info.st_rdev)}\n",
            encoding="ascii",
        )
        device_path = self.dev_root / tty_name
        device_path.symlink_to(slave_path)
        self.device_paths.add(device_path)

    def session(self) -> Any:
        spec_value = {
            "kind": "exact_cdc_acm_banner_v1",
            "usb_vendor_id": "04e8",
            "usb_product_id": "6861",
            "usb_serial": SYNTHETIC_SERIAL,
            "usb_driver": "cdc_acm",
            "usb_interface_number": "00",
            "banner_hex": SYNTHETIC_BANNER.hex(),
        }
        topology_sha256 = hashlib.sha256(b"2-1.3").hexdigest()
        baseline = {
            "schema": self.observer.BASELINE_SCHEMA,
            "spec_sha256": self.observer.digest(spec_value),
            "topology_sha256": topology_sha256,
            "identity_sha256": [],
            "exact_candidate_absent": True,
        }
        baseline_receipt = self.observer.persist_json(
            self.run_dir / "candidate-observer-baseline.json", baseline
        )
        guard_value = {
            "schema": self.observer.GUARD_SCHEMA,
            "status": "armed",
            "spec_sha256": self.observer.digest(spec_value),
            "topology_sha256": topology_sha256,
            "rule_sha256": hashlib.sha256(
                self.observer._guard_rule(spec_value, APPROVED_TOPOLOGY)
            ).hexdigest(),
            "instance_sha256": "5" * 64,
            "output_sha256": "4" * 64,
            "child_alive": True,
        }
        guard_receipt = self.observer.persist_json(
            self.run_dir / "candidate-observer-guard.json", guard_value
        )
        binding = {
            "approval_binding_sha256": "a" * 64,
            "bundle_sha256": "b" * 64,
            "manifest_id": "p318-selector-negative-control",
            "candidate_ap_sha256": "c" * 64,
        }
        return self.observer.ObserverSession(
            spec_value,
            APPROVED_TOPOLOGY,
            self.run_dir,
            binding,
            baseline,
            baseline_receipt,
            _HealthyFixtureGuard(),
            guard_receipt,
            self.class_tty,
            self.dev_root,
        )


def _run_selector_case(
    observer: Any,
    *,
    case_name: str,
    endpoints: tuple[dict[str, str], ...],
    expected_classification: str,
) -> dict[str, Any]:
    fixture = _SelectorFixture(observer, case_name)
    try:
        for endpoint in endpoints:
            fixture.add_endpoint(**endpoint)
        session = fixture.session()
        real_open = observer.os.open
        real_time = observer.time
        open_attempts: list[str] = []

        def open_spy(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
            candidate = Path(os.fspath(path))
            if candidate in fixture.device_paths:
                open_attempts.append(candidate.name)
                raise OSError(errno.EPERM, "negative-control TTY open blocked")
            return real_open(path, flags, *args, **kwargs)

        observer.os.open = open_spy
        observer.time = _OneScanClock()
        try:
            value = session.observe(
                timeout_sec=1,
                download_departure={
                    "download_endpoint_absent": True,
                    "absence_timed_out": False,
                    "sequence": 1,
                },
            )
        finally:
            observer.os.open = real_open
            observer.time = real_time

        reopened = observer.validate_receipt(
            fixture.run_dir / "candidate-observer.json",
            spec=session.spec,
            binding=session.binding,
            topology=APPROVED_TOPOLOGY,
        )
        raw = (fixture.run_dir / "candidate-observer.raw").read_bytes()
        if (
            value.get("classification") != expected_classification
            or reopened.get("classification") != expected_classification
            or value.get("accepted") is not False
            or value.get("endpoint_identity_sha256") is not None
            or raw != b""
            or open_attempts
        ):
            raise NegativeControlError(
                f"real selector negative case failed: {case_name}"
            )
        return {
            "case": case_name,
            "classification": expected_classification,
            "endpoint_count": len(endpoints),
            "accepted": False,
            "endpoint_identity_retained": False,
            "tty_open_attempts": 0,
            "raw_size": 0,
            "raw_sha256": hashlib.sha256(b"").hexdigest(),
            "real_observer_session_observe_executed": True,
            "receipt_reopened": True,
        }
    finally:
        fixture.close()


def run_real_selector_negative_controls(observer_data: bytes) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p318-selector-source-") as temporary:
        observer_path = Path(temporary) / "device_action_cdc_acm_observer_v1.py"
        observer_path.write_bytes(observer_data)
        observer = _load_observer(observer_path)
        cases = [
            _run_selector_case(
                observer,
                case_name="same_suffix_other_controller",
                endpoints=(
                    {
                        "tty_name": "ttyACM0",
                        "controller": "0000:00:14.0",
                        "topology": "3-1.3",
                    },
                ),
                expected_classification="endpoint-timeout",
            ),
            _run_selector_case(
                observer,
                case_name="different_samsung_serial",
                endpoints=(
                    {
                        "tty_name": "ttyACM0",
                        "controller": "0000:00:0d.0",
                        "topology": "2-1.3",
                        "serial": FOREIGN_SERIAL,
                    },
                ),
                expected_classification="identity-mismatch",
            ),
            _run_selector_case(
                observer,
                case_name="multiple_exact_candidates",
                endpoints=(
                    {
                        "tty_name": "ttyACM0",
                        "controller": "0000:00:0d.0",
                        "topology": "2-1.3",
                    },
                    {
                        "tty_name": "ttyACM1",
                        "controller": "0000:00:0d.0",
                        "topology": "2-1.3",
                    },
                ),
                expected_classification="endpoint-ambiguous",
            ),
        ]
    if len(cases) != 3 or sum(row["tty_open_attempts"] for row in cases) != 0:
        raise NegativeControlError("selector negative-control accounting differs")
    return {
        "observer_source": receipt(observer_data),
        "approved_topology": "2-1.3",
        "cases": cases,
        "case_count": 3,
        "tty_open_attempts_total": 0,
        "exact_topology_not_suffix_matching": True,
        "foreign_serial_not_selected": True,
        "multiple_exact_candidates_fail_ambiguous": True,
    }


def _extract_function(source: str, signature: str) -> str:
    if source.count(signature) != 1:
        raise NegativeControlError(f"latch helper signature differs: {signature}")
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 0
    for offset in range(opening, len(source)):
        character = source[offset]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source[start : offset + 1]
    raise NegativeControlError("latch helper body is incomplete")


def run_actual_udc_filter_negative_control(latch_data: bytes) -> dict[str, Any]:
    try:
        source = latch_data.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise NegativeControlError("latch source is not UTF-8") from exc
    targets = re.findall(
        r'^#define S22PLUS_DWC3_TARGET_NAME "([^\"]+)"$', source, re.MULTILINE
    )
    if targets != ["a600000.dwc3"]:
        raise NegativeControlError("latch target name authority differs")
    function = _extract_function(
        source, "static bool s22plus_dwc3_exact_target(const struct dwc3 *dwc)"
    )
    translation_unit = f"""
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

struct device {{ const char *name; }};
struct dwc3 {{ struct device *dev; }};
static const char *dev_name(const struct device *dev) {{ return dev->name; }}
#define S22PLUS_DWC3_TARGET_NAME "{targets[0]}"

{function}

static int reject_name(const char *name)
{{
    struct device device = {{ name }};
    struct dwc3 dwc = {{ &device }};
    return s22plus_dwc3_exact_target(&dwc) ? 1 : 0;
}}

int main(void)
{{
    struct device exact_device = {{ "a600000.dwc3" }};
    struct dwc3 exact = {{ &exact_device }};
    struct dwc3 missing_device = {{ NULL }};

    if (!s22plus_dwc3_exact_target(&exact)) return 10;
    if (s22plus_dwc3_exact_target(NULL)) return 11;
    if (s22plus_dwc3_exact_target(&missing_device)) return 12;
    if (reject_name("a600000.dwc30")) return 13;
    if (reject_name("xa600000.dwc3")) return 14;
    if (reject_name("other.dwc3")) return 15;
    if (reject_name("A600000.dwc3")) return 16;
    puts("{{\\\"negative\\\":6,\\\"positive\\\":1,\\\"verdict\\\":\\\"PASS\\\"}}");
    return 0;
}}
"""
    compiler = shutil.which("cc")
    if compiler is None:
        raise NegativeControlError("host C compiler is unavailable")
    with tempfile.TemporaryDirectory(prefix="p318-udc-filter-") as temporary:
        source_path = Path(temporary) / "udc_filter_fixture.c"
        executable = Path(temporary) / "udc_filter_fixture"
        source_path.write_text(translation_unit, encoding="utf-8")
        compiled = subprocess.run(
            [
                compiler,
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(source_path),
                "-o",
                str(executable),
            ],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        if compiled.returncode != 0 or compiled.stdout:
            raise NegativeControlError("materialized UDC filter did not compile")
        executed = subprocess.run(
            [str(executable)],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    expected = b'{"negative":6,"positive":1,"verdict":"PASS"}\n'
    if executed.returncode != 0 or executed.stdout != expected or executed.stderr:
        raise NegativeControlError("materialized UDC filter negative control failed")
    return {
        "latch_source": receipt(latch_data),
        "target_name": targets[0],
        "actual_materialized_helper_executed": True,
        "positive_count": 1,
        "negative_count": 6,
        "null_dwc_rejected": True,
        "null_device_rejected": True,
        "prefix_suffix_case_near_misses_rejected": True,
    }


def build_contract(
    *, observer_data: bytes, latch_data: bytes, extractor_data: bytes
) -> dict[str, Any]:
    selector = run_real_selector_negative_controls(observer_data)
    udc_filter = run_actual_udc_filter_negative_control(latch_data)
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "inputs": {"extractor": receipt(extractor_data)},
        "real_cdc_acm_selector": selector,
        "actual_latch_udc_filter": udc_filter,
        "scope": {
            "device_actions": 0,
            "actual_s22_usb": False,
            "candidate_bytes_changed": False,
            "observer_bytes_changed": False,
            "live_selector_wired": False,
            "h0_negative_qualification_only": True,
        },
    }


def encode_contract(value: dict[str, Any]) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=repo_root())
    parser.add_argument("--observer", type=Path, default=DEFAULT_OBSERVER)
    parser.add_argument("--latch", type=Path, default=DEFAULT_LATCH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.repo.resolve()

    def resolve(path: Path) -> Path:
        return path if path.is_absolute() else root / path

    extractor_path = Path(__file__).resolve()
    value = build_contract(
        observer_data=stable_read(resolve(args.observer), "real CDC ACM observer"),
        latch_data=stable_read(resolve(args.latch), "DWC3 latch source"),
        extractor_data=stable_read(extractor_path, "selector negative-control audit"),
    )
    payload = encode_contract(value)
    if args.output is None:
        print(payload.decode("utf-8"), end="")
    else:
        output = resolve(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

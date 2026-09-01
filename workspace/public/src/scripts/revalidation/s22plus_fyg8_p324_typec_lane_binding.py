#!/usr/bin/env python3
"""Bind the one P3.24 USB speed-lane transition on this host.

The S22+ is prepared as a SuperSpeed Android device at ``usb:2-1.3`` but the
native candidate exposes a high-speed CDC-ACM gadget at ``usb:3-1.3``.  Linux
publishes both root ports below the same Type-C connector.  This module proves
that exact connector, controller, dual-hub and downstream-port relationship;
it does not infer a generic companion path and it never opens a USB endpoint.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_p324_typec_lane_binding_v1"
CONTRACT_ID = "s22plus-fyg8-p324-typec-port0-lane-pair-v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"

SOURCE_TOPOLOGY = "usb:2-1.3"
CANDIDATE_TOPOLOGY = "usb:3-1.3"
TYPEC_PORT = "port0"
SOURCE_LINK = "usb2-port1"
CANDIDATE_LINK = "usb3-port1"
SOURCE_CONTROLLER = "0000:00:0d.0"
CANDIDATE_CONTROLLER = "0000:00:14.0"
PORT_LOCATION = "0x80000101"

SOURCE_HUB = {
    "vendor": "2109",
    "product": "0822",
    "device_class": "09",
    "device_protocol": "03",
}
CANDIDATE_HUB = {
    "vendor": "2109",
    "product": "2822",
    "device_class": "09",
    "device_protocol": "02",
}

DIGEST_RE = re.compile(r"[0-9a-f]{64}")
TOPOLOGY_RE = re.compile(r"usb:(?P<bus>[0-9]+)-(?P<root>[0-9]+)\.(?P<tail>[0-9]+(?:\.[0-9]+)*)")


class LaneBindingError(ValueError):
    """The exact host connector/lane relationship is unavailable."""


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def binding_digest(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")
    return _digest(payload)


def _read_text(path: Path, label: str, maximum: int = 256) -> str:
    try:
        before = path.lstat()
        payload = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise LaneBindingError(f"{label} is unavailable") from exc
    identity = lambda item: (  # noqa: E731
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_size,
        item.st_mtime_ns,
    )
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_ISLNK(before.st_mode)
        or identity(before) != identity(after)
        or not 0 < len(payload) <= maximum
    ):
        raise LaneBindingError(f"{label} is indirect, unstable, or oversized")
    try:
        value = payload.decode("ascii", "strict").strip()
    except UnicodeError as exc:
        raise LaneBindingError(f"{label} is not ASCII") from exc
    if not value or "\x00" in value:
        raise LaneBindingError(f"{label} is empty")
    return value


def _resolved_link(path: Path, expected: Path, label: str) -> Path:
    try:
        before = path.lstat()
        resolved = path.resolve(strict=True)
        target_before = resolved.lstat()
        expected_resolved = expected.resolve(strict=True)
        target_after = resolved.lstat()
        after = path.lstat()
    except OSError as exc:
        raise LaneBindingError(f"{label} is unavailable") from exc
    identity = lambda item: (  # noqa: E731
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_size,
        item.st_mtime_ns,
    )
    if (
        not stat.S_ISLNK(before.st_mode)
        or identity(before) != identity(after)
        or identity(target_before) != identity(target_after)
        or resolved != expected_resolved
        or not resolved.is_dir()
    ):
        raise LaneBindingError(f"{label} target differs")
    return resolved


def _hub(
    usb_root: Path,
    topology: str,
    expected: dict[str, str],
    label: str,
) -> tuple[dict[str, Any], str]:
    node = usb_root / topology.removeprefix("usb:")
    values = {
        "vendor": _read_text(node / "idVendor", f"{label} hub vendor"),
        "product": _read_text(node / "idProduct", f"{label} hub product"),
        "device_class": _read_text(node / "bDeviceClass", f"{label} hub class"),
        "device_protocol": _read_text(
            node / "bDeviceProtocol", f"{label} hub protocol"
        ),
    }
    if values != expected:
        raise LaneBindingError(f"{label} hub identity differs")
    bus, root = topology.removeprefix("usb:").split("-", 1)
    root_port = root.split(".", 1)[0]
    devpath = _read_text(node / "devpath", f"{label} hub devpath")
    busnum = _read_text(node / "busnum", f"{label} hub bus")
    serial = _read_text(node / "serial", f"{label} hub serial")
    speed = _read_text(node / "speed", f"{label} hub speed")
    manufacturer = _read_text(
        node / "manufacturer", f"{label} hub manufacturer"
    )
    if devpath != root_port or busnum != bus:
        raise LaneBindingError(f"{label} hub placement differs")
    return (
        values
        | {
            "bus": int(bus),
            "root_port": int(root_port),
            "devpath": devpath,
            "speed": speed,
            "serial_sha256": _digest(serial.encode("ascii")),
            "manufacturer_sha256": _digest(manufacturer.encode("ascii")),
        },
        serial,
    )


def capture_binding(
    source_topology: str,
    *,
    usb_root: Path = Path("/sys/bus/usb/devices"),
    typec_root: Path = Path("/sys/class/typec"),
) -> dict[str, Any]:
    """Capture the exact P3.24 connector pair without touching the device."""
    if source_topology != SOURCE_TOPOLOGY:
        raise LaneBindingError("P324 source topology differs")
    source_match = TOPOLOGY_RE.fullmatch(SOURCE_TOPOLOGY)
    candidate_match = TOPOLOGY_RE.fullmatch(CANDIDATE_TOPOLOGY)
    assert source_match is not None and candidate_match is not None
    if (
        source_match.group("root") != candidate_match.group("root")
        or source_match.group("tail") != candidate_match.group("tail")
    ):
        raise LaneBindingError("P324 downstream port chain differs")

    typec_port = typec_root / TYPEC_PORT
    try:
        typec_info = typec_port.lstat()
        typec_resolved = typec_port.resolve(strict=True)
        typec_after = typec_port.lstat()
    except OSError as exc:
        raise LaneBindingError("P324 Type-C connector is unavailable") from exc
    if (
        not stat.S_ISLNK(typec_info.st_mode)
        or (
            typec_info.st_dev,
            typec_info.st_ino,
            typec_info.st_mode,
            typec_info.st_size,
            typec_info.st_mtime_ns,
        )
        != (
            typec_after.st_dev,
            typec_after.st_ino,
            typec_after.st_mode,
            typec_after.st_size,
            typec_after.st_mtime_ns,
        )
        or not typec_resolved.is_dir()
    ):
        raise LaneBindingError("P324 Type-C connector is indirect or invalid")

    try:
        source_bus = (usb_root / "usb2").resolve(strict=True)
        candidate_bus = (usb_root / "usb3").resolve(strict=True)
    except OSError as exc:
        raise LaneBindingError("P324 USB root lanes are unavailable") from exc
    source_lane = _resolved_link(
        typec_port / SOURCE_LINK,
        source_bus / "2-0:1.0" / SOURCE_LINK,
        "P324 source lane",
    )
    candidate_lane = _resolved_link(
        typec_port / CANDIDATE_LINK,
        candidate_bus / "3-0:1.0" / CANDIDATE_LINK,
        "P324 candidate lane",
    )
    if SOURCE_CONTROLLER not in source_lane.parts:
        raise LaneBindingError("P324 source controller differs")
    if CANDIDATE_CONTROLLER not in candidate_lane.parts:
        raise LaneBindingError("P324 candidate controller differs")
    source_location = _read_text(
        typec_port / SOURCE_LINK / "location", "P324 source port location"
    )
    candidate_location = _read_text(
        typec_port / CANDIDATE_LINK / "location", "P324 candidate port location"
    )
    source_connect = _read_text(
        typec_port / SOURCE_LINK / "connect_type", "P324 source connect type"
    )
    candidate_connect = _read_text(
        typec_port / CANDIDATE_LINK / "connect_type",
        "P324 candidate connect type",
    )
    if (
        source_location != PORT_LOCATION
        or candidate_location != PORT_LOCATION
        or source_connect != "hotplug"
        or candidate_connect != "hotplug"
    ):
        raise LaneBindingError("P324 Type-C port relationship differs")

    source_hub, source_serial = _hub(
        usb_root, "usb:2-1", SOURCE_HUB, "P324 source"
    )
    candidate_hub, candidate_serial = _hub(
        usb_root, "usb:3-1", CANDIDATE_HUB, "P324 candidate"
    )
    if (
        source_serial != candidate_serial
        or source_hub["manufacturer_sha256"]
        != candidate_hub["manufacturer_sha256"]
        or source_hub["speed"] not in {"5000", "10000", "20000"}
        or candidate_hub["speed"] != "480"
    ):
        raise LaneBindingError("P324 companion hub relationship differs")

    value = {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "source_topology": SOURCE_TOPOLOGY,
        "candidate_topology": CANDIDATE_TOPOLOGY,
        "typec_port": TYPEC_PORT,
        "typec_port_sha256": _digest(str(typec_resolved).encode("utf-8")),
        "source_lane": {
            "link": SOURCE_LINK,
            "controller": SOURCE_CONTROLLER,
            "location": source_location,
            "resolved_sha256": _digest(str(source_lane).encode("utf-8")),
        },
        "candidate_lane": {
            "link": CANDIDATE_LINK,
            "controller": CANDIDATE_CONTROLLER,
            "location": candidate_location,
            "resolved_sha256": _digest(str(candidate_lane).encode("utf-8")),
        },
        "source_hub": source_hub,
        "candidate_hub": candidate_hub,
        "downstream_port_chain": source_match.group("tail"),
        "same_typec_connector": True,
        "same_location": True,
        "companion_hub_identity": True,
        "selector_topology_count": 1,
        "opens_candidate_acm": False,
        "device_commands": False,
    }
    value["binding_sha256"] = binding_digest(value)
    return value


def validate_binding(value: Any, *, source_topology: str) -> dict[str, Any]:
    shape = capture_shape(value) if isinstance(value, dict) else {}
    if not shape or value != shape:
        raise LaneBindingError("P324 Type-C binding shape differs")
    try:
        expected_binding_sha256 = binding_digest(
            {key: item for key, item in value.items() if key != "binding_sha256"}
        )
    except (TypeError, ValueError, UnicodeError) as exc:
        raise LaneBindingError("P324 Type-C binding is not canonical") from exc
    if (
        source_topology != SOURCE_TOPOLOGY
        or value["schema"] != SCHEMA
        or value["contract_id"] != CONTRACT_ID
        or value["binding_sha256"] != expected_binding_sha256
        or value["target"] != TARGET
        or value["source_topology"] != SOURCE_TOPOLOGY
        or value["candidate_topology"] != CANDIDATE_TOPOLOGY
        or value["typec_port"] != TYPEC_PORT
        or value["source_lane"]["link"] != SOURCE_LINK
        or value["source_lane"]["controller"] != SOURCE_CONTROLLER
        or value["candidate_lane"]["link"] != CANDIDATE_LINK
        or value["candidate_lane"]["controller"] != CANDIDATE_CONTROLLER
        or value["source_lane"]["location"] != PORT_LOCATION
        or value["candidate_lane"]["location"] != PORT_LOCATION
        or any(
            not isinstance(value["source_hub"][key], str)
            for key in (
                "vendor", "product", "device_class", "device_protocol",
                "devpath", "speed", "serial_sha256", "manufacturer_sha256",
            )
        )
        or any(
            not isinstance(value["candidate_hub"][key], str)
            for key in (
                "vendor", "product", "device_class", "device_protocol",
                "devpath", "speed", "serial_sha256", "manufacturer_sha256",
            )
        )
        or value["source_hub"] | SOURCE_HUB != value["source_hub"]
        or value["candidate_hub"] | CANDIDATE_HUB != value["candidate_hub"]
        or type(value["source_hub"]["bus"]) is not int
        or value["source_hub"]["bus"] != 2
        or type(value["candidate_hub"]["bus"]) is not int
        or value["candidate_hub"]["bus"] != 3
        or type(value["source_hub"]["root_port"]) is not int
        or value["source_hub"]["root_port"] != 1
        or type(value["candidate_hub"]["root_port"]) is not int
        or value["candidate_hub"]["root_port"] != 1
        or value["source_hub"]["devpath"] != "1"
        or value["candidate_hub"]["devpath"] != "1"
        or value["source_hub"]["speed"] not in {"5000", "10000", "20000"}
        or value["candidate_hub"]["speed"] != "480"
        or value["downstream_port_chain"] != "3"
        or value["same_typec_connector"] is not True
        or value["same_location"] is not True
        or value["companion_hub_identity"] is not True
        or type(value["selector_topology_count"]) is not int
        or value["selector_topology_count"] != 1
        or value["opens_candidate_acm"] is not False
        or value["device_commands"] is not False
    ):
        raise LaneBindingError("P324 Type-C binding values differ")
    digest_fields = (
        value["typec_port_sha256"],
        value["source_lane"]["resolved_sha256"],
        value["candidate_lane"]["resolved_sha256"],
        value["source_hub"]["serial_sha256"],
        value["source_hub"]["manufacturer_sha256"],
        value["candidate_hub"]["serial_sha256"],
        value["candidate_hub"]["manufacturer_sha256"],
    )
    if any(not isinstance(item, str) or DIGEST_RE.fullmatch(item) is None for item in digest_fields):
        raise LaneBindingError("P324 Type-C binding digest differs")
    if (
        value["source_hub"]["serial_sha256"]
        != value["candidate_hub"]["serial_sha256"]
        or value["source_hub"]["manufacturer_sha256"]
        != value["candidate_hub"]["manufacturer_sha256"]
    ):
        raise LaneBindingError("P324 Type-C binding hub pair differs")
    return value


def capture_shape(value: dict[str, Any]) -> dict[str, Any]:
    """Return the exact accepted shape, preserving values for strict equality."""
    top = {
        "schema",
        "contract_id",
        "binding_sha256",
        "target",
        "source_topology",
        "candidate_topology",
        "typec_port",
        "typec_port_sha256",
        "source_lane",
        "candidate_lane",
        "source_hub",
        "candidate_hub",
        "downstream_port_chain",
        "same_typec_connector",
        "same_location",
        "companion_hub_identity",
        "selector_topology_count",
        "opens_candidate_acm",
        "device_commands",
    }
    lane = {"link", "controller", "location", "resolved_sha256"}
    hub = {
        "vendor",
        "product",
        "device_class",
        "device_protocol",
        "bus",
        "root_port",
        "devpath",
        "speed",
        "serial_sha256",
        "manufacturer_sha256",
    }
    if (
        set(value) != top
        or not isinstance(value.get("source_lane"), dict)
        or not isinstance(value.get("candidate_lane"), dict)
        or set(value["source_lane"]) != lane
        or set(value["candidate_lane"]) != lane
        or not isinstance(value.get("source_hub"), dict)
        or not isinstance(value.get("candidate_hub"), dict)
        or set(value["source_hub"]) != hub
        or set(value["candidate_hub"]) != hub
    ):
        return {}
    return value


def revalidate_binding(
    value: Any,
    *,
    source_topology: str,
    usb_root: Path = Path("/sys/bus/usb/devices"),
    typec_root: Path = Path("/sys/class/typec"),
) -> dict[str, Any]:
    bound = validate_binding(value, source_topology=source_topology)
    current = capture_binding(
        source_topology, usb_root=usb_root, typec_root=typec_root
    )
    if current != bound:
        raise LaneBindingError("P324 Type-C lane binding changed")
    return bound


__all__ = [
    "CANDIDATE_TOPOLOGY",
    "CONTRACT_ID",
    "LaneBindingError",
    "SCHEMA",
    "SOURCE_TOPOLOGY",
    "TARGET",
    "capture_binding",
    "binding_digest",
    "revalidate_binding",
    "validate_binding",
]

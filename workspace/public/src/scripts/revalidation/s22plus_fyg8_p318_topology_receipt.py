#!/usr/bin/env python3
"""Immutable P3.18 Download/candidate/rollback topology receipts.

The raw snapshot is the sole parsing and hashing authority.  Candidate scans
enumerate every ttyACM endpoint but never open one; live selector authority is
therefore not widened by this module.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

import device_action_cdc_acm_observer_v1 as observer
import s22plus_fyg8_p318_cdc_acm_endpoint_transition as transition


SCHEMA = "s22plus_fyg8_p318_topology_receipt_v1"
RAW_SCHEMA = "s22plus_fyg8_p318_topology_raw_snapshot_v1"
RECORD_SCHEMA = "s22plus_fyg8_p318_topology_phase_record_v1"
HEX64_RE = re.compile(r"[0-9a-f]{64}")
USB_TOPOLOGY_RE = re.compile(r"[0-9]+-[0-9]+(?:\.[0-9]+)*")
ODIN_DEVICE_RE = re.compile(r"/dev/bus/usb/[0-9]{3}/[0-9]{3}")
MAX_RAW_BYTES = 256 * 1024


class TopologyReceiptError(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_value(value: Any) -> str:
    return digest_bytes(canonical(value))


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise TopologyReceiptError(f"duplicate raw snapshot key: {key}")
        value[key] = item
    return value


def _text(path: Path, label: str, *, optional: bool = False) -> str:
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        if optional:
            return ""
        raise TopologyReceiptError(f"topology sysfs value is absent: {label}")
    except OSError as exc:
        raise TopologyReceiptError(f"topology sysfs read failed: {label}") from exc
    if not data or len(data) > 512:
        raise TopologyReceiptError(f"topology sysfs value differs: {label}")
    try:
        return data.decode("utf-8", "strict").strip()
    except UnicodeError as exc:
        raise TopologyReceiptError(f"topology sysfs value is not UTF-8: {label}") from exc


def _controller_and_device(usb_path: Path) -> tuple[str, str]:
    try:
        device = usb_path.resolve(strict=True)
    except OSError as exc:
        raise TopologyReceiptError("USB device path is unavailable") from exc
    root = next(
        (item for item in (device, *device.parents) if re.fullmatch(r"usb[0-9]+", item.name)),
        None,
    )
    if root is None or root.parent == root:
        raise TopologyReceiptError("USB controller ancestor is absent")
    return str(root.parent), str(device)


def _endpoint_row(
    *, mode: str, identity: dict[str, str], topology: str,
    controller_path: str, usb_device_path: str,
) -> dict[str, Any]:
    if mode not in {"download", "candidate"} or USB_TOPOLOGY_RE.fullmatch(topology) is None:
        raise TopologyReceiptError("endpoint mode or topology differs")
    if not controller_path.startswith("/") or not usb_device_path.startswith("/"):
        raise TopologyReceiptError("endpoint path is not absolute")
    expected_identity = {
        "vendor", "product_id", "product", "manufacturer", "serial",
        "driver", "interface", "tty_name", "endpoint_node",
    }
    if set(identity) != expected_identity or any(
        not isinstance(value, str) for value in identity.values()
    ):
        raise TopologyReceiptError("endpoint identity shape differs")
    return {
        "mode": mode,
        "identity": identity,
        "endpoint_identity_sha256": digest_value(identity),
        "topology": topology,
        "topology_sha256": digest_bytes(topology.encode("utf-8")),
        "controller_path": controller_path,
        "controller_path_sha256": digest_bytes(controller_path.encode("utf-8")),
        "usb_device_path": usb_device_path,
        "usb_device_path_sha256": digest_bytes(usb_device_path.encode("utf-8")),
    }


def raw_snapshot(*, phase: str, capture_complete: bool, endpoints: list[dict[str, Any]]) -> bytes:
    if phase not in transition.TOPOLOGY_PHASES or not isinstance(capture_complete, bool):
        raise TopologyReceiptError("raw topology phase differs")
    if not isinstance(endpoints, list):
        raise TopologyReceiptError("raw topology endpoint list differs")
    ordered = sorted(endpoints, key=canonical)
    if len({canonical(item) for item in ordered}) != len(ordered):
        raise TopologyReceiptError("raw topology endpoint duplicates")
    return canonical({
        "schema": RAW_SCHEMA,
        "phase": phase,
        "capture_complete": capture_complete,
        "endpoints": ordered,
    })


def parse_raw_snapshot(payload: bytes, *, phase: str) -> dict[str, Any]:
    if not payload or len(payload) > MAX_RAW_BYTES:
        raise TopologyReceiptError("raw topology snapshot extent differs")
    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise TopologyReceiptError("raw topology snapshot is invalid JSON") from exc
    if not isinstance(value, dict) or set(value) != {
        "schema", "phase", "capture_complete", "endpoints"
    }:
        raise TopologyReceiptError("raw topology snapshot shape differs")
    if (
        value["schema"] != RAW_SCHEMA
        or value["phase"] != phase
        or phase not in transition.TOPOLOGY_PHASES
        or not isinstance(value["capture_complete"], bool)
        or not isinstance(value["endpoints"], list)
        or canonical(value) != payload
    ):
        raise TopologyReceiptError("raw topology snapshot authority differs")
    checked = []
    for endpoint in value["endpoints"]:
        if not isinstance(endpoint, dict):
            raise TopologyReceiptError("raw topology endpoint differs")
        expected = _endpoint_row(
            mode=endpoint.get("mode"),
            identity=endpoint.get("identity"),
            topology=endpoint.get("topology"),
            controller_path=endpoint.get("controller_path"),
            usb_device_path=endpoint.get("usb_device_path"),
        )
        if endpoint != expected:
            raise TopologyReceiptError("raw topology endpoint digest differs")
        checked.append(endpoint)
    if checked != sorted(checked, key=canonical) or len({canonical(row) for row in checked}) != len(checked):
        raise TopologyReceiptError("raw topology endpoint order differs")
    return value


def _publish(path: Path, payload: bytes) -> dict[str, Any]:
    if path.exists() or path.is_symlink():
        raise TopologyReceiptError("topology receipt destination exists")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400
    )
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise TopologyReceiptError("short topology receipt write")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.link(temporary, path, follow_symlinks=False)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)
    reopened = path.read_bytes()
    if reopened != payload:
        raise TopologyReceiptError("published topology receipt changed")
    return {"size": len(payload), "sha256": digest_bytes(payload)}


def stable_read(path: Path, *, maximum: int = MAX_RAW_BYTES) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
        if path.is_symlink() or not path.is_file() or not 0 < before.st_size <= maximum:
            raise TopologyReceiptError("topology evidence is not a bounded regular file")
        payload = path.read_bytes()
        after = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise TopologyReceiptError("topology evidence is unavailable") from exc
    if (
        len(payload) != before.st_size
        or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    ):
        raise TopologyReceiptError("topology evidence changed while read")
    return payload


def publish_raw(path: Path, payload: bytes, *, phase: str) -> dict[str, Any]:
    parse_raw_snapshot(payload, phase=phase)
    return _publish(path, payload)


def capture_candidate_raw(
    *, phase: str, class_tty: Path = Path("/sys/class/tty")
) -> bytes:
    if phase != "candidate_end":
        raise TopologyReceiptError("candidate capture phase differs")
    try:
        entries = sorted(class_tty.glob("ttyACM*"))
    except OSError as exc:
        raise TopologyReceiptError("candidate tty class scan failed") from exc
    complete = True
    endpoints: list[dict[str, Any]] = []
    for entry in entries:
        try:
            identity, endpoint = observer._resolve_endpoint(entry)  # noqa: SLF001
            controller, device = _controller_and_device(endpoint.usb_path)
            endpoints.append(_endpoint_row(
                mode="candidate",
                identity={
                    "vendor": identity["vendor"],
                    "product_id": identity["product"],
                    "product": _text(endpoint.usb_path / "product", "candidate product", optional=True),
                    "manufacturer": _text(endpoint.usb_path / "manufacturer", "candidate manufacturer", optional=True),
                    "serial": identity["serial"],
                    "driver": identity["driver"],
                    "interface": identity["interface"],
                    "tty_name": identity["tty_name"],
                    "endpoint_node": f"/dev/{identity['tty_name']}",
                },
                topology=endpoint.topology,
                controller_path=controller,
                usb_device_path=device,
            ))
        except (observer.ObserverError, TopologyReceiptError):
            complete = False
    return raw_snapshot(phase=phase, capture_complete=complete, endpoints=endpoints)


def capture_download_raw(
    *, phase: str, device: str, topology: str, profile: dict[str, Any],
    usb_root: Path = Path("/sys/bus/usb/devices"),
) -> bytes:
    if phase not in {"download_start", "rollback_download"}:
        raise TopologyReceiptError("Download capture phase differs")
    match = re.fullmatch(r"usb:(?P<top>[0-9]+-[0-9]+(?:\.[0-9]+)*)", topology)
    coordinates = ODIN_DEVICE_RE.fullmatch(device)
    if match is None or coordinates is None:
        raise TopologyReceiptError("Download endpoint shape differs")
    node = usb_root / match.group("top")
    try:
        controller, usb_device = _controller_and_device(node)
        values = {
            name: _text(node / name, f"Download {name}", optional=name == "serial")
            for name in (
                "busnum", "devnum", "idVendor", "idProduct", "product",
                "manufacturer", "serial",
            )
        }
        repeated = {
            name: _text(node / name, f"Download repeated {name}", optional=name == "serial")
            for name in values
        }
        download = profile["target"]["download"]
        device_match = re.fullmatch(r"/dev/bus/usb/([0-9]{3})/([0-9]{3})", device)
        assert device_match is not None
        exact = (
            values == repeated
            and values["busnum"] == str(int(device_match.group(1)))
            and values["devnum"] == str(int(device_match.group(2)))
            and values["idVendor"] == download["usb_vendor_id"]
            and values["idProduct"] == download["usb_product_id"]
            and values["product"] == download["product"]
            and values["manufacturer"] == download["manufacturer"]
            and values["serial"] == ""
        )
        endpoints = [] if not exact else [_endpoint_row(
            mode="download",
            identity={
                "vendor": values["idVendor"],
                "product_id": values["idProduct"],
                "product": values["product"],
                "manufacturer": values["manufacturer"],
                "serial": values["serial"],
                "driver": "",
                "interface": "",
                "tty_name": "",
                "endpoint_node": device,
            },
            topology=match.group("top"),
            controller_path=controller,
            usb_device_path=usb_device,
        )]
        return raw_snapshot(
            phase=phase, capture_complete=exact, endpoints=endpoints
        )
    except (KeyError, OSError, TopologyReceiptError):
        return raw_snapshot(phase=phase, capture_complete=False, endpoints=[])


def capture_download_inventory_raw(
    *, phase: str, profile: dict[str, Any],
    usb_root: Path = Path("/sys/bus/usb/devices"),
) -> bytes:
    if phase not in {"download_start", "rollback_download"}:
        raise TopologyReceiptError("Download inventory phase differs")
    try:
        entries = sorted(
            path for path in usb_root.iterdir()
            if USB_TOPOLOGY_RE.fullmatch(path.name) is not None
        )
    except OSError:
        return raw_snapshot(phase=phase, capture_complete=False, endpoints=[])
    endpoints: list[dict[str, Any]] = []
    complete = True
    try:
        download = profile["target"]["download"]
    except (KeyError, TypeError):
        return raw_snapshot(phase=phase, capture_complete=False, endpoints=[])
    for node in entries:
        try:
            vendor = _text(node / "idVendor", "Download inventory idVendor")
            product_id = _text(node / "idProduct", "Download inventory idProduct")
        except TopologyReceiptError:
            complete = False
            continue
        if (
            vendor != download.get("usb_vendor_id")
            or product_id != download.get("usb_product_id")
        ):
            continue
        try:
            values = {
                name: _text(
                    node / name,
                    f"Download inventory {name}",
                    optional=name == "serial",
                )
                for name in (
                    "busnum", "devnum", "product", "manufacturer", "serial"
                )
            }
            repeated = {
                name: _text(
                    node / name,
                    f"Download inventory repeated {name}",
                    optional=name == "serial",
                )
                for name in values
            }
            if (
                values != repeated
                or values["product"] != download["product"]
                or values["manufacturer"] != download["manufacturer"]
                or values["serial"] != ""
                or not values["busnum"].isdigit()
                or not values["devnum"].isdigit()
            ):
                complete = False
                continue
            controller, usb_device = _controller_and_device(node)
            endpoint_node = (
                f"/dev/bus/usb/{int(values['busnum']):03d}/"
                f"{int(values['devnum']):03d}"
            )
            endpoints.append(_endpoint_row(
                mode="download",
                identity={
                    "vendor": vendor,
                    "product_id": product_id,
                    "product": values["product"],
                    "manufacturer": values["manufacturer"],
                    "serial": "",
                    "driver": "",
                    "interface": "",
                    "tty_name": "",
                    "endpoint_node": endpoint_node,
                },
                topology=node.name,
                controller_path=controller,
                usb_device_path=usb_device,
            ))
        except (KeyError, TopologyReceiptError):
            complete = False
    return raw_snapshot(
        phase=phase, capture_complete=complete, endpoints=endpoints
    )


def _target_match(endpoint: dict[str, Any], target: dict[str, str]) -> bool:
    identity = endpoint["identity"]
    return all(identity.get(key) == value for key, value in target.items())


def matching_endpoints(
    payload: bytes, *, phase: str, target_identity: dict[str, str]
) -> list[dict[str, Any]]:
    parsed = parse_raw_snapshot(payload, phase=phase)
    return [
        endpoint for endpoint in parsed["endpoints"]
        if _target_match(endpoint, target_identity)
    ]


def _path_tuple(endpoint: dict[str, Any]) -> tuple[str, str, str]:
    return (
        endpoint["topology_sha256"],
        endpoint["controller_path_sha256"],
        endpoint["usb_device_path_sha256"],
    )


def _candidate_host_observer(value: Any) -> dict[str, Any]:
    keys = {
        "classification",
        "endpoint_identity_sha256",
        "receipt_sha256",
        "topology_sha256",
        "bounded",
        "valid_receipt",
        "download_endpoint_absent",
    }
    if not isinstance(value, dict) or set(value) != keys:
        raise TopologyReceiptError("candidate host observer shape differs")
    classification = value["classification"]
    endpoint = value["endpoint_identity_sha256"]
    valid = value["valid_receipt"]
    if (
        classification not in observer.CLASSIFICATIONS
        or not isinstance(valid, bool)
        or not isinstance(value["download_endpoint_absent"], bool)
        or not isinstance(value["topology_sha256"], str)
        or HEX64_RE.fullmatch(value["topology_sha256"]) is None
        or (
            endpoint is not None
            and (
                not isinstance(endpoint, str)
                or HEX64_RE.fullmatch(endpoint) is None
            )
        )
        or (
            valid
            and (
                classification == "interrupted-before-receipt"
                or value["bounded"] is not True
                or not isinstance(value["receipt_sha256"], str)
                or HEX64_RE.fullmatch(value["receipt_sha256"]) is None
                or (classification == "accepted" and endpoint is None)
                or (classification == "endpoint-timeout" and endpoint is not None)
            )
        )
        or (
            not valid
            and (
                classification != "interrupted-before-receipt"
                or value["bounded"] is not False
                or value["receipt_sha256"] is not None
                or endpoint is not None
                or value["download_endpoint_absent"] is not False
            )
        )
    ):
        raise TopologyReceiptError("candidate host observer domain differs")
    return dict(value)


def build_phase_record(
    payload: bytes,
    *,
    phase: str,
    target_identity: dict[str, str],
    binding_id_sha256: str,
    comparison_binding_id_sha256: str,
    authority_state: str,
    causal_terminal_ready: bool,
    start_path: tuple[str, str, str] | None,
    host_observer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if (
        HEX64_RE.fullmatch(binding_id_sha256) is None
        or HEX64_RE.fullmatch(comparison_binding_id_sha256) is None
        or authority_state not in transition.TOPOLOGY_AUTHORITIES
        or not isinstance(causal_terminal_ready, bool)
        or not isinstance(target_identity, dict)
        or any(not isinstance(key, str) or not isinstance(value, str) for key, value in target_identity.items())
    ):
        raise TopologyReceiptError("topology record binding differs")
    if phase == "candidate_end":
        host = _candidate_host_observer(host_observer)
        if start_path is None or host["topology_sha256"] != start_path[0]:
            raise TopologyReceiptError("candidate host topology binding differs")
    elif host_observer is not None:
        raise TopologyReceiptError("Download phase cannot carry a host observer")
    else:
        host = None
    parsed = parse_raw_snapshot(payload, phase=phase)
    matching = [
        endpoint for endpoint in parsed["endpoints"]
        if _target_match(endpoint, target_identity)
    ]
    snapshot_complete = bool(parsed["capture_complete"])
    complete = snapshot_complete
    if host is not None:
        complete = (
            snapshot_complete
            and host["valid_receipt"] is True
            and host["download_endpoint_absent"] is True
            and host["classification"] != "guard-lost"
        )
    selected = matching[0] if len(matching) == 1 else None
    if not complete:
        relationship = "unavailable"
    elif len(matching) > 1:
        relationship = "ambiguous"
    elif phase == "download_start":
        relationship = "absent" if not matching else "same"
    elif start_path is None:
        raise TopologyReceiptError("topology comparison path is absent")
    elif phase == "rollback_download":
        relationship = (
            "absent"
            if selected is None
            else "same"
            if _path_tuple(selected) == start_path
            else "drift"
        )
    else:
        endpoint_seen = host is not None and host["endpoint_identity_sha256"] is not None
        host_ambiguous = host is not None and host["classification"] in {
            "endpoint-ambiguous", "identity-mismatch"
        }
        endpoint_identity_changed = (
            endpoint_seen
            and selected is not None
            and host["endpoint_identity_sha256"]
            != selected["endpoint_identity_sha256"]
        )
        if host_ambiguous or endpoint_identity_changed:
            relationship = "ambiguous"
        elif selected is not None and _path_tuple(selected) != start_path:
            relationship = "drift"
        elif selected is not None and not endpoint_seen:
            # The exact endpoint appeared only after the bounded host window.
            relationship = "ambiguous"
        elif selected is not None or endpoint_seen:
            relationship = "same"
        else:
            relationship = "absent"
    classification = transition.classify_topology_phase(
        phase=phase,
        relationship=relationship,
        authority_state=authority_state,
        observation_complete=complete,
        causal_terminal_ready=causal_terminal_ready,
    )
    return {
        "schema": RECORD_SCHEMA,
        "phase": phase,
        "target_identity_sha256": digest_value(target_identity),
        "relationship_to_start": relationship,
        "authority_state": authority_state,
        "binding_id_sha256": binding_id_sha256,
        "comparison_binding_id_sha256": comparison_binding_id_sha256,
        "match_count": len(matching),
        "snapshot_capture_complete": snapshot_complete,
        "observation_window_complete": complete,
        "host_observer": host,
        "causal_terminal_ready": causal_terminal_ready,
        "endpoint_identity_sha256": None if selected is None else selected["endpoint_identity_sha256"],
        "topology_sha256": None if selected is None else selected["topology_sha256"],
        "controller_path_sha256": None if selected is None else selected["controller_path_sha256"],
        "usb_device_path_sha256": None if selected is None else selected["usb_device_path_sha256"],
        "immutable_raw_snapshot_size": len(payload),
        "immutable_raw_snapshot_sha256": digest_bytes(payload),
        "decision": classification,
    }


def validate_phase_record(
    value: Any,
    *,
    raw_payload: bytes | None = None,
    target_identity: dict[str, str] | None = None,
    start_path: tuple[str, str, str] | None = None,
) -> dict[str, Any]:
    keys = {
        "schema", "phase", "target_identity_sha256",
        "relationship_to_start", "authority_state",
        "binding_id_sha256", "comparison_binding_id_sha256", "match_count",
        "snapshot_capture_complete", "observation_window_complete",
        "causal_terminal_ready", "host_observer",
        "endpoint_identity_sha256", "topology_sha256",
        "controller_path_sha256", "usb_device_path_sha256",
        "immutable_raw_snapshot_size", "immutable_raw_snapshot_sha256",
        "decision",
    }
    if not isinstance(value, dict) or set(value) != keys:
        raise TopologyReceiptError("topology phase record shape differs")
    phase = value["phase"]
    relationship = value["relationship_to_start"]
    authority = value["authority_state"]
    count = value["match_count"]
    snapshot_complete = value["snapshot_capture_complete"]
    complete = value["observation_window_complete"]
    causal = value["causal_terminal_ready"]
    if (
        value["schema"] != RECORD_SCHEMA
        or phase not in transition.TOPOLOGY_PHASES
        or not isinstance(value["target_identity_sha256"], str)
        or HEX64_RE.fullmatch(value["target_identity_sha256"]) is None
        or relationship not in transition.TOPOLOGY_RELATIONSHIPS
        or authority not in transition.TOPOLOGY_AUTHORITIES
        or any(
            not isinstance(value[name], str)
            or HEX64_RE.fullmatch(value[name]) is None
            for name in ("binding_id_sha256", "comparison_binding_id_sha256")
        )
        or isinstance(count, bool)
        or not isinstance(count, int)
        or count < 0
        or not isinstance(snapshot_complete, bool)
        or not isinstance(complete, bool)
        or not isinstance(causal, bool)
        or isinstance(value["immutable_raw_snapshot_size"], bool)
        or not isinstance(value["immutable_raw_snapshot_size"], int)
        or not 0 < value["immutable_raw_snapshot_size"] <= MAX_RAW_BYTES
        or not isinstance(value["immutable_raw_snapshot_sha256"], str)
        or HEX64_RE.fullmatch(value["immutable_raw_snapshot_sha256"]) is None
    ):
        raise TopologyReceiptError("topology phase record domain differs")
    host = value["host_observer"]
    if phase == "candidate_end":
        host = _candidate_host_observer(host)
    elif host is not None:
        raise TopologyReceiptError("Download phase host observer differs")
    if not snapshot_complete and complete:
        raise TopologyReceiptError("topology snapshot completeness differs")
    if not complete and relationship != "unavailable":
        raise TopologyReceiptError("topology incomplete relationship differs")
    if complete and relationship == "unavailable":
        raise TopologyReceiptError("topology complete relationship differs")
    if complete and count > 1 and relationship != "ambiguous":
        raise TopologyReceiptError("topology phase record count relationship differs")
    selected_fields = (
        "endpoint_identity_sha256", "topology_sha256",
        "controller_path_sha256", "usb_device_path_sha256",
    )
    selected = complete and count == 1
    if any(
        (not isinstance(value[name], str) or HEX64_RE.fullmatch(value[name]) is None)
        if selected else value[name] is not None
        for name in selected_fields
    ):
        raise TopologyReceiptError("topology selected endpoint authority differs")
    expected_decision = transition.classify_topology_phase(
        phase=phase,
        relationship=relationship,
        authority_state=authority,
        observation_complete=complete,
        causal_terminal_ready=causal,
    )
    if value["decision"] != expected_decision:
        raise TopologyReceiptError("topology phase decision differs")
    if raw_payload is not None and (
        len(raw_payload) != value["immutable_raw_snapshot_size"]
        or digest_bytes(raw_payload) != value["immutable_raw_snapshot_sha256"]
        or parse_raw_snapshot(raw_payload, phase=phase)["capture_complete"]
        is not complete
    ):
        raise TopologyReceiptError("topology raw and phase record differ")
    if target_identity is not None:
        if (
            not isinstance(target_identity, dict)
            or any(
                not isinstance(key, str) or not isinstance(item, str)
                for key, item in target_identity.items()
            )
            or digest_value(target_identity) != value["target_identity_sha256"]
        ):
            raise TopologyReceiptError("topology target identity differs")
        if raw_payload is None:
            raise TopologyReceiptError("topology target replay lacks raw bytes")
        expected = build_phase_record(
            raw_payload,
            phase=phase,
            target_identity=target_identity,
            binding_id_sha256=value["binding_id_sha256"],
            comparison_binding_id_sha256=value[
                "comparison_binding_id_sha256"
            ],
            authority_state=authority,
            causal_terminal_ready=causal,
            start_path=start_path,
            host_observer=host,
        )
        if value != expected:
            raise TopologyReceiptError("topology phase replay differs")
    return value


def publish_phase(
    raw_path: Path, record_path: Path, payload: bytes, **record_args: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    record = validate_phase_record(
        build_phase_record(payload, **record_args), raw_payload=payload
    )
    raw_receipt = _publish(raw_path, payload)
    record_payload = canonical(record)
    record_receipt = _publish(record_path, record_payload)
    if raw_receipt != {
        "size": record["immutable_raw_snapshot_size"],
        "sha256": record["immutable_raw_snapshot_sha256"],
    }:
        raise TopologyReceiptError("topology record and raw receipt differ")
    return record, {"raw": raw_receipt, "record": record_receipt}


def publish_record_for_existing_raw(
    raw_path: Path,
    record_path: Path,
    payload: bytes,
    **record_args: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if stable_read(raw_path) != payload:
        raise TopologyReceiptError("existing topology raw snapshot changed")
    record = validate_phase_record(
        build_phase_record(payload, **record_args), raw_payload=payload
    )
    record_receipt = _publish(record_path, canonical(record))
    return record, record_receipt


def start_path(record: dict[str, Any]) -> tuple[str, str, str]:
    if (
        record.get("schema") != RECORD_SCHEMA
        or record.get("phase") != "download_start"
        or record.get("relationship_to_start") != "same"
        or record.get("match_count") != 1
        or record.get("observation_window_complete") is not True
    ):
        raise TopologyReceiptError("Download-start path record is not exact")
    values = tuple(
        record.get(key) for key in (
            "topology_sha256", "controller_path_sha256", "usb_device_path_sha256"
        )
    )
    if any(not isinstance(value, str) or HEX64_RE.fullmatch(value) is None for value in values):
        raise TopologyReceiptError("Download-start path digest differs")
    return values  # type: ignore[return-value]


def validate() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "same_bytes_parsed_and_hashed": True,
        "candidate_scan_opens_endpoint": False,
        "phases": list(transition.TOPOLOGY_PHASES),
        "relationships": list(transition.TOPOLOGY_RELATIONSHIPS),
        "authorities": list(transition.TOPOLOGY_AUTHORITIES),
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))

#!/usr/bin/env python3
"""P3.24 exact Type-C lane adapter for the existing CDC-ACM observer.

The shared observer remains unchanged and still opens one literal topology.
This adapter records both exact connector lanes, proves the Type-C partner did
not disappear or get replaced during the candidate window, and delegates the
only possible open to the bound high-speed candidate lane ``usb:3-1.3``.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import device_action_cdc_acm_observer_v1 as observer
import s22plus_fyg8_p324_typec_lane_binding as lane


SCHEMA = "s22plus_fyg8_p324_cdc_acm_lane_receipt_v1"
ARM_SCHEMA = "s22plus_fyg8_p324_cdc_acm_lane_arm_v1"
CONTRACT_ID = "s22plus-fyg8-p324-cdc-acm-exact-lane-v1"
TARGET = lane.TARGET
SUPPLEMENT_NAME = "p324-candidate-observer-lane.json"
ARM_NAME = "p324-candidate-observer-lane-arm.json"
DIGEST_RE = re.compile(r"[0-9a-f]{64}")


class P324ObserverError(ValueError):
    """The P3.24 lane, partner, inventory, or delegated receipt differs."""


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("ascii")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _file_receipt(path: Path, label: str) -> dict[str, Any]:
    _payload, receipt = _stable_payload(path, label)
    return receipt


def _stable_payload(
    path: Path, label: str, maximum: int = 2 * 1024 * 1024
) -> tuple[bytes, dict[str, Any]]:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        descriptor = os.open(direct, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            inside = os.fstat(descriptor)
            chunks: list[bytes] = []
            remaining = maximum + 1
            while remaining:
                chunk = os.read(descriptor, min(65536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            payload = b"".join(chunks)
        finally:
            os.close(descriptor)
        after = direct.lstat()
    except OSError as exc:
        raise P324ObserverError(f"{label} is unavailable") from exc
    identity = lambda item: (  # noqa: E731
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_nlink,
        item.st_uid,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )
    if (
        direct != resolved
        or not stat.S_ISREG(before.st_mode)
        or stat.S_ISLNK(before.st_mode)
        or before.st_nlink != 1
        or before.st_uid != os.getuid()
        or stat.S_IMODE(before.st_mode) != 0o400
        or identity(before) != identity(inside)
        or identity(before) != identity(after)
        or not 0 < len(payload) <= maximum
        or len(payload) != before.st_size
    ):
        raise P324ObserverError(f"{label} changed")
    return payload, {
        "path": str(direct),
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _partner(typec_root: Path) -> dict[str, Any]:
    path = typec_root / lane.TYPEC_PORT / f"{lane.TYPEC_PORT}-partner"
    try:
        entry_before = path.lstat()
        resolved = path.resolve(strict=True)
        target_before = resolved.lstat()
        entry_after = path.lstat()
        target_after = resolved.lstat()
    except OSError as exc:
        raise P324ObserverError("P324 Type-C partner is unavailable") from exc
    entry_identity = lambda item: (  # noqa: E731
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_ctime_ns,
    )
    target_identity = lambda item: (  # noqa: E731
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_ctime_ns,
    )
    if (
        not stat.S_ISDIR(entry_before.st_mode)
        or not stat.S_ISDIR(target_before.st_mode)
        or entry_identity(entry_before) != entry_identity(entry_after)
        or target_identity(target_before) != target_identity(target_after)
    ):
        raise P324ObserverError("P324 Type-C partner changed while reading")
    return {
        "entry_dev": entry_before.st_dev,
        "entry_ino": entry_before.st_ino,
        "entry_ctime_ns": entry_before.st_ctime_ns,
        "target_dev": target_before.st_dev,
        "target_ino": target_before.st_ino,
        "target_ctime_ns": target_before.st_ctime_ns,
        "target_sha256": hashlib.sha256(
            str(resolved).encode("utf-8")
        ).hexdigest(),
    }


def _exact(
    spec: dict[str, str],
    topology: str,
    identity: dict[str, str],
    endpoint: observer.Endpoint,
    usb_root: Path,
) -> bool:
    if endpoint.topology != topology.removeprefix("usb:"):
        return False
    try:
        expected_path = (
            usb_root / topology.removeprefix("usb:")
        ).resolve(strict=True)
        actual_path = endpoint.usb_path.resolve(strict=True)
    except OSError as exc:
        raise P324ObserverError("P324 endpoint path is unavailable") from exc
    return (
        actual_path == expected_path
        and identity["vendor"] == spec["usb_vendor_id"]
        and identity["product"] == spec["usb_product_id"]
        and identity["serial"] == spec["usb_serial"]
        and identity["driver"] == spec["usb_driver"]
        and identity["interface"] == spec["usb_interface_number"]
    )


def _candidate_like(
    spec: dict[str, str],
    topology: str,
    identity: dict[str, str],
    endpoint: observer.Endpoint,
) -> bool:
    return (
        endpoint.topology == topology.removeprefix("usb:")
        and identity["vendor"] == spec["usb_vendor_id"]
        and identity["product"] == spec["usb_product_id"]
    )


def _inventory(
    spec: dict[str, str], class_tty: Path, usb_root: Path
) -> dict[str, Any]:
    try:
        entries = sorted(class_tty.glob("ttyACM*"))
    except OSError as exc:
        raise P324ObserverError("P324 CDC ACM inventory is unavailable") from exc
    values: list[tuple[dict[str, str], observer.Endpoint]] = []
    for entry in entries:
        try:
            values.append(observer._resolve_endpoint(entry))  # noqa: SLF001
        except observer.ObserverError as exc:
            raise P324ObserverError(
                "P324 CDC ACM inventory contains an unreadable entry"
            ) from exc
    rows: dict[str, Any] = {}
    for topology in (lane.SOURCE_TOPOLOGY, lane.CANDIDATE_TOPOLOGY):
        selected = [
            (identity, endpoint)
            for identity, endpoint in values
            if endpoint.topology == topology.removeprefix("usb:")
        ]
        rows[topology] = {
            "topology_sha256": hashlib.sha256(
                topology.removeprefix("usb:").encode("ascii")
            ).hexdigest(),
            "endpoint_count": len(selected),
            "exact_candidate_count": sum(
                _exact(spec, topology, identity, endpoint, usb_root)
                for identity, endpoint in selected
            ),
            "candidate_like_count": sum(
                _candidate_like(spec, topology, identity, endpoint)
                for identity, endpoint in selected
            ),
            "endpoint_identity_sha256": sorted(
                endpoint.identity_sha256 for _, endpoint in selected
            ),
            "present": bool(selected),
        }
    pair_topologies = {
        lane.SOURCE_TOPOLOGY.removeprefix("usb:"),
        lane.CANDIDATE_TOPOLOGY.removeprefix("usb:"),
    }
    foreign_like = [
        endpoint.identity_sha256
        for identity, endpoint in values
        if endpoint.topology not in pair_topologies
        and identity["vendor"] == spec["usb_vendor_id"]
        and identity["product"] == spec["usb_product_id"]
    ]
    return {
        "scan_complete": True,
        "all_endpoint_count": len(values),
        "all_endpoint_identity_sha256": sorted(
            endpoint.identity_sha256 for _, endpoint in values
        ),
        "foreign_candidate_like_count": len(foreign_like),
        "foreign_candidate_like_identity_sha256": sorted(foreign_like),
        "rows": rows,
    }


def _validate_inventory(value: Any, *, label: str) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "scan_complete",
            "all_endpoint_count",
            "all_endpoint_identity_sha256",
            "foreign_candidate_like_count",
            "foreign_candidate_like_identity_sha256",
            "rows",
        }
        or value["scan_complete"] is not True
        or type(value["all_endpoint_count"]) is not int
        or value["all_endpoint_count"] < 0
        or type(value["foreign_candidate_like_count"]) is not int
        or value["foreign_candidate_like_count"] < 0
        or not isinstance(value["all_endpoint_identity_sha256"], list)
        or len(value["all_endpoint_identity_sha256"])
        != value["all_endpoint_count"]
        or value["all_endpoint_identity_sha256"]
        != sorted(value["all_endpoint_identity_sha256"])
        or not isinstance(value["foreign_candidate_like_identity_sha256"], list)
        or len(value["foreign_candidate_like_identity_sha256"])
        != value["foreign_candidate_like_count"]
        or value["foreign_candidate_like_identity_sha256"]
        != sorted(value["foreign_candidate_like_identity_sha256"])
        or any(
            not isinstance(item, str) or DIGEST_RE.fullmatch(item) is None
            for item in (
                value["all_endpoint_identity_sha256"]
                + value["foreign_candidate_like_identity_sha256"]
            )
        )
        or not isinstance(value["rows"], dict)
        or set(value["rows"]) != {
            lane.SOURCE_TOPOLOGY,
            lane.CANDIDATE_TOPOLOGY,
        }
    ):
        raise P324ObserverError(f"{label} inventory shape differs")
    total = 0
    for topology, row in value["rows"].items():
        if (
            not isinstance(row, dict)
            or set(row)
            != {
                "topology_sha256",
                "endpoint_count",
                "exact_candidate_count",
                "candidate_like_count",
                "endpoint_identity_sha256",
                "present",
            }
            or row["topology_sha256"]
            != hashlib.sha256(
                topology.removeprefix("usb:").encode("ascii")
            ).hexdigest()
            or type(row["endpoint_count"]) is not int
            or type(row["exact_candidate_count"]) is not int
            or type(row["candidate_like_count"]) is not int
            or min(
                row["endpoint_count"],
                row["exact_candidate_count"],
                row["candidate_like_count"],
            )
            < 0
            or row["exact_candidate_count"] > row["candidate_like_count"]
            or row["candidate_like_count"] > row["endpoint_count"]
            or row["present"] is not (row["endpoint_count"] > 0)
            or not isinstance(row["endpoint_identity_sha256"], list)
            or len(row["endpoint_identity_sha256"]) != row["endpoint_count"]
            or row["endpoint_identity_sha256"]
            != sorted(row["endpoint_identity_sha256"])
            or any(
                not isinstance(item, str) or DIGEST_RE.fullmatch(item) is None
                for item in row["endpoint_identity_sha256"]
            )
        ):
            raise P324ObserverError(f"{label} inventory row differs")
        total += row["endpoint_count"]
    if total > value["all_endpoint_count"]:
        raise P324ObserverError(f"{label} inventory total differs")
    return value


def _validate_partner(value: Any, label: str) -> dict[str, Any]:
    keys = {
        "entry_dev",
        "entry_ino",
        "entry_ctime_ns",
        "target_dev",
        "target_ino",
        "target_ctime_ns",
        "target_sha256",
    }
    if (
        not isinstance(value, dict)
        or set(value) != keys
        or any(type(value[key]) is not int or value[key] <= 0 for key in keys - {"target_sha256"})
        or not isinstance(value["target_sha256"], str)
        or DIGEST_RE.fullmatch(value["target_sha256"]) is None
    ):
        raise P324ObserverError(f"{label} Type-C partner differs")
    return value


@dataclass
class P324ObserverSession:
    delegate: observer.ObserverSession
    spec: dict[str, str]
    run_dir: Path
    lane_binding: dict[str, Any]
    lane_binding_receipt: dict[str, Any]
    arm: dict[str, Any]
    arm_receipt: dict[str, Any]
    partner_before: dict[str, Any]
    class_tty: Path
    usb_root: Path
    typec_root: Path
    partner_poll_count: int = 0
    partner_continuous: bool = True

    def _select(self) -> tuple[str, observer.Endpoint | None]:
        self.partner_poll_count += 1
        try:
            current_partner = _partner(self.typec_root)
        except P324ObserverError:
            self.partner_continuous = False
        else:
            if current_partner != self.partner_before:
                self.partner_continuous = False
        try:
            entries = sorted(self.class_tty.glob("ttyACM*"))
            values = [
                observer._resolve_endpoint(entry)  # noqa: SLF001
                for entry in entries
            ]
        except (OSError, observer.ObserverError) as exc:
            raise P324ObserverError(
                "P324 CDC ACM selector inventory is incomplete"
            ) from exc
        source_exact = [
            endpoint
            for identity, endpoint in values
            if _exact(
                self.spec,
                lane.SOURCE_TOPOLOGY,
                identity,
                endpoint,
                self.usb_root,
            )
        ]
        candidate_exact = [
            endpoint
            for identity, endpoint in values
            if _exact(
                self.spec,
                lane.CANDIDATE_TOPOLOGY,
                identity,
                endpoint,
                self.usb_root,
            )
        ]
        candidate_like = [
            endpoint
            for identity, endpoint in values
            if identity["vendor"] == self.spec["usb_vendor_id"]
            and identity["product"] == self.spec["usb_product_id"]
        ]
        if not self.partner_continuous:
            return "identity-mismatch", None
        if (
            len(source_exact) + len(candidate_exact) > 1
            or candidate_exact and len(candidate_like) > 1
        ):
            return "endpoint-ambiguous", None
        if source_exact:
            return "identity-mismatch", None
        if len(candidate_exact) == 1 and len(candidate_like) == 1:
            try:
                lane.revalidate_binding(
                    self.lane_binding,
                    source_topology=lane.SOURCE_TOPOLOGY,
                    usb_root=self.usb_root,
                    typec_root=self.typec_root,
                )
            except lane.LaneBindingError:
                self.partner_continuous = False
                return "identity-mismatch", None
            return "accepted", candidate_exact[0]
        if candidate_exact or candidate_like:
            return "identity-mismatch", None
        return "endpoint-timeout", None

    def observe(
        self, *, timeout_sec: int, download_departure: dict[str, Any]
    ) -> dict[str, Any]:
        if self.delegate.topology != lane.CANDIDATE_TOPOLOGY:
            raise P324ObserverError("P324 delegated selector topology differs")
        original_select = self.delegate._select
        self.delegate._select = self._select  # type: ignore[method-assign]
        try:
            base = self.delegate.observe(
                timeout_sec=timeout_sec, download_departure=download_departure
            )
        finally:
            self.delegate._select = original_select  # type: ignore[method-assign]
        current_lane = lane.revalidate_binding(
            self.lane_binding,
            source_topology=lane.SOURCE_TOPOLOGY,
            usb_root=self.usb_root,
            typec_root=self.typec_root,
        )
        partner_after = _partner(self.typec_root)
        end_inventory = _inventory(self.spec, self.class_tty, self.usb_root)
        _validate_inventory(end_inventory, label="P324 end")
        source_row = end_inventory["rows"][lane.SOURCE_TOPOLOGY]
        candidate_row = end_inventory["rows"][lane.CANDIDATE_TOPOLOGY]
        same_partner = (
            partner_after == self.partner_before
            and self.partner_continuous
            and self.partner_poll_count > 0
        )
        accepted_inventory = (
            base.get("accepted") is True
            and source_row["exact_candidate_count"] == 0
            and candidate_row["exact_candidate_count"] == 1
            and candidate_row["candidate_like_count"] == 1
            and end_inventory["foreign_candidate_like_count"] == 0
        )
        accepted_for_p324 = accepted_inventory and same_partner
        value = {
            "schema": SCHEMA,
            "contract_id": CONTRACT_ID,
            "target": TARGET,
            "lane_binding": self.lane_binding_receipt,
            "lane_binding_sha256": _digest(current_lane),
            "arm": self.arm_receipt,
            "base_observer": _file_receipt(
                self.run_dir / "candidate-observer.json",
                "P324 base observer receipt",
            ),
            "source_topology": lane.SOURCE_TOPOLOGY,
            "candidate_topology": lane.CANDIDATE_TOPOLOGY,
            "selector_topology_count": 1,
            "partner_before": self.partner_before,
            "partner_after": partner_after,
            "partner_poll_count": self.partner_poll_count,
            "partner_continuous": self.partner_continuous,
            "end_inventory": end_inventory,
            "both_topologies_inventory_complete": True,
            "accepted_inventory_exact": accepted_inventory,
            "same_run_typec_partner_continuity": same_partner,
            "accepted_for_p324": accepted_for_p324,
            "opens_only_candidate_topology": True,
            "device_commands": False,
        }
        observer.persist_json(self.run_dir / SUPPLEMENT_NAME, value)
        projected = dict(base)
        if base.get("accepted") is True and not accepted_for_p324:
            projected["accepted"] = False
            projected["exact"] = False
            projected["classification"] = (
                "endpoint-ambiguous"
                if (
                    source_row["exact_candidate_count"]
                    + candidate_row["exact_candidate_count"]
                    + end_inventory["foreign_candidate_like_count"]
                    > 1
                )
                else "identity-mismatch"
            )
        return projected


@contextlib.contextmanager
def observer_session(
    spec: dict[str, str],
    source_topology: str,
    run_dir: Path,
    binding: dict[str, str],
    lane_binding: dict[str, Any],
    lane_binding_receipt: dict[str, Any],
    *,
    class_tty: Path = Path("/sys/class/tty"),
    dev_root: Path = Path("/dev"),
    usb_root: Path = Path("/sys/bus/usb/devices"),
    typec_root: Path = Path("/sys/class/typec"),
    max_sec: int = observer.GUARD_DEFAULT_MAX_SEC,
) -> Iterator[P324ObserverSession]:
    observer.validate_spec(spec)
    current_lane = lane.revalidate_binding(
        lane_binding,
        source_topology=source_topology,
        usb_root=usb_root,
        typec_root=typec_root,
    )
    arm_inventory = _inventory(spec, class_tty, usb_root)
    _validate_inventory(arm_inventory, label="P324 arm")
    if (
        any(
            row["candidate_like_count"] != 0
            for row in arm_inventory["rows"].values()
        )
        or arm_inventory["foreign_candidate_like_count"] != 0
    ):
        raise P324ObserverError("P324 candidate-like identity is present before arm")
    partner_before = _partner(typec_root)
    arm = {
        "schema": ARM_SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "lane_binding": lane_binding_receipt,
        "lane_binding_sha256": _digest(current_lane),
        "source_topology": lane.SOURCE_TOPOLOGY,
        "candidate_topology": lane.CANDIDATE_TOPOLOGY,
        "selector_topology_count": 1,
        "partner_before": partner_before,
        "inventory": arm_inventory,
        "both_topologies_inventory_complete": True,
        "candidate_absent_on_both": True,
        "candidate_like_absent_everywhere": True,
        "opens_candidate_acm": False,
        "device_commands": False,
    }
    arm_receipt = observer.persist_json(run_dir / ARM_NAME, arm)
    with observer.observer_session(
        spec,
        lane.CANDIDATE_TOPOLOGY,
        run_dir,
        binding,
        class_tty=class_tty,
        dev_root=dev_root,
        usb_root=usb_root,
        max_sec=max_sec,
    ) as delegate:
        yield P324ObserverSession(
            delegate,
            spec,
            run_dir,
            current_lane,
            lane_binding_receipt,
            arm,
            arm_receipt,
            partner_before,
            class_tty,
            usb_root,
            typec_root,
        )


def _load_json(
    path: Path, label: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    def unique(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in items:
            if key in result:
                raise P324ObserverError(f"{label} has duplicate keys")
            result[key] = item
        return result

    try:
        payload, receipt = _stable_payload(path, label)
        value = json.loads(payload, object_pairs_hook=unique)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise P324ObserverError(f"{label} is unreadable") from exc
    if not isinstance(value, dict):
        raise P324ObserverError(f"{label} is not an object")
    return value, receipt


def validate_receipt(
    run_dir: Path,
    *,
    spec: dict[str, str],
    binding: dict[str, str],
    source_topology: str,
    lane_binding: dict[str, Any],
    lane_binding_receipt: dict[str, Any],
) -> dict[str, Any]:
    bound_lane = lane.validate_binding(
        lane_binding, source_topology=source_topology
    )
    base_path = run_dir / "candidate-observer.json"
    base_receipt_before = _file_receipt(
        base_path, "P324 base observer receipt"
    )
    try:
        base = observer.validate_receipt(
            base_path,
            spec=spec,
            binding=binding,
            topology=lane.CANDIDATE_TOPOLOGY,
        )
    except observer.ObserverError as exc:
        raise P324ObserverError(str(exc)) from exc
    base_receipt_after = _file_receipt(
        base_path, "P324 base observer receipt"
    )
    if base_receipt_before != base_receipt_after:
        raise P324ObserverError("P324 base observer changed while validating")
    arm_path = run_dir / ARM_NAME
    supplement_path = run_dir / SUPPLEMENT_NAME
    arm, arm_receipt = _load_json(arm_path, "P324 lane arm")
    value, supplement_receipt = _load_json(
        supplement_path, "P324 lane receipt"
    )
    expected_arm_keys = {
        "schema", "contract_id", "target", "lane_binding",
        "lane_binding_sha256", "source_topology", "candidate_topology",
        "selector_topology_count", "partner_before", "inventory",
        "both_topologies_inventory_complete", "candidate_absent_on_both",
        "candidate_like_absent_everywhere", "opens_candidate_acm",
        "device_commands",
    }
    if (
        set(arm) != expected_arm_keys
        or arm["schema"] != ARM_SCHEMA
        or arm["contract_id"] != CONTRACT_ID
        or arm["target"] != TARGET
        or arm["lane_binding"] != lane_binding_receipt
        or arm["lane_binding_sha256"] != _digest(bound_lane)
        or arm["source_topology"] != lane.SOURCE_TOPOLOGY
        or arm["candidate_topology"] != lane.CANDIDATE_TOPOLOGY
        or type(arm["selector_topology_count"]) is not int
        or arm["selector_topology_count"] != 1
        or arm["both_topologies_inventory_complete"] is not True
        or arm["candidate_absent_on_both"] is not True
        or arm["candidate_like_absent_everywhere"] is not True
        or arm["opens_candidate_acm"] is not False
        or arm["device_commands"] is not False
    ):
        raise P324ObserverError("P324 lane arm values differ")
    _validate_partner(arm["partner_before"], "P324 arm")
    arm_inventory = _validate_inventory(arm["inventory"], label="P324 arm")
    if (
        any(
            row["candidate_like_count"] != 0
            for row in arm_inventory["rows"].values()
        )
        or arm_inventory["foreign_candidate_like_count"] != 0
    ):
        raise P324ObserverError("P324 lane arm candidate absence differs")

    expected_keys = {
        "schema", "contract_id", "target", "lane_binding",
        "lane_binding_sha256", "arm", "base_observer", "source_topology",
        "candidate_topology", "selector_topology_count", "partner_before",
        "partner_after", "end_inventory", "both_topologies_inventory_complete",
        "partner_poll_count", "partner_continuous",
        "accepted_inventory_exact", "same_run_typec_partner_continuity",
        "accepted_for_p324", "opens_only_candidate_topology", "device_commands",
    }
    end_inventory = _validate_inventory(
        value.get("end_inventory"), label="P324 end"
    )
    partner_before = _validate_partner(
        value.get("partner_before"), "P324 before"
    )
    partner_after = _validate_partner(
        value.get("partner_after"), "P324 after"
    )
    source_row = end_inventory["rows"][lane.SOURCE_TOPOLOGY]
    candidate_row = end_inventory["rows"][lane.CANDIDATE_TOPOLOGY]
    accepted_inventory = (
        base["accepted"] is True
        and source_row["exact_candidate_count"] == 0
        and candidate_row["exact_candidate_count"] == 1
        and candidate_row["candidate_like_count"] == 1
        and end_inventory["foreign_candidate_like_count"] == 0
    )
    same_partner = (
        partner_before == partner_after
        and value.get("partner_continuous") is True
        and type(value.get("partner_poll_count")) is int
        and value["partner_poll_count"] > 0
    )
    accepted_for_p324 = accepted_inventory and same_partner
    if (
        set(value) != expected_keys
        or value["schema"] != SCHEMA
        or value["contract_id"] != CONTRACT_ID
        or value["target"] != TARGET
        or value["lane_binding"] != lane_binding_receipt
        or value["lane_binding_sha256"] != _digest(bound_lane)
        or value["arm"] != arm_receipt
        or value["base_observer"] != base_receipt_after
        or value["source_topology"] != lane.SOURCE_TOPOLOGY
        or value["candidate_topology"] != lane.CANDIDATE_TOPOLOGY
        or type(value["selector_topology_count"]) is not int
        or value["selector_topology_count"] != 1
        or value["partner_before"] != arm["partner_before"]
        or type(value["partner_poll_count"]) is not int
        or value["partner_poll_count"] <= 0
        or not isinstance(value["partner_continuous"], bool)
        or value["accepted_inventory_exact"] is not accepted_inventory
        or value["same_run_typec_partner_continuity"]
        is not same_partner
        or value["accepted_for_p324"] is not accepted_for_p324
        or value["both_topologies_inventory_complete"] is not True
        or value["opens_only_candidate_topology"] is not True
        or value["device_commands"] is not False
    ):
        raise P324ObserverError("P324 lane receipt values differ")
    result = dict(base) | {
        "source_topology_sha256": hashlib.sha256(
            lane.SOURCE_TOPOLOGY.removeprefix("usb:").encode("ascii")
        ).hexdigest(),
        "candidate_topology_sha256": hashlib.sha256(
            lane.CANDIDATE_TOPOLOGY.removeprefix("usb:").encode("ascii")
        ).hexdigest(),
        "lane_receipt_sha256": supplement_receipt["sha256"],
        "both_topologies_inventory_complete": True,
        "accepted_inventory_exact": accepted_inventory,
        "same_run_typec_partner_continuity": same_partner,
        "accepted_for_p324": accepted_for_p324,
    }
    if base["accepted"] is True and not accepted_for_p324:
        result["accepted"] = False
        result["exact"] = False
        result["classification"] = (
            "endpoint-ambiguous"
            if (
                source_row["exact_candidate_count"]
                + candidate_row["exact_candidate_count"]
                + end_inventory["foreign_candidate_like_count"]
                > 1
            )
            else "identity-mismatch"
        )
    return result


__all__ = [
    "CONTRACT_ID",
    "P324ObserverError",
    "SCHEMA",
    "observer_session",
    "validate_receipt",
]

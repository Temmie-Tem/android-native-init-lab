#!/usr/bin/env python3
"""P3.25 guard-node adapter for the exact P3.24 CDC-ACM observer.

P3.24 owns the S22+ lane binding, selector, and transient udev guard.  The
shared observer's read path asks that guard about the USB interface node, while
the ``ID_MM_*`` properties are attached to the tty event.  This adapter keeps
the P3.24 selector untouched and redirects only the two guard probes made by
the delegated read to the exact selected ``Endpoint.tty_class`` node.

The delegated ModemManager matcher remains authoritative and must continue to
require both ``ID_MM_DEVICE_IGNORE`` and ``ID_MM_PORT_IGNORE``.  No receipt or
classification is rewritten here: a missing pre-open flag blocks the open,
while a post-read flag loss keeps the base observer's existing exact-banner
classification semantics.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import device_action_cdc_acm_observer_v1 as observer
import s22plus_fyg8_p324_cdc_acm_observer as p324


SCHEMA = "s22plus_fyg8_p325_cdc_acm_guard_adapter_v1"
CONTRACT_ID = "s22plus-fyg8-p325-cdc-acm-guard-tty-node-v1"
BASE_CONTRACT_ID = "s22plus-fyg8-p324-cdc-acm-exact-lane-v1"
REQUIRED_MODEM_MANAGER_PROPERTIES = (
    "ID_MM_DEVICE_IGNORE",
    "ID_MM_PORT_IGNORE",
)


class P325ObserverError(ValueError):
    """The P3.25 exact guard-node adapter cannot be installed or used."""


def _validate_base_contract() -> None:
    if (
        p324.CONTRACT_ID != BASE_CONTRACT_ID
        or p324.lane.SOURCE_TOPOLOGY != "usb:2-1.3"
        or p324.lane.CANDIDATE_TOPOLOGY != "usb:3-1.3"
    ):
        raise P325ObserverError("P3.24 exact selector contract differs")


@dataclass
class GuardProbeAudit:
    """In-memory diagnostics for the two redirected guard probes.

    This is deliberately not a device-result receipt.  The P3.24 receipts and
    claim taxonomy remain authoritative; callers may use this audit in focused
    host tests or include its digest in a future, independently reviewed
    private closure.
    """

    nodes: list[Path] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.nodes)


def _validate_delegate(delegate: Any) -> None:
    if (
        delegate is None
        or not hasattr(delegate, "guard")
        or not callable(getattr(delegate.guard, "matches_node", None))
        or not callable(getattr(delegate, "_read_endpoint", None))
    ):
        raise P325ObserverError("P3.25 delegate does not expose the v1 read seam")


@contextlib.contextmanager
def adapt_delegate(delegate: Any) -> Iterator[GuardProbeAudit]:
    """Redirect only v1 read-time guard probes to ``endpoint.tty_class``.

    ``ObserverSession._read_endpoint`` calls ``guard.matches_node`` once before
    opening and once after reading.  The v1 method supplies the interface path
    in both calls.  Keeping the original method and replacing only its node
    argument preserves its raw udev capture, its requirement for both
    ModemManager ignore properties, and its existing post-capture semantics.
    """

    _validate_base_contract()
    _validate_delegate(delegate)
    original_read: Callable[..., str] = delegate._read_endpoint
    audit = GuardProbeAudit()

    def read_endpoint(
        endpoint: observer.Endpoint,
        deadline: float,
        writer: Any,
    ) -> str:
        original_matches: Callable[[Path], bool] = delegate.guard.matches_node

        def matches_node(_interface_node: Path) -> bool:
            # The v1 matcher itself requires BOTH ID_MM_DEVICE_IGNORE=1 and
            # ID_MM_PORT_IGNORE=1.  Never replace it with a one-flag check.
            tty_node = endpoint.tty_class
            audit.nodes.append(tty_node)
            return bool(original_matches(tty_node))

        delegate.guard.matches_node = matches_node
        try:
            return original_read(endpoint, deadline, writer)
        finally:
            delegate.guard.matches_node = original_matches

    delegate._read_endpoint = read_endpoint
    try:
        yield audit
    finally:
        delegate._read_endpoint = original_read


class P325ObserverSession:
    """Thin P3.25 view over the unchanged P3.24 session."""

    def __init__(self, delegate: Any, guard_probe_audit: GuardProbeAudit):
        self.delegate = delegate
        self.guard_probe_audit = guard_probe_audit

    def observe(
        self,
        *,
        timeout_sec: int,
        download_departure: dict[str, Any],
    ) -> dict[str, Any]:
        return self.delegate.observe(
            timeout_sec=timeout_sec,
            download_departure=download_departure,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self.delegate, name)


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
) -> Iterator[P325ObserverSession]:
    """Load the exact P3.24 session and install the P3.25 read seam."""

    _validate_base_contract()
    with p324.observer_session(
        spec,
        source_topology,
        run_dir,
        binding,
        lane_binding,
        lane_binding_receipt,
        class_tty=class_tty,
        dev_root=dev_root,
        usb_root=usb_root,
        typec_root=typec_root,
        max_sec=max_sec,
    ) as p324_session:
        with adapt_delegate(p324_session.delegate) as audit:
            yield P325ObserverSession(p324_session, audit)


def validate_receipt(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Validate the unchanged P3.24 receipt without changing its taxonomy."""

    return p324.validate_receipt(*args, **kwargs)


__all__ = [
    "BASE_CONTRACT_ID",
    "CONTRACT_ID",
    "GuardProbeAudit",
    "P325ObserverError",
    "REQUIRED_MODEM_MANAGER_PROPERTIES",
    "SCHEMA",
    "adapt_delegate",
    "observer_session",
    "validate_receipt",
]

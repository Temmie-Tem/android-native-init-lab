#!/usr/bin/env python3
"""Exercise P3.13 guard derivation, wrappers, and unchanged v2 behavior."""

from __future__ import annotations

import contextlib
import hashlib
import inspect
import json
from pathlib import Path
import tempfile
from unittest import mock

import device_action_cdc_acm_observer_v1 as observer
import device_action_f1_live_v2 as live
import s22plus_fyg8_p313_guard_lifetime as lifetime


SCHEMA = "s22plus_fyg8_p313_guard_lifetime_fixture_v1"
VERDICT = "PASS_P313_GUARD_LIFETIME_AND_V2_COMPATIBILITY_HOST_ONLY"


def _spec() -> dict[str, str]:
    return {
        "kind": "exact_cdc_acm_banner_v1",
        "usb_vendor_id": "04e8",
        "usb_product_id": "6861",
        "usb_serial": "S22E3" + "1" * 32,
        "usb_driver": "cdc_acm",
        "usb_interface_number": "00",
        "banner_hex": (b"S22PLUS-FYG8-E3:" + b"1" * 32 + b"\n").hex(),
    }


def _derivation() -> dict:
    return lifetime.derive(
        download_request_sec=live.DOWNLOAD_REQUEST_TIMEOUT_SEC,
        download_wait_sec=live.DOWNLOAD_WAIT_SEC,
        endpoint_revalidate_sec=live.ENDPOINT_REVALIDATE_SEC,
        odin_timeout_sec=live.ODIN_TIMEOUT_SEC,
        download_departure_wait_sec=live.DISCONNECT_WAIT_SEC,
        candidate_observation_sec=300,
        guard_default_sec=observer.GUARD_DEFAULT_MAX_SEC,
        guard_limit_sec=observer.GUARD_MAX_SEC_LIMIT,
    )


def _bundle(overlay_id: str) -> live.core.Bundle:
    return live.core.Bundle(
        {},
        {
            "manifest_id": "p313-guard-fixture",
            "candidate_ap": {"sha256": "9" * 64},
            "observation": {
                "timeout_sec": 300,
                "candidate_observer": _spec(),
                "acceptance": {
                    "userspace_overlay_contract_id": overlay_id,
                },
            },
        },
        {},
        "e" * 64,
    )


def _prepared(root: Path) -> live.PreparedRun:
    derivation = _derivation()
    approval = {
        "candidate_observer_guard_lifetime": {
            "derivation": derivation,
            "derivation_sha256": lifetime.digest(derivation),
        }
    }
    return live.PreparedRun(
        root,
        root,
        _bundle(lifetime.OVERLAY_CONTRACT_ID),
        {
            "approval_binding_sha256": "f" * 64,
            "approval_binding": approval,
        },
        {"serial": "fixture", "topology": "usb:1-1"},
    )


class _Guard:
    def __init__(self):
        self.arm_receipt = {
            "schema": observer.GUARD_SCHEMA,
            "status": "armed",
            "spec_sha256": observer.digest(_spec()),
            "topology_sha256": hashlib.sha256(b"1-1").hexdigest(),
            "rule_sha256": "2" * 64,
            "instance_sha256": "3" * 64,
            "output_sha256": "4" * 64,
            "child_alive": True,
        }

    def release(self):
        return {
            "schema": observer.GUARD_SCHEMA,
            "status": "released",
            "instance_sha256": "3" * 64,
            "returncode": 0,
            "released": True,
        }


def _v2_default_fixture(root: Path) -> dict:
    captured: list[int] = []

    def arm(_spec, _topology, _evidence_dir, *, max_sec):
        captured.append(max_sec)
        return _Guard()

    baseline = {
        "schema": observer.BASELINE_SCHEMA,
        "spec_sha256": observer.digest(_spec()),
        "topology_sha256": hashlib.sha256(b"1-1").hexdigest(),
        "identity_sha256": [],
        "exact_candidate_absent": True,
    }
    with (
        mock.patch.object(observer, "capture_baseline", return_value=baseline),
        mock.patch.object(observer.ModemManagerGuard, "arm", side_effect=arm),
    ):
        with observer.observer_session(
            _spec(), "usb:1-1", root, {"fixture": "v2"}
        ):
            pass
    arm_value = json.loads((root / "candidate-observer-guard.json").read_text())
    release_value = json.loads(
        (root / "candidate-observer-guard-release.json").read_text()
    )
    if (
        captured != [observer.GUARD_DEFAULT_MAX_SEC]
        or set(arm_value)
        != {
            "schema",
            "status",
            "spec_sha256",
            "topology_sha256",
            "rule_sha256",
            "instance_sha256",
            "output_sha256",
            "child_alive",
        }
        or set(release_value)
        != {"schema", "status", "instance_sha256", "returncode", "released"}
        or observer._guard_root_code(observer.GUARD_DEFAULT_MAX_SEC)  # noqa: SLF001
        != observer.ROOT_UDEV_GUARD_CODE
    ):
        raise RuntimeError("shared v2/default guard behavior changed")
    parameter = inspect.signature(observer.observer_session).parameters["max_sec"]
    if parameter.default != observer.GUARD_DEFAULT_MAX_SEC:
        raise RuntimeError("shared observer default lifetime changed")
    return {"default_max_sec": captured[0], "v2_shapes_unchanged": True}


def _p313_fixture(root: Path) -> dict:
    prepared = _prepared(root)
    captured: list[int] = []

    @contextlib.contextmanager
    def inner(_spec, _topology, run_dir, _binding, *, usb_root, max_sec):
        del usb_root
        captured.append(max_sec)
        observer.persist_json(run_dir / "candidate-observer-guard.json", _Guard().arm_receipt)
        try:
            yield object()
        finally:
            observer.persist_json(
                run_dir / "candidate-observer-guard-release.json", _Guard().release()
            )

    ticks = iter((1_000_000_000, 2_234_000_001))
    with (
        mock.patch.object(observer, "observer_session", new=inner),
        mock.patch.object(live.time, "monotonic_ns", side_effect=lambda: next(ticks)),
    ):
        with live._p313_candidate_observer_session(  # noqa: SLF001
            prepared, _spec(), usb_root=Path("/fixture/usb")
        ):
            pass
    if captured != [1200]:
        raise RuntimeError("P3.13 did not opt into the derived lifetime")
    reopened = live._reopen_candidate_guard_release(prepared)  # noqa: SLF001
    if reopened["status"] != "released" or reopened["released"] is not True:
        raise RuntimeError("P3.13 lifetime receipts did not reopen")
    arm = json.loads((root / live.P313_GUARD_LIFETIME_ARM).read_text())
    release = json.loads((root / live.P313_GUARD_LIFETIME_RELEASE).read_text())
    if (
        arm["derivation"]["configured_subtotal_sec"] != 880
        or arm["derivation"]["max_sec"] != 1200
        or release["elapsed_upper_millis"] != 1235
        or release["released_within_lifetime"] is not True
    ):
        raise RuntimeError("P3.13 lifetime wrapper semantics differ")

    (root / live.P313_GUARD_LIFETIME_RELEASE).unlink()
    if live._reopen_candidate_guard_release(prepared)["status"] != "invalid-or-failed":  # noqa: SLF001
        raise RuntimeError("partial P3.13 lifetime evidence was accepted")
    return {
        "configured_subtotal_sec": 880,
        "reviewed_overhead_sec": 320,
        "derived_max_sec": 1200,
        "elapsed_upper_millis": 1235,
        "partial_upgrade_rejected": True,
    }


def audit() -> dict:
    with tempfile.TemporaryDirectory(prefix="p313-guard-v2-") as name:
        v2 = _v2_default_fixture(Path(name))
    with tempfile.TemporaryDirectory(prefix="p313-guard-lifetime-") as name:
        p313 = _p313_fixture(Path(name))
    expiry = {
        "accepted_then_expired": live._observer_guard_supports_result(  # noqa: SLF001
            accepted=True, status="guard-expired", released=False
        ),
        "expired_before_banner": live._observer_guard_supports_result(  # noqa: SLF001
            accepted=False, status="guard-expired", released=False
        ),
        "normal_release": live._observer_guard_supports_result(  # noqa: SLF001
            accepted=False, status="released", released=True
        ),
    }
    if expiry != {
        "accepted_then_expired": True,
        "expired_before_banner": False,
        "normal_release": True,
    }:
        raise RuntimeError("guard expiry asymmetry changed")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "v2": v2,
        "p313": p313,
        "expiry_semantics": expiry,
    }


def main() -> int:
    try:
        result = audit()
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

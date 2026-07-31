#!/usr/bin/env python3
"""Pure marker validators for the A90 Phase 2D display F1 observer."""

from __future__ import annotations

import re


NATIVE_RELEASE_LOG_RE = re.compile(
    r"^A90D3DISPLAY native_kms_release rc=0 fd_before=[0-9]+ "
    r"disable_plane_rc=0 disable_crtc_rc=0 "
    r"munmap_failures=0 rmfb_failures=0 destroy_dumb_failures=0 "
    r"drop_master_rc=0 close_rc=0 release_complete=1$",
    re.MULTILINE,
)
MODE_RE = re.compile(r"^[1-9][0-9]*x[1-9][0-9]*@[1-9][0-9]*$")
DEVNO_RE = re.compile(r"^[1-9][0-9]*:[0-9]+$")


class ContractError(RuntimeError):
    """Raised when display evidence is not exact."""


def parse_exact_marker(text: str) -> dict[str, str]:
    if not isinstance(text, str) or not text.endswith("\n"):
        raise ContractError("marker must be newline terminated")
    result: dict[str, str] = {}
    for line in text.splitlines():
        if not line or "=" not in line:
            raise ContractError("marker contains an invalid line")
        key, value = line.split("=", 1)
        if not key or key in result or not value:
            raise ContractError("marker keys must be unique and nonempty")
        result[key] = value
    return result


def validate_native_release_evidence(log_text: str, marker_text: str) -> None:
    if NATIVE_RELEASE_LOG_RE.search(log_text) is None:
        raise ContractError("native KMS release success line is absent")
    for line in (
        "A90D3DISPLAY native_pid1_drm_fd_count=0 observed=0",
        "A90D3DISPLAY other_drm_fd_count=0 observed=0",
        "A90D3DISPLAY native_kms_initialized=0 observed=0",
        "A90D3DISPLAY display_services_restart_blocked=1 "
        "corridor=synchronous-handoff",
    ):
        if log_text.count(line) != 1:
            raise ContractError(f"native release evidence is not exact: {line}")
    marker = parse_exact_marker(marker_text)
    if marker != {
        "schema": "a90-native-display-release-v1",
        "native_pid1_drm_fd_count": "0",
        "other_drm_fd_count": "0",
        "native_kms_initialized": "0",
        "display_services_restart_blocked": "1",
        "release_complete": "1",
    }:
        raise ContractError("native release marker is not exact")


def positive_int(value: str, *, label: str) -> int:
    if not value.isdigit() or int(value) <= 0:
        raise ContractError(f"{label} must be a positive integer")
    return int(value)


def validate_debian_ready_marker(
    marker_text: str,
    *,
    display_uid: int = 3904,
    display_gid: int = 3904,
) -> dict[str, str]:
    marker = parse_exact_marker(marker_text)
    expected_keys = {
        "schema",
        "pid1_exe",
        "presenter_pid",
        "presenter_uid",
        "presenter_gid",
        "presenter_cap_eff",
        "no_new_privs",
        "controlling_vt",
        "drm_node",
        "drm_node_major_minor",
        "drm_master",
        "connector_id",
        "crtc_id",
        "mode",
        "setcrtc_rc",
        "native_pid1_drm_fd_count",
        "other_native_drm_fd_count",
        "presenter_self_drm_fd_count",
        "other_process_drm_fd_count",
        "native_init_process_count",
    }
    if set(marker) != expected_keys:
        raise ContractError("Debian display-ready marker key set is not exact")
    fixed = {
        "schema": "a90-debian-display-v1",
        "pid1_exe": "/usr/sbin/init",
        "presenter_uid": str(display_uid),
        "presenter_gid": str(display_gid),
        "presenter_cap_eff": "0000000000000000",
        "no_new_privs": "1",
        "controlling_vt": "none",
        "drm_node": "/dev/dri/card0",
        "drm_master": "1",
        "setcrtc_rc": "0",
        "native_pid1_drm_fd_count": "0",
        "other_native_drm_fd_count": "0",
        "presenter_self_drm_fd_count": "1",
        "other_process_drm_fd_count": "0",
        "native_init_process_count": "0",
    }
    for key, value in fixed.items():
        if marker.get(key) != value:
            raise ContractError(f"Debian display-ready {key} is not exact")
    positive_int(marker["presenter_pid"], label="presenter_pid")
    positive_int(marker["connector_id"], label="connector_id")
    positive_int(marker["crtc_id"], label="crtc_id")
    if DEVNO_RE.fullmatch(marker["drm_node_major_minor"]) is None:
        raise ContractError("DRM major/minor is not exact")
    if MODE_RE.fullmatch(marker["mode"]) is None:
        raise ContractError("display mode is not exact")
    return marker


def validate_bounded_failure_marker(
    marker_text: str,
    *,
    max_attempts: int = 3,
    ready_absent: bool,
) -> dict[str, str]:
    marker = parse_exact_marker(marker_text)
    if set(marker) != {"schema", "attempt", "rc"}:
        raise ContractError("display failure marker key set is not exact")
    if (
        marker["schema"] != "a90-debian-display-v1-failure"
        or marker["attempt"] != str(max_attempts)
        or not marker["rc"].isdigit()
        or int(marker["rc"]) == 0
        or ready_absent is not True
    ):
        raise ContractError("bounded display failure evidence is not terminal")
    return marker

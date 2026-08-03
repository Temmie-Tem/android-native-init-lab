#!/usr/bin/env python3
"""Phase 3 service-aware observer for the A90 D1 switch-root transaction.

The retained observer proves Debian PID1, Dropbear reachability, direct DRM,
automatic native return, and final resident health. This adapter adds one
bounded SSH read while Debian is live so the Phase 3 sysvinit-owned service
marker is also proved exactly. It performs no payload, partition, flash, or
reboot action of its own.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = SCRIPT_DIR.parent / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_v3403_f1_orchestrator as base  # noqa: E402


PROFILE = "phase3-network-ssh-v1"
READY_PATH = "/run/a90-services/ready"
FAILURE_PATH = "/run/a90-services/failure"
READY_BEGIN = "A90OBS_PHASE3_SERVICE_READY_BEGIN"
READY_END = "A90OBS_PHASE3_SERVICE_READY_END"
FAILURE_BEGIN = "A90OBS_PHASE3_SERVICE_FAILURE_BEGIN"
FAILURE_END = "A90OBS_PHASE3_SERVICE_FAILURE_END"
LIVE_BEGIN = "A90OBS_PHASE3_SERVICE_LIVE_BEGIN"
LIVE_END = "A90OBS_PHASE3_SERVICE_LIVE_END"
READY_KEYS = frozenset(
    {
        "schema",
        "owner",
        "pid1_exe",
        "ncm_ifname",
        "ncm_address",
        "ncm_peer",
        "dropbear_pid",
        "dropbear_listen",
        "dropbear_auth",
        "dropbear_forwarding",
    }
)
READY_STATIC = {
    "schema": "a90-debian-network-ssh-v1-ready",
    "owner": "debian-sysvinit",
    "pid1_exe": "/usr/sbin/init",
    "ncm_ifname": "ncm0",
    "ncm_address": "192.168.7.2/24",
    "ncm_peer": "192.168.7.1",
    "dropbear_listen": "192.168.7.2:2222",
    "dropbear_auth": "public-key-only",
    "dropbear_forwarding": "disabled",
}
POSITIVE_DECIMAL_RE = re.compile(r"^[1-9][0-9]*$")


class ContractError(RuntimeError):
    """Raised when Phase 3 live service evidence is not exact."""


def parse_exact_key_values(text: str, *, label: str) -> dict[str, str]:
    if (
        not isinstance(text, str)
        or not text
        or not text.endswith("\n")
        or "\r" in text
    ):
        raise ContractError(f"{label} marker text is not canonical")
    lines = text.splitlines()
    if not lines or any(not line or "=" not in line for line in lines):
        raise ContractError(f"{label} marker lines are malformed")
    result: dict[str, str] = {}
    for line in lines:
        key, value = line.split("=", 1)
        if not key or not value or key in result:
            raise ContractError(f"{label} marker keys are not exact")
        result[key] = value
    return result


def validate_ready_marker(text: str) -> dict[str, str]:
    marker = parse_exact_key_values(text, label="Phase 3 ready")
    if set(marker) != READY_KEYS:
        raise ContractError("Phase 3 ready marker key set is not exact")
    if any(marker.get(key) != value for key, value in READY_STATIC.items()):
        raise ContractError("Phase 3 ready marker static values changed")
    if POSITIVE_DECIMAL_RE.fullmatch(marker["dropbear_pid"]) is None:
        raise ContractError("Phase 3 ready marker Dropbear PID is not exact")
    return marker


def phase3_ssh_command(spec: base.F1Spec, args: Any) -> list[str]:
    remote_script = (
        f"echo {READY_BEGIN}; "
        f"cat {READY_PATH} 2>/dev/null; "
        f"echo {READY_END}; "
        f"echo {FAILURE_BEGIN}; "
        f"cat {FAILURE_PATH} 2>/dev/null; "
        f"echo {FAILURE_END}; "
        "dropbear_pid=; while IFS='=' read -r marker_key marker_value; do "
        "[ \"$marker_key\" = dropbear_pid ] && dropbear_pid=$marker_value; "
        f"done < {READY_PATH}; "
        "listener=$(/usr/bin/timeout 5 /usr/bin/ss -H -ltnp "
        "'sport = :2222' 2>/dev/null || true); "
        "listener_count=$(printf '%s\\n' \"$listener\" | "
        "/usr/bin/awk 'NF { count += 1 } END { print count + 0 }'); "
        "case \"$listener\" in *\"192.168.7.2:2222\"*) "
        "listener_endpoint=1 ;; *) listener_endpoint=0 ;; esac; "
        "listener_owner=\"\\\"dropbear\\\",pid=$dropbear_pid,\"; "
        "case \"$listener\" in *\"$listener_owner\"*) "
        "listener_owner_match=1 ;; *) listener_owner_match=0 ;; esac; "
        f"if [ ! -e {FAILURE_PATH} ] && [ ! -L {FAILURE_PATH} ]; then "
        "failure_absent=1; else failure_absent=0; fi; "
        f"echo {LIVE_BEGIN}; "
        "echo pid1_exe=$(readlink /proc/1/exe 2>/dev/null); "
        "echo dropbear_pid=$dropbear_pid; "
        "echo dropbear_exe=$(readlink \"/proc/$dropbear_pid/exe\" 2>/dev/null); "
        "echo listener_count=$listener_count; "
        "echo listener_endpoint=$listener_endpoint; "
        "echo listener_owner=$listener_owner_match; "
        "echo failure_absent=$failure_absent; "
        f"echo {LIVE_END}; true"
    )
    return [
        "ssh",
        "-i",
        str(spec.observer_key),
        "-p",
        str(spec.observer_port),
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        f"ConnectTimeout={int(args.ssh_connect_timeout)}",
        "-o",
        "BatchMode=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "PreferredAuthentications=publickey",
        "-o",
        "PasswordAuthentication=no",
        "-o",
        "KbdInteractiveAuthentication=no",
        f"root@{spec.observer_device}",
        remote_script,
    ]


def _classify_phase3_service_transcript(
    text: str,
    returncode: int,
) -> dict[str, Any]:
    if type(returncode) is not int or returncode != 0:
        raise ContractError("Phase 3 SSH proof command did not succeed")
    ready_text = base.exact_ssh_section(text, READY_BEGIN, READY_END)
    failure_text = base.exact_ssh_section(
        text,
        FAILURE_BEGIN,
        FAILURE_END,
    )
    live_text = base.exact_ssh_section(text, LIVE_BEGIN, LIVE_END)
    ready = validate_ready_marker(ready_text)
    live = parse_exact_key_values(live_text, label="Phase 3 live")
    if failure_text:
        raise ContractError("Phase 3 failure marker is present")
    if live != {
        "pid1_exe": "/usr/sbin/init",
        "dropbear_pid": ready["dropbear_pid"],
        "dropbear_exe": "/usr/sbin/dropbear",
        "listener_count": "1",
        "listener_endpoint": "1",
        "listener_owner": "1",
        "failure_absent": "1",
    }:
        raise ContractError("Phase 3 live process identity changed")
    return {
        "proof": True,
        "returncode": 0,
        "text": text,
        "profile": PROFILE,
        "ready_marker": ready,
        "failure_marker_absent": True,
        "pid1_live": True,
        "dropbear_live": True,
        "listener_live_exact_owner": True,
        "ssh_public_key_session": True,
    }


def validate_persisted_phase3_service(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("persisted Phase 3 service proof is not an object")
    text = value.get("text")
    returncode = value.get("returncode")
    if not isinstance(text, str):
        raise ContractError("persisted Phase 3 service transcript is not exact")
    expected = _classify_phase3_service_transcript(text, returncode)
    if value != expected:
        raise ContractError("persisted Phase 3 service proof differs from transcript")
    return expected


def observe_phase3_service(spec: base.F1Spec, args: Any) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            phase3_ssh_command(spec, args),
            cwd=base.REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=args.ssh_connect_timeout + 10.0,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "proof": False,
            "returncode": None,
            "error": {"type": "TimeoutExpired", "message": str(exc)},
        }
    text = completed.stdout + completed.stderr
    result: dict[str, Any] = {
        "proof": False,
        "returncode": completed.returncode,
        "text": text,
    }
    try:
        result = _classify_phase3_service_transcript(
            text,
            completed.returncode,
        )
    except (ContractError, base.ContractError) as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    return result


def observe_attended_after_handoff(
    spec: base.F1Spec,
    args: Any,
    transaction_dir: Path,
    pre_handoff: dict[str, Any],
    return_guard: Any = None,
) -> dict[str, Any]:
    """Run the retained attended observer plus the exact Phase 3 live proof."""

    result: dict[str, Any] = {
        "proof": False,
        "pre_handoff": pre_handoff,
        "handoff_attempt_limit": spec.handoff_attempt_limit,
    }
    try:
        result["handoff"] = base.run_handoff(spec, args)
        result["ssh"] = base.observe_ssh(spec, args)
        result["phase3_service"] = observe_phase3_service(spec, args)
        phase3_service_proven = result["phase3_service"].get("proof") is True
        facts = base.display.classify_phase2_display_facts(
            handoff_log=result["handoff"]["text"],
            native_release_marker=result["ssh"]["native_release_marker_text"],
            pid1_comm_init=result["ssh"].get("pid1_comm_init"),
            proc1_exe_init=result["ssh"].get("proc1_exe_init"),
            dropbear_started=phase3_service_proven,
            display_status=str(result["ssh"].get("display_status")),
        )
        result["facts"] = base.display.facts_to_dict(facts)
        result["native_release_proven"] = (
            facts["native_release"].state is base.display.FactState.PROVEN
        )
        result["debian_pid1_proven"] = (
            facts["debian_pid1"].state is base.display.FactState.PROVEN
        )
        result["dropbear_proven"] = (
            facts["dropbear"].state is base.display.FactState.PROVEN
        )
        result["display_status"] = result["ssh"]["display_status"]
        result["display_mechanical_proof"] = (
            result["native_release_proven"]
            and result["debian_pid1_proven"]
            and result["dropbear_proven"]
            and facts["display_acquisition"].state
            is base.display.FactState.PROVEN
        )
        result["bounded_display_failure"] = (
            facts["display_acquisition"].state is base.display.FactState.REFUTED
        )
        result["visible_confirmation_required"] = result[
            "display_mechanical_proof"
        ]
        result["phase3_service_proven"] = phase3_service_proven
    except Exception as exc:  # noqa: BLE001 - native return is still observed
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        try:
            result["candidate_return"] = base.wait_for_candidate_return_attended_once(
                spec,
                args,
                pre_handoff["return_epoch_before_handoff"],
                return_guard=return_guard,
            )
        except Exception as exc:  # noqa: BLE001 - exact recovery may resume later
            result["candidate_return_error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
            }
            result["proof"] = False
        finally:
            if return_guard is not None:
                try:
                    release = base.release_candidate_return_modemmanager_guard(
                        return_guard,
                        transaction_dir,
                    )
                except Exception as exc:  # noqa: BLE001 - preserve primary evidence
                    release = {
                        "schema": base.cdc_guard.GUARD_SCHEMA,
                        "status": "release-evidence-failed",
                        "released": False,
                        "error_type": type(exc).__name__,
                    }
                result["candidate_return_modemmanager_guard_release"] = release
                if release.get("released") is not True:
                    result.pop("candidate_return", None)
                    result["candidate_return_error"] = {
                        "type": "ContractError",
                        "message": (
                            "candidate-return ModemManager guard did not "
                            "release exactly"
                        ),
                    }
                    result["proof"] = False
        if "candidate_return" in result:
            try:
                result["retained_pmsg"] = base.collect_and_clear_retained_pmsg(
                    spec,
                    args,
                    transaction_dir,
                )
            except Exception as exc:  # noqa: BLE001 - native health is separable
                result["retained_pmsg_error"] = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
                result["proof"] = False
    base.write_private_json_exclusive(transaction_dir / "observation.json", result)
    return result

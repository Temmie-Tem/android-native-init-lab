"""Recovery-health receipt codec for prospective S20+ F1 runtimes.

No transport, filesystem writer, activation or CLI is provided. The future
owner supplies its lease-bound command capability and stores the returned
receipt privately. Validation replays the fixed collector against the receipt;
it never contacts a device and never substitutes Android health claims.
"""
from __future__ import annotations

import copy
import re

import s20plus_g986n_twrp_boot_identity_d0 as identity

SCHEMA = "s20plus_g986n_twrp_f1_health_v1"
HEX64 = re.compile(r"[0-9a-f]{64}")


def _binding(predecessor):
    if type(predecessor) is not dict:
        raise ValueError("recovery predecessor is absent")
    for key in ("serial_sha256", "topology_sha256", "boot_id_sha256"):
        if type(predecessor.get(key)) is not str or not HEX64.fullmatch(predecessor[key]):
            raise ValueError("recovery predecessor identity differs")


def _derive(predecessor, command):
    _binding(predecessor)
    observation = identity.collect(command=command, predecessor=predecessor)
    recovery = observation["recovery"]
    return {
        "schema": SCHEMA,
        "health_kind": "retained_t2_recovery",
        "target": observation["target"],
        "serial_sha256": recovery["serial_sha256"],
        "topology_sha256": recovery["topology_sha256"],
        "boot_id_sha256": recovery["current_boot_id_sha256"],
        "observation": observation,
        "android_health_verified": False,
        "boot_content_verified": False,
    }


def collect(*, predecessor, command):
    """Collect via an owner's capability; return private raw receipt and health.

    The caller must already own its guard/lease and have validated the retained
    T2 source closure. This codec supplies no such authority. The command
    capability must durably preserve bounded failure evidence before returning
    or raising; an in-memory transcript is not a failure journal. The owner
    must bind the stored receipt to its run and source closure. Raw ADB inventory,
    serial and boot IDs in the transcript require private storage.
    """
    transcript = []

    def record(argv, timeout, maximum):
        result = command(argv, timeout, maximum)
        rc, stdout, stderr = result
        if type(rc) is not int or type(stdout) is not bytes or type(stderr) is not bytes:
            raise ValueError("recovery transport result types differ")
        if len(stdout) > maximum or len(stderr) > maximum:
            raise ValueError("recovery transport result exceeds bounds")
        transcript.append({"argv": list(argv), "timeout": timeout, "maximum": maximum,
                           "returncode": rc, "stdout_hex": stdout.hex(), "stderr_hex": stderr.hex()})
        return result

    health = _derive(predecessor, record)
    return {"schema": SCHEMA + "_receipt", "predecessor": copy.deepcopy(predecessor),
            "health": health, "transcript": transcript}


def validate(receipt, *, predecessor, prior_boot_ids=()):
    """Re-derive health from exactly seven fixed exchanges without live reads."""
    _binding(predecessor)
    if (type(receipt) is not dict
            or set(receipt) != {"schema", "predecessor", "health", "transcript"}
            or receipt["schema"] != SCHEMA + "_receipt"
            or identity.canonical(receipt["predecessor"]) != identity.canonical(predecessor)
            or type(receipt["transcript"]) is not list or len(receipt["transcript"]) != 7):
        raise ValueError("recovery receipt shape or predecessor differs")
    exchanges = iter(receipt["transcript"])

    def replay(argv, timeout, maximum):
        row = next(exchanges)
        if (type(row) is not dict
                or set(row) != {"argv", "timeout", "maximum", "returncode", "stdout_hex", "stderr_hex"}
                or row["argv"] != argv or type(row["timeout"]) not in (int, float)
                or row["timeout"] != timeout or type(row["maximum"]) is not int
                or row["maximum"] != maximum or type(row["returncode"]) is not int):
            raise ValueError("recovery exchange does not match the fixed collector")
        outputs = []
        for key in ("stdout_hex", "stderr_hex"):
            value = row[key]
            if (type(value) is not str or len(value) > maximum * 2 or len(value) % 2
                    or re.fullmatch(r"[0-9a-f]*", value) is None):
                raise ValueError("recovery exchange output is invalid or oversized")
            outputs.append(bytes.fromhex(value))
        return row["returncode"], *outputs

    health = _derive(predecessor, replay)
    if identity.canonical(health) != identity.canonical(receipt["health"]):
        raise ValueError("recovery health is not transcript-derived")
    for boot_id in prior_boot_ids:
        if type(boot_id) is not str or not HEX64.fullmatch(boot_id):
            raise ValueError("prior boot identity is malformed")
        if health["boot_id_sha256"] == boot_id:
            raise ValueError("terminal recovery boot is not fresh")
    return health

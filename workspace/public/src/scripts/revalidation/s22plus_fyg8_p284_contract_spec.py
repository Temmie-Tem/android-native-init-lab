#!/usr/bin/env python3
"""P2.84 normalized sysfs token overlay for the P2.82 contract."""

from __future__ import annotations

from s22plus_fyg8_p282_contract_spec import *  # noqa: F403
import s22plus_fyg8_p282_contract_spec as p282


SCHEMA = "s22plus_fyg8_p284_contract_spec_v1"

ROLE_NONE_TOKEN = "none"
ROLE_PERIPHERAL_TOKEN = "peripheral"
CHILD_SUSPENDED_TOKEN = "suspended"
CHILD_ACTIVE_TOKEN = "active"


def sysfs_write_wire(token: str) -> str:
    if not token or "\n" in token or "\r" in token or "\0" in token:
        raise SpecError("P2.84 sysfs token is not one normalized line")  # noqa: F405
    return f"{token}\n"


ROLE_NONE_WRITE = sysfs_write_wire(ROLE_NONE_TOKEN)
ROLE_PERIPHERAL_WRITE = sysfs_write_wire(ROLE_PERIPHERAL_TOKEN)
ROLE_NONE_READBACK = ROLE_NONE_TOKEN
ROLE_PERIPHERAL_READBACK = ROLE_PERIPHERAL_TOKEN
CHILD_SUSPENDED_READBACK = CHILD_SUSPENDED_TOKEN
CHILD_ACTIVE_READBACK = CHILD_ACTIVE_TOKEN

MODE_SHOW_TOKENS = (
    ROLE_PERIPHERAL_TOKEN,
    "host",
    ROLE_NONE_TOKEN,
)
RUNTIME_STATUS_SHOW_TOKENS = (
    "error",
    "unsupported",
    CHILD_SUSPENDED_TOKEN,
    "suspending",
    "resuming",
    CHILD_ACTIVE_TOKEN,
)
EXACT_VALUE_RETRY_ERRNOS = (2, 19, 5)  # ENOENT, ENODEV, EIO

RUNTIME_STRING_CONSTANTS = tuple(
    (
        name,
        {
            "P282_ROLE_NONE_WRITE": ROLE_NONE_WRITE,
            "P282_ROLE_PERIPHERAL_WRITE": ROLE_PERIPHERAL_WRITE,
            "P282_ROLE_NONE_READBACK": ROLE_NONE_READBACK,
            "P282_ROLE_PERIPHERAL_READBACK": ROLE_PERIPHERAL_READBACK,
            "P282_CHILD_SUSPENDED_READBACK": CHILD_SUSPENDED_READBACK,
            "P282_CHILD_ACTIVE_READBACK": CHILD_ACTIVE_READBACK,
        }.get(name, value),
    )
    for name, value in p282.RUNTIME_STRING_CONSTANTS
)


def validate() -> None:
    p282.validate()
    if any(
        "\n" in token or "\r" in token or "\0" in token
        for token in (
            ROLE_NONE_READBACK,
            ROLE_PERIPHERAL_READBACK,
            CHILD_SUSPENDED_READBACK,
            CHILD_ACTIVE_READBACK,
        )
    ):
        raise SpecError("P2.84 normalized readback contains wire framing")  # noqa: F405
    if ROLE_NONE_WRITE != f"{ROLE_NONE_READBACK}\n":
        raise SpecError("P2.84 none write/readback token drifted")  # noqa: F405
    if ROLE_PERIPHERAL_WRITE != f"{ROLE_PERIPHERAL_READBACK}\n":
        raise SpecError("P2.84 peripheral write/readback token drifted")  # noqa: F405
    if MODE_SHOW_TOKENS != ("peripheral", "host", "none"):
        raise SpecError("P2.84 mode_show token set changed")  # noqa: F405
    if RUNTIME_STATUS_SHOW_TOKENS != (
        "error",
        "unsupported",
        "suspended",
        "suspending",
        "resuming",
        "active",
    ):
        raise SpecError("P2.84 runtime_status_show token set changed")  # noqa: F405
    if EXACT_VALUE_RETRY_ERRNOS != (2, 19, 5):
        raise SpecError("P2.84 exact-value retry errno policy changed")  # noqa: F405


validate()

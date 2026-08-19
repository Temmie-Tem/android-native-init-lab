#!/usr/bin/env python3
"""Read the USB role and gadget state, and nothing else.

The independent review demoted the mux hypothesis and named the stronger
frontier as `role request -> UDC bind -> DWC3 pull-up/connect -> physical host
attach`.  That frontier is currently one undivided question.  This runner splits
it with reads that have no side effect at all.

Two facts about `mode` matter and are easy to state wrongly.  It exists: the
stock USB HAL rc names `a600000.ssusb/b_sess`, `id` and `usb_data_enabled`, and
none of those three exists in this kernel because that HAL is named for `coral`,
a Pixel; the attributes that do exist come from `ATTRIBUTE_GROUPS(dwc3_msm)`
wired through `.dev_groups` and are exactly `orientation`, `mode`, `speed` and
`bus_vote`.  And it means less than its name suggests: `mode_show` calls
`dwc3_msm_get_role`, which returns DEVICE when `mdwc->vbus_active` is set and
HOST when `mdwc->id_state` is DWC3_ID_GROUND, and those are the same two fields
`dwc3_msm_set_role` assigns.  So `mode` is a faithful readback of the role the
driver has been *told* to take.  It is not evidence that the controller
negotiated anything, and it must not be reported as the controller's operating
state.

The second half comes from the UDC.  `state_show` in the gadget core returns
`usb_state_string(gadget->state)`, which advances only as the host drives
enumeration, so `not attached` against `powered`, `default`, `addressed` and
`configured` is exactly the divide the frontier needs.  `function_show` returns
the bound gadget driver's function name, or nothing when no gadget is bound,
which separates "no gadget bound" from "gadget bound, host silent".

`orientation` is deliberately not read: `orientation_show` reports
`mdwc->orientation_override`, a debug override, and not the CC orientation, so
it would answer a question nobody asked.

Every read here is side-effect free, but not for the reason first written.  The
docstring claimed every target is a `DEVICE_ATTR_RO` whose show is a plain
struct-field read, and that is false for two of them: `mode` is `DEVICE_ATTR_RW`
(`dwc3-msm-core.c:4868`), and `/config/usb_gadget/g1/UDC` is a configfs
attribute rather than a `DEVICE_ATTR` at all.  What holds is narrower and is
what the safety property actually rests on: each target is read through its
*show* path, and every one of those shows only takes a lock and copies state.
`mode_show` calls `dwc3_msm_get_role`, which reads two struct fields; the
configfs UDC show copies `gi->udc_name`, while the bind and unbind effects live
in its separate store function which this runner never reaches.  So no I2C is
issued, no latched interrupt is consumed, and nothing is written.

That also makes this weaker than the Stage B register read, which was not
side-effect free: reading `/sys/class/mxim/debug0/reg` walks 0x00-0x10 and
consumes a latched `REG_VDM_INT`.  This runner needs no acknowledgement flag
because it consumes nothing.

The UDC device carries two write-only attributes, `srp` and `soft_connect`.
`soft_connect` drives the pull-up directly.  Neither is read, neither is
written, and the safety contract proves neither name appears in the script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import device_action_d0_v2 as d0  # noqa: E402
import device_action_raw_capture_v1 as raw_capture  # noqa: E402
import s22plus_fyg8_max77705_sysfs_d0 as prior  # noqa: E402

SCHEMA = "s22plus_fyg8_p319_usb_role_state_v1"
VERSION = "s22plus-fyg8-p319-usb-role-state-v1"
VERDICT = "PASS_S22PLUS_FYG8_P319_USB_ROLE_STATE_D0"
STOP_VERDICT = "STOP_S22PLUS_FYG8_P319_USB_ROLE_STATE_D0"
DEFAULT_RUN_ROOT = Path("workspace/private/runs/s22plus-fyg8-p319-usb-role-state")
MAX_BODY_BYTES = 8 * 1024

# The controller name is not guessed.  init.target.rc:130 sets
# vendor.usb.controller to a600000.dwc3 and the vendor_boot bootconfig carries
# androidboot.usbcontroller=a600000.dwc3, so both firmware sources agree.
CONTROLLER = "a600000.dwc3"
UDC_CLASS_DIR = "/sys/class/udc"

# (key, path, why it is read).  The script is rendered from this tuple and the
# safety contract proves the script is exactly that rendering, so a path cannot
# enter the script without entering this table first.
READ_TARGETS: tuple[tuple[str, str, str], ...] = (
    (
        "role_mode",
        "/sys/bus/platform/devices/a600000.ssusb/mode",
        "dwc3_msm_get_role readback: peripheral, host or none",
    ),
    (
        "udc_state",
        f"{UDC_CLASS_DIR}/{CONTROLLER}/state",
        "usb_state_string(gadget->state): advances only as the host enumerates",
    ),
    (
        "udc_function",
        f"{UDC_CLASS_DIR}/{CONTROLLER}/function",
        "bound gadget driver's function name, empty when no gadget is bound",
    ),
    (
        "udc_current_speed",
        f"{UDC_CLASS_DIR}/{CONTROLLER}/current_speed",
        "usb_speed_string(gadget->speed): negotiated speed, UNKNOWN when none",
    ),
    (
        "udc_maximum_speed",
        f"{UDC_CLASS_DIR}/{CONTROLLER}/maximum_speed",
        "usb_speed_string(gadget->max_speed): what the controller can offer",
    ),
    (
        "udc_is_a_peripheral",
        f"{UDC_CLASS_DIR}/{CONTROLLER}/is_a_peripheral",
        "gadget->is_a_peripheral",
    ),
    (
        "udc_is_selfpowered",
        f"{UDC_CLASS_DIR}/{CONTROLLER}/is_selfpowered",
        "gadget->is_selfpowered",
    ),
    (
        "configfs_udc",
        "/config/usb_gadget/g1/UDC",
        "gi->udc_name: which UDC the g1 gadget is bound to, empty when unbound",
    ),
)
READ_PATHS = tuple(path for _, path, _ in READ_TARGETS)

# Write primitives on the same devices.  soft_connect drives the pull-up.  A
# write to the configfs UDC node is not listed here because listing it would
# match the existence test on the same path; writes are excluded structurally
# instead, by redirect_count == 0 and by the script having to equal the
# rendering of a table that contains only reads.
FORBIDDEN_TOKENS = (
    "soft_connect",
    "srp",
    "echo",
    "tee",
    "b_sess",
    "usb_data_enabled",
    "mxim",
)


class RoleStateError(RuntimeError):
    pass


def render_script(targets: tuple[tuple[str, str, str], ...] = READ_TARGETS) -> str:
    parts = [
        "printf 'role_state\\tbegin\\n'",
        f"printf 'udc_class\\tbegin\\n'",
        f"ls -1 {UDC_CLASS_DIR}",
        "printf 'udc_class\\tend\\n'",
    ]
    for key, path, _why in targets:
        parts.extend(
            [
                f"printf 'attr\\tbegin\\t%s\\n' {key}",
                f"if [ -e {path} ]; then",
                "    printf 'present\\tyes\\n'",
                "    printf 'body\\tbegin\\n'",
                f"    cat {path}",
                # The status is captured before the body is closed but reported
                # after it, so an attribute value can never be confused with the
                # status line that follows it.
                "    rc=$?",
                "    printf 'body\\tend\\n'",
                "    printf 'body_rc\\t%s\\n' \"$rc\"",
                "else",
                "    printf 'present\\tno\\n'",
                "fi",
                f"printf 'attr\\tend\\t%s\\n' {key}",
            ]
        )
    parts.append("printf 'role_state\\tend\\n'")
    return "\n".join(parts) + "\n"


ROLE_STATE_SCRIPT = render_script()

READ_COMMANDS = ("cat", "ls", "od", "head", "tail", "dd")


def role_state_safety_contract(script: str | None = None) -> dict[str, Any]:
    """Prove the script is exactly the rendering of the declared read table.

    A token lint would pass a script that read one extra path.  This asserts
    equality with the rendering, so the only way to widen what the device does
    is to widen READ_TARGETS, which is reviewable as a table.

    The parameter defaults to None rather than to ROLE_STATE_SCRIPT because a
    default argument binds once at definition time: with that binding a caller
    could contract-check the original script while sending a different one, and
    the checked text and the executed text would silently diverge.
    """
    if script is None:
        script = ROLE_STATE_SCRIPT
    lines = [line.strip() for line in script.splitlines()]
    read_lines = [line for line in lines if line.split(" ")[0] in READ_COMMANDS]
    cat_targets = [
        line.split(" ", 1)[1] for line in read_lines if line.startswith("cat ")
    ]
    ls_targets = [
        line.split(" ")[-1] for line in read_lines if line.startswith("ls ")
    ]
    value = {
        "declared_target_count": len(READ_TARGETS),
        "read_line_count": len(read_lines),
        "cat_target_count": len(cat_targets),
        "cat_targets_match_table": tuple(cat_targets) == READ_PATHS,
        "ls_targets": ls_targets,
        "redirect_count": len(re.findall(r"(?<!2)>", script)),
        "forbidden_token_hits": sorted(
            token for token in FORBIDDEN_TOKENS if token in script
        ),
        "script_equals_rendered_table": script == render_script(),
        "script_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
        "script_size": len(script.encode("utf-8")),
    }
    value["reads_only_the_declared_table"] = (
        value["script_equals_rendered_table"]
        and value["cat_targets_match_table"]
        and value["cat_target_count"] == len(READ_TARGETS)
        and value["read_line_count"] == len(READ_TARGETS) + 1
        and value["ls_targets"] == [UDC_CLASS_DIR]
        and value["redirect_count"] == 0
        and not value["forbidden_token_hits"]
    )
    value["result"] = "pass" if value["reads_only_the_declared_table"] else "fail"
    return value


def repo_root() -> Path:
    for candidate in [SCRIPT_DIR, *SCRIPT_DIR.parents]:
        if (candidate / "AGENTS.md").is_file():
            return candidate
    raise RoleStateError("repository root not found")


def allocate_run_dir(root: Path) -> Path:
    base = (root / DEFAULT_RUN_ROOT).absolute()
    base.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = base / f"d0-{stamp}-{os.urandom(6).hex()}"
    run_dir.mkdir(mode=0o700)
    return run_dir


def persist(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True).encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(path, stat.S_IRUSR)


# usb_state_string values, ch9.  The order is the enumeration order and is what
# makes a single read locate the stop rather than merely describe it.
UDC_STATES = (
    "not attached",
    "attached",
    "powered",
    "reconnecting",
    "unauthenticated",
    "default",
    "addressed",
    "configured",
    "suspended",
)


def classify(observation: dict[str, Any]) -> dict[str, Any]:
    """Locate where the chain stops, without inventing a stage it cannot see."""
    values = observation["values"]
    role = values.get("role_mode")
    state = values.get("udc_state")
    function = values.get("udc_function")
    bound = values.get("configfs_udc")

    if role is None:
        stage, reason = "unknown", "mode was not readable"
    elif role != "peripheral":
        stage, reason = (
            "role_not_peripheral",
            f"dwc3 role reads {role!r}; nothing has requested peripheral",
        )
    elif not bound:
        stage, reason = (
            "role_only",
            "role is peripheral but no gadget is bound to the UDC",
        )
    elif state in (None, ""):
        stage, reason = "unknown", "udc state was not readable"
    elif state == "not attached":
        stage, reason = (
            "bound_not_attached",
            "gadget is bound and the role is peripheral, but the UDC reports "
            "not attached, so no host has driven the bus",
        )
    elif state == "configured":
        stage, reason = (
            "configured",
            "the host completed enumeration and selected a configuration",
        )
    else:
        stage, reason = (
            "attached_not_configured",
            f"the host is driving the bus but enumeration stopped at {state!r}",
        )
    return {
        "stage": stage,
        "reason": reason,
        "role_mode": role,
        "udc_state": state,
        "udc_function": function,
        "configfs_bound_to": bound,
        "state_is_known": state in UDC_STATES if state else None,
    }


def parse_role_state(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    values: dict[str, str] = {}
    present: dict[str, str] = {}
    body_rc: dict[str, str] = {}
    udc_class: list[str] = []

    section: str | None = None
    key: str | None = None
    in_body = False
    body: list[str] = []
    for line in lines:
        row = line.split("\t")
        # Body content is claimed before any marker is considered, so an
        # attribute whose value happened to look like a marker cannot end its
        # own section or be mistaken for a scalar.
        if in_body and row != ["body", "end"]:
            body.append(line)
            continue
        if row[0] == "udc_class" and len(row) == 2:
            section = "udc_class" if row[1] == "begin" else None
            continue
        if row[0] == "attr" and len(row) == 3:
            if row[1] == "begin":
                key = row[2]
            else:
                key = None
            continue
        if row[0] == "present" and len(row) == 2 and key is not None:
            present[key] = row[1]
            continue
        if row[0] == "body" and len(row) == 2:
            if row[1] == "begin":
                in_body, body = True, []
            else:
                in_body = False
                if key is not None:
                    values[key] = "\n".join(body).strip()
            continue
        if row[0] == "body_rc" and len(row) == 2 and key is not None:
            body_rc[key] = row[1]
            continue
        if section == "udc_class" and line.strip():
            udc_class.append(line.strip())

    missing = [key for key, _, _ in READ_TARGETS if present.get(key) != "yes"]
    failed = sorted(key for key, rc in body_rc.items() if rc != "0")
    return {
        "reached_end": ["role_state", "end"] in [line.split("\t") for line in lines],
        "udc_class_entries": udc_class,
        "controller_present": CONTROLLER in udc_class,
        "present": present,
        "body_rc": body_rc,
        "values": values,
        "absent_targets": missing,
        "failed_reads": failed,
    }


def collect(root: Path) -> dict[str, Any]:
    # Resolved once, then both checked and sent, so the text the contract
    # cleared is the same object the device receives.
    script = ROLE_STATE_SCRIPT
    contract = role_state_safety_contract(script)
    if contract["result"] != "pass":
        raise RoleStateError("safety contract failed before any device contact")
    run_dir = allocate_run_dir(root)
    capture_dir = raw_capture.prepare_capture_dir(run_dir, "raw-role-state")
    adb = prior.DEFAULT_ADB
    try:
        inventory = raw_capture.acquire_command(
            [str(adb), "devices", "-l"],
            capture_dir,
            "0000-adb-inventory",
            timeout=10,
            stdout_maximum=d0.MAX_TEXT_OUTPUT,
            stderr_maximum=d0.MAX_TEXT_OUTPUT,
        )
        inventory_text = raw_capture.decode_success_stdout(
            inventory, maximum=d0.MAX_TEXT_OUTPUT, strip=False
        )
    except raw_capture.RawCaptureError as exc:
        raise RoleStateError(f"inventory failed: {exc}") from exc
    selection = prior.select_exact_s22(inventory_text)
    try:
        handle = raw_capture.acquire_command(
            [str(adb), "-s", selection.serial, "exec-out", "su", "-c", script],
            capture_dir,
            "0001-usb-role-state",
            timeout=20,
            stdout_maximum=MAX_BODY_BYTES,
            stderr_maximum=d0.MAX_TEXT_OUTPUT,
        )
    except raw_capture.RawCaptureError as exc:
        raise RoleStateError(f"raw acquisition failed: {exc}") from exc
    payload = raw_capture.read_stdout(handle, maximum=MAX_BODY_BYTES)
    stderr = raw_capture.read_stderr(handle, maximum=d0.MAX_TEXT_OUTPUT)
    observation = parse_role_state(payload.decode("utf-8", "replace"))
    frontier = classify(observation)
    # configfs is not mounted on every boot this may run against, so its absence
    # is reported rather than treated as an incomplete run.
    required = [key for key, _, _ in READ_TARGETS if key != "configfs_udc"]
    complete = (
        observation["reached_end"]
        and observation["controller_present"]
        and all(observation["present"].get(key) == "yes" for key in required)
        and not observation["failed_reads"]
        and frontier["stage"] != "unknown"
        and not handle.output_exceeded
        and not handle.timed_out
        and handle.producer_error_type is None
    )
    value = {
        "schema": SCHEMA,
        "version": VERSION,
        "verdict": VERDICT if complete else STOP_VERDICT,
        "complete": complete,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "safety": contract,
        "controller": CONTROLLER,
        "i2c_issued": False,
        "interrupts_consumed": False,
        "device_writes": False,
        "reboot_requested": False,
        "partition_transfer": False,
        "candidate_used": False,
        "f1_authorized": False,
        "live_authorized": False,
        "observation": observation,
        "frontier": frontier,
        "raw": {
            "returncode": handle.returncode,
            "timed_out": handle.timed_out,
            "output_exceeded": handle.output_exceeded,
            "producer_error_type": handle.producer_error_type,
            "stdout_bytes": len(payload),
            "stderr_bytes": len(stderr),
            "stderr_text": stderr.decode("utf-8", "replace")[:400],
            "receipt": str(handle.receipt_path),
        },
    }
    persist(run_dir / "result.json", value)
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--collect", action="store_true")
    args = parser.parse_args(argv)
    script = ROLE_STATE_SCRIPT
    contract = role_state_safety_contract(script)
    if args.validate:
        value = {
            "schema": SCHEMA,
            "version": VERSION,
            "verdict": "PASS_S22PLUS_FYG8_P319_USB_ROLE_STATE_H0_READY",
            "safety": contract,
            "controller": CONTROLLER,
            "read_targets": [
                {"key": key, "path": path, "why": why}
                for key, path, why in READ_TARGETS
            ],
            "script": script,
            "device_contact": False,
            "live_authorized": False,
        }
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0 if contract["result"] == "pass" else 2
    try:
        value = collect(repo_root())
    except (RoleStateError, prior.SysfsD0Error) as exc:
        print(f"P3.19 role state error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0 if value["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

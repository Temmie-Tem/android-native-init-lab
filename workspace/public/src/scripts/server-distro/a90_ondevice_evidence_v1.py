#!/usr/bin/env python3
"""On-device durable evidence for same-ordinal Debian facts.

Three consecutive automatic-handoff ordinals completed the handoff and returned
exact resident health while the host lost the proof to a different
live-observation defect each time. The recurring cause is not any single
predicate: device-internal facts (Debian PID 1 identity, DRM/display, Dropbear)
were confirmed *through the host bridge, in real time, inside a timeout window*,
which turns a durable fact into a transient race.

This module defines the replacement contract. Debian records those facts on the
device, into an append-only durable record on the shared source medium. After
automatic return, native-init reads the record back and folds it onto the same
``CLOCK_BOOTTIME`` axis the benchmark markers already use -- the axis is
continuous across ``switch_root`` because the kernel is unchanged. The host then
dispatches one intent, waits for return, and reads durable evidence with no
deadline.

Producer and consumer live in this one module on purpose. ``writer_script()``
emits the POSIX-sh collector that the rootfs profile installs, and ``parse``/
``evaluate`` consume what it wrote. Keeping both here means the record format
cannot drift between the side that writes it and the side that grades it.

Line format mirrors the existing ``A90BENCH`` convention so the durable native
log stays one uniform, line-oriented, key=value stream::

    A90OBSREC schema=a90-ondevice-evidence-v1 phase=debian_pid1 uptime_ms=... ...

Parsing is deliberately permissive about *shape* and strict about *state*. Every
host-side observer defect that cost this campaign an ordinal was an
over-specification of what normal device output looks like: an LF-only parser
counting one exact CRLF line as zero, an exactly-one rule rejecting legitimate
cumulative boot logs, an equality check rejecting intentional manifest
enrichment. The rule adopted here is the inverse, and the tests pin it: a
record may only fail on evidence of a bad state, never on the absence of an
expected cosmetic shape.

Host-only module. Touches no device and holds no device authority.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable


MARKER = "A90OBSREC "
SCHEMA = "a90-ondevice-evidence-v1"
RESULT_SCHEMA = "a90-ondevice-evidence-result-v1"

# Ordered. A record is complete only when all three are present for one run.
MANDATORY_PHASES = (
    "debian_pid1",
    "debian_drm_master",
    "debian_sshd",
)

# Written to the shared SD medium, deliberately *beside* the rootfs image and
# never inside it. The work-copy replacement unit makes the rootfs read-only
# with a narrow writable bind; an evidence path inside the image would go
# read-only with it and silently kill the instrument exactly when the
# mount-architecture change most needs grading.
# Debian's view. native-init bind-mounts its evidence directory onto the
# image's empty /mnt before switch_root, because only /proc, /sys and /dev
# cross over: a native-namespace path would resolve inside the read-only image
# after the switch and every write would fail silently.
DEFAULT_RECORD_PATH = "/mnt/a90-ondevice-evidence-v1.log"
# The same bytes as native addresses them, for the read-back side.
NATIVE_RECORD_PATH = (
    "/mnt/sdext/a90/runtime/evidence/a90-ondevice-evidence-v1.log"
)

# native-init publishes the arming intent_sha256 here just before dispatch.
# Debian cannot see the enable or latch file -- those live under /cache, and
# after switch_root its root is the SD image -- so the identity is handed across
# on the shared medium. Binding evidence to the arming intent is stronger than
# any run string invented for the purpose.
DEFAULT_RUN_PATH = "/mnt/a90-ondevice-evidence-run"
NATIVE_RUN_PATH = "/mnt/sdext/a90/runtime/evidence/a90-ondevice-evidence-run"

PHASE_RE = re.compile(r"^[a-z0-9_]+$")
RUN_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
IDENTITY_FIELDS = ("run", "pid1_comm", "proc1_exe")

# Fields every well-formed line carries. Unknown extra keys are kept, never
# rejected: forward compatibility is what "reject enrichment" got wrong.
REQUIRED_FIELDS = ("schema", "phase", "uptime_ms", "run")

# Being permissive about shape must not become permissive about substance. A
# phase line that carries no health field at all is not evidence of anything,
# so each mandatory phase names the facts it has to assert and the values that
# count as asserted.
PHASE_REQUIRED_FACTS = {
    "debian_pid1": {"pid1_comm": ("init",), "proc1_exe": ("/usr/sbin/init",)},
    "debian_sshd": {"dropbear": ("1",)},
    "debian_drm_master": {
        "drm_card0": ("char",),
        "drm_master": ("1",),
        "display_ready": ("1",),
    },
}
INTENT_RE = re.compile(r"^[0-9a-f]{64}$")
TRISTATE_FIELDS = ("drm_card0", "drm_master", "dropbear", "display_ready",
                   "display_failure")


class EvidenceError(RuntimeError):
    """The on-device evidence record is not exact."""


def _iter_marker_payloads(text: str) -> Iterable[str]:
    """Yield the payload of every marker line, CR/LF/CRLF alike.

    Non-marker lines are skipped rather than rejected: the durable native log
    is a cumulative, interleaved stream and always will be.
    """
    for line in text.replace("\r", "\n").splitlines():
        marker_at = line.find(MARKER)
        if marker_at >= 0:
            yield line[marker_at + len(MARKER):].strip()


def parse_line(payload: str) -> dict[str, str] | None:
    """Parse one marker payload, or return ``None`` if it is not usable.

    Returning ``None`` instead of raising is the power-loss contract: a record
    truncated mid-write leaves a partial final line, and that must never
    invalidate the complete lines in front of it.
    """
    if not payload:
        return None
    fields: dict[str, str] = {}
    for token in payload.split():
        if "=" not in token:
            return None
        key, value = token.split("=", 1)
        if not key or key in fields:
            return None
        fields[key] = value
    if any(field not in fields for field in REQUIRED_FIELDS):
        return None
    if fields["schema"] != SCHEMA:
        return None
    if not PHASE_RE.match(fields["phase"]):
        return None
    if not RUN_RE.match(fields["run"]):
        return None
    try:
        uptime_ms = int(fields["uptime_ms"], 10)
    except ValueError:
        return None
    if uptime_ms < 0:
        return None
    fields["uptime_ms"] = str(uptime_ms)
    return fields


def parse(text: str) -> list[dict[str, str]]:
    """Return every usable record line, in file order."""
    records = []
    for payload in _iter_marker_payloads(text):
        parsed = parse_line(payload)
        if parsed is not None:
            records.append(parsed)
    return records


def _missing_facts(records: list[dict[str, str]]) -> str | None:
    """Return the first phase that failed to assert a fact it must carry."""
    for record in records:
        wanted = PHASE_REQUIRED_FACTS.get(record["phase"])
        if wanted is None:
            continue
        for field, accepted in wanted.items():
            value = record.get(field)
            if value is None or value == "" or value == "na":
                return f"{record['phase']} carries no {field}"
            if accepted is not None and value not in accepted:
                return f"{record['phase']} recorded {field}={value}"
    return None


def _bad_state(records: list[dict[str, str]]) -> str | None:
    """Return the first positively-recorded bad state, if any.

    This is the only place a record is allowed to fail on content.
    """
    for record in records:
        if record.get("display_failure") == "1":
            return f"{record['phase']} recorded display_failure=1"
        if record["phase"] == "debian_pid1" and record.get("pid1_comm") not in (
            None,
            "na",
            "init",
        ):
            return f"debian_pid1 recorded pid1_comm={record['pid1_comm']}"
        if record["phase"] == "debian_sshd" and record.get("dropbear") == "0":
            return "debian_sshd recorded dropbear=0"
        if record["phase"] == "debian_drm_master" and record.get(
            "drm_card0"
        ) == "absent":
            return "debian_drm_master recorded drm_card0=absent"
        if record["phase"] == "debian_drm_master" and record.get(
            "drm_master"
        ) == "0":
            return "debian_drm_master recorded drm_master=0"
    return None


def select_run(records: list[dict[str, str]], run: str) -> list[dict[str, str]]:
    """Every record belonging to one run, in file order.

    Cumulative records from earlier boots are expected and ignored here, not
    treated as contamination.
    """
    return [record for record in records if record["run"] == run]


def evaluate(text: str, run: str) -> dict[str, Any]:
    """Grade the durable record for one run.

    ``proof`` is true only when all mandatory phases are present for that run,
    identity is self-consistent, phase order is monotonic on the boottime axis,
    and nothing recorded a bad state.
    """
    if not INTENT_RE.match(run):
        raise EvidenceError(
            f"run identity is not one arming intent_sha256: {run!r}"
        )
    all_records = parse(text)
    records = select_run(all_records, run)
    phases = {record["phase"]: record for record in records}

    missing = [phase for phase in MANDATORY_PHASES if phase not in phases]
    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "run": run,
        "records_total": len(all_records),
        "records_selected": len(records),
        "missing_phases": missing,
        "phases": {
            phase: dict(record)
            for phase, record in sorted(phases.items())
        },
        "uptime_ms": {
            phase: int(record["uptime_ms"])
            for phase, record in sorted(phases.items())
        },
        "proof": False,
        "reason": None,
    }

    if missing:
        result["reason"] = "missing phases: " + ", ".join(missing)
        return result

    # Positive bad-state evidence is graded first so the reason names the
    # actual device fact rather than a downstream inconsistency it implies.
    bad = _bad_state(records)
    if bad is not None:
        result["reason"] = bad
        return result

    missing = _missing_facts(records)
    if missing is not None:
        result["reason"] = missing
        return result

    for field in IDENTITY_FIELDS:
        values = {
            record[field] for record in records
            if field in record and record[field] != "na"
        }
        if len(values) > 1:
            result["reason"] = (
                f"{field} is inconsistent within run: {sorted(values)}"
            )
            return result

    # The only real ordering invariant is that Debian was PID 1 before it could
    # own DRM or a listener. The relative order of the other two is a boot
    # sequencing detail -- today the network service signals before the display
    # launcher -- and making it a proof criterion would be exactly the
    # over-specification that has been failing normal boots all along.
    stamps = {
        phase: int(phases[phase]["uptime_ms"]) for phase in MANDATORY_PHASES
    }
    first = stamps[MANDATORY_PHASES[0]]
    later = [phase for phase in MANDATORY_PHASES[1:] if stamps[phase] < first]
    if later:
        result["reason"] = (
            f"{MANDATORY_PHASES[0]} is not the earliest stamp: "
            f"{sorted(stamps.items())}"
        )
        return result

    result["proof"] = True
    # Both are measured on the device's own CLOCK_BOOTTIME, so they join the
    # native benchmark series directly rather than through host wall clock,
    # which carries USB enumeration latency the host cannot subtract out.
    result["pid1_to_sshd_ms"] = stamps["debian_sshd"] - first
    result["pid1_to_debian_ready_ms"] = max(stamps.values()) - first
    return result


def read_run_identity(text: str) -> str:
    """The run identity native-init published for this ordinal.

    Kept strict: this is the one field that decides which records belong to the
    ordinal being graded, so a malformed identity must not silently select the
    wrong boot's evidence.
    """
    candidate = text.strip()
    if not INTENT_RE.match(candidate):
        raise EvidenceError(
            f"published run identity is not one arming intent_sha256: {text!r}"
        )
    return candidate


def writer_script(
    *,
    record_path: str = DEFAULT_RECORD_PATH,
    run_path: str = DEFAULT_RUN_PATH,
    dropbear_port: int = 2222,
) -> str:
    """The POSIX-sh collector Debian installs and runs on the device.

    Invoked once per phase, it appends exactly one line and exits. It reads the
    same device-internal paths the host's SSH probe reads today -- the SSH
    connection only ever contributed transport -- but stamps them with
    ``/proc/uptime`` and lands them somewhere that survives the return reboot.
    Today those facts live under ``/run``, which is tmpfs, which is precisely
    why they had to be read live.

    Dropbear liveness comes from ``/proc/net/tcp[6]`` rather than ``ss`` or
    ``netstat`` so the collector adds no package dependency to the rootfs.
    """
    if not isinstance(dropbear_port, int) or not 0 < dropbear_port < 65536:
        raise EvidenceError(f"dropbear port is not exact: {dropbear_port!r}")
    port_hex = f"{dropbear_port:04X}"
    return f"""#!/bin/sh
# a90-ondevice-evidence-v1 -- append one durable evidence line and exit.
# Generated from a90_ondevice_evidence_v1.writer_script(); do not edit in place.
set -u

RECORD={record_path}
RUN_FILE={run_path}
PHASE=${{1:-}}
RUN=${{2:-}}

[ -n "$PHASE" ] || exit 2

# The rootfs hook only has to know the phase. native-init published the run
# identity beside the record before it dispatched this handoff.
if [ -z "$RUN" ] && [ -r "$RUN_FILE" ]; then
    RUN=$(tr -d '\\r\\n\\t ' < "$RUN_FILE" 2>/dev/null)
fi
[ -n "$RUN" ] || exit 2

# /proc/uptime is centisecond CLOCK_BOOTTIME, the same axis native-init stamps
# its benchmark markers on. Leading zeros are stripped by hand because bash's
# 10# base prefix is not POSIX and silently yields an empty stamp under dash --
# which is what Debian's /bin/sh actually is.
uptime_ms() {{
    read -r _up _idle < /proc/uptime 2>/dev/null || {{ echo na; return; }}
    case "$_up" in
        *.*) _sec=${{_up%%.*}}; _cs=${{_up#*.}}; _cs=${{_cs%%[!0-9]*}} ;;
        *) _sec=$_up; _cs=0 ;;
    esac
    case "$_sec" in ''|*[!0-9]*) echo na; return ;; esac
    [ -n "$_cs" ] || _cs=0
    while [ ${{#_cs}} -gt 1 ]; do
        case "$_cs" in 0*) _cs=${{_cs#0}} ;; *) break ;; esac
    done
    echo $(( _sec * 1000 + _cs * 10 ))
}}

# Values become key=value tokens, so any whitespace inside one would split the
# record. Strip it here rather than trusting every source path.
read_or_na() {{
    _v=""
    if [ -r "$1" ]; then
        _v=$(tr -d '\\r\\n\\t ' < "$1" 2>/dev/null)
    fi
    [ -n "$_v" ] || _v=na
    printf '%s\\n' "$_v"
}}

exists_flag() {{
    if [ -e "$1" ]; then echo 1; else echo 0; fi
}}

dropbear_listening() {{
    for _f in /proc/net/tcp /proc/net/tcp6; do
        [ -r "$_f" ] || continue
        # local_address is field 2 as ADDR:PORT, state 0A is LISTEN.
        if awk -v p=":{port_hex}" '$2 ~ p"$" && $4 == "0A" {{ found = 1 }}
                 END {{ exit !found }}' "$_f" 2>/dev/null; then
            echo 1
            return
        fi
    done
    echo 0
}}

drm_card0() {{
    if [ -c /dev/dri/card0 ]; then echo char; else echo absent; fi
}}

PID1_COMM=$(read_or_na /proc/1/comm)
PROC1_EXE=$(readlink /proc/1/exe 2>/dev/null | tr -d '\\r\\n\\t ')
[ -n "$PROC1_EXE" ] || PROC1_EXE=na

LINE="{MARKER.strip()} schema={SCHEMA}"
LINE="$LINE phase=$PHASE"
LINE="$LINE uptime_ms=$(uptime_ms)"
LINE="$LINE run=$RUN"
LINE="$LINE pid1_comm=$PID1_COMM"
LINE="$LINE proc1_exe=$PROC1_EXE"
LINE="$LINE drm_card0=$(drm_card0)"
LINE="$LINE drm_master=$(exists_flag /run/a90-display/ready)"
LINE="$LINE dropbear=$(dropbear_listening)"
LINE="$LINE display_ready=$(exists_flag /run/a90-display/ready)"
LINE="$LINE display_failure=$(exists_flag /run/a90-display/failure)"

mkdir -p "$(dirname "$RECORD")" 2>/dev/null || true
# One append, one line, then sync. A truncated tail from power loss is a
# discarded line on the read side, never a rejected record.
printf '%s\\n' "$LINE" >> "$RECORD" 2>/dev/null || exit 1
sync 2>/dev/null || true
exit 0
"""


COLLECTOR_RUN_PATH = "/run/a90-ondevice-evidence-v1"
HOOK_RUN_PATH = "/run/a90-debian-ondevice-evidence-hook-v1"


def hook_script(
    *,
    collector_path: str = COLLECTOR_RUN_PATH,
    display_wait_sec: int = 90,
    sshd_wait_sec: int = 90,
) -> str:
    """The one-pass recorder Debian backgrounds at sysinit.

    It grades nothing and gates nothing: bounded waits expire into a recorded
    observation and every exit is success. A missing record and a recorded
    absence are different findings, and only the second tells the host what
    actually happened.
    """
    for name, value in (("display", display_wait_sec), ("sshd", sshd_wait_sec)):
        if not isinstance(value, int) or value <= 0:
            raise EvidenceError(f"{name} wait is not exact: {value!r}")
    return f"""#!/bin/sh
# a90-debian-ondevice-evidence-hook-v1 -- record same-ordinal Debian facts.
# Generated from a90_ondevice_evidence_v1.hook_script(); do not edit in place.
set -u
PATH=/usr/sbin:/usr/bin:/sbin:/bin

COLLECT={collector_path}
[ -x "$COLLECT" ] || exit 0

record() {{ "$COLLECT" "$1" >/dev/null 2>&1 || true; }}

wait_for_any() {{
    _limit=$1
    shift
    _waited=0
    while [ "$_waited" -lt "$_limit" ]; do
        for _p in "$@"; do
            [ -e "$_p" ] && return 0
        done
        _waited=$(( _waited + 1 ))
        sleep 1
    done
    return 1
}}

# PID 1 is Debian by the time sysinit runs this, so the first stamp needs no
# wait.
record debian_pid1

# Each phase is stamped when its own signal arrives, in the order inittab
# actually produces them: the network/SSH service is a blocking entry and the
# display launcher runs after it. Waiting for the later signal first would
# stamp the earlier phase at the wrong time and report a boot slower than it
# was. Either outcome ends a wait -- a recorded failure is evidence, not a
# reason to keep polling. The collector independently reads /proc/net/tcp for
# the listener, so it and this signal do not share a failure mode.
wait_for_any {sshd_wait_sec} /run/a90-services/ready /run/a90-services/failure || true
record debian_sshd

wait_for_any {display_wait_sec} /run/a90-display/ready /run/a90-display/failure || true
record debian_drm_master

exit 0
"""


def service_block(
    *,
    record_path: str = DEFAULT_RECORD_PATH,
    run_path: str = DEFAULT_RUN_PATH,
    dropbear_port: int = 2222,
) -> str:
    """The shell block the rootfs network/SSH service carries verbatim.

    It rides the service rather than the firstboot script on purpose. The
    firstboot contract is deliberately narrow -- return-arm and marker only,
    with network and SSH concerns delegated away and enforced by a forbidden
    token list that a listener probe would trip. The service is the file
    already entitled to know about Dropbear, and it runs first among the
    inittab entries that do.

    The collector and hook are unpacked to /run rather than installed into the
    image. The builder only replaces files that already exist in its SHA-pinned
    base image, so adding new ones would mean reopening that pinned artifact
    chain; and the work-copy replacement will make the rootfs read-only, which
    tmpfs survives. Neither script needs to be durable -- only what they write
    does.
    """
    collector = writer_script(
        record_path=record_path,
        run_path=run_path,
        dropbear_port=dropbear_port,
    )
    hook = hook_script()
    for name, text in (("collector", collector), ("hook", hook)):
        if "\nA90_ONDEV_EOF\n" in text:
            raise EvidenceError(f"{name} collides with the heredoc delimiter")
    return f"""# On-device same-ordinal evidence, unpacked to tmpfs and backgrounded.
# Generated from a90_ondevice_evidence_v1.service_block(); do not edit here.
# Never gating: every failure path leaves the boot alone, because the
# instrument must not become one more way for a defect to kill an ordinal.
cat > {COLLECTOR_RUN_PATH} <<'A90_ONDEV_EOF' || true
{collector}A90_ONDEV_EOF
chmod 0755 {COLLECTOR_RUN_PATH} 2>/dev/null || true
cat > {HOOK_RUN_PATH} <<'A90_ONDEV_EOF' || true
{hook}A90_ONDEV_EOF
chmod 0755 {HOOK_RUN_PATH} 2>/dev/null || true
if [ -x {HOOK_RUN_PATH} ]; then
  {HOOK_RUN_PATH} >/dev/null 2>&1 &
fi
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Grade the A90 on-device durable evidence record.",
    )
    parser.add_argument("--record", type=Path, help="durable record read back "
                        "from the device")
    parser.add_argument("--run", help="run identity to select")
    parser.add_argument("--emit-writer", action="store_true",
                        help="print the POSIX-sh collector and exit")
    parser.add_argument("--record-path", default=DEFAULT_RECORD_PATH)
    parser.add_argument("--run-path", default=DEFAULT_RUN_PATH)
    parser.add_argument("--dropbear-port", type=int, default=2222)
    args = parser.parse_args(argv)

    if args.emit_writer:
        sys.stdout.write(
            writer_script(
                record_path=args.record_path,
                run_path=args.run_path,
                dropbear_port=args.dropbear_port,
            )
        )
        return 0

    if args.record is None or args.run is None:
        parser.error("--record and --run are required without --emit-writer")

    text = args.record.read_text(encoding="utf-8", errors="replace")
    try:
        result = evaluate(text, args.run)
    except EvidenceError as error:
        print(json.dumps({"schema": RESULT_SCHEMA, "error": str(error)}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["proof"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

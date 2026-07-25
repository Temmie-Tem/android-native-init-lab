# S22+ FYG8 P2.66 E3 pre-candidate inhibit API mismatch

## Verdict

`HOST_GUARD_API_ASSUMPTION_RULED_OUT_CANDIDATE_NOT_ATTEMPTED`

The fresh approval and execution closure matched, and the repeated D0 health
check passed. The runner then stopped at `APPROVED` while arming the host ACM
observer. It did not request Download, invoke Odin, transfer the candidate, or
transfer rollback. The device remained healthy FYG8 Android; recovery was not
required.

Private evidence records:

- state `ABORTED`;
- outcome `candidate_observer_arm_failed_before_candidate`;
- candidate classification `not-attempted`;
- four journal records ending in `run_aborted`; and
- only `live_session_start` in the canonical timeline.

The consumed approval and aborted run are not reusable.

## New Evidence

The attended root path worked. `mmcli` reached ModemManager and returned:

```text
WrongState: Modem not exported in the bus
```

The installed host uses ModemManager `1.25.95-1ubuntu1`. Its strict default
filter tags all TTYs as candidates and automatically accepts CDC-ACM
interfaces with the AT-capable interface shape. The E3 interface therefore
must be protected before it appears.

Upstream ModemManager source makes the failure deterministic:

- `mm_manager_inhibit_device()` requires a UID obtained from an existing
  exported `MMModem`;
- `base_manager_inhibit_device()` first resolves that existing device; and
- `mm_device_inhibit()` rejects a device without an exported modem object.

The source comment states why: inhibiting during port probing can split ports
between the device object and base manager. The original strategy attempted
exactly that forbidden pre-probe use. Root authorization cannot make it valid.

Source cross-check:

- ModemManager upstream commit
  `9a2d5863eb21957767dbc826b481080c08736590`;
- `src/mm-device.c`, `mm_device_inhibit()`; and
- `libmm-glib/mm-manager.c`, `mm_manager_inhibit_device()` documentation.

## Replacement Guard

The observer now uses ModemManager's documented udev exclusion mechanism
before candidate enumeration:

1. attended `pkexec` enters one root helper with parent-death `SIGTERM`;
2. the parent freezes the stdlib-only helper source and exact rule in argv,
   while `python3 -I -B -c` prevents repository imports after authorization;
3. the helper validates the decoded rule against both its SHA256 and a strict
   two-line grammar before writing one fixed file under `/run/udev/rules.d`;
4. rules match only the exact approved candidate VID, PID, serial, interface,
   and prepared physical topology;
5. the USB device receives `ID_MM_DEVICE_IGNORE=1`;
6. the TTY receives both `ID_MM_DEVICE_IGNORE=1` and
   `ID_MM_PORT_IGNORE=1`;
7. absolute-path `udevadm verify` and `udevadm control --reload` must pass
   before the helper
   emits its hash-bound arm line; and
8. release, EOF, handled termination, or a 300-second self-deadline removes
   the rule and reloads udev.

The helper refuses a pre-existing fixed rule and does not overwrite changed
content. The observer re-reads the candidate TTY's udev properties before
opening it. A missing ignore property is `guard-lost`, not success.
The exact guard is always armed regardless of the service's instantaneous
active state, so a later ModemManager activation cannot bypass preparation.

This does not stop ModemManager, modify its service or D-Bus policy, write
under `/etc` or `/usr`, or persist across host reboot. Current Android uses a
different PID and serial and cannot match the rule.

## Validation

Host validation covers:

- Python compilation;
- exact rule rendering and `udevadm verify`;
- embedded root-helper compilation and exact base64/SHA payload binding;
- exact embedded-helper execution as uid 0 in an isolated user namespace,
  proving ordered verify, arm reload, release, unlink, and cleanup reload;
- exact command, isolated Python mode, absolute privileged binaries, and
  parent-death binding;
- missing endpoint ignore properties;
- bounded private arm-failure evidence;
- release failure, timeout, and nonzero helper exit;
- raw ACM receipt validation and resume; and
- Process v2 E3 verdict and transfer-continuity integration.

The first independent review correctly returned `NO-GO` on four
execution-critical defects: the service-inactive branch could false-arm,
nonzero cleanup exit could be reported as released, root executed a
user-writable repository path after authorization, and privileged subprocess
resolution was not fully absolute. The replacement removes the branch,
requires `guard_v2/status=armed`, propagates nonzero release failure, executes
an argv-frozen `-I -B -c` helper, and uses absolute privileged binaries.

The next two delta reviews found and closed release-evidence correctness gaps:
cleanup is now reopened before `OBSERVED`, bound to a random current guard
instance, type-checks integer return code zero, participates in both normal and
resumed `C && D && A && G` proof, and cannot suppress rollback. Missing,
malformed, stale, or nonzero cleanup evidence forces
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` after exactly one rollback. The final
read-only safety review returned `GO`; 109 focused tests pass.

Repeated attended GUI smoke launches were cancelled before root code executed.
They left no runtime rule and ModemManager remained active. This is not counted
as helper validation. The required behavior is instead covered without device
contact by the exact user-namespace lifecycle test; the earlier aborted F1
already proved the production `pkexec` path reaches a root process.

No kernel, native userspace, candidate AP, rollback AP, manifest schema, Odin
wrapper, device partition, or firmware artifact changed. A new execution
closure and fresh approval are still required before another F1.

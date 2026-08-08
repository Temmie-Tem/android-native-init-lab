# A90 H7 automatic-handoff E19 incident

Date: 2026-08-09 KST
Target: Samsung Galaxy A90 5G only
Classification: `NATIVE_HANDOFF_REFUTED`, device remained `RESIDENT_HEALTHY`

## Outcome

Attended D1 run `a90-d1-attended-20260809-01` armed the installed H7 resident
once and rebooted once. Automatic handoff reached the immutable root mount,
writable tmpfs set, Debian init verification, and display marker, then returned
native with visible `BOOT ERR auto-handoff E19`. It never emitted
`mount_moves_done` or `switch_root_exec`, so Debian PID 1, SSH ownership, and
DRM/display ownership are not claimed.

The exact seven-record post-cleanup journal was finalized without another arm,
reboot, handoff, or cleanup dispatch. The terminal is
`REFUTED_AUTO_HANDOFF_NATIVE_HANDOFF_RESIDENT_HEALTHY`, with H7
`0.11.175`, self-test `11/1/0`, automatic state `binding=1 enable=1 latch=1`,
the immutable source exact, and the work path absent. Arm and reboot dispatch
counts remain one each; candidate replay, payload transfer, partition write,
flash, and rollback are zero. The private result SHA256 is
`098b0a50ea1f9cdb210d92fc9faf8a797b33eca27d172e7529adf2fd73805ea1`.
S22+ received no command.

## Cause

`E19` is `ENODEV`. The H7 native log proves `/proc` and `/sys` moved
successfully, then reports `/dev` was not a mountpoint and refuses the fallback
with `read-only-root-requires-mounted-dev`. Connected read-only inspection
confirmed that the native base boot mounts `/proc` and `/sys` but not `/dev`.
The kernel advertises `tmpfs` but not `devtmpfs`, so the ignored base
`devtmpfs` request cannot establish the mountpoint H7 expected.

The failure occurred before `/dev` movement and before `switch_root`. The moved
mounts and rootfs mount were restored, the loop was detached, the source bytes
remained unchanged, and native fallback became ready. This is a deterministic
handoff implementation defect, not an observer-only no-proof and not a device
health or recovery failure.

The host runner then exposed a second incident surface: its finalizer required
a complete benchmark even when the native log contained an exact failed
handoff. The first repair accepted that failure tail but initially inspected
only the segment selected by the generic parser. Independent review found that
a complete segment plus a second failed segment could therefore be ignored.
The final repair evaluates every appended segment, requires exactly one exact
complete-or-failed terminal segment, permits only the expected non-handoff
native-return tail after a complete segment, and rejects mixed terminal
segments in either order.

## Corrective action and retirement evidence

For a read-only root with an existing `/dev` directory, native-init now mounts
a private `tmpfs` on the new root's `/dev` before creating the bounded device
nodes and `devpts`. It never creates the `/dev` directory in the image. Failure
cleanup unmounts `devpts` before the private `/dev` tmpfs; an `execve` return
tracks and restores the same state. Existing mount propagation isolation is
retained.

Independent review returned `PASS_GO` with HIGH/MEDIUM/LOW zero at native
closure `0682012c0ef3607e33e3382eb45903828493d33a3033f30b2c22278cfd47d8a2`
and benchmark closure
`23bdeb0f7c82aa5abb3d68d2d1856e01ebe306adc0d21993a06b74f54b601a0e`.
Reviewer validation passed 267 A90 tests, Python compilation, diff checking,
and AArch64 static link, strip, and ELF inspection.

The installed H7 ordinal is terminal and must never be replayed. Its manifest
continues to bind the old native closure and the E19 refusal, so the corrected
C implementation must not be rebuilt or installed under the H7 identity. The
incident retires only after a newly versioned candidate with a new build,
rootfs destination, enable/latch namespace, immutable manifest, qualification,
review, exact D0, attended boot-only install, and one new no-replay D1 ordinal
proves `mount_moves_done`, `switch_root_exec`, exact Debian evidence, automatic
return, cleanup, and final resident health.

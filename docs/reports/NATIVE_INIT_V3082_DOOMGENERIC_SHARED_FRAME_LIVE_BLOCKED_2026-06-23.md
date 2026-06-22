# Native Init V3082 DOOMGENERIC Shared Frame Live Blocked

## Summary

- Cycle: `V3082`
- Track: active Video playback / DOOM capstone live gate.
- Candidate artifact: `workspace/private/inputs/boot_images/boot_linux_v3081_doomgeneric_shared_frame.img`
- Candidate SHA256: `f632711c57bdab2114c02a330af3125e71df0d538692b99a304c68ba32fd2150`
- Decision: `v3082-live-validation-blocked-serial-control-plane`
- Flash performed: `no`

## Gate Result

V3081 shared-frame source build and boot artifact are ready for a rollback-gated
live validation, but the flash gate did not pass. The serial command bridge is
reachable at the host process level, yet `a90ctl` command framing is losing
characters before an `A90P1 END` marker is returned.

Observed safe checks:

- Rollback boot images were present and matched the required SHA256 values for
  v2321 and v2237; final fallback v48 was present.
- Recovery/TWRP artifacts were present.
- The managed bridge wrapper could be restarted.
- TCP control over the USB network answered unauthenticated `ping`, `version`,
  and `status`.

Blocking checks:

- `a90ctl version` failed after bridge restart with no `A90P1 END` marker.
- Slow and doubled input modes still showed character loss in the command text.
- TCP control `run` and `shutdown` require authentication, and no non-serial
  token path was available in this gate.

## Decision

Do not flash V3081 until the control plane is healthy enough to run the required
post-flash `version`, `status`, and `selftest` checks. This is a separate issue
from the DOOM frame pacing path: V3079 already showed stable pageflip cadence,
and V3081 only changes frame IPC to reduce helper/presenter file churn.

## Next Unit

Recover the serial command channel first, then rerun the V3081 live gate:

1. Confirm a clean `a90ctl version`.
2. Confirm `a90ctl status`.
3. Confirm `a90ctl selftest`.
4. Only then flash the exact V3081 artifact via `native_init_flash.py` and run
   the shared-frame timing validation.

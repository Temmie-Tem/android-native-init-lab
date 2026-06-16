# NATIVE_INIT V2598 — ACDB post-init arm handover audit

Date: 2026-06-16

## Scope

Host-only audit of the operator handover requesting an `acdb_ioctl` dump that is
silent during init, arms after `acdb_loader_init_v3()` returns, then calls
`acdb_loader_send_common_custom_topology()`. No Android handoff, device action,
speaker write, or raw ACDB payload publication was performed.

## Decision

- decision: `v2598-postinit-arm-handover-superseded-by-existing-live-evidence`
- ok: `True`
- device_action: `none`
- flash_action: `none`

## Evidence

- V2562 implemented the post-init manual-arm topology helper/preload and live result
  `v2562-init-internal-topology-before-manual-arm-sigsegv` showed init entered the
  topology path before the helper could arm.
- V2576 repeated the same post-init manual-arm topology strategy and hit the same
  `init-internal-topology-before-manual-arm-sigsegv` outcome.
- V2563's alternate arm point, auto-arm immediately after `ACDB_CMD_INITIALIZE_V2`,
  captured the real `4916`-byte topology payload with SHA
  `7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89`.
- V2577 proved the common-topology entry hook can arm before the real function, but
  the real call timed out with zero `acdbtap` rows; do not rerun it unchanged.
- V2597 proved the current frontier is live direct per-device metadata:
  `acdb_ioctl(0x1122e, &0x11135, 4, out, 4) -> ret=0, out=0x10005000`.

## Conclusion

The requested post-`init_v3` manual-arm topology run is superseded by existing live
evidence and should not be rerun as written. The topology payload is already captured
and operator-verified; the meaningful next unit is per-device pure-read GET derivation
from the V2597 `0x1122e` metadata result, not another topology arm variant.

## Machine Checks

- postinit_after_init_return_should_not_be_rerun: `True`
- topology_payload_already_captured_by_v2563: `True`
- common_topology_entry_hook_should_not_be_rerun_without_new_instrumentation: `True`
- current_frontier_is_per_device_direct_get_after_v2597: `True`

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_postinit_arm_handover_audit_v2598.py tests/test_native_audio_acdb_postinit_arm_handover_audit_v2598.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_postinit_arm_handover_audit_v2598`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_postinit_arm_handover_audit_v2598.py --write-report`
- `git diff --check`

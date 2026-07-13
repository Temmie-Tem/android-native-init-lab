# S22+ FYG8 R4W1-A Connected V2 Identity Dry-Run Result

Date: 2026-07-13 KST
Scope: attended connected read-only preflight of parser-binding-fixed helper
Device write, `bugreportz`, reboot, Download transition, Odin, or flash: none

## Verdict

`PASS_R4W1A_CONNECTED_IDENTITY_DRY_RUN_READ_ONLY`

The parser-binding-fixed helper passed its fresh connected read-only gate and
created the v2 promotion record required by a future oracle-policy review.

## Exact Evidence

- source-ready commit: `950a0c3b`;
- helper SHA256:
  `a429d65a0c01a5d5e3dd2c0f328593ac6a132f33ed0928d930e389e7ad6d1a62`;
- focused test SHA256:
  `386fca45a81e723cec6ab23abe26821d98b7724bba2e10a48d8aa176ab65721e`;
- private run:
  `workspace/private/runs/s22plus_fyg8_r4w1a_connected_dry_run_20260713T085633Z`;
- result SHA256:
  `4ba372e52aaf0a5ba8d93dce6c8bb709677e70376ad5e025d40785dd40802879`;
- v2 promotion-record path:
  `workspace/private/state/s22plus_fyg8_r4w1a_connected_dry_run_pass_v2.json`;
- v2 promotion-record SHA256:
  `6db39d84d1dc855a68376f7d09a16022c2c39a581870e7331a209bf876025f16`;
- v2 promotion schema: `s22plus_fyg8_r4w1a_connected_pass_v2`.

The helper reran the independent static checker and reproduced exact result
SHA256 `fc528ba9...3a0b` with verdict
`PASS_R4W1A_THREE_REPRO_STATIC_CONTRACT` before connected evaluation.

## Device State

The run proved exact FYG8 Android identity, completed boot, stopped boot
animation, orange verified-boot state, Magisk `uid=0(root)`, known Magisk boot,
stock DTBO, stock recovery, no Odin endpoint, live `sec_log_buf`, its exact
platform bind, and EOF-complete 2,097,136-byte reads of `/proc/ap_klog` and
`/proc/last_kmsg`. Both snapshots classified the R4W1 marker family absent.

Independent post-run checks reproduced both result and promotion-record hashes.
Android remained boot-complete with Magisk root. The timeline contains only the
canonical eight `events:[{name,timestamp_utc}]` entries with explicit no-flash
phase semantics.

## Boundary

The historical v1 connected record remains preserved but is not accepted by
the current helper. The v2 record above is the only connected prerequisite for
future policy activation. Oracle consumed/PASS and candidate consumed records
remain absent.

This result does not activate oracle policy and does not authorize the capture.
Next is a separate host-only review and exact AGENTS clause activation pinned to
the v2 promotion SHA. Only after that review may a new attended oracle approval
authorize the one `bugreportz` capture. Candidate flash remains blocked.

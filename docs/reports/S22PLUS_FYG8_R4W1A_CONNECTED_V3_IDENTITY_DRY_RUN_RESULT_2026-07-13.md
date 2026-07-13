# S22+ FYG8 R4W1-A Connected V3 Identity Dry-Run Result

Date: 2026-07-13 KST
Scope: attended connected read-only preflight of activation-stable helper
Device write, `bugreportz`, reboot, Download transition, Odin, or flash: none

## Verdict

`PASS_R4W1A_CONNECTED_IDENTITY_DRY_RUN_READ_ONLY`

The activation-stable helper passed its fresh connected read-only gate and
created the v3 promotion record required by the oracle policy clause.

## Exact Evidence

- source-ready commit: `6f78610b`;
- helper SHA256:
  `d541397c823b7c6311dbec950dd3a82dc6a5881984b45838c99ffedebc2d3d14`;
- focused test SHA256:
  `314b3efc9fec555b31bf6b926bcdbe4b34ebe75ad17bf1172d0e3027e52bf145`;
- private run:
  `workspace/private/runs/s22plus_fyg8_r4w1a_connected_dry_run_20260713T091826Z`;
- result SHA256:
  `5e54811e8e3363fa372ca65e2938565e7465511b6b0e5bbe0754679ef7a5c5d3`;
- promotion path:
  `workspace/private/state/s22plus_fyg8_r4w1a_connected_dry_run_pass_v3.json`;
- promotion SHA256:
  `6b78cfb646432bb2dcb8f65a47a7e547d4b8a3862c72cb0ada2cc6237f2c4084`;
- promotion schema: `s22plus_fyg8_r4w1a_connected_pass_v3`.

The helper first reproduced independent static-checker result SHA256
`fc528ba9...3a0b` and verdict
`PASS_R4W1A_THREE_REPRO_STATIC_CONTRACT`.

## Connected Proof

The run proved exact FYG8 Android identity, boot completion, stopped boot
animation, orange verified-boot state, Magisk root, known Magisk boot, stock
DTBO/recovery, no Odin endpoint, live `sec_log_buf`, exact platform bind, and
EOF-complete 2,097,136-byte `/proc/ap_klog` and `/proc/last_kmsg` reads. Both
snapshots classified the R4W1 marker family absent.

Independent rehashing reproduced the result and promotion hashes. The timeline
contains only the canonical eight events with explicit no-flash semantics.
Android remained boot-complete with Magisk root afterward.

## Boundary

Historical v1/v2 records remain preserved and inert. Oracle consumed/PASS and
candidate consumed records remain absent. This result authorizes no capture by
itself. The exact v3 SHA must be present in a separately reviewed binding oracle
clause, followed by a fresh attended capture acknowledgement.

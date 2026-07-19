# S22+ FYG8 R4W1-C Connected PASS and Live Binding GO

Date: 2026-07-20 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Scope: one operator-approved connected read-only qualification followed by a
host-only, read-only review of the generated live-policy binding packet. No
reboot, Download transition, Odin transfer, flash, partition write, or device
write occurred.

## Connected Result

The exact connected helper completed with verdict:

`PASS_R4W1C_CONNECTED_BASELINE_READ_ONLY`

Load-bearing identities:

- PASS record:
  `workspace/private/state/s22plus_fyg8_r4w1c_connected_read_only_pass.json`,
  size `976`, SHA256
  `4b8bd44ee171341592e987171137007376dec71432df05b39a29a083c0914f20`;
- result:
  `workspace/private/runs/s22plus-r4w1c-connected-20260719T200557Z/result.json`,
  size `12821`, SHA256
  `f954c9b7238932f97d0a51c85cd5623ae2deced5b6d4c443992fb73bb0906e3a`;
- helper SHA256
  `fa4e9b0a77032fbb8b17affb2ae985b80c990b6e4b07c0ee095328cfd80516b9`;
- focused-test SHA256
  `98938da61fc6a3f95389a31f019950fa00b3e6575687aab8d1edf5d070240251`;
- connected-clause SHA256
  `35f1d2cf8b9a4b25bac108832fb3f9ec9fd37e05c1b03f9fa34eeb5367c17ffa`.

The target was one completed normal FYG8 Android instance with stopped boot
animation, orange verified-boot state, Magisk root, exact known boot, and stock
`vendor_boot`, DTBO, and recovery. Both Odin snapshots were clean-empty. The
single `/proc/ap_klog` read and both `/proc/last_kmsg` reads completed to EOF;
the two last-kmsg captures were byte-identical and all observers were free of
the R4W1 marker family. Both pstore console paths were absent. The canonical
eight-event timeline used explicit zero-action semantics for candidate and
rollback phases.

## Binding Packet

The deterministic postconnected generator emitted:

- packet SHA256
  `ed5c2c1aa4dd5744457651ce9a47ed57fef58805396e5e4fa28f6b62cf8a0446`;
- rendered-clause SHA256
  `a6ff6388dddfa171ec69e1f38ea938b169b9bc9057b5ea63bff3e04bd5d0cb82`;
- frozen live-helper SHA256
  `db52c25340c9416e0b1c70bfc109b9389cd5010995ff00a6cb66e8b4a2cc69e5`;
- frozen live-test SHA256
  `560d6aac50a6e9fc7557e3c4d2d07966ad8c801f420b2b5b3350dfcc09772402`;
- frozen inert-template SHA256
  `80a893773529c83dd677ee035cee3b0a6c32919bd98aa1bb016a9a79608e3492`.

## Independent Review

A separate `gpt-5.6-sol` high-reasoning session reopened the packet, clause,
PASS, result, every connected evidence file, all frozen sources, all candidate
and rollback artifacts, Odin, and the 9.68 GB FYG8 firmware. It reported no
HIGH, MEDIUM, or LOW findings and returned:

`BINDING GO`

The review confirmed that the evidence tree contains no symlinks, all bytes
and hashes are stable, every AP contains exactly one regular `boot.img.lz4`,
and the rendered clause is byte-exact to the frozen template substitutions.
The clause contains exactly one begin marker, one end marker, and one ACTIVE
sentinel with no unresolved placeholders.

## Decision Boundary

The exact rendered clause is cleared for a separate policy-only commit. This
report does not itself activate the live exception and authorizes no device
action. Even after policy activation, candidate execution requires the fresh
exact acknowledgement `S22PLUS-FYG8-R4W1C-DIRECT-PID1-LIVE` and every helper
preflight gate.

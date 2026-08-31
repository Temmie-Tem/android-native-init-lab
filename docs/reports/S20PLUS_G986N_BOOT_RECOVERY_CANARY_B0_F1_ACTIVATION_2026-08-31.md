# S20+ G986N boot recovery-canary B0 F1 activation record

Date: 2026-08-31

Status: **PASS_GO - EFFECTIVE ONLY AFTER SCOPED COMMIT**

## Scope

This bounded change activates one attended boot-only F1 owner for
the exact operator-owned `SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2` target. It does not activate the direct recovery-partition T0
proposal or the donor-ramdisk T1 candidate. Recovery-partition read, write, and
transfer remain forbidden and fixed at zero.

The complete activation unit consists of the S20+ registry row, binding target
contract, current goal, this record, exact owner, and its focused test. It is
effective only after independent `PASS_GO` with no unresolved finding and a
single scoped commit. Until then no connected mode may run.

## Exact activation closure

- owner:
  `workspace/public/src/scripts/revalidation/s20plus_g986n_boot_recovery_canary_b0_f1.py`;
- size: `218,203` bytes;
- SHA-256:
  `80d961e06c03f4d092efb65ba92f142ec1061227bab55d19068b1b623a69a8ad`;
- activation-normalized SHA-256:
  `cdd34821dbc2b555ccb9ce8f14dbeb6dd0ff2baa9af50deb46708684c9167788`;
- mechanical state: `B0_F1_ACTIVE = True`;
- focused test size: `48,102` bytes;
- focused test SHA-256:
  `872895bfd12277dc35c05c34fa5b2d0105e84df2e640bde1bf52f3a01b14a588`;
- focused validation: `py_compile` and 48/48 tests pass;
- active host-closure SHA-256:
  `3819e058de21ca9642eab669b10356bf36e1262eda934e6992656291ebafe17a`.

`--validate-host` returned `PASS_B0_HOST_CLOSURE_ONLY` with
`live_authority: false`. No prepare, ADB, Odin, USB transition, or device
command was run while constructing this closure.

## Bound effect and recovery

The only candidate archive member is canonical `boot.img.lz4`. The candidate
AP is `36,198,441` bytes at SHA-256
`a8ed52d314e3b0cf5820e99ecd55e97cacdbc8a943d2181886d52d42a1c177fa`.
The mandatory resident-Magisk rollback AP is `25,835,561` bytes at SHA-256
`1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2`
and likewise contains only canonical `boot.img.lz4`.

Activation grants one fresh attended `--prepare` only upon a current direct
operator request. Prepare must prove exact rooted resident health, durably
consume one Download transition, bind the exact endpoint, and emit a run-bound
15-minute approval token. Candidate transfer remains forbidden until the
operator returns that exact token. General or earlier consent is not the token.

Candidate and rollback are one-shot. Any candidate intent makes resident
rollback mandatory, and uncertainty never permits candidate replay. Every Odin
effect is tied to a fixed-environment cgroup that must be quiesced before
recovery. Automatic recovery is preferred; the bounded physical fallback still
requires its separate exact confirmation. The shared guard is released only
after a durable terminal and fresh exact resident health.

## Independent review

Independent hostile review returned `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`.
It re-derived the exact owner, normalized, and test identities; reran
`py_compile`, 48/48 focused tests, scoped diff checking, and host closure; and
checked the activation unit against the common permanent boundaries. It made
no device, ADB, Odin, or USB contact and no edit.

The activation is effective only in the complete reviewed scoped commit. That
commit creates no run, approval, candidate transfer, or unattended authority;
it only makes the fresh-prepare gate reachable. S22+, A90, and unrelated S20+
lanes remain untouched.

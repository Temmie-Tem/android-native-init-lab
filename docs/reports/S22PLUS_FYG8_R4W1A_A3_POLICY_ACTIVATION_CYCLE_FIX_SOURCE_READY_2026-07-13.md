# S22+ FYG8 R4W1-A A3 Policy Activation-Cycle Fix Source Ready

Date: 2026-07-13 KST
Scope: host-only policy-transition test correction and validation
Device contact, device write, reboot, Download transition, Odin, or flash: none

## Verdict

`PASS_R4W1A_POLICY_ACTIVATION_CYCLE_FIXED_SOURCE_READY_HOST_ONLY`

The previous source permanently asserted that the real repository's oracle and
candidate policies were inactive. A valid future ACTIVE clause would therefore
make tests fail, forcing a test hash and helper hash change and invalidating the
promotion record at activation time. That circularity is removed before any
one-shot oracle action.

## Implementation

Real-repository tests now require reported policy state to equal the helper's
exact `active_policy` result rather than hardcoding false. Two synthetic
activation tests independently prove:

- oracle activation requires an exact connected promotion-record SHA; and
- candidate activation requires an exact oracle promotion-record SHA.

Each test creates valid private records in a temporary root, supplies every
required AGENTS pin, proves the intended policy becomes active while the other
gate remains constrained, removes one load-bearing record SHA, and proves the
policy becomes inactive. No real policy was activated.

Connected promotion moved to
`workspace/private/state/s22plus_fyg8_r4w1a_connected_dry_run_pass_v3.json`
with schema `s22plus_fyg8_r4w1a_connected_pass_v3`. Historical v1 and v2
records remain preserved and inert.

## Exact Pins

- helper SHA256:
  `d541397c823b7c6311dbec950dd3a82dc6a5881984b45838c99ffedebc2d3d14`;
- focused test SHA256:
  `314b3efc9fec555b31bf6b926bcdbe4b34ebe75ad17bf1172d0e3027e52bf145`;
- inactive policy draft SHA256:
  `e7aa7c0c7679f7fbfd83913c5e9e484667fce612ea996ace4e05608ea5ceb653`.

## Validation

- Python bytecode compilation passed;
- 24 focused live-helper tests passed;
- 45 related builder, checker, marker-oracle, and live-helper tests passed;
- the complete offline helper reran the independent artifact checker and
  returned `PASS_R4W1A_LIVE_HELPER_OFFLINE_CHECK`;
- offline result recorded `device_contact=false`, `device_write=false`,
  `flash=false`, and both real policies inactive;
- `git diff --check` passed.

Claude Opus independently confirmed both activation circularities are closed,
no activation-time source or test edit remains necessary, and returned `GO`
for this host-only commit plus one fresh v3 connected read-only dry-run request.
Oracle activation and capture remain `NO-GO` until that v3 record and a separate
clause review exist.

## Next Gate

The next device unit is one fresh-ack connected read-only dry-run of the exact
helper above. It performs no `bugreportz`, device write, reboot, Download
transition, Odin transfer, or flash. Its v3 promotion SHA can then be inserted
into `AGENTS.md` without changing helper or test bytes.

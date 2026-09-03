# S20+ G986N TWRP-fastbootd census Q2 H0

Status: `CONSUMED_NO_PROOF_RETURNED_HEALTHY`

## Question

Q1 proved that exact retained T2 can create `ffs.fastboot`, mount its
FunctionFS instance, start fastbootd, expose `ep0/ep1/ep2`, retain ADB, and
return healthy. Q2 asks the remaining narrow question: can that prepared
userspace fastboot service be switched onto the fixed USB gadget and answer
four read-only `getvar` requests?

Q2 does not provide RAM boot. It sends no payload and has no flash, erase,
logical-partition, reboot, or other mutation request.

## Exact closure

- active runner: 63,723 bytes, SHA-256
  `6fa7e0fd0f03406b691b36287654178bf6ebcad1daaea8bc19ef13c958767a86`;
- activation-normalized runner SHA-256:
  `00d8853eb8d43a24424dffff5e5b5edbb9326c6cfad03b5e348a3996397ef328`;
- terminal-owner focused test: 34,011 bytes, SHA-256
  `00ef3c067db164ef6cb72501051bff8956f45ff9876e4411570e783bcdc035d2`;
- preflight script: 2,044 bytes, SHA-256
  `ce11dd0302c3bad95d5a1be5729e65e9805259cfdeb9b09fa3c64825895418f7`;
- corrected inner control: 2,244 bytes, SHA-256
  `963ddd660fbe26e383df3150cae1338958e4cf8da02980b963ae140856ab76e3`;
- launch script: 3,015 bytes, SHA-256
  `a1ff270dcda78d08df4ef8b547b0d62067e7055ea4482d1c0c09120a7cf022ef`;
- Q1 final result: 1,273 bytes, SHA-256
  `afdabd50be11120dafb73793c08bbb8b78e69a108a029c13134f6825ba53cc53`;
- Q1 consumed marker: 654 bytes, SHA-256
  `360bffd3918aa5b693eef723e130009ff6199cbf3ac95add80e40d5990b68b9c`;
- Q1 terminal-owner runner: 42,079 bytes, SHA-256
  `0f7d3c5ed460ce70ceb37aca0bc369f5ec7cb65d14695067f33c5f039a3fdc3f`.

The runner rederives the complete Q1 journal and terminal with zero device
contact. It then retains the prior exact T2 recovery, target/topology, raw-first
capture, fixed official fastboot tool, endpoint validator, four-query grammar,
no-replay guard/journal, and physical-return finalizer. Its one control change
from the consumed census is the Q1-proved create-before-mount order.

Twenty-four focused tests cover Q1 predecessor rederivation, dormancy,
normalized identity, exact script order and forbidden surface, endpoint and
preflight parsing, intent-before-effect, four-command closure, userspace-first
stopping, output bounds, journal cuts, raw-bound results, guard ownership,
physical return, terminal strictness, and contract dormancy.

Independent review returned `PASS_GO` with CRITICAL/MAJOR/MINOR `0/0/0` for
the Q1 predecessor, corrected control, common-boundary delegation, endpoint and
query closure, raw-first evidence, journal cuts, physical return, and target
isolation. Mechanical activation set `LIVE_ACTIVE=true` and rotated only the
full runner/test identities and declared status. It creates no standing
invocation: retained-T2 entry and Q2 each require a fresh direct attended
request.
Activation-only independent review returned `PASS_GO` with
CRITICAL/MAJOR/MINOR `0/0/0`, exact dormant-hash reconstruction, unchanged
normalized/scripts/predecessor/command closure, and reviewer device
contacts/writes `0/0`.

## Live result

The one-use enable intent was armed exactly once. No matching `18d1:4ee0`
fastboot interface appeared during the fixed 30-second observer window. The
stored failure hash exactly matches
`ReturnRequiredError:exact volatile fastbootd endpoint did not arrive`; no
foreign or identity-mismatched fastboot interface was classified. Entry and
getvar intent counts are zero.

Physical TWRP System return reached fresh exact healthy Android. The 1,465-byte
final result SHA-256 is
`e39a663e7eace189f6fdd1e9853efec3d7b6a0a1e68d3ace91a51fd561df5ac8`
with verdict `NO_PROOF_S20PLUS_G986N_TWRP_FASTBOOTD_Q2_RETURNED_HEALTHY`.
Replay is false, and fastboot commands, persistent writes, partition
operations, mutation commands, and cross-target commands are zero. Q2 is
consumed.

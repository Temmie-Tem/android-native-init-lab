# S20+ G986N Magisk bootstrap F1 H0 design

Date: 2026-08-13

Target: `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`

State: **H0 REVIEW PENDING - ENDPOINT SESSION CORRECTION - NO RUN APPROVAL**

## Objective

Qualify the smallest attended experiment that can answer whether the exact
Magisk-patched boot image starts normal Android with working root while
preserving the boot-only boundary. The same experiment must restore exact
stock boot before it can finish healthy. It is not a resident-root install and
does not authorize TWRP or recovery writes.

## Fixed artifacts and tools

- Candidate AP: `25,835,561` bytes, SHA-256
  `1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2`.
- Stock rollback AP: `25,671,721` bytes, SHA-256
  `48a11265a6730a6ab842b07f63cffe9cbdf1582a919b02abdaf1d2b9a2e0bd6b`.
- Each AP has exactly one deterministic regular `boot.img.lz4` member.
- Odin4: `/usr/bin/odin4`, `3,746,744` bytes, SHA-256
  `6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b`.
- ADB SHA-256:
  `05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226`.

Payloads and raw evidence remain under `workspace/private/`.

## State and recovery model

The current dormant connected prepare starts on exact healthy, root-absent
Android rather than accepting an already-present generic Download endpoint. It
creates one fixed unresolved guard, records a no-replay transition intent, sends
one exact Download reboot, and accepts only the resulting Samsung endpoint with
VID:PID `04e8:685d`, exact manufacturer/product, no USB serial string, and one
of the two private hash-bound paired-controller topologies. Only then does it
create one hash-bound private approval token. Prepare never invokes Odin with an
AP.

Execution durably records candidate intent before its only Odin session. Root
proof requires exact-target normal Android plus `su -c id` containing
`uid=0(root)`. Proof or no-proof both lead to mandatory stock rollback. The
initial Download transition and the later stock-rollback Download transition
each have one distinct durable no-replay intent and at most one ADB dispatch.
Otherwise the operator uses the physical key path. Rollback intent precedes the
rollback's only Odin session.

Uncertain candidate or rollback outcomes are never replayed. Endpoint or
observation timeout parks with the guard retained. The guard clears only after
completed stock rollback and exact normal Android health with root absent.

## Isolation and prohibited scope

The CLI exposes no arbitrary ADB, Odin, serial, device, or artifact parameter.
It accepts no BL, CP, CSC, recovery, vendor_boot, DTBO, VBMeta, super, persist,
userdata, or other partition member. It never uses fastboot, raw block access,
`dd`, format, EFS, RPMB, or fuse operations. S22+, A90, and other-target command
counts remain zero.

## Historical activation gate

Independent review returned `PASS_GO` with no unresolved finding for the exact
runner, helpers, contract, goal, report, tests, journal recovery, endpoint
pinning, root observation, and mandatory rollback closure. Dormant runner
SHA-256 was
`cb0d288a1f699b1958927c3c1307639ac63751d1c6bd5c532d974ee17d6b289b`.
Mechanical activation changed only the activation constant, normalized reviewed
hash, and named document/test assertions. Active runner SHA-256 is
`211e001c492930c4490405ace09a6203980bf4092d276dcd018171624a16e887`;
normalized reviewed identity is
`73e8800248796a542c4d9d63acbfb641302dc12fe79b14d30b23771b6bbfb23b`.

Activation does not approve a run. Live use still requires a fresh connected
prepare and the operator's exact approval token while attended. It grants no
resident root, arbitrary Odin/artifact, non-boot partition, S22+, or A90
authority.

## Historical Download-profile correction

Three connected prepare attempts failed closed before any candidate/rollback
intent or Odin AP transfer. Passive host kernel evidence then established the
reason: exact VID:PID `04e8:685d` and absent USB serial were correct, but the
device's Download product is `SM8250`, not the assumed generic label. Link
renegotiation also exposed the same physical port through two exact paired-
controller topology identities. The correction closes the product to `SM8250`
and accepts only their SHA-256 identities. Raw topology remains private. It does not generalize
to another port, VID/PID, product, serial-bearing endpoint, artifact, or target.
Independent review and a fresh mechanical activation are required before
another connected prepare.

Independent correction review returned `PASS_GO` with no unresolved finding.
Dormant corrected runner SHA-256 was
`e3c0e3236d13227fd5321d348f8eb21c3f9b67d6ab7572a405735e2043c94edd`;
mechanically activated runner SHA-256 is
`d2447b21b1ab22b4def7ae309220d508e66b9de6064cc5fde702870758322976`,
with normalized reviewed identity
`f85505049b899be56df0e79b95092c13afd8deaa885befce03c8e0736d1b4407`.
This activates only fresh connected prepare; no run or transfer is approved.

## Pre-effect approved-execute stop

The first exactly approved execute exited fail-closed before candidate intent,
raw Odin output, candidate result, or partition transfer. Host-only inspection
confirmed the prepared binding, artifacts, transition evidence, and runner
closure still matched. The remaining reject was equality between the
prepare-time USB character-device inode/devnum and a freshly enumerated node.
Those values are intentionally ephemeral across Download re-enumeration and
are already pinned immediately before and checked immediately after each Odin
dispatch.

The proposal to accept a fresh generic matching endpoint without prepare-time
identity equality was rejected because it could transfer approval to another
Samsung SM8250 Download device on the same port.

The current dormant correction implements the required single-session design.
Prepare begins on exact healthy, root-absent Android, records a durable
no-replay intent with hashed serial/topology/boot ID, dispatches one Download
reboot, and observes the exact Download profile and allowed paired-controller
topology before producing an approval. The approval binds the complete observed
character-device identity. Execute accepts only the unchanged complete endpoint
record. Missing observation, reboot uncertainty, endpoint replacement, or
re-enumeration produces no approval or no transfer and retains the guard after
the transition intent.

The dormant runner SHA-256 is
`23c6f019c0ea6020c21de68b331e461b395a4693fd341c83209ee032a20d340c`;
its normalized SHA-256 is
`57e7fd9dfd61422c64eac5744cf8a3175b9456206b24c6c7d510e94bafcafcc0`.
Focused host tests pass, but independent review has not qualified this changed
execution-critical closure. `F1_ACTIVE` remains false and there is no current
run approval or live flash authority.

Independent review returned `PASS_GO` only for the host-only pre-effect abandon
finalizer. It is pinned to the exact old binding SHA-256
`0e299f6f05c9846cb8584aef161c109a9bdf1007a5cf642a8c9589e46255c859`
and old runner hashes, requires the exact prepared event and no other directory
node of any type, writes a durable zero-effect receipt, then clears the guard.
It refuses any candidate/rollback intent, raw log, result, symlink, special
node, or extra entry. F1 remains suspended and the old approval is not reusable.

# S20+ G986N Magisk bootstrap F1 H0 design

Date: 2026-08-13

Target: `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`

State: **PASS_GO - FIRST MAGISK ROOT PROVEN; STOCK ROLLBACK HEALTHY**

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

The current active connected prepare starts on exact healthy, root-absent
Android rather than accepting an already-present generic Download endpoint. It
first records an empty Download-endpoint baseline, then creates one fixed
unresolved guard and a no-replay transition intent, sends one exact Download
reboot, and accepts only a single endpoint that appears after that baseline with
VID:PID `04e8:685d`, exact manufacturer/product, no USB serial string, and one
of the two private hash-bound paired-controller topologies. Only then does it
create one hash-bound private approval token. Prepare never invokes Odin with an
AP.

Execution durably records candidate intent before its only Odin session. Root
proof requires exact-target normal Android plus `su -c id` containing
`uid=0(root)`. Proof or no-proof both lead to mandatory stock rollback. The
initial Download transition and the later stock-rollback Download transition
each have one distinct durable no-replay intent and at most one ADB dispatch.
If candidate Android does not return or rollback-mode dispatch is uncertain, the
runner stops. Recovery then requires a two-step attended physical handoff: an
empty endpoint baseline is recorded first, the operator uses the physical key
path, and a second explicit confirmation binds one newly observed endpoint
before the rollback's only Odin session. There is no automatic generic-endpoint
fallback.

The explicit physical recovery CLI is `--confirm-rollback-mode`. Its first
confirmation `S20PLUS-G986N-PHYSICAL-ROLLBACK-ARM` records an empty endpoint
baseline and durable handoff intent without sending Odin. After the operator
uses the physical key path, the second confirmation
`S20PLUS-G986N-PHYSICAL-ROLLBACK-CONFIRM` observes exactly one endpoint once,
binds it to the handoff evidence, and permits only the one stock rollback
transfer. Wrong confirmation, stale/multiple endpoints, missing candidate
evidence, or any existing rollback intent fails closed.

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

The current active correction implements the required single-session design.
Prepare begins on exact healthy, root-absent Android, records an empty Download
baseline and a durable no-replay intent with hashed serial/topology/boot ID,
dispatches one Download reboot, and observes the exact Download profile and
allowed paired-controller topology after that baseline before producing an
approval. The approval binds the observed character-device identity. Execute
accepts only unchanged path, endpoint hash, `st_dev`, inode, `st_rdev`,
topology, and USB profile; mutable `ctime_ns` is observational. It refreshes
and pins the complete identity immediately before Odin, then validates the
rollback-mode baseline, intent, and result before waiting for arrival. Linux
USB device-node addresses are ephemeral across re-enumeration, so a changed
endpoint is recorded as durable candidate re-enumeration evidence and stops
before any Odin transfer. It cannot be silently generalized to another phone
sharing the same profile and port. An attended `--confirm-candidate-endpoint`
handoff with the exact token
`S20PLUS-G986N-CANDIDATE-ENDPOINT-REENUM-CONFIRM` may observe that recorded
endpoint once and authorize the sole candidate transfer; any further change,
missing observation, or ambiguity fails closed and retains the guard. Physical
recovery continues to use only the separate two-step rollback handoff CLI and
never waits for or chooses a generic endpoint automatically.

The active runner SHA-256 is
`fe86f61166a7f719678ca74431abb0de4f1638ead514289f973601f5b47c4cda`;
its normalized SHA-256 is
`6ceec9037dad1e486450a7fc1085aeb5e527b1e3d1ec7420ac6aa23f03bb823e`.
Focused host tests and independent review pass for this changed
execution-critical closure. `F1_ACTIVE` is true and there is no current run
approval; a fresh prepare must issue the exact approval token before any Odin
transfer. The current connected run that encountered endpoint re-enumeration
was stopped before candidate intent and remains in guarded pending state; its
old approval is not reusable after this host correction.

## Generic pre-candidate abort activation

Status: **PASS_GO - ACTIVE**

The proportionality audit found that the existing shared guard correctly
blocks a competing experiment but also blocks the safe normal-return closure
of its own pre-candidate run. The reviewed `--abort-pre-candidate` path fixes
only that ownership defect. It requires the exact guarded prepared run and
initial transition, accepts no candidate/rollback/transfer evidence, and keeps
the partition-transfer count at zero.

When exact healthy Android is already present, the path sends no Odin command;
it performs a bounded exact-target health read, proves serial/topology
continuity and a changed boot ID, writes a durable close receipt, and releases
the guard. When the phone is still in Download, it may issue exactly one
payload-free `odin4 --reboot -d` to the same profile/topology and then performs
the same health closure. That control dispatch is no-replay. A resumed
invocation performs health observation only.

Independent host-only review found no unresolved blocker. Activation does not change
candidate/rollback artifacts, candidate intent as the no-replay boundary,
mandatory rollback after candidate execution, TWRP/recovery exclusions, or
S22+/A90 isolation.

Reviewed dormant runner SHA-256:
`81ac97471d4155a35cbb2fe98a4c81d98b63da0cd81b1019dd2a91e5806db93b`.
Dormant normalized reviewed identity:
`c8c95150be76e7cde100db23a47a9fc30bc8fb836e1e92a44bcd94771f78c43e`.
Active runner SHA-256:
`11ca8aaef183e76c6eeec1a43e75b00bbc14e4b51650e3122c8f4bbdfdc8799f`.
Active normalized reviewed identity:
`457c6c9c06a70b431a0c352d7707c1d421bbe89f190667eb2eab608cab49c57e`.

## Candidate late-observation recovery

The current candidate was transferred once. Odin returned success and its raw
output classified as completed; the only pre/post endpoint change was
`ctime_ns`. The predecessor runner conservatively stored the candidate outcome
as uncertain and therefore did not perform its Android/root observation. A
later exact-target `su -c id` read returned `uid=0(root)` in the Magisk SELinux
domain, establishing that the candidate booted rooted Android. That interactive
read is not used as terminal journal evidence.

The reviewed recovery path revalidates the complete historical candidate
journal, repeats bounded exact-target health and root observation, and durably
records that late observation. A recovery-continuation receipt binds the exact
predecessor and current runner identities before any rollback-mode intent. The
path then sends no candidate transfer and performs only the already-mandatory
one stock-boot rollback. Ctime-only endpoint changes are accepted only when
path, endpoint hash, device, inode, `st_rdev`, topology, and USB profile remain
unchanged; all other drift remains uncertain and no-replay.

The attended recovery completed with verdict
`PASS_S20PLUS_G986N_MAGISK_ROOT_PROVEN_STOCK_ROLLBACK_HEALTHY`. The durable late
observation proved root, the stock rollback transfer completed exactly once,
and final exact-target Android health proved a changed boot ID and root absence
with `su` returning the expected `127`. Candidate and rollback intent/event
counts are each exactly one, both replay permissions are false, the S22+/A90
command counts are zero, and the shared guard is absent. The operator performed
a factory reset during the stock return; no additional Odin transfer was
needed. Private receipt SHA-256 values are: recovery result
`f4cad9dcf5c0b147395e48db6b009d6abb3ac8e09c064a0b6e2885e76d53a8db`,
late candidate observation
`a6e0236d8808f973a9a3063b7656e61bfaa12ee9afb358da3e5f8440550c4071`,
recovery continuation
`29470c0c4b82f261f5a8582367304cb7c8a0d1d1d46f6e064cc12b24faead1ca`,
and rollback result
`acf4049ed16bef1b80c8f0fcf00d2253f634dad621c101f6c505f4c5887040f0`.

Operator observation: after both the patched-boot transfer and the later stock-
boot transfer, the first normal boot fell back to recovery with a boot-failure
condition. In each direction a recovery factory reset allowed normal Android to
boot. This symmetric behavior does not by itself prove that either boot image
is mismatched; it is also consistent with `/data` encryption, metadata, or
mount-state incompatibility exposed by the boot transition. The destructive
reset removed the best pre-reset failure evidence, so root cause remains
`UNCLASSIFIED`. Future resident-root work must treat a factory reset as an
expected attended recovery possibility, collect recovery logs before reset,
and must not infer boot-image mismatch from this run alone.

The next approved run exposed that repeated Odin enumeration can update only
the USB character node's `ctime_ns` while path, `st_dev`, inode, `st_rdev`,
topology, and USB profile remain identical. Candidate intent and transfer were
still absent. The P1 correction excludes only `ctime_ns` from long-lived
session equality, refreshes the full identity immediately before dispatch, and
records an exact pre-candidate runner-rotation receipt before allowing the
already-approved run to continue. Stable-field drift still fails closed.

Before the next fresh prepare, the shared `device_action_f1_v2.py` closure was
rotated to SHA-256
`4e61a7511cc2ed103d1cac4d1afdd2c91d6edc41e30d9bc2832229286d9ee290`.
The byte delta adds only S22+ P3.18 overlay-selection branches; S20+ calls only
the unchanged Odin-output classifier. The first prepare attempt rejected this
host drift before allocating a run, writing a guard, or transitioning the
device.

The pending run was then finalized through the exact healthy-Android branch.
No Odin command was sent, the partition-transfer count remained zero, no
candidate or rollback evidence existed, both replay permissions are false,
and the owning shared guard was released only after the terminal receipt. The
private receipt SHA-256 is
`c50a7e619015bd5061585adcbdedf6d8f3000e23b10c3e6a67f945e006ac470d`.

The one named prepared run that had already completed the initial Download
transition but never created a candidate intent is closable only through
`--close-pre-candidate`. That finalizer is bound to approval/binding
`dfb6aab5ebfcc88aa516e0463b79cb5458abf26c54177a7a1f6a6fd9d3e734f4`, requires
the exact historical runner closure, the six expected journal nodes, no
candidate/rollback/raw transfer evidence, and a fresh exact Android
health/root-absence read. It requires the exact serial/topology and a changed
boot ID after the recorded Download transition, then writes a durable close receipt before releasing
the guard. It is not a retry or a general abandonment path.

The later named run `9bc9b25e4299126b239541b7808135ea5a55367543b44dc2fa5ba787a60b80d9`
has a separate `--close-endpoint-uncertain` host repair. It accepts only that
binding with the historical runner closure, the exact seven regular journal
files plus `events/`, the durable endpoint-uncertain result, and no candidate,
rollback, or raw transfer evidence. It requires a fresh exact Android
serial/topology match, a changed boot ID, and root absence before writing its
receipt and releasing the guard. It never retries endpoint discovery or calls
Odin.

## Current activation record

Independent review returned `PASS_GO` with no unresolved finding for the
single-session correction, baseline/arrival binding, no-follow evidence reads,
candidate-observation state gate, physical handoff, and mandatory rollback.
Mechanical activation changed only `F1_ACTIVE`, the normalized runner identity,
the exact registry row, and these named status/hash assertions. It grants only
one attended boot-only candidate transfer followed by the mandatory stock
rollback. It grants no resident root, TWRP, recovery write, arbitrary Odin,
non-boot partition, S22+, or A90 authority.

Independent review returned `PASS_GO` only for the host-only pre-effect abandon
finalizer. It is pinned to the exact old binding SHA-256
`0e299f6f05c9846cb8584aef161c109a9bdf1007a5cf642a8c9589e46255c859`
and old runner hashes, requires the exact prepared event and no other directory
node of any type, writes a durable zero-effect receipt, then clears the guard.
It refuses any candidate/rollback intent, raw log, result, symlink, special
node, or extra entry. The old approval is not reusable.

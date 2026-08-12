# S20+ G986N Magisk bootstrap F1 H0 design

Date: 2026-08-13

Target: `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`

State: **PASS_GO - CORRECTED CAPABILITY ACTIVE - NO RUN APPROVAL**

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

Connected prepare is endpoint enumeration only. It accepts one Samsung
Download endpoint with VID:PID `04e8:685d`, expected manufacturer/product, no
USB serial string, and the previously bound private topology. It creates one
fixed unresolved guard and one hash-bound private approval token. Prepare does
not invoke Odin with an AP.

Execution durably records candidate intent before its only Odin session. Root
proof requires exact-target normal Android plus `su -c id` containing
`uid=0(root)`. Proof or no-proof both lead to mandatory stock rollback. The
runner sends at most one `adb reboot download`; otherwise the operator uses the
physical key path. Rollback intent precedes the rollback's only Odin session.

Uncertain candidate or rollback outcomes are never replayed. Endpoint or
observation timeout parks with the guard retained. The guard clears only after
completed stock rollback and exact normal Android health with root absent.

## Isolation and prohibited scope

The CLI exposes no arbitrary ADB, Odin, serial, device, or artifact parameter.
It accepts no BL, CP, CSC, recovery, vendor_boot, DTBO, VBMeta, super, persist,
userdata, or other partition member. It never uses fastboot, raw block access,
`dd`, format, EFS, RPMB, or fuse operations. S22+, A90, and other-target command
counts remain zero.

## Activation gate

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

## Connected prepare correction

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

# S22+ first native baseline roundtrip H0 — 2026-09-10

## Bounded result

Internal **P383 / v0.2.0-rc.1** implements the first attended qualification:
Android → N → Download → the same N → fresh native health → Download → A →
final rooted FYG8/original-partition Android health. Device execution is pending;
no native baseline adoption or new live proof is claimed. P382/v0.1.2 remains
consumed, closed and unchanged.

The [common exception](../operations/S22PLUS_NATIVE_ROUNDTRIP_FIRST_QUALIFICATION_V1.md)
expressly specializes the permanent same-candidate repeat rule for one declared
restoration role. Relabelling N as rollback would not have authorized it.
The change retains boot-only payloads, exact target/rollback identities,
physical attendance, private evidence and the permanent installation claim.

## Implementation

The existing F1 owner handles initial installation and Android cleanup. The
new `s22plus_native_roundtrip_owner_v1.py` binds the three roles before approval
and owns the single exceptional restoration, using the same boot-only archive,
Odin, endpoint and bounded raw/receipt machinery. The second arrival has its
own immutable intent/delivery, observer guard/raw streams, CONTROL intent and
Download window. It cannot become an independent ordinary candidate run.

A fixed native-health EXEC proves numeric root, PID1 parentage, real proc/sys/dev
mounts, complete binary stdout/stderr and terminal status, followed by idle
STATUS. The second authenticated kernel boot identity and challenge must both
change before its CONTROL. A new challenge alone is insufficient. CONTROL ACK
remains acceptance-only; exact timely Download is independently observed.

Recovery cannot invoke N restoration or reopen either native console. A failed,
missing or uncertain A result cannot consume another A attempt. Result validation
reopens the original claim, restoration intent/delivery/raw result, both native
health streams and both Download windows; its role timeline is separate from
the ordinary journal's timeline. Final ownership retirement follows that
validation. A complete native proof survives a later local publication cut;
recovery does not upgrade an incomplete or failed native roundtrip.

One H0 cut exposed a pre-install Download-recovery reporting mismatch: the
P383 native no-proof validator expected the full candidate timeline even though
no candidate intent existed. The P383-only branch now accepts the existing
exact request-cut recovery timeline only with `candidate_classification=not-attempted`.
It does not invent candidate events or relax other variants.

## Validation

- **23 focused tests PASS**, including real generated P383 C authentication,
  supervisor/fork/pipes, fixed health and raw replay, plus the joined three-role
  owner, actual bounded writers, current USB/Download producer and Android final
  consumer against explicit hardware/transport fixtures.
- Joined normal close performs exactly N installation, one N restoration and
  one A cleanup. The original consumed claim remains retained; CLOSED recovery
  reopens evidence without another transfer.
- Eleven publication cuts cover exception-claim publication, restoration
  intent/delivery/result, second raw receipt, complete native proof, A start/
  result and CLOSED result publication. No role is repeated. A intent without
  a result parks. Completed native proof is retained across later local cuts.
- Actual short restoration-intent writes preserve partial bytes and allow only
  the predeclared A recovery. Same-kernel second arrival stops before CONTROL.
  Failed or uncertain restoration and Android results are not retried.
- **77 existing common live tests PASS**. Ordinary release/attempt/recovery
  semantics remain unchanged outside P383; no global registry bypass is added.
- Actual A/B build passed with identical APs: size **31,150,121**, SHA256
  `16d723931a86bcb9efe894743995fde8d151991520bd2adbc0853bb71ab8b119`.
  Both `/init` outputs are static ARM64 ELF. The new Image is size **41,490,944**,
  SHA256 `776e5a2461b2c3260bf084ef30844628dcaf562d38f958433e3204b02899c4f4`.
  Its identity-only IKCONFIG transform preserves compressed length/layout.
- Generated native helper bytes normalize exactly to P382 after the declared
  identity substitution. The renderer change is the prospective version label.
  No numeric syscall flag, native ABI behavior or module algorithm changes.

Raw H0 logs, fixtures and A/B artifacts stay under `workspace/private/`.
The tests' UUID/root/mount/USB/Odin/ADB facts are fixtures, not live health,
flashed-image or physical-recovery proof. The failed first image-layout attempt
and its log are retained; only the fresh exact-length identity is qualified.

## Independent review and readiness

Independent **PASS_GO** covers the complete changed execution closure and the
common-boundary specialization. The reviewer independently ran all 23 focused
tests, checked all 348 build inputs, both APs/45 cpio entries, native source
normalization and all 54 current static source bindings. The prior static
metadata predating the final policy/target text is preserved privately; the
fresh canonical result binds the current reviewed bytes.

- Candidate static: size **38,959**, SHA256
  `fd2cc2a87320cd418ba34e926f41fc4fd40f44f2574a21a00ff9a92302327d54`.
- Initial independent review: size **14,919**, SHA256
  `ca3117e8682e48d8d9ab0cc18056c35e10a8335263a8ff2edcf3ac48135b143e`.
- Final binding-correction PASS_GO: size **14,606**, SHA256
  `7baa608b661a3133c382c37e789ef310b9046bc27fc655a304da8241c955f379`.
- READY manifest: size **6,703**, SHA256
  `0e8ad44a2dea05067247cd0d3bb85ff06b160cab23fe9de2f43865f5845f0b70`.
- Verified READY bundle:
  `a13d7843452b07dbd9eedc36c0c4538433f866144c0b532609d9a62784e0b027`.

The unchanged foreground-goal capability's review was refreshed only for
`f1_owner`, `common` and `target`; the other six sources and eight actions are
unchanged. This refresh opens or renews no grant. No previous token, session
grant, manifest or consumed candidate is reused.

The corrected connected preparation below is complete; its exact finite
attended Process-v2 approval remains required before device effects. The first qualification ends in Android;
standing native-baseline adoption and future faster loops remain a separate
bounded unit.

## First preparation and host binding correction

The first connected preparation at `p383-ready1-prepared-20260910-1` completed
D0 with `PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. Its exact target,
Android/root/original hash and bounded observer evidence remain unchanged.
It performed no reboot, Download request, Odin invocation or partition write.
The later host binding construction stopped with `KeyError: member`, before
`prepared.json`, any approval token or F1 intent existed.

The real `core.verify_bundle` adds `member` only to the candidate AP receipt;
the old generic fixture also supplied it for rollback. P383 preparation now
reopens the exact hash-verified Android AP with the existing boot-only reader
and derives its member identity explicitly. Later observer/control/recovery/
result paths validate that sealed identity without reopening the Android AP;
pre-restoration artifact checks still compare its actual member with the seal.
The joined fixture now uses the actual rollback receipt shape. All five joined
normal/cut/failure tests and 77 common live tests passed after this correction.

The successful original D0 and pre-correction static/promotion/READY bytes are
preserved privately. Their bundle binding is not rewritten to fit changed
sources. Fresh coherent H0 metadata and exact connected preparation bind the corrected
execution closure; no candidate or device effect is replayed.

The actual existing A also requires the ordinary rollback reader's
`require_deterministic_metadata=False` at both pin and member parsing; N keeps
`True`. The regression fixture now uses nonzero A tar UID/GID/mtime and the
actual pinned receipt producer. Both actual APs pass member derivation, and
current `core.verify_bundle → prepare_plan → _binding` passed without a device
call or prepared/token publication. The closure/binding body is 36,848 bytes.
The final correction review confirms these exact bytes and all 54 current
static bindings, with no remaining finding. Only the foreground `f1_owner`
review pin changed after the earlier refresh; all eight actions remain fixed.

## Corrected connected preparation

`p383-ready1-prepared-20260910-2` completed the exact D0 preparation with
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. It verified current rooted FYG8
Android health, exact original boot/supporting hashes, target continuity and
Download absence. No reboot, mode change, candidate/restore/cleanup transfer,
F1 transaction or exception consumption has occurred.

The new approval binding is
`938a3f15bbd75b8a03db4ba70b6339365dcd280b714219b7e9cd34e1d7008b9f`.
The private preparation owns exactly N installation, one N restoration and one
A cleanup/fallback with the fixed native health profile. The additional-command
plan is empty. The operator must supply a fresh approval while physically able
to perform the demonstrated Download recovery; this report is not that grant.

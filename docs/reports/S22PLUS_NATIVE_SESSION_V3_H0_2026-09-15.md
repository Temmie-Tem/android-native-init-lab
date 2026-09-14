# S22+ native session V3 H0 qualification

This records the pre-grant H0 checkpoint. The subsequent attended bootstrap
and physical USB reconnect results are in the
[V3 live report](S22PLUS_NATIVE_SESSION_V3_LIVE_2026-09-15.md).

The clean V3 owner implements the workflow corrections from the
[proportionality audit](S22PLUS_VALIDATION_PROPORTIONALITY_AUDIT_2026-09-15.md).
It has a separate live entry point and imports no legacy live owner. The
existing content registry, global F1 exclusion, boot-only transport, raw
capture and wire algorithms retain their original roles. Historical runs and
consumed images are unchanged.

## Result and boundary

The implementation and candidate artifacts are complete in H0; the reviewed
host configuration is installed and passes actual noninteractive readiness.
Independent review returned **PASS_GO — V3_REACHABLE_CAPABILITY**, with no
remaining findings. Passing runs cover **86 selected tests**: an initial full
85-test run and all 16 affected host tests after the final correction, including
one new regression. Python compilation also passes. No V3 grant or device effect has occurred.
The phone's last verified state remains the healthy P392 Android close.

P393 N and P394 E use v0.2.1's reviewed idle-reconnect/thermal runtime with
different fresh build identities. Both actual ARM64 A/B packages match, their
AP/member/init/renderer joins qualify, and the existing global content registry
reports both unclaimed. The actual init and renderer files are static AArch64
ELFs. The two candidates share the same 144-entry native source map, canonical
SHA-256 `60e62445fea35133183da94d09d009ec2027abfe3109bdfcf791b2d461449ec6`.

| Candidate | Boot-only AP SHA-256 | Size |
| --- | --- | ---: |
| P393 N | `5fd182c4cf2f129c302ba406003291bc87fd82d448a38a74168b93e0e0a09aa4` | 31,303,721 |
| P394 E | `12c5330e4fa5a3ed893194a7717dc21706f208b39d27c252b25405f4e439ccc6` | 31,303,721 |

These are artifact qualifications, not native admission, physical USB
reconnect proof or current device health. The consumed, unadmitted P392 AP is
not reused. The retained exact A transfer and seven fresh final-health reads
also rederive through the new bounded recovery-evidence reader.

## Changed behavior

- Fixed host setup precedes the grant clock. Five reviewed root-owned files
  establish a no-argument tty-holder census and the exact native-gadget udev
  exclusion. A dedicated polkit action supports a detail-free noninteractive
  readiness query. The permanent exception cannot invoke the installer or
  arbitrary root commands. Only byte-exact prior installation content may be
  updated through its original manifest; unknown different content is refused.
- A pure host/Android preflight failure consumes no F1 operation capacity.
  A native authentication attempt separately owns its unique prior tail and
  original A recovery, so an uncertain OPEN cannot be retried through another
  operation or lose its attended recovery route.
- Bootstrap retains two N installations and four authenticated sessions.
  Normal N/E/N uses one final N health/DETACH. E reentry, real cable reconnect
  and HUD collection are explicit selections; HUD is absent from routine N
  health. No V3 E content can be replayed.
- Original BOOTTIME deadlines cover the task, protocol and USB transitions.
  Durable publication cannot extend dispatch time. A is present and verified
  before native effects; completed A health can resume without requiring the
  AP file after its transfer has completed.
- Actual open/close facts and raw protocol streams are independent records.
  Missing aggregates can be reconstructed after a host reporting failure.
  Completed final proof never triggers another flash because publication failed.

The [policy](../operations/S22PLUS_NATIVE_SESSION_V3.md), common details and
S22+ target adoption are review-gated. V3 device effects and recovery require
the original host boot. A host OS restart needs a separately reviewed recovery
route bound to the original journal; H0 reconstruction remains available.

## Validation

The focused suite covers actual resident C/PTY handshake and detach/reentry,
real host fuser/descriptor behavior, actual boot-only subprocess capture,
missing or changed A, source/target/artifact bindings, delayed intent writes,
injected host-suspend time, no-repeat ownership, one-shot A recovery and H0
publication repair. The shared protocol primitives retain their default clock
for existing callers; V3 explicitly supplies BOOTTIME. Their regression tests
also pass. No native numeric syscall flags or functional C behavior changed.

The first private combined-test driver omitted the repository root from its
Python import path; it failed before four test modules could load. The corrected
driver and both raw results are retained. The final run completed 85 tests in
17.701 seconds with no capture timeout, overflow or producer error.

Actual PC preflight exposed a polkit 127 restriction absent from the mocked
API test: an unprivileged detail-bearing `pkcheck` query returned rc127. This
happened after host installation and before any grant or device command. The
independently reviewed correction uses a dedicated policy action bound to the
fixed helper and a query without details. The five-file update completed;
actual `pkcheck`, privileged helper execution, installed-file digest/mode checks
and complete holder census now pass without interactive authorization. Native
tty state was absent with zero holders; this is not fresh Android health.

Both exact source variants received independent `PASS_GO`: the actual working
contract and the publication contract excluding pre-existing unrelated S20
status edits. The published binding uses the latter; the reviewed active local
binding preserves the former. Neither accepts an unreviewed hash or transfers
authority between targets.

The concrete attended request is prepared at
`workspace/private/runs/s22plus-native-session-v3/task-20260915-1/`: P393
bootstrap, P394 physical-USB-reconnect N/E/N, optional original A exit, at most
three operations in 3600 seconds. HUD is not requested. Proposal SHA-256 is
`ad031d1f885562df33f0372657bf7126107329515def3dc8a590ece65cdd9350`.
The original clock has not opened. The next device step needs the actual
returned grant and current physical attendance, then its machine preflight.

Private qualification, installer proposal, verification and recovery evidence
are under `workspace/private/outputs/s22plus-native-v3-h0-20260915-1/`. Public
material contains source and artifact metadata only. A90 and S20+ received no
commands or device actions in this work.

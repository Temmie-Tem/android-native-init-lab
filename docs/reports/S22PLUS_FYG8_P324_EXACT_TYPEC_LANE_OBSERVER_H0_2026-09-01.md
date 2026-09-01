# S22+ FYG8 P3.24 exact Type-C lane observer H0

Date: 2026-09-01

Target: `SM-S906N` / `g0q` / `S906NKSS7FYG8`

Status: F1 closed and consumed; exact USB enumeration proved, native PID-1
arrival unproved, exact rollback and final health verified

## Live result and incident

The first prepared invocation stopped at `ABORTED/4` before candidate intent
because the Codex process could not cross the host `pkexec` privilege boundary.
It performed no reboot, Download entry, Odin session, candidate transfer, or
rollback transfer. Its approval is stopped and was not reused.

The fresh attended invocation then completed the exact P3.24 candidate and
rollback transfers once each and closed its journal at 19 records. Final rooted
FYG8 health passed and `recovery_required=false`; P3.24 is consumed and never
replayable. The host P3.00 trace and P3.24 lane receipt prove that the candidate
enumerated at exact `usb:3-1.3` as `04e8:6861`, `cdc_acm`, and `ttyACM0`, with
source-lane count zero, candidate exact count one, foreign count zero, and
same-run Type-C partner continuity.

The primary observer nevertheless retained zero bytes and classified
`identity-mismatch`. Its pre-open ModemManager check passed the resolved USB
interface node `3-1.3:1.0` to `udevadm`; that object's properties did not carry
the two tty rule flags. The same-run tty add event did carry
`ID_MM_DEVICE_IGNORE=1`, `ID_MM_PORT_IGNORE=1`, and interface `00`. This proves
a host observer property-scope defect before `open()`, not a missing candidate
endpoint or failed guard arm. It does not prove the candidate banner, native
PID 1, or USB data success. The retained Carrier projection also remains
`NO_PROOF_OBSERVER` and grants no causal, MUX, or host-silent claim.

After `CLOSED`, the ordinary result path tried to add the final arrival
projection to the 29,102-byte live state. The canonical state became 34,672
bytes and exceeded the shared 32 KiB record bound before `live-result.json`
publication. The exact-run host-only finalizer permitted only that pinned
pre-state to become the pinned mode-`0400` state, then published the canonical
38,558-byte mode-`0400`/single-link result. Post-publication audit passes with
no ADB, USB revalidation, Odin, backend, candidate, rollback, or device action.
Its SHA-256 values are `9f23ecbf34ebec17693d6f5b62283e0b4a0970866d36124d0563919967b1ab24`
for state and `b2eca7a4921e8d8294f3ef9dad01ec6dd18acf4fd4d74aa23015c0b0caf6749a`
for result.

Independent hostile review found and blocked an initial audit-only seam where
the common journal reopen routine rewrote an identical journal head. Commit
`7fa1a78b65` replaces that call with a validating read-only journal view; a
real post-publication audit then preserved the inode, size, timestamps, mode,
link count, and bytes of the journal head, state, and result. The re-review
verdict is `PASS_GO` for this exact host-only finalizer.

The formal terminal is therefore
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` /
`p324_acm_primary_native_pid1_arrival_unproved_rollback_verified`. The next
candidate must be fresh. The proportional P3.25 repair keeps the P3.24 lane,
selector, transient udev rule, receipt taxonomy, and rollback unchanged and
redirects only the two delegated guard property probes to the exact selected
tty class node.

## Why P3.23 did not produce proof

P3.23 remains consumed with exact candidate/rollback transfers `1/1`, a
healthy rooted FYG8 return, and formal `NO_PROOF`. The operator observed a
normal candidate boot without a boot loop, but the durable ACM observer
selected no endpoint and retained zero bytes. That observation is supportive,
not formal native PID-1/USB proof.

Post-run host evidence shows that the candidate enumerated as the exact
`04e8:6861` E3 ACM identity with `cdc_acm` and `ttyACM0` at `usb:3-1.3`. The
P3.23 selector was frozen to the Android preparation topology `usb:2-1.3`, so
it correctly opened nothing. This localizes the immediate failure to the
host selector topology rather than to candidate boot or banner generation.
Whether a physical reconnect occurred during P3.23 is not established, and
the consumed result is not reclassified or replayable.

## Proportional P3.24 repair

The host exposes one exact Type-C `port0` lane pair:

- source SuperSpeed lane `usb:2-1.3` through `usb2-port1` and controller
  `0000:00:0d.0`;
- candidate high-speed lane `usb:3-1.3` through `usb3-port1` and controller
  `0000:00:14.0`;
- identical connector location `0x80000101`, `hotplug` connection type, and
  the exact companion USB2/USB3 hub pair.

P3.24 captures that relationship during read-only preparation, places its
private receipt in the approval binding, and revalidates it at prepared-run
load, execution D0, exact Download identification, observer arm, and immediately
before the one candidate endpoint is opened. The observer inventories both
lanes but may open only exact `usb:3-1.3`. A source-lane candidate, duplicate,
foreign candidate-like endpoint, malformed inventory, changed resolved path,
or changed Type-C partner makes the observation no-proof. USB4 and topology
suffix inference are not selectors.

The same-run Type-C partner object is corroborating evidence only. It does not
prove that a person never unplugged or rerouted the cable; the attended
no-disconnect/no-move/no-reroute condition remains separate.

The P3.00 passive trace launcher also receives one bounded two-second `/proc`
ownership poll to tolerate the post-`Popen` exec/environ scheduling race seen
in P3.23. It starts the sidecar once and never retries ADB, Odin, USB, a
candidate action, or any device action.

No new D1 rotation, Full-LTO build, bespoke review receipt, second approval,
or per-poll lane scan was added. P3.24 keeps the ordinary Process-v2 sequence:
one read-only prepare, one exact approval, one candidate transfer, bounded
observation, mandatory exact rollback, and final health verification.

## Exact host artifacts

The fresh run identity is `c324f1e0a90b5e6d7c8a9b0c1d2e3f4b`.

- Candidate AP A/B: 27,279,401 bytes, SHA-256
  `a1703c66557375dee614fc38b6eceb476544a1ad6ed59815a72896e370976ce1`.
- Builder result `-03`: 39,893 bytes, SHA-256
  `16769c766acd329623781376893da40d465cb4e06c4614174f1ecbca820be779`.
- Candidate-static `-03`: 22,558 bytes, SHA-256
  `e694dbef5a25e2865fa62c9e09f4976a6400d18c1783430b48abb377b4738103`.
- Promotion run manifest: 1,021 bytes, SHA-256
  `52e4d4fdd3fea51d07b04c3ea2526ee47a115bdfe0000ad4110a4547b7be70f5`.
- Promotion static check: 1,835 bytes, SHA-256
  `4d29493ad2a3846441dcf7b15468b8d0a65ea75ad35395c7e553971642cf0c64`.
- Public ready manifest: 3,327 bytes, SHA-256
  `d7fecb3a443c0df78c297c1a748f81529b7c486092694032a86e006f39daba54`.
- Exact rollback AP remains 23,367,721 bytes, SHA-256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

The candidate AP contains only `boot.img.lz4`; A/B are byte-identical and all
P3.19-P3.23 identities are rejected. The P3.24 runtime keeps the P3.23 ACM
behavior and rotates the candidate identity because P3.23 is consumed.

## Validation and authority boundary

The final P300/P324/common focused selection passes 189 tests. It covers the
exact lane pair, USB4 exclusion, source/duplicate/foreign/malformed rejection,
open-time lane revalidation, receipt reopening, P323-banner rejection, exact
consumed-P323 baseline admission, P300 bounded ownership polling, artifact
identity, candidate-static, ready publication, common evidence/core/live
behavior, rollback, and terminal classification. Python compilation,
builder/static audit-only, ready rehearsal, `core.verify_bundle(...,
runtime_bound=True)`, private `0400`/link-one promotion modes, public `0644`
manifest mode, and diff checks pass.

The global raw-first auditor is not counted as a P3.24 failure: its current
tree scan stops first on a concurrently added S20+ source outside this unit.
The P3.24 execution closure directly binds the changed common live source and
the new lane and observer sources; the independent review treats the unrelated
cross-target scan stop separately.

The former ready manifest was H0 capability evidence and is now consumed by the
closed P3.24 run. Exact candidate enumeration, two exact transfers, rollback,
and final health are proved; banner/native-PID-1 arrival and candidate success
remain unproved. No P3.24 approval, replay, recovery, or live authority remains.
A P3.25 successor requires fresh candidate bytes, host qualification, connected
preparation, and a new attended approval.

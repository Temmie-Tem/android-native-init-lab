# S22+ FYG8 P3.24 exact Type-C lane observer H0

Date: 2026-09-01

Target: `SM-S906N` / `g0q` / `S906NKSS7FYG8`

Status: H0 ready capability; no P3.24 device action yet

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

This report and the ready manifest are H0 capability evidence only. They create
no D0 result, prepared binding, approval, reboot, Download entry, Odin call,
partition transfer, recovery, candidate success, USB proof, or live authority.
A fresh connected D0 prepare and its newly emitted exact approval token are
required before P3.24 F1.

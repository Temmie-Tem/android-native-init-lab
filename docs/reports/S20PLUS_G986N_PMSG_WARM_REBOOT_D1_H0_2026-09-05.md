# S20+ PMSG ordinary-reboot marker: H0 capability

Date: 2026-09-05. Target: `SM-G986N/y2q/y2qksx/G986NKSS8IYC2`.
Status: **PASS_GO_NOT_ACTIVE - H0 CAPABILITY REVIEWED**.
Device writes, reboots and S20+/S22+/A90/other-target commands in this unit: **0**.

## Question and implementation

The [readiness D0](S20PLUS_G986N_PSTORE_READINESS_D0_2026-09-05.md)
proved live metadata readiness, but it did not write or find a retained marker.
This unit implements one future attended transaction: generate one private
144-byte marker, write it through the verified PMSG character-device API,
request one ordinary Android reboot, compare the marker in the first observed
returned boot's fixed old PMSG record, and establish final exact Android health.

The [source](../../workspace/public/src/scripts/revalidation/s20plus_g986n_pmsg_warm_reboot_d1.py)
has only `--render-plan`, `--connected` and read-only `--resume` entry points.
It remains `ACTIVE=False`. Its normalized SHA-256 is
`8605430e64f8aa33c7535e3707a7ca50461c29df39867bc40b3b297afb3acf33`.
The normalized identity changes only the activation boolean. It pins the
unchanged readiness source and its existing health/inventory/ADB closure.

The common D1 contract now explicitly delegates this narrow reserved-RAM
experiment to the exact target. Reserved RAM alone was not authority for a
privileged marker write; the earlier metadata D0 expressly prohibited it.
The new delegation requires separate target activation and one current attended
request. It grants no R1 installation/staging, persistent-file/configuration
mutation, block access, partition payload or recovery-mode operation.
The [target section](../operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md#s20-pmsg-warm-reboot-marker-d1)
contains the exact command, path, source, output and failure limits.

The writer first pins a read-only character descriptor, verifies its live
major/minor and link count, and only then opens that descriptor for writing.
The only marker bytes come from canonical fresh target/topology/boot/source
binding plus an internally generated nonce. The reader performs a bounded
full-line match on-device; private log contents are never exported. The
existing routine-action interlock excludes other device owners. A single fixed
trial directory and atomically published one-shot intents prevent a second
marker write or reboot, including after missing or malformed results.

## Proof and failure behavior

A positive result needs one exact marker match, completed write and ordinary
reboot receipts, no observation gap, and a healthy same-target return.
It proves retention across this ordinary Android reboot only. Native PID1,
Download/TWRP/recovery, panic/watchdog and power-loss retention remain unproved.
The first publicly healthy changed boot is pinned before further root health
checks. This is the first observed return; it does not prove absence of unseen
boots.

Missing, Android-consumed, overwritten, unreadable, duplicated or ambiguous
records remain NO_PROOF. A write/reboot intent without its receipt consumes the
action and prevents positive ordinary-route attribution. A comparison intent
without result never causes another comparison. A resume without durable
arrival records an observation gap before reading, so a later matching marker
cannot promote lost first-return provenance to proof. A changed already-pinned
return boot stops.

Nonreturn retains HEALTH_PENDING and the shared guard. Resume performs one
fresh bounded exact-target health observation and only a still-unconsumed
comparison; it never writes, reboots or waits for return. It grants no automatic
flashing or physical recovery action. A fully published terminal can be
revalidated/re-emitted and its owned guard released without device contact.
A pre-binding zero-effect abort can release only its own guard without claiming
health. Unknown/partial journal nodes and foreign guards remain stops.

## Validation and review

- New focused suite: **21/21** passed, including real host-shell writer/reader
  producer-to-parser fixtures, exact/binary/duplicate/missing/oversized/indirect
  records, descriptor checks, every journal publication cut, no effect replay,
  target/topology drift, foreign guards, strict JSON/claim validation and
  conservative lost-arrival handling.
- Existing fixed readiness suite: **18/18** passed. Neither its source nor its
  frozen health/inventory dependencies changed.
- Touched Python compiled; H0 render-plan reports inactive and empty executed
  command/write lists. No device transport was invoked by these checks.
- Final repository boundary and diff checks are recorded in the private closure.

Independent review is required by the repository's Review Rules because the
common/target delegation, runner and journal are new. Preliminary review
accepted the narrow D1 classification. Implementation review identified two
issues: ordinary command/parser failures initially lost output digests, and
first-return identity was recorded too late. Both were repaired and covered by
regressions; all returned command envelopes now retain bounded digests before
parsing, and arrival/gap rules preserve uncertainty across publication cuts.
Final independent review returned **PASS_GO_NOT_ACTIVE**, with no remaining
blocking finding. It also covered the exact future boolean/status activation
flips: active runner SHA-256 would be
`5da0ff52ed719c3c3de6f67242b28c3f71f3028f991befe460cfbb16e8d507e5`.
The current source and target remain dormant. Capability PASS is not a live
approval; the single transaction still needs current attended authority and
fresh exact runtime binding.

Private source, test, policy, validation and review evidence is retained under
`workspace/private/work/s20plus-pmsg-warm-reboot-d1-h0-20260905-s4ll_l_z/`.
No firmware, device logs or identifiers are included in this commit.

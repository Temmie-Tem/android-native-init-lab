# S22+ FYG8 P3.03 HS-PHY Silent-Failure Implementation

Date: 2026-08-05
Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q` / `S906NKSS7FYG8`)
Tier: H0 only
State: host-qualified; canonical manifest absent; no device contact or F1 arm

## Outcome

P3.03 is implemented as a userspace-only attribution observer over the fixed
P3.00 Image. It measures the otherwise silent clock-return boundary in
`phy-msm-snps-hs.ko` and captures the vendor driver's existing reset and
register-readback error logs during the same candidate window. It does not
rebuild the kernel, change or inject a module, or add a partition payload.

The exact vendor module is 67,488 bytes, SHA-256
`22a866320ba0de46619484efafaf0cf7ea3f7ba387cee7c3dd085f3a82492e94`,
Build ID `cdb249f9a7599440ca66208f02caec0a6601bc03`. The exact FYG8 device tree has
no `cfg_ahb_clk`, so any cfg clock hit is an observer contradiction.

## Offset-Probe Contract

The vendor compiler fully inlined the clock helper. `msm_hsphy_init()` has six
`clk_prepare` and six `clk_enable` calls across its EUD and normal paths. Each
probe is bound to the instruction immediately after a relocation-proved `bl`;
that instruction is the first `cbz/cbnz w0` consumer. The return value is
therefore fixed by the AArch64 ABI and has not yet been overwritten.

This does not relax P3.00's rejection of an instruction-offset probe at a
path-dependent function epilogue. P3.00 had several paths converging with
different register allocation. P3.03 accepts only a named call edge followed
immediately by its ABI return consumer. The static checker requires all twelve
callsite proofs and the exact module receipt. Candidate A and B reuse the same
unchanged vendor module, so the audit is common to both.

Reach and return are separate facts. A callsite with hit count zero is not a
zero return. If `msm_hsphy_init()` enters and returns zero while all twelve
callsites miss, detail `0xD00` records only that the clock block did not run;
it asks where `clocks_enabled` became true. Missing init entry/return or a
nonzero init return is a contradiction family. Profile loss, record loss, or
an unexpected cfg callsite also invalidates the clock conclusion.

## Result Contract

- Ordinal 105, PROGRESS, `0xD00-0xDA2`: clock-path reach and return buckets for
  EUD/normal, ref-source/ref/cfg, prepare/enable, and
  `0/-EINVAL/-EIO/-ETIMEDOUT/other-negative`.
- Ordinal 106, FAILURE, `0x4001-0x4800`: candidate `/dev/kmsg` summary containing
  first write-readback offset, count bucket, and reset-failure mask.
- `0x6001-0x600F`: fail-closed observer and path contradictions.

The log observer opens `/dev/kmsg` at its current end before module loading,
checks sequence continuity and overflow, requires the normal HS-PHY path marker,
and retains reset failures plus `msm_usb_write_readback ... FAILED` events.
The stock baseline parser normalizes the immediately-post-reboot working log
into the same domain. The ready path now requires the exact raw/result pair,
proves that the retained timestamps cover boot start through a timestamped
normal-path marker, binds the actual on-device module hash and stable boot ID,
and exact-matches the pair to the outer manifest ID and live run ID. A
candidate signature equal to stock is not causal attribution. Clean logged
paths close only reset and register-readback errors; they do not prove the
silent clock path. An incomplete stock log disables only this log comparison;
it does not turn a missed clock callsite into return zero or erase a valid
clock hit/return result.

## Artifacts

- static `/init`: 66,416 bytes, SHA-256
  `635d714ef7eb1e16bb7b131ff3c0ae8aa0b7282c3f1671a1ff0577941991e36b`
- boot image A/B: 100,663,296 bytes, SHA-256
  `434a4075532ac4c35ec5068aaa56da441322f63e5e342fa22f6ee8f62ad52b68`
- `boot.img.lz4` A/B: 27,100,964 bytes, SHA-256
  `a390795b74e58d2ff652509a38adbef4721f9bbb9f725766143ae01af89da45c`
- one-member AP A/B: 27,105,321 bytes, SHA-256
  `f2cb42b88276dd5c2793d2583308bff60c15e6a7dcf9bb3531b4a6d33f236ad2`
- fixed Image: SHA-256
  `01457240881b432f725b0f2d795813c38ef7cca4365633f9b0fc7c3a62744a3f`

A/B are byte-identical. The AP contains only `boot.img.lz4`. No module is
injected and no Full-LTO or kernel rebuild is needed.

## Validation

- the 12-file SOURCE_KEYS intent reverified without drift;
- exact callsite audit: 12/12 verified;
- P3.03 telemetry and Process-v2 tests: 16/16 passed, including truncated or
  late stock-log rejection and outer campaign-ID mismatch rejection;
- common Process-v2 evidence tests: 25/25 passed;
- common Process-v2 runner tests: 22/22 passed;
- P3.02 Process-v2 regressions: 7/7 passed, including actual current P3.01-r1
  promotion in the same process;
- static artifact closure:
  `PASS_P303_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY`;
- Process-v2 offline evidence promotion:
  `PASS_P234_PROCESS_V2_OFFLINE_EVIDENCE_PROMOTION`;
- canonical ready-manifest rehearsal:
  `PASS_P303_PROCESS_V2_READY_MANIFEST_REHEARSAL_HOST_ONLY`, with
  `created=false`, an exact five-artifact acceptance contract, and no manifest.

The standalone private callsite-audit receipt was regenerated after an earlier
private copy lacked the already-required A/B offset-identity field. The new
receipt is byte-for-byte equivalent to the audit embedded in the frozen intent;
candidate bytes and all twelve SOURCE_KEYS remained unchanged.

One unrelated historical P3.01 private fixture still carries its older decoder
policy hash; the current P3.01-r1 fixture and P3.02/P3.03 regressions pass. It
was not repaired or attributed to P3.03.

## Live Preconditions

Before a P3.03 F1 run, connected D0 must verify the exact S22+ profile and the
on-device `phy-msm-snps-hs.ko` SHA-256 above. If the retained baseline requires
the already-defined normal reboot rotation, capture the bounded working stock
HS-PHY log immediately after that same reboot; no additional reboot is added.
Reject the pair if the boot window, normal-path marker, target/module identity,
stable boot ID, or exact P3.03 campaign binding is absent. Only that actual D0
pair may allow Process-v2 prepare to create the canonical live binding. The
consumed P3.01-r1 candidate is never replayed.

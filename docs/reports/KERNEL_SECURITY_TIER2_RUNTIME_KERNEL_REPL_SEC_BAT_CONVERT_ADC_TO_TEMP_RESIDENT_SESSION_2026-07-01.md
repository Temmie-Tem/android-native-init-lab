# Kernel Tier-2 REPL live-call proof: sec_bat_convert_adc_to_temp

Date: 2026-07-01

## Result

`sec_bat_convert_adc_to_temp(unsigned int adc_ch, int temp_adc)` is live-proven
only under the target-specific invalid-channel scalar contract:

- Input: `adc_ch=0`, `temp_adc=12345`.
- Expected return: source-defined default sentinel `25000` (`0x61a8`).
- Live result: two repeated calls returned `0x61a8`, stable.
- Proof status: `trusted-under-sec-bat-invalid-channel-conversion-contract`.
- Auto-call policy: target-specific proof only; the global call-safety gate
  remains `DENY`.

Private run evidence:
`workspace/private/runs/kernel/repl-resident-session-sec-bat-convert-adc-to-temp-20260701T133219Z/`

## Static Gate

- Symbol: `sec_bat_convert_adc_to_temp`
- Link address: `0xffffff8009573654`
- Resolution: `export-recovery`, map agrees with relocated export, direct BL
  xrefs `2`.
- Next symbol boundary: `sec_bat_get_thr_voltage` at `+0x148`.
- Source signature:
  `int sec_bat_convert_adc_to_temp(unsigned int adc_ch, int temp_adc)` at
  `drivers/battery_v2/sec_adc.c:376`.
- Source contract: unsupported `adc_ch` branches to `temp_to_adc_goto` before
  selecting `local_battery` ADC tables; return expression keeps sentinel
  `25000`.
- Prefix words pinned:
  `ca1103d0 a9bf43fd 910003fd d0011448 f9434108 b4000128 7101481f 540001a0 7101341f 540007a1 f9400509 910ae128`.
- Static arg-taint evidence: no caller-provided scalar argument is used as a
  memory base; pointer arg indices are empty.

`sec_abc_wait_enabled()` was rejected before implementation despite being an
adjacent ABC symbol: disassembly shows non-leaf paths through `printk` and
`wait_for_completion_timeout`, so it is not a read-only getter proof target.

## Live Run

Resident-session mode was used:

`v1-repl flash once -> warm reboot -> one bounded batch -> per-target flush -> v2321 rollback once`.

Run summary:

- Session decision: `a90-repl-resident-session-pass`
- Batch count: `1`
- Completed target count: `1`
- Flash count: `2`
- Candidate flashed once: `true`
- Rollback flashed once: `true`
- Warm reboot between batches: `true`
- Timeline errors: `[]`

Timeline events are canonical top-level `events` only and include the required
eight phase events plus batch sub-events.

Selected phase timings:

- Candidate flash: `64.205967s`
- Candidate boot/health: `32.301651s`
- Warm reboot to batch-ready: `33.253096s`
- Batch target call window: `2.952422s`
- Live session total: `69.782803s`
- Rollback flash: `64.992606s`
- Rollback boot/health: `48.089661s`
- Candidate-flash-start to rollback-boot-ready total: `279.388792s`

Final resident after rollback:

- `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- `selftest: pass=11 warn=1 fail=0`

## Host Validation

Commands run:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_repl.py \
  workspace/public/src/scripts/revalidation/a90_repl_resident_session.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_a90_repl.CallSafetyClassificationTests.test_proven_live_call_targets_stay_safe \
  tests.test_a90_repl.CallSafetyClassificationTests.test_source_signature_oracle_distinguishes_scalar_and_pointer_args \
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_sec_bat_convert_adc_to_temp_passes_with_invalid_channel_contract

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  sec_bat_convert_adc_to_temp

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl_resident_session.py \
  --dry-run --batch sec_bat_convert_adc_to_temp --max-batch-size 30

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/analysis/analyze_repl_run_timing.py \
  --batch-size 10 --resident-batches 10 --warm-reboot-sec 15
```

Validation results:

- `py_compile`: pass
- Focused unittest: `3` tests pass
- Classifier: host-only pass; target remains global `DENY`, not seed-whitelisted
- Resident-session dry-run: pass
- Timing aggregator after this run: `16/64` canonical timelines, resident
  projection `20 -> 2` flashes, `13.4s/target`, `20.6x` vs per-unit flash

## Function Map Entry

```json
{
  "symbol": "sec_bat_convert_adc_to_temp",
  "status": "live-proven",
  "trusted_input_contract": "two scalar arguments only: adc_ch=0 unsupported channel and temp_adc=12345; this source path never selects local_battery ADC tables and dereferences no caller-provided pointer",
  "return_contract": "int return is the source-defined invalid-channel/default sentinel 25000 and stable across immediate repeated proof calls",
  "observed_return_value": "repeated invalid-channel scalar calls returned the source-defined default sentinel 0x61a8",
  "cleanup": "n/a-sec-bat-scalar-invalid-channel-no-owned-allocation",
  "auto_call_policy": "target-specific-proof-only-not-global-auto-call"
}
```

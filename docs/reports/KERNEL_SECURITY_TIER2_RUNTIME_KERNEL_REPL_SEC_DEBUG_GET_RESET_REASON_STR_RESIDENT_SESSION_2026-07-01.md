# Runtime Kernel REPL — `sec_debug_get_reset_reason_str` Resident-Session Proof (2026-07-01)

## Result

`sec_debug_get_reset_reason_str(unsigned int reason)` is live-proven under a
bounded read-only borrowed-string contract.

- Target: `sec_debug_get_reset_reason_str`
- Source: `include/linux/samsung/debug/sec_debug_user_reset.h:28`
- Signature: `extern char * sec_debug_get_reset_reason_str(unsigned int reason)`
- Static identity: `exact-leaf-map+xref+word-boundary`
- Link address: `0xffffff80086ed4a4`
- Next symbol boundary: `sec_debug_store_extc_idx` at `+0x28`
- Direct BL xrefs: `6`
- Body: leaf, no BL, no pre-call argument pointer dereference
- Return: borrowed kernel `char *`, never freed by the proof

Live result from
`workspace/private/runs/kernel/repl-resident-session-sec-debug-get-reset-reason-str-retry-20260701T125452Z/`:

- Decision: `a90-repl-live-call-proof-sec_debug_get_reset_reason_str-pass`
- Reason `1`: `SP`, repeated twice, stable
- Reason `12`: `NP`, repeated twice, stable
- Reason `13`: `NP`, repeated twice, stable
- Clamp proof: out-of-range reason `13` returned the same borrowed pointer/string as reason `12`
- Runtime pointers and KASLR slide remained private-only

## Safety

The proof used resident-session mode:

1. Flash v1-repl once.
2. Warm reboot v1-repl before the bounded batch.
3. Run one target batch and flush per-target result to disk.
4. Roll back to v2321 once at the end.

Rollback/fallback artifacts were confirmed before live work:

- v2321 rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- v2237 fallback SHA256: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- v48 fallback present
- v1-repl SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`

Final resident after bridge restart:

- `version`: `v2321-usb-clean-identity-rodata`
- `selftest`: `pass=11 warn=1 fail=0`

## Attempt Notes

Attempt 1:
`workspace/private/runs/kernel/repl-resident-session-sec-debug-get-reset-reason-str-20260701T124848Z/`
failed before completing the target. The failure was a transient REPL transport
marker capture loss on the first non-replay-safe `OP_CALL`; no target result was
promoted. The script rolled back to v2321, and a bridge restart confirmed final
v2321 health.

The harness was tightened before retry:

- `sec_debug_get_reset_reason_str` target calls are now `replay_safe=True`
  because the function is a pinned read-only leaf and the proof already repeats
  the same inputs.
- `a90_repl_resident_session.py` now records `live_session_end` in exception
  paths after `live_session_start`, preserving the canonical timeline schema.

Attempt 2 passed.

## Timing

Canonical timeline:
`workspace/private/runs/kernel/repl-resident-session-sec-debug-get-reset-reason-str-retry-20260701T125452Z/timeline.json`

- Candidate flash: `64.248881s`
- Candidate boot/health: `30.975862s`
- Live session: `74.898211s`
- Batch live window: `11.870893s`
- Rollback flash: `63.767765s`
- Rollback boot/health: `0.840946s`
- Candidate start to rollback boot ready: `234.747757s`

`analyze_repl_run_timing.py --json` now uses `14` canonical timelines and
projects resident mode as:

- Flashes: `20 -> 2`
- Resident per target: `13.785392s`
- Speedup vs unbatched unit: `20.10x`
- Speedup vs per-unit in-boot batch: `2.01x`

## Validation

Host/static:

- `python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py workspace/public/src/scripts/revalidation/a90_repl_resident_session.py tests/test_a90_repl.py`
- `PYTHONPATH=tests python3 -m unittest tests.test_a90_repl.CallSafetyClassificationTests.test_seed_inventory_summary_counts_tiers tests.test_a90_repl.CallSafetyClassificationTests.test_source_signature_oracle_distinguishes_scalar_and_pointer_args tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_sec_debug_get_reset_reason_str_passes_with_borrowed_string_contract`
- `python3 workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img sec_debug_get_reset_reason_str`

Live:

- `python3 workspace/public/src/scripts/revalidation/a90_repl_resident_session.py --batch sec_debug_get_reset_reason_str --run-dir workspace/private/runs/kernel/repl-resident-session-sec-debug-get-reset-reason-str-retry-20260701T125452Z`
- `python3 workspace/public/src/scripts/analysis/analyze_repl_run_timing.py --json`


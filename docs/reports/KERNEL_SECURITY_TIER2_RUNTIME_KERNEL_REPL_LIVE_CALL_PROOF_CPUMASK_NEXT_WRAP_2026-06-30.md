# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: cpumask_next_wrap

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-cpumask_next_wrap-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-cpumask-next-wrap-20260630/proof/a90_repl_evidence.json`

## Candidate Selection

This unit continued the cpumask wrapper sweep after `cpumask_next` and `cpumask_any_but`.
`cpumask_next_wrap` was selected before `cpumask_next_and` because it still has exactly one
cpumask pointer. The extra surface is scalar only: `n`, `start`, and the internal wrap-state flag.

The selected target is not trusted as a general cpumask facility. The proof creates an owned kernel
cpumask buffer, verifies the wrapper's compiled `nr_cpumask_bits=8` instructions, calls a bounded
wrap-iterator case table, checks the return table, re-peeks the cpumask/canary after every call, and
frees the allocation.

## Static Gate

Target:

- `cpumask_next_wrap`: `0xffffff80099a9f1c`
- Resolution method: `export-recovery`
- Direct BL xrefs: `6`
- Shape: JOPP entry, non-leaf wrapper, one BL to `find_next_bit`.
- Wrapper evidence: `0x52800101` (`mov w1,#8`) at the `find_next_bit` call setup, and
  `0x52800117` (`mov w23,#8`) for the sentinel.
- Source signature: `include/linux/cpumask.h:244`,
  `extern int cpumask_next_wrap(int n, const struct cpumask *mask, int start, bool wrap)`
- Source pointer contract: x1 is `const struct cpumask *mask`; x0/x2/x3 are scalars.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x1 `cpumask-buffer`.

The target was not called with an arbitrary numeric pointer. The proof requires an owned cpumask
buffer and scalar `n/start/wrap` values bounded by compiled `nr_cpumask_bits=8`.

## Host Validation

Commands:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_repl.py \
  tests/test_a90_repl.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --no-objdump \
  cpumask_next_wrap

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_a90_repl.CallSafetyClassificationTests \
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_cpumask_next_wrap_passes_with_owned_cpumask_contract

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_repl
```

Result:

- `py_compile`: pass.
- CLI classify: `SAFE-WITH-VALID-PTR`, verified by `export-recovery`, direct-BL xrefs `6`,
  non-leaf wrapper, required x1 `cpumask-buffer`.
- Focused tests: static classification/source tests and the new fake-transport proof passed.
- Full `tests.test_a90_repl`: `Ran 134 tests`, `OK`.

## Flash And Health

Preconditions:

- v1-repl candidate SHA matched `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- v2321 rollback SHA matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- v2237 fallback SHA matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Final fallback `boot_linux_v48.img` existed with SHA
  `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
- TWRP recovery image existed with SHA
  `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`.
- TWRP recovery tar existed with SHA
  `6d9e929462ea4c85f257b080431d387d5bfb787ff800bd4178c823c3874d862a`.
- Bridge was connected.
- Baseline before flash: `v2321`, `version` OK, `status` OK, `selftest pass=11 warn=1 fail=0`.

Candidate flash:

```sh
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  --from-native \
  --expect-sha256 b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65 \
  --expect-readback-sha256 b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65 \
  workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img
```

Result:

- Remote pushed image SHA matched candidate SHA.
- Boot readback SHA matched candidate SHA.
- Post-flash `version/status` verification passed.
- Candidate standalone selftest returned `pass=11 warn=1 fail=0`.
- REPL selftest completed and returned `a90-repl-v2a1-selftest-pass`.

The v1-repl image intentionally keeps the v2321 native-init identity string, so `version` alone does
not distinguish it from the clean rollback image. The REPL selftest is the functional proof that the
candidate kernel REPL path is resident.

## Live Proof

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-proof \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --timeout 180 --dmesg-tail 80 --safe-op-retries 5 --retry-delay-sec 0.75 \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --evidence-dir workspace/private/runs/kernel/live-call-proof-cpumask-next-wrap-20260630/proof \
  cpumask_next_wrap
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-cpumask_next_wrap-pass",
  "ok": true,
  "proof_status": "trusted-under-owned-input-contract",
  "input_contract": "scalar int n + owned cpumask buffer with compiled nr_cpumask_bits=8 + scalar start + scalar wrap-state",
  "return_contract": "int == next set CPU in wrap iterator order, or 8 when the iterator reaches the start boundary/no set CPU exists",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Case table:

| Case | Set CPU bits | n | start | wrap | Expected | Observed |
| --- | --- | ---: | ---: | ---: | --- | --- |
| initial-forward-hit | `2,6` | 3 | 4 | 0 | `0x6` | `0x6` |
| initial-wrap-low-hit | `2` | 3 | 4 | 0 | `0x2` | `0x2` |
| wrapped-low-next | `2,6` | 1 | 4 | 1 | `0x2` | `0x2` |
| wrapped-tail-wrap-low-hit | `2,6` | 6 | 4 | 1 | `0x2` | `0x2` |
| wrapped-crosses-start-stop | `2,6` | 2 | 4 | 1 | `0x8` | `0x8` |
| empty-mask | empty | 3 | 4 | 0 | `0x8` | `0x8` |

Checks:

- `static-c1-identity`: OK, `cpumask_next_wrap` resolved by `export-recovery`.
- `static-source-contract`: OK, signature matches the source oracle and pointer arg indices are `[1]`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x1 `cpumask-buffer`.
- `static-compiled-nr-cpumask-bits`: OK, wrapper word `0x52800101` matched compiled 8-bit mask.
- `static-sentinel-nr-cpumask-bits`: OK, sentinel word `0x52800117` matched compiled 8-bit mask.
- `kmalloc-owned-cpumask-next-wrap-mask`: OK, owned kernel cpumask allocation returned sane lowmem.
- `cpumask-next-wrap-case-table`: OK, all 6 calls returned expected CPU indices or sentinel `8`.
- Per-case immutability: OK, cpumask and canary stayed unchanged after every call.
- `kfree-owned-cpumask-next-wrap-mask`: OK.

Raw per-boot slide, target runtime address, owned allocation pointer, and observed bytes were written
only to private evidence and are not included in this report.

Candidate selftest after proof: `pass=11 warn=1 fail=0`.

## Rollback

Rollback command:

```sh
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  --from-native \
  --expect-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb \
  --expect-readback-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb \
  workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img
```

Result:

- Remote pushed image SHA matched rollback SHA.
- Boot readback SHA matched rollback SHA.
- Post-rollback `version/status` verification passed.
- Final standalone selftest returned `pass=11 warn=1 fail=0`.

## Function Map Update

Add `cpumask_next_wrap` as `live-proven` only under this contract:

- Static link identity: `0xffffff80099a9f1c`, `export-recovery`, direct BL xrefs `6`.
- Trusted input contract: scalar int `n`, owned cpumask buffer with compiled `nr_cpumask_bits=8`,
  scalar `start`, scalar wrap-state.
- Observed result: forward hit, initial low wrap hit, wrapped low next, tail-to-low wrap hit,
  start-boundary sentinel, and empty-mask sentinel cases.
- Cleanup: `kfree-owned-cpumask-next-wrap-mask-ok`.

This does not authorize arbitrary cpumask pointers, wider CPU masks, `cpumask_next_and`, arbitrary
iteration states, or mass calling.

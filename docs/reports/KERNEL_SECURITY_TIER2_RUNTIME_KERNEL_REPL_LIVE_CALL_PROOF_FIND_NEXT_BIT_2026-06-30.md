# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: find_next_bit

- Date: 2026-06-30
- Decision: `a90-repl-live-call-proof-find_next_bit-pass`
- Scope: separately gated one-target live-call proof after the REPL epic close.
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-find-next-bit-20260630/proof/a90_repl_evidence.json`

## Candidate Selection

This unit followed the `find_next_zero_bit` proof with the adjacent positive bitmap scanner instead
of carrying trust across the bit-search family. The candidate is still a pointer-reading bitmap
helper, so it needed its own one-target contract, static gate, live result table, immutability check,
and cleanup check.

The selected target was `find_next_bit`: it has a clean exported identity, leaf/no-BL shape, and a
source signature that declares only x0 as the pointer argument. The static analyzer conservatively
flags x1/x2 size/offset address-flow because they influence where the bitmap read occurs. This proof
therefore builds an owned bitmap inside the kernel and bounds all scalar size/offset arguments inside
that allocation.

## Static Gate

Target:

- `find_next_bit`: `0xffffff8008564e2c`
- Resolution method: `export-recovery`
- Direct BL xrefs: `564`
- Shape: JOPP entry, leaf/no-BL, RET observed.
- Disasm contract: bitmap memory is read through x0; no tainted-argument call was observed.
- Source signature: `include/asm-generic/bitops/find.h:15`,
  `extern unsigned long find_next_bit(const unsigned long *addr, unsigned long size, unsigned long offset)`
- Source pointer contract: x0 is `const unsigned long *addr`; x1/x2 are scalar size/offset.
- Call-safety tier: `SAFE-WITH-VALID-PTR`
- Required valid pointer args: x0 `bitmap-buffer`.

The target was not called with an arbitrary numeric pointer. The proof first allocates an owned
kernel bitmap, writes a fixed two-word bitmap plus canary, peeks it back, calls only the verified
target with bounded scalar size/offset cases, re-peeks the bitmap/canary, and frees the allocation.

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
  find_next_bit

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_a90_repl.CallSafetyClassificationTests.test_proven_live_call_targets_stay_safe \
  tests.test_a90_repl.CallSafetyClassificationTests.test_seed_inventory_summary_counts_tiers \
  tests.test_a90_repl.CallSafetyClassificationTests.test_source_signature_oracle_distinguishes_scalar_and_pointer_args \
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_find_next_bit_passes_with_owned_bitmap_contract

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_repl
```

Result:

- `py_compile`: pass.
- CLI classify: `SAFE-WITH-VALID-PTR`, verified by `export-recovery`, direct-BL xrefs `564`,
  leaf/no-BL, required x0 `bitmap-buffer`.
- Focused tests: static classification/source tests and the new fake-transport proof passed.
- Full `tests.test_a90_repl`: `Ran 130 tests`, `OK`.

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
  --evidence-dir workspace/private/runs/kernel/live-call-proof-find-next-bit-20260630/proof \
  find_next_bit
```

Public result:

```json
{
  "decision": "a90-repl-live-call-proof-find_next_bit-pass",
  "ok": true,
  "proof_status": "trusted-under-owned-input-contract",
  "input_contract": "owned unsigned-long bitmap buffer + scalar bit size + scalar offset inside that bitmap",
  "return_contract": "unsigned long == first set bit index >= offset, or size when no set bit exists",
  "raw_runtime_values_redacted": true,
  "owned_pointer_redacted": true,
  "observed_bytes_redacted": true
}
```

Case table:

| Case | Size bits | Offset bits | Expected | Observed |
| --- | ---: | ---: | --- | --- |
| first-one-low-word | 128 | 0 | `0x9` | `0x9` |
| skip-low-one | 128 | 10 | `0x49` | `0x49` |
| full-size-third-one | 128 | 74 | `0x5a` | `0x5a` |
| bounded-second-word-hit | 80 | 64 | `0x49` | `0x49` |
| bounded-tail-miss-before-third | 88 | 74 | `0x58` | `0x58` |
| no-one-after-third | 128 | 91 | `0x80` | `0x80` |

Checks:

- `static-c1-identity`: OK, `find_next_bit` resolved by `export-recovery`.
- `static-source-contract`: OK, signature matches the source oracle and pointer arg indices are `[0]`.
- `static-call-safety-contract`: OK, tier `SAFE-WITH-VALID-PTR`, x0 `bitmap-buffer`.
- `kmalloc-owned-find-next-bit-bitmap`: OK, owned kernel bitmap allocation returned sane lowmem.
- `owned-find-next-bit-bitmap-poke-peek`: OK, 128-bit bitmap had set bits at `9`, `73`, and `90`.
- `find-next-bit-case-table`: OK, all 6 calls returned expected bit indices.
- `find-next-bit-bitmap-immutability`: OK, bitmap and canary stayed unchanged.
- `kfree-owned-find-next-bit-bitmap`: OK.

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

- Remote pushed image SHA matched v2321 SHA.
- Boot readback SHA matched v2321 SHA.
- Post-rollback `version/status` verification passed.
- Final resident: `v2321-usb-clean-identity-rodata`.
- The first standalone final selftest read hit serial noise; bridge status and `version` then passed,
  and the retried standalone selftest returned `pass=11 warn=1 fail=0`.

## Conclusion

`find_next_bit` is now live-proven under an owned unsigned-long bitmap contract with scalar size and
offset bounded inside that bitmap. The proof confirms the intended exported helper was reached,
returned the expected first-set or size result for low-word, high-word, full-size third-hit,
bounded-tail miss, and post-third miss cases, did not modify the bitmap/canary, and cleaned up the
owned allocation. This does not authorize arbitrary bitmap pointers, unbounded sizes, negative or
out-of-allocation offsets, broader bitops state, or mass calling. The device was rolled back to clean
v2321 with final `selftest fail=0`.

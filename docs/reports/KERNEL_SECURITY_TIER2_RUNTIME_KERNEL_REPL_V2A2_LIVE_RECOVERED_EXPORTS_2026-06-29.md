# Kernel Security Tier-2 Runtime Kernel REPL v2a2 - Live Poke Round-Trip via Recovered Exports

- Date: 2026-06-29
- Decision: `a90-repl-v2a2-poke-roundtrip-pass`
- Device action: yes, boot partition only through `native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/v2a2-repl-poke-roundtrip/live-evidence-v2a2rp/a90_repl_evidence.json`

## Static Gate

Before live rerun, the recovered allocator addresses from v2a2R' were cross-checked with host objdump and
xref telemetry.

Recovered link addresses used for the live run:

- `__kmalloc`: `0xffffff800826ae34`
- `kfree`: `0xffffff800826b354`

Static signals:

- `__kmalloc` first block preserves `x0` as scalar size (`mov x20,x0`, `cmp x0,#0x2,lsl #12`,
  `mov x0,x20`, `mov w1,w19`, then first `BL`); no pre-first-`BL` `x0` dereference.
- `kfree` first block preserves `x0` as pointer (`mov x22,x0`) and enters the free path; no
  pre-first-`BL` `x0` dereference.
- `__kmalloc` direct `bl` xrefs: `1765`.
- `kfree` direct `bl` xrefs: `10596`.

This closes the operator Gate-2 correction: the previous failure was a System.map mm/slab-region
mislabel, not an allocator ABI problem.

## Flash And Health

Preconditions:

- Rollback images were present:
  - v2321 SHA matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
  - v2237 SHA matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
  - final fallback `boot_linux_v48.img` existed
- TWRP recovery image existed at `workspace/private/inputs/firmware/twrp/recovery.img`
- Bridge was connected to `/dev/ttyACM0`.
- Baseline v2321 health before flash: `version`/`status` OK, `selftest pass=11 warn=1 fail=0`.

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
- Post-flash `selftest verbose` passed: `pass=11 warn=1 fail=0`.

One immediate post-flash selftest attempt hit serial fragment noise (`ATAT` / missing `A90P1 END`), then
`version` realigned the bridge and the selftest retry passed. The fragment did not indicate device health
failure.

## Live Round-Trip

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/a90_repl.py poke-roundtrip \
    --map workspace/private/runs/kernel/v2a2-repl-poke-roundtrip/System.map \
    --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
    --use-recovered-allocator-exports \
    --timeout 60 \
    --dmesg-tail 80 \
    --evidence-dir workspace/private/runs/kernel/v2a2-repl-poke-roundtrip/live-evidence-v2a2rp
```

Public result:

```json
{
  "decision": "a90-repl-v2a2-poke-roundtrip-pass",
  "ok": true,
  "allocator_address_source": "allocator-export-recovery",
  "allocator_link_vaddrs": {
    "__kmalloc": "0xffffff800826ae34",
    "kfree": "0xffffff800826b354"
  },
  "gfp_kernel": "0x14000c0"
}
```

Checks:

- `kmalloc-owned-buffer`: OK, returned pointer was non-null kernel lowmem.
- `poke-peek-qword` sentinel A: OK.
- `poke-peek-qword` sentinel B: OK.
- `poke-peek-low32`: OK, high 32 bits preserved and low 32 bits changed.
- `kfree-owned-buffer`: OK.

Raw runtime slide and allocation pointer were written only to private evidence and are not included in
this report.

Cleanup on candidate:

- `panic_on_oops`: `1`
- Candidate selftest after live run: `pass=11 warn=1 fail=0`

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
- Final `selftest verbose`: `pass=11 warn=1 fail=0`.
- Final `panic_on_oops`: `1`.

One immediate final selftest attempt also hit serial fragment noise, but `version` realigned the bridge and
the selftest retry passed with a clean `A90P1 END` marker.

## Conclusion

v2a2 is live-proven. The existing v1-repl image can call the real recovered `__kmalloc`, write to the
owned allocation with `op2`, read the written values back with `op1`, exercise the 32-bit write path, and
free the allocation with recovered `kfree`. The device was rolled back to clean v2321 with final
`selftest fail=0`.

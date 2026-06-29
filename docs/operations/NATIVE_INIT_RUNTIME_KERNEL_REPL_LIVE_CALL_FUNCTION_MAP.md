# Native-Init Runtime Kernel REPL Live-Call Function Map

Date: 2026-06-29

Scope: redacted public map of functions that have live-call evidence under the runtime kernel REPL.
This is not an autonomous call allowlist. Each row is trusted only under the listed input contract
and the C1 fail-closed identity gate.

## Guardrails

- Static link addresses are allowed in this document; per-boot slide, runtime addresses, and owned
  allocation pointers stay only in `workspace/private/`.
- `call-safety-sweep` candidates remain advisory until a separate one-target proof runs.
- `SAFE-WITH-VALID-PTR` means the tool must create or verify the pointer; arbitrary numeric pointer
  arguments are not trusted by this map.
- A row status of `live-proven` does not authorize mass calling or recursive candidate probing.

## Live-Proven Rows

| Symbol | Static link identity | Trusted input contract | Observed result | Cleanup | Evidence |
| --- | --- | --- | --- | --- | --- |
| `printk` | `0xffffff800813adfc`, `export-recovery`, max direct-BL variadic wrapper | `@repl_format` format pointer plus scalar sentinel | sentinel echoed through `printk(format, sentinel)` | n/a | v2a1 named-call proof |
| `__kmalloc` | `0xffffff800826ae34`, `export-recovery`, direct BL xrefs `1765` | scalar `size`, scalar `gfp` | returned sane kernel lowmem owned pointer | caller-owned cleanup required | v2a2 recovered-export poke round-trip |
| `kfree` | `0xffffff800826b354`, `export-recovery`, direct BL xrefs `10596` | owned `kmalloc` object pointer or NULL | cleanup call returned through REPL | freed owned allocation | v2a2 recovered-export poke round-trip |
| `ksize` | `0xffffff800826b27c`, `export-recovery`, direct BL xrefs `39` | owned `__kmalloc` pointer generated inside `call-proof` | `ksize(0x1000 allocation) == 0x1000`, within `[0x1000, 0x2000]` | `kfree-owned-buffer-ok` | `a90-repl-live-call-proof-ksize-pass` |
| `filp_open` | `0xffffff800828a664`, `export-recovery`, direct BL xrefs `48` | owned kernel pathname buffer containing `/init`, `O_RDONLY`, mode `0` | sane `struct file *`, not NULL and not ERR_PTR | `filp_close` returned `0` | `a90-repl-live-call-proof-filp_open-pass` |
| `filp_close` | `0xffffff800828ac14`, `export-recovery`, direct BL xrefs `67` | cleanup only: `struct file *` returned by the paired `filp_open` proof | returned `0` | closed opened file | paired cleanup evidence from `a90-repl-live-call-proof-filp_open-pass` |
| `kernel_read` | `0xffffff800828bae4`, `export-recovery`, direct BL xrefs `17` | `filp_open(/init)` file pointer plus owned read buffer plus owned `loff_t *` position | `kernel_read(file, buf, 16, pos) == 0x10`, buffer prefix `7f454c46`, pos advanced to `0x10` | `filp_close` returned `0`; owned path/read/pos buffers freed | `a90-repl-live-call-proof-kernel_read-pass` |

## Parked Candidate Families

- Allocator sweep: only `ksize` has crossed the live proof gate beyond the allocator primitives
  already required for owned-buffer orchestration.
- Read-I/O sweep: `filp_open`, cleanup-only `filp_close`, and `kernel_read` have crossed the live
  proof gate only under their paired owned `/init` file/buffer/position contracts. Broader read paths,
  arbitrary file pointers, and arbitrary destination buffers remain parked until separate contracts are
  proven.

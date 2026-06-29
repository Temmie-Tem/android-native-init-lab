# Native-Init Runtime Kernel REPL Live-Call Function Map

Date: 2026-06-30

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
| `strlen` | `0xffffff80099a8cc0`, `leaf-map-disasm+xref`, direct BL xrefs `2073`, leaf/no-BL | owned NUL-terminated kernel string buffer | `strlen("A90STRLEN") == 0x9` | `kfree-owned-string-buffer-ok` | `a90-repl-live-call-proof-strlen-pass` |
| `strnlen` | `0xffffff80099a8f4c`, `leaf-map-disasm+xref`, direct BL xrefs `473`, leaf/no-BL | owned NUL-terminated kernel string buffer plus scalar `maxlen` | `strnlen("A90STRNLEN", 64) == 0xa` | `kfree-owned-string-buffer-ok` | `a90-repl-live-call-proof-strnlen-pass` |
| `strscpy` | `0xffffff80099b9794`, `export-recovery`, direct BL xrefs `8`, leaf/no-BL | owned destination buffer plus owned NUL-terminated source string buffer plus bounded size | `strscpy(dst, "A90STRSCPY", 32) == 0xa`, destination prefix matched source, canary after size preserved | `kfree-owned-strscpy-buffers-ok` | `a90-repl-live-call-proof-strscpy-pass` |
| `strlcpy` | `0xffffff80099b9724`, `export-recovery`, direct BL xrefs `963`, calls `__pi_strlen`/`__memcpy` | owned destination buffer plus owned NUL-terminated source string buffer plus bounded size | `strlcpy(dst, "A90STRLCPY", 32) == 0xa`, destination prefix matched source, canary after size preserved | `kfree-owned-strlcpy-buffers-ok` | `a90-repl-live-call-proof-strlcpy-pass` |
| `strncpy` | `0xffffff80099b96f4`, `export-recovery`, direct BL xrefs `187`, leaf/no-BL | owned destination buffer plus owned NUL-terminated source string buffer plus bounded count | `strncpy(dst, "A90STRNCPY", 32)` returned the owned destination pointer (redacted), destination prefix matched source, NUL padded to count, canary after count preserved | `kfree-owned-strncpy-buffers-ok` | `a90-repl-live-call-proof-strncpy-pass` |

## Parked Candidate Families

- Allocator sweep: only `ksize` has crossed the live proof gate beyond the allocator primitives
  already required for owned-buffer orchestration.
- Read-I/O sweep: `filp_open`, cleanup-only `filp_close`, and `kernel_read` have crossed the live
  proof gate only under their paired owned `/init` file/buffer/position contracts. Broader read paths,
  arbitrary file pointers, and arbitrary destination buffers remain parked until separate contracts are
  proven.
- String sweep: `strlen`, `strnlen`, `strscpy`, `strlcpy`, and `strncpy` have crossed the live proof gate only under
  owned NUL-terminated kernel string/buffer contracts. `strnlen` additionally requires the scalar
  `maxlen` contract; `strscpy`, `strlcpy`, and `strncpy` additionally require an owned destination
  buffer and a bounded size/count inside that destination. Other string/memory helpers remain parked
  until separate C1 identity and pointer contracts are proven.

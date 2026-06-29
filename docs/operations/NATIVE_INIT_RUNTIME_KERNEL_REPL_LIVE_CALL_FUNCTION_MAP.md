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
| `strnchr` | `0xffffff80099b99a4`, `export-recovery`, direct BL xrefs `45`, leaf/no-BL | owned NUL-terminated kernel string buffer plus scalar bounded count and scalar search byte | `strnchr("A90STRNCHR-HEAD-Q-TAIL-Q", 24, 'Q')` returned the owned string pointer at offset `16` (redacted); boundary count `16` returned `0x0`; string stayed unchanged | `kfree-owned-strnchr-string-buffer-ok` | `a90-repl-live-call-proof-strnchr-pass` |
| `skip_spaces` | `0xffffff80099b99d4`, `export-recovery`, direct BL xrefs `52`, first RET offset `0x18` | owned NUL-terminated kernel string buffer | `skip_spaces("   A90SKIP-SPACES")` returned the owned string pointer at offset `3` (redacted); no-leading string `A90SKIP-NO-LEADING` returned the original owned pointer (redacted); string stayed unchanged | `kfree-owned-skip-spaces-string-buffer-ok` | `a90-repl-live-call-proof-skip_spaces-pass` |
| `strim` | `0xffffff80099b99f4`, `export-recovery`, direct BL xrefs `59`, calls `__pi_strlen` | owned mutable NUL-terminated kernel string buffer | `strim("   A90STRIM-BODY   ")` returned the owned string pointer at offset `3` (redacted) and replaced the first trailing space at offset `16` with NUL; clean string `A90STRIM-CLEAN` returned the original owned pointer (redacted) and stayed unchanged | `kfree-owned-strim-string-buffer-ok` | `a90-repl-live-call-proof-strim-pass` |
| `strreplace` | `0xffffff80099ba12c`, `export-recovery`, direct BL xrefs `15`, leaf/no-BL | owned mutable NUL-terminated kernel string buffer plus scalar old/new bytes | `strreplace("A90STRREPLACE-Q-Q-END", 'Q', 'Z')` returned the owned NUL terminator pointer at offset `21` (redacted), replaced both `Q` bytes with `Z`, and preserved canary; missing byte `@` returned the same NUL pointer and left the string unchanged | `kfree-owned-strreplace-string-buffer-ok` | `a90-repl-live-call-proof-strreplace-pass` |
| `strchr` | `0xffffff80099a8b48`, `leaf-map-disasm+xref`, direct BL xrefs `127`, leaf/no-BL | owned NUL-terminated kernel string buffer plus scalar search byte | `strchr("A90STRCHR-Q-B-Q-Z", 'Q')` returned the owned pointer at offset `10` (redacted); missing `@` returned `0x0`; string stayed unchanged | `kfree-owned-strchr-string-buffer-ok` | `a90-repl-live-call-proof-strchr-pass` |
| `strchrnul` | `0xffffff80099b9984`, `export-recovery`, direct BL xrefs `7`, leaf/no-BL | owned NUL-terminated kernel string buffer plus scalar search byte | `strchrnul("A90STRCHRNUL-Q-B-Q-Z", 'Q')` returned the owned pointer at offset `13` (redacted); missing `@` returned the owned NUL-terminator pointer at offset `20` (redacted); string stayed unchanged | `kfree-owned-strchrnul-string-buffer-ok` | `a90-repl-live-call-proof-strchrnul-pass` |
| `strstr` | `0xffffff80099b9ebc`, `export-recovery`, direct BL xrefs `50`, calls `__pi_strlen`/`__pi_memcmp` | owned NUL-terminated haystack and needle kernel string buffers | `strstr("A90STRSTR-HEAD-NEEDLE-TAIL", "NEEDLE")` returned the owned haystack pointer at offset `15` (redacted); missing needle `ABSENT` returned `0x0`; both strings stayed unchanged | `kfree-owned-strstr-strings-ok` | `a90-repl-live-call-proof-strstr-pass` |
| `strpbrk` | `0xffffff80099b9b34`, `export-recovery`, direct BL xrefs `40`, leaf/no-BL | owned NUL-terminated haystack and accept-set kernel string buffers | `strpbrk("A90STRPBRK-HEAD-Q-TAIL-Z", "QZ")` returned the owned haystack pointer at offset `16` (redacted); missing accept set `xy` returned `0x0`; both strings stayed unchanged | `kfree-owned-strpbrk-strings-ok` | `a90-repl-live-call-proof-strpbrk-pass` |
| `strcmp` | `0xffffff80099a8b6c`, `leaf-map-disasm+xref`, direct BL xrefs `3507`, leaf/no-BL | two owned NUL-terminated kernel string buffers | equal string compare returned `0x0`; first-difference case returned positive (`0xd0`); both strings stayed unchanged | `kfree-owned-strcmp-strings-ok` | `a90-repl-live-call-proof-strcmp-pass` |
| `strncmp` | `0xffffff80099a8d44`, `leaf-map-disasm+xref`, direct BL xrefs `590`, leaf/no-BL | two owned NUL-terminated kernel string buffers plus bounded count inside both buffers | `strncmp("A90STRNCMP-PREFIXZ-LEFT", "A90STRNCMP-PREFIX@-RIGHT", 17) == 0x0` despite post-count byte difference; count-internal mismatch at offset `3` returned positive (`0x98`); both strings stayed unchanged | `kfree-owned-strncmp-strings-ok` | `a90-repl-live-call-proof-strncmp-pass` |
| `strnlen` | `0xffffff80099a8f4c`, `leaf-map-disasm+xref`, direct BL xrefs `473`, leaf/no-BL | owned NUL-terminated kernel string buffer plus scalar `maxlen` | `strnlen("A90STRNLEN", 64) == 0xa` | `kfree-owned-string-buffer-ok` | `a90-repl-live-call-proof-strnlen-pass` |
| `strrchr` | `0xffffff80099a900c`, `leaf-map-disasm+xref`, direct BL xrefs `1405`, leaf/no-BL | owned NUL-terminated kernel string buffer plus scalar search byte | `strrchr("A90STRRCHR-A-B-A-Z", 'A')` returned the owned pointer at offset `15` (redacted); missing `@` returned `0x0`; string stayed unchanged | `kfree-owned-strrchr-string-buffer-ok` | `a90-repl-live-call-proof-strrchr-pass` |
| `strscpy` | `0xffffff80099b9794`, `export-recovery`, direct BL xrefs `8`, leaf/no-BL | owned destination buffer plus owned NUL-terminated source string buffer plus bounded size | `strscpy(dst, "A90STRSCPY", 32) == 0xa`, destination prefix matched source, canary after size preserved | `kfree-owned-strscpy-buffers-ok` | `a90-repl-live-call-proof-strscpy-pass` |
| `strlcpy` | `0xffffff80099b9724`, `export-recovery`, direct BL xrefs `963`, calls `__pi_strlen`/`__memcpy` | owned destination buffer plus owned NUL-terminated source string buffer plus bounded size | `strlcpy(dst, "A90STRLCPY", 32) == 0xa`, destination prefix matched source, canary after size preserved | `kfree-owned-strlcpy-buffers-ok` | `a90-repl-live-call-proof-strlcpy-pass` |
| `strncpy` | `0xffffff80099b96f4`, `export-recovery`, direct BL xrefs `187`, leaf/no-BL | owned destination buffer plus owned NUL-terminated source string buffer plus bounded count | `strncpy(dst, "A90STRNCPY", 32)` returned the owned destination pointer (redacted), destination prefix matched source, NUL padded to count, canary after count preserved | `kfree-owned-strncpy-buffers-ok` | `a90-repl-live-call-proof-strncpy-pass` |
| `memcmp` | `0xffffff80099a84b0`, `leaf-map-disasm+xref`, direct BL xrefs `921`, leaf/no-BL | two owned initialized buffers plus bounded size inside both buffers | equal buffer compare returned `0x0`; first-difference case returned positive (`0x80`); both buffers stayed unchanged | `kfree-owned-memcmp-buffers-ok` | `a90-repl-live-call-proof-memcmp-pass` |
| `memchr` | `0xffffff80099a8488`, `leaf-map-disasm+xref`, direct BL xrefs `25`, leaf/no-BL | owned initialized buffer plus scalar search byte plus bounded size inside the buffer | `memchr("A90MEMCHR-HIT-Q-END-012345", 'Q', 26)` returned the owned pointer at offset `14` (redacted); missing `@` returned `0x0` even though the post-size canary contained `@`; buffer stayed unchanged | `kfree-owned-memchr-buffer-ok` | `a90-repl-live-call-proof-memchr-pass` |
| `memcpy` | `0xffffff80099a8680`, `leaf-map-disasm+xref`, direct BL xrefs `6227`, leaf/no-BL | distinct owned destination/source buffers plus bounded size inside both buffers | `memcpy(dst, "A90MEMCPY-SRC-0123456789ABCDEF", 30)` returned the owned destination pointer (redacted), destination first 30 bytes matched source, destination post-size canary preserved, source buffer stayed unchanged | `kfree-owned-memcpy-buffers-ok` | `a90-repl-live-call-proof-memcpy-pass` |
| `memmove` | `0xffffff80099a8800`, `leaf-map-disasm+xref`, direct BL xrefs `165`, leaf/no-BL | same owned buffer with overlapping destination/source ranges plus bounded size inside allocation | `memmove(buf+5, buf, 29)` returned the owned destination pointer (redacted), final buffer matched overlap-safe snapshot-copy semantics, post-move canary preserved | `kfree-owned-memmove-overlap-buffer-ok` | `a90-repl-live-call-proof-memmove-pass` |
| `memset` | `0xffffff80099a8980`, `leaf-map-disasm+xref`, direct BL xrefs `6517`, leaf/no-BL | owned destination buffer plus scalar fill byte plus bounded size inside destination | `memset(dst, 0x5a, 32)` returned the owned destination pointer (redacted), first 32 bytes became `0x5a`, post-size canary preserved | `kfree-owned-memset-destination-buffer-ok` | `a90-repl-live-call-proof-memset-pass` |

## Parked Candidate Families

- Allocator sweep: only `ksize` has crossed the live proof gate beyond the allocator primitives
  already required for owned-buffer orchestration.
- Read-I/O sweep: `filp_open`, cleanup-only `filp_close`, and `kernel_read` have crossed the live
  proof gate only under their paired owned `/init` file/buffer/position contracts. Broader read paths,
  arbitrary file pointers, and arbitrary destination buffers remain parked until separate contracts are
  proven.
- String sweep: `strlen`, `strnchr`, `skip_spaces`, `strim`, `strreplace`, `strchr`, `strchrnul`, `strstr`, `strpbrk`, `strcmp`, `strncmp`, `strnlen`, `strrchr`,
  `strscpy`, `strlcpy`, and
  `strncpy` have crossed the live proof gate only under owned NUL-terminated kernel string/buffer
  contracts. `strnchr` additionally requires scalar bounded count/search-byte args and only proves
  one hit inside count plus one boundary-count NULL case; `skip_spaces` additionally requires a valid
  owned string pointer and only proves leading ASCII space skip to offset `3` plus the no-leading-space identity case; `strim`
  additionally requires a mutable owned string pointer and only proves leading/trailing ASCII space
  trimming with bounded first-trailing-space NUL mutation plus the clean-string identity case;
  `strreplace` additionally requires a mutable owned string pointer plus scalar old/new bytes and only
  proves bounded byte replacement plus a missing-byte no-op case; `strchr` additionally
  requires a scalar search byte and only proves first-occurrence
  hit plus missing-byte-returns-NULL cases; `strchrnul` additionally requires a scalar search byte
  and only proves first-occurrence hit plus missing-byte-returns-NUL-terminator cases; `strstr`
  additionally requires owned haystack and needle strings and only proves one present substring plus
  one missing-needle NULL case; `strpbrk` additionally requires owned haystack and accept-set strings
  and only proves one present accept-set hit plus one missing accept-set NULL case; `strcmp`
  additionally requires two owned terminated strings and only proves equal/positive-sign compare
  cases; `strncmp` additionally requires two owned terminated strings plus a scalar bounded count
  inside both buffers and only proves bounded-equal plus positive-sign mismatch cases; `strnlen`
  additionally requires the scalar `maxlen` contract; `strrchr` additionally
  requires a scalar search byte and a terminated owned string; `strscpy`, `strlcpy`, and `strncpy`
  additionally require an owned destination buffer and a bounded size/count inside that destination.
  Other string/memory helpers remain parked until separate C1 identity and pointer contracts are
  proven.
- Memory-search/compare sweep: `memcmp` has crossed the live proof gate only under the two-owned-buffer
  plus bounded-size contract. `memchr` has crossed the live proof gate only under the owned-buffer plus
  scalar-search-byte and bounded-size contract, including a canary check that the search stays inside
  the size argument. These rows do not authorize arbitrary pointers, unbounded sizes, user pointers, or
  other memory helpers.
- Memory-write sweep: `memset` has crossed the live proof gate only under the owned destination plus
  scalar-fill-byte and bounded-size contract. `memcpy` has crossed the live proof gate only under the
  distinct-owned-destination/source-buffer plus bounded-size contract with non-overlapping allocation
  ranges. `memmove` has crossed the live proof gate only under the same-owned-buffer `dst=src+5`,
  bounded-size overlap contract. These rows do not authorize arbitrary pointers, unbounded sizes, user
  pointers, or broader overlap shapes without separate proof.

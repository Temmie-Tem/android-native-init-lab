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
| `hex_to_bin` | `0xffffff800856a9dc`, `export-recovery`, direct BL xrefs `80`, leaf/no-BL | scalar ASCII character | case table: `'0' -> 0`, `'9' -> 9`, `'a'/'A' -> 10`, `'f'/'F' -> 15`, invalid `'g' -> 0xffffffff` | n/a-scalar-only | `a90-repl-live-call-proof-hex_to_bin-pass` |
| `__sw_hweight32` | `0xffffff800856d844`, `export-recovery`, direct BL xrefs `36`, leaf/no-BL | scalar unsigned 32-bit word | case table: `0x00000000 -> 0`, `0xffffffff -> 32`, `0xaaaaaaaa -> 16`, `0x80000000 -> 1`, `0xa90f00dc -> 13` | n/a-scalar-only | `a90-repl-live-call-proof-__sw_hweight32-pass` |
| `__sw_hweight64` | `0xffffff800856d8e4`, `export-recovery`, direct BL xrefs `228`, leaf/no-BL | scalar unsigned 64-bit word | case table: `0x0000000000000000 -> 0`, `0xffffffffffffffff -> 64`, `0xaaaaaaaaaaaaaaaa -> 32`, `0x8000000000000000 -> 1`, `0xa90f00dca90f00dc -> 26` | n/a-scalar-only | `a90-repl-live-call-proof-__sw_hweight64-pass` |
| `__sw_hweight16` | `0xffffff800856d87c`, `export-recovery`, direct BL xrefs `19`, leaf/no-BL | scalar unsigned 16-bit word in the low x0 bits | case table: `0x0000 -> 0`, `0xffff -> 16`, `0xaaaa -> 8`, `0x8000 -> 1`, `0xa90d -> 7` | n/a-scalar-only | `a90-repl-live-call-proof-__sw_hweight16-pass` |
| `__sw_hweight8` | `0xffffff800856d8b4`, `export-recovery`, direct BL xrefs `23`, leaf/no-BL | scalar unsigned 8-bit byte in the low x0 bits | case table: `0x00 -> 0`, `0xff -> 8`, `0xaa -> 4`, `0x80 -> 1`, `0xa9 -> 4` | n/a-scalar-only | `a90-repl-live-call-proof-__sw_hweight8-pass` |
| `__bitmap_weight` | `0xffffff800855cdd4`, `export-recovery`, direct BL xrefs `19`, non-leaf wrapper calls `__sw_hweight64` | owned unsigned-long bitmap buffer plus scalar bit count bounded inside that bitmap | case table: `nbits=0 -> 0`, `nbits=10 -> 3`, `nbits=64 -> 5`, `nbits=80 -> 7`, `nbits=91 -> 8`, `nbits=127 -> 8`, `nbits=128 -> 9`; bitmap and canary stayed unchanged | `kfree-owned-bitmap-weight-bitmap-ok` | `a90-repl-live-call-proof-__bitmap_weight-pass` |
| `__bitmap_complement` | `0xffffff800855c8e4`, `export-recovery`, direct BL xrefs `1`, leaf/no-BL | owned destination unsigned-long bitmap buffer plus owned source unsigned-long bitmap buffer plus scalar bit count bounded inside both bitmaps | case table: `nbits=0` left destination unchanged, `nbits=10` complemented the first word tail path, `nbits=64` complemented the first word only, `nbits=80` complemented the first and second words through the tail path, `nbits=128` complemented both words; source bitmap and both canaries stayed unchanged | `kfree-owned-bitmap-complement-buffers-ok` | `a90-repl-live-call-proof-__bitmap_complement-pass` |
| `__bitmap_or` | `0xffffff800855cbb4`, `export-recovery`, direct BL xrefs `2`, leaf/no-BL | owned destination unsigned-long bitmap buffer plus two owned source unsigned-long bitmap buffers plus scalar bit count bounded inside all three bitmaps | case table: zero-size partial right -> no-op, low-tail and first-word boundary -> first-word OR result, second-word tail and full-size -> two-word OR result, full right bitmap -> two-word OR result; left/right buffers and canaries stayed unchanged | `kfree-owned-bitmap-or-buffers-ok` | `a90-repl-live-call-proof-__bitmap_or-pass` |
| `__bitmap_set` | `0xffffff800855ce7c`, `export-recovery`, direct BL xrefs `24`, leaf/no-BL | owned unsigned-long bitmap buffer plus scalar `start` and `len` bounded inside that bitmap | case table: zero-length no-op, low single-bit set, low range set, cross-word range set, second-word range set, and full-size set; bitmap matched expected range-set bytes and canary stayed unchanged | `kfree-owned-bitmap-set-buffer-ok` | `a90-repl-live-call-proof-__bitmap_set-pass` |
| `__bitmap_clear` | `0xffffff800855cf14`, `export-recovery`, direct BL xrefs `33`, leaf/no-BL | owned unsigned-long bitmap buffer plus scalar `start` and `len` bounded inside that bitmap | case table: zero-length no-op, low single-bit clear, low range clear, cross-word range clear, second-word range clear, and full-size clear; bitmap matched expected range-clear bytes and canary stayed unchanged | `kfree-owned-bitmap-clear-buffer-ok` | `a90-repl-live-call-proof-__bitmap_clear-pass` |
| `__bitmap_andnot` | `0xffffff800855cc24`, `export-recovery`, direct BL xrefs `1`, leaf/no-BL | owned destination unsigned-long bitmap buffer plus owned source and mask unsigned-long bitmap buffers plus scalar bit count bounded inside all three bitmaps | case table: zero-size partial mask -> `0`, low-tail/first-word/second-word/bit90/full-size partial-mask positives -> `1`, full-size full-mask negative -> `0`; destination matched `source & ~mask` for each case, source/mask buffers and canaries stayed unchanged | `kfree-owned-bitmap-andnot-buffers-ok` | `a90-repl-live-call-proof-__bitmap_andnot-pass` |
| `__bitmap_subset` | `0xffffff800855cd3c`, `export-recovery`, direct BL xrefs `3`, leaf/no-BL | two owned unsigned-long bitmap buffers plus scalar bit count bounded inside both bitmaps | case table: zero-size nonempty source -> `1`, empty source full-size -> `1`, low-tail/first-word/second-word-before-missing positives -> `1`, include missing bit 90 -> `0`, full-size partial mask -> `0`, full-size full mask -> `1`; all bitmaps and canaries stayed unchanged | `kfree-owned-bitmap-subset-buffers-ok` | `a90-repl-live-call-proof-__bitmap_subset-pass` |
| `find_next_bit` | `0xffffff8008564e2c`, `export-recovery`, direct BL xrefs `564`, leaf/no-BL | owned unsigned-long bitmap buffer plus scalar bit size and scalar offset inside that bitmap | case table: `size=128,offset=0 -> 9`, `size=128,offset=10 -> 73`, `size=128,offset=74 -> 90`, `size=80,offset=64 -> 73`, `size=88,offset=74 -> 88`, `size=128,offset=91 -> 128`; bitmap and canary stayed unchanged | `kfree-owned-find-next-bit-bitmap-ok` | `a90-repl-live-call-proof-find_next_bit-pass` |
| `find_next_zero_bit` | `0xffffff8008564e94`, `export-recovery`, direct BL xrefs `120`, leaf/no-BL | owned unsigned-long bitmap buffer plus scalar bit size and scalar offset inside that bitmap | case table: `size=128,offset=0 -> 9`, `size=128,offset=10 -> 73`, `size=128,offset=74 -> 128`, `size=80,offset=64 -> 73`, `size=80,offset=74 -> 80`; bitmap and canary stayed unchanged | `kfree-owned-find-next-zero-bit-bitmap-ok` | `a90-repl-live-call-proof-find_next_zero_bit-pass` |
| `find_last_bit` | `0xffffff8008564f0c`, `export-recovery`, direct BL xrefs `9`, leaf/no-BL | owned unsigned-long bitmap buffer plus scalar bit size bounded inside that bitmap | case table: `size=128 -> 90`, `size=88 -> 73`, `size=64 -> 9`, `size=10 -> 9`, `size=9 -> 9`, `size=0 -> 0`; bitmap and canary stayed unchanged | `kfree-owned-find-last-bit-bitmap-ok` | `a90-repl-live-call-proof-find_last_bit-pass` |
| `cpumask_next` | `0xffffff80099a9e14`, `export-recovery`, direct BL xrefs `1563`, wrapper calls `find_next_bit` | scalar int `n` plus owned cpumask buffer with compiled `nr_cpumask_bits=8` | case table: `n=-1 -> 2`, `n=1 -> 2`, `n=2 -> 6`, `n=6 -> 8`, `n=7 -> 8`; cpumask and canary stayed unchanged | `kfree-owned-cpumask-next-mask-ok` | `a90-repl-live-call-proof-cpumask_next-pass` |
| `cpumask_next_wrap` | `0xffffff80099a9f1c`, `export-recovery`, direct BL xrefs `6`, wrapper calls `find_next_bit` | scalar int `n` plus owned cpumask buffer with compiled `nr_cpumask_bits=8` plus scalar `start` and scalar wrap-state | case table: `bits={2,6},n=3,start=4,wrap=0 -> 6`, `bits={2},n=3,start=4,wrap=0 -> 2`, `bits={2,6},n=1,start=4,wrap=1 -> 2`, `bits={2,6},n=6,start=4,wrap=1 -> 2`, `bits={2,6},n=2,start=4,wrap=1 -> 8`, `bits={},n=3,start=4,wrap=0 -> 8`; cpumask and canary stayed unchanged | `kfree-owned-cpumask-next-wrap-mask-ok` | `a90-repl-live-call-proof-cpumask_next_wrap-pass` |
| `cpumask_next_and` | `0xffffff80099a9e44`, `export-recovery`, direct BL xrefs `88`, wrapper calls `find_next_bit` and tests the second cpumask word | scalar int `n` plus two owned cpumask buffers with compiled `nr_cpumask_bits=8` and runtime `nr_cpu_ids=8` | case table: `src={1,3,6},and={3,6},n=-1 -> 3`, `src={1,3,6},and={3,6},n=2 -> 3`, `src={1,3,6},and={3,6},n=3 -> 6`, `src={1,3,6},and={3,6},n=6 -> 8`, `src={1},and={3,6},n=-1 -> 8`, `src={},and={3,6},n=-1 -> 8`, `src={1,3,6},and={},n=-1 -> 8`; both cpumasks and canaries stayed unchanged | `kfree-owned-cpumask-next-and-masks-ok` | `a90-repl-live-call-proof-cpumask_next_and-pass` |
| `cpumask_any_but` | `0xffffff80099a9ebc`, `export-recovery`, direct BL xrefs `1`, wrapper calls `find_next_bit` | owned cpumask buffer with compiled `nr_cpumask_bits=8` plus scalar excluded CPU inside runtime `nr_cpu_ids=8` | case table: `bits={2,6},cpu=1 -> 2`, `bits={2,6},cpu=2 -> 6`, `bits={2,6},cpu=6 -> 2`, `bits={2},cpu=2 -> 8`, `bits={},cpu=2 -> 8`; cpumask and canary stayed unchanged | `kfree-owned-cpumask-any-but-mask-ok` | `a90-repl-live-call-proof-cpumask_any_but-pass` |
| `hex2bin` | `0xffffff800856aa3c`, `export-recovery`, direct BL xrefs `15`, leaf/no-BL | owned destination byte buffer plus owned ASCII hex source buffer plus scalar byte count | `hex2bin(dst, "A90f00dC0ffEe1", 7) == 0x0`, destination decoded to `a90f00dc0ffee1`, destination canary preserved, source stayed unchanged | `kfree-owned-hex2bin-buffers-ok` | `a90-repl-live-call-proof-hex2bin-pass` |
| `bin2hex` | `0xffffff800856aaf4`, `export-recovery`, direct BL xrefs `5`, leaf/no-BL | owned destination ASCII hex buffer plus owned source byte buffer plus scalar byte count | `bin2hex(dst, a90f00dc0ffee1, 7)` returned the owned destination pointer plus offset `14` (redacted), destination encoded to `a90f00dc0ffee1`, destination canary preserved, source stayed unchanged | `kfree-owned-bin2hex-buffers-ok` | `a90-repl-live-call-proof-bin2hex-pass` |
| `parse_option_str` | `0xffffff80099a9c44`, `disasm-signature+xref+map`, direct BL xrefs `3`, calls `__pi_strlen`/`__pi_strncmp` | owned NUL-terminated comma-separated option string plus owned NUL-terminated option string | exact token case returned `1`; prefix-only token and missing token returned `0`; list and option buffers stayed unchanged | `kfree-owned-parse-option-str-buffers-ok` | `a90-repl-live-call-proof-parse_option_str-pass` |
| `strsep` | `0xffffff80099b9b94`, `export-recovery`, direct BL xrefs `230`, leaf/no-BL | owned `char **` cursor slot pointing at owned mutable NUL-terminated string plus owned delimiter string | `strsep(&cursor, ",")` over `A90STRSEP-HEAD,Q-TAIL` returned the original string pointer at offset `0` (redacted), replaced delimiter offset `14` with NUL, advanced cursor slot to offset `15`, delimiter stayed unchanged, slot/string/delimiter canaries stayed unchanged | `kfree-owned-strsep-buffers-ok` | `a90-repl-live-call-proof-strsep-pass` |
| `simple_strtoull` | `0xffffff80099ba314`, `export-recovery`, direct BL xrefs `9`, calls `_parse_integer_fixup_radix`/`_parse_integer` | owned NUL-terminated numeric string plus owned `char **` endp slot plus scalar base | `simple_strtoull("1234abcdZ", &endp, 16) == 0x1234abcd`; `endp` pointed to the owned input pointer plus offset `8` (redacted); input and end-slot canary stayed unchanged | `kfree-owned-simple-strtoull-buffers-ok` | `a90-repl-live-call-proof-simple_strtoull-pass` |
| `kstrtoull` | `0xffffff800856b3f4`, `export-recovery`, direct BL xrefs `196`, leaf/no-BL | owned NUL-terminated unsigned long long numeric string plus scalar base plus owned `unsigned long long *` result slot | `kstrtoull("1234567890abcdef", 16, &res) == 0`; result slot stored `0x1234567890abcdef`; input stayed unchanged; 8-byte result-slot canary stayed unchanged | `kfree-owned-kstrtoull-buffers-ok` | `a90-repl-live-call-proof-kstrtoull-pass` |
| `kstrtoll` | `0xffffff800856b524`, `export-recovery`, direct BL xrefs `42`, calls `kstrtoull` | owned NUL-terminated signed long long numeric string plus scalar base plus owned `long long *` result slot | `kstrtoll("-1234567890abcdef", 16, &res) == 0`; result slot stored signed `-1311768467294899695` with raw `0xedcba9876f543211`; input stayed unchanged; 8-byte result-slot canary stayed unchanged | `kfree-owned-kstrtoll-buffers-ok` | `a90-repl-live-call-proof-kstrtoll-pass` |
| `kstrtouint` | `0xffffff800856b7a4`, `export-recovery`, direct BL xrefs `217`, calls `kstrtoull` | owned NUL-terminated numeric string plus scalar base plus owned `unsigned int *` result slot | `kstrtouint("123456789", 10, &res) == 0`; result slot stored `123456789`; input stayed unchanged; result-slot canary stayed unchanged | `kfree-owned-kstrtouint-buffers-ok` | `a90-repl-live-call-proof-kstrtouint-pass` |
| `kstrtou16` | `0xffffff800856b8a4`, `export-recovery`, direct BL xrefs `17`, calls `kstrtoull` | owned NUL-terminated unsigned 16-bit numeric string plus scalar base plus owned `u16 *` result slot | `kstrtou16("54321", 10, &res) == 0`; result slot stored unsigned `54321` with raw `0xd431`; input stayed unchanged; 2-byte result-slot canary stayed unchanged | `kfree-owned-kstrtou16-buffers-ok` | `a90-repl-live-call-proof-kstrtou16-pass` |
| `kstrtou8` | `0xffffff800856b9a4`, `export-recovery`, direct BL xrefs `59`, calls `kstrtoull` | owned NUL-terminated unsigned 8-bit numeric string plus scalar base plus owned `u8 *` result slot | `kstrtou8("213", 10, &res) == 0`; result slot stored unsigned `213` with raw `0xd5`; input stayed unchanged; 1-byte result-slot canary stayed unchanged | `kfree-owned-kstrtou8-buffers-ok` | `a90-repl-live-call-proof-kstrtou8-pass` |
| `kstrtos8` | `0xffffff800856ba24`, `export-recovery`, direct BL xrefs `12`, calls `kstrtoll` | owned NUL-terminated signed 8-bit numeric string plus scalar base plus owned `s8 *` result slot | `kstrtos8("-85", 10, &res) == 0`; result slot stored signed `-85` with raw `0xab`; input stayed unchanged; 1-byte result-slot canary stayed unchanged | `kfree-owned-kstrtos8-buffers-ok` | `a90-repl-live-call-proof-kstrtos8-pass` |
| `kstrtobool` | `0xffffff800856baa4`, `export-recovery`, direct BL xrefs `50`, leaf/no-BL bool parser | owned NUL-terminated bool string plus owned `bool *` result slot | `kstrtobool("Y", &res) == 0`; result slot stored bool `true` with raw `0x01`; input stayed unchanged; 1-byte result-slot canary stayed unchanged | `kfree-owned-kstrtobool-buffers-ok` | `a90-repl-live-call-proof-kstrtobool-pass` |
| `kstrtoint` | `0xffffff800856b824`, `export-recovery`, direct BL xrefs `167`, calls `kstrtoll` | owned NUL-terminated signed numeric string plus scalar base plus owned `int *` result slot | `kstrtoint("-12345", 10, &res) == 0`; result slot stored signed `-12345` with raw `0xffffcfc7`; input stayed unchanged; result-slot canary stayed unchanged | `kfree-owned-kstrtoint-buffers-ok` | `a90-repl-live-call-proof-kstrtoint-pass` |
| `kstrtos16` | `0xffffff800856b924`, `export-recovery`, direct BL xrefs `1`, calls `kstrtoll` | owned NUL-terminated signed 16-bit numeric string plus scalar base plus owned `s16 *` result slot | `kstrtos16("-1234", 10, &res) == 0`; result slot stored signed `-1234` with raw `0xfb2e`; input stayed unchanged; 2-byte result-slot canary stayed unchanged | `kfree-owned-kstrtos16-buffers-ok` | `a90-repl-live-call-proof-kstrtos16-pass` |
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
| `strnstr` | `0xffffff80099b9f44`, `export-recovery`, direct BL xrefs `268`, calls `__pi_strlen`/`__pi_memcmp` | owned NUL-terminated haystack and needle kernel string buffers plus scalar bounded length inside haystack | `strnstr("A90STRNSTR-HEAD-NEEDLE-TAIL", "NEEDLE", 27)` returned the owned haystack pointer at offset `16` (redacted); boundary length `21` returned `0x0`; missing needle `ABSENT` returned `0x0`; both strings stayed unchanged | `kfree-owned-strnstr-strings-ok` | `a90-repl-live-call-proof-strnstr-pass` |
| `match_string` | `0xffffff80099b9c9c`, `export-recovery`, direct BL xrefs `5`, calls `__pi_strcmp` | owned `const char *` array containing owned NUL-terminated kernel strings plus owned search string and scalar bounded count inside array | `match_string(["A90MATCH-ALPHA","A90MATCH-BRAVO","A90MATCH-CHARLIE"], 3, "A90MATCH-BRAVO") == 1`; missing search `A90MATCH-MISSING` returned `0xffffffea`; zero count returned `0xffffffea`; layout stayed unchanged | `kfree-owned-match-string-layout-ok` | `a90-repl-live-call-proof-match_string-pass` |
| `__sysfs_match_string` | `0xffffff80099b9d1c`, `export-recovery`, direct BL xrefs `11`, leaf/no-BL sysfs matcher | owned `const char *` array containing owned NUL-terminated kernel strings plus owned search string and scalar bounded count inside array | `__sysfs_match_string(["A90SYSFSMATCH-ALPHA","A90SYSFSMATCH-BRAVO","A90SYSFSMATCH-CHARLIE"], 3, "A90SYSFSMATCH-BRAVO\n") == 1`; missing search `A90SYSFSMATCH-MISSING` returned `0xffffffea`; zero count returned `0xffffffea`; layout stayed unchanged | `kfree-owned-sysfs-match-string-layout-ok` | `a90-repl-live-call-proof-__sysfs_match_string-pass` |
| `match_token` | `0xffffff800855b404`, `export-recovery`, direct BL xrefs `23`, calls `__pi_strcmp`/`strchr` plus parser helpers on `%` paths | owned mutable option string, owned `match_token` table with one exact no-`%` pattern plus NULL-pattern terminator, and owned `substring_t args[MAX_OPT_ARGS]` array | `match_token("A90MATCH-TOKEN", [{0x4a90,"A90MATCH-TOKEN"},{0,NULL}], args) == 0x4a90`; table, args, input string, pattern string, and canaries stayed unchanged | `kfree-owned-match-token-layout-ok` | `a90-repl-live-call-proof-match_token-pass` |
| `match_int` | `0xffffff800855b65c`, `export-recovery`, direct BL xrefs `54`, wrapper calls `match_number` with base `0` | owned `substring_t` pointing at owned bounded decimal text plus owned `int *` result slot | `match_int({from,to="12345"}, &res) == 0`; result slot stored signed `12345` with raw `0x00003039`; `substring_t`, input text, and result-slot canary stayed unchanged | `kfree-owned-match-int-layout-ok` | `a90-repl-live-call-proof-match_int-pass` |
| `match_octal` | `0xffffff800855b83c`, `export-recovery`, direct BL xrefs `14`, wrapper calls `match_number` with base `8` | owned `substring_t` pointing at owned bounded octal text plus owned `int *` result slot | `match_octal({from,to="755"}, &res) == 0`; result slot stored signed `493` with raw `0x000001ed`; `substring_t`, input text, and result-slot canary stayed unchanged | `kfree-owned-match-octal-layout-ok` | `a90-repl-live-call-proof-match_octal-pass` |
| `match_strdup` | `0xffffff800855b98c`, `export-recovery`, direct BL xrefs `28`, calls `__kmalloc`/`__memcpy` | owned `substring_t` pointing at owned bounded text | `match_strdup({from,to="A90MATCH-STRDUP-Q-END"})` returned a new owned kmalloc string pointer (redacted); duplicate bytes matched the substring plus generated NUL; `substring_t` and input text stayed unchanged | `kfree-owned-match-strdup-layout-and-duplicate-ok` | `a90-repl-live-call-proof-match_strdup-pass` |
| `sysfs_streq` | `0xffffff80099b9c14`, `export-recovery`, direct BL xrefs `68`, leaf/no-BL | two owned NUL-terminated kernel string buffers | `sysfs_streq("A90SYSFS-VALUE\n", "A90SYSFS-VALUE") == 1`; exact equal strings returned `1`; mismatch `A90SYSFS-OTHER` returned `0`; both strings stayed unchanged | `kfree-owned-sysfs-streq-strings-ok` | `a90-repl-live-call-proof-sysfs_streq-pass` |
| `kstrdup` | `0xffffff800822a664`, `export-recovery`, direct BL xrefs `160`, calls `__pi_strlen`/`__kmalloc_track_caller`/`__memcpy` | owned NUL-terminated kernel source string buffer plus scalar `GFP_KERNEL` | `kstrdup("A90KSTRDUP-SOURCE-Q-END", GFP_KERNEL)` returned a distinct owned kernel duplicate pointer (redacted); duplicate bytes matched the source including NUL; source string and canary stayed unchanged | `kfree-owned-kstrdup-source-and-duplicate-ok` | `a90-repl-live-call-proof-kstrdup-pass` |
| `kstrndup` | `0xffffff800822a77c`, `export-recovery`, direct BL xrefs `26`, calls `__pi_strnlen`/`__kmalloc_track_caller`/`__memcpy` | owned NUL-terminated kernel source string buffer plus scalar bounded length and scalar `GFP_KERNEL` | `kstrndup("A90KSTRNDUP-HEAD-Q-TAIL", 16, GFP_KERNEL)` returned a distinct owned kernel duplicate pointer (redacted); duplicate bytes matched `A90KSTRNDUP-HEAD\0`; source string and canary stayed unchanged | `kfree-owned-kstrndup-source-and-duplicate-ok` | `a90-repl-live-call-proof-kstrndup-pass` |
| `kmemdup` | `0xffffff800822a7fc`, `export-recovery`, direct BL xrefs `912`, calls `__kmalloc_track_caller`/`__memcpy` | owned initialized kernel source buffer plus scalar bounded length and scalar `GFP_KERNEL` | `kmemdup(A90KMEMDUP-RAW, 29, GFP_KERNEL)` returned a distinct owned kernel duplicate pointer (redacted); duplicate bytes matched the bounded source bytes including embedded NUL and non-ASCII byte; source and canary stayed unchanged | `kfree-owned-kmemdup-source-and-duplicate-ok` | `a90-repl-live-call-proof-kmemdup-pass` |
| `kmemdup_nul` | `0xffffff800822a85c`, `export-recovery`, direct BL xrefs `1`, calls `__kmalloc_track_caller`/`__memcpy`, stores generated NUL at duplicate offset `len` | owned initialized kernel source buffer plus scalar bounded length and scalar `GFP_KERNEL` | `kmemdup_nul(A90KMEMDUPNUL-RAW-Q0123456789, 29, GFP_KERNEL)` returned a distinct owned kernel duplicate pointer (redacted); duplicate bytes matched the bounded source bytes plus generated trailing NUL; source byte after `len` was not copied; source and canary stayed unchanged | `kfree-owned-kmemdup-nul-source-and-duplicate-ok` | `a90-repl-live-call-proof-kmemdup_nul-pass` |
| `strpbrk` | `0xffffff80099b9b34`, `export-recovery`, direct BL xrefs `40`, leaf/no-BL | owned NUL-terminated haystack and accept-set kernel string buffers | `strpbrk("A90STRPBRK-HEAD-Q-TAIL-Z", "QZ")` returned the owned haystack pointer at offset `16` (redacted); missing accept set `xy` returned `0x0`; both strings stayed unchanged | `kfree-owned-strpbrk-strings-ok` | `a90-repl-live-call-proof-strpbrk-pass` |
| `strspn` | `0xffffff80099b9a6c`, `export-recovery`, direct BL xrefs `2`, leaf/no-BL | owned NUL-terminated haystack and accept-set kernel string buffers | `strspn("A90STRSPN-HEAD-Q-TAIL", "A90STRSPNHED-") == 15`; full accept set `A90STRSPNHEDQIL-` returned haystack length `21`; both strings stayed unchanged | `kfree-owned-strspn-strings-ok` | `a90-repl-live-call-proof-strspn-pass` |
| `strcspn` | `0xffffff80099b9ac4`, `export-recovery`, direct BL xrefs `8`, leaf/no-BL | owned NUL-terminated haystack and reject-set kernel string buffers | `strcspn("A90STRCSPN-HEAD-Q-TAIL", "QZ") == 16`; missing reject set `xy` returned haystack length `22`; both strings stayed unchanged | `kfree-owned-strcspn-strings-ok` | `a90-repl-live-call-proof-strcspn-pass` |
| `strcmp` | `0xffffff80099a8b6c`, `leaf-map-disasm+xref`, direct BL xrefs `3507`, leaf/no-BL | two owned NUL-terminated kernel string buffers | equal string compare returned `0x0`; first-difference case returned positive (`0xd0`); both strings stayed unchanged | `kfree-owned-strcmp-strings-ok` | `a90-repl-live-call-proof-strcmp-pass` |
| `strcasecmp` | `0xffffff80099b9684`, `export-recovery`, direct BL xrefs `112`, leaf/no-BL | two owned NUL-terminated kernel string buffers | `strcasecmp("A90STRCASECMP-PROOF-ZZ", "a90strcasecmp-proof-zz") == 0x0`; first casefolded mismatch returned positive (`0x3a`); both strings stayed unchanged | `kfree-owned-strcasecmp-strings-ok` | `a90-repl-live-call-proof-strcasecmp-pass` |
| `strncasecmp` | `0xffffff80099b960c`, `export-recovery`, direct BL xrefs `88`, leaf/no-BL | two owned NUL-terminated kernel string buffers plus bounded count inside both buffers | `strncasecmp("A90STRNCASECMP-PREFIX...", "a90strncasecmp-prefix...", 21) == 0x0` while post-count bytes differed; first casefolded mismatch inside count returned positive (`0x30`); both strings stayed unchanged | `kfree-owned-strncasecmp-strings-ok` | `a90-repl-live-call-proof-strncasecmp-pass` |
| `strncmp` | `0xffffff80099a8d44`, `leaf-map-disasm+xref`, direct BL xrefs `590`, leaf/no-BL | two owned NUL-terminated kernel string buffers plus bounded count inside both buffers | `strncmp("A90STRNCMP-PREFIXZ-LEFT", "A90STRNCMP-PREFIX@-RIGHT", 17) == 0x0` despite post-count byte difference; count-internal mismatch at offset `3` returned positive (`0x98`); both strings stayed unchanged | `kfree-owned-strncmp-strings-ok` | `a90-repl-live-call-proof-strncmp-pass` |
| `strnlen` | `0xffffff80099a8f4c`, `leaf-map-disasm+xref`, direct BL xrefs `473`, leaf/no-BL | owned NUL-terminated kernel string buffer plus scalar `maxlen` | `strnlen("A90STRNLEN", 64) == 0xa` | `kfree-owned-string-buffer-ok` | `a90-repl-live-call-proof-strnlen-pass` |
| `strrchr` | `0xffffff80099a900c`, `leaf-map-disasm+xref`, direct BL xrefs `1405`, leaf/no-BL | owned NUL-terminated kernel string buffer plus scalar search byte | `strrchr("A90STRRCHR-A-B-A-Z", 'A')` returned the owned pointer at offset `15` (redacted); missing `@` returned `0x0`; string stayed unchanged | `kfree-owned-strrchr-string-buffer-ok` | `a90-repl-live-call-proof-strrchr-pass` |
| `strscpy` | `0xffffff80099b9794`, `export-recovery`, direct BL xrefs `8`, leaf/no-BL | owned destination buffer plus owned NUL-terminated source string buffer plus bounded size | `strscpy(dst, "A90STRSCPY", 32) == 0xa`, destination prefix matched source, canary after size preserved | `kfree-owned-strscpy-buffers-ok` | `a90-repl-live-call-proof-strscpy-pass` |
| `strlcpy` | `0xffffff80099b9724`, `export-recovery`, direct BL xrefs `963`, calls `__pi_strlen`/`__memcpy` | owned destination buffer plus owned NUL-terminated source string buffer plus bounded size | `strlcpy(dst, "A90STRLCPY", 32) == 0xa`, destination prefix matched source, canary after size preserved | `kfree-owned-strlcpy-buffers-ok` | `a90-repl-live-call-proof-strlcpy-pass` |
| `strcpy` | `0xffffff80099b96d4`, `export-recovery`, direct BL xrefs `589`, leaf/no-BL | owned destination buffer large enough for owned NUL-terminated source string buffer | `strcpy(dst, "A90STRCPY-SRC-Q-END")` returned the owned destination pointer (redacted), destination matched source including NUL, post-NUL tail and canary stayed unchanged, source stayed unchanged | `kfree-owned-strcpy-buffers-ok` | `a90-repl-live-call-proof-strcpy-pass` |
| `strlcat` | `0xffffff80099b98f4`, `export-recovery`, direct BL xrefs `522`, calls `__pi_strlen`/`__memcpy` | owned mutable NUL-terminated destination string buffer plus owned source string plus bounded size greater than destination length and inside destination allocation | `strlcat("A90STRLCAT-DST", "-SRC-Q-END", 21) == 0x18`, destination became `A90STRLCAT-DST-SRC-Q` including NUL, post-NUL tail and canary stayed unchanged, source stayed unchanged | `kfree-owned-strlcat-buffers-ok` | `a90-repl-live-call-proof-strlcat-pass` |
| `strncat` | `0xffffff80099b98b4`, `export-recovery`, direct BL xrefs `193`, leaf/no-BL | owned mutable NUL-terminated destination string buffer plus owned source string plus bounded count | `strncat("A90STRNCAT-DST", "-SRC-Q-END", 6)` returned the owned destination pointer (redacted), destination became `A90STRNCAT-DST-SRC-Q` including NUL, post-NUL tail and canary stayed unchanged, source stayed unchanged | `kfree-owned-strncat-buffers-ok` | `a90-repl-live-call-proof-strncat-pass` |
| `strcat` | `0xffffff80099b988c`, `export-recovery`, direct BL xrefs `77`, leaf/no-BL | owned mutable NUL-terminated destination string buffer with enough tail room for owned source string | `strcat("A90STRCAT-DST", "-SRC-Q-END")` returned the owned destination pointer (redacted), destination became `A90STRCAT-DST-SRC-Q-END` including NUL, post-NUL tail and canary stayed unchanged, source stayed unchanged | `kfree-owned-strcat-buffers-ok` | `a90-repl-live-call-proof-strcat-pass` |
| `strncpy` | `0xffffff80099b96f4`, `export-recovery`, direct BL xrefs `187`, leaf/no-BL | owned destination buffer plus owned NUL-terminated source string buffer plus bounded count | `strncpy(dst, "A90STRNCPY", 32)` returned the owned destination pointer (redacted), destination prefix matched source, NUL padded to count, canary after count preserved | `kfree-owned-strncpy-buffers-ok` | `a90-repl-live-call-proof-strncpy-pass` |
| `memcmp` | `0xffffff80099a84b0`, `leaf-map-disasm+xref`, direct BL xrefs `921`, leaf/no-BL | two owned initialized buffers plus bounded size inside both buffers | equal buffer compare returned `0x0`; first-difference case returned positive (`0x80`); both buffers stayed unchanged | `kfree-owned-memcmp-buffers-ok` | `a90-repl-live-call-proof-memcmp-pass` |
| `memchr` | `0xffffff80099a8488`, `leaf-map-disasm+xref`, direct BL xrefs `25`, leaf/no-BL | owned initialized buffer plus scalar search byte plus bounded size inside the buffer | `memchr("A90MEMCHR-HIT-Q-END-012345", 'Q', 26)` returned the owned pointer at offset `14` (redacted); missing `@` returned `0x0` even though the post-size canary contained `@`; buffer stayed unchanged | `kfree-owned-memchr-buffer-ok` | `a90-repl-live-call-proof-memchr-pass` |
| `memchr_inv` | `0xffffff80099b9fc4`, `export-recovery`, direct BL xrefs `31`, leaf/no-BL | owned initialized buffer plus scalar fill byte plus bounded size inside the buffer | `memchr_inv(buf, 0x5a, 32)` returned the owned pointer at first non-fill offset `13` (redacted); all-fill bounded range returned `0x0` even though the post-size canary contained non-fill bytes; buffer stayed unchanged | `kfree-owned-memchr-inv-buffer-ok` | `a90-repl-live-call-proof-memchr_inv-pass` |
| `memcpy` | `0xffffff80099a8680`, `leaf-map-disasm+xref`, direct BL xrefs `6227`, leaf/no-BL | distinct owned destination/source buffers plus bounded size inside both buffers | `memcpy(dst, "A90MEMCPY-SRC-0123456789ABCDEF", 30)` returned the owned destination pointer (redacted), destination first 30 bytes matched source, destination post-size canary preserved, source buffer stayed unchanged | `kfree-owned-memcpy-buffers-ok` | `a90-repl-live-call-proof-memcpy-pass` |
| `memmove` | `0xffffff80099a8800`, `leaf-map-disasm+xref`, direct BL xrefs `165`, leaf/no-BL | same owned buffer with overlapping destination/source ranges plus bounded size inside allocation | `memmove(buf+5, buf, 29)` returned the owned destination pointer (redacted), final buffer matched overlap-safe snapshot-copy semantics, post-move canary preserved | `kfree-owned-memmove-overlap-buffer-ok` | `a90-repl-live-call-proof-memmove-pass` |
| `memset` | `0xffffff80099a8980`, `leaf-map-disasm+xref`, direct BL xrefs `6517`, leaf/no-BL | owned destination buffer plus scalar fill byte plus bounded size inside destination | `memset(dst, 0x5a, 32)` returned the owned destination pointer (redacted), first 32 bytes became `0x5a`, post-size canary preserved | `kfree-owned-memset-destination-buffer-ok` | `a90-repl-live-call-proof-memset-pass` |
| `memzero_explicit` | `0xffffff80099b9dd4`, `export-recovery`, direct BL xrefs `140`, calls `__memset` | owned initialized destination buffer plus scalar bounded zero count inside destination | `memzero_explicit(dst, 24)` zeroed the first 24 bytes; return was ignored as `void`; bytes after count and post-count canary stayed unchanged | `kfree-owned-memzero-explicit-destination-buffer-ok` | `a90-repl-live-call-proof-memzero_explicit-pass` |

## Parked Candidate Families

- Allocator sweep: `ksize`, `kmemdup`, and `kmemdup_nul` have crossed the live proof gate beyond the
  allocator primitives already required for owned-buffer orchestration. `kmemdup` and `kmemdup_nul`
  are trusted only under an owned initialized source buffer plus scalar bounded length and
  `GFP_KERNEL`; `kmemdup_nul` additionally proves the generated trailing NUL case.
- Hex helper sweep: `hex_to_bin` has crossed the live proof gate only under the scalar ASCII
  character contract. `hex2bin` has crossed the live proof gate only under an owned destination byte
  buffer plus owned ASCII hex source buffer plus scalar byte count contract. `bin2hex` has crossed the
  live proof gate only under an owned destination ASCII hex buffer plus owned source byte buffer plus
  scalar byte count contract. These proofs cover one bounded decoder/encoder table input path each;
  they do not authorize arbitrary parser state, arbitrary pointers, unbounded counts, output aliases,
  or mass calling.
- Scalar bit helper sweep: `__sw_hweight64`, `__sw_hweight32`, `__sw_hweight16`, and `__sw_hweight8`
  have crossed the live proof gate only under scalar unsigned word contracts for their respective widths. The proofs cover zero,
  all-ones, alternating, single-high-bit, and mixed A90 marker words; they do not authorize arbitrary
  target calls, broader bitops state, high-bit widening outside the stated contract, or mass calling.
- Bitmap helper sweep: `__bitmap_weight`, `__bitmap_complement`, `__bitmap_or`, `__bitmap_set`, `__bitmap_clear`, `__bitmap_andnot`, `__bitmap_subset`, `find_next_bit`, `find_next_zero_bit`, and
  `find_last_bit` have crossed the live proof gate only under owned unsigned-long bitmap buffers plus
  scalar count/size/offset/start/len bounded inside those bitmaps. `__bitmap_weight` covers zero count, low-tail
  popcount, first-word boundary, second-word tail, third-set-bit inclusion, last-bit exclusion
  boundary, and full-size popcount cases. `__bitmap_complement` covers zero-size no-op, low-tail
  destination mutation, first-word boundary, second-word tail, and full-size destination complement
  cases while preserving the source bitmap and canaries. `__bitmap_or` covers zero-size no-op,
  low-tail/first-word/two-word/full-size destination OR mutation under word coverage semantics while
  preserving both source bitmaps and canaries. `__bitmap_set` covers zero-length no-op, low single-bit,
  low-range, cross-word, second-word-range, and full-size range-set cases while preserving the canary.
  `__bitmap_clear` covers the same zero-length, low single-bit, low-range, cross-word,
  second-word-range, and full-size range-clear cases from an all-ones bitmap while preserving the
  canary.
  `__bitmap_andnot` covers zero-size false,
  low-tail/first-word/second-word/bit90/full-size partial-mask positives, and full-size full-mask
  negative cases while preserving the source and mask bitmaps and canaries. `__bitmap_subset` covers
  zero-size true, empty-source true, low-tail/first-word/second-word positive subset cases, a missing
  bit-90 negative case, full-size partial-mask negative, and full-size full-mask positive. `find_next_bit` covers low-word set hit,
  high-word set hit, full-size third set hit,
  bounded-tail miss before bit 90, and post-third miss cases. `find_next_zero_bit` covers low-word
  zero hit, high-word zero hit, full-size miss, and bounded-tail miss cases. `find_last_bit` covers
  full-size third set hit, bounded size before the third set bit, first-word hit, boundary inclusion,
  no-set-before-bound, and zero-size miss cases. All bitmap helper proofs validated bitmap and canary
  immutability and do not authorize arbitrary bitmap pointers, unbounded sizes, or mass calling.
- Cpumask scanner sweep: `cpumask_next`, `cpumask_next_wrap`, `cpumask_next_and`, and
  `cpumask_any_but` have crossed the live proof gate only under owned cpumask buffers, compiled
  `nr_cpumask_bits=8`, and scalar CPU/index contracts. `cpumask_next` covers first-hit,
  skip-first-hit, and no-CPU sentinel returns. `cpumask_next_wrap` additionally covers forward hit,
  initial low wrap hit, wrapped low-next, tail-to-low wrap hit, start-boundary sentinel, and
  empty-mask sentinel cases under scalar `start` plus wrap-state. `cpumask_next_and` additionally
  requires two owned cpumasks plus runtime `nr_cpu_ids=8`, proves that src-only bits are skipped,
  proves common-bit hits after `n`, and covers no-common, empty-src, and empty-and sentinels.
  `cpumask_any_but` additionally gates runtime `nr_cpu_ids=8` and covers first-set-not-excluded,
  excluded-first-set, excluded-later-set, only-excluded-set, and empty-mask sentinel cases. All four
  proofs validate cpumask/canary immutability. They do not authorize arbitrary cpumask pointers,
  wider CPU masks, other cpumask wrappers, arbitrary iteration states, or mass calling.
- Option parser sweep: `parse_option_str` has crossed the live proof gate only under owned
  NUL-terminated comma-separated option and option strings. Its C1 identity is the
  `disasm-signature+xref+map` path, not export recovery; the target's early x0 byte read is allowed
  only because x0 is an owned string buffer. This proof covers one exact-token hit, one prefix-only
  miss, and one missing-token miss; it does not authorize arbitrary parser state, user pointers,
  unterminated strings, unbounded scans, or mass calling.
- Parser token sweep: `match_token` has crossed the live proof gate only under an owned mutable
  option string, an owned `match_token` table with a single exact no-`%` pattern and NULL-pattern
  terminator, plus an owned `substring_t args[MAX_OPT_ARGS]` array. The proof covers one exact-token
  hit and validates token return `0x4a90`, table/input/pattern/args immutability, and layout cleanup.
  It does not authorize `%d/%s/%u/%o/%x` substring extraction paths, arbitrary tables, user pointers,
  unterminated patterns, invalid terminators, output aliases, or mass calling.
- Parser substring duplicate sweep: `match_strdup` has crossed the live proof gate only under an
  owned `substring_t {from,to}` range pointing at owned bounded text. Its returned pointer is trusted
  only as a newly owned kmalloc string that must be freed by the caller; the proof validates duplicate
  bytes, generated trailing NUL, source layout immutability, and cleanup of both the returned duplicate
  and the proof layout. It does not authorize arbitrary substring pointers, invalid ranges, NULL
  returns, stale buffers, ownership transfer beyond immediate cleanup, or mass calling.
- Integer parser sweep: `simple_strtoull`, `kstrtoull`, `kstrtoll`, `kstrtouint`, `kstrtou16`, `kstrtou8`,
  `kstrtos8`, `kstrtoint`, `kstrtos16`, `match_int`, and `match_octal`
  have crossed the live proof gate only under owned NUL-terminated numeric strings plus their
  specific owned output-slot contracts, or for `match_int`/`match_octal`, an owned `substring_t`
  range plus an owned `int *` result slot.
  `simple_strtoull` additionally requires an owned `char **` endp output slot and scalar base; its
  proof covers one bounded hexadecimal parse with a non-numeric terminator and validates returned
  value, end-pointer offset, input immutability, and end-slot canary. `kstrtoull` additionally
  requires an owned `unsigned long long *` result slot and scalar base; its proof covers one bounded
  hexadecimal success case and validates return code `0`, 64-bit result-slot value, input
  immutability, and 8-byte result-slot canary. `kstrtoll` additionally requires an owned
  `long long *` result slot and scalar base; its proof covers one bounded negative hexadecimal
  success case and validates return code `0`, signed result-slot value, raw two's-complement
  representation, input immutability, and 8-byte result-slot canary. `kstrtouint` additionally
  requires an owned `unsigned int *` result slot and scalar base; its proof covers one bounded decimal
  success case and validates return code `0`, result-slot value, input immutability, and result-slot
  canary. `kstrtou16` additionally requires an owned `u16 *` result slot and scalar base; its proof
  covers one bounded unsigned 16-bit decimal success case and validates return code `0`, unsigned
  result-slot value, raw representation, input immutability, and 2-byte result-slot canary.
  `kstrtou8` additionally requires an owned `u8 *` result slot and scalar base; its proof covers one
  bounded unsigned 8-bit decimal success case and validates return code `0`, unsigned result-slot
  value, raw representation, input immutability, and 1-byte result-slot canary.
  `kstrtos8` additionally requires an owned `s8 *` result slot and scalar base; its proof covers one
  bounded signed 8-bit decimal success case and validates return code `0`, signed result-slot value,
  raw two's-complement representation, input immutability, and 1-byte result-slot canary.
  `kstrtoint` additionally requires an owned `int *` result slot and scalar base; its proof covers one
  bounded signed decimal success case and validates return code `0`, signed result-slot value, raw
  two's-complement representation, input immutability, and result-slot canary. `kstrtos16`
  additionally requires an owned `s16 *` result slot and scalar base; its proof covers one bounded
  signed 16-bit decimal success case and validates return code `0`, signed result-slot value, raw
  two's-complement representation, input immutability, and 2-byte result-slot canary. `match_int`
  additionally requires an owned `substring_t {from,to}` slot whose range points at owned bounded
  decimal text plus an owned `int *` result slot; its proof covers one bounded decimal success case
  and validates return code `0`, signed result-slot value `12345`, raw representation `0x00003039`,
  substring immutability, input immutability, and result-slot canary. `match_octal` additionally
  requires an owned `substring_t {from,to}` slot whose range points at owned bounded octal text plus
  an owned `int *` result slot; its proof covers one bounded octal success case and validates return
  code `0`, signed result-slot value `493`, raw representation `0x000001ed`, substring immutability,
  input immutability, and result-slot canary. These rows do
  not authorize arbitrary parser state, user pointers, unterminated strings, invalid bases, overflows,
  NULL output slots, failure paths, or mass calling.
- Bool parser sweep: `kstrtobool` has crossed the live proof gate only under an owned
  NUL-terminated bool string plus owned `bool *` result slot contract. The proof covers one true
  success case, `kstrtobool("Y", &res) == 0`, and validates raw result `0x01`, input immutability,
  1-byte result-slot canary, and cleanup. This row does not authorize arbitrary strings, false cases,
  invalid cases, user pointers, NULL output slots, failure paths, or mass calling.
- Read-I/O sweep: `filp_open`, cleanup-only `filp_close`, and `kernel_read` have crossed the live
  proof gate only under their paired owned `/init` file/buffer/position contracts. Broader read paths,
  arbitrary file pointers, and arbitrary destination buffers remain parked until separate contracts are
  proven.
- Sysfs array matcher sweep: `__sysfs_match_string` has crossed the live proof gate only under an
  owned `const char *` array plus owned NUL-terminated string entries, an owned search string, and
  bounded `n` inside the array. The proof covers a newline-tolerant hit, missing search, zero-count
  `-EINVAL`, layout immutability, and cleanup. It does not authorize arbitrary arrays, user pointers,
  unterminated strings, unbounded counts, output aliases, or mass calling.
- String sweep: `strlen`, `strnchr`, `skip_spaces`, `strim`, `strreplace`, `strchr`, `strchrnul`, `strstr`, `strnstr`, `match_string`, `__sysfs_match_string`, `sysfs_streq`, `kstrdup`, `kstrndup`, `strsep`, `strpbrk`, `strcmp`, `strcasecmp`, `strncasecmp`, `strncmp`, `strnlen`, `strrchr`,
  `strscpy`, `strlcpy`, `strcpy`, `strlcat`, `strncat`, `strcat`, and
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
  one missing-needle NULL case; `strnstr` additionally requires owned haystack and needle strings
  plus a scalar bounded length inside the haystack and only proves one present substring inside the
  length, one boundary-length NULL case, and one missing-needle NULL case; `match_string` additionally
  requires an owned string-pointer array, owned NUL-terminated string entries, an owned search string,
  and a scalar count inside the array, and only proves one hit-index case plus missing/zero-count
  `-EINVAL` cases; `__sysfs_match_string` additionally requires an owned string-pointer array, owned
  NUL-terminated string entries, an owned search string, and a scalar count inside the array, and only
  proves one newline-tolerant hit-index case plus missing/zero-count `-EINVAL` cases; `sysfs_streq`
  additionally requires two owned terminated strings and only proves
  exact equality, one left-trailing-newline sysfs equality case, and one mismatch false case; `kstrdup`
  additionally allocates a new owned duplicate string and only proves one owned source string plus
  `GFP_KERNEL` case; `kstrndup` additionally allocates a new owned duplicate string and only proves
  one owned source string, one truncating bounded length, and `GFP_KERNEL` case; `strsep` additionally
  requires an owned `char **` cursor slot pointing at an owned mutable string plus an owned delimiter
  string, and only proves one delimiter-hit mutation case with return offset `0`, delimiter offset
  `14` replaced with NUL, cursor update to offset `15`, delimiter immutability, and canary
  preservation; `strpbrk` additionally requires owned haystack and accept-set strings
  and only proves one present accept-set hit plus one missing accept-set NULL case; `strcmp`
  additionally requires two owned terminated strings and only proves equal/positive-sign compare
  cases; `strcasecmp` additionally requires two owned terminated strings and only proves case-fold
  equal plus positive-sign mismatch cases; `strncasecmp` additionally requires two owned terminated
  strings plus a scalar bounded count inside both buffers and only proves bounded case-fold equal plus
  positive-sign mismatch cases; `strncmp` additionally requires two owned terminated strings plus a scalar bounded count
  inside both buffers and only proves bounded-equal plus positive-sign mismatch cases; `strnlen`
  additionally requires the scalar `maxlen` contract; `strrchr` additionally
  requires a scalar search byte and a terminated owned string; `strscpy`, `strlcpy`, `strcpy`,
  `strcat`, and `strncpy` additionally require an owned destination buffer and enough capacity inside
  that destination; `strncat` additionally requires a mutable owned destination string, owned source
  string, enough destination tail room, and a scalar bounded count; `strlcat` additionally requires a
  mutable owned destination string, owned source string, scalar size greater than destination length,
  and size inside the destination allocation.
  Other string/memory helpers remain parked until separate C1 identity and pointer contracts are
  proven.
- Memory-search/compare sweep: `memcmp` has crossed the live proof gate only under the two-owned-buffer
  plus bounded-size contract. `memchr` has crossed the live proof gate only under the owned-buffer plus
  scalar-search-byte and bounded-size contract, including a canary check that the search stays inside
  the size argument. `memchr_inv` has crossed the live proof gate only under the owned initialized
  buffer plus scalar-fill-byte and bounded-size contract, including a canary check that non-fill bytes
  outside the size argument are ignored. These rows do not authorize arbitrary pointers, unbounded sizes,
  user pointers, or other memory helpers.
- Memory-write sweep: `memset` has crossed the live proof gate only under the owned destination plus
  scalar-fill-byte and bounded-size contract. `memzero_explicit` has crossed the live proof gate only
  under the owned initialized destination plus scalar bounded zero-count contract; its `void` return is
  intentionally ignored and the proof rests on zeroed prefix, preserved tail, and preserved canary.
  `memcpy` has crossed the live proof gate only under the distinct-owned-destination/source-buffer
  plus bounded-size contract with non-overlapping allocation ranges. `memmove` has crossed the live
  proof gate only under the same-owned-buffer `dst=src+5`, bounded-size overlap contract. These rows do
  not authorize arbitrary pointers, unbounded sizes, user pointers, broader overlap shapes, or
  zeroing of unowned memory without separate proof.

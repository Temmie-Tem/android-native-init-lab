# Kernel Security Tier-2 Runtime Kernel REPL v2c C2D - Ksymtab ABI Audit

- Date: 2026-06-29
- Unit: `v2c C2D`
- Decision: `a90-repl-v2c-c2d-ksymtab-abi-audit-fenced`
- Device action: no
- Boot image changed: no
- Public code: `workspace/public/src/scripts/revalidation/a90_repl.py`
- Tests: `tests/test_a90_repl.py`, `tests/test_a90_stock_kallsyms_extract.py`

## Objective

Close the remaining C2 oracle gap without promoting the noisy C2A string-reference
scanner into a broad map truth source. The operator-requested direction was to use
a grounded `__ksymtab` source, then either repair the map decoder or explicitly
fence the unsupported broad-drift claim.

## Source ABI Check

The local Samsung kernel source for this image does not define the PREL32
`struct kernel_symbol { s32 value_offset; s32 name_offset; }` ABI. Its
`include/linux/export.h` defines:

```c
struct kernel_symbol
{
	unsigned long value;
	const char *name;
};
```

So the source-grounded audit for this tree is a 16-byte absolute
`{ value, name }` pair search, not a PREL32 decode.

## Implementation

`a90_repl.py ksymtab-audit` now separates two cases:

- A source-ABI `struct kernel_symbol` row: any aligned qword reference to an exact
  exported symbol string whose previous qword is an in-image kernel text/data
  address.
- The noisy C2A-style table: a large 24-byte record stream shaped like
  `0x403, pointer, aux`, where string-reference candidates can appear but are not
  source-ABI ksymtab rows.

The audit focuses on the anchors that previously defined the C2 correction:
`printk`, `__kmalloc`, and `kfree`.

## Host Evidence

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/a90_repl.py ksymtab-audit \
    --map workspace/private/runs/kernel/v2a1-repl-driver/System.map \
    --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img
```

Observed summary:

- `decision`: `a90-repl-v2c-c2d-ksymtab-abi-audit-fenced`
- `ok`: `true`
- `source_abi_record_size`: `16`
- `noisy_403_table_total_run_count`: `1`
- top noisy run: raw offset `0x2699620`, record size `24`,
  flags qword `0x403`, record count `162763`

Focus rows:

- `printk`: `absolute_kernel_symbol_pair_candidate_count=0`;
  `noisy_403_candidate_count=2`. The noisy candidates include the known false
  string-ref candidates and remain classified as
  `noisy-24-byte-0x403-record-table-not-kernel_symbol-pair`.
- `__kmalloc`: `absolute_kernel_symbol_pair_candidate_count=0`;
  `noisy_403_candidate_count=1`; candidate `0xffffff800826ae34` is the already
  independently verified allocator truth from v2a2R'/C2C, but this audit still
  treats the table itself as noisy rather than broad truth.
- `kfree`: `absolute_kernel_symbol_pair_candidate_count=0`;
  `noisy_403_candidate_count=2`; candidate `0xffffff800826b354` is the already
  independently verified free truth from v2a2R'/C2C, but the table also has a
  non-function false candidate, proving it cannot be promoted wholesale.

Validation:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
  python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_repl.py \
  tests/test_a90_repl.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
PYTHONPATH=tests:workspace/public/src/scripts/revalidation \
  python3 -m unittest tests.test_a90_repl tests.test_a90_stock_kallsyms_extract
```

Results:

- `py_compile`: pass
- `tests.test_a90_repl` + `tests.test_a90_stock_kallsyms_extract`: `62/62` pass

## Conclusion

C2D does not produce a broad drift map and does not justify rewriting
`a90_stock_kallsyms_extract.py`. It proves that the C2A string-reference table is
not a source-ABI `struct kernel_symbol` source for this image, and therefore must
stay fenced as noisy evidence.

For v2c safety and usability, the correct policy remains:

- `call` and `poke` use C1 fail-closed verified resolution only.
- `map-audit` trusts the C2C high-confidence anchor rows only.
- Any new symbol requires independent semantic/disasm proof or a future grounded
  oracle before being used as a live call/poke target.

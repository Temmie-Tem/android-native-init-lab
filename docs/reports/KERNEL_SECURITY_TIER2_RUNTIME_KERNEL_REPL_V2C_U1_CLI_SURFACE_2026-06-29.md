# Kernel Security Tier-2 Runtime Kernel REPL v2c U1 - CLI Surface

- Date: 2026-06-29
- Unit: `v2c U1`
- Decision: `a90-repl-v2c-u1-cli-surface-host-pass`
- Device action: no
- Boot image changed: no
- Public code: `workspace/public/src/scripts/revalidation/a90_repl.py`
- Tests: `tests/test_a90_repl.py`, `tests/test_a90_stock_kallsyms_extract.py`

## Objective

Add first-class operator CLI commands on top of the already-live-proven v1-repl
ops, without building a new image:

- `read SYMBOL|ADDR --len N`: arbitrary-length read by looping op1 `peek` in
  bounded chunks.
- `call SYMBOL [args...]`: named call through C1 verified resolution only.
- `poke VALUE`: owned-buffer-only poke proof; never poke an arbitrary address.

Public output must keep raw runtime pointers, slide, raw call returns, and raw
read bytes out of stdout. Private evidence may contain those values when
`--evidence-dir` is supplied.

## Implementation

Added U1 helpers and CLI commands in `a90_repl.py`:

- `read_runtime_bytes(...)` loops `peek_runtime(...)` in 1..8 byte chunks and
  reconstructs bytes in little-endian order.
- `run_read(...)` accepts a symbol, link vaddr, or `--runtime-addr`, applies the
  KASLR slide when needed, reports byte count/chunk count/SHA256/static-image
  match, and writes raw bytes only to private evidence.
- `run_call(...)` requires `resolve_verified(..., purpose="call")` and refuses
  unverified symbols before any transport op. Argument and return values are
  private evidence only.
- `run_owned_poke(...)` allocates via verified `__kmalloc`, pokes the fresh owned
  buffer, verifies by `peek`, then calls verified `kfree` in cleanup. There is no
  arbitrary-address `poke` CLI.

CLI smoke checks passed for:

```sh
python3 workspace/public/src/scripts/revalidation/a90_repl.py read --help
python3 workspace/public/src/scripts/revalidation/a90_repl.py call --help
python3 workspace/public/src/scripts/revalidation/a90_repl.py poke --help
```

## Host Evidence

Validation commands:

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
- `tests.test_a90_repl` + `tests.test_a90_stock_kallsyms_extract`: `61/61` pass

Focused fake-transport coverage:

- `read` of `kgsl_pwrctrl_force_no_nap_store` length `20` used `1` slide op +
  `3` peek ops, matched static image bytes, and redacted raw data from the
  public summary.
- `call printk(...)` used verified C1 resolution and redacted args/returns from
  the public summary.
- `call kallsyms_lookup_name` was refused before transport.
- `poke VALUE` used a kmalloc-owned buffer, verified by peek, freed it, and
  redacted pointer/value details from the public summary.

## Conclusion

U1 is host-complete: the operator now has first-class `read`, `call`, and
owned-buffer-only `poke` commands on the existing v1-repl image. Remaining U1
work is live validation over the bridge under the v2c flash/rollback gates.

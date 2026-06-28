# Kernel Security Tier-2 Runtime Kernel REPL v2c S1A - Safe-Op Retry

- Date: 2026-06-29
- Unit: `v2c S1A`
- Decision: `a90-repl-v2c-s1a-safe-op-retry-host-pass`
- Device action: no
- Boot image changed: no
- Public code: `workspace/public/src/scripts/revalidation/a90_repl.py`
- Tests: `tests/test_a90_repl.py`

## Objective

Harden the live REPL op path against transient serial/ring capture noise such as
`ATAT` fragments or missing `A90P1 END` without blindly replaying dangerous operations.

## Implementation

Added conservative retry/classification support to `ReplSession`:

- New `ReplTransientNoiseError` class for "no `A90R` captured" failures.
- New config knobs:
  - `safe_op_retries`
  - `retry_delay_sec`
- `_op_values()` now retries only replay-safe ops by default.
- Replay-safe ops are currently:
  - `OP_SLIDE`
  - `OP_PEEK`
- `OP_CALL` is not replayed by default because duplicating calls such as `__kmalloc`
  or `kfree` can leak or corrupt state.
- `run_selftest` marks its `printk` call as explicitly replay-safe because duplicate
  `printk(format, sentinel)` is acceptable for the proof.
- `_op_values()` now uses the configured `dmesg_tail` instead of the helper default.
- CLI common options expose `--safe-op-retries` and `--retry-delay-sec`.

This is a host-side stability unit. It does not claim to make every possible live op
retryable; it prevents unsafe duplicate side effects while self-healing the idempotent
read path.

## Host Evidence

Focused tests now cover:

- `slide()` retries after an `ATAT`/no-`A90R` response and succeeds on the next
  response.
- `call_runtime()` does not replay by default after a no-`A90R` response.
- `call_runtime_values(..., replay_safe=True)` can replay an explicitly safe call.
- Existing C1/C2 behavior remains intact.

Validation commands:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
  python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_repl.py \
  tests/test_a90_repl.py \
  workspace/public/src/scripts/revalidation/a90_stock_kallsyms_extract.py \
  tests/test_a90_stock_kallsyms_extract.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
PYTHONPATH=tests:workspace/public/src/scripts/revalidation \
  python3 -m unittest tests.test_a90_repl tests.test_a90_stock_kallsyms_extract
```

Results:

- `py_compile`: pass
- `tests.test_a90_repl` + `tests.test_a90_stock_kallsyms_extract`: `56/56` pass in
  `30.520s`

## Conclusion

S1A is host-complete. The REPL driver now distinguishes transient capture noise from
ordinary logical failure and can self-heal `slide`/`peek` and explicitly safe calls.
The remaining S1 work is live validation against real serial fragments and, if needed,
additional non-replay re-read/realign handling for unsafe operations.

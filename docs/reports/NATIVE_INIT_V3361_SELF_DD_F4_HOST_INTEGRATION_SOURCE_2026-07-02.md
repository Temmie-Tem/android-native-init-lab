# Native Init V3361 Self-dd F4 Host Integration Source

- Cycle: `V3361`
- Decision: `v3361-self-dd-f4-host-integration-source-pass-live-policy-blocked`
- Scope: host-only `native_init_flash.py` F4 scaffold.
- Device action: none.
- Flash action: none.
- Final device state: unchanged from the prior clean v2321 rollback state.

## Change

- Added explicit opt-in flags to `native_init_flash.py`:
  - `--experimental-self-write`
  - `--self-write-plan-only`
  - `--self-write-staging-dir`
- The default checked-helper/TWRP flash path is unchanged.
- Plan-only mode performs local image inspection, then emits a JSON plan for the post-F3 self-write
  path:
  - preflight commands: `version`, `status`, `selftest`, `pstore summary`
  - tcpctl staging into an approved flash-staging root
  - `boot-flash-plan`
  - `boot-flash-f2 BOOT-FLASH-F2-BOOT-CANDIDATE`
  - host-controlled `reboot`
  - required canonical timeline events
  - checked-helper/TWRP rollback fallback
- The live self-write path remains blocked. `--experimental-self-write` without
  `--self-write-plan-only` raises:
  `F4/production fast-flash is not authorized by AGENTS.md or design section 12.1`.

## Safety Gate

- Requires `--expect-sha256`, `--expect-version`, and `--expect-android-magic`.
- Rejects `--allow-unpinned-image`.
- Restricts staging to:
  - `/mnt/sdext/a90/flash-staging`
  - `/cache/a90-runtime/flash-staging`
- Rejects unsafe remote image basenames.
- Performs no recovery transition, staging transfer, boot write, reboot, or rollback in plan-only
  mode.
- Performs no live self-write at all until a future explicit F4 policy amendment.

## Host Plan-Only Probe

Command shape:

```text
native_init_flash.py --expect-android-magic --expect-version 0.11.123 \
  --expect-sha256 2989c292d1a7ae7cd5f9eb78906b2451d717e4221b9c9b76114ddc9054b52a29 \
  --experimental-self-write --self-write-plan-only \
  workspace/private/inputs/boot_images/boot_linux_v3360_self_dd_f3_self_rollback.img
```

Observed:

```text
local image starts with Android boot magic
local image contains expected marker: 0.11.123
local image size: 62644224
local image sha256: 2989c292d1a7ae7cd5f9eb78906b2451d717e4221b9c9b76114ddc9054b52a29
policy_state: plan-only-live-blocked
source_plan_command: boot-flash-plan ... 0.11.123
self_write_command: boot-flash-f2 BOOT-FLASH-F2-BOOT-CANDIDATE ... 0.11.123
```

The private JSON output was written under `workspace/private/runs/` and is not committed.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_init_flash.py tests/test_native_init_flash.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover -s tests -p 'test_native_init_flash.py'
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover -s tests -p 'test_native_self_dd*.py'
git diff --check
```

Results:

```text
test_native_init_flash.py: Ran 18 tests, OK
test_native_self_dd*.py: Ran 14 tests, OK
git diff --check: OK
```

## Conclusion

V3361 prepares the F4 host integration surface while preserving the safety boundary: plan-only is
usable for review and command-shape validation, but live self-write remains fail-closed. F4 live use
and production fast-flash integration remain blocked until a future explicit policy amendment.

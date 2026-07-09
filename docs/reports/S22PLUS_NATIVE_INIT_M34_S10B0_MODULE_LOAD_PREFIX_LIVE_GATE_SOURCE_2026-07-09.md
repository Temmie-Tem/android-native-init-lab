# S22+ M34 S10B0 Module-Load Prefix Live-Gate Source (2026-07-09)

## Verdict

S10B0 live-gate source is ready, but no live authorization exists. No flash,
reboot, ADB device mutation, or Odin action was performed in this unit.

The helper is:

```text
workspace/public/src/scripts/revalidation/s22plus_m34_s10b0_module_load_prefix_live_gate.py
```

The tests are:

```text
tests/test_s22plus_m34_s10b0_module_load_prefix_live_gate.py
```

## Candidate

S10B0 is the first S10B prefix predicate. It keeps the S9/S10A 89-module
runtime recipe and checks only whether `cmd_db` appears in `/proc/modules`
under native-init.

```text
stage: S10B0
stage_number: 13
module_load_probe: proc_modules_prefix_1
prefix_index: 0
prefix_expected: 1
prefix_modules: cmd_db
true_action: reboot(download)
false_action: park
```

Interpretation:

```text
HIT: cmd_db appears in /proc/modules under native-init; the candidate should self-enter Download.
MISS: cmd_db never appears, or /proc/modules is not trustworthy there; the candidate parks and manual Download rollback is required.
```

## Hash Pins

```text
S10B0 AP.tar.md5 SHA256: c117d8789b4ed990afd047ef3a6bb8d32f0b7b5d76bdce58eecf8ae98725d47c
S10B0 boot.img SHA256: a30120d094d3484b6b4234e0a285f6c26e95120f032ed9ec3671fd287661b610
S10B0 /init SHA256: 50bd942c92d6aad3b143e1f215c0e7a313819994f5dbfa580c11666d32d5f761
Template source SHA256: 6ac888ddf29e559a9a9b7522eda4edd54c5a38264782dddd2bd5c80d6d8e21a6
Module-list SHA256: c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26
Known Magisk base boot SHA256: 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
Preserved kernel SHA256: bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
```

Default artifact paths:

```text
workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_12/S10B0/odin4/AP.tar.md5
workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_12/manifest.json
```

## Safety Envelope

The helper verifies that the manifest still encodes the S10B isolation
constraints:

```text
boot-only candidate
AP contains exactly boot.img.lz4
no configfs gadget setup
no UDC bind
no TypeC role write
no ssusb role write
no FunctionFS
no stock-composite
no Android/Magisk handoff
no persistent partition mount
no block write
no module binary injection into boot ramdisk
driver_load_only=1
manual_power_write=0
```

Default dry-run and live mode both require an exact active `AGENTS.md`
exception template. The helper can print the draft/active template or write an
AGENTS candidate to a separate file, but it refuses to write `AGENTS.md`
directly.

## Validation

Executed:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m34_s10b0_module_load_prefix_live_gate.py
```

Result: pass.

Executed:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s10b0_module_load_prefix_live_gate.py \
  --offline-check \
  --run-dir workspace/private/runs/s22plus_m34_s10b0_offline_check_tmp
```

Result:

```text
offline-check ok: M34 S10B0 artifacts verified; no AGENTS/device action
```

Executed:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s10b0_module_load_prefix_live_gate.py \
  --print-agents-exception-active-template
```

Result: active exception template printed; it contains the S10B0 ack tokens and
hash pins and does not contain the draft-only marker.

Executed:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s10b0_module_load_prefix_live_gate.py \
  --write-agents-candidate /tmp/AGENTS.s10b0.candidate.md

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s10b0_module_load_prefix_live_gate.py \
  --verify-agents-candidate /tmp/AGENTS.s10b0.candidate.md
```

Result: candidate write+verify passed. `AGENTS.md` was not modified.

Executed:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_m34_s10b0_module_load_prefix_live_gate.py
```

Result:

```text
Ran 6 tests in 0.106s
OK
```

## Next

If proceeding live:

1. Insert the generated exact S10B0 active exception into `AGENTS.md`.
2. Run the helper default dry-run against the current rooted Android/Magisk
   baseline.
3. Require explicit operator approval.
4. Run only S10B0 live.
5. Analyze HIT/MISS before authorizing S10B1 or any downstream stage.

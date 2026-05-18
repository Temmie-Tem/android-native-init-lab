# Native Init v237 Linker Offset Symbolization

## Summary

- Goal: map the v236 Android `linker64` crash file offset `0x1002f4` to ELF
  section, nearest symbol, and bounded disassembly context.
- Result: PASS / `linker-offset-symbolized`.
- Reason: crash offset mapped to `linker64` `.text`, nearest symbol list, and
  disassembly context.
- No PID1 boot image update, Wi-Fi daemon start, scan, connect, DHCP,
  credential, routing, rfkill write, or Android partition write was used.

## Implementation

Added host tool:

- `scripts/revalidation/wifi_linker_offset_symbolize.py`

Added plan:

- `docs/plans/NATIVE_INIT_V237_LINKER_OFFSET_SYMBOLIZATION_PLAN_2026-05-18.md`

Tool modes:

- `plan`: writes plan-only private evidence without device access.
- `analyze`: parses v236 evidence, optionally pulls linker64 from device, and
  runs host `readelf`/`objdump` analysis.

Live linker64 source:

```text
/mnt/system/system/apex/com.android.runtime/bin/linker64
```

The only device mutation used by the tool was existing read-only `mountsystem ro`.
File export used `toybox base64 -w 0` from the allowlisted linker path.

## Validation

Static checks:

```bash
python3 -m py_compile scripts/revalidation/wifi_linker_offset_symbolize.py
python3 scripts/revalidation/wifi_linker_offset_symbolize.py \
  --out-dir tmp/wifi/v237-plan-smoke plan
python3 scripts/revalidation/wifi_linker_offset_symbolize.py \
  --out-dir tmp/wifi/v237-linker-offset-symbolize-no-elf \
  --no-pull analyze || true
```

No-ELF preflight confirmed v236 evidence parsing before live pull:

```json
{
  "decision": "linker-offset-symbolization-blocked-no-elf",
  "pass": false,
  "reason": "matching linker64 ELF was not provided or pulled",
  "offsets": ["0x1002f4"],
  "case_count": 6
}
```

Live analysis command:

```bash
python3 scripts/revalidation/wifi_linker_offset_symbolize.py \
  --out-dir tmp/wifi/v237-linker-offset-symbolize-live \
  --pull-from-device \
  analyze
```

Live result:

```json
{
  "decision": "linker-offset-symbolized",
  "pass": true,
  "reason": "crash offset mapped to linker64 section, nearest symbol list, and disassembly context"
}
```

A local ELF smoke test also verified the host `readelf`/`objdump` path against
`stage3/linux_init/helpers/a90_android_execns_probe`; it is not a conclusion
about Android `linker64`.

## Linker ELF

| item | value |
| --- | --- |
| host evidence path | `tmp/wifi/v237-linker-offset-symbolize-live/files/linker64` |
| size | `1816360` |
| SHA-256 | `ebd1db608558ccb01f851a4988abea2f2dd8844b7bc09e1847ebaf05e36a421d` |
| file type | `ELF 64-bit LSB shared object, ARM aarch64, dynamically linked, not stripped` |
| BuildID | `e8fdced9e7490875160097adfe101461` |

## v236 Evidence Reuse

The v237 tool parsed v236 crash captures and confirmed:

| item | value |
| --- | --- |
| crash cases parsed | `6` |
| consistent file offset | `0x1002f4` |
| fault address | `0xa1` |
| signal | `SIGSEGV(11)` |

The offset is computed from crash PC and `/proc/<pid>/maps`:

```text
file_offset = pc - mapping_start + mapping_file_offset
```

Crash cases:

| linker | target | fault | pc | file offset | perms |
| --- | --- | --- | --- | --- | --- |
| `system-linker` | `system-toybox` | `0xa1` | `0x7f821512f4` | `0x1002f4` | `r-xp` |
| `system-linker` | `apex-linker64-self` | `0xa1` | `0x7fbbe1e2f4` | `0x1002f4` | `r-xp` |
| `system-linker` | `cnss-daemon` | `0xa1` | `0x7fadfa32f4` | `0x1002f4` | `r-xp` |
| `apex-linker` | `system-toybox` | `0xa1` | `0x7fbcc142f4` | `0x1002f4` | `r-xp` |
| `apex-linker` | `apex-linker64-self` | `0xa1` | `0x7fb4f4d2f4` | `0x1002f4` | `r-xp` |
| `apex-linker` | `cnss-daemon` | `0xa1` | `0x7fafeb32f4` | `0x1002f4` | `r-xp` |

## Symbolization Result

| item | value |
| --- | --- |
| file offset | `0x1002f4` |
| mapped vaddr | `0x1002f4` |
| section | `.text` |
| section index | `11` |
| section delta | `819956` |
| nearest containing symbol | `__dl__ZL13__early_aborti` |
| symbol value | `0x1002e0` |
| symbol size | `28` |
| symbol delta | `0x14` |
| selected instruction | `1002f4: b900011f str wzr, [x8]` |

Nearest symbols:

| name | type | value | size | delta | contains |
| --- | --- | --- | --- | --- | --- |
| `__dl__ZL13__early_aborti` | `FUNC` | `0x1002e0` | `28` | `0x14` | `true` |
| `__dl_$x.9` | `NOTYPE` | `0x1002e0` | `0` | `0x14` | `false` |
| `__dl_$x.8` | `NOTYPE` | `0x100018` | `0` | `0x2dc` | `false` |
| `__dl__Z21__libc_init_AT_SECUREPPc` | `FUNC` | `0x100018` | `712` | `0x2dc` | `false` |
| `__dl_$x.1` | `NOTYPE` | `0xfff34` | `0` | `0x3c0` | `false` |

Disassembly window evidence:

```text
1002c8: 528017a0  mov w0, #0xbd
1002cc: 94000005  bl  1002e0 <__dl__ZL13__early_aborti>
1002d0: 528029e0  mov w0, #0x14f
1002d4: 94000003  bl  1002e0 <__dl__ZL13__early_aborti>
1002d8: 52801880  mov w0, #0xc4
1002dc: 94000001  bl  1002e0 <__dl__ZL13__early_aborti>

00000000001002e0 <__dl__ZL13__early_aborti>:
1002e0: d503233f  paciasp
1002e4: a9bf7bfd  stp x29, x30, [sp, #-16]!
1002e8: 910003fd  mov x29, sp
1002ec: 2a0003e8  mov w8, w0
1002f0: 52800020  mov w0, #0x1
1002f4: b900011f  str wzr, [x8]
1002f8: 9400563a  bl  115be0 <__dl__Exit>
```

## Interpretation

The crash is an intentional early-abort trap in Android linker initialization,
not an arbitrary unknown instruction stream.

The abort helper copies its integer argument into `w8`, then executes
`str wzr, [x8]`.  v236 captured fault address `0xa1`, and v237 shows that the
faulting instruction stores through `x8`.  This means the linker deliberately
caused a `SIGSEGV` by writing to the abort-code address.

The three call sites immediately before `__early_abort` pass constants:

| call site | abort code |
| --- | --- |
| `0x1002c8` -> `__early_abort` | `0xbd` / `189` |
| `0x1002d0` -> `__early_abort` | `0x14f` / `335` |
| `0x1002d8` -> `__early_abort` | `0xc4` / `196` |

v236 fault address was `0xa1`, so the actual caller is likely another call site
or optimized path not fully covered by the ±`0x80` disassembly window.  Next work
should expand call-site analysis and map abort-code constants to bionic linker
source checks.

## Next Step

Recommended next work:

1. disassemble or symbol-scan all call references to
   `__dl__ZL13__early_aborti`;
2. map the abort argument `0xa1`/`161` to the corresponding bionic linker source
   check if source for this Samsung build or matching Android branch can be
   correlated;
3. compare native private namespace process context against Android context only
   after the abort condition is identified.

Wi-Fi daemon start remains blocked until this early-abort cause is understood or
bypassed by a safer execution path.

## Guardrails

- No Android daemon execution.
- No Wi-Fi scan/connect.
- No rfkill write.
- No credential collection.
- No system/vendor write.
- Host output directories/files are private.

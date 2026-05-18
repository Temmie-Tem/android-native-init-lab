# Native Init v237 Linker Offset Symbolization

## Summary

- Goal: map the v236 Android `linker64` crash file offset `0x1002f4` to ELF
  section, nearest symbol, and bounded disassembly context.
- Current result: PREPARED / `linker-offset-symbolization-blocked-no-elf`.
- Reason: v236 crash evidence was parsed successfully, but the matching device
  `linker64` ELF was not available in the host checkout and live serial/NCM
  access was unavailable during this run.
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

Optional device pull path is intentionally narrow:

```text
/mnt/system/system/apex/com.android.runtime/bin/linker64
```

The only device mutation allowed by the tool is the existing read-only
`mountsystem ro` command. File export uses `toybox base64 -w 0` from the
allowlisted linker path.

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

No-ELF evidence result:

```json
{
  "decision": "linker-offset-symbolization-blocked-no-elf",
  "pass": false,
  "reason": "matching linker64 ELF was not provided or pulled",
  "offsets": ["0x1002f4"],
  "case_count": 6
}
```

Local ELF smoke test used the static helper binary only to verify the host
`readelf`/`objdump` path:

```bash
python3 scripts/revalidation/wifi_linker_offset_symbolize.py \
  --out-dir tmp/wifi/v237-local-elf-smoke \
  --linker-elf stage3/linux_init/helpers/a90_android_execns_probe \
  --offset 0x400 analyze
```

Smoke result:

```json
{
  "decision": "linker-offset-disassembled-no-symbol",
  "pass": true,
  "section": ".text",
  "mapped_vaddr": "0x400400",
  "disassembly": "host/objdump-crash-window.txt"
}
```

This validates the host-side section/disassembly machinery, but it is not a
conclusion about Android `linker64`.

## v236 Evidence Reuse

The v237 tool successfully parsed v236 crash captures and confirmed:

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

## Blocker

The matching Android `linker64` ELF is required before v237 can become a PASS.
The repository does not currently contain that exact file, and the active device
connection was not reachable in this run.

Observed access state during the run:

- `a90ctl version`: failed with `A90P1 END marker not found before timeout` and
  `Connection refused`.
- `ping 192.168.7.2`: failed, 100% packet loss.
- `tcpctl_host.py status`: failed with TCP timeout.

## Next Command

When serial bridge/NCM is restored, run:

```bash
python3 scripts/revalidation/wifi_linker_offset_symbolize.py \
  --out-dir tmp/wifi/v237-linker-offset-symbolize-live \
  --pull-from-device \
  analyze
```

Expected PASS decision if the ELF exports and analysis succeeds:

```text
linker-offset-symbolized
```

or, if symbols are stripped but disassembly is available:

```text
linker-offset-disassembled-no-symbol
```

## Guardrails

- No Android daemon execution.
- No Wi-Fi scan/connect.
- No rfkill write.
- No credential collection.
- No system/vendor write.
- Host output directories/files are private.

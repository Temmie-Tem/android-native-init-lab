# Native Init v237 Linker Offset Symbolization Plan

## Summary

- v237 focuses on the fixed Android linker crash offset found by v236.
- Goal: convert `linker64` crash PC file offset `0x1002f4` into ELF section,
  nearest symbol, and bounded disassembly context when the matching linker ELF is
  available.
- Scope is host-side evidence tooling and documentation only; no PID1 boot image
  change, Wi-Fi daemon start, scan, connect, DHCP, credential handling, or Android
  partition write.

## Inputs

- v236 evidence: `tmp/wifi/v236-linker-crash-capture-live/manifest.json` and
  `matrix/*.txt`.
- Target ELF: matching `/apex/com.android.runtime/bin/linker64` from the device.
- Default remote source for optional pull:
  `/mnt/system/system/apex/com.android.runtime/bin/linker64`.

## Implementation

- Add `scripts/revalidation/wifi_linker_offset_symbolize.py`.
- Modes:
  - `plan`: write a private out-dir summary without touching the device.
  - `analyze`: parse v236 evidence, optionally pull linker64 through base64, and
    run host `readelf`/`objdump` symbolization.
- Safety guardrails:
  - allowlisted remote linker paths only;
  - read-only `mountsystem ro` only;
  - no daemon execution;
  - no Wi-Fi/rfkill/network mutation;
  - no system/vendor write;
  - private output files only.

## Analysis Rules

1. Parse v236 crash files for:
   - `capture.crash.regset.word32` as PC;
   - `capture.crash.siginfo.addr` as fault address;
   - linker64 executable mapping from `A90_EXECNS_CAPTURE_crash_maps`.
2. Compute file offset from maps:
   `file_offset = pc - mapping_start + mapping_file_offset`.
3. Verify all selected v236 cases agree on one offset.
4. If linker ELF is available:
   - compute SHA-256 and `file` output;
   - parse LOAD segments and section table;
   - map file offset to virtual address;
   - find nearest symbol from `readelf -Ws`;
   - produce bounded disassembly around the mapped virtual address.
5. If linker ELF is unavailable:
   - report `linker-offset-symbolization-blocked-no-elf`;
   - keep the v236-derived offset and exact next command to rerun with pull.

## Test Plan

- `python3 scripts/revalidation/wifi_linker_offset_symbolize.py plan`
- `python3 scripts/revalidation/wifi_linker_offset_symbolize.py analyze --no-pull`
- If bridge is available:
  `python3 scripts/revalidation/wifi_linker_offset_symbolize.py analyze --pull-from-device`
- Static checks:
  - `python3 -m py_compile scripts/revalidation/wifi_linker_offset_symbolize.py`
  - `git diff --check`

## Acceptance

- PASS when matching linker ELF is analyzed and `0x1002f4` maps to one section,
  nearest symbol/disassembly context is written, and v236 offset consistency is
  preserved.
- Non-PASS but useful when device pull is unavailable; this must be explicitly
  classified as missing ELF, not as a linker conclusion.

## Next Step After PASS

- Use the disassembly/symbol result to decide whether the crash is caused by a
  missing Android process context input, missing runtime mount/config, or a
  linker-internal assumption that cannot be satisfied safely in native init.

# Native Init v391 Libc Symbolization Plan

## Purpose

V390 captured `servicemanager` SIGABRT PC/LR map rows and proved both addresses are inside bionic `libc.so`. V391 pulls the matching Android `libc.so` read-only from the mounted system image and maps those offsets to section, symbol, and disassembly context.

The goal is fatal-path attribution. It is not a runtime repair and it is not Wi-Fi bring-up.

## Starting Evidence

- V390 approved live: `docs/reports/NATIVE_INIT_V390_APPROVED_LIVE_RESULT_2026-05-20.md`
- V390 evidence: `tmp/wifi/v390-approved-full-20260520-063910/`
- V390 map-row result:
  - PC: `/apex/com.android.runtime/lib64/bionic/libc.so + 0x8bebc`
  - LR: `/apex/com.android.runtime/lib64/bionic/libc.so + 0x8be90`
- Read-only device path found after V390:
  - `/mnt/system/system/apex/com.android.runtime/lib64/bionic/libc.so`

## Scope

Implement and run a V391 host tool:

- parse V390 `run-system-servicemanager.txt`.
- extract `capture.crash.maprow.pc.relative_offset`.
- extract `capture.crash.maprow.lr.relative_offset`.
- optionally pull allowlisted Android `libc.so` via:
  - `version`
  - `status`
  - `mountsystem ro`
  - `stat /mnt/system/system/apex/com.android.runtime/lib64/bionic/libc.so`
  - `toybox base64 -w 0 /mnt/system/system/apex/com.android.runtime/lib64/bionic/libc.so`
- decode to a private host evidence file.
- run `file`, `readelf`, `addr2line`, and `objdump` on the pulled ELF.
- record section, nearest symbol, selected instruction, and disassembly window for PC/LR.

## Non-Goals

V391 must not perform:

- Wi-Fi HAL start.
- Wi-Fi scan/connect/link-up.
- `servicemanager`, `hwservicemanager`, CNSS, wificond, supplicant, or hostapd start.
- credentials, DHCP, routing, rfkill writes.
- driver bind/unbind or firmware mutation.
- Android partition writes.
- runtime repair.

## Artifact

Tool:

```text
scripts/revalidation/wifi_service_manager_libc_symbolize.py
```

Expected live evidence:

```text
tmp/wifi/v391-libc-symbolize-20260520-065233/
```

## Validation Plan

Static/local validation:

1. Compile the new Python tool.
2. Run plan-only mode and confirm no device command/mutation/daemon/Wi-Fi action.
3. Run no-pull mode against V390 evidence and confirm it extracts PC/LR offsets but blocks on missing `libc.so`.

Read-only live validation:

1. Run `--pull-from-device analyze`.
2. Confirm only allowlisted read-only commands run.
3. Confirm pulled ELF size and SHA256 are recorded.
4. Confirm PC/LR map into `.text`.
5. Confirm PC/LR resolve to bionic `abort`.
6. Confirm device mutation, daemon start, and Wi-Fi bring-up are all `False`.

## Expected Outcome

V391 should turn the V390 map rows into:

```text
pc: libc.so + 0x8bebc -> abort
lr: libc.so + 0x8be90 -> abort
```

If `addr2line` lacks file/line info, `objdump` disassembly still provides the needed abort-delivery context.

## Next Step

If V391 proves PC/LR are only inside bionic `abort`, the next useful step is not Wi-Fi HAL. V392 should capture enough caller context to identify who called `abort`: likely frame pointer/backchain capture from x29/SP, more selected registers, or a bounded call-stack reconstruction while the tracee is stopped.

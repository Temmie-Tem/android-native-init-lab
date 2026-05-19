# Native Init v391 Libc Symbolization Result

## Summary

V391 successfully pulled the matching Android bionic `libc.so` from the mounted system image using read-only commands and symbolized the V390 `servicemanager` SIGABRT PC/LR offsets.

Both PC and LR resolve to bionic `abort`. This confirms V390 stopped inside abort delivery, not at the original `servicemanager` fatal call site.

This is not Wi-Fi bring-up. Wi-Fi HAL, scan, connect, credentials, DHCP, routing, rfkill writes, firmware mutation, driver bind/unbind, and Android partition writes were not executed.

## Evidence

- Plan: `docs/plans/NATIVE_INIT_V391_LIBC_SYMBOLIZATION_PLAN_2026-05-20.md`
- Tool: `scripts/revalidation/wifi_service_manager_libc_symbolize.py`
- Input V390 live log: `tmp/wifi/v390-approved-full-20260520-063910/live/native/run-system-servicemanager.txt`
- V391 live evidence: `tmp/wifi/v391-libc-symbolize-20260520-065233/`

## Validation

Static/local:

```text
python3 -m py_compile scripts/revalidation/wifi_service_manager_libc_symbolize.py
python3 scripts/revalidation/wifi_service_manager_libc_symbolize.py --out-dir tmp/wifi/v391-plan-check plan
python3 scripts/revalidation/wifi_service_manager_libc_symbolize.py --out-dir tmp/wifi/v391-no-pull-check --no-pull analyze
```

Results:

- plan: `service-manager-libc-symbolization-plan-ready`, device command `False`, mutation `False`, daemon `False`, Wi-Fi `False`.
- no-pull: `service-manager-libc-symbolization-blocked-no-elf`, offsets extracted, device command `False`, mutation `False`, daemon `False`, Wi-Fi `False`.

Read-only live:

```text
python3 scripts/revalidation/wifi_service_manager_libc_symbolize.py \
  --out-dir tmp/wifi/v391-libc-symbolize-20260520-065233 \
  --run-log tmp/wifi/v390-approved-full-20260520-063910/live/native/run-system-servicemanager.txt \
  --pull-from-device \
  --timeout 240 \
  analyze
```

Result:

```text
decision: service-manager-libc-symbolization-pass
pass: True
reason: PC/LR offsets mapped to libc sections, nearest symbols, and disassembly context
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Device Commands

V391 executed only allowlisted read-only commands:

```text
version
status
mountsystem ro
stat /mnt/system/system/apex/com.android.runtime/lib64/bionic/libc.so
run /cache/bin/toybox base64 -w 0 /mnt/system/system/apex/com.android.runtime/lib64/bionic/libc.so
```

No Android daemon or Wi-Fi process was started.

## Pulled ELF

Source:

```text
/mnt/system/system/apex/com.android.runtime/lib64/bionic/libc.so
```

Host evidence file:

```text
tmp/wifi/v391-libc-symbolize-20260520-065233/files/libc.so
```

Metadata:

```text
size: 1331136
sha256: 05b46edc9bf95e52c7eaf73ee340d78c52971ca2482cafa3c4d0c510691ba204
ELF: ELF64 AArch64 shared object
Build ID: f85c82661f93b28ab3119d33214bb7b9
```

## Symbolization Result

### PC

V390:

```text
capture.crash.maprow.pc.relative_offset=0x8bebc
```

V391:

```text
offset: 0x8bebc
mapped_vaddr: 0x8bebc
section: .text
addr2line: abort
selected_instruction: 8bebc: 910003e1  mov x1, sp
nearest_symbol: abort@@LIBC + 168
```

### LR

V390:

```text
capture.crash.maprow.lr.relative_offset=0x8be90
```

V391:

```text
offset: 0x8be90
mapped_vaddr: 0x8be90
section: .text
addr2line: abort
selected_instruction: 8be90: b0fffce8  adrp x8, 28000 <je_sz_size2index_tab+0x200>
nearest_symbol: abort@@LIBC + 124
```

## Interpretation

V391 proves the current PC/LR evidence is inside bionic `abort`, specifically around the syscall path that sends SIGABRT:

```text
8beb4: 52801e08  mov w8, #0xf0
8beb8: d4000001  svc #0x0
8bebc: 910003e1  mov x1, sp
```

This matches V390's register evidence:

```text
x2=0x6
x8=0xf0
```

`x8=0xf0` is AArch64 `rt_tgsigqueueinfo`, so the captured stop is abort delivery after `servicemanager` already decided to abort. The original fatal caller is still above `abort` on the call stack.

## Conclusion

V391 resolves the V390 `elf-artifact` blocker. The remaining blocker is caller attribution, not ELF symbolization.

The next step should capture bounded caller context from the crashing process while it is ptrace-stopped:

- x29/frame pointer.
- x30/LR already captured but only points within `abort`.
- stack words around SP and frame-chain candidate addresses.
- map-row resolution for candidate return addresses.
- optional bounded backchain reconstruction if frame pointers are valid.

Wi-Fi HAL/start/scan/connect remains blocked until the `servicemanager` abort caller is identified or proven irrelevant to the Wi-Fi path.

## Next Step

V392 should implement caller-context/backchain capture in `a90_android_execns_probe` without starting Wi-Fi HAL. It should preserve the v390 cleanup behavior and bounded output constraints.

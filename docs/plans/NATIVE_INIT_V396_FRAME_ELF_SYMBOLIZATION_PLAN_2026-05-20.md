# Native Init v396 Frame ELF Symbolization Plan

## Goal

Resolve the V392 service-manager frame-chain from "ELF missing" to actionable caller evidence by pulling only the Android system ELFs that already appeared in the captured backchain.

This is a read-only evidence step. It must not deploy helpers, start Android daemons, start Wi-Fi HAL, scan, connect, collect credentials, or mutate the device.

## Starting Evidence

- approved V392 result: `docs/reports/NATIVE_INIT_V392_APPROVED_BACKCHAIN_CAPTURE_RESULT_2026-05-20.md`
- approved V392 executor evidence: `tmp/wifi/v392-approved-full-20260520-072551/`
- V392 run log: `tmp/wifi/v392-approved-full-20260520-072551/live/native/run-system-servicemanager.txt`
- V392 framechain result:
  - frame0: `/system/lib64/liblog.so + 0x63bc`, ELF missing
  - frame1: `/system/lib64/libbase.so + 0x16188`, ELF missing
  - frame2: `/system/bin/servicemanager + 0x8294`, ELF missing
  - frame3: `/system/bin/servicemanager + 0x13b14`, ELF missing
  - frame4: bionic `libc.so + 0x84378`, `__libc_init`
  - frame5: `/system/bin/servicemanager + 0x8058`, ELF missing

## Scope

Add `scripts/revalidation/wifi_service_manager_frame_elf_pull.py` with a narrow read-only contract:

- allowlist only these remote files:
  - `/mnt/system/system/bin/servicemanager`
  - `/mnt/system/system/lib64/libbase.so`
  - `/mnt/system/system/lib64/liblog.so`
- use `mountsystem ro` only.
- collect `version` and `status` as context.
- use `stat` and `toybox base64 -w 0` for read-only file transfer.
- cap each file with `--max-file-bytes`, default `8 MiB`.
- write private evidence under the selected output directory.
- rerun `scripts/revalidation/wifi_service_manager_framechain_analyze.py` with the pulled `system-root`.

## Non-Goals

V396 must not perform:

- helper deploy or helper replacement.
- `servicemanager`, `hwservicemanager`, `vndservicemanager`, Wi-Fi HAL, `wificond`, supplicant, hostapd, CNSS, or service-manager start outside already captured evidence.
- Wi-Fi scan/connect/link-up, credentials, DHCP, routing, rfkill writes, driver bind/unbind, or firmware mutation.
- Android partition writes.
- runtime repair before caller attribution.

## Validation Plan

Static and plan-only validation:

```text
python3 -m py_compile scripts/revalidation/wifi_service_manager_frame_elf_pull.py
python3 scripts/revalidation/wifi_service_manager_frame_elf_pull.py \
  --out-dir tmp/wifi/v396-frame-elf-pull-plan \
  --run-log tmp/wifi/v392-approved-full-20260520-072551/live/native/run-system-servicemanager.txt \
  plan
```

Expected plan result:

```text
decision: service-manager-frame-elf-pull-plan-ready
pass: True
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Read-only live validation:

```text
python3 scripts/revalidation/wifi_service_manager_frame_elf_pull.py \
  --out-dir tmp/wifi/v396-frame-elf-pull-$(date +%Y%m%d-%H%M%S) \
  --run-log tmp/wifi/v392-approved-full-20260520-072551/live/native/run-system-servicemanager.txt \
  --timeout 300 \
  pull
```

Expected live result:

```text
decision: service-manager-frame-elf-symbolization-pass
pass: True
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Expected Outcome

V396 should convert the V392 missing-ELF frames into host-readable caller evidence. If the symbolized/disassembled caller points to a concrete missing runtime dependency, the next cycle should verify that dependency surface before any Wi-Fi HAL start-only attempt.

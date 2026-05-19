# v365 Plan: Service Runtime Repair Packet

- date: `2026-05-20`
- scope: no-daemon/no-link-up packet for the next bounded runtime repair smoke
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- prerequisite: V364 `hal-service-readiness-blocked`

## Summary

V364 proved the Wi-Fi HAL/service-manager start-only path is still blocked by
runtime prerequisites: Binder devnodes, service-manager process state, property
runtime, and linkerconfig visibility.

V365 does not start service-manager, Wi-Fi HAL, `wificond`, supplicant, hostapd,
`cnss-daemon`, or `cnss_diag`. Its job is to generate and validate a bounded
repair packet for the next step: V366 temporary runtime repair smoke.

The packet combines:

- V292 Binder open-only proof;
- V320 private property lookup proof;
- V362 bounded CNSS start-only proof;
- V364 blocker map;
- current live availability of `a90_android_execns_probe`, real linkerconfig
  inputs, private property root, system root, and vendor block metadata.

## References

- Android 11+ generates linker configuration at runtime under `/linkerconfig`,
  so the native private namespace must materialize linkerconfig explicitly:
  <https://source.android.com/docs/core/architecture/partitions/linker-namespace>
- HIDL HALs are binderized IPC services, so Binder/service-manager readiness is
  a prerequisite before Wi-Fi HAL execution:
  <https://source.android.com/docs/core/architecture/hidl>
- Android Wi-Fi has separate Vendor, Supplicant, and Hostapd HAL surfaces, so
  HAL/service-manager readiness must be solved before scan/connect:
  <https://source.android.com/docs/core/connect/wifi-hal>

## Implementation

Add packet builder:

```text
scripts/revalidation/wifi_service_runtime_repair_packet.py
```

Modes:

```bash
python3 scripts/revalidation/wifi_service_runtime_repair_packet.py \
  --out-dir tmp/wifi/v365-service-runtime-repair-packet-plan-20260520 \
  plan

python3 scripts/revalidation/wifi_service_runtime_repair_packet.py \
  --out-dir tmp/wifi/v365-service-runtime-repair-packet-live-20260520-r2 \
  run
```

The live mode only runs status/stat/ls/cat read-only checks. It does not create
Binder nodes, block nodes, property sockets, global linkerconfig mounts, or any
service process.

## V366 Approval Boundary

If V365 passes, the next explicit phrase is:

```text
approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up
```

V366 may then perform only a temporary repair smoke:

1. create temporary `/dev/block/sda29` from `/proc/partitions` major/minor;
2. create temporary `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder` from known
   Binder minor numbers;
3. run private property lookup through `/cache/bin/a90_android_execns_probe`;
4. check real linkerconfig inputs for later private namespace use;
5. cleanup temporary nodes;
6. verify no service-manager/CNSS/Wi-Fi link surface remains.

## Guardrails

V365 and the generated V366 packet still forbid:

- service-manager, `hwservicemanager`, or `vndservicemanager` execution;
- Wi-Fi HAL, `wificond`, supplicant, hostapd, `cnss-daemon`, or `cnss_diag`
  execution;
- Wi-Fi scan/connect/link-up/credential/DHCP/routing;
- rfkill unblock, ICNSS bind/unbind, module load/unload, or firmware mutation;
- Android partition writes.

## Acceptance

- script compiles with `python3 -m py_compile`;
- plan mode returns `service-runtime-repair-packet-plan-ready`;
- live mode returns `service-runtime-repair-packet-ready` or a precise blocker;
- live mode confirms current environment is clean: no Binder devnodes, no
  service-manager process, no CNSS process, no Wi-Fi link surface;
- if ready, V366 exact approval phrase and future command sketch are recorded.

# Native Init V784 Memshare/CMA Surface Plan

## Goal

Classify the V783 memshare/CMA lead without triggering Wi-Fi.  V782 showed
memshare allocation failures at the modem sysmon window, while V783 showed the
first Android/native divergence is before service-notifier `74/180`.  V784
reads the current native memshare/CMA/reserved-memory surface and compares it
with the V782 failure request sizes.

## Scope

- Native live read-only collection through the existing serial bridge.
- No `boot_wlan`, `qcwlanstate ON`, daemon ordering retry, HAL start,
  scan/connect, DHCP, external ping, reboot, flash, mount, bind, or route
  change.
- Preserve enough evidence to decide whether the next lead is simple CMA
  headroom or client registration/timing/reserved-pool behavior.

## Inputs

- V782 dmesg evidence: `tmp/wifi/v782-bpf-counter-boot-wlan/native/dmesg-delta.txt`
- V783 manifest: `tmp/wifi/v783-android-native-pil-gap/manifest.json`
- live native v724 bridge on `127.0.0.1:54321`

## Method

1. Confirm stock native v724 runtime.
2. Read `/proc/cmdline`, focused `/proc/meminfo`, `/proc/buddyinfo`, and focused
   `/proc/iomem`.
3. Read memshare platform sysfs tree and safe attributes.
4. Read focused reserved-memory/devicetree paths for CMA, modem, MHI, WLAN, and
   memshare.
5. Read focused dmesg lines for memshare, CMA, service-notifier, QRTR, sysmon,
   WLAN-PD, ICNSS-QMI, BDF, firmware-ready, and `wlan0`.
6. Parse V782 request/failure sizes and compare them with current idle CMA
   headroom.

## Success Criteria

- Runtime is `A90 Linux init 0.9.68 (v724)`.
- All live commands complete successfully.
- No mutating command or Wi-Fi trigger executes.
- V782 memshare/CMA failure sizes are parsed.
- Current native memshare sysfs/reserved-memory/CMA state is classified.
- Next candidate is narrowed without repeating blind WLAN triggers.

## Safety Boundaries

- no boot image or partition write
- no reboot
- no mount or unmount
- no bind/unbind or `driver_override`
- no module load/unload
- no `boot_wlan` or `qcwlanstate ON`
- no service-manager, Wi-Fi HAL, scan/connect, credential use, DHCP, route, or
  external ping

## Runner

```bash
python3 -m py_compile scripts/revalidation/native_wifi_memshare_cma_surface_v784.py
python3 scripts/revalidation/native_wifi_memshare_cma_surface_v784.py plan
python3 scripts/revalidation/native_wifi_memshare_cma_surface_v784.py run
```

# Native Init V758 Kernel Instrumentation Feasibility Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_kernel_instrumentation_feasibility_v758.py`
- plan evidence: `tmp/wifi/v758-kernel-instrumentation-feasibility-plan/`
- run evidence: `tmp/wifi/v758-kernel-instrumentation-feasibility/`
- decision: `v758-source-acquisition-required-before-kernel-instrumentation`
- status: `pass`

## Summary

V758 checked whether the V757-selected kernel/source/boot-image instrumentation
route can be patched immediately. It cannot: boot image tooling and rollback
artifacts are present, but exact kernel/QCACLD source is not local.

Result:

```text
local kernel source: absent
target QCACLD/CNSS source files: absent
current native boot image: present
v319 boot image: present
v261 rollback image: present
v48 known-good image: present
mkbootimg/build/flash tooling: present
patch-now route: no
```

V759 should acquire or stage exact compatible Samsung kernel source before any
instrumentation patch is attempted.

## Checks

| check | result |
| --- | --- |
| V757 input | pass; `v757-boot-image-log-instrumentation-selected` |
| local kernel source | blocked; no source tree or target QCACLD/CNSS files found |
| boot image and rollback | pass; current, v319, v261 rollback, and v48 known-good images exist |
| host tooling | pass; build, mkbootimg, flash, and rollback docs/tools exist |
| patch-now route | review; safe handoff is possible after source, but patching now is not |

## Safety Result

V758 was host-only. It executed no device command, no boot image or partition
write, no source patch, no mount, no Wi-Fi trigger, no service-manager or Wi-Fi
HAL start, no scan/connect, no credential use, no DHCP/routes, and no external
ping.

## Interpretation

The project has a practical rollback envelope for boot-image experiments, but
not the source material needed to add trustworthy kernel-side log points. A
binary patch or blind boot-image mutation would be the wrong next step.

The next unit should be source acquisition/staging:

1. search/download or locate the exact Samsung open-source package for the
   SM-A908N Android 12 A908NKSU5EWA3-compatible kernel;
2. verify it contains the target QCACLD/CNSS files;
3. record toolchain/build prerequisites;
4. only then plan minimal log instrumentation around `__hdd_module_init`,
   `pld_init`, `hdd_init`, and `wlan_hdd_register_driver`.

## Evidence

- `tmp/wifi/v758-kernel-instrumentation-feasibility/manifest.json`
- `tmp/wifi/v758-kernel-instrumentation-feasibility/summary.md`

## Source References

- Samsung Open Source Release Center:
  <https://opensource.samsung.com/?method=search>
- SM-A908N A908NKSU5EWA3 firmware reference:
  <https://samfw.com/firmware/SM-A908N/KOO/A908NKSU5EWA3>
- SM-A908N Korea firmware sequence:
  <https://www.sammobile.com/samsung/galaxy-a90-5g/firmware/SM-A908N/KOO/>

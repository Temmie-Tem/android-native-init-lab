# V896 Android mdm_helper Image Contract Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| host-only classifier | `tmp/wifi/v896-android-mdm-helper-image-contract/manifest.json` | `v896-android-mdm-helper-image-contract-classified` |

V896 classifies the V895 blocker as a missing Android `mdm_helper` / `ks` MHI
image/link contract, not as a need for blind `ESOC_BOOT_DONE`, longer polling,
or generic eSoC command-engine expansion.

## Implementation

- Added classifier:
  `scripts/revalidation/native_wifi_android_mdm_helper_image_contract_v896.py`
- Evidence:
  `tmp/wifi/v896-android-mdm-helper-image-contract/summary.md`
- Latest pointer:
  `tmp/wifi/latest-v896-android-mdm-helper-image-contract.txt`
- The classifier is host-only. It does not contact the device or run ADB.

## Findings

- V895 native negative control:
  - `ESOC_REQ_IMG` observed.
  - `ESOC_IMG_XFER_DONE` sent.
  - `ESOC_GET_STATUS` stayed `0` for `86` polls.
  - `ESOC_BOOT_DONE` was not sent.
  - GPIO 142 `mdm status` IRQ count stayed `0` across `89` phases.
- Android positive control:
  - `mdm3=ONLINE`.
  - WLFW, BDF, WLAN-PD, and `wlan0` markers are present.
  - `/proc/interrupts` shows GPIO 142 `mdm status` IRQ count `1`.
  - Android dmesg shows PCIe RC1 link initialized before WLAN-PD/BDF markers.
- Android actor contract:
  - `mdm_helper` holds `/dev/esoc-0`.
  - `ks` runs under `vendor_mdm_helper` context and holds `/dev/esoc-0`.
  - `ks` uses `/dev/mhi_0305_01.01.00_pipe_10` and bootdevice image path.
  - `pm-service` holds `/dev/subsys_esoc0` and `/dev/subsys_modem`.
  - init, ueventd, and SELinux rules for these actors are present.
- Source contract:
  - `ESOC_REQ_IMG` is queued from the PON path.
  - Source comment states userspace confirms link establishment.
  - `ESOC_IMG_XFER_DONE` starts the MDM2AP status check window.
  - GPIO 142 IRQ is the path that sets readiness.

## Interpretation

The existing Android evidence is sufficient for V896; a Magisk module or new
Android boot capture is not required yet. Android already proves the readiness
line fires when the `mdm_helper`/`ks` path is active. Native V895 proves that
immediate `IMG_XFER_DONE` without that path does not make the line fire.

The next safe step is to design the smallest native equivalent of the Android
`mdm_helper`/`ks` contract. It must be fail-closed and host-only first.

## Guardrails

- No Android boot, ADB command, Magisk module, live eSoC ioctl,
  `/dev/subsys_esoc0` open, actor start, daemon start, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, external ping, module load/unload,
  boot image write, partition write, firmware mutation, GPIO write, sysfs
  write, debugfs write, or Wi-Fi link-up occurred in V896.

## Next

V897 should be a host-only native `mdm_helper`/`ks` contract design and
preflight classifier. Only after that should a separate bounded live gate
consider starting Android-equivalent actors.

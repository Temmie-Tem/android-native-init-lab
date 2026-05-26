# V1029 PM Runtime Input Delta Plan

- date: `2026-05-26`
- type: host-only classifier
- inputs:
  - `tmp/wifi/v1028-pm-proxy-helper-modem-get-classifier/manifest.json`
  - `tmp/wifi/v1024-fast-fd-android-timing-handoff-live-20260526-181232/v1022-early-android-pm-esoc-timing/android/commands/sample-loop.txt`
  - `tmp/wifi/v1024-fast-fd-android-timing-handoff-live-20260526-181232/v1022-early-android-pm-esoc-timing/android/commands/props-before.txt`
  - `tmp/wifi/v1027-pm-full-contract-live/native/mdm-helper-cnss-before-esoc.txt`
  - `tmp/wifi/v1027-pm-full-contract-live/native/post-dmesg-wifi-esoc-tail.txt`
  - `tmp/wifi/v863-pm-proxy-helper-rc-live/manifest.json`

## Objective

Classify the Android/native runtime input delta behind the V1028
`pm_proxy_helper` modem-get blocker before changing helper behavior or retrying
the PM full-contract live gate.

## Gate

Compare the PM actors across Android-positive and native-negative evidence:

```text
Android V1024:
  pm_proxy_helper attr=u:r:per_proxy_helper:s0 -> /dev/subsys_modem
  pm-service      attr=u:r:vendor_per_mgr:s0   -> /dev/subsys_modem
  pm-proxy        attr=u:r:vendor_per_proxy:s0
  mdm_helper      attr=u:r:vendor_mdm_helper:s0 -> /dev/esoc-0

Native V1027:
  target contexts requested and accepted
  captured attr/current remains kernel
  pm_proxy_helper enters modem subsystem-get/PIL loading
```

## Guardrails

- host-only evidence parsing
- no device command
- no actor start
- no daemon start
- no Wi-Fi HAL, `wificond`, scan/connect, credentials, DHCP, route, or external ping
- no `/dev/subsys_esoc0` open
- no eSoC ioctl, notify, BOOT_DONE, GPIO/sysfs/debugfs write
- no boot image or partition write

## Success Criteria

The classifier passes if it proves:

- V1028 already classified the modem-get blocker.
- Android PM actors run in expected vendor SELinux domains while holding the
  required fd contract.
- Native V1027 requested matching target contexts and `setexeccon` reported OK.
- Native V1027 captured `attr/current=kernel` for the same actor class.
- Native V1027 still has the fd gap and modem-get dmesg lines.
- Existing helper/source already models the basic init contract, so the next
  unit should target runtime-domain proof rather than generic init-contract
  replay.

## Commands

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_runtime_input_delta_v1029.py
python3 scripts/revalidation/native_wifi_pm_runtime_input_delta_v1029.py run
```

## Next

If V1029 passes, V1030 should be source/build-only support for a fail-closed PM
actor runtime-domain proof. A live PM full-contract retry should not run until
the helper can prove PM actors are actually executing outside `kernel` context.

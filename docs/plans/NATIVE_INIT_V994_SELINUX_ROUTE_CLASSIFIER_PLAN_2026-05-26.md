# Native Init V994 SELinux Route Classifier Plan

## Goal

Classify the next safe route after V993 proved that `wificond` remains in the
`kernel` SELinux context at both traced `exec` and crash stops.

V994 is host-only. It does not contact the device and does not retry the Android
service-window.

## Inputs

- V490 policy-load evidence:
  `tmp/wifi/v490-run-v52-20260521-082835/manifest.json`
- V491 post-load domain proof:
  `tmp/wifi/v491-run-v52-20260521-082856/manifest.json`
- V990 service registration gap:
  `tmp/wifi/v990-wificond-service-registration-gap/manifest.json`
- V993 service-window live evidence:
  `tmp/wifi/v993-android-service-window-live-v168/manifest.json`
- V993 transcript:
  `tmp/wifi/v993-android-service-window-live-v168/native/mdm-helper-cnss-before-esoc.txt`

## Classification Questions

1. Does V990 prove the `wifinl80211` service context exists?
2. Does V993 prove `setexeccon` was accepted but `wificond` stayed `kernel`
   after `execv`?
3. Did V993 refresh current-boot V490 policy-load/domain proof before the
   service-window?
4. Does AOSP `servicemanager` require `service_manager:add` checks against the
   caller SELinux SID?
5. Is the next step a current-boot SELinux refresh/domain proof, a full native
   Android init reexec path, or a private service-manager compatibility bypass?

## Guardrails

- No device command.
- No policy load.
- No actor start, service-manager start, Wi-Fi HAL start, `wificond`, or daemon
  start.
- No scan/connect/link-up, credentials, DHCP/routes, external ping, boot image
  write, partition write, firmware mutation, GPIO write, sysfs write, or
  debugfs write.

## Success Criteria

- Produce a private V994 manifest and summary.
- Select exactly one next route.
- If evidence is incomplete, block before any live action.

## Expected Decision

If all existing evidence is present, V994 should select a fresh current-boot
SELinux policy-load/domain proof before another Android service-window retry.
The service-manager bypass route should stay closed unless a later proof shows
that the SELinux transition cannot be repaired cleanly.

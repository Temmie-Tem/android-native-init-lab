# Native Init V924 CNSS/WLFW Precondition Gap Plan

## Goal

Classify why V923 can start `mdm_helper`, `cnss_diag`, and `cnss-daemon`, yet
does not reach the Android-positive `cnss-daemon wlfw_start` marker.

## Scope

V924 is host-only. It parses existing V923 live evidence plus V914/V919 Android
positive-control evidence. It does not contact the device or start any actor.

## Inputs

- `tmp/wifi/v923-mdm-helper-cnss-before-esoc-capture-live/manifest.json`
- `tmp/wifi/v923-mdm-helper-cnss-before-esoc-capture-live/native/mdm-helper-cnss-before-esoc.txt`
- `tmp/wifi/v923-mdm-helper-cnss-before-esoc-capture-live/native/post-dmesg-wifi-esoc-tail.txt`
- `tmp/wifi/v914-v913-android-timeline-reclassifier/manifest.json`
- `tmp/wifi/v919-sdx50m-soft-reset-blocker-classifier/manifest.json`

## Questions

1. Did native `cnss-daemon` reach the kernel `cld80211` netlink surface?
2. Did native produce any WLFW/BDF/`wlan0` upper path marker?
3. Which runtime namespace warnings are present in native stderr?
4. Does Android positive-control evidence still prove the WLFW/BDF/`wlan0`
   sequence?
5. Is the next useful unit another live retry or a focused runtime namespace
   repair?

## Hard Guardrails

- No device contact, ADB, Android boot, serial command, actor start, eSoC ioctl,
  `/dev/subsys_esoc0` open, service-manager, Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, external ping, boot image write, partition write,
  firmware mutation, GPIO/sysfs/debugfs write, module load/unload, bind, or
  unbind.

## Success Criteria

- Produce private V924 evidence under `tmp/wifi/`.
- Produce a report with a ranked next gate.
- Keep final native Wi-Fi bring-up unclaimed.

## Expected Next

If V924 confirms that CNSS reaches `cld80211` but not `wlfw_start`, and native
stderr still shows linkerconfig/property-context gaps, V925 should repair or
prove the CNSS runtime namespace before any further `/dev/subsys_esoc0` live
gate.

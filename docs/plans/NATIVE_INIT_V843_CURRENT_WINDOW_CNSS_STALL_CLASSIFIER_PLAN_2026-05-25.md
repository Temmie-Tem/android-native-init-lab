# Native Init V843 Current-Window CNSS Stall Classifier Plan

## Goal

Classify the current V840 provider-first `cnss-daemon` retry stall point from
existing evidence, without repeating a live device window.

## Scope

V843 is host-only. It reads V842 and V840 artifacts and does not contact the
device, start daemons, start service-manager, start Wi-Fi HAL, scan/connect,
use credentials, run DHCP, change routes, ping externally, write sysfs/debugfs,
write boot images, write partitions, or flash a custom kernel.

## Inputs

- V842 CNSS pre-WLFW contract classifier:
  `tmp/wifi/v842-cnss-prewlfw-contract-classifier/manifest.json`
- V840 provider-first prearmed listener manifest:
  `tmp/wifi/v840-provider-first-prearmed-listener-live/manifest.json`
- V840 helper transcript with cleanup-time stall snapshot:
  `tmp/wifi/v840-provider-first-prearmed-listener-live/native/companion-start-only-with-holder.txt`

## Classification Rules

V843 passes if:

1. V842 selected the current-window CNSS stall snapshot as the next gate.
2. V840 still reports provider-first prearmed listener pass with no WLAN-PD
   indication.
3. The V840 helper transcript contains the captured `cnss-daemon` retry stall
   snapshot.
4. The captured retry process is alive in `poll`/`futex` wait surfaces with
   CNSS user socket and netlink evidence.
5. V840 marker counts still show no `wlfw_start`, WLAN-PD, BDF, FW-ready, or
   `wlan0`.

## Expected Decision

Expected result: `v843-cnss-retry-poll-futex-prewlfw-event-gap`.

This means the native `cnss-daemon` retry is not immediately crashing or
blocked at broad launcher setup. It is alive and waiting for an event source
that still never publishes the pre-WLFW/WLAN-PD progression.

## Next Gate

V844 should classify the missing source-backed ICNSS/WLFW event publication
prerequisite before any Wi-Fi HAL, scan/connect, DHCP/routes, credential, or
external ping action.

# Native Init V920 CNSS-before-eSoC Trigger Gate Plan

## Context

V919 reclassified the current Wi-Fi bring-up blocker using existing Android and
V918 evidence:

- Android positive ordering:
  `vendor.mdm_helper` starts at `8.148s`, `cnss-daemon wlfw_start` appears at
  `8.349s`, `__subsystem_get(esoc0)` appears at `8.402s`, then WLAN-PD, BDF,
  and `wlan0` appear.
- V918 native ordering:
  `pm-service` and `mdm_helper` start, `mdm_helper` holds `/dev/esoc-0`, the
  gated `/dev/subsys_esoc0` child opens, and the child blocks in
  `sdx50m_toggle_soft_reset` with no KS/MHI/WLFW/BDF/wlan0 progression.

The next useful gate must therefore test the missing Android precondition before
the native `/dev/subsys_esoc0` trigger is opened. It must not repeat the V918
D-state open unless the CNSS/WLFW precondition is actually observed.

## Goal

Design the smallest fail-closed native proof that starts the Android-like
CNSS/WLFW request path before attempting the `/dev/subsys_esoc0` trigger.

## Cycle Label

`V920 CNSS-before-eSoC trigger gate design`

## Scope

V920 is host-only/design-only. It consumes existing reports, source, helper
contracts, and evidence. It must not contact the device or run a live proof.

## Non-Goals

- No Wi-Fi scan, association, credential use, DHCP, route mutation, or external
  ping.
- No Wi-Fi HAL, wificond, supplicant, hostapd, or Android framework bring-up.
- No boot image, partition, firmware, GPIO, sysfs, debugfs, module, rfkill, bind,
  or unbind mutation.
- No live `/dev/subsys_esoc0` open in V920.
- No fake `ESOC_NOTIFY`, `ESOC_BOOT_DONE`, or direct GPIO forcing.

## Prior Evidence Constraints

| Evidence | Constraint |
| --- | --- |
| V704 | CNSS retry can remain alive without immediate Binder failure, yet still stall before WLFW. |
| V752 | CNSS companion before `boot_wlan` did not advance HDD/QMI/BDF/wlan0 without the corrected eSoC trigger context. |
| V918 | Corrected `mdm_helper` fd gate reaches the real SDX50M power-up path but blocks in `sdx50m_toggle_soft_reset`. |
| V919 | Android orders `cnss-daemon wlfw_start` before `__subsystem_get(esoc0)`, so the next trigger must prove that precondition first. |

## Proposed V921 Source/Build Unit

Add helper support for a new bounded mode, tentatively:

```text
wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture
```

The mode should implement this order:

1. materialize private Android runtime namespace and required `/dev` nodes;
2. mount/read-only vendor/system surfaces exactly like the current helper
   contract requires;
3. start `pm-service` only if needed for existing property/runtime parity;
4. start `/vendor/bin/mdm_helper`;
5. wait until `mdm_helper` owns `/dev/esoc-0`;
6. start `cnss_diag` and `cnss-daemon` in their existing start-only identity
   contract;
7. observe for a bounded `cnss-daemon wlfw_start` marker or an equivalent
   WLFW request/process marker;
8. if and only if the WLFW precondition is observed, start a child that opens
   `/dev/subsys_esoc0`;
9. capture wchan/syscall/stack/status, dmesg deltas, `ks`, MHI pipe, WLFW/BDF,
   WLAN-PD, and `wlan0` surfaces;
10. terminate/reap actors if possible; if the trigger child or actor cannot be
    proven stopped, require reboot cleanup exactly as V918 did.

## Fail-Closed Gate

The helper must explicitly report:

```text
cnss_before_esoc.wlfw_precondition_observed=0|1
cnss_before_esoc.subsys_esoc0_open_gate=cnss-wlfw-precondition
cnss_before_esoc.subsys_esoc0_open_attempted=0|1
```

Rules:

- If `wlfw_precondition_observed=0`, do **not** open `/dev/subsys_esoc0`.
- If `cnss-daemon` crashes, exits, or never reaches WLFW, do **not** open
  `/dev/subsys_esoc0`; capture the stall/crash evidence and stop.
- If `wlfw_precondition_observed=1`, the trigger child may open
  `/dev/subsys_esoc0` under a short timeout with blocker snapshots and mandatory
  cleanup/reboot handling.

## Live Success Criteria for Later Cycle

The later live gate is successful if it proves one of these outcomes:

| Outcome | Meaning |
| --- | --- |
| `wlfw-precondition-missing-no-open` | CNSS/WLFW precondition still cannot be reproduced natively; no D-state trigger was attempted. |
| `wlfw-precondition-observed-trigger-clean` | WLFW precondition was observed, trigger was attempted, all actors stopped or were safely cleaned. |
| `wlfw-precondition-observed-wlan-progress` | WLFW/BDF/WLAN-PD/wlan0 progressed without scan/connect/DHCP/external ping. |
| `wlfw-precondition-observed-trigger-reboot-cleaned` | Trigger still blocked or actors remained, but cleanup reboot restored bootstatus/selftest. |

The final project goal is not complete until native Wi-Fi connects and
`google.com` ping passes. Any V920/V921/V922/V923 pass is only an intermediate
blocker classification.

## Live Failure Criteria for Later Cycle

- `/dev/subsys_esoc0` opens while the WLFW precondition is absent.
- service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
  external ping execute.
- fake `ESOC_NOTIFY` or `ESOC_BOOT_DONE` executes.
- an actor remains after cleanup and reboot cleanup is not requested or fails.
- evidence omits wchan/syscall/stack/status for a blocked trigger child.

## Safety and Observability Requirements

- Preserve V918 cleanup behavior for uninterruptible child states.
- Preserve explicit forbidden counters for service-manager, HAL, scan/connect,
  credentials, DHCP/routes, external ping, notify, and boot-done.
- Capture pre/mid/post:
  - `mdm_helper` fd links;
  - `cnss-daemon` process status and selected sockets;
  - dmesg WLFW/BDF/WLAN-PD markers;
  - `/proc/interrupts` GPIO142 line;
  - `/sys/bus/mhi/devices`, `/dev/mhi_0305_01.01.00_pipe_10`;
  - `/sys/class/net/wlan0`, `/proc/net/dev`;
  - `/sys/bus/msm_subsys/devices/subsys9/state`.

## Implementation Phasing

| Version | Unit | Purpose |
| --- | --- | --- |
| V921 | source/build verifier | Add helper mode and verify fail-closed gates statically. |
| V922 | deploy-only | Deploy helper and prove remote checksum/mode parity. |
| V923 | bounded live precondition gate | Start `mdm_helper` + CNSS, only open `/dev/subsys_esoc0` if WLFW precondition appears. |

## Decision

Proceed to V921 source/build only. The next code change should not run live
actors. It should add the helper mode, explicit counters, and static verifier
needed to make the later live gate fail closed.

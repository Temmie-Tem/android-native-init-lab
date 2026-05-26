# Native Init V1073 PM Actor Exit Host Classifier Plan

## Goal

Classify the `pm-service` / `vendor.per_mgr` exit-255 boundary using only host
evidence before adding another live probe.  V1073 must determine which causes
can be ruled out from Android init rc, vendor binary strings, library
dependencies, and the V1072 exit snapshot.

## Background

V1071 closed the service-manager crash surface by materializing the SELinuxfs
runtime nodes.  V1072 then captured `per_mgr` and `per_proxy` at ptrace
`PTRACE_EVENT_EXIT` and proved the PM actors exit before holding either
`/dev/subsys_modem` or `/dev/vndbinder`.

The remaining blocker is earlier than a persistent subsystem fd:

```text
pm-service / per_mgr exit_code=255
pm-proxy / per_proxy exit_code=1
per_mgr_subsys_modem_seen=0
pm_proxy_helper_subsys_modem_seen=0
```

## Inputs

- V1072 live manifest and transcript.
- Android vendor init rc handoff from the extracted vendor image.
- Host-extracted vendor binaries:
  - `/vendor/bin/pm-service`
  - `/vendor/bin/pm-proxy`
  - `/vendor/bin/pm_proxy_helper`
- Host-extracted strings and dynamic dependency surfaces for:
  - `pm-service`
  - `pm-proxy`
  - `pm_proxy_helper`
  - `libmdmdetect.so`
  - `libperipheral_client.so`
  - `libqmi_csi.so`
  - `libqmi_cci.so`

## Gate

- Add a host-only classifier script:
  `scripts/revalidation/native_wifi_pm_actor_exit_host_classifier_v1073.py`.
- Parse `init.target.rc` and `pm_proxy_helper.rc` for PM service contracts.
- Parse V1072 exit snapshots for fd targets and exit status.
- Parse vendor strings/dependencies for binder, QMI, mdmdetect, and subsystem
  surfaces.
- Emit a private evidence manifest under
  `tmp/wifi/v1073-pm-actor-exit-host-classifier/`.

## Forbidden

- No device command execution.
- No live actor start.
- No service-manager, PM, CNSS, Wi-Fi HAL, or `mdm_helper` start.
- No `/dev/esoc*` or subsystem trigger.
- No scan/connect/DHCP/route/external ping.
- No boot image write.

## Success Criteria

- The classifier runs from existing host evidence only.
- Android init socket creation is either confirmed or eliminated.
- Current stderr capture usefulness for `pm-service` is classified.
- Direct `pm-service` `/dev/subsys_modem` literal usage is classified against
  `pm_proxy_helper`.
- Remaining failure classes are ranked without claiming an unproven syscall.
- The next live gate is reduced to a bounded `pm-service` syscall/input
  classifier if exact cause remains unproven.

# Native Init V719 CNSS2 Service-positive Reconciliation Plan

- date: `2026-05-24 KST`
- scope: host-only reconciliation of same-window service-positive evidence and
  current-boot read-only evidence
- runner: `scripts/revalidation/native_wifi_cnss2_service_positive_reconcile_v719.py`

## Goal

Avoid mixing two different states:

1. the V717 same-window lower path where service-notifier `180/74` was present;
2. the V718 current boot after cleanup where service-notifier `180/74` was
   absent and `mss`/`mdm3` were `OFFLINING`.

The next Wi-Fi gate must be chosen from the service-positive window, not from a
post-reboot lower-not-ready state.

## Inputs

- service-positive evidence:
  `tmp/wifi/latest-v717-icnss-edge-long-observe.txt`
- current-boot read-only evidence:
  `tmp/wifi/latest-v718-cnss2-pd-notifier-readonly-current.txt`

## Classification Model

```text
modem ONLINE
  -> service-locator can resolve WLAN-PD
    -> service-notifier 180/74 appears
      -> kernel CNSS2 notifier should fire
        -> QCA6390 power/MHI/WLFW progresses
          -> service 69 / BDF / fw_ready / wlan0
```

V719 checks whether service-positive dmesg contains any of the kernel
progression markers:

- `qrtr-ns` companion startup observability and postflight safety;
- service-locator / SERVREG text, including whether any `SERVICE_STATE_UP`
  indication is visible;
- `pd_notifier` / `server_arrive`
- QCA6390-specific power or MHI/PCIe lines
- `icnss_qmi`
- WLFW, BDF, firmware-ready, or `wlan0`

It separately records whether the current boot is lower-ready.

## Guardrails

V719 is host-only:

- no device command execution;
- no daemon start;
- no Wi-Fi HAL, scan/connect, credential use, DHCP, route change, or external
  ping;
- no sysfs write;
- no boot image or partition write.

## Success Criteria

- `python3 -m py_compile` passes.
- `plan` and `run` produce manifests.
- V717 input is service `180/74` positive.
- V718 input is capture-clean.
- The final decision separates same-window service-positive evidence from the
  post-reboot lower-not-ready state.

## Expected Next Gate

If V719 confirms service `180/74` without CNSS2/QCA/WLFW progression, V720
should be a bounded live gate that reproduces lower readiness and captures
CNSS2 notifier-to-QCA transition in that same window. For SM8250, treat CNSS2
as the target driver path; legacy `ICNSS` labels are preserved only where they
are existing script names or literal kernel/log marker names.

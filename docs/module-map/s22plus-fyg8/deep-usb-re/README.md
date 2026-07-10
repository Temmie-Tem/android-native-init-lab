# FYG8 Deep USB Role RE

## Verdict

`PASS; EXACT ELF CALL PATH + MATCHED SOURCE + 11 DT OVERLAYS VERIFIED`.

This artifact is generated entirely on the host. It performs no ADB command,
device read/write, module insertion, reboot, image build, or flash.

## Exact Inputs

```text
modules=5
call_edges=21
g0q_overlays=11
g0q_dts_manifest=8e9c1bd351d08783adae5670d9b4813af8611b12e032959128f58c3289409255
stock_dtbo_sha256=97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
usb_notify_source_sha256=cdb489a2aecd3dc4c7d00899421d827c2aa64cd865e931b3a6cc6a3aa540d02b
```

`live-crosscheck.json`, when present, is a separately collected read-only stock
Android sidecar. It is preserved across host-only regeneration and is not an
input to this static verdict.

## Reconstructed Stock Path

```text
pdic_max77705
  max77705_usbc_probe -> typec_register_port
  max77705_ccic_event_work -> typec_set_data_role/typec_set_pwr_role
  max77705_ccic_event_notifier -> pdic_notifier_notify
        |
        v
usb_typec_manager
  pdic_notifier_register -> manager_event_work
  manager_event_notify -> blocking_notifier_call_chain
        |
        v
usb_notifier_qcom
  manager_notifier_register -> ccic_usb_handle_notification
  ccic callback -> send_otg_notify
  sec_otg_notify callback table -> qcom_set_host/qcom_set_peripheral
        |
        v
usb_notify_layer
  otg_notify_state: HOST -> set_host, VBUS -> set_peripheral
        |
        v
dwc3-msm
  qcom_set_host -> dwc_msm_id_event
  qcom_set_peripheral -> dwc_msm_vbus_event
  events -> OTG work -> parent/child USB role switches
```

Every arrow up to the notifier callback table is backed by a relocation in the
exact FYG8 modules. The `send_otg_notify -> otg_notify_state -> set_*` dispatch
is also present in the SHA-pinned Samsung `usb_notify.c` source and has matching
symbols in the exact `usb_notify_layer.ko`.

## Device Tree

All 11 g0q revision overlays contain the same relevant shape:

- `usb0` gets `usb-role-switch` and a `dwc3@a600000` child with
  `usb-role-switch` plus `dr_mode = "otg"`.
- Graph endpoints connect the USB controller overlay to the `ucsi` connector.
- `max77705@66/max77705_pdic` is on `qupv3_se5_i2c`, advertises
  `support_pd_role_swap`, and has no direct DWC3 phandle.
- `samsung,usb-notifier` is a separate platform node under `soc`.
- No overlay contains an explicit `extcon = ...` property for this path.

This matches a runtime notifier design, not a direct Max77705-to-DWC3 DT
dependency. DWC3 still imports some extcon APIs for other state/property paths;
that does not make extcon the proven attach transport here.

## Interpretation Boundary

The stock automatic role path requires more than `dwc3-msm.ko`: it includes the
Max77705 PDIC, Samsung Type-C manager, USB notifier, and USB notify layer. This
does not prove that a direct native PID1 implementation must clone the entire
chain. The separate exact `dwc3-msm.ko` forced-role path closes the narrower
question:

```text
mode_store("peripheral") -> dwc3_msm_set_role(role=2)
  -> set VBUS-active/role state -> dwc3_ext_event_notify
  -> OTG work -> dwc3_otg_start_peripheral
  -> usb_role_switch_set_role + vbus_session_notify + usb_gadget_connect
```

The mode attribute callback relocation, the `peripheral` literal-to-role-2
instruction path, the shared VBUS-active field, and all seven calls are verified
in the SHA-pinned FYG8 binary. Therefore the Max77705 notifier chain is not
required after `dwc3-msm` is successfully bound and this explicit mode write
executes. O3/O3F's chain omission cannot explain their no-USB result unless the
candidate never reached the mode write or an earlier/downstream gate failed.

## Web Cross-Check

Primary Linux/Android sources listed in `static-analysis.json` independently
confirm the method: Type-C port drivers report roles with `typec_set_*`, DWC3
uses `usb-role-switch` when that firmware property exists, and otherwise has an
extcon fallback. They validate the APIs and interpretation method; the exact
Samsung chain above comes from the pinned FYG8 binaries and source artifacts.

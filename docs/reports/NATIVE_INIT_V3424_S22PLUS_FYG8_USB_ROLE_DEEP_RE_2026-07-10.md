# V3424 S22+ FYG8 USB Role Deep RE and Live Cross-Check

## Verdict

`PASS-LIVE-ROLE-CROSSCHECK-PARTIAL; EXACT STOCK AUTOMATIC ROLE PATH RECONSTRUCTED; DIRECT-PID1 BYPASS NOT PROVED`.

V3424 reconstructed the FYG8 automatic Type-C/USB-role path from exact module
ELF relocations, matched Samsung source, and all g0q DT overlays. A separate
rooted-stock read-only capture then proved the selected board DT, all five
modules, the participating platform-driver binds, and an ordered live
PDIC-to-Type-C-manager notifier relay.

The current boot ring did not contain a USB attach event through
`usb_notifier_qcom` and DWC3. That downstream runtime segment is therefore
`NOT_CAPTURED_THIS_BOOT`, not promoted from source intent.

## Artifacts

```text
workspace/public/src/scripts/revalidation/s22plus_fyg8_usb_role_static_re.py
workspace/public/src/scripts/revalidation/s22plus_stock_usb_role_crosscheck_readonly.py
tests/test_s22plus_fyg8_usb_role_static_re.py
tests/test_s22plus_stock_usb_role_crosscheck_readonly.py
docs/module-map/s22plus-fyg8/deep-usb-re/README.md
docs/module-map/s22plus-fyg8/deep-usb-re/static-analysis.json
docs/module-map/s22plus-fyg8/deep-usb-re/live-crosscheck.json
workspace/private/runs/s22plus_stock_usb_role_crosscheck_readonly_20260709T235217Z/
```

The static generator pins every input hash and rejects missing edges, source
pattern drift, DT topology drift, stale generated files, and unexpected extra
files. The live sidecar is explicitly preserved as independent evidence and is
not an input to the static verdict.

## Exact Static Result

Five exact FYG8 modules were inspected:

```text
dwc3-msm.ko             8913b050419e88699033e957d927beef86742ed035f531dc5c4729f50cea60f1
pdic_max77705.ko        27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db
usb_typec_manager.ko    4da0a4d056abfb09e111ffc4f74fe0adbddcf7be0bc172a48c36f55fd0ea52dc
usb_notifier_qcom.ko    73f937efc9302d5fa8c2758b5e71b80f52063141d72c063bfe73b1583c781ccb
usb_notify_layer.ko     710d9cc6f523d615e459d22e2d9e3d1ff082514b7efcd6add0f437e890b3d294
```

Twenty-one exact call relocations reconstruct this stock path:

```text
pdic_max77705
  max77705_ccic_event_notifier -> pdic_notifier_notify
  max77705_ccic_event_work -> typec_set_data_role/typec_set_pwr_role
        |
        v
usb_typec_manager
  pdic_notifier_register -> manager_event_work
  manager_event_notify -> blocking_notifier_call_chain
        |
        v
usb_notifier_qcom
  manager_notifier_register -> ccic_usb_handle_notification
  ccic_usb_handle_notification -> send_otg_notify
  callback table -> qcom_set_host/qcom_set_peripheral
        |
        v
usb_notify_layer
  HOST -> set_host; VBUS -> set_peripheral
        |
        v
dwc3-msm
  qcom callbacks -> dwc_msm_id_event/dwc_msm_vbus_event
  queued OTG work -> parent/child USB role switches
```

The `usb_notify_layer` dispatch was additionally verified in Samsung
`usb_notify.c` SHA256
`cdb489a2aecd3dc4c7d00899421d827c2aa64cd865e931b3a6cc6a3aa540d02b`.

All 11 g0q revision overlays share the relevant topology. They provide
`usb-role-switch` on both `usb0` and `dwc3@a600000`, set the child to
`dr_mode = "otg"`, connect USB graph endpoints to UCSI, define
`max77705@66/max77705_pdic` with `support_pd_role_swap`, and define a separate
`samsung,usb-notifier` platform node. None contains an explicit `extcon = ...`
property or direct Max77705-to-DWC3 phandle. The exact stock DTBO SHA256 is
`97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`.

## Stock Live Result

The read-only capture passed against the exact known-booting Magisk boot SHA256
`2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.

```text
active model                    Samsung G0Q PROJECT (board-id,12)
modules loaded                  5/5
parent/child role-switch props  present/present
child dr_mode                   otg
Max77705/PDIC status            okay/okay
PD role-swap property           present
usb-notifier compatible         samsung,usb-notifier
max77705-usbc driver/module     bound/pdic_max77705
usb-notifier driver/module      bound/usb_notifier_qcom
msm-dwc3 driver/module          bound/dwc3_msm
read command failures           0
```

The retained filtered dmesg group was ordered:

```text
max77705_ccic_event_notifier
manager_handle_pdic_notification
manager_event_notify
manager_event_notify: notify done(0x0)
```

It was a `BATTERY/ID_POWER_STATUS` event, not a USB attach. It proves the live
PDIC-to-manager relay and manager notifier dispatch when combined with the exact
call relocation. It does not prove that this boot traversed
`ccic_usb_handle_notification -> send_otg_notify -> dwc_msm_*_event` for a USB
role change.

## Public-Source Cross-Check

The public sources validate the analysis method and API interpretation:

- Android common Type-C class implements `typec_set_data_role()` and
  `typec_set_pwr_role()` as port-driver role-reporting APIs that update role
  state and notify userspace:
  https://android.googlesource.com/kernel/common/+/5bad7993b0ff764e1ff37d00e370c0ed85661ea3/drivers/usb/typec/class.c
- Android common DWC3 DRD registers a firmware-described USB role switch and
  retains an extcon fallback path:
  https://android.googlesource.com/kernel/common/+/9e5737bd0457955690d871b3f4fc66dea40ea141/drivers/usb/dwc3/drd.c
- Qualcomm's public DWC3 MSM source provides the same general ID/VBUS event and
  queued-work pattern used to audit the exact FYG8 binary:
  https://android.googlesource.com/kernel/msm/+/53f9955dd5876826f623fb9a1a736cfe36bec176/drivers/usb/dwc3/dwc3-msm.c
- The upstream USB DRD DT binding defines the role and dual-role firmware
  description vocabulary used in the overlay audit:
  https://www.kernel.org/doc/Documentation/devicetree/bindings/usb/usb-drd.yaml

These sources do not establish Samsung FYG8's exact notifier chain. That board-
specific result comes from the pinned FYG8 binaries, matched Samsung source,
DT overlays, and live stock bind evidence above. Public search found no equally
authoritative exact FYG8 result that can replace this local proof.

## Interpretation

The stock automatic cable/role path is not a direct Max77705 extcon phandle. It
is a Samsung runtime notifier chain that eventually calls DWC3 role events.
Consequently, loading `dwc3-msm.ko` alone does not reproduce stock automatic
role policy.

At V3424 close, a fixed peripheral role was still classified
`PLAUSIBLE_NOT_PROVED`. V3425 subsequently verified the exact FYG8
`mode_store("peripheral")` instruction and call path through DWC3 peripheral
start and gadget connect. The later result supersedes this V3424 boundary.

## Safety and Validation

The static half was host-only. The live half used only fixed read operations:
`cat`, `stat`, `readlink`, `dmesg`, and the already reviewed V3423 topology
collector. It performed no flash, reboot, partition write, module insertion,
service control, sysfs write, or configfs write. Public and private artifacts
were scanned for the device serial and MAC-like values.

```text
static/deep-RE tests                  6/6 PASS at V3424 close
live cross-check tests               6/6 PASS
live result                          pass-live-role-crosscheck-partial
command failures                     0
static regeneration/check            PASS
```

## Next Bound

Correction: O0 had already passed in V3403, O1.1 in V3409, and O2 in V3410.
The original V3424 `O0 next` statement was stale and is retired by V3425.
V3424 narrows later native-PID1 reasoning and authorizes no new flash.

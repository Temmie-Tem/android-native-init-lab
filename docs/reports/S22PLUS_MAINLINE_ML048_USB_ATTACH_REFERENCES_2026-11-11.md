# ML048 reference investigation: USB enumeration with the cable already attached

The closest public reproduction found is the SM8450 Galaxy S22 SM-S901E
(`r0q`). Its author recorded the phone-side USB state both before and after
reconnecting the cable. The search did not identify a separate SM-S906N
(`g0q`) report with those observations. The comparison below uses the
[ML048 no-replug result](S22PLUS_MAINLINE_ML048_NO_REPLUG_RUN_2026-11-11.md)
as the S22+ baseline.

| Source | Observation | Scope |
| --- | --- | --- |
| [S22 attempt 4b](https://github.com/cammo1997/SM-S901E-Linux-Part-Working/blob/9863baf29b5a9cb30c3df3e466c5de6b04948557/docs/boot-log.md#L109-L115) | The author reports successful PHY and controller probing and gadget setup. At 7, 17 and 27 seconds the UDC still reported `not attached`. Software disconnect/connect did not bring up the link. After one physical replug the UDC reported `configured` and the PC acquired the network interface. | Direct reproduction on the smaller S22. ML048 has only host-side observations during the corresponding interval. |
| [Same S22, attempt 23](https://github.com/cammo1997/SM-S901E-Linux-Part-Working/blob/9863baf29b5a9cb30c3df3e466c5de6b04948557/docs/boot-log.md#L670-L682) | With a MAX77705 Type-C driver, connector/role-switch DT changes and other patches, the phone detected the PC, reported sink power role and device data role, configured the UDC, and served SSH about 25 seconds after boot without replugging. | Twelve patches were applied together. This before/after result does not isolate one patch. |
| [Galaxy Tab S8+ driver](https://github.com/aaronsb/sm-x800-linux/blob/6f32485482581692135eb50867a395a82d5d76fb/pmaports-overlay/device/testing/linux-postmarketos-qcom-sm8450/max77705-typec.patch#L1414-L1421) | Probe queues work to detect a partner that is already present. The [worker](https://github.com/aaronsb/sm-x800-linux/blob/6f32485482581692135eb50867a395a82d5d76fb/pmaports-overlay/device/testing/linux-postmarketos-qcom-sm8450/max77705-typec.patch#L1100-L1135) samples connection state, and the [role helper](https://github.com/aaronsb/sm-x800-linux/blob/6f32485482581692135eb50867a395a82d5d76fb/pmaports-overlay/device/testing/linux-postmarketos-qcom-sm8450/max77705-typec.patch#L580-L586) delivers host/device role to the USB controller. | Implementation provenance for the S22 changes, not an independent reproduction of the original failure. |
| [Upstream Linux commit 9835a6ef](https://github.com/torvalds/linux/commit/9835a6ef1a96b203278629bbcf5099622070c32b) | On a PXA27x board, an already-high VBUS produced no new interrupt during boot. The gadget could only enumerate after replugging. Sampling the VBUS GPIO at initialization supplied the missing initial state. | A demonstrated mechanism on a different PHY and board. |

## What differs on the tested S22+

The ML048 task's fixed capability identifies the exact kernel configuration
and DTB. The configuration enables `CONFIG_USB_DWC3_GADGET` and
`CONFIG_USB_ROLE_SWITCH`, while `CONFIG_TYPEC` is unset. The decoded DTB
contains `dr_mode = "peripheral"`, `maximum-speed = "high-speed"` and
`usb-role-switch`. It contains no MAX77705 compatible or
`role-switch-default-mode`. A role-switch property alone does not supply
the MAX77705 partner detection implemented in the reference port.
The [g0q DT source](../../workspace/public/src/mainline/s22plus_canary_h0/g0q.dtsi)
and [ML021 analysis](S22PLUS_MAINLINE_ML021_USB_ATTACH_H0_2026-11-04.md)
also describe the existing PHY/VBUS overrides.

The retained Samsung FYG8 vendor source takes a further step. Its MUIC
initial detection reads and classifies the connection status. For applicable
USB attachments it selects the application processor's USB data path.
The audited source hash matches the
[existing FYG8 source analysis](S22PLUS_FYG8_MAX77705_USB2_MUX_HYPOTHESIS_AND_FALSIFICATION_H0_2026-08-11.md).
This is code-path evidence for this board, not a measurement of ML048's
connector switch position.

The first useful distinction on g0q is whether USB gadget setup reached
the UDC bind and what state the UDC reported with the cable continuously
attached. A successful bind followed by persistent `not attached` would
match the r0q observation and focus investigation on initial partner
detection, role propagation and USB2 routing. An earlier setup failure
would place the investigation elsewhere. ML048's 88 absent host samples
cannot distinguish these cases.

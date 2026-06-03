# Native Init V1838 WLAN-PD Lower-Continuation Sampler Handoff

## Summary

- Cycle: `V1838`
- Type: one-run rollbackable WLAN-PD lower-continuation sampler discriminator
- Decision: `v1838-lower-continuation-static-gap-rollback-pass`
- Result: PASS
- Reason: read-only PMIC/GDSC focus samples remained static and MHI/WLFW/wlan0 stayed absent
- Evidence: `tmp/wifi/v1838-wlan-pd-lower-continuation-sampler-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`
- Post-rollback version ok: `True`
- Post-rollback selftest fail=0: `True`
- Post-rollback version evidence: `tmp/wifi/v1838-wlan-pd-lower-continuation-sampler-handoff/post-rollback-version-filtered.stdout.txt`
- Post-rollback selftest evidence: `tmp/wifi/v1838-wlan-pd-lower-continuation-sampler-handoff/post-rollback-selftest.stdout.txt`

## Gate Label

- lower-continuation label: `lower-continuation-static-gap`
- PM focus contract/safety: `True` / `True`
- PM focus change fields: `[]`
- PM focus mdm-status delta: `0`
- PM focus MHI/wlan0 progress: `False`
- QIPCRTR bound poll/recv label: `qipcrtr-bound-recv-poll-timeout-passive`
- WLFW QRTR readback label: `wlfw-readback-empty`
- service-locator domain label: `servloc-domain-wlan-pd-instance180`
- service-notifier label: `service-notifier-uninit`
- lower-state label: `stable-mdm3-offlining`
- safety ok: `True`

## PMIC/GDSC Focus Samples

- `wlan_pd_after_holder_start` begin/focus/end: `1` / `1` / `1`
- `wlan_pd_after_holder_start` mdm3/status/crash: `OFFLINING` / `0` / `0`
- `wlan_pd_after_holder_start` PCIe current/link/runtime/L23: `error:No such file or directory` / `error:No such file or directory` / `unsupported` / `100000`
- `wlan_pd_after_holder_start` GDSC seen lines: pcie1 `1` `pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV`; pcie0 `1` `pcie_0_gdsc                      0    1      0     0mV     0mA     0mV     0mV`
- `wlan_pd_after_holder_start` GPIO/PMIC lines: gpio135 `1` `gpio135 : out 0 16mA no pull`; gpio142 `1` `gpio142 : in  0 8mA no pull`; pmic `1` `pin 7 (gpio9): (MUX UNCLAIMED) c440000.qcom,spmi:qcom,pm8150l@4:pinctrl@c000:1270`
- `wlan_pd_after_holder_start` PCI/MHI/KS/wlan0: `0` / `0` / `0` / `0` / `0` / `0` / `0`
- `wlan_pd_after_holder_start` powerup process/thread/subsys-open: `1` / `0` / `0`
- `wlan_pd_after_holder_start` line-request/write/esoc-ioctl executed flags: `0` / `0` / `0`
- `wlan_pd_after_post_listener_window` begin/focus/end: `1` / `1` / `1`
- `wlan_pd_after_post_listener_window` mdm3/status/crash: `OFFLINING` / `0` / `0`
- `wlan_pd_after_post_listener_window` PCIe current/link/runtime/L23: `error:No such file or directory` / `error:No such file or directory` / `unsupported` / `100000`
- `wlan_pd_after_post_listener_window` GDSC seen lines: pcie1 `1` `pcie_1_gdsc                      0    2      0     0mV     0mA     0mV     0mV`; pcie0 `1` `pcie_0_gdsc                      0    1      0     0mV     0mA     0mV     0mV`
- `wlan_pd_after_post_listener_window` GPIO/PMIC lines: gpio135 `1` `gpio135 : out 0 16mA no pull`; gpio142 `1` `gpio142 : in  0 8mA no pull`; pmic `1` `pin 7 (gpio9): (MUX UNCLAIMED) c440000.qcom,spmi:qcom,pm8150l@4:pinctrl@c000:1270`
- `wlan_pd_after_post_listener_window` PCI/MHI/KS/wlan0: `0` / `0` / `0` / `0` / `0` / `0` / `0`
- `wlan_pd_after_post_listener_window` powerup process/thread/subsys-open: `1` / `0` / `0`
- `wlan_pd_after_post_listener_window` line-request/write/esoc-ioctl executed flags: `0` / `0` / `0`

## Inherited Lower State

- early/late service-notifier state: `uninit` / `uninit`
- mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`
- service180/service74/wlan_pd raw: `1,1,1` / `0,0,0` / `0,0,0`
- PM-client register/connect/return-path rc: `0` / `0` / `0`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1837/dev/__properties__`
- Transport: `serial-uudecode-tar-gz`
- Uploaded files/bytes: `22` / `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- The new V1838 surface only reads PMIC/GDSC, GPIO debugfs text, mdm3, PCIe, MHI, process, and `wlan0` state at two guarded lower-observer phases.
- The inherited route retains bounded QRTR/QMI probes from V1834: WLFW readback without QMI WLFW request payload, service-locator domain-list QMI, and service-notifier listener QMI.
- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, direct `/dev/subsys_esoc0` open, fake ONLINE, PMIC/GPIO/GDSC write, eSoC notify, BOOT_DONE spoof, forced RC1, `boot_wlan`, restart-PD request, PCI rescan, or platform bind/unbind was used.
- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Next

- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.
- If the label is `lower-continuation-static-gap`, classify the remaining mdm3/ext-SDX50M prerequisite gap before any next live action.

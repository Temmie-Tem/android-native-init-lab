# Native Init V1876 SDX50M Private Mount Handoff

## Summary

- Cycle: `V1876`
- Type: one-run rollbackable `A90 Linux init 0.9.170 (v1874-lower-response-readonly-sampler)` private SDX50M cnss-daemon mount discriminator
- Decision: `v1876-lower-input-power-clock-snapshot-gap-rollback-pass`
- Result: PASS
- Reason: read-only sampler captured pcie1 power/clock surface but lower publication stayed absent.
- Evidence: `tmp/wifi/v1876-lower-response-readonly-sampler-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`
- Post-rollback version ok: `True`
- Post-rollback selftest fail=0: `True`
- Post-rollback version evidence: `tmp/wifi/v1876-lower-response-readonly-sampler-handoff/post-rollback-version-filtered.stdout.txt`
- Post-rollback selftest evidence: `tmp/wifi/v1876-lower-response-readonly-sampler-handoff/post-rollback-selftest.stdout.txt`

## Gate Label

- private mount label: `private-mount-sdx50m-selected`
- open-context label/path/fd: `open-context-modem-success-static` / `/dev/subsys_modem` / `0x8`
- post-ack label/total: `post-ack-open-branch-reached` / `32`
- callback/ack label/total: `callback-ack-present-no-powerup` / `42`
- PM register candidate/requested/no-peripheral: `SDX50M` / `modem` / ``
- PM-service first add names/devnodes: `SDX50M,modem` / `/dev/subsys_esoc0,/dev/subsys_modem`
- lower-continuation label: `lower-continuation-static-gap`
- PM focus change fields / mdm-status delta: `[]` / `0`
- PM focus MHI/wlan0 progress: `False`
- service-notifier / QIPCRTR labels: `service-notifier-uninit` / `qipcrtr-bound-recv-poll-timeout-passive`
- lower-state label: `stable-mdm3-offlining`
- safety ok: `True`

## Private Mount

- contract/source/target/bind: `True` / `True` / `True` / `True`
- source path: `/cache/bin/cnss-daemon.sdx50m`
- target path: `/tmp/a90-v231-546/root/vendor/bin/cnss-daemon`
- source/target-before/target-after sizes: `95112` / `` / `95112`
- expected C string: `SDX50M`

## Lower State

- mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`
- service180/service74/wlan_pd raw: `1,1,1` / `0,0,0` / `0,0,0`
- PM-client register/connect/return-path rc: `0` / `0` / `0`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1874/dev/__properties__`
- Transport: `serial-uudecode-tar-gz`
- Uploaded files/bytes: `22` / `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Lower Response Input Contract

- contract label: `lower-input-power-clock-snapshot-gap`
- sample configured/observed: `12` / `12`
- offsets ms: `0,1,2,5,10,20,50,100,150,250,500,1000`
- guard read-only/no-esoc0/no-rc/no-pci/no-hal: `True` / `True` / `True` / `True` / `True`
- max mdm-status/pci/mhi/ks: `0` / `0` / `0` / `0`
- mhi-pipe/wlan0/pcie1-gdsc-line: `False` / `False` / `True`

## Safety Scope

- The only new live delta is namespace-local bind mounting the pre-staged private SDX50M `cnss-daemon` over the helper namespace `/vendor/bin/cnss-daemon`.
- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, direct `/dev/subsys_esoc0` open, fake ONLINE, PMIC/GPIO/GDSC write, eSoC notify, BOOT_DONE spoof, forced RC1, `boot_wlan`, restart-PD request, PCI rescan, or platform bind/unbind was used.
- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Next

- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.
- If the label is `private-mount-lower-publication-progress`, run a direct read-only prerequisite check before any connect attempt.
- If the label is `private-mount-pre-wifi-gap`, keep classifying the remaining mdm3/ext-SDX50M lower-response gap before another live mutation.

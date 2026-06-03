# Native Init V1868 SDX50M Private Mount Handoff

## Summary

- Cycle: `V1868`
- Type: one-run rollbackable `A90 Linux init 0.9.168 (v1867-sdx50m-private-mount-argvfix)` private SDX50M cnss-daemon mount discriminator
- Decision: `v1868-private-mount-bind-failed`
- Result: BLOCKED
- Reason: private SDX50M cnss-daemon bind-mount contract was not observed; stop before interpreting PM/lower-state deltas
- Evidence: `tmp/wifi/v1868-sdx50m-private-mount-argvfix-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`
- Post-rollback version ok: `True`
- Post-rollback selftest fail=0: `True`
- Post-rollback version evidence: `tmp/wifi/v1868-sdx50m-private-mount-argvfix-handoff/post-rollback-version-filtered.stdout.txt`
- Post-rollback selftest evidence: `tmp/wifi/v1868-sdx50m-private-mount-argvfix-handoff/post-rollback-selftest.stdout.txt`

## Gate Label

- private mount label: `private-mount-bind-failed`
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

- contract/source/target/bind: `False` / `False` / `False` / `False`
- source path: ``
- target path: ``
- source/target-before sizes: `` / ``
- expected C string: ``

## Lower State

- mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`
- service180/service74/wlan_pd raw: `1,1,1` / `0,0,0` / `0,0,0`
- PM-client register/connect/return-path rc: `0` / `0` / `0`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1867/dev/__properties__`
- Transport: `serial-uudecode-tar-gz`
- Uploaded files/bytes: `22` / `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- The only new live delta is namespace-local bind mounting the pre-staged private SDX50M `cnss-daemon` over the helper namespace `/vendor/bin/cnss-daemon`.
- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, direct `/dev/subsys_esoc0` open, fake ONLINE, PMIC/GPIO/GDSC write, eSoC notify, BOOT_DONE spoof, forced RC1, `boot_wlan`, restart-PD request, PCI rescan, or platform bind/unbind was used.
- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Next

- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.
- If the label is `private-mount-lower-publication-progress`, run a direct read-only prerequisite check before any connect attempt.
- If the label is `private-mount-pre-wifi-gap`, keep classifying the remaining mdm3/ext-SDX50M lower-response gap before another live mutation.

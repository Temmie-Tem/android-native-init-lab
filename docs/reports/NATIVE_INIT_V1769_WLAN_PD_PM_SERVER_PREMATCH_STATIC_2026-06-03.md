# Native Init V1769 WLAN-PD PM Server Pre-match Static Classifier

## Summary

- Cycle: `V1769`
- Type: host-only static disassembly classifier
- Decision: `v1769-pm-server-prematch-list-mutex-boundary-host-pass`
- Label: `pm-server-prematch-list-mutex-boundary`
- Result: PASS
- Reason: pm-service pre-match path is supported-peripheral list traversal through a per-record mutex getter; V1107 shows CNSS can wait behind a modem record mutex held by a pre-CNSS PM path
- Evidence: `tmp/wifi/v1769-wlan-pd-pm-server-prematch-static`

## Inputs

- pm-service binary: `tmp/wifi/v1073-host-only/vendor-extract/files/pm-service`
- V1768 branch classifier: `tmp/wifi/v1768-wlan-pd-pm-server-branch-classifier/manifest.json`
- V1107 mutex owner classifier: `tmp/wifi/v1107-pm-server-mutex-owner-classifier/manifest.json`
- V1107 report: `docs/reports/NATIVE_INIT_V1107_PM_SERVER_MUTEX_OWNER_CLASSIFIER_2026-05-27.md`

## Disassembly Artifacts

- pre-match range: `tmp/wifi/v1769-wlan-pd-pm-server-prematch-static/host/pm-service-register-prematch-0x6048-0x60cc.S`
- surrounding range: `tmp/wifi/v1769-wlan-pd-pm-server-prematch-static/host/pm-service-register-surrounding-0x6048-0x614c.S`
- record getter: `tmp/wifi/v1769-wlan-pd-pm-server-prematch-static/host/pm-service-record-getter-0x9538-0x9568.S`

## Facts

- V1768 pre-match label retained: `True`
- Pre-match iterates supported list: `True`
- Pre-match calls record getter `0x9538`: `True`
- Pre-match uses `strcmp`: `True`
- Match branch target is `0x60cc`: `True`
- Permission/caller UID starts after match: `True`
- Getter locks/unlocks record mutex: `True`
- V1107 mutex owner blocked: `True`
- V1107 owner return offset: `0x87c8`
- V1107 owner wchans: `['__subsystem_get', '_request_firmware', 'binder_ioctl_write_read']`
- V1107 CNSS waiter wchans: `['binder_ioctl_write_read', 'futex_wait_queue_me']`

## Interpretation

- The `0x6048..0x60cc` path is not a service-manager or permission branch; it is supported-peripheral list traversal.
- The only call before the first match checkpoint is the per-record getter at `0x9538`, followed by dereferencing the requested peripheral string and `strcmp`.
- Caller UID permission checks start after `0x60cc`, so UID/SELinux permission is not the retained V1768 pre-match boundary.
- V1107 independently shows the same modem record mutex can be held by a pre-CNSS PM path while CNSS waits in `futex_wait_queue_me`.
- Combined label: the retained blocker is best modeled as a pre-match list/mutex boundary, not as missing provider registration.

## Consequence

- A live PM gate, if explicitly reopened, should avoid pre-CNSS `per_proxy`/positive-control connect paths that hold the modem record mutex.
- While the current stop remains active, the only aligned follow-up is host/source-only reconstruction of the minimal CNSS-first PM register ordering and its expected labels.

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PM actor start, QCACLD load, eSoC/RC1 action, restart-PD request, firmware write, partition write, PMIC/GPIO/GDSC write, PCI rescan, platform bind/unbind, BPF attach, or tracefs write.

## Next

- Draft a host-only CNSS-first PM register ordering contract that removes pre-CNSS `per_proxy` connect as a positive-control side effect.
- Do not live-run that route unless a new directive explicitly reopens the narrow PM register gate.
- Completion remains unproven: native Wi-Fi has not reached WLFW service 69, `wlan0`, scan/connect, or external ping.
